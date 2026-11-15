#!/bin/bash
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK OPENBLAS_NUM_THREADS=$SLURM_CPUS_PER_TASK
export PYTHONPATH=/public/home/yuzelu/project-circuit/LLMHardwareDesign/operator-graphs-20261026/deps
/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python -u -B frontend/export_cached_decode.py \
 /public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/models/qwen25-3b-5defd279 \
 "evidence/cached-decode-graph-$SLURM_JOB_ID" "$@"
