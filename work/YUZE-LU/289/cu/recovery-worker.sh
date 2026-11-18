#!/bin/bash
set -euo pipefail
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu
kind=$1
exec /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --env "OMP_NUM_THREADS=8,RECOVERY_KIND=$kind" /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash -c '
set -euo pipefail
source /OpenROAD-flow-scripts/env.sh
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu
case "$RECOVERY_KIND" in
 proof)
  cd "$root"
  yosys -s select-proof.ys > select-proof-recovery.log 2>&1
  yosys -s loader-proof.ys > loader-proof-recovery.log 2>&1
  date -Is > LOADER_PARALLEL_PROOF_PASSED ;;
 original|parallel)
  run=$root/loader-map-$RECOVERY_KIND
  mkdir -p "$run"
  if [ ! -f "$run/map.ys" ]; then sed "s/loader-original.sv/loader-$RECOVERY_KIND.sv/" "$root/loader-map-original/map.ys" > "$run/map.ys"; fi
  cd "$run"
  yosys -s map.ys > synthesis-recovery.log 2>&1
  openroad -no_init -exit "$root/loader-map-sta.tcl" > sta-recovery.log 2>&1 ;;
 pg)
  openroad -no_init -exit "$root/pg-vias.tcl" > "$root/pg-vias.log" 2>&1 ;;
 U|C)
  if [ "$RECOVERY_KIND" = U ]; then run=$root/runs/U-v6-ctsdelay-x8-seed0; lower=u; else run=$root/runs/C-v10-ctsdelay-newG-x8-seed0; lower=c; fi
  cd "$run"
  args=(-C /OpenROAD-flow-scripts/flow DESIGN_CONFIG="$run/config.mk" WORK_HOME="$run/flow" NUM_CORES=8)
  res=$run/flow/results/nangate45/$lower-overlay-current/base
  if [ ! -f "$res/5_1_grt.odb" ]; then make "${args[@]}" do-grt > grt-recovery.log 2>&1; fi
  make "${args[@]}" do-5_2_route do-5_3_fillcell do-5_route do-5_route.sdc > route-recovery.log 2>&1
  make "${args[@]}" do-finish > finish-recovery.log 2>&1
  make "${args[@]}" do-gds > gds-recovery.log 2>&1
  a=0; bash "$root/signoff-v4.sh" "$run" || a=$?
  b=0; bash "$root/lec-v3.sh" "$run" /public/home/yuzelu/project-circuit/yzl-cu-overlay-physical-20261116/$RECOVERY_KIND/flow/results/nangate45/$lower-overlay-current/base/4_cts.odb || b=$?
  test "$a" -eq 0 -a "$b" -eq 0 ;;
 *) exit 2;;
esac
'
