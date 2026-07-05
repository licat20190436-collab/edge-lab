#!/bin/bash
# run_experiments.sh — Load injection for all experimental groups
# Requires: hey (https://github.com/rakyll/hey)
# Usage: bash run_experiments.sh [group]
# Example: bash run_experiments.sh B

URL="http://localhost/api/attraction/eiffel-tower"
COOL=90   # seconds between runs

run_hey() {
  local label=$1
  local concurrency=$2
  echo "=== ${label}: ${concurrency} concurrent ==="
  hey -c "$concurrency" -z 30s "$URL"
  echo "--- Cooling down ${COOL}s ---"
  sleep "$COOL"
}

change_memory() {
  local limit=$1
  sed -i "s/mem_limit: [0-9]*m/mem_limit: ${limit}/" docker-compose.yml
  docker compose up -d --force-recreate fastapi
  docker inspect edge_fastapi --format='{{.HostConfig.Memory}}'
  sleep 30
}

case "$1" in
  A)
    echo "=== Group A: 400MB unconstrained ==="
    change_memory 400m
    bash setup_netem.sh none
    run_hey "A1" 50
    run_hey "A2" 100
    bash setup_netem.sh fixed
    run_hey "A3" 100
    run_hey "A4" 300
    ;;

  B)
    echo "=== Group B: 128MB no impairment ==="
    change_memory 128m
    bash setup_netem.sh none
    for c in 100 120 150 180 200 300; do
      run_hey "B_c${c}" "$c"
    done
    ;;

  C)
    echo "=== Group C: 128MB fixed weak network ==="
    change_memory 128m
    bash setup_netem.sh fixed
    for c in 100 120 150 180 200; do
      run_hey "C_c${c}" "$c"
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
      run_hey "E_c${c}" "$c"
    done
    ;;

  F)
    echo "=== Group F: 128MB jittered weak network ==="
    change_memory 128m
    bash setup_netem.sh jitter
    run_hey "F1" 120
    run_hey "F2" 150
    ;;

  G)
    echo "=== Group G: 256MB no impairment 300 concurrent (reproducibility) ==="
    change_memory 256m
    bash setup_netem.sh none
    run_hey "G1" 300
    echo "Waiting 120s for TCP TIME-WAIT to drain..."
    sleep 120
    run_hey "G2" 300
    ;;

  *)
    echo "Usage: $0 [A|B|C|D|E|F|G]"
    echo "  A — 400MB unconstrained baseline"
    echo "  B — 128MB no impairment"
    echo "  C — 128MB fixed weak network (150ms+5% loss)"
    echo "  D — 256MB no impairment"
    echo "  E — 256MB fixed weak network"
    echo "  F — 128MB jittered weak network (150ms±20ms+5% loss)"
    echo "  G — 256MB no impairment, 300 concurrent, reproducibility check"
    exit 1
    ;;
esac

echo "=== Experiment complete ==="
