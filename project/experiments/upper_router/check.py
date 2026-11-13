"""Geometry/connectivity verifier: reads rectangles, not A* search state."""
import hashlib
import json
from geometry import (NativePins, Occupancy, RoutingGrid, box, contains, need, segment_shape,
                      touching, validate, via_shapes)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()


def verify(spec, result):
    validate(spec)
    need(result.get('spec_sha256') == digest(spec), 'stale route input fingerprint')
    need(result.get('physical_qualified') is False, 'geometry is not physical qualification')
    need(result.get('electrical_status') == 'not_evaluated' and result.get('timing_status') == 'not_evaluated',
         'unsupported electrical/timing claim')
    need(result.get('context') == spec.get('context', {}), 'stale physical context')
    nets = {n['id']: n for n in spec['nets']}
    need(not set(result['routes']) & set(result['failed']) and
         set(result['routes']) | set(result['failed']) == set(nets), 'net coverage differs')
    need(all(r in ('grid_access_not_found', 'search_not_found', 'search_budget_exhausted')
             for r in result['failed'].values()), 'unsupported failure claim')
    need(result['status'] == ('partial' if result['failed'] else 'geometry_complete'), 'false complete claim')
    t = spec['technology']
    native = NativePins(spec)
    occupancy = Occupancy(t)
    occupancy.add([(o['layer'], o['rect']) for o in spec.get('obstacles', [])], None)
    length = 0
    cuts10 = cuts11 = 0
    for name, route in result['routes'].items():
        net = nets[name]
        if not net['sinks']:
            need(not any(route.values()), 'native-only net has unexpected route')
            continue
        shapes = []
        metal = []
        bridges = []
        pins = {}
        terminals = {net['driver'], *net['sinks']}
        def add_metals(items):
            indices = []
            for layer, rect in items:
                shapes.append((layer, rect))
                if layer.startswith('M'):
                    indices.append(len(metal))
                    metal.append((layer, rect))
            return indices
        grid = RoutingGrid(t, (spec['pins'][p] for p in [net['driver'], *net['sinks']]))
        def on_grid(a, b):
            need(grid.allows(a, b), 'route outside the declared coarse or local access grid')
        for s in route['segments']:
            a, b, layer = s['a'], s['b'], s['layer']
            on_grid(a, b)
            need((layer == 'M11' and a[1] == b[1] and a[0] != b[0]) or
                 (layer == 'M12' and a[0] == b[0] and a[1] != b[1]), 'invalid routing layer/direction')
            length += abs(a[0]-b[0])+abs(a[1]-b[1])
            add_metals([segment_shape(layer, a, b, t)])
        for v in route['via10']:
            pin, point = v['pin'], v['at']
            on_grid(point, point)
            need(pin in [net['driver']]+net['sinks'] and pin not in pins, 'foreign/duplicate via10 terminal')
            lower = box(point, t['via10']['cut']+2*t['via10']['lower_enclosure'])
            need(any(contains(rect, lower) for rect in spec['pins'][pin]), 'via10 not enclosed by actual M10 pin')
            need(native.exclusive(point, terminals), 'via10 could contact a foreign M10 pin')
            pins[pin] = add_metals(via_shapes('via10', point, t))[0]
            cuts10 += 1
        need(set(pins) == set([net['driver']]+net['sinks']), 'missing terminal access')
        need(len({tuple(v['at']) for v in route['via10']}) == len(pins), 'shared via10 landing')
        need(len({tuple(p) for p in route['via11']}) == len(route['via11']), 'duplicate via11')
        for point in route['via11']:
            on_grid(point, point)
            indices = add_metals(via_shapes('via11', point, t))
            bridges.append(tuple(indices))
            cuts11 += 1
        # Check actual shapes against fixed obstacles and all prior networks.
        # Commit individually to also validate cuts within the same network.
        for shape in shapes:
            need(occupancy.legal([shape], name), 'spacing/short/boundary violation')
            occupancy.add([shape], name)
        adjacency = [set() for _ in metal]
        for i, (layer, rect) in enumerate(metal):
            for j in range(i):
                if layer == metal[j][0] and touching(rect, metal[j][1]):
                    adjacency[i].add(j); adjacency[j].add(i)
        for a, b in bridges:
            adjacency[a].add(b); adjacency[b].add(a)
        seen = {pins[net['driver']]}
        pending = list(seen)
        while pending:
            i = pending.pop()
            for j in adjacency[i]-seen:
                seen.add(j); pending.append(j)
        need(all(i in seen for i in pins.values()), 'disconnected terminal')
        need(len(seen) == len(metal), 'disconnected copper island')
    return {'passed': True, 'nets_checked': len(result['routes']), 'wire_length_dbu': length,
            'via10_count': cuts10, 'via11_count': cuts11,
            'scope': 'declared two-layer rectangular rules and M10 enclosure; not foundry DRC/RC/STA'}
