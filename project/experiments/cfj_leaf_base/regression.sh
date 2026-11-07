#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "$0")/../../.." && pwd)
bundle=$(realpath "$1")
kind=$2
cd "$bundle"
case "$kind" in
    -1|1|4) ;;
    *) exit 2 ;;
esac
bash design/run.sh "$bundle" "$bundle/results/$SLURM_ARRAY_JOB_ID-$SLURM_ARRAY_TASK_ID" "$kind"
