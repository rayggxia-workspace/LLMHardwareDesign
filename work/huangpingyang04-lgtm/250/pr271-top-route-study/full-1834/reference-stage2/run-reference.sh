#!/usr/bin/env bash
#SBATCH --job-name=hpy-pr276-cugr-ref
#SBATCH --partition=c96
#SBATCH --cpus-per-task=1
#SBATCH --time=00:35:00
set -euo pipefail

workspace=$(pwd -P)
variant=$1
lower=$2
base=/public/home/yuzelu/PingyangHuang/hpy-pr271-top-hsVf4b
orig="$base/inputs/top-1834/algorithm2-input.json"
before=/public/home/yuzelu/PingyangHuang/hpy-pr276-stage2.y7AnXlp8
overlay_check=/public/home/yuzelu/PingyangHuang/hpy-pr276-escape.EaL1oAqq/upper-v2
export PYTHONPATH="$base/project/experiments/upper_router:$base/project/experiments/block_synthesis"
run=$(mktemp -d "$workspace/run-$variant.XXXXXXXX")
cd "$run"
export TMPDIR="$run" PYTHONDONTWRITEBYTECODE=1
printf 'run=%s\nvariant=%s\nlower=%s\n' "$run" "$variant" "$lower"
printf '%s  %s\n' \
    9c28df8dccacb06ce71a65ffc1141755a1a443e1f732a7a21f3d45abc0e80c61 \
    "$workspace/cugr-maze-route.inc" | sha256sum -c
g++ -std=c++17 -O3 -Wall -Wextra -Wno-unused-variable "$workspace/reference-maze.cpp" -o reference-maze
printf '%s\n' '1 1 420 420 2' '0 3 3' '43 42' '251 210' '336 42' '21 21 64 64' '230 189 273 231' '315 21 357 63' '1 2 2' '42 336' '252 336' '21 315 63 357' '231 315 273 357' > smoke.graph
./reference-maze smoke.graph smoke.paths
test "$(awk 'NF == 3 { n++ } END { print n+0 }' smoke.paths)" = 2

if [[ "$lower" == original ]]; then
    spec="$orig"
    sha256sum "$before/verify-stage2.py"
    python3 -B "$before/verify-stage2.py" export "$spec" graph.txt
else
    spec="$lower/derived-spec.json"
    escape="$lower/lower-evidence.json"
    sha256sum "$overlay_check/verify-escape-top.py" "$escape"
    python3 -B "$overlay_check/verify-escape-top.py" export "$spec" graph.txt --original "$orig" --escape "$escape"
fi
sha256sum "$spec" graph.txt "$workspace/reference-maze.cpp" "$workspace/cugr-maze-route.inc" "$workspace/run-reference.sh"
printf 'search=upstream-MazeRoute-route ordered=handoff pin_windows=integrated legacy_reservations=off\n'
/usr/bin/time -f 'routing_seconds=%e rss_kib=%M' ./reference-maze graph.txt paths.txt
if [[ "$lower" == original ]]; then
    python3 -B "$before/verify-stage2.py" verify "$spec" paths.txt routes.json
else
    python3 -B "$overlay_check/verify-escape-top.py" verify "$spec" paths.txt routes.json --original "$orig" --escape "$escape"
fi
sha256sum paths.txt routes.json
