#!/usr/bin/env bash
#SBATCH --job-name=hpy-pr276-sw-wide
#SBATCH --partition=c96
#SBATCH --cpus-per-task=1
#SBATCH --time=00:12:00
set -euo pipefail
root=$(pwd -P)
run=$(mktemp -d "$root/switch-wide.XXXXXXXX")
cd "$run"
export TMPDIR="$run" PYTHONDONTWRITEBYTECODE=1
p=/public/home/yuzelu/PingyangHuang
sw="$p/hpy-pr276-more-escape.wTRlKfO9"
locked="$p/hpy-pr276-escape.EaL1oAqq/lower-p2.BLaJsN66"
base="$p/hpy-pr271-top-hsVf4b/inputs"
printf 'run=%s\n' "$run"
g++ -std=c++17 -O3 -Wall -Wextra -Wpedantic "$root/lower-block.cpp" -o lower-four
python3 -B "$root/switch-wide.py" prepare "$base" "$sw/native-sw-full.tsv" "$sw/lower-tech-full.txt" "$locked" "$run" --order edge --site-pitch 3
/usr/bin/time -f 'lower_seconds=%e' ./lower-four input.txt paths.txt 589 5 200
python3 -B "$root/switch-wide.py" verify "$base" "$sw/native-sw-full.tsv" "$sw/lower-tech-full.txt" "$locked" "$run"
sha256sum lower-evidence.json plan.json paths.txt derived-spec.json "$root/switch-wide.py" "$root/lower-block.cpp"
