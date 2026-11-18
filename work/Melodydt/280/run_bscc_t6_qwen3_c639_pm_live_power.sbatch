#!/usr/bin/env bash
#SBATCH --job-name=mdt-280pmlivepwr
#SBATCH --partition=v6_384
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=12
#SBATCH --time=0
#SBATCH --output=slurm-%j.log
set -euo pipefail
if [[ ${1:-} != inside ]]; then
    bundle=${SLURM_SUBMIT_DIR:?}
    cd "$bundle"
    sha256sum --quiet -c live-inputs.sha256
    set +u
    source /public3/soft/modules/module.sh
    module load singularity/3.7.0
    set -u
    exec srun --ntasks=1 --cpus-per-task="$SLURM_CPUS_PER_TASK" --cpu-bind=cores \
        singularity exec --cleanenv --bind "$(dirname "$bundle")" "$HOME/LLMHardware/opt/orfs-current-repacked.rootfs" \
        bash "$bundle/run_bscc_t6_qwen3_c639_pm_live_power.sbatch" inside \
        "$bundle" "$SLURM_JOB_ID" "$SLURM_CPUS_PER_TASK" "${1:?PM audit job}"
fi

source /OpenROAD-flow-scripts/env.sh
bundle=$2
root=$(dirname "$bundle")
audit=$root/pm-runtime/pm-runtime-$5
product=$root/m-product/wide-38792112
replay=$product/replay-38792112
rtl_dir=$product/source/project/experiments/shared_x_control/rtl
rtl=$rtl_dir/lc_program_store_1k.sv
controller=$rtl_dir/lc_native_scope_controller.sv
physical=$root/leaf-physical/physical-38794460
helper=$root/writer-power/frozen
key=nangate45/lc_program_store_1k/base
out=$bundle/pm-live-power-$3

(cd "$replay" && sha256sum --quiet -c wide-results.sha256)
(cd "$physical" && sha256sum --quiet -c physical.sha256)
(cd "$audit" && sha256sum --quiet -c results.sha256)
expected_rtl=$(awk '$2 ~ /\/lc_program_store_1k\.sv$/ {print $1}' "$physical/source.sha256")
[[ $expected_rtl =~ ^[0-9a-f]{64}$ ]]
printf '%s  %s\n' "$expected_rtl" "$rtl" | sha256sum -c -
grep -Eq '^\s*lc_program_store_1k\s+pm\s*\(' "$controller"
mkdir "$out"
export PYTHONPATH=$helper:$root/pm-runtime
python3 -B - "$replay" "$audit/pm-runtime-audit.json" "$physical" "$key" "$out" "$helper" "$4" <<'PY'
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import subprocess
import sys
from extract_c639_m_ports import extract
from gate_power_300 import analyze
from qwen3_c639_pm_runtime_audit import count, digest

replay, audit_path, physical, key, out, helper = map(Path, sys.argv[1:7])
threads = int(sys.argv[7]) // 3
audit = json.loads(audit_path.read_bytes())
netlist = physical / "flow/results" / key
timing = json.loads((physical / "flow/logs" / key / "6_report.json").read_bytes())
drc = physical / "flow/reports" / key / "5_route_drc.rpt"
setup = timing["finish__timing__setup__ws"]
hold = timing["finish__timing__hold__ws"]
if min(setup, hold) < 0 or drc.stat().st_size:
    raise ValueError("LC PM physical timing or detailed-route DRC gate failed")

samples = []
for mode in (0, 1):
    label = "mode-{}-writer-active".format(mode)
    prefix = replay / "DDR-{}".format(mode) / "ffn-writer-active"
    wave = prefix.with_suffix(".fst")
    if digest(wave) != audit["inputs_sha256"][str(wave)]:
        raise ValueError("C639 PM waveform differs from runtime audit: {}".format(wave))
    with prefix.with_name(prefix.name + "-signals.tsv").open() as table:
        kind, first, last, timescale = next(table).split()
    first, last = int(first), int(last)
    if kind != "time" or timescale != "-12" or last - first != 81920000:
        raise ValueError("unexpected C639 PM window extent: {}".format(wave))
    for site in (0, 1, 2):
        row = audit["windows"][label][str(site)]
        if not row["requests"] or not row["responses"]:
            raise ValueError("missing audited runtime PM transactions: {}/{}".format(label, site))
        samples.append((label, site, wave, first, last, row))


def measure(sample):
    label, site, wave, first, last, row = sample
    name = "{}-site{}".format(label, site)
    target = out / name
    target.mkdir()
    raw, ports = target / "raw.vcd", target / "ports.vcd"
    with (target / "extract.log").open("w") as log:
        subprocess.run([str(helper / "fst_scope_vcd"), str(wave), str(raw), row["scope"]],
                       check=True, stdout=log)
    extract(netlist / "6_final.v", raw, ports, row["scope"], first, last, 100, None)
    raw.unlink()
    handshakes = count(ports, "dut")
    for field in ("rising_edges", "requests", "responses", "errors", "pending_at_start", "pending_at_end"):
        if handshakes[field] != row[field]:
            raise ValueError("normalized PM window changed {}: {}".format(field, name))
    original_addresses = {int(key): value for key, value in row["requests_by_address_bytes"].items()}
    if handshakes["requests_by_address_bytes"] != original_addresses:
        raise ValueError("normalized PM address counts changed: {}".format(name))
    declaration = json.loads(ports.with_suffix(".json").read_bytes())
    power = analyze(ports, netlist, "dut", target / "power", 10000, 0, last - first,
                    threads, reference_annotations=sum(declaration["port_bits"].values()))
    return name, {"handshakes": handshakes, "power_w": power["power_w"], "energy_nj": power["energy_nj"],
                  "annotated": power["annotated"], "unannotated": power["unannotated"]}


with ThreadPoolExecutor(max_workers=3) as pool:
    windows = dict(pool.map(measure, samples))
with (out / "pm-live-window-power.json").open("x") as stream:
    json.dump({"scope": "lc_program_store_1k layout 38794460, C639 writer-active leaf windows",
               "activity": "routed leaf driven by measured boundary VCD; propagated internal activity",
               "target_clock_mhz": 300, "setup_wns_ns": setup, "hold_wns_ns": hold,
               "drc_ok": True, "windows": windows}, stream, indent=2)
    stream.write("\n")
PY
cd "$out"
sha256sum "$bundle/live-inputs.sha256" "$root/pm-runtime/qwen3_c639_pm_runtime_audit.py" \
    "$physical/physical.sha256" "$physical/source.sha256" "$audit/results.sha256" \
    "$replay/wide-results.sha256" "$rtl" "$controller" \
    "$helper"/{fst_scope_vcd,extract_c639_m_ports.py,gate_power_300.py} \
    mode-*/ports.{vcd,json} mode-*/power/receipt.json pm-live-window-power.json > results.sha256
sha256sum -c results.sha256
