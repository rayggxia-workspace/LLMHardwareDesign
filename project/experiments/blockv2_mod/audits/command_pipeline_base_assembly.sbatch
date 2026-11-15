#!/bin/bash
#SBATCH --job-name=yzl-pipeline-assembly
#SBATCH --partition=c64,c96
#SBATCH --cpus-per-task=4
#SBATCH --time=00:40:00
set -euo pipefail
python=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python
export PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1
export PYTHONPATH="$PWD/compiler:$PWD/hardware"
exec 9>evidence/command-pipeline-assembly.lock
flock 9
selected="$1";seed="$2"
"$python" hardware/build_nine_control_plane.py "$selected"
"$python" hardware/build_selected_nine_assembly.py "$selected" "$seed"
/public/home/yuzelu/project-circuit/issue250-u-n32-stored-link-20261112-01/tool.sh bash tests/elaborate_selected_nine_assembly.sh
"$python" hardware/check_selected_nine_assembly.py "evidence/architecture-revision-185/selected-nine-assembly-$SLURM_JOB_ID"
