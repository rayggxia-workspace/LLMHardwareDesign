#!/bin/bash
#SBATCH --job-name=yzl-model-gap
#SBATCH --partition=c64,c96
#SBATCH --cpus-per-task=2
#SBATCH --time=00:20:00
set -euo pipefail
cd /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search/blockv2-mod
export PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1
python=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python
export PYTHONPATH="$("$python" -c 'import json,os;d=json.load(open("reproducibility/environment.json"));print(os.pathsep.join([os.getcwd()+"/hardware"]+d["module_roots"]+d["extra_python_roots"]))')"
"$python" audits/model_path_gaps.py "evidence/model-path-gaps-$SLURM_JOB_ID"
