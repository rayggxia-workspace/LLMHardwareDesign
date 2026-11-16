#!/usr/bin/env bash
#SBATCH --job-name=hpy-pr276-fan77
#SBATCH --partition=c64,c96,debug
#SBATCH --cpus-per-task=1
#SBATCH --time=00:12:00
set -euo pipefail
root=$(pwd -P)
plan=$(sed -n 's/^run=//p' "$1")
run="$root/focus-layout"
mkdir "$run"
printf 'run=%s\n' "$run"
origin=/public/home/yuzelu/PingyangHuang/hpy-pr271-top-hsVf4b
orig="$origin/inputs/top-1184-no-u0-dma/algorithm2-input.json"
export PYTHONPATH="$origin/project/experiments/upper_router:$origin/project/experiments/block_synthesis"
export TMPDIR="$run" PYTHONDONTWRITEBYTECODE=1
python3 -B fanout-c0.py prepare "$plan" "$run"
g++ -O3 -std=c++17 lower-block.cpp -o "$run/escape"
"$run/escape" "$run/input.txt" "$run/paths.txt" 1 5 110
python3 -B fanout-c0.py verify "$plan" "$run"
python3 -B verify-top.py export "$run/derived-spec.json" "$run/graph.txt" --original "$orig" --escape "$run/lower-evidence.json"
g++ -O3 -std=c++17 access-audit.cpp -o "$run/audit"
"$run/audit" "$run/graph.txt" > "$run/access.tsv"
sha256sum "$run/paths.txt" "$run/fanout.json" "$run/graph.txt" "$run/access.tsv"
