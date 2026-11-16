#!/usr/bin/env bash
#SBATCH --job-name=hpy-pr276-entryplan
#SBATCH --partition=c64,c96,debug
#SBATCH --cpus-per-task=1
#SBATCH --time=00:12:00
set -euo pipefail
root=$(pwd -P)
prior=/public/home/yuzelu/PingyangHuang/hpy-pr276-scarce1184.fOd5vRE3
input=${1:-$root/precheck-final}
run=$(mktemp -d "$root/entry-plan.XXXXXXXX")
printf 'run=%s\nlayout=%s\n' "$run" "$input"
export TMPDIR="$run" PYTHONDONTWRITEBYTECODE=1
cd "$run"
python3 -B "$root/focus-targets.py" "$input/derived-spec.json" "$prior/diagnose.NC87PAMq/unresolved.tsv" > targets.tsv
g++ -O3 -std=c++17 -Wall -Wextra -Wno-unused-variable "$root/plan-focus.cpp" -o plan
./plan "$input/graph.txt" targets.tsv "$run"
cat v11-audit.tsv
sha256sum "$input/graph.txt" targets.tsv reservations.tsv entry.paths v11-audit.tsv
