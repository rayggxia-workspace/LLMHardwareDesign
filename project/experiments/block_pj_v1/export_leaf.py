"""Derive parent-facing trial views from exact independently accepted leaves."""
import hashlib
import json
import re
from pathlib import Path
import subprocess
import sys
import tarfile

repo, root = (Path(p) for p in sys.argv[1:3])
name = sys.argv[3]
view = root / 'views' / name
view.mkdir()
standard = Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib')
bank = Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-155/bank-views-011/generation/bank/s_sram_256x128_freepdk45_TT_1p1V_25C.lib')


def digest(path):
    with Path(path).open('rb') as stream:
        h = hashlib.sha256()
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            h.update(chunk)
        return h.hexdigest()


def tcl(command, path):
    return f'{command} {{{path}}}\n'


if name in ('p4', 'n4'):
    leaves = json.loads((Path(__file__).parent / 'sram-inputs.json').read_text())
    directory = root / 'inputs' / name
    expected = leaves[name]
    libraries = [standard, bank]
    assert digest(bank) == leaves['bank_liberty_sha256']
else:
    index = json.loads((repo / 'work/YUZE-LU/143/release-six/index.json').read_text())['macros'][name]
    assert index['qualified']
    archive = Path(index['archive']['path'])
    assert digest(archive) == index['archive']['sha256'], archive
    expected = {n: v['sha256'] for n, v in index['final_files'].items()}
    directory = root / 'inputs' / name
    directory.mkdir()
    with tarfile.open(archive) as tar:
        members = {Path(m.name).name: m for m in tar if '/native/' in '/' + m.name and m.isfile()}
        for filename in expected:
            with tar.extractfile(members[filename]) as source, (directory / filename).open('wb') as dest:
                for chunk in iter(lambda: source.read(8 * 1024 * 1024), b''):
                    dest.write(chunk)
    libraries = [standard]

for filename, sha in expected.items():
    assert digest(directory / filename) == sha, (name, filename)
script = ''.join(tcl('read_liberty', lib) for lib in libraries)
for ext, command in [('odb', 'read_db'), ('sdc', 'read_sdc'), ('spef', 'read_spef')]:
    script += tcl(command, directory / f'6_final.{ext}')
script += 'set_propagated_clock [all_clocks]\nset_clock_latency -source 0 [all_clocks]\n'
script += tcl('write_timing_model', view / 'leaf.lib')
script += tcl('write_abstract_lef -bloat_factor 0', view / 'leaf.lef')
script += tcl('report_check_types -max_slew -max_capacitance -min_pulse_width -violators >', view / 'leaf-electrical.rpt')
script += 'report_worst_slack -max\nreport_worst_slack -min\n'
(view / 'export.tcl').write_text(script)
with (view / 'openroad.log').open('w') as log:
    subprocess.run(['openroad', '-threads', '4', '-exit', str(view / 'export.tcl')],
                   stdout=log, stderr=subprocess.STDOUT, check=True)
lef = (view / 'leaf.lef').read_text()
lib = (view / 'leaf.lib').read_text()
master, = re.findall(r'^MACRO (\S+)', lef, re.MULTILINE)
pins = re.findall(r'^\s+PIN (\S+)', lef, re.MULTILINE)
assert len(set(pins)) == len(pins) and len(pins) > 2
assert re.search(r'cell\s*\(\s*"?' + re.escape(master) + r'"?\s*\)', lib), master
receipt = dict(master=master, pins=len(pins), source=str(directory), source_sha256=expected,
               library_sha256={str(p): digest(p) for p in libraries},
               outputs={p.name: digest(p) for p in view.iterdir()},
               timing_view_scope='Derived for trial assembly; parent and hierarchical arc checks pending')
(view / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
