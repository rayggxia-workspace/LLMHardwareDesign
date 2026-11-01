#!/bin/bash
set -euo pipefail
export OMP_NUM_THREADS=96 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
scontrol show job -o "$SLURM_JOB_ID" > allocation.txt
date -u +%FT%TZ > started.txt
trap 'rc=$?; echo $rc > exit-code.txt; date -u +%FT%TZ > finished.txt' EXIT
bash /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261101-894/src/project/experiments/block_v1/worker.sh /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261101-894/src native-node-queue
