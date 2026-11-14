"""Expand qualified, aligned tensor slices into ordinary frontier tasks."""
from collections import Counter, defaultdict, deque
from itertools import combinations, product
from copy import deepcopy

from solver import Unsupported


def lower_tiles(model, groups):
    """Keep each operator's tile order and expose cross-operator interleaving.

    The hardware must qualify each sliced recipe against its exact operator,
    attributes, tensor signatures and slice coordinates. Outside operands
    remain whole. Any tiled value visible outside the group is joined.
    """
    graph = deepcopy(model)
    values = graph['values']
    nodes = {node['id']: node for node in graph['tasks']}
    if len(nodes) != len(graph['tasks']):
        raise Unsupported('duplicate graph node')
    counts = Counter(value for node in nodes.values() for value in node['outputs'])
    users = Counter(value for node in nodes.values() for value in node['inputs'])
    tile_specs, order, owners, used = {}, {}, {}, set()
    for group in groups:
        if not isinstance(group, dict) or set(group) != {'nodes', 'axes', 'tile_size'}:
            raise Unsupported('tile group requires nodes, axes and tile_size')
        names, axes, step = group['nodes'], group['axes'], group['tile_size']
        if (not isinstance(names, list) or not names or any(not isinstance(n, str) for n in names)
                or len(set(names)) != len(names) or set(names) & used
                or not set(names) <= nodes.keys() or not isinstance(axes, dict)
                or type(step) is not int or step < 1):
            raise Unsupported('invalid or overlapping tile group')
        selected = [nodes[name] for name in names]
        outputs = [value for node in selected for value in node['outputs']]
        if not outputs or any(counts[value] != 1 for value in outputs) or set(outputs) != axes.keys():
            raise Unsupported('tile axes must name every group output exactly once')
        if set(outputs) & set(graph['inputs']):
            raise Unsupported('tile group output aliases a graph input')
        outside = set(graph['outputs'])
        inside_count = Counter(value for node in selected for value in node['inputs'])
        outside.update(value for value in outputs if users[value] > inside_count[value])
        if not any(inside_count[v] for v in outputs):
            raise Unsupported('tile group needs a producer-consumer edge')
        extents = set()
        for value, axis in axes.items():
            desc = values.get(value, {})
            shape = desc.get('shape')
            if (not isinstance(shape, (list, tuple))
                    or any(type(d) is not int or d < 1 for d in shape)
                    or type(axis) is not int or not 0 <= axis < len(shape)
                    or 'storage_bytes' in desc):
                raise Unsupported(f'{value}: tile axis needs a concrete unpacked tensor')
            extents.add(shape[axis])
        if len(extents) != 1 or step >= next(iter(extents)):
            raise Unsupported('tile axes need the same extent and at least two tiles')
        extent = extents.pop()
        parts = {value: [] for value in outputs}
        previous = {}
        used.update(names)
        for name in names:
            del nodes[name]
        for lo in range(0, extent, step):
            hi = min(lo + step, extent)
            slices = {}
            for value, axis in axes.items():
                part = f'{value}::tile::{lo}:{hi}'
                if part in values:
                    raise Unsupported(f'generated tile value already exists: {part}')
                shape = list(values[value]['shape'])
                shape[axis] = hi - lo
                values[part] = {**values[value], 'shape': shape}
                parts[value].append(part)
                slices[value] = part
            for node in selected:
                name = node['id']
                tile = f'{name}::tile::{lo}:{hi}'
                if tile in nodes or tile in used:
                    raise Unsupported(f'generated tile task already exists: {tile}')
                inputs, results = node['inputs'], node['outputs']
                nodes[tile] = {**node, 'id': tile,
                               'inputs': [slices.get(value, value) for value in inputs],
                               'outputs': [slices[value] for value in results]}
                owners[tile] = name
                tile_specs[tile] = {'start': lo, 'stop': hi,
                                    'input_axes': [axes.get(value) for value in inputs],
                                    'output_axes': [axes[value] for value in results]}
                if name in previous:
                    order[tile] = [previous[name]]
                previous[name] = tile
        for value in outputs:
            if value not in outside:
                continue
            join = f'{value}::tile_join'
            if join in nodes or join in used:
                raise Unsupported(f'generated tile join already exists: {join}')
            nodes[join] = {'id': join, 'op': 'Concat', 'attributes': {'axis': axes[value]},
                           'inputs': parts[value], 'outputs': [value]}
    graph['tasks'] = list(nodes.values())
    return graph, tile_specs, order, owners


