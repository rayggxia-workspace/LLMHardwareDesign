#!/usr/bin/env bash
#SBATCH --job-name=hpy-pr276-localab
#SBATCH --partition=c64,c96,debug
#SBATCH --nodes=1
#SBATCH --ntasks=2
#SBATCH --cpus-per-task=1
#SBATCH --time=00:28:00
set -euo pipefail
root=$(pwd -P)
export TMPDIR="$root" PYTHONDONTWRITEBYTECODE=1
base="$root/../hpy-pr276-clean1184.kFNrCO4l"
origin="$root/../hpy-pr271-top-hsVf4b"
export PYTHONPATH="$origin/project/experiments/upper_router:$origin/project/experiments/block_synthesis"
input="$root/input"
mkdir "$input"
cp "$base/precheck-final/"{access.tsv,derived-spec.json,lower-evidence.json} "$input/"
python3 -B "$root/verify-top.py" export "$input/derived-spec.json" "$input/graph.txt" \
    --original "$origin/inputs/top-1184-no-u0-dma/algorithm2-input.json" --escape "$input/lower-evidence.json"
cmp "$input/graph.txt" "$base/precheck-final/graph.txt"
printf '%s  %s\n' 6cdb63981f539c8f02b35bbba592931be2eec9e3b0b67299828253b05415a744 "$origin/inputs/placement.json" | sha256sum -c
printf '%s  %s\n' 9c28df8dccacb06ce71a65ffc1141755a1a443e1f732a7a21f3d45abc0e80c61 "$root/cugr-maze-route.inc" | sha256sum -c
python3 -B build-candidates.py "$input/graph.txt" "$input/derived-spec.json" "$base/diagnose.qyWeD9Tf/unresolved.tsv" \
    "$root/local-edges.tsv" "$root/candidate-regions.json"
sha256sum "$input/"{graph.txt,access.tsv,derived-spec.json,lower-evidence.json} local-edges.tsv candidate-regions.json \
    local-engine.cpp local-tracks.inc route-ab.cpp "$base/diagnose.qyWeD9Tf/unresolved.tsv"
g++ -std=c++17 -O3 -Wall -Wextra -Wno-unused-variable route-ab.cpp -o maze
srun -N1 -n1 -c1 --exclusive --cpu-bind=cores bash "$root/run-arm.sh" "$root" A &
job_a=$!
srun -N1 -n1 -c1 --exclusive --cpu-bind=cores bash "$root/run-arm.sh" "$root" B &
job_b=$!
failure=0
wait "$job_a" || failure=1
wait "$job_b" || failure=1
exit "$failure"
