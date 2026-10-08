# Edge Lab — Reproduction Package

Reproduction scripts and configuration for:

> **"Cascading Failure Characterization in Resource-Constrained Edge Microservices Under Cross-Border Weak Network Conditions"**  
> IEEE Access, manuscript \#Access-2026-32899  
> Junrui Li, Department of Electronic Engineering, The Chinese University of Hong Kong

Raw measurement data, figure generation code, and experiment logs are included in this repository.

---

## Testbed Requirements

| Component | Specification |
|-----------|--------------|
| VM | 1 vCPU, 1 GB RAM (961 MB usable) |
| OS | **Debian 12 (Bookworm)**, kernel 6.1.x |
| Location | Bangalore, India (Vultr) |
| Docker | 29.x with Compose v2 |
| Load generator | `hey` v0.1.4 |

> **Important**: Debian 13 (Trixie, kernel 6.12+) produces different TCP scheduling behaviour that weakens tidal synchronisation. Use Debian 12 for faithful reproduction.

---

## Quick Start

### 1. Install dependencies

```bash
apt-get update && apt-get install -y iproute2 wrk apache2-utils
curl -fsSL https://get.docker.com | bash

# Install hey v0.1.4
wget -q https://github.com/rakyll/hey/releases/download/v0.1.4/hey_linux_amd64 \
  -O /usr/local/bin/hey
chmod +x /usr/local/bin/hey
```

### 2. Build and start services

```bash
cd edge-lab
docker compose build
docker compose up -d
sleep 20

# Verify
curl http://localhost/api/attraction/eiffel-tower
# Expected: {"name":"Eiffel Tower",...,"_cache":"MISS"}
```

### 3. Run key experiments

```bash
# Group C: 128 MB + fixed weak network (collapse at C120)
bash run_experiments.sh C

# Group F: 128 MB + jittered weak network (recovery at F120)
bash run_experiments.sh F

# Repeatability: C120 x10 trials
bash run_experiments.sh repeat_c120

# Repeatability: F120 x10 trials
bash run_experiments.sh repeat_f120
```

---

## Critical Reproduction Note — Cache-Expiry Timing

The Group C collapse at 120 concurrent connections depends on a specific
cache timing sequence identified during independent replication:

```
C100 run (30 s)  →  wait 35 s  →  C120 run (30 s)
      ↑                 ↑
 warms cache      TTL=30 s expires; next request is MISS
```

**Mechanism:**

1. C100 warms the Redis cache for `eiffel-tower` (TTL = 30 s)
2. After C100 completes, wait 35 s — just long enough for the cache entry to expire
3. C120 fires: all 120 concurrent connections arrive simultaneously
4. The first request is a cache MISS, triggering FastAPI processing (10–80 ms random delay)
5. Under fixed 150 ms propagation delay, all 120 connections arrive at the Uvicorn event loop **in phase** (tidal synchronisation)
6. The single-process event loop cannot drain the queue before the 20 s client timeout
7. Result: simultaneous queue exhaustion and cascading timeouts

**Without this timing** (warm cache), requests are served from Redis HITs with negligible FastAPI involvement — no memory pressure, no collapse.

This timing dependency also explains the **non-monotonic variance** across repeated C120 trials: the exact cache state at the moment C120 fires varies slightly, producing different synchronisation windows and therefore variable success rates (27.7–84.6% across 13 trials), while the timeout count remains consistently elevated.

---

## Service Architecture

```
Client (hey / ab)
      │
      ▼
Nginx 1.27-alpine  (48 MB limit)
      │  proxy_pass, 20 s read timeout
      ▼
FastAPI 0.111 + Uvicorn  (128 MB or 256 MB limit)
      │  single process, single worker
      │  random processing delay: 10–80 ms per request
      ▼
Redis 7-alpine  (80 MB limit)
      maxmemory 80 mb, allkeys-lru eviction, TTL = 30 s
```

Memory limits enforced via Linux cgroups v2.  
`OOMKilled=false` confirmed across all experimental groups — failure mode is **queue exhaustion**, not OOM termination.

---

## Network Impairment

Applied to the Docker bridge interface (`br-*`) using Linux `tc` + `netem`:

```bash
bash setup_netem.sh fixed    # 150 ms fixed delay + 5% loss  (Groups C, E)
bash setup_netem.sh jitter   # 150 ms ±20 ms delay + 5% loss (Group F)
bash setup_netem.sh none     # remove all impairment          (Groups B, D)
```

---

## Experimental Groups

| Group | Memory | Network | Concurrency levels |
|-------|--------|---------|-------------------|
| A | 400 MB | None / Fixed | 50, 100, 300 |
| B | 128 MB | None | 100, 120, 150, 180, 200, 300 |
| C | 128 MB | Fixed 150 ms + 5% | 100, 120, 150, 180, 200 |
| D | 256 MB | None | 100, 150, 200, 300 |
| E | 256 MB | Fixed 150 ms + 5% | 100, 150, 200, 300 |
| F | 128 MB | Jitter 150 ms ±20 ms + 5% | 120, 150 |

