#!/usr/bin/env bash
#SBATCH --job-name=mdt-280lcfetch
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
    sha256sum --quiet -c inputs.sha256
    set +u
    source /public3/soft/modules/module.sh
    module load singularity/3.7.0
    set -u
    exec srun --ntasks=1 --cpus-per-task="$SLURM_CPUS_PER_TASK" --cpu-bind=cores \
        singularity exec --cleanenv --bind "$(dirname "$bundle")" "$HOME/LLMHardware/opt/orfs-current-repacked.rootfs" \
        bash "$bundle/run_bscc_t6_qwen3_lc_fetch_power.sbatch" inside "$bundle" "$SLURM_JOB_ID" \
        "$SLURM_CPUS_PER_TASK" "${1:-400}" "${2:-0}"
fi

source /OpenROAD-flow-scripts/env.sh
bundle=$2
root=$(dirname "$bundle")
out=$bundle/fetch-$3
cores=$4
side=$5
buffer_limit=$6
[[ $side =~ ^[1-9][0-9]{2}$ && $buffer_limit =~ ^(0|[1-9][0-9]?)$ ]]
product=$root/m-product/wide-38792112
rtl=$product/source/project/experiments/shared_x_control/rtl/lc_scope_fetch128.sv
controller=$product/source/project/experiments/shared_x_control/rtl/lc_native_scope_controller.sv
replay=$product/replay-38792112
helper=$root/writer-power/frozen
activity=$root/control-activity/activity-38796363/control-activity.json
mkdir "$out"
(cd "$replay" && sha256sum --quiet -c wide-results.sha256)
(cd "$(dirname "$activity")" && sha256sum --quiet -c results.sha256)
grep -Eq 'lc_scope_fetch128[[:space:]]+scope_fetch[[:space:]]*\(' "$controller"
sha256sum "$rtl" "$controller" "$root/write-span/target.sdc" "$activity" "$replay/wide-results.sha256" \
    "$helper"/{fst_scope_vcd,gate_power_300.py,extract_c639_m_ports.py} "$(command -v openroad)" > "$out/source.sha256"
cat > "$out/config.mk" <<EOF
export PLATFORM = nangate45
export DESIGN_NAME = lc_scope_fetch128
export SYNTH_HDL_FRONTEND = slang
export VERILOG_FILES = $rtl
export SDC_FILE = $root/write-span/target.sdc
export DIE_AREA = 0 0 $side $side
export CORE_AREA = 10 10 $((side-10)) $((side-10))
export PLACE_DENSITY = 0.55
EOF
if (( buffer_limit > 0 )); then
    cat > "$out/hold-buffer-cap.tcl" <<EOF
rename repair_timing fetch_design_repair_timing
proc repair_timing {args} {
  tailcall fetch_design_repair_timing {*}\$args -max_buffer_percent $buffer_limit
}
EOF
    printf 'export PRE_CTS_TCL = %s\n' "$out/hold-buffer-cap.tcl" >> "$out/config.mk"
    printf 'export PRE_GLOBAL_ROUTE_TCL = %s\n' "$out/hold-buffer-cap.tcl" >> "$out/config.mk"
    sha256sum "$out/hold-buffer-cap.tcl" >> "$out/source.sha256"
fi
make -C /OpenROAD-flow-scripts/flow DESIGN_CONFIG="$out/config.mk" WORK_HOME="$out/flow" \
    NUM_CORES="$cores" finish > "$out/flow.log" 2>&1
key=nangate45/lc_scope_fetch128/base
netlist=$out/flow/results/$key
timing=$out/flow/logs/$key/6_report.json
drc=$out/flow/reports/$key/5_route_drc.rpt
export PYTHONPATH=$helper
python3 -B - "$replay" "$helper" "$activity" "$netlist" "$timing" "$drc" "$out" "$cores" <<'PY'
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import subprocess
import sys

from extract_c639_m_ports import extract
from gate_power_300 import analyze

