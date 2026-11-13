"""Generate a runtime-window mother fixture from the accepted public-port test.

Only testbench clock, observation ports and an idle branch change. Functional
RTL, accepted gate netlist, original libraries and RC remain unchanged. Finite
peer delays are fixture controls, never a complete Qwen timing/energy model.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def generate(accepted, output):
    manifest = json.loads((accepted/'manifest.json').read_text())
    if not manifest['passed'] or manifest['resident_targets'] != 2:
        raise ValueError('unexpected mother acceptance scope')
    sources = ['physical/6_final.'+s for s in ('v', 'odb', 'sdc', 'spef')]
    sources += ['gate/cells.sv', 'execution-source/source-25.tar.gz',
        'bank-dependency/s_sram_256x128_freepdk45.v',
        'bank-dependency/s_sram_256x128_freepdk45_TT_1p1V_25C.lib']
    for name in sources:
        if sha(accepted/name) != manifest['files_sha256'][name]:
            raise ValueError('accepted source drift: '+name)
    output.mkdir(exist_ok=False)
    with tarfile.open(accepted/'execution-source/source-25.tar.gz') as archive:
        selected = [m for m in archive.getmembers() if m.isfile() and (
            m.name.startswith('project/rtl/mother_control_v1/') or
            m.name == 'project/rtl/s_sram/block_feed_s16k_sram.sv' or
            m.name in ['project/experiments/mother_control_v1/'+n for n in
                       ('tb_mother.sv', 'tb_wires.svh', 'tb_init.svh')])]
        for member in selected:
            if member.issym() or member.islnk() or '..' in Path(member.name).parts:
                raise ValueError('unsafe source path')
            target = output/member.name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(archive.extractfile(member).read())
    bench = output/'project/experiments/mother_control_v1/tb_mother.sv'
    if sha(bench) != 'f089eeb7e6c85e64809b528427347f16ab2dd5a345fcc447ac0d90eef45ff0a8':
        raise ValueError('accepted public-port test source changed')
    text = bench.read_text()
    changes = {
        'module tb_mother;': '''module tb_mother(output wire benchmark_runtime,
 output wire [31:0] benchmark_cycle,benchmark_calls,benchmark_results);
 assign benchmark_runtime=runtime_active;
 assign benchmark_cycle=cycle;
 assign benchmark_calls=calls;
 assign benchmark_results=returns;
 integer activity_idle_cycles=0,activity_clock_phase=0;''',
        'always #5 clk_i=~clk_i;': '''always begin
  if(activity_clock_phase==2) #1.666; else #1.667;
  clk_i=~clk_i;activity_clock_phase=(activity_clock_phase+1)%3;
 end''',
        '    runtime_active=1;': '''    runtime_active=1;
    n=$value$plusargs("ACTIVITY_IDLE_CYCLES=%d",activity_idle_cycles);
    if(activity_idle_cycles!=0) begin
      repeat(activity_idle_cycles) @(negedge clk_i);
      $display("PASS mother activity idle, program remains deployed");
      $finish;disable scenario;
    end'''}
    for old, new in changes.items():
        if text.count(old) != 1:
            raise ValueError('unexpected benchmark patch location')
        text = text.replace(old, new)
    bench.write_text(text)
    receipt = {'scope': __doc__, 'accepted_manifest_sha256': sha(accepted/'manifest.json'),
        'accepted_files_sha256': {n: sha(accepted/n) for n in sources},
        'original_tb_sha256': 'f089eeb7e6c85e64809b528427347f16ab2dd5a345fcc447ac0d90eef45ff0a8',
        'instrumented_tb_sha256': sha(bench), 'testbench_changes': changes,
        'functional_hardware_modified': False, 'timing_qualified': False,
        'system_energy_qualified': False}
    (output/'generation.json').write_text(json.dumps(receipt, indent=2)+'\n')
    return receipt


def main():
    p = argparse.ArgumentParser()
    for name in ('accepted', 'output'):
        p.add_argument(name, type=Path)
    a = p.parse_args()
    print(json.dumps(generate(a.accepted, a.output)))


if __name__ == '__main__':
    main()
