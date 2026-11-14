"""Expand qualified, aligned tensor slices into ordinary frontier tasks."""
from collections import Counter
from copy import deepcopy

from solver import Unsupported


def lower_tiles(model, groups):
    """Keep each operator's tile order and expose cross-operator interleaving.

    The hardware must qualify each sliced recipe against its exact operator,
    attributes, tensor signatures and slice coordinates. Outside operands
    remain whole. Any tiled value visible outside the group is joined.
    """
    if not isinstance(groups, (list, tuple)):
        raise Unsupported('tile_groups must be a list')
    graph = deepcopy(model)
    values = graph['values']
    nodes = {node['id']: node for node in graph['tasks']}
    if len(nodes) != len(graph['tasks']):
        raise Unsupported('duplicate graph node')
    counts = Counter(value for node in nodes.values() for value in node['outputs'])
    users = Counter(value for node in nodes.values() for value in node['inputs'])
    tile_specs, order, used = {}, {}, set()
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
    return graph, tile_specs, order
