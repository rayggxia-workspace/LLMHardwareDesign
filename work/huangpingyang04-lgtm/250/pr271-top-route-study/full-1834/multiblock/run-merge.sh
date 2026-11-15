#!/usr/bin/env bash
#SBATCH --job-name=hpy-pr276-merge
#SBATCH --partition=c64,c96
#SBATCH --cpus-per-task=1
#SBATCH --time=00:22:00
set -euo pipefail
root=$(pwd -P)
base_log=${1:-top-all-warm-116553.log}
candidate_log=${2:-top-all-scratch-116554.log}
run=$(mktemp -d "$root/top-merged.XXXXXXXX")
origin=/public/home/yuzelu/PingyangHuang/hpy-pr271-top-hsVf4b
warm=$(sed -n 's/^run=//p' "$base_log")
cold=$(sed -n 's/^run=//p' "$candidate_log")
variant=$(sed -n 's/^variant=//p' "$base_log")
test "$variant" = "$(sed -n 's/^variant=//p' "$candidate_log")"
spec_dir="$root/$variant"
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$origin/project/experiments/upper_router:$origin/project/experiments/block_synthesis"
printf 'run=%s\nvariant=%s\nwarm=%s\ncold=%s\n' "$run" "$(basename "$spec_dir")" "$warm" "$cold"
cd "$run"
export TMPDIR="$run"
python3 -B -c 'import json,sys; data=[json.load(open(p)) for p in sys.argv[1:]]; assert all(q["geometry_check"]["passed"] for q in data) and data[0]["context"]==data[1]["context"]' "$warm/routes.json" "$cold/routes.json"
g++ -std=c++17 -O3 -Wall -Wextra -Wno-unused-variable "$root/merge-maze.cpp" -o merge-maze
sha256sum "$warm/paths.txt" "$cold/paths.txt" "$spec_dir/graph.txt" "$root/merge-maze.cpp" "$root/run-merge.sh"
/usr/bin/time -f 'routing_seconds=%e rss_kib=%M' ./merge-maze "$spec_dir/graph.txt" "$warm/paths.txt" "$cold/paths.txt" paths.txt
python3 -B "$root/verify-top.py" verify "$spec_dir/derived-spec.json" paths.txt routes.json --original "$origin/inputs/top-1834/algorithm2-input.json" --escape "$spec_dir/lower-evidence.json"
sha256sum paths.txt paths.txt.initial routes.json
