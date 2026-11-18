#!/usr/bin/env bash
#SBATCH --job-name=mdt-280mcmp
#SBATCH --partition=c64,c96
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --time=00:15:00
#SBATCH --output=slurm-%j.log
set -euo pipefail
base=/public/home/yuzelu
bundle=${SLURM_SUBMIT_DIR:?}
cd "$bundle"
if [[ ${1:-} != container ]]; then
    sha256sum -c bundle.sha256
    exec srun --exact -n1 -c "$SLURM_CPUS_PER_TASK" --cpu-bind=cores \
      /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind "$base" \
      --env "SLURM_SUBMIT_DIR=$bundle" "$base/opt/eda/containers/orfs-current-repacked.sif" \
      bash "$bundle/run_c639_m_contract.sbatch" container "$SLURM_JOB_ID" "$SLURM_CPUS_PER_TASK"
fi
out=$bundle/contract-$2
cores=$3
run=$base/Melodydt/runs/issue-280/c639-g32-gate-01/c639-g32-116937
old=$base/project-circuit/issue250-m-physical-20261111-60
rtl=project/rtl/w8a16_v1
vlt=$base/opt/eda/verilator-5.042/bin/verilator
mkdir "$out"
(cd "$run" && sha256sum --quiet -c gate-results.sha256)
(cd "$old" && grep -E 'project/rtl/w8a16_v1/(m_native_leaf_s32|m_native_s32|weight_records|m_group_s32|projection_context_s32|scale_group_s32)\.sv$' source.sha256 | sha256sum -c -)
sha256sum "$old/tasks/delivery/delivery.json" "$old/tasks/delivery/6_final.v" "$vlt" > "$out/tools-inputs.sha256"
"$vlt" --version > "$out/verilator.txt"

python3 -B - "$out" "$old" "$run" "$rtl" <<'PY'
from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess
import sys

out, old, run, rtl = map(Path, sys.argv[1:])
files = ('m_native_leaf_s32', 'm_native_s32', 'weight_records', 'm_group_s32', 'projection_context_s32', 'scale_group_s32')
delivery = json.loads((old / 'tasks/delivery/delivery.json').read_text())
if not delivery['passed'] or not delivery['native_leaf_accepted']:
    raise ValueError('expected qualified M60 route provenance')
signal = delivery['final_files']['6_final.v']
if signal['sha256'] != (out / 'tools-inputs.sha256').read_text().splitlines()[1].split()[0]:
    raise ValueError('delivered M60 signal netlist differs from the physical receipt')

def ports(path):
    text = path.read_text().split(');', 1)[0].split(')(', 1)[-1]
    entries = re.sub(r'//[^\n]*', '', text).split(',')
    result = {}
    direction = width = None
    for entry in entries:
        entry = entry.strip()
        match = re.fullmatch(r'(input|output)\s+(?:wire|reg)\s*(\[[^]]+\])?\s*(\w+)', entry)
        if match:
            direction, width, name = match.groups()
        elif re.fullmatch(r'\w+', entry) and direction:
            name = entry
        else:
            raise ValueError(entry)
        result[name] = (direction, (width or '').replace('KEY_W-1', '127'))
    return result

evidence = {}
for file in files:
    a, b = [path / 'source' / rtl / (file + '.sv') for path in (old, run)]
    diff = subprocess.run(['diff', '-u', str(a), str(b)], stdout=subprocess.PIPE, check=False)
    if diff.returncode not in (0, 1):
        raise ValueError(file)
    (out / (file + '.diff')).write_bytes(diff.stdout)
    evidence[file] = {'m60': sha256(a.read_bytes()).hexdigest(), 'c639': sha256(b.read_bytes()).hexdigest(), 'same': diff.returncode == 0}
(out / 'sources.json').write_text(json.dumps({'m60_signal_netlist': signal, 'rtl': evidence}, indent=2) + '\n')

current = run / 'source' / rtl / 'weight_records.sv'
previous = old / 'source' / rtl / 'weight_records.sv'
interface = ports(current)
if interface != ports(previous):
    raise ValueError('weight_records interface changed')
controls = {
    'clk': 'clk', 'reset': 'reset', 'alloc_valid': 'alloc_valid', 'alloc_key': 'alloc_key',
    'alloc_record': 'alloc_record', 'alloc_n': "4'd4", 'alloc_ack_ready': "1'b1",
    'issue_valid': 'issue_valid', 'issue_generation': 'generation', 'issue_key': "128'd11",
    'issue_record': "32'd21", 'issue_beat': 'beat', 'fill_valid': 'fill_valid',
    'fill_generation': 'generation', 'fill_key': "128'd11", 'fill_record': "32'd21",
    'fill_beat': 'beat', 'fill_last': "beat == 5'd16", 'fill_data': "beat == 5'd16 ? 512'h3c003c003c003c00 : 512'b0",
    'fill_ack_ready': "1'b1",
    'start_valid': 'start_valid', 'start_generation': 'generation', 'start_key': "128'd11",
    'start_record': "32'd21", 'start_use': "16'd1", 'fault_ready': "1'b1",
}
observe = {'alloc_ready', 'alloc_ack_valid', 'alloc_ack_error', 'alloc_ack_bank', 'alloc_ack_generation',
           'issue_ready', 'fill_ready', 'fill_ack_valid', 'fill_ack_error', 'start_ready', 'start_accepted',
           'ready_mask', 'free_mask', 'fault_valid'}
