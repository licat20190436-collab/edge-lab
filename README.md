# Edge Microservice Cascading Failure Benchmark

Experimental artifacts for the paper:

**"Cascading Failure Characterization in Resource-Constrained Edge Microservices Under Cross-Border Weak Network Conditions"**  
Junrui Li, Department of Electronic Engineering, The Chinese University of Hong Kong

---

## Overview

This repository contains all scripts and data used to reproduce the experiments in the paper. The testbed is a three-tier containerized microservice stack (Nginx → FastAPI → Redis) deployed on a single 1 GB virtual machine, with network impairment simulated using Linux `tc netem`.

---

## Testbed Requirements

| Component | Specification |
|---|---|
| OS | Debian 12 |
| CPU | 1 vCPU |
| RAM | 961 MB |
| Provider | Vultr (Bangalore, India) |
| Docker | 24.x + Docker Compose v2 |
| Load tool | [hey](https://github.com/rakyll/hey) |

---

## Repository Structure

```
edge-lab/
├── docker-compose.yml          # Three-tier service configuration
├── scripts/
│   ├── setup_netem.sh          # Network impairment configuration
│   └── run_experiments.sh      # Load injection for all groups
├── data/
│   └── results.xlsx            # Aggregated measurement results
├── figures/
│   └── plot_benchmark.py       # Figure generation script
└── README.md
```

---

## Reproducing the Experiments

### 1. Deploy the stack

```bash
git clone https://github.com/<your-username>/edge-lab.git
cd edge-lab
docker compose up -d
```

### 2. Configure network impairment

```bash
# No impairment (Groups A, B, D, G)
bash scripts/setup_netem.sh none

# Fixed 150ms delay + 5% loss (Groups C, E)
bash scripts/setup_netem.sh fixed

# Jittered 150ms ±20ms delay + 5% loss (Group F)
bash scripts/setup_netem.sh jitter
```

### 3. Run load injection

```bash
# Example: run Group C experiments
bash scripts/run_experiments.sh C
```

Each run lasts 30 seconds with a 90-second cooling period between runs.

---

## Experimental Groups

| Group | Memory | Network | Concurrency | Purpose |
|---|---|---|---|---|
| A | 400 MB | None / Fixed | 50, 100, 300 | Unconstrained baseline |
| B | 128 MB | None | 100–300 | Memory-constrained baseline |
| C | 128 MB | Fixed 150ms+5% | 100–200 | Weak network + memory |
| D | 256 MB | None | 100–300 | Higher memory baseline |
| E | 256 MB | Fixed 150ms+5% | 100–300 | Higher memory + weak network |
| F | 128 MB | Jittered 150ms±20ms+5% | 120, 150 | Tidal sync isolation |
| G | 256 MB | None | 300 × 2 | Reproducibility check |

---

## Generating Figures

```bash
pip install matplotlib pandas numpy
python figures/plot_benchmark.py
```

Output: four PNG figures saved in the current directory.

---

## Key Finding

Under fixed 150 ms delay, 120 concurrent connections produce **0% success rate** (tidal synchronization effect). Replacing fixed delay with ±20 ms jitter recovers success rate to **98.7%** at the same concurrency level, with no application changes.

---

## License

MIT License. Data and scripts are freely available for research use.
