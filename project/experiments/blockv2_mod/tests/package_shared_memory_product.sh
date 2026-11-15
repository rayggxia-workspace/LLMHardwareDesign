#!/bin/bash
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1
python=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python
export PYTHONPATH="$("$python" -c 'import json,os;d=json.load(open("reproducibility/environment.json"));print(os.pathsep.join([os.getcwd()+"/hardware"]+d["module_roots"]+d["extra_python_roots"]))')"
out="evidence/architecture-revision-185/shared-memory-bound-packages-$SLURM_JOB_ID"
mkdir -p "$out"
for stage in prefill decode; do
 "$python" compiler/package_native_plan.py  "evidence/architecture-revision-185/shared-memory-graphs-114904/$stage-plan/plan.json"  "$out/$stage-package" evidence/architecture-revision-185/shared-memory-product-114907/candidate-wiring.json
done
