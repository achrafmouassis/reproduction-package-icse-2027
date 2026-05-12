# Setup

This folder contains the environment setup for running Grid'5000 experiments.

## Files

- `flake.nix` — Nix flake defining the reproducible dev shell (Java 17, Maven, Rust via fenix, Python 3.12, uv)
- `setup.sh` — Bootstrap script: installs Nix in daemon mode, then enters the dev shell and installs `joule-profiler-cli`

## Usage

```bash
cd setup
./setup.sh
```

Once the script completes, you are dropped into the Nix dev shell with all dependencies available.

To re-enter the dev shell later without re-running the full setup:

```bash
nix develop --extra-experimental-features "nix-command flakes"
```

## Requirements

- Linux x86_64 (Grid'5000 node)