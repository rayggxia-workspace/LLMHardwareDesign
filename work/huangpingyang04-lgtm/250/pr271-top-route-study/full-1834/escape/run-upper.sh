#!/usr/bin/env bash
#SBATCH --job-name=hpy-pr276-upper
#SBATCH --partition=c96
#SBATCH --cpus-per-task=1
#SBATCH --time=00:24:00
set -euo pipefail
workspace=$(pwd -P)
lower=$1
threshold=$2
order=$3
run=$(mktemp -d "$workspace/upper-d$threshold.XXXXXXXX")
cd "$run"
export TMPDIR="$run" PYTHONDONTWRITEBYTECODE=1
base=/public/home/yuzelu/PingyangHuang/hpy-pr271-top-hsVf4b
original="$base/inputs/top-1834/algorithm2-input.json"
router=/public/home/yuzelu/PingyangHuang/hpy-pr276-stage2.y7AnXlp8/stage2-router.cpp
export PYTHONPATH="$base/project/experiments/upper_router:$base/project/experiments/block_synthesis"
printf 'run=%s\nlower=%s\nthreshold=%s order=%s\n' "$run" "$lower" "$threshold" "$order"
printf '%s  %s\n' 97ca5122953fe42c7230cb97d804abb820b85d6e5053b40f9f4a59047e6d7f10 "$router" | sha256sum -c
patch -s "$router" "$workspace/reserve.patch" -o stage2-reserve.cpp
g++ -std=c++17 -O3 -Wall -Wextra -Wpedantic stage2-reserve.cpp -o stage2-reserve
printf '%s\n' '1 1 420 420 2' '0 2 2' '43 42' '251 210' '21 21 64 64' '230 189 273 231' '1 2 2' '42 336' '252 336' '21 315 63 357' '231 315 273 357' > smoke.txt
./stage2-reserve smoke.txt smoke.paths short 1
test "$(awk 'NF == 3 { n++ } END { print n+0 }' smoke.paths)" = 2
spec="$lower/derived-spec.json"
overlay="$lower/lower-evidence.json"
python3 -B "$workspace/verify-escape-top.py" export "$spec" graph.txt --original "$original" --escape "$overlay"
/usr/bin/time -f 'routing_elapsed=%e seconds max_rss=%M KiB' ./stage2-reserve graph.txt paths.txt "$order" "$threshold"
python3 -B "$workspace/verify-escape-top.py" verify "$spec" paths.txt routes.json --original "$original" --escape "$overlay"
sha256sum "$spec" "$overlay" stage2-reserve.cpp graph.txt paths.txt routes.json "$workspace/verify-escape-top.py" "$workspace/run-upper.sh" "$workspace/reserve.patch"
