#!/bin/bash
set -euo pipefail
root="$PWD"
out="$root/evidence/architecture-revision-185/shared-memory-graphs-$SLURM_JOB_ID"
mkdir -p "$out"
python=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python
export PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1
export PYTHONPATH="$("$python" -c 'import json,os;d=json.load(open("reproducibility/environment.json"));print(os.pathsep.join([os.getcwd()+"/hardware"]+d["module_roots"]+d["extra_python_roots"]))')"
for stage in prefill decode; do
 if [ "$stage" = prefill ]; then graph=evidence/two-input-114228; else graph=evidence/two-input-114287; fi
 "$python" compiler/run_macro_graph_frontend.py --graph-directory "$graph" --hardware hardware/blockv2-mod-shared-memory.json --services hardware/service-controller-contracts.json --output "$out/$stage-candidates" >"$out/$stage-candidates.log"
 "$python" compiler/run_macro_selection.py --graph-directory "$graph" --candidate-directory "$out/$stage-candidates" --hardware hardware/blockv2-mod-shared-memory.json --services hardware/service-controller-contracts.json --output "$out/$stage-plan" >"$out/$stage-selection.log"
 "$python" compiler/package_native_plan.py "$out/$stage-plan/plan.json" "$out/$stage-package" >"$out/$stage-package.log"
done
