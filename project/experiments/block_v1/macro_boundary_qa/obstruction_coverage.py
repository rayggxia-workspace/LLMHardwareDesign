"""Exact integer rectangle-union coverage of source occupancy by abstract OBS.

Pin windows are exemptions only on the same layer and on the actual source
net connected to that port. This checks source exported LEF/ODB occupancy,
not hidden transistor/GDS geometry or routing/DRC correctness.
"""
from collections import Counter, defaultdict

from audit import rectangle, require


def covered(target, rectangles):
    x0, y0, x1, y1 = target
    events = defaultdict(list)
    for a, b, c, d in rectangles:
        if a <= x0 and b <= y0 and c >= x1 and d >= y1:
            return True
        left, bottom, right, top = max(a, x0), max(b, y0), min(c, x1), min(d, y1)
        if left < right and bottom < top:
            events[left].append(((bottom, top), 1))
            events[right].append(((bottom, top), -1))
    active = Counter()
    points = sorted(set(events) | {x0, x1})
    for index, x in enumerate(points[:-1]):
        for interval, change in events[x]:
            active[interval] += change
            if active[interval] == 0:
                del active[interval]
        require(all(count > 0 for count in active.values()), "invalid coverage sweep")
        if points[index+1] <= x:
            continue
        reached = y0
        for bottom, top in sorted(active):
            if bottom > reached:
                break
            reached = max(reached, top)
            if reached >= y1:
                break
        if reached < y1:
            return False
    return True


def inspect(source_rows, lef_rows):
    # A callable supplies a fresh iterator for each pass. Large native TSVs
    # retain only net/port metadata, never millions of geometry tuples.
    if callable(source_rows):
        source_factory = source_rows
    else:
        saved_rows = list(source_rows)
        source_factory = lambda: iter(saved_rows)
    obstacles, windows = defaultdict(list), defaultdict(list)
    for row in lef_rows:
        if row[0] == "obstruction":
            obstacles[row[1]].append(rectangle(row[2:]))
        elif row[0] == "box":
            windows[(row[1], row[2])].append(rectangle(row[3:]))
    require(obstacles, "empty abstract obstruction inventory")
    nets, ports, source_count, dbu = {}, defaultdict(list), 0, None
    for row in source_factory():
        if row[0].startswith("# block-v1-odb-geometry/1"):
            require(dbu is None and row == ["# block-v1-odb-geometry/1 dbu_per_um=2000"], "source geometry units/header")
            dbu = 2000
        elif row[0].startswith("# NET "):
            _, _, alias, name = row[0].split()
            require(alias not in nets, "duplicate geometry net")
            nets[alias] = bytes.fromhex(name).decode("utf-8")
        elif row[0].startswith("# PORT "):
            _, _, alias, name = row[0].split()
            decoded = bytes.fromhex(name).decode("utf-8")
            require(decoded not in ports[alias], "duplicate geometry port")
            ports[alias].append(decoded)
        elif row[0].startswith("#"):
            raise ValueError("unknown geometry metadata")
        else:
            require(len(row) == 7, "source occupancy row arity")
            source_count += 1
    require(dbu == 2000 and source_count and nets, "empty/untyped source occupancy")
    require(set(ports) <= nets.keys(), "unresolved source port net")
    uncovered, uncovered_count, count = [], 0, 0
    by_layer = Counter()
    native_layers = {f"metal{i}" for i in range(1, 11)} | {f"via{i}" for i in range(1, 10)}
    reread_count = 0
    for row in source_factory():
        if row[0].startswith("#"):
            continue
        require(len(row) == 7, "source occupancy reread arity")
        alias, layer, kind, *coords = row
        require(layer in native_layers, "source nonnative layer")
        box = rectangle(coords)
        reread_count += 1
        require(alias in nets, "unresolved geometry net")
        # Abstract via cut OBS are not required: adjacent metal OBS provide
        # normal route/via keepouts. Preserve cut counts separately.
        by_layer[layer] += 1
        if layer.startswith("via"):
            continue
        count += 1
        allowed = obstacles[layer] + [rect for name in ports[alias] for rect in windows[(name, layer)]]
        if not covered(box, allowed):
            uncovered_count += 1
            if len(uncovered) < 100:
                uncovered.append({"net_or_owner": nets[alias], "layer": layer, "kind": kind, "bbox_dbu": list(box)})
    require(reread_count == source_count, "source geometry changed between passes")
    return {"schema": "block-v1-abstract-occupancy-coverage/1", "passed": uncovered_count == 0,
            "checked_source_metal_rectangles": count, "source_shapes_by_layer": dict(by_layer),
            "uncovered_count": uncovered_count, "uncovered_examples": uncovered,
            "hidden_gds_geometry_qualified": False, "qualified_hard_macro": False,
            "scope": "Exact union coverage of exported source occupancy and same-net pin windows; via cuts counted, hidden GDS geometry and DRC not qualified"}
