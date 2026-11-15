#!/usr/bin/env bash
#SBATCH --job-name=hpy-pr276-lower
#SBATCH --partition=c96
#SBATCH --cpus-per-task=1
#SBATCH --time=00:24:00
set -euo pipefail
workspace=$(pwd -P)
p=$1
goal=$2
run=$(mktemp -d "$workspace/lower-p$p.XXXXXXXX")
cd "$run"
export TMPDIR="$run" PYTHONDONTWRITEBYTECODE=1
handoff=/public/home/yuzelu/PingyangHuang/hpy-pr271-top-hsVf4b/inputs
stage2=/public/home/yuzelu/PingyangHuang/hpy-pr276-stage2.y7AnXlp8
args=("$handoff" "$workspace/native-sw.tsv" "$stage2/cut-stage2.json" "$stage2/run-short.sSYgdlAJ/routes.json" "$run" "--site-pitch" "$p" "--prefer-missing")
printf 'run=%s\nsite_pitch=%s goal=%s\n' "$run" "$p" "$goal"
g++ -std=c++17 -O3 -Wall -Wextra -Wpedantic "$workspace/lower-escape.cpp" -o lower-escape
python3 -B "$workspace/escape-overlay.py" prepare "${args[@]}"
/usr/bin/time -f 'lower_elapsed=%e seconds' ./lower-escape lower-input.txt lower-paths.txt "$goal"
python3 -B "$workspace/escape-overlay.py" verify "${args[@]}"
sha256sum lower-evidence.json lower-plan.json lower-paths.txt derived-spec.json "$workspace/lower-escape.cpp" "$workspace/escape-overlay.py" "$workspace/run-lower.sh"
