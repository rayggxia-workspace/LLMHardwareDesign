#!/bin/bash
#SBATCH --job-name=yzl-sc153-granite-groups
#SBATCH --partition=c64
#SBATCH --nodelist=node1
#SBATCH --cpus-per-task=3
#SBATCH --time=00:15:00
set -euo pipefail
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/public/home/yuzelu/project-circuit/LLMHardwareDesign/systemc-llm-issue153/src-r20/project/systemc/llm/tools R=/public/home/yuzelu/project-circuit/LLMHardwareDesign/systemc-llm-issue153
printf '%s\n' router norm experts | xargs -n1 -P3 bash -c '
 set -euo pipefail
 OUT="$R/diagnostic-granite-$0-r27";mkdir "$OUT"
 ln -s "$R/run-granite-r23/systemc_receipt.json" "$OUT/systemc_receipt.json"
 /public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python "$R/continuation-r8/diagnose_quantized_model-r27.py" "$R/granite-r1" "$OUT" --restore-group "$0" > "$R/logs/granite-$0-r27.log" 2>&1
'