replay, helper, boundary, netlist, report, drc, out = map(Path, sys.argv[1:8])
threads = int(sys.argv[8]) // 3
timing = json.loads(report.read_bytes())
setup = timing['finish__timing__setup__ws']
hold = timing['finish__timing__hold__ws']
if min(setup, hold) < 0 or drc.stat().st_size:
    raise ValueError('routed fetch timing or detailed-route DRC failed')
scopes = json.loads(boundary.read_bytes())['scopes']
events = ('start', 'fetch', 'mc_req', 'mc_rsp', 'mc_close')

def count(path):
    required = {'clk'} | {event + '_' + suffix for event in events for suffix in ('valid', 'ready')}
    counts = dict((event, 0) for event in events)
    names, previous, changes = {}, {}, {}

    def flush():
        if previous.get('clk') == '0' and changes.get('clk') == '1':
            for event in events:
                counts[event] += previous[event + '_valid'] == previous[event + '_ready'] == '1'
            value = 1
        else:
            value = 0
        previous.update(changes)
        changes.clear()
        return value

    cycles = 0
    with path.open() as stream:
        for line in stream:
            fields = line.split()
            if fields[:1] == ['$var'] and fields[4] in required:
                if fields[2] != '1':
                    raise ValueError('handshake is not scalar')
                names.setdefault(fields[3], []).append(fields[4])
            elif fields[:1] == ['$enddefinitions']:
                break
        if {n for group in names.values() for n in group} != required:
            raise ValueError('required fetch handshake absent')
        for line in stream:
            if line.startswith('#'):
                cycles += flush()
            elif line[:1] in ('0', '1'):
                for name in names.get(line[1:].strip(), ()):
                    changes[name] = line[0]
        cycles += flush()
    if cycles != 8192:
        raise ValueError('unexpected C639 window cycles')
    return counts


def measure(item):
    mode, phase, site = item
    name = 'mode-{}-{}-site{}'.format(mode, phase, site)
    directory = out / name
    directory.mkdir()
    wave = replay / 'DDR-{}'.format(mode) / 'ffn-{}.fst'.format(phase)
    with wave.with_name(wave.stem + '-signals.tsv').open() as signals:
        row, first, last, precision = next(signals).split()
    first, last = int(first), int(last)
    if row != 'time' or precision != '-12' or last - first != 81920000:
        raise ValueError('unexpected C639 time range')
    scope = scopes['local_controller_{}'.format(site)] + '/scope_fetch'
    raw, port = directory / 'raw.vcd', directory / 'ports.vcd'
    with (directory / 'extract.log').open('w') as log:
        subprocess.run([str(helper / 'fst_scope_vcd'), str(wave), str(raw), scope], stdout=log, check=True)
    extract(netlist / '6_final.v', raw, port, scope, first, last, 100, None)
    raw.unlink()
    ports = json.loads(port.with_suffix('.json').read_bytes())
    transactions = count(port)
    power = analyze(port, netlist, 'dut', directory / 'power', 10000, 0, last - first, threads,
                    reference_annotations=sum(ports['port_bits'].values()))
    return name, {'transactions': transactions, 'power_w': power['power_w'], 'annotated': power['annotated']}


cases = [(mode, phase, site) for mode in (0, 1) for phase in ('gate-up', 'down', 'writer-active') for site in range(4)]
with ThreadPoolExecutor(max_workers=3) as pool:
    result = dict(pool.map(measure, cases))
if not any(r['transactions']['fetch'] for r in result.values()):
    raise ValueError('no completed descriptor fetch in the representative windows')
(out / 'lc-fetch-power.json').write_text(json.dumps({'target_clock_mhz': 300, 'setup_ns': setup, 'hold_ns': hold,
    'scope': 'lc_scope_fetch128 descriptor registers and control only', 'windows': result}, indent=2) + '\n')
PY
cd "$out"
sha256sum "$bundle/inputs.sha256" source.sha256 config.mk "$netlist"/6_final.{v,odb,sdc,spef} "$timing" "$drc" \
    lc-fetch-power.json mode-*/ports.{vcd,json} mode-*/power/receipt.json > results.sha256
sha256sum -c results.sha256
