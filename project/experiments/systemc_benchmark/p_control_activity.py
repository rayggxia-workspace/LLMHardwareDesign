"""Observe an accepted P_64 LC/native-M/feeder/store integration fixture.

Only testbench observation, runtime window, idle branch and clock change.
The parent gate netlist and independent functional leaf RTL stay untouched.
The bank uses the existing explicitly zero-delay activity view; arbitrary
OpenRAM delay/X decoration is not a characterized300MHz timing model.
This is component calibration, not full-model timing or total chip energy.
"""
import argparse
import hashlib
import json
from pathlib import Path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def generate(accepted, receipt, bank_source, output):
    from s_functional_bank import create
    evidence = json.loads(receipt.read_text())
    if evidence['archive_sha256'] != '13545e6ee575512edac07aebe553bf5d6c8666ccec3b040afde581cd4f35c390':
        raise ValueError('unexpected P64 acceptance')
    output.mkdir(exist_ok=False)
    for name, row in evidence['selected_files'].items():
        if sha(accepted/name) != row['sha256']:
            raise ValueError('accepted input drift: '+name)
    original = accepted/'gate/normal/design/tb_native_pair.sv'
    text = original.read_text()
    changes = {
        'module tb_native_pair #(parameter integer SINGLE_KIND=-1);': '''module tb_native_pair #(parameter integer SINGLE_KIND=-1)(
 output wire benchmark_runtime,output wire [31:0] benchmark_cycle);
 reg activity_runtime=0;
 integer activity_idle_cycles=0,activity_phase=0;
 assign benchmark_runtime=activity_runtime;
 assign benchmark_cycle=cycle;''',
        'always #5 clk_i=~clk_i;': '''always begin
 if(activity_phase==2) #1.666; else #1.667;
 clk_i=~clk_i;activity_phase=(activity_phase+1)%3;
 end''',
        '        start_job_i=7;': '''        activity_runtime=1;
        if($value$plusargs("ACTIVITY_IDLE_CYCLES=%d",activity_idle_cycles) && activity_idle_cycles>0) begin
            repeat(activity_idle_cycles) @(negedge clk_i);
            activity_runtime=0;
            $display("PASS native deployed idle");
            $finish;
        end
        start_job_i=7;''',
        '        @(negedge clk_i); result_ready_i=0;': '''        @(negedge clk_i); result_ready_i=0;
        activity_runtime=0;'''}
    for old, new in changes.items():
        if text.count(old) != 1:
            raise ValueError('unexpected fixture patch location')
        text = text.replace(old, new)
    target = output/'tb_native_pair.sv'
    target.write_text(text)
    bank = create(bank_source, output/'sram-functional.v')
    result = {'scope': __doc__, 'accepted_receipt_sha256': sha(receipt),
        'original_tb_sha256': sha(original), 'instrumented_tb_sha256': sha(target),
        'changes': changes, 'hardware_modified': False,
        'zero_delay_activity_bank': bank,
        'parent_netlist_sha256': sha(accepted/'native/6_final.v'),
        'parent_RTL_sha256': sha(accepted/'gate/normal/lc/pu_p_controlled_64.sv')}
    (output/'generation.json').write_text(json.dumps(result, indent=2)+'\n')


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    for name in ('accepted', 'receipt', 'output'):
        p.add_argument(name, type=Path)
    p.add_argument('--bank-source', type=Path, required=True)
    a = p.parse_args()
    generate(a.accepted, a.receipt, a.bank_source, a.output)
