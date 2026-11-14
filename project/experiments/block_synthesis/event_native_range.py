"""Lower independently committable native loop ranges for the event frontier."""
from collections import defaultdict
from math import prod

from event_deploy import digest
from streaming_ir import counts, primitive_body, seq


_POINTWISE = frozenset(('Convert', 'Product', 'Add', 'Maximum', 'Minimum', 'Select',
                        'MaskZero', 'MaskFloor', 'Compare', 'NExp'))
_REDUCE = frozenset(('Sum', 'SquareSum', 'Max', 'NFactor'))
_METADATA = frozenset(('Constant', 'View', 'Mask'))


def _row_grid(ops):
    """One invocation owns complete output rows and complete reductions."""
    if any(node['op'] in ('View', 'Mask') for node in ops):
        return None
    work = [node for node in ops if node['op'] not in _METADATA]
    if not work or any(node['op'] not in _POINTWISE | _REDUCE | {'Dot'}
                       or not node['shape'] for node in work):
        return None
    grid = tuple(work[0]['shape'][:-1])
    if any(tuple(node['shape'][:-1]) != grid for node in work):
        return None
    local = {node['id']: node for node in work}
    for node in work:
        for slot, name in enumerate(node['inputs']):
            if name in local and not _aligned(node, slot, local[name], grid):
                return None
    return grid


def _aligned(consumer, slot, producer, grid):
    shape = producer['shape']
    if not shape or tuple(shape[:-1]) != grid:
        return False
    if consumer['op'] in _POINTWISE:
        return shape[-1] in (1, consumer['shape'][-1])
    if consumer['op'] in _REDUCE or (consumer['op'] == 'Dot' and slot == 0):
        return shape[-1] == consumer['attributes']['length']
    return False


