#!/bin/bash
set -euo pipefail
base=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117
r=$base/cu
run=$r/runs/C-v42-neighbor-common
mkdir "$run";cd "$run"
source_run=$r/runs/C-v38-close-y640-h50
cp "$source_run/config.mk" config.mk
export CU_LIBS=$(sed -n 's/^export ADDITIONAL_LIBS = //p' config.mk | tail -1)
export CU_RESULTS=$run/flow/results/nangate45/c-overlay-current/base RESULTS_DIR=$run
mkdir -p "$CU_RESULTS"
cp "$source_run/flow/results/nangate45/c-overlay-current/base/1_synth_lec.v" "$CU_RESULTS/"
export C_ECO_SOURCE_SDC=$source_run/flow/results/nangate45/c-overlay-current/base/6_final.sdc
export C_CLOSE_SOURCE_ODB=$source_run/flow/results/nangate45/c-overlay-current/base/6_final.odb
export C_SIZES_PLAN=$run/size-plan.tsv
cp "$r/runs/C-v40-final-sizes/size-plan.tsv" "$C_SIZES_PLAN"
echo '8e64222ad9eeab2266455e4f8a3023ca0eb622f5028e37a48efab8e0db2a66a7  '"$C_CLOSE_SOURCE_ODB" | sha256sum -c -
cp "$r/c-final-sizes-edit-v1.tcl" edit-frozen.tcl
cp "$r/c-final-sizes-prepare-v1.tcl" route-frozen.tcl
cp "$r/c-neighbor-rip-v1.tcl" neighbor-hook.tcl
cp "$base/audit/C40-neighbor-rip-plan-v1/all-nets.txt" neighbor-nets.txt
cp "$base/audit/C40-neighbor-rip-plan-v1/frozen-report-5.rpt" neighbor-report.rpt
cp "$base/audit/C40-neighbor-rip-plan-v1/plan.json" neighbor-plan.json
cp "$base/audit/C40-neighbor-rip-plan-v1/db-validation-receipt.json" neighbor-source-validation.json
export C_EXTRA_RIP_HOOKS=$run/neighbor-hook.tcl
export C_NEIGHBOR_NETS=$run/neighbor-nets.txt
for f in neighbor-hook.tcl neighbor-nets.txt neighbor-report.rpt neighbor-plan.json neighbor-source-validation.json "$C_CLOSE_SOURCE_ODB" "$C_ECO_SOURCE_SDC" "$C_SIZES_PLAN" edit-frozen.tcl route-frozen.tcl "$r/c-freeze-outputs-v1.tcl" "$r/geometry.tcl" $CU_LIBS;do test -s "$f";sha256sum "$f";done > inputs.sha256
source /OpenROAD-flow-scripts/env.sh
openroad -no_init -exit edit-frozen.tcl > edit.log 2>&1
openroad -no_init -exit route-frozen.tcl > prepare-route.log 2>&1
cmp legalized.v "$r/runs/C-v40-final-sizes/legalized.v"
python3 - "$r/runs/C-v40-final-sizes/legalized.def" legalized.def <<'PY'
import pathlib,re,sys
texts=[pathlib.Path(p).read_text() for p in sys.argv[1:]]
for section in ('COMPONENTS','PINS','SPECIALNETS'):
 blocks=[re.search(r'\n'+section+r'\b.*?\nEND '+section+r'\b',s,re.S).group() for s in texts]
 assert blocks[0]==blocks[1], ('Changed physical interface/cells',section)
print('COMMON_COMPONENTS_PINS_PG_EXACT_VS_PROVEN_C40')
PY
sha256sum legalized.{odb,def,v} global.odb regenerated-ap.odb route.guide geometry-original.tsv config.mk size-plan.tsv > prepared.sha256
