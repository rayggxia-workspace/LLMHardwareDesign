#!/bin/bash
#SBATCH --job-name=yzl-range-request
#SBATCH --partition=c64,c96
#SBATCH --cpus-per-task=4
#SBATCH --time=04:00:00
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1
export LD_LIBRARY_PATH=/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-234-systemc-benchmark/python-compat-001
python=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python
export PYTHONPATH="$PWD/hardware:$("$python" -c 'import json,os;d=json.load(open("reproducibility/environment.json"));print(os.pathsep.join(d["module_roots"]+d["extra_python_roots"]))')"
base="$1";plans="$2";out="evidence/range-integration/request-$SLURM_JOB_ID";mkdir -p "$out"
ev=evidence/architecture-revision-185
"$python" audits/rebind_range_assets.py "$ev/shared-memory-bound-packages-114908/prefill-package" "$base/prefill-package" "$ev/macro-prefill-assets-114989/assets.json" "$out/prefill-assets"
run_phase() {
 /public/home/yuzelu/project-circuit/issue250-u-n32-stored-link-20261112-01/tool.sh env PYTHONPATH="$PYTHONPATH" LD_LIBRARY_PATH="$LD_LIBRARY_PATH" PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 "$python" tlm/run_macro_package.py "$base/$1-package" "$out/$1-assets/assets.json" "$ev/dram-batch-115020.so" /public/home/yuzelu/project-circuit/issue234-algo1-ffn-chain-20261112-01/DDR4-single-channel.ini /public/home/yuzelu/project-circuit/issue260-product-retirement-V6JR7Km4/source/project/experiments/w8a16_g/reference.py "$out/$1-execution" --core-ps 3333 --result logits --batch-dram
}
run_phase prefill
"$python" tests/compare_macro_exported_reference.py "$out/prefill-execution/receipt.json" "$ev/graph-numeric-reference-115054/receipt.json" "$ev/shared-memory-bound-packages-114908/prefill-package" "$base/prefill-package" "$plans/prefill/plan.json" "$out/prefill-bit-exact.json" --all-produced
"$python" compiler/build_phase_state_bridge.py "$base/prefill-package" "$base/decode-package" evidence/two-input-114228/native-recipe-graph.json evidence/two-input-114228/native-value-layout.json evidence/two-input-114287/native-recipe-graph.json "$out/bridge.json"
"$python" tlm/materialize_phase_state.py "$out/bridge.json" "$out/prefill-execution/committed-state.bin" "$out/prefill-execution/receipt.json" "$out/state-inputs"
"$python" tlm/prepare_macro_decode_assets.py "$base/prefill-package" "$out/prefill-assets/assets.json" evidence/two-input-114228/native-recipe-graph.json "$out/prefill-execution/receipt.json" "$out/state-inputs/runtime-inputs.json" "$base/decode-package" evidence/cached-decode-graph-114276/decode.onnx "$out/decode-assets" --logits-value logits
run_phase decode
"$python" tests/compare_macro_exported_reference.py "$out/decode-execution/receipt.json" "$ev/graph-numeric-reference-115085/receipt.json" "$ev/shared-memory-bound-packages-114908/decode-package" "$base/decode-package" "$plans/decode/plan.json" "$out/decode-bit-exact.json" --all-produced
