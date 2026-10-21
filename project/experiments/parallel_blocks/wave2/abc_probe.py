"""Minimal ABC completion-protocol probe; no wall-clock deadline."""
import json
import os
from pathlib import Path
import subprocess

spec = json.loads(Path('task.json').read_text())
short = spec['name'].endswith('short')
Path('toy.v').write_text('module toy(input [15:0] a,b, output [15:0] c); assign c=a+b; endmodule\n')
lib = '/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib'
Path('probe.ys').write_text('read_verilog toy.v\nsynth -top toy -noabc\nabc -liberty ' + lib +
    ' -script /OpenROAD-flow-scripts/flow/scripts/abc_speed.script\ncheck -assert\nwrite_json mapped.json\n')
env = dict(os.environ)
if short:
    env.pop('TMPDIR', None)
Path('probe-input.json').write_text(json.dumps(dict(short_default_temporary_directory=short,
    TMPDIR=env.get('TMPDIR'), deadline=None, note='Same toy, library, script and binary; only TMPDIR changes'), indent=2)+'\n')
with Path('probe.log').open('w') as log:
    code = subprocess.run(['yosys', '-Q', '-T', '-s', 'probe.ys'], env=env, stdout=log, stderr=subprocess.STDOUT).returncode
Path('validation.json').write_text(json.dumps(dict(passed=code==0 and Path('mapped.json').is_file(),
    kind='Minimal ABC protocol probe', short_default_temporary_directory=short, exit_code=code), indent=2)+'\n')
raise SystemExit(code)
