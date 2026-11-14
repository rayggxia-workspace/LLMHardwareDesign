"""Functional interpreter for emitted, finite-loop control programs."""
from collections import defaultdict
from math import prod

from dot_cache_replay import order_program
from event_deploy import digest, loop_lease_edges
from wide_program import execute


def _verify_ranges(library):
    ranges = library.get('ranges', {})
    if not ranges:
        return
    if digest(ranges) != library.get('range_program_sha256'):
        raise ValueError('native range descriptors differ from their digest')
    owners = defaultdict(list)
    primitives = defaultdict(list)
    for node in library['program']['instructions']:
        if node['op'] not in ('Constant', 'View', 'Mask'):
            primitives[node['kernel']].append(node)
    for task, span in ranges.items():
        kernel, (lo, hi), grid = span['kernel'], span['rows'], span['grid']
        if (task not in library['dependencies'] or not 0 <= lo < hi <= prod(grid)
                or not primitives[kernel]
                or any(node['shape'][:-1] != grid for node in primitives[kernel])
                or span['output_indices'] != {node['id']: [lo * node['shape'][-1], hi * node['shape'][-1]]
                                             for node in primitives[kernel]}):
            raise ValueError('invalid native loop output range')
        regions = library['primitive_regions']
        expected = {}
        for value, (first, stop) in span['output_indices'].items():
            region = regions[value]
            if region.get('record_bytes') != 16 or stop > region['words']:
                raise ValueError('native range exceeds its reserved output records')
            base = region['address_words']
            expected[value] = [base + first, base + stop]
        if span['commit_record_ranges'] != expected:
            raise ValueError('native range commits different DDR records')
        owners[kernel].append((lo, hi, task))
    for kernel, parts in owners.items():
        stop, previous = 0, None
        for lo, hi, task in sorted(parts):
            if lo != stop or (previous and previous not in library['dependencies'][task]):
                raise ValueError('native range overlap, gap or missing scratch lifetime dependency')
            stop, previous = hi, task
        if stop != prod(primitives[kernel][0]['shape'][:-1]) or kernel in library['dependencies']:
            raise ValueError('incomplete or duplicate native range coverage')


def decode(program, hardware):
    """Validate dispatch and ACK order, returning whole primitives or a range trace."""
    spec = hardware['event_model']
    library = program['native_loop_library']
    if (program['schema'] != 'block-event-control/1'
            or program['source']['hardware_sha256'] != digest(hardware)
            or library != spec['native_loop_library']
            or library['integer_program_sha256'] != digest(library['program'])):
        raise ValueError('finite-loop program does not match its qualified hardware and arithmetic')
    _verify_ranges(library)
    ranges = library.get('ranges', {})
    if spec.get('native_sram_handoff'):
        from event_handoff_control import decode_handoff

        lease_edges = loop_lease_edges(program['mother'][:-1], hardware['resources'])
        ordered = decode_handoff(program, hardware, lease_edges)
        return {'instructions': library['program']['instructions'],
                'ranges': [(row['task_id'], ranges.get(row['task_id'])) for row in ordered]}
    by_sequence = defaultdict(dict)
    for group, commands in program['locals'].items():
        for command in commands:
            number = command['sequence']
            if group in by_sequence[number]:
                raise ValueError('duplicate finite-loop local command')
            by_sequence[number][group] = command

    dispatches = program['mother'][:-1]
    dispatched = {row['task_id']: row['sequence'] for row in dispatches}
    if len(dispatched) != len(dispatches) or dispatched.keys() != library['dependencies'].keys():
        raise ValueError('incomplete finite-loop program')
    lease_edges = loop_lease_edges(dispatches, hardware['resources'])
    finishes = {row['sequence']: row['estimated_end'] for row in dispatches}
    for number, dispatch in enumerate(dispatches):
        task = dispatch['task_id']
        parents = {dispatched[parent] for parent in library['dependencies'][task]} | lease_edges[number]
        commands = by_sequence.pop(number, {})
        if (dispatch['op'] != 'DISPATCH' or dispatch['sequence'] != number
                or dispatch['wait_for'] != sorted(parents)
                or any(finishes[parent] > dispatch['estimated_start'] for parent in parents)
                or dispatch['targets'] != sorted(commands) or not commands):
            raise ValueError('invalid finite-loop dispatch or ACK dependency')
        service_id = task + '@' + dispatch['binding_id']
        service = spec['services'][service_id]
        loop = service['finite_loop']
        if loop.get('range') != ranges.get(task):
            raise ValueError('finite-loop service differs from its native range')
        if (dispatch['leases'] != service['claims']
                or dispatch['estimated_end'] - dispatch['estimated_start'] != service['ticks']):
            raise ValueError('finite-loop dispatch duration or resource lease differs')
        if set(commands) != {item['control'] for item in loop['participants'].values()}:
            raise ValueError('finite-loop local target differs from its selected binding')
        for target, command in commands.items():
            if 'memory_by_site' in service:
                site = hardware['control_groups'][target]['site']
                if command.get('external_memory') != service['memory_by_site'].get(site, {}):
                    raise ValueError('finite-loop local memory demand differs from its selected binding')
            if (command['op'] != 'RUN_LOOP' or command['task_id'] != task
                    or command['binding_id'] != dispatch['binding_id'] or command['service'] != service_id
                    or command['required_completion'] != loop['completion'] or command['loop'] != loop
                    or command['roles'] != ['execute'] or command['read'] or command['write']):
                raise ValueError('finite-loop local descriptor differs from its selected binding')
    if by_sequence or program['mother'][-1] != {'op': 'END', 'wait_for': list(range(len(dispatches)))}:
        raise ValueError('incomplete finite-loop program')
    decision_order = [{'id': row['task_id']} for row in sorted(
        dispatches, key=lambda item: (item['estimated_start'], item['sequence']))]
    if ranges:
        return {'instructions': library['program']['instructions'],
                'ranges': [(row['id'], ranges.get(row['id'])) for row in decision_order]}
    ordered = order_program(library['program'], {'tasks': decision_order})
    if len(ordered['instructions']) != len(library['program']['instructions']):
        raise ValueError('finite-loop program lost integer instructions')
    return ordered


def replay(program, hardware, initial, ids, oracle):
    """Execute the selected control order with the qualified integer arithmetic."""
    decoded = decode(program, hardware)
    if 'ranges' in decoded:
        from event_range_replay import replay_ranges

        return replay_ranges(program['native_loop_library']['program'], decoded['ranges'], initial, ids, oracle)
    return execute(decoded, initial, ids, oracle)
