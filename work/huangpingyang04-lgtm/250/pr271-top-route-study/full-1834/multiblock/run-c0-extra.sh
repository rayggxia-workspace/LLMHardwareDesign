#!/usr/bin/env bash
#SBATCH --job-name=hpy-pr276-c-local
#SBATCH --partition=c64
#SBATCH --cpus-per-task=1
#SBATCH --time=00:15:00
set -euo pipefail
root=$(pwd -P)
run=$(mktemp -d "$root/lower-C0-extra.XXXXXXXX")
locked=$(sed -n 's/^run=//p' lower-C0-116532.log)
source=$(sed -n 's/^run=//p' native-C-116526.log)
native="$source/native.tsv.gz"
b=/public/home/yuzelu/PingyangHuang
more="$b/hpy-pr276-more-escape.wTRlKfO9"
prior=$(sed -n 's/^run=//p' "$more/upper/upper-edge2-d9-116336.log")
base=$(sed -n 's/^run=//p' "$more/lower-edge2-116322.log")
layout="$b/hpy-pr271-top-hsVf4b/inputs/placement.json"
printf 'run=%s\n' "$run"
cd "$run"
export TMPDIR="$run" PYTHONDONTWRITEBYTECODE=1
g++ -std=c++17 -O3 -Wall -Wextra -Wpedantic "$root/lower-block.cpp" -o lower-block
python3 -B "$root/extend-c0.py" prepare "$locked" "$run"
./lower-block input.txt extra-paths.txt 36 5 25
python3 -B "$root/extend-c0.py" merge "$locked" "$run"
python3 -B "$root/block-overlay.py" verify C0 "$base/derived-spec.json" "$layout" "$prior/routes.json" "$native" "$run"
sha256sum block-evidence.json paths.txt extra-paths.txt plan.json "$root/extend-c0.py" "$root/run-c0-extra.sh"
