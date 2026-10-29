"""Render exact exported upper-metal rectangles, with SHA-bound provenance."""
import argparse
import hashlib
import html
import json
from pathlib import Path


def render(source, destination):
    request = json.loads((source / 'route-inputs.json').read_text())
    geometry = source / 'geometry.tsv'
    width, height = request['die_um']
    pieces = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="-30 -80 %.9g %.9g">' % (width + 60, height + 150)]
    provenance = dict(geometry_sha256=hashlib.sha256(geometry.read_bytes()).hexdigest(),
                      inputs_sha256=hashlib.sha256((source / 'route-inputs.json').read_bytes()).hexdigest(),
                      source=str(source), links=len(request['links']), coordinates='um, Y flipped for display')
    pieces.append('<metadata>' + html.escape(json.dumps(provenance)) + '</metadata>')
    pieces.append('<rect x="-30" y="-80" width="%.9g" height="%.9g" fill="white"/>' % (width + 60, height + 150))
    pieces.append('<text x="0" y="-35" font-family="sans-serif" font-size="32">%d complete signal nets; actual OpenDB rectangles</text>' % len(request['links']))
    pieces.append('<g transform="translate(0 %.9g) scale(1 -1)">' % height)
    for name, (x, y) in request['placements'].items():
        w, h = request['size'][name]
        pieces.append('<rect x="%.9g" y="%.9g" width="%.9g" height="%.9g" fill="#f1f5f9" stroke="#334155" stroke-width="2"/>' % (x, y, w, h))
    colors = {'metal11': '#2563eb', 'metal12': '#dc2626', 'via10': '#15803d', 'via11': '#7e22ce'}
    seen = set()
    for line in geometry.read_text().splitlines():
        if line.startswith('#'):
            continue
        net, layer, kind, *coords = line.split('\t')
        key = (net, layer, *coords)
        if layer not in colors or key in seen:
            continue
        seen.add(key)
        x0, y0, x1, y1 = [int(v) / 2000 for v in coords]
        pieces.append('<rect x="%.9g" y="%.9g" width="%.9g" height="%.9g" fill="%s" fill-opacity="0.75"/>' % (x0, y0, x1 - x0, y1 - y0, colors[layer]))
    pieces.append('</g>')
    for name, (x, y) in request['placements'].items():
        w, h = request['size'][name]
        left = name in ('booster','return') and x < min(request['placements'][k][0] for k in ('m','t','s') if k in request['placements'])
        pieces.append('<text x="%.9g" y="%.9g" text-anchor="%s" font-family="sans-serif" font-size="24">%s</text>' % (x - 8 if left else x + 8, height - y - h + 30, 'end' if left else 'start', html.escape(name.upper())))
    pieces.append('<text x="0" y="%.9g" font-family="sans-serif" font-size="22">M11 blue; M12 red; via10 green; via11 purple. Native internals omitted.</text></svg>' % (height + 45))
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text('\n'.join(pieces), encoding='utf-8')
    # A standard plotting preview of the same rectangles, without a browser
    # screenshot or raster editing. The SVG retains the exact micron geometry.
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.collections import PatchCollection
    from matplotlib.patches import Rectangle
    fig, axis = plt.subplots(figsize=(8, 8 * height / width))
    for name, (x, y) in request['placements'].items():
        w, h = request['size'][name]
        axis.add_patch(Rectangle((x, y), w, h, facecolor='#f1f5f9', edgecolor='#334155', linewidth=.6))
        left = name in ('booster','return') and x < min(request['placements'][k][0] for k in ('m','t','s') if k in request['placements'])
        axis.text(x - 8 if left else x + 8, y + h - 16, name.upper(), fontsize=7, va='top', ha='right' if left else 'left', zorder=5,
                  bbox=dict(facecolor='white', edgecolor='none', alpha=.8, pad=1))
    layers = {layer: [] for layer in colors}
    for net, layer, *coords in seen:
        x0, y0, x1, y1 = [int(v) / 2000 for v in coords]
        layers[layer].append(Rectangle((x0, y0), x1 - x0, y1 - y0))
    for layer, rectangles in layers.items():
        axis.add_collection(PatchCollection(rectangles, facecolor=colors[layer], edgecolor='none', alpha=.75))
    axis.set(xlim=(-15, width + 15), ylim=(-15, height + 15), aspect='equal',
             xlabel='X (um)', ylabel='Y (um)',
             title='%d complete signal nets: actual OpenDB rectangles' % len(request['links']))
    axis.tick_params(labelsize=7)
    fig.tight_layout()
    fig.savefig(destination.with_suffix('.png'), dpi=160)
    plt.close(fig)
    print(json.dumps(dict(output=str(destination), **provenance)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('destination', type=Path)
    args = parser.parse_args()
    render(args.source, args.destination)
