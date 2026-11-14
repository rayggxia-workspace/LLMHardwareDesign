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
    if prod(grid) < 2 or any(tuple(node['shape'][:-1]) != grid for node in work):
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


def lower_ranges(event_ir, hardware):
    """Use the same native loop leaves and final ACK once per finite range.

    Slicing begins and ends at independent output iterations. Addresses keep
    the original tensor shape and use the output span's absolute scalar index.
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

    # Only split operators on an edge that can actually hand off a tile.
    endpoints = {node for name in grids for parent in tasks[name]['after']
                 if aligned_edges[name].get(parent, False) for node in (name, parent)}
    if not endpoints:
        return event_ir, hardware
    parts = {name: (f'{name}::range::0', f'{name}::range::1') if name in endpoints else (name,)
             for name in tasks}
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
                if (len(parts[name]) > 1 and len(parts[parent]) > 1
                        and aligned_edges[name].get(parent, False)):
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
            extent = prod(grids[name])
            lo, hi = (0, extent // 2) if index == 0 else (extent // 2, extent)
            spans = {node['id']: [lo * node['shape'][-1], hi * node['shape'][-1]]
                     for node in kernels[name] if node['op'] not in _METADATA}
            records = {}
            for value, (first, stop) in spans.items():
                region = library['primitive_regions'][value]
                if region.get('record_bytes') != 16 or stop > region['words']:
                    raise ValueError(f'{name}: native range exceeds its reserved output records')
                base = region['address_words']
                records[value] = [base + first, base + stop]
            descriptor = {'kernel': name, 'rows': [lo, hi], 'grid': list(grids[name]),
                          'output_indices': spans, 'commit_record_ranges': records}
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
                # Identical per-row leaf work including both DDR directions.
                if any(stats[key] * extent != whole[key] * (hi - lo) for key in stats.keys() | whole.keys()):
                    raise ValueError(f'{name}: native range work differs from whole-loop work')
                ticks, remainder = divmod(service['ticks'] * (hi - lo), extent)
                if remainder or not ticks:
                    raise ValueError(f'{name}: native range duration is not integral')
                memory = {
                    site: {direction: {**entry, 'bytes': entry['bytes'] * (hi - lo) // extent}
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
