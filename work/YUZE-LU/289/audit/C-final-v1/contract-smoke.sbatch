#!/bin/bash
#SBATCH --job-name=yzl-289-C-contract
#SBATCH --partition=c96,c64
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --time=00:30:00
#SBATCH --output=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-contract-smoke-%j.log
set -euo pipefail
r=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117
src=$r/cu/runs/C-v20-native-clock4
out=$r/audit/C-final-v1/contract-smoke-v20
mkdir "$out"
mkdir "$out/res"
ln -s "$src/global-candidate.odb" "$out/res/6_final.odb"
cp "$r/audit/C-final-v1/expected-contract.tcl" "$out/"
cat > "$out/actual.tcl" <<'TCL'
read_liberty /OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib
foreach lib $::env(C_LIBS) {read_liberty $lib}
read_db $::env(C_FINAL_RES)/6_final.odb
read_sdc $::env(C_ACTUAL_SDC)
set_propagated_clock [all_clocks]
write_sdc -digits 9 actual-normalized.sdc
TCL
export C_FINAL_RES=$out/res
export C_LIBS=$(sed -n 's/^export ADDITIONAL_LIBS = //p' "$src/config.mk" | tail -1)
export C_ACTUAL_SDC=$src/route-source.sdc
sha256sum "$src/global-candidate.odb" "$C_ACTUAL_SDC" "$src/config.mk" "$out/"*.tcl > "$out/inputs-before.sha256"
/public/software/singularity-ce-4.3.4/bin/singularity exec --bind /public/home/yuzelu --pwd "$out" /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash -c 'set -euo pipefail; source /OpenROAD-flow-scripts/env.sh; openroad -no_init -exit expected-contract.tcl > expected.log 2>&1; openroad -no_init -exit actual.tcl > actual.log 2>&1'
sha256sum "$src/global-candidate.odb" "$C_ACTUAL_SDC" "$src/config.mk" "$out/"*.tcl > "$out/inputs-after.sha256"
cmp "$out/inputs-before.sha256" "$out/inputs-after.sha256"
python3 - "$out" <<'PY'
from pathlib import Path
import sys,json,hashlib,difflib
p=Path(sys.argv[1]);names=('expected-normalized.sdc','actual-normalized.sdc');lines=lambda f:[s.strip() for s in f.read_text().splitlines() if s.strip() and not s.lstrip().startswith('#')];a,b=[lines(p/n) for n in names];diff=list(difflib.unified_diff(a,b));(p/'difference.txt').write_text('\n'.join(diff));r=dict(passed=a==b,scope='Read-only current C-v20 route-source SDC smoke; no final timing/physical qualification',noncomment_commands=len(a),source_sha256={str(p/n):hashlib.sha256((p/n).read_bytes()).hexdigest() for n in names});(p/'receipt.json').write_text(json.dumps(r,indent=2));print(json.dumps(r,indent=2));assert r['passed']
PY
