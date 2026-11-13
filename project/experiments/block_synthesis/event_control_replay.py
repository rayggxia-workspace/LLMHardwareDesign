"""Execute exported two-level control with independent data/ACK checking."""
from collections import Counter, defaultdict
import heapq

from event_deploy import DDR


def require(condition, message):
    if not condition:
        raise ValueError(message)


def execute(program, hardware, payloads, services, *, ack_delay=None, read_external=None):
    """Run program commands, with optional injected destination ACK delay.

    The reference acquires the union of a command's resource claims until
    completion. It is a conservative functional replay, not a phase-timing
    or native RTL implementation of the two control levels.
    """
    require(program.get('schema') == 'block-event-control/1', 'unsupported event control program')
    spec = hardware['event_model']
    windows = spec['windows']
    groups = hardware.get('control_groups', {})
    targets = {entry['site']: name for name, entry in groups.items()}
    initial = {(windows[w]['site'], windows[w]['offset']): (v, payloads[v])
               for w, v in spec.get('initial_copies', {}).items()}
    initial_backing = set(spec.get('initial_backing', ()))
    initial.update({(DDR, program['external_addresses'][value]): (value, payloads[value])
                    for value in initial_backing if value in payloads})
    require(read_external is not None or initial_backing <= payloads.keys(),
            'missing initial external payload')
    for value, data in initial.values():
        require(isinstance(data, bytes) and len(data) == spec['value_bytes'][value], 'initial payload size differs')

    def address(operand):
        window, value = operand['window'], operand['value']
        require(operand['bytes'] == spec['value_bytes'][value], 'command length differs')
        if window == DDR:
            expected = DDR, program['external_addresses'][value]
        else:
            entry = windows[window]
            expected = entry['site'], entry['offset']
            require(operand['bytes'] <= entry['bytes'], 'command overruns S window')
        require((operand['site'], operand['address']) == expected, 'command address differs')
        return expected

    operations = defaultdict(dict)
    known = groups.keys() | (hardware['sites'].keys() - targets.keys())
    require(program['locals'].keys() <= known, 'unknown local control target')
    for local, commands in program['locals'].items():
        for command in commands:
            sequence = command['sequence']
            require(local not in operations[sequence], 'duplicate local command')
            operations[sequence][local] = command

    dispatch = program['mother'][:-1]
    terminal = program['mother'][-1]
    ids = {row['sequence'] for row in dispatch}
    require(len(ids) == len(dispatch) and set(operations) == ids, 'dispatch coverage differs')
    require(terminal['op'] == 'END' and set(terminal['wait_for']) == ids, 'mother terminates before completion')
    require(all(row['op'] == 'DISPATCH' and set(row['wait_for']) <= ids - {row['sequence']}
                for row in dispatch), 'invalid mother control flow')
    outstanding = {row['sequence']: row for row in sorted(dispatch, key=lambda row: (
        row['estimated_start'], row['estimated_end'], row['sequence']))}
    queue, done, occupied = [], set(), Counter()
    live_reads, live_writes = Counter(), set()
    state, log, now = dict(initial), [], 0

    def decode(row):
        commands = operations[row['sequence']]
        require(set(commands) == set(row['targets']), 'invalid dispatch target')
        first = next(iter(commands.values()))
        shared = ('op', 'route', 'service', 'read', 'write', 'required_completion', 'indexed_read')
        require(all(all(command.get(field) == first.get(field) for field in shared)
                    for command in commands.values()), 'local command contract differs')
        if first['op'] == 'COPY':
            route = spec['routes'][first['route']]
            src, dst = first['read'][0], first['write'][0]
            require(src['value'] == dst['value'] and src['site'] == route['src'] and dst['site'] == route['dst'],
                    'transfer identity or endpoints differ')
            expected = defaultdict(list)
            for side, operand in (('send', src), ('receive', dst)):
                site = operand['site']
                if site != DDR:
                    expected[targets.get(site, site)].append(side)
            require(first['required_completion'] == 'destination_commit_ack', 'transfer completion must be ACK')
            ticks = route['setup'] + (src['bytes'] + route['bytes_per_tick'] - 1)//route['bytes_per_tick']
            claims = dict(route['claims'])
            if 'phases' in route:
                profile = route['phases']
                ticks += profile['issue']['ticks'] + profile['ack']['ticks']
                for group in (profile['issue']['claims'], profile['ack']['claims'], profile['hold_claims']):
                    for resource, units in group.items():
                        claims[resource] = max(claims.get(resource, 0), units)
        else:
            service = spec['services'][first['service']]
            indexed = service.get('indexed_read')
            if indexed:
                table = indexed['table']
                expected = {**indexed,'table_address':program['external_addresses'][table]}
                require(first['op'] == 'INDEXED_LOAD' and first['required_completion'] == 'destination_commit_ack'
                        and first.get('indexed_read') == expected and table in initial_backing,
                        'invalid indexed memory command or table address')
            else:
                require(first['op'] == 'EXEC' and first['required_completion'] == 'service_done',
                        'invalid local service command')
            site = service.get('control_site')
            if site is not None:
                expected = {targets.get(site, site): ['execute']}
            else:
                require(len(commands) == 1, 'missing service control target')
                fallback = first['read'] or first['write']
                expected = ({targets.get(fallback[0]['site'], fallback[0]['site']): ['execute']}
                            if fallback else {next(iter(commands)): ['execute']})
            ticks, claims = service['ticks'], service['claims']
        require({local: command['roles'] for local, command in commands.items()} == expected,
                'local dispatch target or role differs')
        return first, ticks, claims

    def external(value, offset, size):
        require(value in initial_backing and 0 <= offset <= spec['value_bytes'][value] - size,
                'read outside immutable external allocation')
        data = payloads[value][offset:offset+size] if value in payloads else read_external(value,offset,size)
        require(isinstance(data,bytes) and len(data) == size, 'external payload length differs')
        return data

    def gather(command, data):
        from indexed_memory import index_address

        request = command['indexed_read']
        index_bytes, row_words = request['index_bits'] // 8, request['row_words']
        require(len(data) == 1 and len(data[0]) == request['indices'] * index_bytes,
                'indexed command index record length differs')
        # Validate every requested index before issuing any read for this command.
        offsets = [index_address(int.from_bytes(data[0][i:i+index_bytes],'little',signed=True),
                                 request['rows'],row_words,0,row_words,request['address_bits'])
                   for i in range(0,len(data[0]),index_bytes)]
        return [b''.join(external(request['table'],offset,row_words*16) for offset in offsets)]

    decoded = {row['sequence']: decode(row) for row in dispatch}
    while outstanding or queue:
        for number, row in list(outstanding.items()):
            if not set(row['wait_for']) <= done:
                continue
            command, ticks, claims = decoded[number]
            if any(occupied[resource] + units > hardware['resources'][resource]
                   for resource, units in claims.items()):
                continue
            read = [address(entry) for entry in command['read']]
            write = [address(entry) for entry in command['write']]
            require(not live_writes.intersection((*read, *write)) and not any(live_reads[w] for w in write),
                    'issued command violates S/DDR custody before ACK')
            data = []
            for slot, entry in zip(read, command['read']):
                if slot not in state and slot[0] == DDR and entry['value'] in initial_backing:
                    data.append(external(entry['value'],0,entry['bytes']))
                else:
                    require(slot in state and state[slot][0] == entry['value'], 'stale or missing source value')
                    data.append(state[slot][1])
            if command['op'] == 'COPY':
                result = data
            elif command['op'] == 'INDEXED_LOAD':
                result = gather(command,data)
            else:
                result = list(services(command['service'], data))
            if command['required_completion'] == 'destination_commit_ack' and ack_delay is not None:
                delay = ack_delay(number, command)
                require(type(delay) is int and delay >= 0, 'invalid injected ACK delay')
                ticks += delay
            require(len(result) == len(write) and all(isinstance(data, bytes) and len(data) == entry['bytes']
                    for data, entry in zip(result, command['write'])), 'service result length differs')
            values = [(entry['value'], data) for entry, data in zip(command['write'], result)]
            occupied.update(claims)
            live_reads.update(read)
            live_writes.update(write)
            heapq.heappush(queue, (now + ticks, number, claims, read, write, values))
            log.append({'event': 'issue', 'sequence': number, 'tick': now})
            del outstanding[number]
        if not queue:
            require(not outstanding, 'mother/local command deadlock')
            break
        now = queue[0][0]
        while queue and queue[0][0] == now:
            _, number, claims, read, write, values = heapq.heappop(queue)
            occupied.subtract(claims)
            live_reads.subtract(read)
            live_writes.difference_update(write)
            state.update(zip(write, values))
            done.add(number)
            log.append({'event': 'ack', 'sequence': number, 'tick': now})
    return {'values': dict(state.values()), 'events': log, 'reference_ticks': now}
