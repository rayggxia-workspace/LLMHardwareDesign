#!/usr/bin/env bash
set -euo pipefail
root=$(pwd -P)
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$root/project/experiments/upper_router:$root/project/experiments/block_synthesis"
variant=$1
mode=$2
out="$root/$variant/$mode"
case "$mode" in
  study) args=(--budget 2600 --repair-budget 8500 --max-targets 12) ;;
  weighted) args=(--weight 4 --budget 3000 --repair-budget 4500 --max-targets 12) ;;
  reserve) args=(--weight 6 --reserve-access --budget 4200 --repair-budget 5000 --max-targets 18) ;;
  jumps) args=(--weight 6 --reserve-access --jumps --budget 1750 --repair-budget 2400 --max-targets 24) ;;
  near)
    mkdir -p "$root/$variant/fast"
    out="$root/$variant/fast/results"
    args=(--weight 3 --reserve-access --jumps --budget 3800 --repair-budget 6000 --max-targets 20)
    ;;
  direct)
    status=0
    python3 -B "$root/project/experiments/upper_router/run.py" "inputs/$variant/algorithm2-input.json" "$out.json" --rounds 3 --max-expansions 16000 --handoff "inputs/$variant" || status=$?
    [[ $status == 0 || $status == 2 ]] && test -s "$out.json"
    exit
    ;;
  full-repair) args=(--direct "$root/$variant/direct.json" --weight 4 --repair-budget 4500 --max-targets 12) ;;
  *) exit 2 ;;
esac
python3 -B "$root/analysis/study.py" "inputs/$variant" cells.lib "$out" "${args[@]}"