if not set(controls) | observe <= set(interface):
    raise ValueError('missing testbench ports')
for name, path in [('m60', previous), ('c639', current)]:
    raw = path.read_text()
    if raw.count('module weight_records #(') != 1:
        raise ValueError('unexpected weight_records declaration')
    (out / (name + '.sv')).write_text(raw.replace('module weight_records #(', f'module {name} #('))
    connections = []
    nets = []
    for port, (direction, width) in interface.items():
        if direction == 'input':
            value = controls.get(port, "'0")
        elif port in observe:
            value = f'{name}_{port}'
            nets.append(f'wire {width} {value};')
        else:
            value = ''
        connections.append(f'.{port}({value})')
    nets.append(f'{name} {name}_dut(' + ',\n'.join(connections) + ');')
    (out / (name + '.svh')).write_text('\n'.join(nets) + '\n')
PY

cat > "$out/test_m_contract.sv" <<'SV'
`timescale 1ns/1ps
module test_m_contract;
  bit clk = 0, reset = 1;
  always #5 clk = ~clk;
  bit alloc_valid, start_valid, issue_valid, fill_valid;
  logic [127:0] alloc_key = 128'd11;
  logic [31:0] alloc_record = 32'd21;
  logic [4:0] beat = 0;
  logic [15:0] generation;
  `include "m60.svh"
  `include "c639.svh"

  initial begin
    repeat (2) @(negedge clk);
    reset = 0;
    alloc_valid = 1;
    #1;
    if (!m60_alloc_ready || !c639_alloc_ready) $fatal(1, "first ALLOC was not ready");
    @(posedge clk);
    #1;
    alloc_valid = 0;
    if (!(m60_alloc_ack_valid && c639_alloc_ack_valid) || m60_alloc_ack_error || c639_alloc_ack_error ||
        m60_alloc_ack_bank != 0 || c639_alloc_ack_bank != 0 || m60_alloc_ack_generation != c639_alloc_ack_generation)
      $fatal(1, "first allocation mismatch");
    generation = m60_alloc_ack_generation;
    for (int i = 0; i < 17; ++i) begin
      @(negedge clk);
      beat = 5'(i);
      issue_valid = 1;
      #1;
      if (!m60_issue_ready || !c639_issue_ready) $fatal(1, "issue not accepted");
      @(negedge clk);
      issue_valid = 0;
      fill_valid = 1;
      #1;
      if (!m60_fill_ready || !c639_fill_ready) $fatal(1, "fill not accepted");
      @(posedge clk);
      #1;
      fill_valid = 0;
      if (m60_fault_valid || c639_fault_valid) $fatal(1, "bad fill record");
    end
    wait (m60_fill_ack_valid && c639_fill_ack_valid);
    if (m60_fill_ack_error || c639_fill_ack_error) $fatal(1, "weight record rejected");
    wait (m60_ready_mask[0] && c639_ready_mask[0]);
    @(negedge clk);
    start_valid = 1;
    alloc_valid = 1;
    alloc_key = 128'd12;
    alloc_record = 32'd22;
    #1;
    if (!(m60_start_ready && c639_start_ready && m60_start_accepted && c639_start_accepted))
      $fatal(1, "START of the ready record was not accepted by both");
    if (!m60_alloc_ready || c639_alloc_ready) $fatal(1, "expected same-edge ALLOC readiness difference");
    @(posedge clk);
    #1;
    if (!m60_alloc_ack_valid || m60_alloc_ack_error || m60_alloc_ack_bank != 1 || c639_alloc_ack_valid ||
        m60_fault_valid || c639_fault_valid || m60_free_mask[1] || !c639_free_mask[1])
      $fatal(1, "expected successful simultaneous allocation only on M60");
    $display("M60_C639_WEIGHT_CONTRACT_DIFF start_accepted=1/1 alloc_accepted=1/0 free_bank1=0/1");
    $finish;
  end
  initial begin
    #2000;
    $fatal(1, "weight contract watchdog");
  end
endmodule
SV
"$vlt" --binary --timing --assert --top-module test_m_contract -Wno-TIMESCALEMOD \
    -I"$out" -j "$cores" --Mdir "$out/obj" "$out/"{m60,c639,test_m_contract}.sv > "$out/build.log" 2>&1
"$out/obj/Vtest_m_contract" > "$out/run.log" 2>&1
grep '^M60_C639_WEIGHT_CONTRACT_DIFF ' "$out/run.log"
sha256sum "$out/"{*.sv,*.svh,*.diff,verilator.txt,tools-inputs.sha256,sources.json,run.log} > "$out/contract-results.sha256"
sha256sum -c "$out/contract-results.sha256"
