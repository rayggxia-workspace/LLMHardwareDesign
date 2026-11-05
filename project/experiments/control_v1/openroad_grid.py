"""Reject rather than normalize OpenROAD wires outside the existing grid model."""
import collections
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def read(path, terminals, nx, ny):
    sys.path.insert(0, str(ROOT / 'project/experiments/block_v1'))
    from native_escape import records
    branches = {}
    occupied = {}
    edge_count = 0
    vias = 0
    for record in records(Path(path)):
        name = record.split()[1]
        assert name in terminals and name not in branches, ('Unexpected/duplicate net', name)
        assert record.count('+ ROUTED ') == 1, ('Missing/duplicate physical route', name)
        raw = record.split('+ ROUTED ', 1)[1].strip()
        assert raw.endswith(';')
        paths = []
        adjacency = collections.defaultdict(set)
        points = set()
        for chunk in re.split(r'\s+NEW\s+', raw[:-1].strip()):
            layer, body = chunk.split(None, 1)
            assert layer in ('metal11', 'metal12'), ('Noncustom layer', layer)
            level = int(layer == 'metal12')
            previous = None
            path_points = []
            pattern = r'\(\s*(-?\d+|\*)\s+(-?\d+|\*)(?:\s+(-?\d+))?\s*\)|(BV1_via11)'
            assert not re.sub(pattern, '', body).strip(), ('Unsupported route grammar', body)
            for match in re.finditer(pattern, body):
                xx, yy, extension, via = match.groups()
                if via:
                    assert previous is not None
                    assert (previous[0] + previous[1]) % 2 == 0, ('Noncheckerboard via', name, previous)
                    other = (previous[0], previous[1], 1-previous[2])
                    path_points.append(other)
                    previous = other
                    level = other[2]
                    vias += 1
                    continue
                assert extension is None or int(extension) in (0, 2000), ('Noncanonical extension', extension)
                assert previous is not None or (xx != '*' and yy != '*')
                if xx == '*':
                    x = previous[0]
                else:
                    assert (int(xx)-190) % 8000 == 0, ('Off-grid X', name, xx)
                    x = (int(xx)-190)//8000
                if yy == '*':
                    y = previous[1]
                else:
                    assert (int(yy)-140) % 8000 == 0, ('Off-grid Y', name, yy)
                    y = (int(yy)-140)//8000
                point = (x, y, level)
                if previous is None:
                    path_points.append(point)
                else:
                    assert previous[2] == level
                    # Existing tree_router.cpp and system_geometry.py permit
                    # both Manhattan directions on either layer. Keep that
                    # original model, including its stricter via parity rule.
                    assert previous[1] == y or previous[0] == x, ('Non-Manhattan wire', name, previous, point)
                    dx = (x > previous[0]) - (x < previous[0])
                    dy = (y > previous[1]) - (y < previous[1])
                    cursor = previous
                    while cursor != point:
                        cursor = (cursor[0]+dx, cursor[1]+dy, level)
                        path_points.append(cursor)
                previous = point
            assert path_points
            for v in path_points:
                x, y, layer = v
                assert 4 <= x < nx-4 and 4 <= y < ny-4, ('Outside existing route margin', name, v)
                assert occupied.setdefault(v, name) == name, ('Cross-net occupied vertex', name, v)
                points.add(v)
            for v, w in zip(path_points, path_points[1:]):
                assert sum(abs(a-b) for a, b in zip(v, w)) == 1
                adjacency[v].add(w)
                adjacency[w].add(v)
                edge_count += 1
            paths.append(path_points)
        ends = terminals[name]
        pins = [(*pt, 0) if len(pt) == 2 else tuple(pt) for pt in ends]
        assert all(len(pt) == 3 and pt[2] in (0, 1) for pt in pins)
        root = pins[0]
        seen = {root}
        todo = [root]
        while todo:
            for point in adjacency[todo.pop()]:
                if point not in seen:
                    seen.add(point)
                    todo.append(point)
        assert seen == points and all(pt in seen for pt in pins), ('Missing/unconnected actual sink', name)
        branches[name] = paths
    assert set(branches) == set(terminals), 'Skipped nets'
    return branches, dict(final_conflicts=0, independent_tree_flood=True,
                          independent_cross_net_occupancy=True, checked_edges=edge_count,
                          checked_vias=vias, net_count=len(terminals),
                          scope='Existing Manhattan 4um grid, original margin and checkerboard via checks; no coordinate repair or acceptance relaxation. Full actual geometry, spacing, PG and RC remain mandatory.')


def regression(out):
    """Exercise failures that must never be normalized into accepted geometry."""
    out.mkdir(exist_ok=False)
    base = '- a + ROUTED metal11 ( 64190 64140 ) ( 96190 * ) ;\n'
    terminals = {'a': [(8, 8), (12, 8)]}
    cases = [
        ('positive', base, terminals, True),
        ('offgrid', base.replace('96190', '96191'), terminals, False),
        ('diagonal', base.replace('( 96190 * )', '( 96190 96140 )'), terminals, False),
        ('margin', base.replace('96190', '8190'), {'a': [(8, 8), (1, 8)]}, False),
        ('missing-sink', base, {'a': [(8, 8), (13, 8)]}, False),
        ('missing-net', base, dict(terminals, b=[(8, 12), (12, 12)]), False),
        ('short', base + base.replace('- a ', '- b '), dict(terminals, b=terminals['a']), False),
        ('bad-via', base.replace('( 96190 * )', '( 72190 * ) BV1_via11'), terminals, False),
        ('unsupported-cut', base.replace('( 96190 * )', '( 96190 * ) GENERATED_VIA'), terminals, False),
        ('wrong-layer', base.replace('metal11', 'metal10'), terminals, False),
    ]
    results = []
    for name, raw, ends, expected in cases:
        path = out / (name + '.def')
        path.write_text('NETS ' + str(len(ends)) + ' ;\n' + raw + 'END NETS\n')
        try:
            read(path, ends, 48, 48)
        except AssertionError as error:
            assert not expected, (name, str(error))
            results.append(dict(name=name, rejected=True, error=str(error)))
        else:
            assert expected, ('Invalid input accepted', name)
            results.append(dict(name=name, accepted=True))
    result = dict(passed=True, cases=results, negative_cases=len(cases)-1)
    (out / 'receipt.json').write_text(json.dumps(result, indent=2) + '\n')
    return result
