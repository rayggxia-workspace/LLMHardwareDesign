#!/bin/bash
#SBATCH --job-name=yzl-clean-reference
#SBATCH --partition=c64,c96
#SBATCH --cpus-per-task=4
#SBATCH --time=02:00:00
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1
python=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python
export PYTHONPATH="$PWD/hardware:$("$python" -c 'import json,os;d=json.load(open("reproducibility/environment.json"));print(os.pathsep.join(d["module_roots"]+d["extra_python_roots"]))')"
"$python" tests/compare_macro_exported_reference.py evidence/range-integration/request-115220/prefill-execution/receipt.json evidence/architecture-revision-185/graph-numeric-reference-115054/receipt.json evidence/architecture-revision-185/shared-memory-bound-packages-114908/prefill-package evidence/range-integration/package-115219/prefill-package evidence/range-integration/115217/prefill/plan.json evidence/range-integration/request-115220/prefill-equivalent-plan-bit-exact.json --all-produced