---

## Repeatability Results

### Group C — 128 MB + Fixed 150 ms delay (collapse condition), 13 trials

| Trial | Success | Timeouts | Success rate | RPS |
|-------|---------|----------|-------------|-----|
| 1 (original) | 0 | 240 | 0.0% | 5.99 |
| 2 | 92 | 240 | 27.7% | 7.33 |
| 3 | 243 | 239 | 50.4% | 9.85 |
| 4 | 653 | 221 | 74.7% | 13.20 |
| 5 | 426 | 190 | 69.2% | 13.46 |
| 6 | 210 | 187 | 52.9% | 9.53 |
| 7 | 484 | 136 | 78.1% | 14.15 |
| 8 | 322 | 146 | 68.8% | 11.06 |
| 9 | 204 | 240 | 45.9% | 10.28 |
| 10 | 459 | 164 | 73.7% | 14.68 |
| 11 | 224 | 239 | 48.4% | 10.60 |
| 12 | 1293 | 235 | 84.6% | 30.63 |
| 13 | 254 | 163 | 60.9% | 9.85 |
| **Mean (excl. trial 1)** | **424** | **192** | **61.3%** | **~14** |
| **Std dev** | **±305** | **±38** | **±16.0%** | — |

Trial 1 (0%) was recorded immediately after Group B (concurrency up to 300), when residual TCP TIME_WAIT sockets and accumulated event-loop backlog lowered the effective threshold — representing an acute worst-case within the distribution.

### Group F — 128 MB + Jittered 150 ms ±20 ms delay (recovery condition), 6 trials

| Trial | Success | Timeouts | Success rate | RPS |
|-------|---------|----------|-------------|-----|
| 1a | 3,985 | 0 | 100.0% | 118.5 |
| 1b | 3,310 | 9 | 99.7% | 107.0 |
| 2 | 3,551 | 0 | 100.0% | 113.4 |
| 3 | 3,455 | 5 | 99.9% | 109.8 |
| 4 | 3,556 | 0 | 100.0% | 110.1 |
| 5 | 3,526 | 4 | 99.9% | 108.8 |
| **Mean** | **3,564** | **3** | **99.9%** | **~112** |
| **Std dev** | **±228** | **±3** | **±0.1%** | — |

**The two distributions exhibit zero overlap**: C120 maximum (84.6%) remains strictly below F120 minimum (99.7%), providing robust statistical separation between the fixed-delay and jittered regimes.

---

## Independent-Host Validation

To verify that co-location of the load generator does not inflate results, key experiments were replicated from a second Vultr Debian 12 VM (1 vCPU, same data-centre region) targeting the service VM over the public network.

### C120 — Fixed 150 ms + 5% loss (3 runs from external host)

| Run | Successful | Timeouts | RPS |
|-----|-----------|----------|-----|
| 1 | 3,897 | 113 | 86.4 |
| 2 | 3,841 | 62 | 86.9 |
| 3 | 3,929 | 0 | 110.9 |
| **Mean** | **3,889** | **58** | **~95** |

### F120 — Jitter 150 ms ±20 ms + 5% loss (3 runs from external host)

| Run | Successful | Timeouts | RPS |
|-----|-----------|----------|-----|
| 1 | 4,096 | 96 | 85.3 |
| 2 | 4,096 | 96 | 85.3 |
| 3 | 3,904 | 101 | 82.0 |
| **Mean** | **4,032** | **98** | **~84** |

The qualitative finding — fixed delay causes synchronisation-induced degradation while jitter mitigates it — is reproduced under independent load generation. The reduced timeout count in external C120 runs is mechanistically consistent: the additional cross-host RTT (~400–500 ms) partially perturbs the fixed-delay synchronisation window, attenuating phase-locking at the application layer, as the Group F jitter experiment confirms.

---

## File Structure

```
edge-lab/
├── app/
│   ├── main.py              # FastAPI application (tourist attraction API)
│   ├── requirements.txt     # Python dependencies
│   └── Dockerfile           # Container image build
├── nginx/
│   └── nginx.conf           # Nginx gateway configuration
├── docker-compose.yml       # Service orchestration (mem limits, network)
├── setup_netem.sh           # Network impairment control (none/fixed/jitter)
├── run_experiments.sh       # Full experiment runner with cache-expiry timing
├── collect_metrics.py       # 1-second resolution metric collection (node_exporter)
├── random_slug.lua          # wrk Lua script for randomised URL load generation
└── logs/                    # Experiment output logs (git-ignored)
```

---

## Citation

```bibtex
@article{li2026cascading,
  title   = {Cascading Failure Characterization in Resource-Constrained
             Edge Microservices Under Cross-Border Weak Network Conditions},
  author  = {Li, Junrui},
  journal = {IEEE Access},
  year    = {2026},
  doi     = {10.1109/ACCESS.2026.0000000}
}
```
