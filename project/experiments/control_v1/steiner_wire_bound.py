"""Necessary rectilinear wire bound, never a routability certificate.

Doubling any connected Steiner tree gives a terminal tour of at most twice
its length. L1 shortcutting and then taking a metric MST cannot increase
that tour. Thus ceil(MST/2) is a lower bound in integer grid-edge units.
"""


def grid_tree_bound(points):
    points = list(dict.fromkeys(tuple(p) for p in points))
    assert points and all(len(p) == 2 and all(type(v) is int for v in p) for p in points)
    span = sum(max(p[d] for p in points) - min(p[d] for p in points) for d in (0, 1))
    distances = [None] * len(points)
    distances[0] = 0
    used = set()
    mst = 0
    for _ in points:
        j = min((i for i in range(len(points)) if i not in used and distances[i] is not None),
                key=lambda i: distances[i])
        used.add(j)
        mst += distances[j]
        x, y = points[j]
        for i, (xx, yy) in enumerate(points):
            if i not in used:
                candidate = abs(x - xx) + abs(y - yy)
                distances[i] = candidate if distances[i] is None else min(distances[i], candidate)
    return dict(hpwl_grid_edges=span, metric_mst_grid_edges=mst,
                necessary_wire_grid_edges=max(span, (mst + 1) // 2))
