#!/usr/bin/env bash
#SBATCH --job-name=hpy-cugr276
#SBATCH --partition=c96
#SBATCH --cpus-per-task=1
#SBATCH --time=00:30:00
set -euo pipefail

if (( $# != 5 )); then
    echo "usage: run-dijkstra.sh handoff-root guide-padding states-per-search passes repair-passes" >&2
    exit 2
fi
workspace=$(pwd -P)
handoff=$1
padding=$2
budget=$3
passes=$4
repair_passes=$5
[[ "$padding" =~ ^[0-9]+$ ]]
run=$(mktemp -d "$workspace/run-p$padding.XXXXXXXX")
cd "$run"
export TMPDIR="$run" PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$handoff/project/experiments/upper_router:$handoff/project/experiments/block_synthesis"
spec="$handoff/inputs/top-1834/algorithm2-input.json"
printf '%s\n' "run=$run" "padding=$padding budget=$budget passes=$passes repair_passes=$repair_passes"
g++ --version | sed -n '1p'
g++ -std=c++17 -O3 -Wall -Wextra -Wpedantic "$workspace/dijkstra-maze.cpp" -o router
python3 -B "$workspace/verify.py" export "$spec" graph.txt
sha256sum "$spec" "$handoff/inputs/placement.json" graph.txt "$workspace/dijkstra-maze.cpp" "$workspace/verify.py" "$workspace/run-dijkstra.sh"
printf '%s\n' '1 1 420 420 2' '0 2 2' '42 42' '252 210' '21 21 63 63' '231 189 273 231' '1 2 2' '42 336' '252 336' '21 315 63 357' '231 315 273 357' > smoke.txt
./router smoke.txt smoke.paths 1 10000 1 1
test "$(awk 'NF == 3 { n++ } END { print n+0 }' smoke.paths)" = 2
/usr/bin/time -f 'routing_elapsed=%e seconds max_rss=%M KiB' ./router graph.txt paths.txt "$padding" "$budget" "$passes" "$repair_passes"
python3 -B "$workspace/verify.py" verify "$spec" paths.txt routes.json
sha256sum paths.txt routes.json
