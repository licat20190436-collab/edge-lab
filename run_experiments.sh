#!/bin/bash
# run_experiments.sh — Reproduce key experimental groups
#
# CRITICAL REPRODUCTION NOTE (discovered during replication, Oct 2026):
# -----------------------------------------------------------------------
# Group C collapse (C120) requires the following exact timing sequence:
#   1. Run C100 first (warms Redis cache for eiffel-tower, TTL=30s)
#   2. Wait exactly 35 seconds (cache expires, next request is MISS)
#   3. Immediately run C120 (all 120 concurrent requests arrive as MISS,
#      triggering tidal synchronization + queue exhaustion)
#
# If C120 is run with a warm cache, requests are served from Redis HIT
# and FastAPI memory pressure never materialises — no collapse observed.
# This timing dependency explains the non-monotonic oscillation across
# repeated trials and is consistent with the tidal synchronization theory.
# -----------------------------------------------------------------------
#
# Requirements: hey (https://github.com/rakyll/hey/releases/tag/v0.1.4)
# Usage: bash run_experiments.sh [C|F|B|D|E|repeat_c120|repeat_f120]

URL="http://localhost/api/attraction/eiffel-tower"
COOL=90

run_hey() {
    local label=$1
    local concurrency=$2
    echo "=== ${label}: ${concurrency} concurrent ==="
    hey -c "$concurrency" -z 30s "$URL"
    echo "--- Cooling down ${COOL}s ---"
    sleep "$COOL"
}

# Warm cache then expire, then hit with target concurrency
# This is the key sequence for reproducing Group C collapse
run_c_with_cache_expire() {
    local label=$1
    local concurrency=$2
    echo "=== ${label}: ${concurrency} concurrent (cache-expire sequence) ==="

    # Step 1: flush and warm cache with C100
    docker exec edge_redis redis-cli FLUSHALL 2>/dev/null || \
    docker exec edge-lab-redis-1 redis-cli FLUSHALL
    echo "Warming cache with C100..."
    hey -c 100 -z 30s "$URL" > /dev/null 2>&1

    # Step 2: wait for TTL=30s cache to expire
    echo "Waiting 35s for cache TTL to expire..."
    sleep 35

    # Step 3: immediately fire target concurrency (cache is cold)
    echo "Firing ${concurrency} concurrent requests (cold cache)..."
    hey -c "$concurrency" -z 30s "$URL"

    echo "--- Cooling down ${COOL}s ---"
    sleep "$COOL"
}

change_memory() {
    local limit=$1
    sed -i "s/mem_limit: [0-9]*m/mem_limit: ${limit}/" docker-compose.yml
    docker compose up -d --force-recreate fastapi
    sleep 30
    echo "Memory limit set to ${limit}"
    docker inspect edge_fastapi --format='Actual limit: {{.HostConfig.Memory}} bytes' \
        2>/dev/null || \
    docker inspect edge-lab-fastapi-1 --format='Actual limit: {{.HostConfig.Memory}} bytes'
}

