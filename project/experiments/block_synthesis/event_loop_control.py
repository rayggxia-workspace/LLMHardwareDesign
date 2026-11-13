"""Functional interpreter for emitted, finite-loop control programs."""
from collections import defaultdict

from dot_cache_replay import order_program
from event_deploy import digest, loop_lease_edges
from wide_program import execute


def decode(program, hardware):
    """Resolve issued loops and check their program order and ACK dependencies."""
    spec = hardware['event_model']
    library = program['native_loop_library']
    if (program['schema'] != 'block-event-control/1'
            or program['source']['hardware_sha256'] != digest(hardware)
            or library != spec['native_loop_library']
            or library['integer_program_sha256'] != digest(library['program'])):
        raise ValueError('finite-loop program does not match its qualified hardware and arithmetic')
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
        if (dispatch['leases'] != service['claims']
                or dispatch['estimated_end'] - dispatch['estimated_start'] != service['ticks']):
            raise ValueError('finite-loop dispatch duration or resource lease differs')
        if set(commands) != {item['control'] for item in loop['participants'].values()}:
            raise ValueError('finite-loop local target differs from its selected binding')
        for command in commands.values():
            if (command['op'] != 'RUN_LOOP' or command['task_id'] != task
                    or command['binding_id'] != dispatch['binding_id'] or command['service'] != service_id
                    or command['required_completion'] != loop['completion'] or command['loop'] != loop
                    or command['roles'] != ['execute'] or command['read'] or command['write']):
                raise ValueError('finite-loop local descriptor differs from its selected binding')
    if by_sequence or program['mother'][-1] != {'op': 'END', 'wait_for': list(range(len(dispatches)))}:
        raise ValueError('incomplete finite-loop program')
    decision_order = [{'id': row['task_id']} for row in sorted(
        dispatches, key=lambda item: (item['estimated_start'], item['sequence']))]
    ordered = order_program(library['program'], {'tasks': decision_order})
    if len(ordered['instructions']) != len(library['program']['instructions']):
        raise ValueError('finite-loop program lost integer instructions')
    return ordered


def replay(program, hardware, initial, ids, oracle):
    """Execute the selected control order with the qualified integer arithmetic."""
    return execute(decode(program, hardware), initial, ids, oracle)
