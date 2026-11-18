#!/usr/bin/env bash
#SBATCH --job-name=mdt-280ctrl300
#SBATCH --partition=c64,c96
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=12
#SBATCH --time=04:30:00
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
      "$base/opt/eda/containers/orfs-current-repacked.sif" bash "$bundle/run_c639_control_component_power_300.sbatch" inside "$bundle" "$SLURM_JOB_ID" "$SLURM_CPUS_PER_TASK" "${1:?use dma or fetch}"
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
component=$5
frozen=$runs/c639-g32-gate-01/c639-g32-116937
source=$frozen/source/project
replay=$frozen/replay-116937
fixture=$source/experiments/block_local_native
extractor=$runs/c639-g32-power-03/power-116943/fst_scope_vcd
wave_audit=$runs/c639-m-wave-audit-01/wave-116958
route=$runs/c639-m-physical-03/route-116976/native
root=TOP/test_native_decode638_product_replay
case "$component" in
    dma)
        top=mc_dma_fabric_typed_p
        rtl=$source/rtl/mother_control_native/$top.sv
        binding=$fixture/native_typed_dma_phase_mux.sv
        grep -F 'mc_dma_fabric_typed_p dma (' "$binding"
        grep -F 'native_typed_dma_phase_mux typed_dma(' "$fixture/test_native_decode638_product_replay.sv"
        side=2000
        sites=("$root/typed_dma/dma")
        ;;
    fetch)
        top=lc_scope_fetch128
        rtl=$source/experiments/shared_x_control/rtl/$top.sv
        binding=$source/experiments/shared_x_control/rtl/lc_native_scope_controller.sv
        grep -F 'lc_scope_fetch128 scope_fetch(' "$binding"
        side=420
        sites=()
        for lane in 0 1 2 3; do sites+=("$root/controller/cohort/local_target[$lane]/local_controller/scope_fetch"); done
        ;;
    *) echo "expected dma or fetch, got $component" >&2; exit 2 ;;
esac
sha256sum --quiet -c "$wave_audit/wave-inputs.sha256"
sha256sum "$rtl" "$binding" "$fixture/test_native_decode638_product_replay.sv" "$route/input.sdc" \
  "$extractor" "$frozen"/activity-{0,1}.txt "$wave_audit/wave-inputs.sha256" > "$out/inputs.sha256"
cp "$route/input.sdc" "$out/target.sdc"
cat > "$out/config.mk" <<EOF
export PLATFORM = nangate45
export DESIGN_NAME = $top
export DESIGN_NICKNAME = $top
export SYNTH_HDL_FRONTEND = slang
export VERILOG_FILES = $rtl
export SDC_FILE = $out/target.sdc
export DIE_AREA = 0 0 $side $side
export CORE_AREA = 10 10 $((side-10)) $((side-10))
export PLACE_DENSITY = 0.55
EOF
make -C /OpenROAD-flow-scripts/flow DESIGN_CONFIG="$out/config.mk" WORK_HOME="$out/flow" NUM_CORES="$cores" \
  finish > "$out/flow.log" 2>&1
