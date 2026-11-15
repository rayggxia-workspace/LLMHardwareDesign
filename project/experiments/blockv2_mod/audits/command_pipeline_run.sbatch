#!/bin/bash
#SBATCH --job-name=yzl-command-decode512
#SBATCH --partition=c64,c96
#SBATCH --cpus-per-task=4
#SBATCH --time=08:00:00
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1
export LD_LIBRARY_PATH=/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-234-systemc-benchmark/python-compat-001
python=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python
export PYTHONPATH="$PWD/hardware:$("$python" -c 'import json,os;d=json.load(open("reproducibility/environment.json"));print(os.pathsep.join(d["module_roots"]+d["extra_python_roots"]))')"
packages="$1";plans="$2";out="$3"
mkdir -p "$out"
ev=evidence/architecture-revision-185
static_package="$ev/shared-memory-bound-packages-114908/decode-package"
static_assets="$ev/macro-decode-assets-115071/assets.json"
g=/public/home/yuzelu/project-circuit/issue260-product-retirement-V6JR7Km4/source/project/experiments/w8a16_g/reference.py
for h in 512 513; do
 extra=()
 if [[ "$h" == 513 ]]; then
  extra=(--previous-package "$packages/512-package" --previous-assets "$out/512-assets/assets.json" --previous-execution "$out/512-execution/receipt.json")
 fi
 "$python" audits/command_pipeline_assets.py "$packages/$h-package" "$out/$h-assets" --static-package "$static_package" --static-assets "$static_assets" "${extra[@]}"
 /public/home/yuzelu/project-circuit/issue250-u-n32-stored-link-20261112-01/tool.sh env PYTHONPATH="$PYTHONPATH" LD_LIBRARY_PATH="$LD_LIBRARY_PATH" PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 "$python" tlm/run_macro_package.py "$packages/$h-package" "$out/$h-assets/assets.json" "$ev/dram-batch-115020.so" /public/home/yuzelu/project-circuit/issue234-algo1-ffn-chain-20261112-01/DDR4-single-channel.ini "$g" "$out/$h-execution" --core-ps 3333 --result logits --batch-dram
 graph="evidence/joint-frontier/decode512-standard/graph-$h"
 "$python" tests/native_graph_numeric_reference.py "$packages/$h-package" "$out/$h-assets/assets.json" "$graph/native-operand-recipes.json" "$graph/native-recipe-graph.json" "$out/$h-reference" "$g"
 "$python" tests/compare_macro_exported_reference.py "$out/$h-execution/receipt.json" "$out/$h-reference/receipt.json" "$packages/$h-package" "$packages/$h-package" "$plans/$h/plan.json" "$out/$h-bit-exact.json"
done
"$python" audits/command_pipeline_accept.py "$out"
