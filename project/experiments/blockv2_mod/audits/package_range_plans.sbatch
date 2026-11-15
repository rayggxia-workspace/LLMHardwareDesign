#!/bin/bash
#SBATCH --job-name=yzl-range-package
#SBATCH --partition=c64,c96
#SBATCH --cpus-per-task=4
#SBATCH --time=00:30:00
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1
python=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python
export PYTHONPATH="$PWD/hardware:$("$python" -c 'import json,os;d=json.load(open("reproducibility/environment.json"));print(os.pathsep.join(d["module_roots"]+d["extra_python_roots"]))')"
plans="$1";out="evidence/range-integration/package-$SLURM_JOB_ID"
"$python" audits/package_range_plans.py "$plans" "$out" prepare
"$python" hardware/build_nine_control_plane.py "$out/selected.json"
"$python" hardware/build_selected_nine_assembly.py "$out/selected.json" hardware/blockv2-mod-shared-memory.json
/public/home/yuzelu/project-circuit/issue250-u-n32-stored-link-20261112-01/tool.sh bash tests/elaborate_selected_nine_assembly.sh
"$python" hardware/check_selected_nine_assembly.py "evidence/architecture-revision-185/selected-nine-assembly-$SLURM_JOB_ID"
"$python" audits/package_range_plans.py "$plans" "$out" "evidence/architecture-revision-185/selected-nine-assembly-$SLURM_JOB_ID/receipt.json"
