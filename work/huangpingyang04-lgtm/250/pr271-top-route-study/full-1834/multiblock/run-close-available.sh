#!/usr/bin/env bash
#SBATCH --job-name=hpy-pr276-close
#SBATCH --partition=c64,c96
#SBATCH --cpus-per-task=1
#SBATCH --time=00:07:00
set -euo pipefail
root=$(pwd -P)
top_log=$1
diag_log=$2
top=$(sed -n 's/^run=//p' "$top_log")
diagnosed=$(sed -n 's/^diagnose_run=//p' "$diag_log")
variant=$(sed -n 's/^variant=//p' "$top_log")
spec="$root/$variant"
run=$(mktemp -d "$root/top-close.XXXXXXXX")
origin=/public/home/yuzelu/PingyangHuang/hpy-pr271-top-hsVf4b
export PYTHONDONTWRITEBYTECODE=1 TMPDIR="$run"
export PYTHONPATH="$origin/project/experiments/upper_router:$origin/project/experiments/block_synthesis"
cd "$run"
printf 'run=%s\nvariant=%s\n' "$run" "$variant"
sha=$(sha256sum "$top/paths.txt" | cut -d ' ' -f 1)
grep -F "$sha  $top/paths.txt" "$root/$diag_log"
awk -F '\t' '$2 == "available_on_frozen_board" {print $1}' "$diagnosed/unresolved.tsv" > targets.txt
g++ -std=c++17 -O3 -Wall -Wextra -Wno-unused-variable "$root/close-available.cpp" -o close-available
./close-available "$spec/graph.txt" "$top/paths.txt" targets.txt paths.txt
python3 -B "$root/verify-top.py" verify "$spec/derived-spec.json" paths.txt routes.json --original "$origin/inputs/top-1834/algorithm2-input.json" --escape "$spec/lower-evidence.json"
sha256sum "$root/close-available.cpp" paths.txt paths.txt.initial routes.json
