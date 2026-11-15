#!/bin/bash
#SBATCH --job-name=yzl-graph-oracle
#SBATCH --partition=debug,c64,c96
#SBATCH --cpus-per-task=4
#SBATCH --time=00:28:00
set -euo pipefail
cd /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search/blockv2-mod
export PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=4
python=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python
export PYTHONPATH="$("$python" -c 'import json,os;d=json.load(open("reproducibility/environment.json"));print(os.pathsep.join([os.getcwd()+"/hardware"]+d["module_roots"]+d["extra_python_roots"]))')"
"$python" tests/native_graph_numeric_reference.py evidence/architecture-revision-185/shared-memory-bound-packages-114908/prefill-package evidence/architecture-revision-185/macro-prefill-assets-114989/assets.json evidence/two-input-114228/native-operand-recipes.json evidence/two-input-114228/native-recipe-graph.json "evidence/architecture-revision-185/graph-numeric-reference-$SLURM_JOB_ID" /public/home/yuzelu/project-circuit/issue260-product-retirement-V6JR7Km4/source/project/experiments/w8a16_g/reference.py
