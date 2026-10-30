"""Render captured diagnostic rectangles; this is not a complete layout view."""
from pathlib import Path
import json
import re
import hashlib
from decimal import Decimal
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Patch

root = Path(__file__).resolve().parent
data = json.loads((root / 'index.json').read_bytes())
markers = json.loads(next(root.rglob('markers.json')).read_bytes())
fig, axes = plt.subplots(2, 2, figsize=(11, 9))
for marker, ax in zip(markers, axes.flat):
    i = marker['index']
    fields = re.search(r'bbox = \(([^,]+), ([^)]+)\) - \(([^,]+), ([^)]+)\)',
                       marker['report_record']).groups()
    box = [int(Decimal(s) * 2000) for s in fields]
    target = re.search(r'srcs: net:([^\n]+)', marker['report_record'])[1]
    cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
    for shape in data['marker_shapes'][str(i)]:
        a, b, c, d = shape['bbox_dbu']
        color = '#2563eb' if shape['net'] == target else '#6b7280'
        ax.add_patch(Rectangle(((a-cx)/2, (b-cy)/2), (c-a)/2, (d-b)/2,
                               facecolor=color, edgecolor=color, alpha=.35,
                               hatch='///' if 'via' in shape['kind'] else None))
    ax.add_patch(Rectangle(((box[0]-cx)/2, (box[1]-cy)/2), (box[2]-box[0])/2,
                           (box[3]-box[1])/2, fill=False, edgecolor='#dc2626',
                           linewidth=2, linestyle='--', zorder=10))
    a, b, c, d = marker['expanded_box_dbu']
    half = max(c-a, d-b)/4
    ax.set(xlim=(-half, half), ylim=(-half, half), aspect='equal',
           xlabel='X relative to marker center (nm)', ylabel='Y relative to marker center (nm)')
    ax.set_title(f"{i}: {marker['layer']} / {marker['report_record'].splitlines()[0]}\n"
                 f"center = ({cx/2000:.4f}, {cy/2000:.4f}) um", fontsize=10)
    ax.grid(alpha=.15)
fig.suptitle('V400: four native DRC markers and captured conductor rectangles', fontsize=13)
fig.legend(handles=[Patch(color='#2563eb', alpha=.35, label='Reported net'),
                    Patch(color='#6b7280', alpha=.35, label='Nearby other net'),
                    Patch(facecolor='white', edgecolor='black', hatch='///', label='Via metal'),
                    Patch(fill=False, edgecolor='#dc2626', linestyle='--', label='DRC marker')],
           loc='lower center', bbox_to_anchor=(.5, .035), ncol=4, frameon=False)
fig.text(.5, .015, 'Read-only local wire/via/PG/block-port sample. Cell-pin geometry omitted. Diagnostic only.',
         ha='center', fontsize=9)
fig.tight_layout(rect=(0, .08, 1, .95))
outputs = {}
for ext in ('png', 'svg'):
    path = root / ('marker-overview.' + ext)
    fig.savefig(path, dpi=160, metadata={'Date': None} if ext == 'svg' else None)
    outputs[path.name] = dict(bytes=path.stat().st_size, sha256=hashlib.sha256(path.read_bytes()).hexdigest())
(root / 'plot-index.json').write_text(json.dumps(dict(
    input_index_sha256=hashlib.sha256((root/'index.json').read_bytes()).hexdigest(),
    generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    markers=4, outputs=outputs, scope='Diagnostic rectangles, not complete layout or DRC acceptance.'), indent=2)+'\n')
