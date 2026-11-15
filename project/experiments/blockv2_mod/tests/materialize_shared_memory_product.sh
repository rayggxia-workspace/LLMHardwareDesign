#!/bin/bash
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1
python=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python
"$python" compiler/materialize_native_product.py  --plan evidence/architecture-revision-185/shared-memory-graphs-114904/prefill-plan/plan.json  --plan evidence/architecture-revision-185/shared-memory-graphs-114904/decode-plan/plan.json  --hardware hardware/blockv2-mod-shared-memory.json  --assembly-receipt evidence/architecture-revision-185/selected-nine-assembly-114900/receipt.json  --output "evidence/architecture-revision-185/shared-memory-product-$SLURM_JOB_ID"
