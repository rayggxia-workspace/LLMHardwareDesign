#!/usr/bin/env bash
#SBATCH --job-name=hpy-pr276-fanout
#SBATCH --partition=c64,c96,debug
#SBATCH --cpus-per-task=1
#SBATCH --time=00:15:00
set -euo pipefail
root=$(pwd -P)
block=$1
run="$root/fanout-$block${2:-}"
mkdir "$run"
printf 'run=%s\n' "$run"
export TMPDIR="$run" PYTHONDONTWRITEBYTECODE=1
python3 -B refresh-fanout.py prepare "$block" "$run"
g++ -O3 -std=c++17 lower-block.cpp -o "$run/fanout"
"$run/fanout" "$run/input.txt" "$run/paths.txt" 260 5 110
python3 -B refresh-fanout.py verify "$block" "$run"
sha256sum "$run/fanout-verified.json" "$run/paths.txt"
