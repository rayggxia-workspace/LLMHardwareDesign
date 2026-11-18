#!/usr/bin/env bash
#SBATCH --job-name=mdt-280mccontrol
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
        bash "$bundle/run_bscc_t6_qwen3_mother_control_power.sbatch" inside "$bundle" "$SLURM_JOB_ID" "$SLURM_CPUS_PER_TASK"
fi

source /OpenROAD-flow-scripts/env.sh
bundle=$2
root=$(dirname "$bundle")
out=$bundle/mc-$3
incoming=$root/incoming/macro-views
netlist=$incoming/mother128/physical
bank=$incoming/source/issue-155/bank-views-011/generation/bank/s_sram_256x128_freepdk45_TT_1p1V_25C.lib
product=$root/m-product/wide-38792112
replay=$product/replay-38792112
rtl=$product/source/project/rtl
helper=$root/writer-power/frozen
activity=$root/control-activity/activity-38796363/control-activity.json
mkdir "$out"
(cd "$incoming/mother128" && sha256sum --quiet -c ../mother-subset.sha256)
(cd "$incoming/source" && sha256sum --quiet -c ../source-files.sha256)
(cd "$replay" && sha256sum --quiet -c wide-results.sha256)
(cd "$(dirname "$activity")" && sha256sum --quiet -c results.sha256)
printf '%s  %s\n' \
  2c50b01717220c27c41a884613c1a980da4f550719d05b27e865ceb28ac52c5b "$rtl/mother_control_v1/mother_control_64.sv" \
  a1ba89671305fd76f99e1b0c2a6fdadcbc73c783a0383c2b9640b496577317ef "$rtl/s_sram/block_feed_s16k_sram.sv" \
  > "$out/binding.sha256"
sha256sum -c "$out/binding.sha256"
export PYTHONPATH=$out:$helper
python3 -B - "$replay" "$helper" "$activity" "$netlist" "$bank" "$out" "$4" <<'PY'
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import re
import subprocess
import sys

from extract_c639_m_ports import extract

replay, helper, activity, netlist, bank, out = map(Path, sys.argv[1:7])
threads = int(sys.argv[7]) // 3
scope = json.loads(activity.read_bytes())['scopes']['mother_core'].rsplit('/', 1)[0]
pm = scope + '/program_store'
gate_source = (helper / 'gate_power_300.py').read_text()
clock = 'fields[4] == "clk"'
if gate_source.count(clock) != 1:
    raise ValueError('unexpected original clock normalization')
(out / 'gate_power_clk_i.py').write_text(gate_source.replace(clock, 'fields[4] == "clk_i"'))
from gate_power_clk_i import analyze


def pm_counts(path):
    wanted = {'clk_i', 'rst_ni', 'req_valid_i', 'req_ready_o', 'req_write_i', 'rsp_valid_o', 'rsp_ready_i', 'rsp_error_o'}
    counts = dict(cycles=0, reads=0, writes=0, returns=0, errors=0)
    stack, codes, states, changes = [], {}, {}, {}

    def flush():
        if states.get('clk_i') == 0 and changes.get('clk_i') == 1:
            if set(states) != wanted or states['rst_ni'] != 1:
                raise ValueError('missing mother PM activity or active reset')
            counts['cycles'] += 1
            request = states['req_valid_i'] and states['req_ready_o']
            counts['writes'] += request and states['req_write_i']
            counts['reads'] += request and not states['req_write_i']
            response = states['rsp_valid_o'] and states['rsp_ready_i']
            counts['returns'] += response
            counts['errors'] += response and states['rsp_error_o']
        states.update(changes)
        changes.clear()

    with path.open() as stream:
        for row in stream:
            fields = row.split()
            if fields[:1] == ['$scope']:
                stack.append(fields[2])
            elif fields[:1] == ['$upscope']:
                stack.pop()
            elif fields[:1] == ['$var'] and '/'.join(stack) == pm and fields[4] in wanted:
                codes.setdefault(fields[3], []).append(fields[4])
            elif fields[:1] == ['$enddefinitions']:
                break
        for row in stream:
            if row.startswith('#'):
                flush()
            elif row[:1] in ('0', '1'):
                for name in codes.get(row[1:].strip(), ()):
                    changes[name] = int(row[0])
        flush()
    if counts['cycles'] != 8192 or counts['errors']:
        raise ValueError('invalid mother PM sample counts: {}'.format(counts))
    return counts


def one(item):
    mode, phase = item
    name = 'mode-{}-{}'.format(mode, phase)
    wave = replay / 'DDR-{}'.format(mode) / ('ffn-' + phase + '.fst')
    with wave.with_name(wave.stem + '-signals.tsv').open() as stream:
        label, first, last, resolution = next(stream).split()
    first, last = int(first), int(last)
    if label != 'time' or resolution != '-12' or last - first != 81920000:
        raise ValueError('unexpected waveform bounds')
    folder = out / name
    folder.mkdir()
    raw, normalized, pm_raw = folder / 'mother.vcd', folder / 'ports.vcd', folder / 'pm.vcd'
    with (folder / 'extract.log').open('w') as log:
        subprocess.run([str(helper / 'fst_scope_vcd'), str(wave), str(raw), scope], stdout=log, check=True)
        subprocess.run([str(helper / 'fst_scope_vcd'), str(wave), str(pm_raw), pm], stdout=log, check=True)
    counts = pm_counts(pm_raw)
    extract(netlist / '6_final.v', raw, normalized, scope, first, last, 100, None)
    raw.unlink()
    pm_raw.unlink()
    ports = json.loads(normalized.with_suffix('.json').read_bytes())
    data = analyze(normalized, netlist, 'dut', folder / 'power', 10000, 0, last - first, threads,
                   libs=(bank,), reference_annotations=sum(ports['port_bits'].values()))
    report = (folder / 'power' / 'power.log').read_text()
    found = re.search(r'(?m)^Macro\s+(?:[\d.eE+-]+\s+){3}([\d.eE+-]+)', report)
    if not found or float(found[1]) <= 0 or data['power_w']['total'] <= float(found[1]):
        raise ValueError('SRAM Macro category missing or inconsistent')
    return name, {'mother_pm': counts, 'mother_total_w': data['power_w']['total'],
                  'mother_macro_group_w': float(found[1]),
                  'mother_excluding_macro_group_w': data['power_w']['total'] - float(found[1]),
                  'annotated': data['annotated']}


with ThreadPoolExecutor(max_workers=3) as pool:
    windows = dict(pool.map(one, [(m, p) for m in (0, 1) for p in ('gate-up', 'down', 'writer-active')]))
(out / 'mother-control-power.json').write_text(json.dumps({'clock_mhz': 300,
    'scope': 'cohort/mother/mother on restored #223 mother_control_64 routing',
    'scope_exclusion': 'The shell estimate subtracts the Macro report group. PM bridge, other switch modules, and system clock interconnect are separate.',
    'windows': windows}, indent=2) + '\n')
PY
cd "$out"
sha256sum "$bundle/inputs.sha256" "$incoming/mother-subset.sha256" "$incoming/source-files.sha256" "$helper/gate_power_300.py" \
    "$activity" "$replay/wide-results.sha256" binding.sha256 gate_power_clk_i.py mother-control-power.json \
    mode-*/ports.{vcd,json} mode-*/power/receipt.json > results.sha256
sha256sum -c results.sha256
