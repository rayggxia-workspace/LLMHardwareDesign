#!/bin/bash
#SBATCH --job-name=yzl-macro-fast
#SBATCH --partition=c64,c96
#SBATCH --cpus-per-task=4
#SBATCH --time=03:00:00
set -euo pipefail
cd /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search/blockv2-mod
export PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=4
export LD_LIBRARY_PATH=/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-234-systemc-benchmark/python-compat-001
python=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python
export PYTHONPATH="$("$python" -c 'import json,os;d=json.load(open("reproducibility/environment.json"));print(os.pathsep.join([os.getcwd()+"/hardware"]+d["module_roots"]+d["extra_python_roots"]))')"
mkdir -p tmp
/public/home/yuzelu/project-circuit/issue250-u-n32-stored-link-20261112-01/tool.sh env PYTHONPATH="$PYTHONPATH" LD_LIBRARY_PATH="$LD_LIBRARY_PATH" PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 "$python" tlm/run_macro_package.py evidence/architecture-revision-185/shared-memory-bound-packages-114908/prefill-package "$1/assets.json" /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search/blockv2-mod/evidence/architecture-revision-185/dram-batch-115020.so /public/home/yuzelu/project-circuit/issue234-algo1-ffn-chain-20261112-01/DDR4-single-channel.ini /public/home/yuzelu/project-circuit/issue260-product-retirement-V6JR7Km4/source/project/experiments/w8a16_g/reference.py "evidence/architecture-revision-185/macro-prefill-$SLURM_JOB_ID" --core-ps 3333 --result logits --batch-dram
