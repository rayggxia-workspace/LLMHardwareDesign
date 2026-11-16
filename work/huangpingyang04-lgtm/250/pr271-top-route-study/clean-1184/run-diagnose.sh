#!/usr/bin/env bash
#SBATCH --job-name=hpy-pr276-diagnose
#SBATCH --partition=c64,c96,debug
#SBATCH --cpus-per-task=4
#SBATCH --time=00:14:00
set -euo pipefail
root=$(pwd -P)
route=$(sed -n 's/^run=//p' "$1")
run=$(mktemp -d "$root/diagnose.XXXXXXXX")
printf 'run=%s\nrouting=%s\n' "$run" "$route"
cd "$run"
cmp "$root/precheck-final/graph.txt" "$route/graph.txt"
export TMPDIR="$run" PYTHONDONTWRITEBYTECODE=1
g++ -O3 -std=c++17 "$root/diagnose-clean.cpp" -o diagnose
workers=${SLURM_CPUS_PER_TASK:-1}
pids=()
for ((i=0;i<workers;i++)); do
    ./diagnose "$route/graph.txt" "$route/paths.txt" "$i" "$workers" > "part-$i.tsv" &
    pids+=("$!")
done
for pid in "${pids[@]}"; do wait "$pid"; done
head -1 part-0.tsv > causes.tsv
for f in part-*.tsv; do tail -n +2 "$f"; done | sort -n >> causes.tsv
python3 -B "$root/classify.py" "$root" "$route" "$run" > diagnosis.json
cat diagnosis.json
sha256sum "$route/paths.txt" causes.tsv diagnosis.json unresolved.tsv
