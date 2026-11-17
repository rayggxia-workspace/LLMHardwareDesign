#!/bin/bash
# Gate-level equivalence, identical hard macro functional boundaries.
# Run only inside allocated ORFS container; a failure is never accepted.
set -euo pipefail
run=$(realpath "$1")
case "$run" in /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/runs/*) ;; *) exit 2;; esac
export CU_RESULTS=$(find "$run/flow/results/nangate45" -mindepth 2 -maxdepth 2 -type d | head -1)
export CU_SIGNOFF=$run/signoff
mkdir -p "$CU_SIGNOFF"
source /OpenROAD-flow-scripts/env.sh
openroad -no_init -exit /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/export-baseline.tcl > "$CU_SIGNOFF/export-baseline.log" 2>&1
python3 - "$run" "$CU_RESULTS" "$CU_SIGNOFF" <<'PY'
from pathlib import Path
import sys,re
run,res,out=map(Path,sys.argv[1:])
config=(run/'config.mk').read_text()
top=re.findall(r'^export DESIGN_NAME\s*=\s*(\S+)',config,re.M)[-1]
libs=re.findall(r'^export ADDITIONAL_LIBS\s*=\s*(.*)',config,re.M)[-1].split()
std='/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib'
lines=[]
for name,netlist in [('gold',out/'cts-baseline.v'),('gate',res/'6_final.v')]:
 lines += [f'read_liberty -ignore_miss_func {std}']
 lines += [f'read_liberty -lib {lib}' for lib in libs]
 lines += [f'read_verilog {netlist}', f'hierarchy -check -top {top}', 'proc', 'flatten', 'opt_clean', f'rename {top} {name}',f'design -stash {name}']
lines += ['design -copy-from gold -as gold gold','design -copy-from gate -as gate gate','equiv_make gold gate equiv','hierarchy -top equiv','equiv_simple','equiv_induct -seq 4','equiv_status -assert']
(out/'equivalence.ys').write_text('\n'.join(lines)+'\n')
PY
yosys -s "$CU_SIGNOFF/equivalence.ys" > "$CU_SIGNOFF/equivalence.log" 2>&1
date -Is > "$CU_SIGNOFF/LEC_PASSED"
