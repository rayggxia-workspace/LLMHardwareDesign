#!/bin/bash
#SBATCH --job-name=yzl-pr185-admit
#SBATCH --partition=debug,c64,c96
#SBATCH --cpus-per-task=2
#SBATCH --time=00:20:00
set -euo pipefail
cd /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search/blockv2-mod
export PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD/hardware:$PWD/compiler"
out="evidence/architecture-revision-185/pr185-admission-$SLURM_JOB_ID"
mkdir -p "$out/validated-source"
python3.11 tests/check_selected_parent_admission.py evidence/architecture-revision-185/selected-nine-assembly-114958/parent.xml > "$out/full-assembly-admission.json"
python3.11 hardware/audit_rtl_review_coverage.py > "$out/coverage.json"
bash tests/check_bound_product_packages.sh > "$out/bound-packages.json"
python3.11 - "$out" <<'PY'
import json,sys,shutil,hashlib
from pathlib import Path
out=Path(sys.argv[1])
files=['hardware/pr185-parent-resource-admission.json','hardware/pr185-historical-source-disposition.json',
'hardware/check_selected_nine_assembly.py','hardware/audit_rtl_review_coverage.py','tests/check_selected_parent_admission.py']
hashes={}
for name in files:
 p=Path(name);q=out/'validated-source'/name;q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,q)
 hashes[name]=hashlib.sha256(p.read_bytes()).hexdigest()
(out/'receipt.json').write_text(json.dumps({'sources':hashes,'elaboration_job':114958,'architecture_admission':True,
 'numerical_acceptance':False,'timing_acceptance':False},indent=2)+'\n')
print('complete architecture admission and existing bound package checks passed')
PY
