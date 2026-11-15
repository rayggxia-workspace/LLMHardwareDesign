#!/usr/bin/env bash
#SBATCH --job-name=hpy-pr276-join
#SBATCH --partition=c96
#SBATCH --cpus-per-task=1
#SBATCH --time=00:10:00
set -euo pipefail
dma_job=$1
b=/public/home/yuzelu/PingyangHuang
more="$b/hpy-pr276-more-escape.wTRlKfO9"
handoff="$b/hpy-pr271-top-hsVf4b/inputs"
root=$(pwd -P)
prior=$(sed -n 's/^run=//p' "$more/lower-edge2-116322.log")
declare -a overlays
for f in lower-U0-116531.log lower-C0-116532.log "lower-dma-$dma_job.log" lower-P0-116534.log lower-P1-116535.log lower-P2-116536.log lower-mc-116537.log; do
  d=$(sed -n 's/^run=//p' "$f")
  test -f "$d/block-evidence.json"
  overlays+=("$d")
done
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$b/hpy-pr271-top-hsVf4b/project/experiments/upper_router:$b/hpy-pr271-top-hsVf4b/project/experiments/block_synthesis"
for mode in all focused; do
  dir=$(mktemp -d "$root/combined-$mode.XXXXXXXX")
  printf 'combined_%s=%s\n' "$mode" "$dir"
  original="$handoff/top-1834/algorithm2-input.json"
  python3 -B "$root/join-overlays.py" "$mode" "$original" "$prior" "$handoff/placement.json" "$dir" "${overlays[@]}"
  python3 -B "$root/verify-top.py" export "$dir/derived-spec.json" "$dir/graph.txt" --original "$original" --escape "$dir/lower-evidence.json"
  sha256sum "$dir/derived-spec.json" "$dir/lower-evidence.json" "$dir/graph.txt"
done
