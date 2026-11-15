#!/bin/bash
#SBATCH --job-name=yzl-benchmark-algo1
#SBATCH --partition=c64,c96
#SBATCH --cpus-per-task=2
#SBATCH --time=02:00:00
set -euo pipefail
cd /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search/blockv2-mod
export PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
python=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python
"$python" -B tests/convert_remaining_benchmarks.py   --catalog evidence/architecture-revision-185/remaining-benchmark-source-catalog.json   --qwen-acceptance "${1:?Qwen acceptance receipt required}"   --output "evidence/architecture-revision-185/remaining-benchmark-conversion-$SLURM_JOB_ID"
