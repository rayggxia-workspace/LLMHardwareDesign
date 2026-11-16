#!/usr/bin/env bash
#SBATCH --job-name=hpy-pr276-lower-block
#SBATCH --partition=c96
#SBATCH --cpus-per-task=1
#SBATCH --time=00:25:00
set -euo pipefail
root=$(pwd -P)
name=$1
native=$2
goal=$3
cap=$4
run=$(mktemp -d "$root/lower-$name.XXXXXXXX")
cd "$run"
export TMPDIR="$run" PYTHONDONTWRITEBYTECODE=1
base=/public/home/yuzelu/PingyangHuang
more="$base/hpy-pr276-more-escape.wTRlKfO9"
prior=$(sed -n 's/^run=//p' "$more/upper/upper-edge2-d9-116336.log")
lower=$(sed -n 's/^run=//p' "$more/lower-edge2-116322.log")
layout="$base/hpy-pr271-top-hsVf4b/inputs/placement.json"
printf 'run=%s\nblock=%s\nnative=%s\ngoal=%s side_cap=%s\n' "$run" "$name" "$native" "$goal" "$cap"
printf '%s  %s\n' 74abf93569d797f9f64e0a10528a53b08f9a9cf105dca3bf47ad7996fbcace0d "$root/lower_rules.py" | sha256sum -c
g++ -std=c++17 -O3 -Wall -Wextra -Wpedantic "$root/lower-block.cpp" -o lower-block
python3 -B "$root/block-overlay.py" prepare "$name" "$lower/derived-spec.json" "$layout" "$prior/routes.json" "$native" "$run"
/usr/bin/time -f 'lower_seconds=%e rss_kib=%M' ./lower-block input.txt paths.txt "$goal" 5 "$cap"
python3 -B "$root/block-overlay.py" verify "$name" "$lower/derived-spec.json" "$layout" "$prior/routes.json" "$native" "$run"
sha256sum block-evidence.json plan.json paths.txt "$root/lower-block.cpp" "$root/block-overlay.py" "$root/run-lower.sh"
