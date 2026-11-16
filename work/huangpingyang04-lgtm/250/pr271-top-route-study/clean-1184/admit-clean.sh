#!/usr/bin/env bash
#SBATCH --job-name=hpy-pr276-admit
#SBATCH --partition=c64,c96,debug
#SBATCH --cpus-per-task=1
#SBATCH --time=00:13:00
set -euo pipefail
root=$(pwd -P)
layout="$root/admitted-layout"
receipts=()
for b in U0 C0-retry P0 P1 P2 mc sw; do receipts+=("$root/fanout-$b"); done
PYTHONDONTWRITEBYTECODE=1 python3 -B admit-fanout.py "$layout" "${receipts[@]}"
bash precheck.sh "$layout" "$root/precheck-final"
