#!/bin/bash
#SBATCH --job-name=yzl-sc153-grporacle
#SBATCH --partition=c64
#SBATCH --nodelist=node4
#SBATCH --cpus-per-task=1
#SBATCH --time=00:30:00
set -euo pipefail
ROOT=/public/home/yuzelu/project-circuit/LLMHardwareDesign/systemc-llm-issue153
cd "$ROOT"
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 SLURM_CPUS_PER_TASK=1 PYTHONDONTWRITEBYTECODE=1
sha256sum systemc-src-f6.tar.gz src-f6/project/systemc/llm/tools/diagnose_quantized_model.py sequence-gemma-f7/weights.bin sequence-gemma-f7/weights.scales sequence-gemma-f7/export_receipt.json > sequence-diagnostic-gemma-group-f12.inputs.sha256
/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python src-f6/project/systemc/llm/tools/diagnose_quantized_model.py sequence-gemma-f7 run-gemma-f4-sequence --out sequence-diagnostic-gemma-group-f12.json
