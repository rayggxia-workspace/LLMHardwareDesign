#!/bin/bash
set -euo pipefail
kind=$1
case "$kind" in cached) ;; *) exit 2;; esac
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu
src=/public/home/yuzelu/project-circuit/yzl-cu-overlay-physical-20261116/C
run=${2:-$root/runs/C-v16-genericadder-$kind}
mkdir -p "$run"
cd "$run"
test ! -e STARTED || exit 2
date -Is > STARTED
cp "$root/loader-$kind.sv" loader-candidate.sv
echo "a0f71497ee0c873649c41d64122e2a906775caaed90dc615a686be053625d0f9  loader-candidate.sv" | sha256sum -c
cp "$root/../audit/C-cached-loader-proof-binding.json" source-proof-binding.json
cp "$src/config.mk" config.mk
cp "$src/input.sdc" input.sdc
cat "$root/provisional-io.sdc" >> input.sdc
python3 - "$run" "$root" <<'PY'
from pathlib import Path
import sys
run,root=map(Path,sys.argv[1:]);p=run/'config.mk';s=p.read_text();g=root.parent/'gs/candidate-G-hold03-v3'
old='/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search/blockv2-mod-pipeline-next-20261115/staging/algo1-main-execution-20261116/new-control/e32_tiled_dot_loader.sv'
assert s.count(old)==1;s=s.replace(old,str(run/'loader-candidate.sv'))
lines=[];seen=set()
for line in s.splitlines():
 if line.startswith('export ADDITIONAL_'):
  words=line.split()
  for i,w in enumerate(words):
   if w.endswith('/block_v2_g.lef'):words[i]=str(g/'parent-abstract-v3/block_v2_g.lef');seen.add('lef')
   elif w.endswith('/block_v2_g.lib'):words[i]=str(g/'qualification-v2/block_v2_g.lib');seen.add('lib')
   elif '/release/g/' in w and w.endswith('/6_final.gds'):words[i]=str(g/'qualification-v2/flow/results/nangate45/bv1_block_v2_g/base/6_final.gds');seen.add('gds')
  line=' '.join(words)
 lines.append(line)
assert seen=={'lef','lib','gds'}
lines += [f'export SDC_FILE = {run}/input.sdc',f'export FOOTPRINT_TCL = {root}/c-exact-signal-footprint.tcl',f'export PRE_GLOBAL_ROUTE_TCL = {root}/pre-global-v3.tcl',f'export POST_GLOBAL_ROUTE_TCL = {root}/post-global-v5.tcl','export GLOBAL_ROUTE_ARGS = -verbose -congestion_report_iter_step 5','export GLOBAL_ROUTE_USE_CUGR = 0','export CTS_ARGS = -sink_clustering_enable -repair_clock_nets -apply_ndr none -balance_levels -root_buf BUF_X32 -buf_list {BUF_X8 BUF_X16 BUF_X32}','export SKIP_CTS_REPAIR_TIMING = 0']
p.write_text('\n'.join(lines)+'\n')
with (run/'input.sdc').open('a') as f:
 for port in (root/'C-outputs.txt').read_text().splitlines(): f.write('set_load 50 [get_ports {'+port+'}]\n')
PY
printf '\nexport PDN_TCL = %s/c-macro-pdn.tcl\nexport POST_PDN_TCL = %s/c-post-pdn.tcl\nexport FOOTPRINT_TCL = %s/c-fixed-footprint.tcl\nexport POST_IO_PLACEMENT_TCL = %s/c-post-io-exact.tcl\nexport ADDER_MAP_FILE =\n' "$root" "$root" "$root" "$root" >> config.mk
source /OpenROAD-flow-scripts/env.sh
export CU_OUTPUT_PORTS=$root/C-outputs.txt
python3 "$root/manifest.py" "$run"
sha256sum loader-candidate.sv input.sdc "$root/c-exact-signal-footprint.tcl" > candidate-contract-sha256.txt
args=(-C /OpenROAD-flow-scripts/flow DESIGN_CONFIG="$run/config.mk" WORK_HOME="$run/flow" NUM_CORES=8)
res=$run/flow/results/nangate45/c-overlay-current/base
make "${args[@]}" synth > synth.log 2>&1
make "${args[@]}" floorplan > floorplan.log 2>&1
make "${args[@]}" place > place.log 2>&1
export CU_SNAPSHOT_ODB=$src/flow/results/nangate45/c-overlay-current/base/4_cts.odb CU_SNAPSHOT_OUT=$run/geometry-reference.tsv
openroad -no_init -exit "$root/snapshot-geometry.tcl" > geometry-reference.log 2>&1
export CU_SNAPSHOT_ODB=$res/3_place.odb CU_SNAPSHOT_OUT=$run/geometry-prects.tsv
openroad -no_init -exit "$root/snapshot-geometry.tcl" > geometry-prects.log 2>&1
python3 "$root/compare-signal-geometry.py" geometry-reference.tsv geometry-prects.tsv geometry-prects-contract.json
make "${args[@]}" cts > cts.log 2>&1
export CU_SNAPSHOT_ODB=$res/4_cts.odb CU_SNAPSHOT_OUT=$run/geometry-postcts.tsv
openroad -no_init -exit "$root/snapshot-geometry.tcl" > geometry-postcts.log 2>&1
python3 "$root/compare-signal-geometry.py" geometry-reference.tsv geometry-postcts.tsv geometry-postcts-contract.json
make "${args[@]}" do-grt > grt.log 2>&1
make "${args[@]}" do-5_2_route do-5_3_fillcell do-5_route do-5_route.sdc > route.log 2>&1
make "${args[@]}" do-finish > finish.log 2>&1
make "${args[@]}" do-gds > gds.log 2>&1
bash "$root/signoff-v4.sh" "$run"
bash "$root/lec-v3.sh" "$run" "$src/flow/results/nangate45/c-overlay-current/base/4_cts.odb"
