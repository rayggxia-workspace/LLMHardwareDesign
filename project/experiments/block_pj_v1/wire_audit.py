"""Check physical terminal reachability in the final routed parent ODB."""
from collections import defaultdict
import json
from pathlib import Path
import subprocess
import sys

repo, odb, folder = map(Path, sys.argv[1:4])
folder.mkdir()
legacy = repo / 'project/experiments/block_v1'
sys.path.insert(0, str(legacy))
from native_escape import records
from native_rect_completion import rectangles

helper = (legacy / 'odb_geometry.tcl').read_text()
start = '  foreach net [$block getNets] {'
assert helper.count(start) == 1
helper = helper.replace(start, start + '''
    if {[$net getSigType] in {POWER GROUND}} {continue}
    set count [expr {[llength [$net getITerms]] + [llength [$net getBTerms]]}]
    if {$count < 2} {continue}
''')
helper = helper.replace('  set output [open $destination w]',
                        '  set output [open $destination w]\n  set expectation [open terminals.tsv w]')
helper = helper.replace('    set alias n[$net getId]', '''    set alias n[$net getId]
    puts $expectation "$alias\t$count"
''')
helper = helper.replace('db_box $output $alias $box block-port',
                        'db_box $output $alias $box P-[binary encode hex [encoding convertto utf-8 [$term getName]]]')
helper = helper.replace('db_box $output $alias $box instance-pin $transform',
                        '''db_box $output $alias $box I-[binary encode hex [encoding convertto utf-8 "[$inst getName]/[[$term getMTerm] getName]"]] $transform''')
helper = helper.replace('  close $output', '  close $output\n  close $expectation')
(folder / 'geometry.tcl').write_text(f'read_db {{{odb}}}\n' + helper +
                                      'bvgeom::export wire-audit.tsv\nwrite_def readback.def\n')
with (folder / 'geometry.log').open('w') as log:
    subprocess.run(['openroad', '-no_init', '-threads', '12', '-exit', 'geometry.tcl'],
                   cwd=folder, stdout=log, stderr=subprocess.STDOUT, check=True)

aliases = {}
by_net = defaultdict(list)
with (folder / 'wire-audit.tsv').open() as stream:
    for line in stream:
        if line.startswith('# NET '):
            _, _, alias, encoded = line.split()
            name = bytes.fromhex(encoded).decode().replace(chr(92), '')
            assert name not in aliases
            aliases[name] = alias
        elif not line.startswith('#'):
            alias, layer, kind, *coords = line.rstrip('\n').split('\t')
            by_net[alias].append((layer, kind, tuple(map(int, coords))))
for record in records(folder / 'readback.def'):
    name = record.lstrip().split()[1].replace(chr(92), '')
    if name in aliases:
        for _, layer, *box in rectangles(record):
            by_net[aliases[name]].append((layer, 'wire-rect', tuple(box)))

def level(layer):
    if layer.startswith('metal'):
        return 2 * int(layer[5:])
    assert layer.startswith('via'), layer
    return 2 * int(layer[3:]) + 1

def reach(shapes):
    roots = list(range(len(shapes)))
    def find(i):
        while roots[i] != i:
            roots[i] = roots[roots[i]]
            i = roots[i]
        return i
    def join(a, b):
        roots[find(a)] = find(b)
    terminal_ids = defaultdict(list)
    wires = []
    active = []
    order = sorted(range(len(shapes)), key=lambda i: shapes[i][2][0])
    for i in order:
        layer, kind, box = shapes[i]
        li = level(layer)
        active = [e for e in active if e[2][2] >= box[0]]
        for j, lj, other in active:
            if li != lj and abs(li-lj) != 1:
                continue
            dx = min(box[2], other[2]) - max(box[0], other[0])
            dy = min(box[3], other[3]) - max(box[1], other[1])
            if (dx > 0 and dy > 0) or (li == lj and min(dx,dy) == 0 and max(dx,dy) > 0):
                join(i,j)
        active.append((i, li, box))
        if kind.startswith(('I-','P-')):
            terminal_ids[kind].append(i)
        elif kind.startswith('wire'):
            wires.append(i)
    for ids in terminal_ids.values():
        for i in ids[1:]:
            join(ids[0], i)
    components = {find(i) for i in wires}
    missing = [term for term, ids in terminal_ids.items() if find(ids[0]) not in components]
    return dict(components=len(components), terminals=len(terminal_ids), missing=missing)

expect = dict((k, int(n)) for k, n in (line.split('\t') for line in (folder / 'terminals.tsv').read_text().splitlines()))
assert expect and set(expect) == set(aliases.values())
failed = {}
for name, alias in aliases.items():
    got = reach(by_net[alias])
    if got['components'] != 1 or got['terminals'] != expect[alias] or got['missing']:
        failed[name] = dict(expected_terminals=expect[alias], **got)
result = dict(passed=not failed, checked_nets=len(expect), checked_terminals=sum(expect.values()),
              failures=failed)
(folder / 'wire-reachability.json').write_text(json.dumps(result, indent=2) + '\n')
print(f'WIRE REACHABILITY nets={len(expect)} failures={len(failed)}')
assert result['passed']
