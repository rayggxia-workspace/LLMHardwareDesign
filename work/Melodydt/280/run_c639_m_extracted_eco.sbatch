#!/usr/bin/env bash
#SBATCH --job-name=mdt-280meco2
#SBATCH --partition=c64,c96
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=12
#SBATCH --time=04:00:00
#SBATCH --output=slurm-%j.log
set -euo pipefail
base=/public/home/yuzelu
if [[ ${1:-} == inside ]]; then
    bundle=$2
else
    bundle=${SLURM_SUBMIT_DIR:?}
fi
cd "$bundle"
if [[ ${1:-} != inside ]]; then
    sha256sum -c bundle.sha256
    exec srun --exact -n1 -c "$SLURM_CPUS_PER_TASK" --cpu-bind=cores \
      /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind "$base" \
      "$base/opt/eda/containers/orfs-current-repacked.sif" bash "$bundle/run_c639_m_extracted_eco.sbatch" inside "$bundle" "$SLURM_JOB_ID" "$SLURM_CPUS_PER_TASK"
fi
source /OpenROAD-flow-scripts/env.sh
bundle=$2
runs=$base/Melodydt/runs/issue-280
project=$base/project-circuit/LLMHardwareDesign
out=$bundle/result-$3
cores=$4
mkdir "$out"
openroad -version > "$out/openroad-version.txt"
sha256sum "$(command -v openroad)" > "$out/openroad.sha256"
route=$runs/c639-m-physical-03/route-116976
key=nangate45/bv1_m_native_leaf_s32/base
physical=$route/native/flow/results/$key
base_config=$route/native/config.mk
(cd "$route" && sha256sum -c route-results.sha256)
sha256sum "$physical/1_2_yosys.v" "$base_config" "$route/route-results.sha256" > "$out/inputs.sha256"
cp "$base_config" "$out/config.mk"
for folder in results reports logs objects; do mkdir -p "$out/flow/$folder/$key"; done
work=$out/flow/results/$key
cp -p "$physical/1_2_yosys.v" "$work/"
cat > "$out/eco.tcl" <<'TCL'
set base $::env(C639_ECO_INPUT)
set out $::env(C639_ECO_OUT)
set work $::env(C639_ECO_WORK)
set platform /OpenROAD-flow-scripts/flow/platforms/nangate45
read_liberty $platform/lib/NangateOpenCellLibrary_typical.lib
read_db $base/6_final.odb
read_sdc $base/6_final.sdc
source $platform/setRC.tcl
set_propagated_clock [all_clocks]
remove_fillers
read_spef $base/6_final.spef

proc timing_snapshot {prefix} {
  report_checks -path_delay max -group_path_count 30 -endpoint_path_count 1 -slack_max 0 \
      -sort_by_slack -format full_clock_expanded -fields {net input_pin slew capacitance fanout} \
      -digits 6 > "$prefix-setup.rpt"
  report_checks -path_delay min -group_path_count 30 -endpoint_path_count 1 -slack_max 0 \
      -sort_by_slack -format full_clock_expanded -fields {net input_pin slew capacitance fanout} \
      -digits 6 > "$prefix-hold.rpt"
  report_worst_slack -max -digits 6
  report_worst_slack -min -digits 6
}
puts {BASELINE_EXTRACTED}
timing_snapshot "$out/baseline-extracted"

puts {EXTRACTED_SETUP_ECO_BEGIN}
repair_timing -setup -setup_margin 0.020 -repair_tns 100 -max_passes 20 \
    -max_iterations 2000 -max_repairs_per_pass 4 -verbose
puts {EXTRACTED_HOLD_ECO_BEGIN}
repair_timing -hold -hold_margin 0.005 -max_buffer_percent 1 -verbose
puts {PLACEMENT_AND_GR_BEGIN}
detailed_placement
check_placement -verbose
# Existing signal routes reference the old cell connectivity. Preserve the PG
# special wires, remove signal routes, and regenerate routing guides.
set block [ord::get_db_block]
foreach net [$block getNets] {
  if {[$net getSigType] in {POWER GROUND}} { continue }
  set wire [$net getWire]
  if {$wire != "NULL"} { odb::dbWire_destroy $wire }
}
set_routing_layers -signal metal1-metal10 -clock metal4-metal10
pin_access -via_in_pin_bottom_layer metal10 -via_in_pin_top_layer metal10
global_route -congestion_iterations 30 -guide_file "$work/route.guide" -verbose
estimate_parasitics -global_routing
timing_snapshot "$out/post-eco-global-route"
write_db "$work/5_1_grt.odb"
write_sdc -no_timestamp "$work/5_1_grt.sdc"
TCL
export C639_ECO_INPUT="$physical" C639_ECO_OUT="$out" C639_ECO_WORK="$work"
openroad -no_init -threads "$cores" -exit "$out/eco.tcl" > "$out/eco.log" 2>&1
make_flow() {
  make -C /OpenROAD-flow-scripts/flow DESIGN_CONFIG="$out/config.mk" WORK_HOME="$out/flow" NUM_CORES="$cores" "$@"
}
make_flow do-5_2_route do-5_3_fillcell do-5_route do-5_route.sdc > "$out/detail-route.log" 2>&1
make_flow do-finish > "$out/finish.log" 2>&1
metrics=$out/flow/logs/$key/6_report.json
cd "$out"
sha256sum eco.tcl config.mk inputs.sha256 openroad.sha256 baseline-extracted-*.rpt post-eco-global-route-*.rpt \
    "$work"/6_final.{v,odb,sdc,spef} "$metrics" "$out/flow/reports/$key/"{6_finish.rpt,5_route_drc.rpt} > results.sha256
sha256sum -c results.sha256
python3 - "$metrics" <<'PY'
import json
import sys
with open(sys.argv[1]) as stream:
    data = json.load(stream)
metrics = {key: data[f"finish__timing__{key}"] for key in ("setup__ws", "hold__ws", "setup__tns", "hold__tns")}
print(json.dumps(metrics))
print("C639_M_ECO_300_STA_PASS" if min(metrics.values()) >= 0 else "C639_M_ECO_300_TIMING_REMAINS")
PY
