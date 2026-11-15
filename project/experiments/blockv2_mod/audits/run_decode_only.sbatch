#!/bin/bash
#SBATCH --job-name=yzl-decode-only
#SBATCH --partition=c64,c96
#SBATCH --cpus-per-task=4
#SBATCH --time=02:00:00
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1
export LD_LIBRARY_PATH=/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-234-systemc-benchmark/python-compat-001
python=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python
export PYTHONPATH="$PWD/hardware:$("$python" -c 'import json,os;d=json.load(open("reproducibility/environment.json"));print(os.pathsep.join(d["module_roots"]+d["extra_python_roots"]))')"
package="$1";plan="$2";out="evidence/joint-frontier/decode-$SLURM_JOB_ID";mkdir -p "$out"
ev=evidence/architecture-revision-185
"$python" audits/rebind_range_assets.py "$ev/shared-memory-bound-packages-114908/decode-package" "$package" "$ev/macro-decode-assets-115071/assets.json" "$out/assets"
/public/home/yuzelu/project-circuit/issue250-u-n32-stored-link-20261112-01/tool.sh env PYTHONPATH="$PYTHONPATH" LD_LIBRARY_PATH="$LD_LIBRARY_PATH" PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 "$python" tlm/run_macro_package.py "$package" "$out/assets/assets.json" "$ev/dram-batch-115020.so" /public/home/yuzelu/project-circuit/issue234-algo1-ffn-chain-20261112-01/DDR4-single-channel.ini /public/home/yuzelu/project-circuit/issue260-product-retirement-V6JR7Km4/source/project/experiments/w8a16_g/reference.py "$out/execution" --core-ps 3333 --result logits --batch-dram
"$python" tests/compare_macro_exported_reference.py "$out/execution/receipt.json" "$ev/graph-numeric-reference-115085/receipt.json" "$ev/shared-memory-bound-packages-114908/decode-package" "$package" "$plan" "$out/bit-exact.json"