def discover_tiles(model, recipes, signature, limit):
    """Find pairwise compatible complete slice families and joinable regions."""
    values, nodes = model['values'], {n['id']: n for n in model['tasks']}
    if len(nodes) != len(model['tasks']):
        return []
    by_op, by_profile = defaultdict(list), set()
    for recipe in recipes:
        by_op[recipe.get('domain', ''), recipe['op']].append(recipe)
        if recipe.get('tile') is None and not recipe.get('domain') and recipe['op'] == 'Concat':
            by_profile.add(_freeze((recipe['inputs'], recipe['outputs'], recipe.get('attributes', {}))))
    producers = {v: n['id'] for n in nodes.values() for v in n['outputs']}
    consumers = defaultdict(set)
    for n in nodes.values():
        for v in n['inputs']:
            consumers[v].add(n['id'])
    outputs = set(model['outputs'])
    families = {}
    for name, node in nodes.items():
        candidates = {}
        for recipe in by_op[node.get('domain', ''), node['op']]:
            tile = recipe.get('tile')
            if not tile or recipe.get('attributes', {}) != node.get('attributes', {}):
                continue
            if not isinstance(tile, dict) or set(tile) != {'start', 'stop', 'input_axes', 'output_axes'}:
                continue
            lo, hi = tile['start'], tile['stop']
            if type(lo) is not int or type(hi) is not int or not 0 <= lo < hi:
                continue
            if not all(isinstance(tile[key], (list, tuple)) for key in ('input_axes', 'output_axes')):
                continue
            ia, oa = tuple(tile['input_axes']), tuple(tile['output_axes'])
            if any(axis is not None and type(axis) is not int for axis in (*ia, *oa)):
                continue
            if not oa or None in oa:
                continue
            inputs, result = node['inputs'], node['outputs']
            if len(ia) != len(inputs) or len(oa) != len(result):
                continue
            profiles = []
            extents = set()
            if any(len({a for v, a in zip(inputs, ia) if v == value}) != 1 for value in set(inputs)):
                continue
            for value, axis in zip((*inputs, *result), (*ia, *oa)):
                desc = values.get(value)
                if desc is None:
                    break
                profile = signature(desc)
                if axis is not None:
                    shape = profile['shape']
                    if ('storage_bytes' in desc or not shape or type(axis) is not int
                            or not 0 <= axis < len(shape) or type(shape[axis]) is not int
                            or hi > shape[axis]):
                        break
                    extents.add(shape[axis])
                    profile['shape'] = [*shape[:axis], hi - lo, *shape[axis + 1:]]
                profiles.append(profile)
            else:
                if (len(extents) == 1 and profiles[:len(ia)] == recipe['inputs']
                        and profiles[len(ia):] == recipe['outputs']):
                    extent, = extents
                    candidates.setdefault((ia, oa, extent), set()).add((lo, hi))
        options = []
        for (ia, oa, extent), spans in candidates.items():
            for step in sorted(hi for lo, hi in spans if lo == 0 and hi < extent):
                if all((lo, min(extent, lo + step)) in spans for lo in range(0, extent, step)):
                    options.append((dict(zip(node['inputs'], ia)), dict(zip(node['outputs'], oa)), extent, step))
        if options:
            families[name] = options

    def joinable(value, axis, extent, step):
        out = signature(values[value])
        shape = out['shape']
        parts = [{**out, 'shape': [*shape[:axis], min(step, extent - lo), *shape[axis + 1:]]}
                 for lo in range(0, extent, step)]
        return _freeze((parts, [out], {'axis': axis})) in by_profile

    def group_for(members, choices):
        extent, step = choices[0][2:]
        if any(choice[2:] != (extent, step) for choice in choices):
            return None
        axes = {v: a for choice in choices for v, a in choice[1].items()}
        for choice in choices:
            for value, axis in choice[0].items():
                if axes.get(value) != axis:
                    return None
        for value, axis in axes.items():
            if (value in outputs or consumers[value] - members) and not joinable(value, axis, extent, step):
                return None
        return {'nodes': sorted(members), 'axes': axes, 'tile_size': step}

    # Discover connected groups across the graph. Start with maximal compatible
    # components, then consider their connected subsets within the trial budget.
    candidates = {}
    for name, choices in families.items():
        for choice in choices:
            candidates.setdefault(choice[2:], {}).setdefault(name, []).append(choice)

    def adjacent(choice, variant):
        return any(variant[0].get(v) == a for v, a in choice[1].items() if v in variant[0]) or any(
            choice[0].get(v) == a for v, a in variant[1].items() if v in choice[0])

    seeds = []
    for grid, options in sorted(candidates.items()):
        neighbors = {name: set() for name in options}
        for other, variants in options.items():
            for value in nodes[other]['inputs']:
                name = producers.get(value)
                if name != other and name in options and any(
                        adjacent(c, v) for c in options[name] for v in variants):
                    neighbors[name].add(other)
                    neighbors[other].add(name)
        remaining = set(options)
        while remaining:
            region = {min(remaining)}
            queue = list(region)
            while queue:
                new = neighbors[queue.pop()] - region
                region.update(new)
                queue.extend(sorted(new))
            remaining -= region
            if len(region) > 1:
                seeds.append((tuple(sorted(region)), grid, options, neighbors))

    found = {}
    queue = deque(sorted(seeds, key=lambda seed: (-len(seed[0]), seed[0], seed[1])))
    visited = {(subset, grid) for subset, grid, _, _ in queue}
    # Bound rejected layouts too. A graph may have exponentially many subsets.
    attempts = 0
    budget = max(limit * 32, len(queue))
    while queue and attempts < budget:
        subset, grid, options, neighbors = queue.popleft()
        for choices in product(*(options[name] for name in subset)):
            attempts += 1
            group = group_for(set(subset), choices)
            if group is not None:
                found[_freeze(group)] = group
            if attempts >= budget or len(found) >= limit:
                break
        if len(found) >= limit:
            break
        if len(subset) > 2:
            for smaller in combinations(subset, len(subset) - 1):
                if (smaller, grid) in visited:
                    continue
                visited.add((smaller, grid))
                members = set(smaller)
                reached = {smaller[0]}
                todo = list(reached)
                while todo:
                    new = (neighbors[todo.pop()] & members) - reached
                    reached.update(new)
                    todo.extend(new)
                if reached == members:
                    queue.append((smaller, grid, options, neighbors))
    return sorted(found.values(), key=lambda g: (-len(g['nodes']), g['nodes'], g['tile_size'],
                                                  sorted(g['axes'].items())))


def _freeze(value):
    if isinstance(value, dict):
        return tuple((k, _freeze(v)) for k, v in sorted(value.items()))
    if isinstance(value, (tuple, list)):
        return tuple(map(_freeze, value))
    return value


def tile_layouts(groups, limit):
    """Enumerate bounded, disjoint regions and retain the whole graph option."""
    if not groups:
        return []
    layouts, active = [], set()
    combined = []
    for group in groups:
        if not active.intersection(group['nodes']):
            combined.append(group)
            active.update(group['nodes'])
    if len(combined) > 1:
        layouts.append(combined)
    layouts.extend([group] for group in groups[:limit - len(layouts)])
    return layouts
