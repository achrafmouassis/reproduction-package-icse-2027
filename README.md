# ICSE 2027 Tool Demonstration and Data Showcase - Reproduction Package

This repository contains the reproduction package for the ICSE submission. Follow the steps below to set up the environment, run the benchmarks, and visualize the results.

---

## Requirements

- Internet access (for downloading dependencies during setup)
- RAPL (Running Average Power Limit) with the perf_event interface.

---

## Step 1 — Environment Setup

Borrow a node on Grid'5000 (replace the cluster placeholder):
```
oarsub -p {cluster} -l host=1,walltime=2:00:00 "sleep 365d"
```

Navigate to the `setup/` directory and run the setup script:

```bash
cd setup
./setup.sh
cd ..
```

This script will:

- Initialize a **Nix** environment with all required system dependencies
- Install **[Joule Profiler](https://github.com/joule-profiler/joule-profiler)**
- Install **Maven**
- Install **Gson**

---

## Step 2 — Run the Benchmarks

Once the environment is set up, return to the root of the repository and run the benchmark script using `uv`:

```bash
uv run notebooks/bench.py
```

This will execute the full benchmark suite and write the results into the `results` folder.

---

## Step 3 — Visualize Results

Two [Marimo](https://marimo.io/) notebooks are provided for exploring and visualizing the benchmark results.

### Aggregate results

Before aggregating, validate the cold/warm pairs with Python 3.10 or later.
Extract the published archive first, or use the results directory of a fresh benchmark.

~~~bash
python -m zipfile -e results.zip .
python validate_results.py results
~~~

The check reads each iteration directory and requires a readable JSON report
with phases and a successful Maven exit code for both builds. It reports the
file paths of any failures and exits with status 1. It detects missing
reports inside existing iterations, but cannot infer entirely missing iterations.
It uses only the Python standard library and requires no access to RAPL.

```bash
uv run marimo edit notebooks/01_aggregate.py
```

Loads and aggregates raw benchmark outputs and export results in the `data` folder.

### Visualize results

```bash
uv run marimo edit notebooks/02_visualise.py
```

Produces plots and summary statistics from the aggregated data.

### Dataset

Our experiments dataset, conducted on Grid'5000 (https://www.grid5000.fr) on a chirop cluster node (2 Intel Xeon Platinum 8358, 512 GB RAM, kernel
version 5.10.0-38-amd64) is located in the `results.zip` archive.
Also, the aggregated data is located in the `data.zip` archive.
