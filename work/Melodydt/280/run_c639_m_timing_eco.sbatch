#!/usr/bin/env bash
#SBATCH --job-name=mdt-280meco
#SBATCH --partition=c64,c96
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=12
#SBATCH --time=04:30:00
#SBATCH --output=slurm-%j.log
set -euo pipefail
base=/public/home/yuzelu
cd "$SLURM_SUBMIT_DIR"
bundle=$PWD
sha256sum -c bundle.sha256
route=$base/Melodydt/runs/issue-280/c639-m-physical-03/route-116976
original=$route/native
key=nangate45/bv1_m_native_leaf_s32/base
out=$bundle/eco-$SLURM_JOB_ID
mkdir "$out" "$out/tmp"
(cd "$route" && sha256sum -c route-results.sha256)
sha256sum -c cts-inputs.sha256
for kind in results logs reports objects; do mkdir -p "$out/flow/$kind/$key"; done
for f in "$original/flow/results/$key"/{4_cts.odb,4_cts.sdc,1_2_yosys.v,1_synth.sdc,3_place.odb,3_place.sdc}; do
    if [[ -f "$f" ]]; then cp -p "$f" "$out/flow/results/$key/"; fi
done
cp "$original/flow/reports/$key/6_finish.rpt" "$out/pre-eco-finish.rpt"
cp "$original/flow/logs/$key/6_report.json" "$out/pre-eco-metrics.json"
sed '/^export PRE_GLOBAL_ROUTE_TCL =/d; /^export HOLD_SLACK_MARGIN =/d; /^export SETUP_SLACK_MARGIN =/d' "$original/config.mk" > "$out/config.mk"
cat >> "$out/config.mk" <<EOF
export PRE_GLOBAL_ROUTE_TCL = $out/timing-eco.tcl
export HOLD_SLACK_MARGIN = 0.065
export SETUP_SLACK_MARGIN = 0.150
EOF
echo "source {$original/input-diodes.tcl}" > "$out/timing-eco.tcl"
cat >> "$out/timing-eco.tcl" <<'TCL'
rename repair_timing_helper original_repair_timing_helper
proc repair_timing_helper {args} {
  puts {MDT_M_ECO_SETUP_BEGIN}
  uplevel 1 [list original_repair_timing_helper {*}$args -setup -max_passes 80 -max_repairs_per_pass 10]
  puts {MDT_M_ECO_HOLD_BEGIN}
  uplevel 1 [list original_repair_timing_helper {*}$args -hold -max_buffer_percent 4]
  puts {MDT_M_ECO_REPAIR_END}
}
TCL
cp "$bundle/cts-inputs.sha256" "$out/"
srun --exact -N1 -n1 -c "$SLURM_CPUS_PER_TASK"     /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind "$base"     --env "TMPDIR=$out/tmp" "$base/opt/eda/containers/orfs-current-repacked.sif"     bash -c '
    set -euo pipefail
    source /OpenROAD-flow-scripts/env.sh
    out=$1
    cores=$2
    openroad -version > "$out/openroad-version.txt"
    sha256sum "$(command -v openroad)" > "$out/tool.sha256"
    make -C /OpenROAD-flow-scripts/flow DESIGN_CONFIG="$out/config.mk" WORK_HOME="$out/flow" NUM_CORES="$cores" do-route
    make -C /OpenROAD-flow-scripts/flow DESIGN_CONFIG="$out/config.mk" WORK_HOME="$out/flow" NUM_CORES="$cores" do-finish
    ' bash "$out" "$SLURM_CPUS_PER_TASK" > "$out/flow.log" 2>&1
cd "$out"
final=flow/results/$key
logs=flow/logs/$key
rep=flow/reports/$key
sha256sum config.mk timing-eco.tcl cts-inputs.sha256 openroad-version.txt tool.sha256 pre-eco-{finish.rpt,metrics.json} \
    "$final"/6_final.{v,odb,sdc,spef} "$logs/6_report.json" "$rep"/{6_finish.rpt,5_route_drc.rpt} > eco-results.sha256
sha256sum -c eco-results.sha256
python3 - "$logs/6_report.json" <<'PY'
import json
import sys

data = json.load(open(sys.argv[1]))
keys = ("finish__timing__setup__ws", "finish__timing__hold__ws")
print({key: data[key] for key in keys})
print("MDT_M_TIMING_" + ("PASS" if all(data[key] >= 0 for key in keys) else "VIOLATIONS_REMAIN"))
PY
