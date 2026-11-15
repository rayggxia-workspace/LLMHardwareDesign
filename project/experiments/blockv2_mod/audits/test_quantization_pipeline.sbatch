#!/bin/bash
#SBATCH --job-name=yzl-quantize-tlm
#SBATCH --partition=c64,c96
#SBATCH --cpus-per-task=4
#SBATCH --time=02:00:00
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1
python=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python
export PYTHONPATH="$PWD/hardware:$("$python" -c 'import json,os;d=json.load(open("reproducibility/environment.json"));print(os.pathsep.join(d["module_roots"]+d["extra_python_roots"]))')"
"$python" -B audits/test_quantization_pipeline.py
