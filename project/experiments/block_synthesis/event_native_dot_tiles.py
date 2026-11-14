"""Offer measured full-K Dot tiles to the common event scheduler."""
from collections import Counter, defaultdict
from math import prod

from event_deploy import digest
from memory import descriptor_ticks
from streaming_ir import counts
from tile_recipe import cost


def lower_dot_tiles(ir, hardware):
    """Use declared P/E bindings and keep the scalar alternatives available."""
    profile = hardware.get('tile_service_profiles')
    declared = hardware.get('tile_service_bindings')
    if profile is None and declared is None:
        return ir, hardware
    if (not profile or not declared or profile.get('kind') != 'native-p-e-tile-services-v1'
            or declared.get('kind') != 'native-tile-instance-services-v1'
            or declared.get('qualification_sha256') != digest(profile) or not declared.get('evidence')):
        raise ValueError('explicit instance-to-qualified-service bindings required')
    inventory = hardware['leaf_inventory']
    for role, macro in (('P', 'M'), ('E', 'E')):
        if any(group not in inventory or macro not in inventory[group]['macros']
               for group in declared[role]):
            raise ValueError('declared tile service is unavailable on this inventory')
    spec = hardware['event_model']
    library = spec['native_loop_library']
    program = library['program']
    forms = program['initial_formats']
    kernels = defaultdict(list)
    for node in program['instructions']:
        if node['op'] not in ('Constant', 'Mask', 'View'):
            kernels[node['kernel']].append(node)
    services = spec['services'].copy()
    ranges = library.get('ranges', {})
    qualified = {tuple(shape) for shape in profile['shapes']}
    memory = hardware['virtual_memory']
    scalar = counts({'call': 'split32'}, library['templates'])
    origin = max((region['address_words'] + region['words'] for region in (
        *library['external_regions'].values(), *library['primitive_regions'].values(),
        *library['constants'].values(),
        *(item['finite_loop']['scratch_external'] for item in services.values()))), default=0)
    capacity = min(hardware.get('external_capacity_words', 1 << memory['address_bits']),
                   (1 << memory['address_bits']) // 16)
    constants = {'kind': 'native-tile-s16-basis-v1', 'address_words': origin, 'words': 9,
                 'records': [[0] * 8] + [[int(i == j) for j in range(8)] for i in range(8)]}
    base = origin + constants['words']
    prepared = {}
    lowered = []
    for task in ir['tasks']:
        span = ranges.get(task['id'], {})
        nodes = kernels[span.get('kernel', task['id'])]
        if len(nodes) != 1 or nodes[0]['op'] != 'Dot':
            lowered.append(task)
            continue
        node, = nodes
        weight = forms.get(node['inputs'][1], {})
        columns = node['shape'][-1]
        length = node['attributes']['length']
        shift = node['attributes']['shift']
        if (library['operands'][node['id']] != [3, 1] or not 0 <= shift <= 63
                or weight.get('bits') != 16 or weight.get('shape') != [length, columns]
                or not (weight.get('source_file') or 'literal' in weight)):
            lowered.append(task)
            continue
        start, stop = span.get('rows', (0, prod(node['shape'][:-1])))
        first, last = span.get('columns', (0, columns))
        rows, width = stop - start, last - first
        bindings = list(task['bindings'])
        need = 3 * prod(node['shape'][:-1]) * length
        if node['id'] not in prepared and base + need > capacity:
            lowered.append(task)
            continue
        for binding in task['bindings']:
            stage, = binding['event_stages']
            source = services[stage['service']]
            loop = source['finite_loop']
            p = binding['macro_binding'].get('M')
            e = binding['macro_binding'].get('E')
            if (p not in declared['P'] or e not in declared['E']
                    or stage.get('inputs')):
                continue
            pm, em = inventory[p], inventory[e]
            if pm['site'] == em['site']:
                continue
            p_site, e_site = pm['site'], em['site']
            # The measured recipe commits a canonical DDR result. A scalar
            # binding can publish a named handoff window instead, so leave it
            # available as the other candidate.
            outputs = stage.get('outputs', {})
            if outputs:
                continue
            if not {p_site, e_site} <= source['memory_by_site'].keys():
                continue

            choices = []
            for rt, ct in sorted({(min(r, rows), min(c, width)) for r, c in qualified}):
                try:
                    work = cost(rows, width, length, rt, ct, profile, memory, pm, em)
                except ValueError:
                    continue
                if (work['P_words'] > hardware['sites'][p_site]['words']
                        or work['E_words'] > hardware['sites'][e_site]['words']
                        or work['temporary_external_words'] > loop['scratch_external']['words']):
                    continue
                choices.append((work['ticks'], work['external_words'], rt, ct, work))
            if not choices:
                continue
            _, _, rt, ct, work = min(choices, key=lambda item: item[:4])
            if node['id'] not in prepared:
                prepared[node['id']] = {'address_words': base, 'words': need}
                base += need
            region = prepared[node['id']]
            # Legacy split32 writes high, negative-test, and flag. The
            # low component aliases the original SSA operand, so DMA reads
            # that original address when the tile requests component zero.
            prep_elems = rows * length
            quantities = {
                p_site: Counter(read=work['external_read_words'] - work.get('packed_outputs', 0),
                                write=work['external_write_words'] - work.get('flag_outputs', 0)),
                e_site: Counter(read=work.get('packed_outputs', 0), write=work.get('flag_outputs', 0)),
            }
            delta = 0
            for macro, meta in (('M', pm), ('E', em)):
                site = meta['site']
                reads, writes = scalar[macro + ':read'], scalar[macro + ':write']
                quantities[site].update(read=prep_elems * reads, write=prep_elems * writes)
                delta += prep_elems * (
                    scalar[macro + ':core'] + reads * (meta['io_read_ticks']
                        + descriptor_ticks(memory, 1, 'load', meta['io_write_ticks']))
                    + writes * (meta['io_write_ticks']
                        + descriptor_ticks(memory, 1, 'store', meta['io_read_ticks'])))
            ticks = work['ticks'] + delta
            memory_by_site = {
                site: {direction: {**source['memory_by_site'][site][direction], 'bytes': words * 16}
                       for direction, words in volume.items() if words}
                for site, volume in quantities.items() if any(volume.values())
            }
            read_bytes = sum(v['read'] for v in quantities.values()) * 16
            write_bytes = sum(v['write'] for v in quantities.values()) * 16
            tile = {'kind': 'prepared-s32-static-b-tile-v1', 'primitive': node['id'],
                    'rows': rows, 'columns': width, 'K': length, 'tile': [rt, ct],
                    'output_columns': [first, last], 'output_rows': [start, stop],
                    'final_shift': shift, 'B': node['inputs'][1],
                    'prepared_A_base': region['address_words'] + start * length * 3,
                    'prepare_elements': prep_elems, 'constant_base': origin,
                    'component_sources': ['original_A.low16', 'prepared_high16', 'prepared_negative_flag'],
                    'scratch_regions': {'P': [0, work['P_words']], 'E': [0, max(8, work['E_words'])]},
                    'temporary_external_region': loop['scratch_external']}
            bid = binding['id'] + ';native-dot-tile'
            sid = task['id'] + '@' + bid
            footprint = {p_site: work['P_words'], e_site: max(8, work['E_words'])}
            participants = {site: {**item, 'words': footprint[site]}
                            for site, item in loop['participants'].items()}
            service = {**source, 'ticks': ticks, 'read_bytes': read_bytes, 'write_bytes': write_bytes,
                       'memory_by_site': memory_by_site, 'finite_loop': {
                           **loop, 'body': {'native_dot_tile': tile}, 'participants': participants,
                           'dot_tile': tile, 'tile_work': work}}
            service.pop('native_providers', None)
            services[sid] = service
            bindings.append({**binding, 'id': bid, 'ticks': ticks, 'external_read_words': read_bytes // 16,
                             'external_write_words': write_bytes // 16, 'scratch_by_site': footprint,
                             'scratch_words': max(footprint.values()),
                             'event_stages': [{**stage, 'service': sid}]})
        lowered.append({**task, 'bindings': bindings})
    if len(services) == len(spec['services']):
        return ir, hardware
    return {**ir, 'tasks': lowered}, {**hardware, 'event_model': {
        **spec, 'services': services, 'native_loop_library': {
            **library, 'dot_tile_constants': constants, 'dot_tile_prepared_regions': prepared}}}
