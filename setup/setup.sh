#!/usr/bin/env bash
set -euo pipefail

# ==============================================================
# Grid'5000 experiment environment setup
# ==============================================================
# Steps:
#   1. Install Nix (daemon mode)
#   2. Run `nix develop` + install joule-profiler
# ==============================================================

LOG() { echo -e "\n\033[1;34m==>\033[0m $*"; }
OK()  { echo -e "\033[1;32m  ✔ $*\033[0m"; }
WARN(){ echo -e "\033[1;33m  ⚠ $*\033[0m"; }

# --------------------------------------------------------------
# Step 0 — Obtain sudo privileges via Grid'5000 helper
# --------------------------------------------------------------
if command -v sudo-g5k &>/dev/null; then
  LOG "Obtaining sudo privileges..."
  /usr/bin/sudo-g5k
  OK "sudo privileges granted"
else
  WARN "sudo-g5k not found, skipping sudo privilege step."
fi

# --------------------------------------------------------------
# Step 1 — Install Nix (daemon mode, skip if already present)
# --------------------------------------------------------------
LOG "Installing Nix..."
if command -v nix &>/dev/null; then
  WARN "Nix already installed ($(nix --version)), skipping."
else
  sh <(curl --proto '=https' --tlsv1.2 -L https://nixos.org/nix/install) --daemon
  OK "Nix installed"

  # Source Nix into the current shell without reopening the terminal
  if [ -f /etc/profile.d/nix.sh ]; then
    . /etc/profile.d/nix.sh
  elif [ -f "$HOME/.nix-profile/etc/profile.d/nix.sh" ]; then
    . "$HOME/.nix-profile/etc/profile.d/nix.sh"
  fi
fi

# --------------------------------------------------------------
# Step 2 — Enter nix dev shell + install joule-profiler
# --------------------------------------------------------------
LOG "Entering nix dev shell and installing joule-profiler..."

NIX_FLAGS="--extra-experimental-features nix-command --extra-experimental-features flakes"

# Run joule-profiler installation inside the dev shell non-interactively,
# then drop the user into an interactive shell.
nix $NIX_FLAGS develop --command bash -c "
  echo 'Running joule-profiler installation...'
  
  cargo install joule-profiler-cli

  echo 'Setting perf_event_paranoid level to 0.'
  sudo sysctl kernel.perf_event_paranoid=0
  sudo cpupower frequency-set -g performance
  echo off | sudo tee /sys/devices/system/cpu/smt/control
  
  echo ''
  echo 'joule-profiler installation done'

  echo "Cloning gson project..."
  git clone https://github.com/google/gson.git ../gson

  echo 'All setup complete - you are now inside the nix dev shell.'
  exec bash
"
