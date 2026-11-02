"""Prepare a separate, GDS-derived M4 obstruction abstraction with KLayout.

Invoke with -rd GDS=... -rd LEF=... -rd OUTPUT=... -rd RECEIPT=...
Only M4 OBS text changes; every pin, other layer, size and circuit is retained.
This is a geometric proof, not a routed-access or physical qualification.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import pya

assert os.environ.get('SLURM_JOB_ID')
gds, lef, output = map(Path, (GDS, LEF, OUTPUT))
assert not output.exists() and output.resolve() != lef.resolve()


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


inputs = {str(p): sha(p) for p in (gds, lef)}
layout = pya.Layout()
layout.read(str(gds))
assert layout.dbu == 0.0005 and len(layout.top_cells()) == 1
assert layout.top_cell().name == 's_sram_256x128_freepdk45'
actual = pya.Region(layout.top_cell().begin_shapes_rec(layout.find_layer(17, 0)))
actual.merge()
text = lef.read_text()
rect = r'RECT\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s*;'


def region(part):
    result = pya.Region()
    for m in re.finditer(rect, part):
        coordinates = [float(x) / layout.dbu for x in m.groups()]
        assert all(abs(x - round(x)) < 1e-6 for x in coordinates)
        result.insert(pya.Box(*map(round, coordinates)))
    assert not re.sub(rect, '', part).strip(), 'Unsupported LEF geometry'
    return result.merged()


obs = list(re.finditer(r'(?ms)^\s*OBS\s*\n(.*?)^\s*END\s*$', text))
assert len(obs) == 1
m4s = list(re.finditer(r'(?s)LAYER\s+metal4\s*;(.*?)(?=\bLAYER\b|\Z)', obs[0].group(1)))
assert len(m4s) == 1
m4 = m4s[0]
old = region(m4.group(1))
ports = pya.Region()
for pin in re.finditer(r'(?ms)^\s*PIN\s+(\S+)\s*\n(.*?)^\s*END\s+\1\s*$', text):
    for part in re.finditer(r'(?s)LAYER\s+metal4\s*;(.*?)(?=\bLAYER\b|\bEND\b|\Z)', pin.group(2)):
        ports += region(part.group(1))
ports.merge()
assert not actual.is_empty() and not ports.is_empty()
assert (actual - (old | ports)).is_empty(), 'Original abstraction misses real M4'
replacement = (actual - ports).merged()
assert (replacement - old).is_empty()
decomposed = replacement.decompose_trapezoids_to_region()
boxes = []
for polygon in decomposed.each():
    assert polygon.is_box(), 'Expected Manhattan rectangular decomposition'
    b = polygon.bbox()
    boxes.append((b.left, b.bottom, b.right, b.top))
assert boxes
geometry = '\n' + ''.join('    RECT ' + ' '.join(format(x * layout.dbu, '.4f') for x in b) + ' ;\n'
                            for b in sorted(boxes)) + '    '
readback = region(geometry)
assert (readback ^ replacement).is_empty()
assert (actual - (readback | ports)).is_empty(), 'Real M4 must remain covered'
start = obs[0].start(1) + m4.start(1)
end = obs[0].start(1) + m4.end(1)
refined = text[:start] + geometry + text[end:]
output.write_text(refined)
assert output.read_text() == refined
assert all(sha(Path(p)) == h for p, h in inputs.items())
record = dict(passed=True, qualified=False,
              scope='Geometric M4 abstraction only; native LEF readback and actual routing/DRC remain required',
              inputs=inputs, source_lef=str(lef), source_gds=str(gds), output=str(output),
              output_sha256=sha(output), dbu_um=layout.dbu, m4_gds_layer=[17, 0],
              rectangles=len(boxes), actual_m4_area_dbu2=actual.area(),
              original_obs_area_dbu2=old.area(), refined_obs_area_dbu2=readback.area(),
              all_real_m4_covered_by_obstructions_or_unchanged_ports=True,
              serialized_geometry_exact=True, only_metal4_obs_text_changed=True,
              unchanged_prefix_sha256=hashlib.sha256(text[:start].encode()).hexdigest(),
              unchanged_suffix_sha256=hashlib.sha256(text[end:].encode()).hexdigest())
Path(RECEIPT).write_text(json.dumps(record, indent=2) + '\n')
