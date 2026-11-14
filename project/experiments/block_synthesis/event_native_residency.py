"""Register finite SRAM handoffs for native ranges in the existing event DP."""
from collections import defaultdict

from memory import descriptor_ticks


WRITE_RESULT = frozenset(('Dot', 'Product', 'Convert', 'Add'))
READ_SOURCE = frozenset(('Dot', 'Product', 'Convert', 'Add'))


def lower_residency(ir, hardware, *, spill=False):
    spec = hardware['event_model']
    library = spec['native_loop_library']
    ranges = library.get('ranges', {})
    if not ranges or spec['windows'] or spec['value_bytes']:
        return ir, hardware
    program = library['program']
    nodes = {node['id']: node for node in program['instructions']}
    task_by_id = {task['id']: task for task in ir['tasks']}
    by_kernel = defaultdict(dict)
    for task, span in ranges.items():
        by_kernel[span['kernel']][tuple(span['rows'])] = task
    readers = defaultdict(list)
    for node in nodes.values():
        for slot, name in enumerate(node['inputs']):
            readers[name].append((node, slot))

    max_window_bytes = max(site['bytes'] for site in hardware['sites'].values()) - 8 * 16
    # Keep a named output only when every read can be explicitly redirected
    # to the same row partition. Views, graph outputs and other uses stay DDR.
    candidates = {}
    for task, span in ranges.items():
        for value, (lo, hi) in span['output_indices'].items():
            node = nodes[value]
            accesses = readers[value]
            if ((hi - lo) * 16 > max_window_bytes
                    or node['op'] not in WRITE_RESULT or value in program['outputs'].values()
                    or not accesses):
                continue
            uses = defaultdict(set)
            for user, slot in accesses:
                dest = by_kernel[user['kernel']].get(tuple(span['rows']))
                if (dest is None or dest == task or task not in task_by_id[dest]['after']
                        or user['op'] not in READ_SOURCE or ranges[dest]['grid'] != span['grid']
                        or user['id'] not in ranges[dest]['output_indices']
                        or (user['op'] == 'Dot' and (slot != 0 or node['shape'][-1] != user['attributes']['length']))
                        or (user['op'] != 'Dot' and node['shape'][-1] not in (1, user['shape'][-1]))):
                    break
                split = user['op'] == 'Add' or library['operands'][user['id']][slot] == 3
                uses[dest].update(('M', 'E') if split else ('M',))
            else:
                candidates[task, value] = (lo, hi, uses)
    if not candidates:
        return ir, hardware

    endpoints = {meta['site']: (group, meta) for group, meta in hardware['leaf_inventory'].items()}
    sites_for = defaultdict(set)
    touch = defaultdict(set)
    scratch_by_site = defaultdict(int)
    for item, (_, _, uses) in candidates.items():
        writer, _ = item
        for task, macros in {writer: {'M'}, **uses}.items():
            for binding in task_by_id[task]['bindings']:
                for site, words in binding['scratch_by_site'].items():
                    scratch_by_site[site] = max(scratch_by_site[site], words * 16)
                for macro in macros:
                    site = hardware['leaf_inventory'][binding['macro_binding'][macro]]['site']
                    sites_for[item].add(site)
                    touch[task, site].add(item)

    # Color simultaneous operand uses into distinct finite windows. Otherwise
    # windows are reusable, with eviction/writeback and lifetime enforced by DP.
    windows, locations, selected = {}, {}, set()
    for item, (lo, hi, uses) in sorted(candidates.items(), key=lambda pair: (
            -(pair[1][1] - pair[1][0]), pair[0])):
        size = (hi - lo) * 16
        allocations = {}
        for site in sorted(sites_for[item]):
            slots = locations.get(site, ())
            related = set().union(*(items for (task, owner), items in touch.items()
                                     if owner == site and item in items))
            # The two ranges of an operator may both be live before either consumer runs.
            related.update(other for other in selected if other[1] == item[1])
            slot = next((i for i, (length, assigned) in enumerate(slots)
                         if size <= length and not related.intersection(assigned)), None)
            if slot is None:
                scratch_bytes = scratch_by_site[site]
                if scratch_bytes + sum(length for length, _ in slots) + size > hardware['sites'][site]['bytes']:
                    break
                slot = len(slots)
            allocations[site] = slot
        else:
            selected.add(item)
            for site, slot in allocations.items():
                slots = locations.setdefault(site, [])
                if slot == len(slots):
                    slots.append((size, set()))
                slots[slot][1].add(item)
    if not selected:
        return ir, hardware

    window_for = {}
    for site, slots in locations.items():
        offset = scratch_by_site[site]
        for i, (size, items) in enumerate(slots):
            name = f'{site}.handoff.{i}'
            windows[name] = {'site': site, 'offset': offset, 'bytes': size}
            for item in items:
                window_for[site, item] = name
            offset += size

    inputs, outputs = defaultdict(dict), defaultdict(dict)
    value_bytes, addresses = {}, {}
    for task, value in sorted(selected):
        lo, hi, uses = candidates[task, value]
        version = f'{value}@{task}'
        value_bytes[version] = (hi - lo) * 16
        addresses[version] = ranges[task]['commit_record_ranges'][value][0] * 16
        outputs[task][version] = (task, value)
        for user, macros in uses.items():
            inputs[user][version] = ((task, value), macros)

    services = spec['services'].copy()
    tasks = []
    profile = hardware['virtual_memory']
    for task in ir['tasks']:
        name = task['id']
        bindings = []
        for binding in task['bindings']:
            stage, = binding['event_stages']
            service = services[stage['service']]
            claims = service['claims']
            local_in, local_out, removed = {}, {}, defaultdict(lambda: defaultdict(int))
            for version, (item, macros) in sorted(inputs[name].items()):
                for macro in sorted(macros):
                    site = hardware['leaf_inventory'][binding['macro_binding'][macro]]['site']
                    window = window_for[site, item]
                    if window not in local_in:
                        local_in[window] = version
                        removed[site]['read'] += value_bytes[version] // 16
            for version, item in outputs[name].items():
                site = hardware['leaf_inventory'][binding['macro_binding']['M']]['site']
                local_out[window_for[site, item]] = version
                removed[site]['write'] += value_bytes[version] // 16
            if not removed:
                bindings.append(binding)
                continue
            memory = {}
            ticks = service['ticks']
            for site, directions in service['memory_by_site'].items():
                _, meta = endpoints[site]
                remaining = {}
                for direction, entry in directions.items():
                    words = removed[site].get(direction, 0)
                    available = entry['bytes'] // 16
                    if words > available:
                        raise ValueError(f'{name}: SRAM boundary exceeds modeled DDR work')
                    mode, port = ('load', 'io_write_ticks') if direction == 'read' else ('store', 'io_read_ticks')
                    ticks -= words * descriptor_ticks(profile, 1, mode, meta[port])
                    if words < available:
                        remaining[direction] = {**entry, 'bytes': (available - words) * 16}
                if remaining:
                    memory[site] = remaining
            if any(set(directions) - service['memory_by_site'].get(site, {}).keys()
                   for site, directions in removed.items()) or ticks < 1:
                raise ValueError(f'{name}: SRAM boundary has no matching modeled DDR work')
            read_bytes = sum(traffic.get('read', {}).get('bytes', 0) for traffic in memory.values())
            write_bytes = sum(traffic.get('write', {}).get('bytes', 0) for traffic in memory.values())
            loop = {**service['finite_loop'], 'sram_handoff': {
                'inputs': local_in, 'outputs': local_out},
                'completion': 'native_loop_final_ack'}
            services[stage['service']] = {**service, 'ticks': ticks, 'claims': claims, 'finite_loop': loop,
                                          'memory_by_site': memory, 'read_bytes': read_bytes,
                                          'write_bytes': write_bytes}
            bindings.append({**binding, 'ticks': ticks, 'external_read_words': read_bytes // 16,
                             'external_write_words': write_bytes // 16, 'event_stages': [{
                                 **stage, 'inputs': local_in, 'outputs': local_out,
                                 **({'input_policy': 'backing', 'backed_outputs': sorted(local_out)} if spill else {}),
                             }]})
        tasks.append({**task, 'bindings': bindings})

    # Calibrate fallback to the same per-record DDR descriptor cost as the
    # original loops. Cross-site COPY requires an explicitly supplied route.
    routes = {name: route for name, route in spec['routes'].items()
              if route['src'] in locations and route['dst'] in locations}
    # Model-side DDR endpoints use the native loop's logical DMA interface.
    nets = hardware['nets'].copy()
    for site in sorted(locations):
        group, meta = endpoints[site]
        channel = meta['memory_group'] % profile['channels']
        claims = {meta['io_resource']: 1, group + '.LC.service': 1,
                  f'virtual-memory.channel.{channel}': 1}
        for direction, src, dst, port in (
                ('load', 'DDR', site, 'io_write_ticks'), ('store', site, 'DDR', 'io_read_ticks')):
            base = descriptor_ticks(profile, 1, direction, meta[port])
            name = f'{site}.handoff.{direction}'
            net = f'{site}.io.{direction}'
            nets.setdefault(net, {'cost': 1, 'fixed': False, 'unit': 'logical interface bundle',
                                  'qualification': 'unbound pin demand'})
            routes[name] = {'src': src, 'dst': dst, 'bytes_per_tick': 16,
                            'setup': 0, 'ticks_per_word': base, 'claims': claims,
                            'nets': [net]}
    active = {**hardware, 'nets': nets, 'event_model': {**spec, 'services': services, 'windows': windows,
              'routes': routes, 'value_bytes': value_bytes, 'external_addresses': addresses,
              'external_alignment_bytes': 16, 'native_sram_handoff': True}}
    return {**ir, 'tasks': tasks}, active
