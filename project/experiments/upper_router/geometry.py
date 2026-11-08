"""Integer-DBU geometry for an explicitly declared two-layer research grid."""
from collections import defaultdict


def need(ok, message):
    if not ok:
        raise ValueError(message)


def contains(outer, inner):
    return outer[0] <= inner[0] and outer[1] <= inner[1] and outer[2] >= inner[2] and outer[3] >= inner[3]


def touching(a, b):
    return max(a[0], b[0]) <= min(a[2], b[2]) and max(a[1], b[1]) <= min(a[3], b[3])


def too_close(a, b, spacing):
    # Conservative rectangular (L-infinity) spacing, including diagonal corners.
    dx = max(a[0]-b[2], b[0]-a[2], 0)
    dy = max(a[1]-b[3], b[1]-a[3], 0)
    return touching(a, b) or max(dx, dy) < spacing


def box(point, size):
    x, y = point
    return (x-size//2, y-size//2, x+size//2, y+size//2)


def segment_shape(layer, a, b, tech):
    r = tech['width']//2
    return (layer, (min(a[0], b[0])-r, min(a[1], b[1])-r,
                    max(a[0], b[0])+r, max(a[1], b[1])+r))


def via_shapes(kind, point, tech):
    v = tech[kind]
    if kind == 'via10':
        return [('V10', box(point, v['cut'])), ('M11', box(point, v['cut']+2*v['upper_enclosure']))]
    return [('V11', box(point, v['cut'])),
            ('M11', box(point, v['cut']+2*v['lower_enclosure'])),
            ('M12', box(point, v['cut']+2*v['upper_enclosure']))]


def spacing(layer, tech):
    return tech['via10' if layer == 'V10' else 'via11']['spacing'] if layer.startswith('V') else tech['spacing']


def validate(spec):
    need(spec.get('schema_version') == 'upper-router/1', 'unsupported routing schema')
    need(spec.get('units') == 'dbu', 'explicit DBU units required')
    t = spec['technology']
    need(len(t['bounds']) == 4 and all(type(x) is int for x in t['bounds']), 'invalid bounds')
    need(t['bounds'][0] < t['bounds'][2] and t['bounds'][1] < t['bounds'][3], 'empty bounds')
    need(len(t['origin']) == 2 and all(type(x) is int for x in t['origin']), 'invalid grid origin')
    need(type(t['pitch']) is int and t['pitch'] > 0, 'invalid pitch')
    need(type(t['width']) is int and t['width'] > 0 and t['width'] % 2 == 0, 'width must be positive even DBU')
    need(type(t['spacing']) is int and t['spacing'] >= 0, 'invalid spacing')
    # Coarse-grid baseline: distinct grid sites are legal cut sites even within
    # a net. Finer routing tracks with larger via pitches need a richer state.
    for kind in ('via10', 'via11'):
        v = t[kind]
        need(all(type(v[k]) is int for k in ('cut', 'lower_enclosure', 'upper_enclosure', 'spacing')), 'invalid via rules')
        need(v['cut'] > 0 and v['cut'] % 2 == 0 and min(v['lower_enclosure'], v['upper_enclosure'], v['spacing']) >= 0,
             'invalid via dimensions')
        need(t['pitch'] >= v['cut']+v['spacing'], 'baseline grid pitch must cover cut spacing')
    need(t['pitch'] >= t['width']+t['spacing'], 'grid pitch below metal spacing')
    owners = {}
    ids = set()
    for n in spec['nets']:
        need(n['id'] not in ids, 'duplicate net')
        ids.add(n['id'])
        need(len(n['sinks']) == len(set(n['sinks'])) and n['driver'] not in n['sinks'], 'invalid net terminals')
        for pin in [n['driver']]+n['sinks']:
            need(pin in spec['pins'] and spec['pins'][pin], 'unknown/empty pin')
            need(pin not in owners or owners[pin] == n['id'], 'pin used by different nets')
            owners[pin] = n['id']
            for rect in spec['pins'][pin]:
                need(len(rect) == 4 and all(type(x) is int for x in rect) and rect[0] < rect[2] and rect[1] < rect[3], 'invalid M10 pin rectangle')
    for obstacle in spec.get('obstacles', []):
        need(obstacle['layer'] in ('M11', 'M12', 'V10', 'V11'), 'unknown obstacle layer')
        rect = obstacle['rect']
        need(len(rect) == 4 and all(type(x) is int for x in rect) and rect[0] < rect[2] and rect[1] < rect[3], 'invalid obstacle')


class Occupancy:
    """Spatial bins contain actual rectangular metal/cut footprints."""
    def __init__(self, tech):
        self.tech = tech
        self.bins = defaultdict(list)
        self.cell = tech['pitch']

    def keys(self, layer, rect, margin=0):
        a, b, c, d = rect
        for x in range((a-margin)//self.cell, (c+margin)//self.cell+1):
            for y in range((b-margin)//self.cell, (d+margin)//self.cell+1):
                yield layer, x, y

    def add(self, shapes, owner):
        for layer, rect in set((layer, tuple(r)) for layer, r in shapes):
            for key in self.keys(layer, rect):
                self.bins[key].append((owner, rect))

    def legal(self, shapes, owner):
        t = self.tech
        for layer, rect in shapes:
            if not contains(t['bounds'], rect):
                return False
            seen = set()
            for key in self.keys(layer, rect, spacing(layer, t)):
                for other, r in self.bins.get(key, []):
                    if (other, r) in seen:
                        continue
                    seen.add((other, r))
                    if other == owner and (not layer.startswith('V') or tuple(rect) == r):
                        continue
                    if too_close(rect, r, spacing(layer, t)):
                        return False
        return True


def access_points(rects, tech):
    """All grid candidates in each real M10 rectangle, with full enclosure."""
    pitch = tech['pitch']
    ox, oy = tech['origin']
    margin = tech['via10']['cut']//2+tech['via10']['lower_enclosure']
    points = set()
    for a, b, c, d in rects:
        first_x = -(-(a+margin-ox)//pitch)
        first_y = -(-(b+margin-oy)//pitch)
        for i in range(first_x, (c-margin-ox)//pitch+1):
            for j in range(first_y, (d-margin-oy)//pitch+1):
                points.add((ox+i*pitch, oy+j*pitch))
    return sorted(points)