case "$1" in
    C)
        echo "=== Group C: 128MB + fixed weak network ==="
        change_memory 128m
        bash setup_netem.sh fixed
        run_c_with_cache_expire "C1" 100
        run_c_with_cache_expire "C2" 120
        run_c_with_cache_expire "C3" 150
        run_c_with_cache_expire "C4" 180
        run_c_with_cache_expire "C5" 200
        ;;

    F)
        echo "=== Group F: 128MB + jittered weak network ==="
        change_memory 128m
        bash setup_netem.sh jitter
        run_c_with_cache_expire "F1" 120
        run_c_with_cache_expire "F2" 150
        ;;

    B)
        echo "=== Group B: 128MB no impairment ==="
        change_memory 128m
        bash setup_netem.sh none
        for c in 100 120 150 180 200 300; do
            run_hey "B_c${c}" "$c"
        done
        ;;

    D)
        echo "=== Group D: 256MB no impairment ==="
        change_memory 256m
        bash setup_netem.sh none
        for c in 100 150 200 300; do
            run_hey "D_c${c}" "$c"
        done
        ;;

    E)
        echo "=== Group E: 256MB fixed weak network ==="
        change_memory 256m
        bash setup_netem.sh fixed
        for c in 100 150 200 300; do
            run_c_with_cache_expire "E_c${c}" "$c"
        done
        ;;

    repeat_c120)
        echo "=== Repeatability: C120 x10 (Group C conditions) ==="
        change_memory 128m
        bash setup_netem.sh fixed
        LOGDIR=./logs/C120_repeat
        mkdir -p "$LOGDIR"
        for i in $(seq 1 10); do
            echo "--- Run ${i}/10 ---"
            docker exec edge_redis redis-cli FLUSHALL 2>/dev/null || \
            docker exec edge-lab-redis-1 redis-cli FLUSHALL
            hey -c 100 -z 30s "$URL" > /dev/null 2>&1
            echo "Waiting 35s for cache expiry..."
            sleep 35
            hey -c 120 -z 30s "$URL" | tee "${LOGDIR}/run_${i}.txt"
            echo "Cooling ${COOL}s..."
            sleep "$COOL"
        done
        echo "=== Summary ==="
        for i in $(seq 1 10); do
            f="${LOGDIR}/run_${i}.txt"
            success=$(grep "\[200\]" "$f" | awk '{print $2}')
            timeout=$(grep "context deadline" "$f" | awk '{print $2}')
            total=$(( ${success:-0} + ${timeout:-0} ))
            rate=$(( total > 0 ? 100 * ${success:-0} / total : 0 ))
            echo "Run ${i}: success=${success:-0} timeout=${timeout:-0} rate=${rate}%"
        done | tee "${LOGDIR}/summary.txt"
        ;;

    repeat_f120)
        echo "=== Repeatability: F120 x10 (Group F conditions) ==="
        change_memory 128m
        bash setup_netem.sh jitter
        LOGDIR=./logs/F120_repeat
        mkdir -p "$LOGDIR"
        for i in $(seq 1 10); do
            echo "--- Run ${i}/10 ---"
            docker exec edge_redis redis-cli FLUSHALL 2>/dev/null || \
            docker exec edge-lab-redis-1 redis-cli FLUSHALL
            hey -c 100 -z 30s "$URL" > /dev/null 2>&1
            echo "Waiting 35s for cache expiry..."
            sleep 35
            hey -c 120 -z 30s "$URL" | tee "${LOGDIR}/run_${i}.txt"
            echo "Cooling ${COOL}s..."
            sleep "$COOL"
        done
        echo "=== Summary ==="
        for i in $(seq 1 10); do
            f="${LOGDIR}/run_${i}.txt"
            success=$(grep "\[200\]" "$f" | awk '{print $2}')
            timeout=$(grep "context deadline" "$f" | awk '{print $2}')
            total=$(( ${success:-0} + ${timeout:-0} ))
            rate=$(( total > 0 ? 100 * ${success:-0} / total : 0 ))
            echo "Run ${i}: success=${success:-0} timeout=${timeout:-0} rate=${rate}%"
        done | tee "${LOGDIR}/summary.txt"
        ;;

    *)
        echo "Usage: $0 [C|F|B|D|E|repeat_c120|repeat_f120]"
        echo ""
        echo "  C            — Group C: 128MB + fixed 150ms+5% loss"
        echo "  F            — Group F: 128MB + jitter 150ms+-20ms+5% loss"
        echo "  B            — Group B: 128MB no impairment"
        echo "  D            — Group D: 256MB no impairment"
        echo "  E            — Group E: 256MB + fixed 150ms+5% loss"
        echo "  repeat_c120  — Run C120 x10 for repeatability analysis"
        echo "  repeat_f120  — Run F120 x10 for repeatability analysis"
        echo ""
        echo "IMPORTANT: hey must be installed at /usr/local/bin/hey"
        echo "Download: https://github.com/rakyll/hey/releases/tag/v0.1.4"
        exit 1
        ;;
esac

echo "=== Experiment complete ==="
