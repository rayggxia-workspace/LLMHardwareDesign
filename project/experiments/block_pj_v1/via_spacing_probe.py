"""Test native via-enclosure alternatives for reported same-net spacing."""
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

repo, source, geom, out = map(Path, sys.argv[1:5])
out.mkdir()
sys.path.insert(0, str(repo / 'project/experiments/block_v1'))
from native_escape import records
from native_escape_audit import def_inventory
from revision300_v_corner_probe import violations

lef = Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lef/NangateOpenCellLibrary.tech.lef')
definitions = {}
for name, body in re.findall(r'(?ms)^VIA (via[123]_\d+) DEFAULT\n(.*?)^END \1\s*$', lef.read_text()):
    by_layer = {}
    for layer, rect in re.findall(r'LAYER (\w+)\s*;\s*RECT ([^;]+);', body):
        by_layer[layer] = [round(float(x) * 2000) for x in rect.split()]
    assert len(by_layer) == 3, name
    definitions[name] = by_layer

via = re.compile(r'(\(\s*(-?\d+)\s+(-?\d+)\s*\)\s+)(via[123]_\d+)(?=\s)')
original = geom / 'original.def'
rows = json.loads((geom / 'geometry.json').read_text())['markers']
by_net = {}
selection = set(json.loads(os.environ.get('PJ_VIA_NETS', '[]')))
policy = os.environ.get('PJ_VIA_POLICY', 'both')
assert policy in ('both', 'first', 'last')
for row in rows:
    if row['rule'] == 'Metal Spacing' and row['layer'] in ('metal2', 'metal3') and len(row['nets']) == 1:
        name, = row['nets']
        if not selection or name in selection:
            by_net.setdefault(name, []).append(row)

replacements = {}
edits = []
for record in records(original):
    name = record.lstrip().split()[1].replace(chr(92), '')
    if name not in by_net:
        continue
    lookup = {}
    edit_by_offset = {}
    for m in via.finditer(record):
        x, y = int(m[2]), int(m[3])
        for row in by_net[name]:
            layer = row['layer']
            old = definitions.get(m[4])
            if not old or layer not in old:
                continue
            rect = [v + (x if i % 2 == 0 else y) for i, v in enumerate(old[layer])]
            if not any(s['shape'] == 'wire-via' and s['bbox_dbu'] == rect for s in row['nearby'][name]):
                continue
            box = row['bbox_dbu']
            axis = 1 if layer == 'metal2' else 0
            other = 1 - axis
            touches = (rect[axis+2] == box[axis] or rect[axis] == box[axis+2])
            if not touches or rect[other] > box[other] or rect[other+2] < box[other+2]:
                continue
            options = [candidate for candidate, layers in definitions.items()
                       if set(layers) == set(old)
                       and all(layers[k] == old[k] for k in old if k != layer)
                       and layers[layer][axis] > old[layer][axis]
                       and layers[layer][axis+2] < old[layer][axis+2]]
            if options:
                chosen = sorted(options)[0]
                lookup[m.start(4)] = chosen
                edit_by_offset[m.start(4)] = dict(net=name, location_dbu=[x,y], layer=layer,
                                                 before=m[4], after=chosen, marker=box)
    if lookup:
        if policy != 'both':
            offset = sorted(lookup)[0 if policy == 'first' else -1]
            lookup = {offset: lookup[offset]}
        edits.extend(edit_by_offset[offset] for offset in lookup)
        replacements[name] = via.sub(lambda m: m[1] + lookup.get(m.start(4), m[4]), record)
if not replacements:
    (out / 'receipt.json').write_text(json.dumps(dict(eligible=False, nets=sorted(selection)), indent=2))
    sys.exit(0)
header = re.search(r'(?m)^DESIGN (\S+) ;$', original.read_text())[1]
(out / 'edits.json').write_text(json.dumps(edits, indent=2) + '\n')
patch = 'VERSION 5.8 ;\nDIVIDERCHAR "/" ;\nBUSBITCHARS "[]" ;\n'
patch += f'DESIGN {header} ;\nUNITS DISTANCE MICRONS 2000 ;\nNETS {len(replacements)} ;\n'
patch += ''.join(replacements.values()) + 'END NETS\nEND DESIGN\n'
(out / 'vias.def').write_text(patch)
(out / 'check.tcl').write_text(f'read_db {{{source}}}\nread_def -floorplan_initialize vias.def\n'
                              'write_db edited.odb\nwrite_def edited.def\n'
                              'drt::check_drc_cmd after.rpt 0 0 0 0 native_whole_drc\n')
with (out / 'check.log').open('w') as log:
    subprocess.run(['openroad', '-no_init', '-threads', '12', '-exit', 'check.tcl'],
                   cwd=out, stdout=log, stderr=subprocess.STDOUT, check=True)
base, base_nonroute = def_inventory(original)
updated, updated_nonroute = def_inventory(out / 'edited.def')
exact = base_nonroute == updated_nonroute and base.keys() == updated.keys()
diff = {key.replace(chr(92), '') for key in base if base[key] != updated.get(key)}
exact = exact and diff == set(replacements)
def canonical(record):
    header, rest = record.split('+', 1)
    tokens = re.findall(r'\(\s*([^()]*)\)', header)
    assert len(tokens) == header.count('(') == header.count(')')
    return (header.split()[1], sorted(' '.join(t.split()) for t in tokens), ' '.join(rest.split()))


expected = {key: canonical(val) for key, val in replacements.items()}
for record in records(out / 'edited.def'):
    name = record.lstrip().split()[1].replace(chr(92), '')
    if name in expected:
        exact = exact and expected[name] == canonical(record)
old = Counter((m['rule'], tuple(sorted(m['nets'])), m['layer'], tuple(m['bbox_dbu'])) for m in rows)
final = (out / 'after.rpt').read_text()
marks = re.compile(r'violation type: ([^\n]+)\n\s*srcs: ([^\n]+)\n'
                   r'\s*bbox = \(([^,]+), ([^)]+)\) - \(([^,]+), ([^)]+)\) on Layer (\w+)')
observed = Counter()
for rule, srcs, *rest in marks.findall(final):
    names = sorted(name.replace(chr(92), '') for name in re.findall(r'net:(\S+)', srcs))
    observed[rule, tuple(names), rest[-1], tuple(round(float(x)*2000) for x in rest[:-1])] += 1
new_count = sum(violations(final).values())
assert sum(observed.values()) == new_count
digest = hashlib.sha256()
with source.open('rb') as stream:
    for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b''):
        digest.update(chunk)
receipt = dict(edited_via_sites=len({(e['net'], *e['location_dbu'], e['before']) for e in edits}),
               original_markers=sum(old.values()), final_markers=new_count, exact_def_diff=exact,
               eligible=True, selection=sorted(selection), policy=policy,
               introduced_markers=[(key, count) for key, count in (observed-old).items()],
               removed_markers=[(key, count) for key, count in (old-observed).items()],
               source_sha256=digest.hexdigest())
(out / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
assert exact and not receipt['introduced_markers'] and receipt['removed_markers'], receipt
