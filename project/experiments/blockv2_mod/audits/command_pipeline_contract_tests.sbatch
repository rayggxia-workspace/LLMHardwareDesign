#!/bin/bash
#SBATCH --job-name=yzl-contract-negative
#SBATCH --partition=c64,c96
#SBATCH --cpus-per-task=4
#SBATCH --time=02:00:00
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1
python=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python
export PYTHONPATH="$PWD/hardware:$("$python" -c 'import json,os;d=json.load(open("reproducibility/environment.json"));print(os.pathsep.join(d["module_roots"]+d["extra_python_roots"]))')"
"$python" -B tests/command_pipeline_admission_tests.py
"$python" -c 'import ast;from pathlib import Path;paths=[*Path("audits").glob("command_pipeline_*.py"),*Path("tests").glob("command_pipeline_*.py"),Path("compiler/command_pipeline_contract.py"),Path("hardware/build_shared_memory_inventory.py"),Path("hardware/check_selected_nine_assembly.py"),Path("tlm/macro_provider_registry.py")];[ast.parse(p.read_text(),str(p)) for p in paths];print("parsed",len(paths),"pipeline sources")'
