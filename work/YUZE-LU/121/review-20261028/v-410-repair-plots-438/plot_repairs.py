"""Measured copy geometry, with unchanged sampled neighbors for local context."""
from pathlib import Path
import sys
import json
import hashlib
from decimal import Decimal
import re
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parent
sys.path.insert(0, str(BASE.parents[3] / 'project/experiments/block_v1'))
from native_escape_audit import geometry

original = json.loads((BASE / 'v-410-marker-geometry-427/index.json').read_bytes())
markers_file = next((BASE / 'v-410-marker-geometry-427').rglob('markers.json'))
markers = json.loads(markers_file.read_bytes())
cases = [('m2', 0, 'net111996', '35 nm free-bend shift', '429'),
         ('m3', 1, '$abc$1379946$new_n88505', '20 nm via and adjoining-path shift', '431'),
         ('m9', 2, 'net95974', '55 nm free-bend shift', '429')]
inputs = {}
fig, axes = plt.subplots(3, 2, figsize=(12, 13))
for row, (name, marker_index, net, label, run) in enumerate(cases):
    source = BASE / ('v-410-bend-clearance-429' if run == '429' else 'v-410-via-clearance-431')
    folder = next(source.rglob(name))
    marker = markers[marker_index]
    values = re.search(r'bbox = \(([^,]+), ([^)]+)\) - \(([^,]+), ([^)]+)\)', marker['report_record']).groups()
    box = [int(Decimal(s) * 2000) for s in values]
    cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
    bounds = marker['expanded_box_dbu']
    for col, stage in enumerate(('before', 'after')):
        ax = axes[row, col]
        file = folder / (stage + '-geometry.tsv')
        inputs[str(file.relative_to(BASE))] = hashlib.sha256(file.read_bytes()).hexdigest()
        own = geometry(file)[net]
        shapes = [(layer, kind, b, True) for layer, kind, b in own]
        # Untouched routes and all non-NETS geometry were checked by full DEF
        # readback. These are finite original neighboring shapes, not a new
        # complete lower-layer export of the edited copy.
        shapes += [(s['layer'], s['kind'], s['bbox_dbu'], False)
                   for s in original['marker_shapes'][str(marker_index)] if s['net'] != net]
        for layer, kind, b, target in shapes:
            if layer != marker['layer']:
                continue
            a, y, c, d = b
            if c <= bounds[0] or a >= bounds[2] or d <= bounds[1] or y >= bounds[3]:
                continue
            color = '#2563eb' if target else '#6b7280'
            ax.add_patch(Rectangle(((a-cx)/2, (y-cy)/2), (c-a)/2, (d-y)/2,
                                   facecolor=color, edgecolor=color, alpha=.35,
                                   hatch='///' if 'via' in kind else None))
        ax.add_patch(Rectangle(((box[0]-cx)/2, (box[1]-cy)/2), (box[2]-box[0])/2,
                               (box[3]-box[1])/2, fill=False, edgecolor='#dc2626',
                               linestyle='--', linewidth=1.8))
        half = max(abs(bounds[0]-cx), abs(bounds[2]-cx), abs(bounds[1]-cy), abs(bounds[3]-cy))/2
        ax.set(xlim=(-half, half), ylim=(-half, half), aspect='equal',
               xlabel='X relative to original marker center (nm)',
               ylabel='Y relative to original marker center (nm)')
        ax.set_title(f'{name.upper()} {stage}: {label}\nWhole native DRC: {487 if col == 0 else 486}; target {"present" if col == 0 else "absent"}', fontsize=10)
        ax.grid(alpha=.15)
fig.suptitle('V410: three independently verified local copy repairs', fontsize=14)
fig.text(.5, .023, 'Blue: target metal; gray: unchanged sampled neighbors; hatch: via metal; red: original marker location.\nEach copy removes exactly one marker, adds none. Diagnostic only; RC/STA/full GDS qualification still required.', ha='center', fontsize=9)
fig.tight_layout(rect=(0, .065, 1, .965))
outputs = {}
for ext in ('png', 'svg'):
    p = ROOT / ('before-after.' + ext)
    fig.savefig(p, dpi=160, metadata={'Date': None} if ext == 'svg' else None)
    outputs[p.name] = dict(bytes=p.stat().st_size, sha256=hashlib.sha256(p.read_bytes()).hexdigest())
(ROOT / 'index.json').write_text(json.dumps(dict(inputs=inputs, outputs=outputs,
    generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    scope='Actual selected-net before/after rectangles plus finite unchanged original neighbors. Not complete layout, DRC acceptance or final implementation.'), indent=2)+'\n')
