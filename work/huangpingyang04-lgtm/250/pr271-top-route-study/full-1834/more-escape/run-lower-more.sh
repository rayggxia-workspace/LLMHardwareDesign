#!/usr/bin/env bash
#SBATCH --job-name=hpy-pr276-more-lower
#SBATCH --partition=c96
#SBATCH --cpus-per-task=1
#SBATCH --time=00:25:00
set -euo pipefail
workspace=$(pwd -P)
order=$1
site=$2
via=$3
goal=$4
run=$(mktemp -d "$workspace/lower-$order-p$site.XXXXXXXX")
cd "$run"
export TMPDIR="$run" PYTHONDONTWRITEBYTECODE=1
base=/public/home/yuzelu/PingyangHuang/hpy-pr271-top-hsVf4b/inputs
locked=/public/home/yuzelu/PingyangHuang/hpy-pr276-escape.EaL1oAqq/lower-p2.BLaJsN66
native="$workspace/native-sw-full.tsv"
tech="$workspace/lower-tech-full.txt"
printf 'run=%s\norder=%s site=%s via_cost=%s goal=%s\n' "$run" "$order" "$site" "$via" "$goal"
g++ -std=c++17 -O3 -Wall -Wextra -Wpedantic "$workspace/lower-four.cpp" -o lower-four
python3 -B "$workspace/extend-overlay.py" prepare "$base" "$native" "$tech" "$locked" "$run" --order "$order" --site-pitch "$site"
/usr/bin/time -f 'lower_seconds=%e max_rss_kib=%M' ./lower-four input.txt paths.txt "$goal" "$via"
python3 -B "$workspace/extend-overlay.py" verify "$base" "$native" "$tech" "$locked" "$run"
sha256sum lower-evidence.json plan.json paths.txt derived-spec.json input.txt "$workspace/lower-four.cpp" "$workspace/extend-overlay.py" "$workspace/run-lower-more.sh"