key=nangate45/$top/base
physical=$out/flow/results/$key
metrics=$out/flow/logs/$key/6_report.json
sha256sum "$physical"/6_final.{v,odb,sdc,spef} "$metrics" > "$out/physical.sha256"
echo COMPONENT_300_ROUTED "$component"
workers=1
if [[ $component == fetch ]]; then workers=4; fi
threads=$((cores / workers))
one_sample() {
    local sample=$1 wave=$2 scope=$3 first=$4 last=$5
    mkdir -p "$sample"
    "$extractor" "$wave" "$sample/raw.vcd" "$scope" > "$sample/extract.log"
    python3 -B - "$bundle" "$physical/6_final.v" "$sample" "$scope" "$first" "$last" "$component" "$threads" <<'PY'
import json
from pathlib import Path
import sys
bundle, netlist, sample = map(Path, sys.argv[1:4])
scope, first, last, component, threads = sys.argv[4:]
first, last, threads = int(first), int(last), int(threads)
sys.path.insert(0, str(bundle))
from extract_c639_m_ports import extract
from gate_power_300 import analyze

untraced = ("c_rsp_data",) if component == "dma" else ()
wave = sample / "ports.vcd"
extract(netlist, sample / "raw.vcd", wave, scope, first, last, 100, None, untraced)
ports = json.loads(wave.with_suffix(".json").read_text())
expected = sum(ports["port_bits"].values())
pairs = [("client_reads", "c_req_valid", "c_req_ready"), ("client_returns", "c_rsp_valid", "c_rsp_ready"),
         ("ddr_reads", "d_req_valid", "d_req_ready"), ("ddr_returns", "d_rsp_valid", "d_rsp_ready")]
if component == "fetch":
    pairs = [("scope_starts", "start_valid", "start_ready"), ("descriptor_deliveries", "fetch_valid", "fetch_ready"),
             ("dma_requests", "mc_req_valid", "mc_req_ready"), ("dma_returns", "mc_rsp_valid", "mc_rsp_ready")]
wanted = {"clk"} | {name for _, valid, ready in pairs for name in (valid, ready)}
signals, values, prev = {}, {}, {}
counts = {key: 0 for key, _, _ in pairs}
counts["clock"] = 0

def boundary():
    if prev.get("clk") == 0 and values.get("clk") == 1:
        counts["clock"] += 1
        for key, valid, ready in pairs:
            counts[key] += (prev[valid] & prev[ready]).bit_count()
    prev.update(values)

for line in wave.open():
    fields = line.split()
    if fields[:1] == ["$var"] and fields[4] in wanted:
        signals[fields[3]] = fields[4]
    elif line.startswith("#"):
        boundary()
    elif line.startswith("b") and len(fields) == 2 and fields[1] in signals:
        values[signals[fields[1]]] = int(fields[0][1:], 2)
    elif line[:1] in ("0", "1") and line[1:].strip() in signals:
        values[signals[line[1:].strip()]] = int(line[0])
boundary()
if set(signals.values()) != wanted or counts["clock"] != 8192:
    raise ValueError(f"missing transaction evidence in {wave}: {counts}")
(sample / "activity.json").write_text(json.dumps(counts, indent=2) + "\n")
analyze(wave, netlist.parent, "dut", sample / "power", 10000, 0, last - first, threads,
        reference_annotations=expected)
PY
}
for mode in 0 1; do
    for phase in gate-up down; do
        wave=$replay/DDR-$mode/ffn-$phase.fst
        read -r first last < <(awk -v phase="$phase" '$1==phase {print $2,$3}' "$frozen/activity-$mode.txt")
        pids=()
        for lane in "${!sites[@]}"; do
            (set -e; one_sample "$out/mode-$mode-$phase/site-$lane" "$wave" "${sites[$lane]}" "$first" "$last") &
            pids+=("$!")
        done
        failed=0
        for pid in "${pids[@]}"; do if ! wait "$pid"; then failed=1; fi; done
        ((failed == 0))
    done
done
python3 - "$out" "$metrics" "$component" "$side" <<'PY'
import json
from pathlib import Path
import sys
out, metrics = map(Path, sys.argv[1:3])
component, side = sys.argv[3:]
k = json.loads(metrics.read_text())
rows = {}
for sample in sorted(out.glob("mode-*/site-*")):
    power = json.loads((sample / "power/receipt.json").read_text())
    ports = json.loads((sample / "ports.json").read_text())
    rows[str(sample.relative_to(out))] = {
        "transactions": json.loads((sample / "activity.json").read_text()),
        "coverage": ports, "power_w": power["power_w"], "energy_nj": power["energy_nj"],
        "direct_pin_activity": power["annotated"], "tool_inferred_activity": power["unannotated"],
    }
if len(rows) != (4 if component == "dma" else 16):
    raise ValueError("missing windows")
summary = {"component": component, "frequency_hz": 300000000, "die_side_um": int(side),
           "activity": "explicit frozen C639 RTL ports; propagated internal activity",
           "setup_wns_ns": k["finish__timing__setup__ws"], "hold_wns_ns": k["finish__timing__hold__ws"], "windows": rows}
(out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
PY
cd "$out"
sha256sum inputs.sha256 physical.sha256 openroad.sha256 config.mk target.sdc summary.json \
    mode-*/site-*/{ports.json,activity.json,power/receipt.json,power/power.log} > results.sha256
sha256sum -c results.sha256
echo C639_COMPONENT_POWER_300_PASS "$component"
