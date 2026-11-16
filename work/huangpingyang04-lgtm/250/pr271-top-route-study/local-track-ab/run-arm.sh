#!/usr/bin/env bash
set -euo pipefail
root=$1
arm=$2
cd "$root"
input="$root/input"
run="$root/$arm"
mkdir "$run"
exec > "$run/route.log" 2>&1
printf 'arm=%s\nslurm_job=%s\nslurm_step=%s\nnode=%s\n' "$arm" "$SLURM_JOB_ID" "$SLURM_STEP_ID" "$(hostname)"
case "$arm" in
  A) manifest=- ;;
  B) manifest="$root/local-edges.tsv" ;;
  *) exit 2 ;;
esac
origin=/public/home/yuzelu/PingyangHuang/hpy-pr271-top-hsVf4b
orig="$origin/inputs/top-1184-no-u0-dma/algorithm2-input.json"
export PYTHONPATH="$origin/project/experiments/upper_router:$origin/project/experiments/block_synthesis"
export TMPDIR="$run" PYTHONDONTWRITEBYTECODE=1
cd "$run"
test ! -e paths.txt
printf 'params=12 45 3200 1700 300\n'
/usr/bin/time -o timing.txt -f 'elapsed=%e user_cpu=%U sys_cpu=%S max_rss_kib=%M' \
  "$root/maze" "$input/graph.txt" "$input/access.tsv" paths.txt 12 45 3200 1700 300 "$manifest"
cat timing.txt
python3 -B "$root/verify-ab.py" "$root/verify-top.py" "$manifest" verify "$input/derived-spec.json" \
    paths.txt routes.json --original "$orig" --escape "$input/lower-evidence.json"
sha256sum "$input/graph.txt" "$input/derived-spec.json" "$input/lower-evidence.json" paths.txt routes.json
