"""C stream: new views of old results, explicitly retaining their failed electrical status."""
import hashlib
import json
from pathlib import Path
import re
import subprocess

root = Path.cwd()
baseline = Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-7/parallel-blocks-01')
platform = Path('/OpenROAD-flow-scripts/flow/platforms/nangate45')
standard = list((platform / 'lib').glob('*typical.lib*'))
assert len(standard) == 1, standard
views = {}
inputs = []
for case in ('opentpu-act', 'opentpu-mxu', 'opentpu-act-mxu'):
    old = baseline / case
    result = old / 'flow/results/nangate45' / ('parallel_' + case.replace('-', '_')) / 'base'
    destination = root / 'views' / case
    destination.mkdir(parents=True)
    script = 'read_liberty {' + str(standard[0]) + '}\n'
    for lib in sorted((old / 'memory-model/macros').glob('*.lib')):
        script += 'read_liberty {' + str(lib) + '}\n'
    for suffix, command in [('odb', 'read_db'), ('sdc', 'read_sdc'), ('spef', 'read_spef')]:
        p = result / ('6_final.' + suffix)
        assert p.is_file(), p
        inputs.append(p)
        script += command + ' {' + str(p) + '}\n'
    script += 'set_propagated_clock [all_clocks]\nset_clock_latency -source 0 [all_clocks]\n'
    script += 'write_timing_model {' + str(destination / 'original.lib') + '}\n'
    script += 'write_abstract_lef -bloat_factor 0 {' + str(destination / 'original.lef') + '}\n'
    tcl = destination / 'export.tcl'
    tcl.write_text(script)
    with (destination / 'export.log').open('w') as log:
        subprocess.run(['openroad', '-exit', str(tcl)], stdout=log, stderr=subprocess.STDOUT, check=True)
    alias = 'llhd_baseline_' + case.replace('-', '_')
    for suffix in ('lib', 'lef'):
        text = (destination / ('original.' + suffix)).read_text()
        assert 'otpu_asic_top' in text
        text = re.sub(r'(?<![A-Za-z0-9_$])otpu_asic_top(?![A-Za-z0-9_$])', alias, text)
        (destination / (alias + '.' + suffix)).write_text(text)
    ports = json.loads((old / 'elab.json').read_text())['modules']['otpu_asic_top']['ports']
    expected = set()
    for name, p in ports.items():
        if len(p['bits']) == 1:
            expected.add(name)
        else:
            expected.update(name + '[' + str(i + p.get('offset', 0)) + ']' for i in range(len(p['bits'])))
    pins = set()
    dimensions = None
    with (destination / (alias + '.lef')).open() as f:
        for line in f:
            match = re.match(r'\s*PIN\s+(\S+)', line)
            if match:
                pins.add(match[1].strip('"').replace('\\', ''))
            match = re.match(r'\s*SIZE\s+([\d.]+)\s+BY\s+([\d.]+)', line)
            if match:
                dimensions = [float(match[1]), float(match[2])]
    assert pins - {'VDD', 'VSS'} == expected, (case, sorted(expected - pins)[:10], sorted(pins - expected)[:10])
    lib = (destination / (alias + '.lib')).read_text()
    assert re.search(r'cell\s*\(\s*"?' + alias + r'"?\s*\)', lib)
    views[case] = dict(alias=alias, directory=str(destination), ports={k:dict(direction=v['direction'], width=len(v['bits'])) for k,v in ports.items()},
                       signal_pins=len(expected), size_um=dimensions, minimum_period_present='minimum_period' in lib,
                       original_name='otpu_asic_top', identity_change='Alias only in derived LEF/Lib; original ODB/SDC/SPEF untouched',
                       qualified_hard_macro=False, prior_max_cap_violations={'opentpu-act':2,'opentpu-mxu':12,'opentpu-act-mxu':41}[case])
    Path('view-progress.json').write_text(json.dumps(views, indent=2) + '\n')
with Path('baseline-inputs.sha256').open('w') as out:
    for path in inputs:
        h = hashlib.sha256()
        with path.open('rb') as f:
            for chunk in iter(lambda:f.read(8*1024*1024), b''):h.update(chunk)
        out.write(h.hexdigest() + '  ' + str(path) + '\n')
Path('validation.json').write_text(json.dumps({'passed':True,'kind':'baseline view and pin preparation only','views':views,
    'top_pnr_executed':False,'full_timing_arc_audit_complete':False,
    'scope':'Engineering preparation with explicitly unqualified baseline blocks; no hierarchical PPA or signoff conclusion'}, indent=2)+'\n')
