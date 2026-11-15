#!/bin/bash
#SBATCH --job-name=yzl-macro-assets
#SBATCH --partition=debug,c64,c96
#SBATCH --cpus-per-task=4
#SBATCH --time=00:28:00
set -euo pipefail
cd /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search/blockv2-mod
export PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=4
python=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python
export PYTHONPATH="$("$python" -c 'import json,os;d=json.load(open("reproducibility/environment.json"));print(os.pathsep.join([os.getcwd()+"/hardware"]+d["module_roots"]+d["extra_python_roots"]))')"
"$python" tlm/materialize_macro_assets.py evidence/architecture-revision-185/shared-memory-bound-packages-114908/prefill-package evidence/two-input-114228/native-recipe-graph.json ../full-qwen25-3b-v1/complete/full.onnx ../full-qwen25-3b-v1/complete/receipt.json "evidence/architecture-revision-185/macro-prefill-assets-$SLURM_JOB_ID" --tokens 1 2
