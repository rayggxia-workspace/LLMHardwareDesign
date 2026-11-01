#!/bin/bash
#SBATCH --job-name=yzl-sc153-parmoracle
#SBATCH --partition=c64
#SBATCH --nodelist=node4
#SBATCH --cpus-per-task=6
#SBATCH --time=00:30:00
set -euo pipefail
ROOT=/public/home/yuzelu/project-circuit/LLMHardwareDesign/systemc-llm-issue153
cd "$ROOT";export ROOT
printf '%s
' gemma-norm falcon-norm falcon-conv falcon-state_parameters falcon-nonmatrix | xargs -n1 -P6 bash -c '
 set -euo pipefail
 export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 SLURM_CPUS_PER_TASK=1 PYTHONDONTWRITEBYTECODE=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
 TASK=$0;MODEL=${TASK%%-*};GROUP=${TASK#*-}
 if [[ "$MODEL" == gemma ]];then CP=sequence-gemma-f7;else CP=sequence-falcon-f8;fi
 export PYTHONPATH="$ROOT/src-f6/project/systemc/llm/tools"
 sha256sum continuation-r8/diagnose-parameters-f13.py "$CP/export_receipt.json" "$CP/weights.bin" "$CP/weights.scales" > "sequence-diagnostic-$TASK-f13.inputs.sha256"
 /public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python continuation-r8/diagnose-parameters-f13.py "$CP" "run-$MODEL-f4-sequence" --restore-group "$GROUP" --out "sequence-diagnostic-$TASK-f13.json" > "logs/parameter-oracle-$TASK-f13.log" 2>&1
'
