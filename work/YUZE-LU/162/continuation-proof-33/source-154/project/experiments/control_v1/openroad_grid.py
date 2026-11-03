"""Reject rather than normalize OpenROAD wires outside the existing grid model."""
import collections
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
                    assert (previous[1] == y if level == 0 else previous[0] == x), ('Wrong-way wire', name, previous, point)
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
        root = (*ends[0], 0)
        seen = {root}
        todo = [root]
        while todo:
            for point in adjacency[todo.pop()]:
                if point not in seen:
                    seen.add(point)
                    todo.append(point)
        assert seen == points and all((*xy, 0) in seen for xy in ends), ('Missing/unconnected actual sink', name)
        branches[name] = paths
    assert set(branches) == set(terminals), 'Skipped nets'
    return branches, dict(final_conflicts=0, independent_tree_flood=True,
                          independent_cross_net_occupancy=True, checked_edges=edge_count,
                          checked_vias=vias, net_count=len(terminals),
                          scope='Strict existing preferred-direction 4um grid, original margin and checkerboard via checks; no coordinate repair or acceptance relaxation. Full actual geometry, spacing, PG and RC remain mandatory.')
