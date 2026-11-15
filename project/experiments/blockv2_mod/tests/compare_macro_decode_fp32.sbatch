#!/bin/bash
#SBATCH --job-name=yzl-decode-quality
#SBATCH --partition=debug,c64,c96
#SBATCH --cpus-per-task=2
#SBATCH --time=00:10:00
set -euo pipefail
cd /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search/blockv2-mod
export PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1
python=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python
export PYTHONPATH="$("$python" -c 'import json,os;d=json.load(open("reproducibility/environment.json"));print(os.pathsep.join([os.getcwd()+"/hardware"]+d["module_roots"]+d["extra_python_roots"]))')"
ev=evidence/architecture-revision-185
"$python" tests/compare_macro_prefill.py "$ev/macro-decode-115084/receipt.json" "$ev/macro-decode-reference-115098/receipt.json" "$ev/macro-decode-assets-115071/assets.json" evidence/two-input-114287/native-recipe-graph.json "$ev/decode-FP32-comparison-$SLURM_JOB_ID.json"
