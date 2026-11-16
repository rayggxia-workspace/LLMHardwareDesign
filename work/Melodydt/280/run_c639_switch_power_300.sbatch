#!/usr/bin/env bash
#SBATCH --job-name=mdt-280sw300
#SBATCH --partition=c64,c96
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --time=00:40:00
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
      "$base/opt/eda/containers/orfs-current-repacked.sif" bash "$bundle/run_c639_switch_power_300.sbatch" inside "$bundle" "$SLURM_JOB_ID" "$SLURM_CPUS_PER_TASK"
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
frozen=$runs/c639-g32-gate-01/c639-g32-116937
replay=$frozen/replay-116937
source=$frozen/source/project
switch=$source/rtl/mother_control_native/mc_lc_packet128_switch.sv
cohort=$source/rtl/mother_control_native/native_three_lc_cohort.sv
controller=$source/rtl/mother_control_native/native_product_controller.sv
fixture=$source/experiments/block_local_native/test_native_decode638_product_replay.sv
runner=$source/experiments/block_local_native/run_decode638_q_tile_replay.sh
route=$runs/c639-m-physical-03/route-116976/native
scope=TOP/test_native_decode638_product_replay/controller/cohort/transport
extractor=$runs/c639-g32-power-03/power-116943/fst_scope_vcd
wave_audit=$runs/c639-m-wave-audit-01/wave-116958
sha256sum --quiet -c "$wave_audit/wave-inputs.sha256"
sha256sum "$switch" "$cohort" "$controller" "$fixture" "$runner" "$extractor" \
  "$frozen"/activity-{0,1}.txt "$wave_audit/wave-inputs.sha256" > "$out/inputs.sha256"
python3 - "$switch" "$cohort" "$controller" "$fixture" "$out/top.sv" <<'PY'
from pathlib import Path
import re
import sys

source, cohort, controller, fixture, output = map(Path, sys.argv[1:])
assert "localparam int LOCAL_COUNT=4;" in fixture.read_text()
assert ".LOCAL_COUNT(LOCAL_COUNT), .REBIND_TARGET(LOCAL_COUNT'(1))" in fixture.read_text()
assert "LOCAL_TARGET(" not in fixture.read_text()
assert "LOCAL_TARGET = '0," in controller.read_text()
assert ".LOCAL_COUNT(LOCAL_COUNT)" in controller.read_text()
assert ".REBIND_TARGET(REBIND_TARGET), .LOCAL_TARGET(LOCAL_TARGET)" in controller.read_text()
assert ".ENDPOINTS(LOCAL_COUNT), .REBIND_TARGET(REBIND_TARGET), .LOCAL_TARGET(LOCAL_TARGET)" in cohort.read_text()
ports, = re.findall(r"module mc_lc_packet128_switch #\(.*?\)\s*\((.*?)\n\);", source.read_text(), re.S)
ports = ports.replace("ENDPOINTS", "4")
output.write_text("module mdt_c639_switch(" + ports + "\n);\n"
                  "  mc_lc_packet128_switch #(.ENDPOINTS(4), .REBIND_TARGET(4'b0001), .LOCAL_TARGET(32'b0)) dut(.*);\n"
                  "endmodule\n")
PY
cp "$route/input.sdc" "$out/target.sdc"
cat > "$out/config.mk" <<EOF
export PLATFORM = nangate45
export DESIGN_NAME = mdt_c639_switch
export DESIGN_NICKNAME = mdt_c639_switch
export SYNTH_HDL_FRONTEND = slang
export VERILOG_FILES = $switch $out/top.sv
export SDC_FILE = $out/target.sdc
export CORE_UTILIZATION = 35
export PLACE_DENSITY = 0.55
EOF
make -C /OpenROAD-flow-scripts/flow DESIGN_CONFIG="$out/config.mk" WORK_HOME="$out/flow" NUM_CORES="$cores" \
  finish > "$out/flow.log" 2>&1
physical=$out/flow/results/nangate45/mdt_c639_switch/base
metrics=$out/flow/logs/nangate45/mdt_c639_switch/base/6_report.json
sha256sum "$physical"/6_final.{v,odb,sdc,spef} "$metrics" > "$out/physical.sha256"
echo C639_FOUR_ENDPOINT_SWITCH_ROUTED
for mode in 0 1; do
    for phase in gate-up down; do
        sample=$out/mode-$mode-$phase
        mkdir "$sample"
        wave=$replay/DDR-$mode/ffn-$phase.fst
        read -r first last < <(awk -v phase="$phase" '$1 == phase {print $2,$3}' "$frozen/activity-$mode.txt")
        "$extractor" "$wave" "$sample/raw.vcd" "$scope" > "$sample/extract.log"
        python3 -B - "$bundle" "$physical/6_final.v" "$sample" "$scope" "$first" "$last" <<'PY'
from pathlib import Path
import sys
bundle, netlist, sample = map(Path, sys.argv[1:4])
scope, first, last = sys.argv[4:]
sys.path.insert(0, str(bundle))
from extract_c639_m_ports import extract
extract(netlist, sample / "raw.vcd", sample / "ports.vcd", scope, int(first), int(last), 100, 762)
PY
        python3 -B "$bundle/gate_power_300.py" "$sample/ports.vcd" "$physical" dut "$sample/power" \
            10000 0 "$((last-first))" --cores "$cores" --reference-annotations 762
    done
done
python3 - "$out" "$metrics" <<'PY'
import json
from pathlib import Path
import sys
out, metrics = map(Path, sys.argv[1:])
data = json.loads(metrics.read_text())
rows = {path.parent.parent.name: json.loads(path.read_text()) for path in sorted(out.glob("mode-*/power/receipt.json"))}
if len(rows) != 4:
    raise ValueError("expected four archived switch windows")
summary = {"endpoints": 4, "rebind_target": 1, "local_target": 0, "frequency_mhz": 300,
           "activity": "frozen C639 packet-switch RTL port VCD with internal activity propagation",
           "setup_wns_ns": data["finish__timing__setup__ws"], "hold_wns_ns": data["finish__timing__hold__ws"],
           "windows": {label: {key: row[key] for key in ("power_w", "energy_nj", "annotated", "unannotated")}
                       for label, row in rows.items()}}
(out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
PY
cd "$out"
sha256sum inputs.sha256 physical.sha256 top.sv config.mk target.sdc openroad.sha256 summary.json \
  mode-*/power/{receipt.json,power.log} > results.sha256
sha256sum -c results.sha256
echo C639_FOUR_ENDPOINT_SWITCH_POWER_300_PASS
