#!/bin/bash
#SBATCH --job-name=yzl-sc153-cd-full
#SBATCH --partition=c64
#SBATCH --cpus-per-task=8
#SBATCH --time=04:00:00
set -euo pipefail
: "${CD_EXPERIMENT_ROOT:?}"
cd "$CD_EXPERIMENT_ROOT"
awk '/MemAvailable/ {print; if ($2 < 120*1024*1024) exit 1}' /proc/meminfo
tar -xzf source.tar.gz
sha256sum -c upload.sha256
python3 source/project/systemc/llm_cd/run.py --control-root control-source \
 --systemc-prefix "$(dirname "$CD_EXPERIMENT_ROOT")/install" \
 --out "$CD_EXPERIMENT_ROOT/experiment" --save-evidence "$CD_EXPERIMENT_ROOT/build-evidence" --no-sanitize
python3 source/project/systemc/llm_cd/remote_suite.py
