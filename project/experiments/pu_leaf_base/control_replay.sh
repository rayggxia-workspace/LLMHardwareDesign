#!/usr/bin/env bash
set -euo pipefail
root=$1
src=$root/source
case "${SLURM_ARRAY_TASK_ID:?}" in
    0) kind=3 ;;
    1) kind=-1 ;;
    *) exit 2 ;;
esac
run=$root/fixture-$SLURM_ARRAY_TASK_ID
python3 -B "$src/project/experiments/pu_leaf_base/control_replay.py" "$src" "$run"
exec bash "$run/design/run.sh" "$run" "$run/results" "$kind"
