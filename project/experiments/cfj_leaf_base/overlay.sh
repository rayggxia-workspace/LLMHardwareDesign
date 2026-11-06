#!/usr/bin/env bash
set -euo pipefail
run=$1
pair=$SLURM_ARRAY_TASK_ID
out="$run/$pair"
result=$(find "$out/flow/results" -name 6_final.odb -printf '%h\n')
[[ -n "$result" && -s "$result/6_final.gds" ]]
export SINGULARITYENV_CFJ_FINAL_ODB="$result/6_final.odb"
export SINGULARITYENV_CFJ_NATIVE_GDS="$result/6_final.gds"
export SINGULARITYENV_CFJ_ENDPOINTS="$out/endpoints.tsv"
export SINGULARITYENV_CFJ_OVERLAY_DIR="$out"
export SINGULARITYENV_CFJ_FINAL_LIBS SINGULARITYENV_CFJ_FINAL_LEFS SINGULARITYENV_CFJ_FINAL_TOP
SINGULARITYENV_CFJ_FINAL_LIBS=$(sed -n 's/^export ADDITIONAL_LIBS = //p' "$out/config.mk")
SINGULARITYENV_CFJ_FINAL_LEFS=$(sed -n 's/^export ADDITIONAL_LEFS = //p' "$out/config.mk")
SINGULARITYENV_CFJ_FINAL_TOP=$(sed -n 's/^export DESIGN_NAME = //p' "$out/config.mk")
cpus=$SLURM_CPUS_PER_TASK
exec srun --exact --ntasks=1 --cpus-per-task="$cpus" --cpu-bind=cores \
 /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv \
 --bind /public/home/yuzelu /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif \
 bash -c '
  set -eu
  source /OpenROAD-flow-scripts/env.sh
  openroad -no_init -exit "$1/endpoints.tcl"
  overlay_rc=0
  klayout -b -r "$1/overlay.py" || overlay_rc=$?
  upper_rc=0
  if [[ "$overlay_rc" == 0 ]]; then
    (
      set -eu
      python3 "$1/stitch_spef.py" "$CFJ_OVERLAY_DIR" "$(dirname "$CFJ_FINAL_ODB")"
      openroad -no_init -exit "$1/stitch_netlist.tcl" > "$CFJ_OVERLAY_DIR/stitched-netlist.log" 2>&1
      for variant in base high; do
        CFJ_UPPER_RC_VARIANT=$variant openroad -no_init -exit "$1/stitch_sta.tcl" \
          > "$CFJ_OVERLAY_DIR/stitched-$variant.log" 2>&1
      done
      python3 "$1/upper_receipt.py"
    ) &
    upper_job=$!
  fi
  native_rc=0
  openroad -no_init -exit "$1/native_audit.tcl" > "$CFJ_OVERLAY_DIR/native-audit.log" 2>&1 || native_rc=$?
  klayout -b -r /OpenROAD-flow-scripts/flow/platforms/nangate45/drc/FreePDK45.lydrc \
    -rd "in_gds=$CFJ_NATIVE_GDS" -rd "report_file=$CFJ_OVERLAY_DIR/native-drc.lyrdb" \
    > "$CFJ_OVERLAY_DIR/native-drc.log" 2>&1 || native_rc=$?
  python3 "$1/native_audit.py" || native_rc=$?
  if [[ "$overlay_rc" != 0 ]]; then exit "$overlay_rc"; fi
  wait "$upper_job" || upper_rc=$?
  if [[ "$native_rc" != 0 ]]; then exit "$native_rc"; fi
  exit "$upper_rc"
 ' bash "$2"
