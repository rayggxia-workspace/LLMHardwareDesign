#!/bin/bash
#SBATCH --job-name=yzl-pipeline-admit
#SBATCH --partition=c64,c96
#SBATCH --cpus-per-task=4
#SBATCH --time=00:20:00
set -euo pipefail
python=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python
export PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD/compiler:$PWD/hardware"
"$python" audits/command_pipeline_register_parents.py "$1" "$2" "$3"
"$python" hardware/check_selected_nine_assembly.py "$2"
