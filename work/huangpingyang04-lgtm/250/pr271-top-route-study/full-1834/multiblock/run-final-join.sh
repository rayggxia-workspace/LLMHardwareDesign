#!/usr/bin/env bash
#SBATCH --job-name=hpy-pr276-join-alt
#SBATCH --partition=c96
#SBATCH --cpus-per-task=1
#SBATCH --time=00:10:00
set -euo pipefail
variant=$1
switch_lower=$2
b=/public/home/yuzelu/PingyangHuang
handoff="$b/hpy-pr271-top-hsVf4b/inputs"
root=$(pwd -P)
declare -a overlays
for f in lower-U0-116531.log c0-extra-116786.log lower-dma-116546.log lower-P0-116534.log lower-P1-116535.log lower-P2-116536.log lower-mc-116537.log; do
  d=$(sed -n 's/^run=//p' "$f")
  test -f "$d/block-evidence.json"
  overlays+=("$d")
done
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$b/hpy-pr271-top-hsVf4b/project/experiments/upper_router:$b/hpy-pr271-top-hsVf4b/project/experiments/block_synthesis"
dir=$(mktemp -d "$root/combined-$variant.XXXXXXXX")
printf 'combined=%s\n' "$dir"
original="$handoff/top-1834/algorithm2-input.json"
python3 -B "$root/join-wide.py" all "$original" "$switch_lower" "$handoff/placement.json" "$dir" "${overlays[@]}"
python3 -B "$root/verify-top.py" export "$dir/derived-spec.json" "$dir/graph.txt" --original "$original" --escape "$dir/lower-evidence.json"
python3 -B "$root/audit-cuts.py" "$dir" "$handoff/placement.json" > "$dir/cuts.json"
sha256sum "$dir/derived-spec.json" "$dir/lower-evidence.json" "$dir/graph.txt" "$dir/cuts.json"
