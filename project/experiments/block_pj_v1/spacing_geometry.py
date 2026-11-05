"""Localize native DRC against actual routed wires, vias, and transformed pins."""
from collections import defaultdict
import json
from pathlib import Path
import re
import subprocess
import sys

repo, folder, source, report = map(Path, sys.argv[1:5])
folder.mkdir()
legacy = repo / 'project/experiments/block_v1'
sys.path.insert(0, str(legacy))
from native_escape import records
from native_rect_completion import rectangles
from revision300_v_corner_probe import candidates

pattern = re.compile(
    r'violation type: ([^\n]+)\n\s*srcs: ([^\n]+)\n'
    r'\s*bbox = \(([^,]+), ([^)]+)\) - \(([^,]+), ([^)]+)\) on Layer (\w+)')
markers = []
for rule, srcs, x0, y0, x1, y1, layer in pattern.findall(report.read_text()):
    names = [name.replace(chr(92), '') for name in re.findall(r'net:(\S+)', srcs)]
    markers.append(dict(rule=rule, nets=names, layer=layer,
                        bbox_dbu=[round(float(x)*2000) for x in (x0, y0, x1, y1)]))
assert len(markers) == report.read_text().count('violation type:')
wanted = set(name for marker in markers for name in marker['nets'])
select = 'set wanted [dict create]\n'
for name in sorted(wanted):
    select += f'dict set wanted [encoding convertfrom utf-8 [binary decode hex {{{name.encode().hex()}}}]] 1\n'
helper = (legacy / 'odb_geometry.tcl').read_text()
anchor = '  foreach net [$block getNets] {'
assert helper.count(anchor) == 1
helper = helper.replace(anchor, select + anchor + '''
    set normalized [string map [list [format %c 92] {}] [$net getName]]
    if {![dict exists $wanted $normalized]} {continue}
''')
(folder / 'helper.tcl').write_text(helper)
(folder / 'geometry.tcl').write_text(
    f'read_db {{{source}}}\nsource helper.tcl\nbvgeom::export selected.tsv\nwrite_def original.def\n')
with (folder / 'geometry.log').open('w') as log:
    subprocess.run(['openroad', '-no_init', '-threads', '12', '-exit', 'geometry.tcl'],
                   cwd=folder, stdout=log, stderr=subprocess.STDOUT, check=True)

shapes = defaultdict(list)
aliases = {}
for line in (folder / 'selected.tsv').read_text().splitlines():
    if line.startswith('# NET '):
        _, _, alias, name = line.split()
        aliases[alias] = bytes.fromhex(name).decode().replace(chr(92), '')
    elif not line.startswith('#'):
        alias, layer, kind, *box = line.split('\t')
        shapes[aliases[alias], layer].append(dict(shape=kind, bbox_dbu=list(map(int, box))))
for record in records(folder / 'original.def'):
    name = record.lstrip().split()[1].replace(chr(92), '')
    if name in wanted:
        for _, layer, *box in rectangles(record):
            shapes[name, layer].append(dict(shape='wire-rect', bbox_dbu=box))
def nearby(marker, name):
    x0, y0, x1, y1 = marker['bbox_dbu']
    guard = 3200 if marker['layer'] == 'metal10' else 600
    return [shape for shape in shapes[name, marker['layer']]
            if shape['bbox_dbu'][0] < x1+guard and shape['bbox_dbu'][2] > x0-guard
            and shape['bbox_dbu'][1] < y1+guard and shape['bbox_dbu'][3] > y0-guard]

single = []
for marker in markers:
    marker['nearby'] = {name: nearby(marker, name) for name in marker['nets']}
    if marker['rule'] == 'Metal Spacing' and len(marker['nets']) == 1:
        name = marker['nets'][0]
        single.append(dict(marker=dict(net=name, layer=marker['layer'], bbox_dbu=marker['bbox_dbu']),
                           same_net_nearby_rectangles=marker['nearby'][name]))
proposed, skipped = candidates(single)
(folder / 'geometry.json').write_text(json.dumps(dict(markers=markers, proposed=proposed, skipped=skipped), indent=2))