def feature_tile_words(hardware):
    """Leave at least three quarters of the smallest site for other windows."""
    return max(1, min(site['words'] for site in hardware['leaf_inventory'].values()) // 4)


def lower_ranges(event_ir, hardware, *, feature_words=None):
    """Use the same native loop leaves and final ACK once per finite range.

    Slicing begins and ends at independent output iterations. Addresses keep
    the original tensor shape and absolute scalar index. A feature tile covers
    columns of one output row and never shortens a Dot's reduction.
    Transparent masks preserve indices. General views, RHS matrix operands,
    and unsliced endpoints retain whole-value synchronization.
    """
    spec = hardware['event_model']
    library = spec['native_loop_library']
    program = library['program']
    nodes = {node['id']: node for node in program['instructions']}
    kernels = defaultdict(list)
    for node in program['instructions']:
        kernels[node['kernel']].append(node)
    tasks = {task['id']: task for task in event_ir['tasks']}
    grids = {name: grid for name in tasks if (grid := _row_grid(kernels[name])) is not None}
    if not grids:
        return event_ir, hardware

    def sources(value, aligned=True):
        source = nodes.get(value)
        if source is None or source['op'] == 'Constant':
            return
        if source['op'] in ('View', 'Mask'):
            yield from sources(source['inputs'][0], aligned and source['op'] == 'Mask')
        else:
            yield source, aligned

    aligned_edges = defaultdict(dict)
    for name, grid in grids.items():
        for node in kernels[name]:
            if node['op'] in _METADATA:
                continue
            for slot, operand in enumerate(node['inputs']):
                for source, aligned in sources(operand):
                    owner = source['kernel']
                    if owner in grids and owner != name:
                        old = aligned_edges[name].get(owner, True)
                        aligned_edges[name][owner] = (old and aligned and grids[owner] == grid
                                                      and _aligned(node, slot, source, grid))

    # Feature ranges keep complete Dot reductions and pointwise iterations.
    feature_extent = {}
    if feature_words is not None:
        if type(feature_words) is not int or feature_words < 1:
            raise ValueError('feature tile size must be positive')
        for name in grids:
            work = [node for node in kernels[name] if node['op'] not in _METADATA]
            extent = work[0]['shape'][-1]
            if extent <= feature_words or any(
                    node['op'] not in _POINTWISE | {'Dot'} or node['shape'][-1] != extent
                    or node['attributes'].get('predicate_source') is not None for node in work):
                continue
            local = {node['id'] for node in work}
            if any(node['op'] == 'Dot' and local.intersection(node['inputs']) for node in work):
                continue
            feature_extent[name] = extent

    def same_feature_edge(name, parent):
        if (name not in feature_extent or feature_extent.get(name) != feature_extent.get(parent)
                or not aligned_edges[name].get(parent, False)):
            return False
        seen = False
        for node in kernels[name]:
            for operand in node['inputs']:
                for source, aligned in sources(operand):
                    if source['kernel'] != parent:
                        continue
                    if (not aligned or node['op'] not in _POINTWISE
                            or source['shape'] != node['shape']):
                        return False
                    seen = True
        return seen

    feature_edges = {(name, parent) for name in feature_extent for parent in tasks[name]['after']
                     if same_feature_edge(name, parent)}
    feature_nodes = {node for edge in feature_edges for node in edge}
    row_nodes = {node for name, grid in grids.items() if prod(grid) > 1
                 for parent in tasks[name]['after'] if aligned_edges[name].get(parent, False)
                 and name not in feature_nodes and parent not in feature_nodes for node in (name, parent)}
    tiles = {}
    for name in row_nodes:
        extent = prod(grids[name])
        tiles[name] = [(0, extent // 2, None), (extent // 2, extent, None)]
    for name in feature_nodes:
        extent = feature_extent[name]
        tiles[name] = [(row, row + 1, [col, min(extent, col + feature_words)])
                       for row in range(prod(grids[name])) for col in range(0, extent, feature_words)]
    if not tiles:
        return event_ir, hardware
    parts = {name: tuple(f'{name}::range::{i}' for i in range(len(tiles[name])))
             if name in tiles else (name,) for name in tasks}
    if len({part for names in parts.values() for part in names}) != sum(map(len, parts.values())):
        raise ValueError('native range task name collision')
    services = {}
    lowered = []
    templates = library['templates']
    components = library['operands']
    ranges = {}
    for name, task in tasks.items():
        for index, part in enumerate(parts[name]):
            parents = []
            for parent in task['after']:
                if ((name, parent) in feature_edges or
                        (name in row_nodes and parent in row_nodes and aligned_edges[name].get(parent, False))):
                    parents.append(parts[parent][index])
                else:
                    parents.extend(parts[parent])
            if part == name:
                lowered.append({**task, 'after': sorted(set(parents))})
                for binding in task['bindings']:
                    service = binding['event_stages'][0]['service']
                    services[service] = spec['services'][service]
                continue
            # Both ranges use the owner's allocated temporary region. Reuse it
            # only after the previous range has committed and released it.
            if index:
                parents.append(parts[name][index - 1])
            lo, hi, columns = tiles[name][index]
            spans = {}
            for node in kernels[name]:
                if node['op'] in _METADATA:
                    continue
                stride = node['shape'][-1]
                spans[node['id']] = ([lo * stride, hi * stride] if columns is None else
                                     [lo * stride + columns[0], lo * stride + columns[1]])
            records = {}
            for value, (first, stop) in spans.items():
                region = library['primitive_regions'][value]
                if region.get('record_bytes') != 16 or stop > region['words']:
                    raise ValueError(f'{name}: native range exceeds its reserved output records')
                base = region['address_words']
                records[value] = [base + first, base + stop]
            descriptor = {'kernel': name, 'rows': [lo, hi], 'grid': list(grids[name]),
                          'output_indices': spans, 'commit_record_ranges': records}
            if columns is not None:
                descriptor['columns'] = columns
            ranges[part] = descriptor
            body = seq(*(primitive_body({**node, 'shape': [spans[node['id']][1] - spans[node['id']][0]]},
                                         components[node['id']])[0]
                         for node in kernels[name] if node['id'] in spans))
            stats = counts(body, templates)
            bindings = []
            for binding in task['bindings']:
                original_id = binding['event_stages'][0]['service']
                service = spec['services'][original_id]
                whole = counts(service['finite_loop']['body'], templates)
                extent = prod(grids[name])
                iterations = hi - lo
                if columns is not None:
                    extent *= feature_extent[name]
                    iterations *= columns[1] - columns[0]
                if any(stats[key] * extent != whole[key] * iterations for key in stats.keys() | whole.keys()):
                    raise ValueError(f'{name}: native range work differs from whole-loop work')
                ticks, remainder = divmod(service['ticks'] * iterations, extent)
                if remainder or not ticks:
                    raise ValueError(f'{name}: native range duration is not integral')
                memory = {
                    site: {direction: {**entry, 'bytes': entry['bytes'] * iterations // extent}
                           for direction, entry in directions.items()}
                    for site, directions in service['memory_by_site'].items()
                }
                reads = sum(item.get('read', {}).get('bytes', 0) for item in memory.values())
                writes = sum(item.get('write', {}).get('bytes', 0) for item in memory.values())
                new_id = part + '@' + binding['id']
                loop = {**service['finite_loop'], 'task_id': part, 'body': body,
                        'range': descriptor}
                # A whole-command binary encoder is not proof that it accepts
                # absolute iteration bounds. Physical admission requires its own region encoder.
                ranged_service = {**service, 'ticks': ticks, 'memory_by_site': memory,
                                  'read_bytes': reads, 'write_bytes': writes, 'finite_loop': loop}
                ranged_service.pop('native_providers', None)
                services[new_id] = ranged_service
                bindings.append({**binding, 'ticks': ticks, 'external_read_words': reads // 16,
                                 'external_write_words': writes // 16,
                                 'event_stages': [{'service': new_id}]})
            lowered.append({**task, 'id': part, 'tile_parent': name, 'after': sorted(set(parents)),
                            'bindings': bindings})
    resolved = {**hardware, 'event_model': {**spec, 'services': services, 'native_loop_library': {
        **library, 'dependencies': {task['id']: task['after'] for task in lowered},
        'ranges': ranges,
        'range_program_sha256': digest(ranges)}}}
    return {**event_ir, 'tasks': lowered}, resolved
