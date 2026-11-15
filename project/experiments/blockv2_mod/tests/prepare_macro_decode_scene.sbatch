#!/bin/bash
#SBATCH --job-name=yzl-decode-scene
#SBATCH --partition=debug,c64,c96
#SBATCH --cpus-per-task=2
#SBATCH --time=00:20:00
set -euo pipefail
cd /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search/blockv2-mod
export PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1
python=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python
export PYTHONPATH="$("$python" -c 'import json,os;d=json.load(open("reproducibility/environment.json"));print(os.pathsep.join([os.getcwd()+"/hardware"]+d["module_roots"]+d["extra_python_roots"]))')"
ev=evidence/architecture-revision-185
base="$ev/shared-memory-bound-packages-114908"
execution="$ev/macro-prefill-115069"
assets="$ev/macro-prefill-assets-114989/assets.json"
"$python" tests/compare_macro_committed_reference.py "$execution/receipt.json" "$ev/graph-numeric-reference-115054/receipt.json" "$ev/prefill-bit-exact-$SLURM_JOB_ID.json"
"$python" tests/compare_macro_prefill.py "$execution/receipt.json" "$ev/macro-prefill-reference-115013/receipt.json" "$assets" evidence/two-input-114228/native-recipe-graph.json "$ev/prefill-comparison-$SLURM_JOB_ID.json"
state="$ev/decode-state-inputs-$SLURM_JOB_ID"
"$python" tlm/materialize_phase_state.py "$ev/phase-state-bridge-115046.json" "$execution/committed-state.bin" "$execution/receipt.json" "$state"
"$python" tlm/prepare_macro_decode_assets.py "$base/prefill-package" "$assets" evidence/two-input-114228/native-recipe-graph.json "$execution/receipt.json" "$state/runtime-inputs.json" "$base/decode-package" evidence/cached-decode-graph-114276/decode.onnx "$ev/macro-decode-assets-$SLURM_JOB_ID" --logits-value logits
