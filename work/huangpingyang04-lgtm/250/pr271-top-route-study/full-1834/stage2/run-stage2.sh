#!/usr/bin/env bash
#SBATCH --job-name=hpy-cugr276-s2
#SBATCH --partition=c96
#SBATCH --cpus-per-task=1
#SBATCH --time=00:30:00
set -euo pipefail

if (( $# != 2 )); then
    echo "usage: run-stage2.sh handoff-root short|long|pin-access" >&2
    exit 2
fi
workspace=$(pwd -P)
handoff=$1
order=$2
case "$order" in
    short|long|pin-access) ;;
    *) exit 2 ;;
esac
run=$(mktemp -d "$workspace/run-$order.XXXXXXXX")
cd "$run"
export TMPDIR="$run" PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$handoff/project/experiments/upper_router:$handoff/project/experiments/block_synthesis"
spec="$handoff/inputs/top-1834/algorithm2-input.json"
printf '%s\n' "run=$run" "order=$order"
g++ --version | sed -n '1p'
g++ -std=c++17 -O3 -Wall -Wextra -Wpedantic "$workspace/stage2-router.cpp" -o stage2-router
printf '%s\n' '1 1 420 420 2' '0 2 2' '43 42' '251 210' '21 21 64 64' '230 189 273 231' '1 2 2' '42 336' '252 336' '21 315 63 357' '231 315 273 357' > smoke.txt
./stage2-router smoke.txt smoke.paths short
test "$(awk 'NF == 3 { n++ } END { print n+0 }' smoke.paths)" = 2
python3 -B "$workspace/verify-stage2.py" export "$spec" graph.txt
sha256sum "$spec" "$handoff/inputs/placement.json" graph.txt "$workspace/stage2-router.cpp" "$workspace/verify-stage2.py" "$workspace/run-stage2.sh"
/usr/bin/time -f 'routing_elapsed=%e seconds max_rss=%M KiB' ./stage2-router graph.txt paths.txt "$order"
python3 -B "$workspace/verify-stage2.py" verify "$spec" paths.txt routes.json
sha256sum paths.txt routes.json
