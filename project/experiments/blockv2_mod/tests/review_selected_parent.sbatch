#!/bin/bash
#SBATCH --job-name=yzl-pr185-review
#SBATCH --partition=debug,c64,c96
#SBATCH --cpus-per-task=2
#SBATCH --time=00:25:00
set -euo pipefail
cd /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search/blockv2-mod
mkdir -p tmp
export PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD/hardware:$PWD/compiler"
tool=/public/home/yuzelu/project-circuit/issue250-u-n32-stored-link-20261112-01/tool.sh
"$tool" bash tests/elaborate_selected_nine_assembly.sh
folder="evidence/architecture-revision-185/selected-nine-assembly-$SLURM_JOB_ID"
python3.11 hardware/check_selected_nine_assembly.py "$folder"
python3.11 tests/check_selected_parent_admission.py "$folder/parent.xml" > "$folder/admission-tests.json"
python3.11 hardware/test_pr185_control_admission.py > "$folder/control-tests.json"
python3.11 - <<'PY'
import ast,pathlib
files=list(pathlib.Path('tlm').glob('macro_*.py'))
for f in files:ast.parse(f.read_text(),filename=str(f))
print('TLM syntax only:',len(files))
PY
