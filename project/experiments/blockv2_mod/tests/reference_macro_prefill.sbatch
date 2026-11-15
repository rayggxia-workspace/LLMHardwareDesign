#!/bin/bash
#SBATCH --job-name=yzl-macro-ref
#SBATCH --partition=debug,c64,c96
#SBATCH --cpus-per-task=4
#SBATCH --time=00:20:00
set -euo pipefail
cd /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search/blockv2-mod
export PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1
python=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python
export PYTHONPATH="$("$python" -c 'import json,os;d=json.load(open("reproducibility/environment.json"));print(os.pathsep.join([os.getcwd()+"/hardware"]+d["module_roots"]+d["extra_python_roots"]))')"
"$python" tests/reference_macro_prefill.py
