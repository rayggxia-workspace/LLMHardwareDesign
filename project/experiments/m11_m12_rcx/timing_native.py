"""Reuse frozen native implementations and matching legacy timing abstractions.

All output must be a new directory; this never runs physical implementation.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

RECEIPT = Path('/public/home/yuzelu/PingyangHuang/issue-215-top-pex-zOz2uxIr/route-206.json')
KINDS = ('C0', 'F0', 'J0', 'P0', 'T0', 'U0')
STD = Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib')
PJ = Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-187-p16-j16')


def sha(p):
    h = hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda: f.read(4 << 20), b''): h.update(b)
    return h.hexdigest()


def sources(kind):
    r = json.loads(RECEIPT.read_text())
    native = Path(r['native_masks'][kind]['path']).with_suffix('')
    module = re.search(r'^module\s+(\S+)', native.with_suffix('.v').read_text())[1]
    libs = [STD]
    model = None
    if kind in ('P0', 'J0'):
        folder = '139-p-final-gates' if kind == 'P0' else '119-j-start-extraction-retry'
        gate = PJ / folder / 'gates' / (kind[0] + '-electrical')
        export = (gate / 'export.tcl').read_text()
        libs = [Path(p) for p in re.findall(r'read_liberty \{([^}]+)\}', export)]
        sdc = Path(re.search(r'read_sdc \{([^}]+)\}', export)[1])
        assert str(native.with_suffix('.odb')) in export
        assert str(native.with_suffix('.spef')) in export
        model = gate / (module + '.lib')
    else:
        libs += list(native.parent.glob('*sram*.lib'))
        sdc = native.with_suffix('.sdc')
    return dict(kind=kind, module=module, native=str(native), libraries=list(map(str, libs)),
                sdc=str(sdc), legacy_model=str(model) if model else None)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--kind', choices=KINDS, default=KINDS[int(os.environ.get('TIMING_INDEX', '0'))])
    p.add_argument('--out', type=Path, default=Path(os.environ.get('TIMING_OUT', '.')) / 'result')
    a = p.parse_args()
    a.out.mkdir()
    s = sources(a.kind)
    native = Path(s['native'])
    inputs = [RECEIPT, *map(Path, s['libraries']), Path(s['sdc']),
              native.with_suffix('.odb'), native.with_suffix('.v'), native.with_suffix('.spef')]
    if s['legacy_model']: inputs += [Path(s['legacy_model'])]
    provenance = {str(f): dict(bytes=f.stat().st_size, sha256=sha(f)) for f in inputs}
    text = ''.join(f'read_liberty {{{x}}}\n' for x in s['libraries'])
    text += f'read_db {{{native.with_suffix(".odb")}}}\nread_sdc {{{s["sdc"]}}}\n'
    text += f'read_spef {{{native.with_suffix(".spef")}}}\nset_propagated_clock [all_clocks]\n'
    text += 'set_clock_latency -source 0 [all_clocks]\n'
    text += r'''
set fp [open ports.tsv w]
foreach p [get_ports *] {
  puts $fp "[binary encode hex [get_full_name $p]]\t[get_property $p direction]"
}
close $fp
report_parasitic_annotation > annotation.rpt
report_worst_slack -max -digits 8
report_worst_slack -min -digits 8
report_checks -path_delay max -group_path_count 8 -format full_clock_expanded -digits 8 > original-max.rpt
report_checks -path_delay min -group_path_count 8 -format full_clock_expanded -digits 8 > original-min.rpt
check_setup -verbose > check-setup.rpt
'''
    if not s['legacy_model']:
        text += f'write_timing_model {{{a.out.resolve() / (s["module"] + ".lib")}}}\n'
        s['model'] = str(a.out.resolve() / (s['module'] + '.lib'))
        s['model_origin'] = 'Generated from unchanged old native RC; missing legacy artifact only'
    else:
        s['model'] = s['legacy_model']
        s['model_origin'] = 'Existing matching accepted native export; reused unchanged'
    text += 'puts TIMING_NATIVE_COMPLETE\nexit\n'
    (a.out / 'native.tcl').write_text(text)
    with (a.out / 'openroad.log').open('xb') as log:
        subprocess.run(['openroad', '-no_init', '-threads', os.environ.get('TIMING_CPUS', '1'),
                        '-exit', str(a.out.resolve() / 'native.tcl')], cwd=a.out,
                       stdout=log, stderr=subprocess.STDOUT, check=True)
    assert 'TIMING_NATIVE_COMPLETE' in (a.out / 'openroad.log').read_text()
    s.update(inputs=provenance, route_receipt_sha256=sha(RECEIPT),
             outputs={f.name: dict(bytes=f.stat().st_size, sha256=sha(f)) for f in a.out.iterdir() if f.is_file()},
             qualification='Original implementation/model audit only; no post-coupling timing qualification.')
    (a.out / 'native.json').write_text(json.dumps(s, indent=2) + '\n')
    print(json.dumps({k: s[k] for k in ('kind', 'module', 'model', 'model_origin')}), flush=True)


if __name__ == '__main__': main()
