"""Record real MC/LC handshakes in the frozen #251 programmed FFN."""
import argparse
import json
from bisect import bisect_right
from pathlib import Path

from cover_frontier import search
from dma_read import Profile, Read
from event_replay import Operation, Phase, replay
from ffn_scatter import scatter_service, stripe_fragments
from verify_cover_frontier import verify


ANCHOR = ' end else begin: direct_test'
MONITOR = """  reg [2:0] probe_offer_seen=0;
  reg [2:0] probe_fetch_seen=0;
  reg [31:0] probe_fetch_tag[3];
  always @(posedge clk) if($test$plusargs("TRACE_CONTROL")&&!reset)begin
   if(program_start&&program_ready)$display("CONTROL start %0d",cycle);
   if(program_result&&program_result_take)
    $display("CONTROL result %0d %0d %0d",cycle,terminal_reads,terminal_writes);
   if(control.tx_valid&&control.tx_ready&&control.tx_eop)
    $display("CONTROL call %0d %0d",cycle,control.tx_target);
   if(control.rx_valid&&control.rx_ready&&control.rx_eop)
    $display("CONTROL terminal %0d %0d",cycle,control.rx_source);
   for(integer p=0;p<3;p++)begin
    if(dr_valid[p]&&(!probe_fetch_seen[p]||probe_fetch_tag[p]!=dr_tag[p*32+:32]))
     $display("CONTROL fetch_valid %0d %0d %0d %0d",cycle,p,dr_tag[p*32+:32],dr_address[p*64+:64]);
    if(dr_valid[p]&&dr_ready[p])
     $display("CONTROL fetch %0d %0d %0d %0d",cycle,p,dr_tag[p*32+:32],dr_address[p*64+:64]);
    if(dr_rsp_valid[p]&&dr_rsp_ready[p])
     $display("CONTROL fetch_return %0d %0d %0d",cycle,p,dr_rsp_tag[p*32+:32]);
    if(lc_call[p]&&!probe_offer_seen[p])
     $display("CONTROL offer %0d %0d %0d",cycle,p,lc_owner[p*128+:32]);
    if(lc_call[p]&&lc_call_ready[p])
     $display("CONTROL dispatch %0d %0d %0d",cycle,p,lc_owner[p*128+:32]);
    if(lc_done[p]&&lc_done_ready[p])
     $display("CONTROL done %0d %0d %0d %0d %0d",cycle,p,lc_done_owner[p*128+:32],
              lc_done_reads[p*32+:32],lc_done_writes[p*32+:32]);
    probe_offer_seen[p]<=lc_call[p];
    probe_fetch_seen[p]<=dr_valid[p];
    probe_fetch_tag[p]<=dr_tag[p*32+:32];
   end
  end
"""
ADMISSION_MONITOR = """  reg [31:0] probe_down_session=0;
  wire [2:0] probe_range_ready,probe_exec_ready;
  reg [5:0] probe_ready_previous;
  reg probe_ready_seen=0;
  for(genvar q=0;q<3;q++)begin: admission_port
   assign probe_range_ready[q]=ps[q].node.exec.range_ready;
   assign probe_exec_ready[q]=ps[q].node.exec.exec_ready;
  end
  always @(posedge clk) if($test$plusargs("TRACE_ADMISSION")&&!reset)begin
   if(start_valid&&start_ready)
    $display("RELEASE start %0d",cycle);
   if(stripe_commit_valid&&stripe_commit_ready)
    $display("RELEASE scatter %0d",cycle);
   if(dut.schedule.mid_commit_valid&&dut.schedule.mid_commit_ready)
    $display("RELEASE mid %0d",cycle);
   if(!down_phase&&inspect&&inspect_rsp_take&&aux_v[inspect_p])
    $display("RELEASE mid_read %0d",cycle);
   if(down_take&&(&down_terminal))
    $display("RELEASE down_done %0d",cycle);
   if(stripe_valid&&stripe_ready)
    $display("ADMISSION stripe %0d %0d",cycle,tile_session);
   if(down_phase&&tile_session!=probe_down_session)begin
    $display("ADMISSION down %0d %0d",cycle,tile_session);
    probe_down_session<=tile_session;
   end
   if(!probe_ready_seen||probe_ready_previous!={probe_range_ready,probe_exec_ready})
    $display("ADMISSION ready %0d %0d %0d",cycle,probe_range_ready,probe_exec_ready);
   probe_ready_seen<=1;
   probe_ready_previous<={probe_range_ready,probe_exec_ready};
  end
"""
SCATTER_MONITOR = """  always @(posedge clk) if($test$plusargs("TRACE_SCATTER")&&!reset)begin
   if(copy_start&&copy_ready)
    $display("SCATTER start %0d %0d %0d %0d %0d %0d %0d %0d %0d",cycle,tile_session,
             copy_generation,source_p,gather.way,copy_first,copy_src,copy_ring,copy_words);
   if(cs_valid&&cs_ready)$display("SCATTER read %0d %0d %0d",cycle,cs_address,cs_tag);
   if(cs_rsp_valid&&cs_rsp_ready)$display("SCATTER response %0d %0d",cycle,cs_rsp_tag);
   if(cd_valid&&cd_ready)$display("SCATTER write %0d %0d %0d",cycle,cd_address,cd_tag);
   if(cd_rsp_valid&&cd_rsp_ready)$display("SCATTER ack %0d %0d",cycle,cd_rsp_tag);
   if(copy_done&&copy_take)
    $display("SCATTER done %0d %0d %0d",cycle,copy_prefix,copy_error);
  end
"""

# From the last accepted CALL flit, the LC accepts the frame, reads PM and
# metadata, then presents the first 64 B fetch. CRC scans 124 bytes after the
# final data handshake. The two following edges consume CRC and assert service.
CALL_TO_FETCH = 46
DESCRIPTOR_CHECK_TICKS = 125  # DMA phase ends one edge after the final beat.
DONE_TO_TERMINAL_FRAME = 5
TERMINAL_FRAME_WITH_BUBBLE = 5
TERMINAL_EOP_OFFSET = 3
GATE_UP_STRIPES = 58
DOWN_GROUPS = 6
P_COUNT = 3
ALL_P = (1 << P_COUNT) - 1
GATE_UP_COLUMNS = 11008
STRIPE_COLUMNS = 192
MID_COLUMNS = 128


def require(condition, message):
    if not condition:
        raise ValueError(message)


def instrument(source, destination):
    rtl = source.read_text(encoding='utf-8')
    if rtl.count(ANCHOR) != 1:
        raise ValueError('expected the unique programmed FFN block in #251')
    with destination.open('x', encoding='utf-8', newline='\n') as output:
        output.write(rtl.replace(ANCHOR, MONITOR + ADMISSION_MONITOR + SCATTER_MONITOR + ANCHOR))


def read_trace(source):
    open_calls = {}
    scopes = []
    admission = {'ready': [], 'stripe': [], 'down': []}
    upstream = []
    scatter = []
    start = result = program = None
    passed = False
    for line in source:
        if line.startswith('PROGRAM_PROFILE '):
            require(program is None, 'duplicate programmed FFN profile')
            program = dict(item.split('=') for item in line.split()[1:])
        if line.startswith('PASS ffn_three_p_native ') and ' program=1 ' in line:
            passed = True
        if line.startswith('ADMISSION '):
            _, kind, *fields = line.split()
            require(kind in admission, 'unknown admission event')
            admission[kind].append(tuple(map(int, fields)))
        if line.startswith('RELEASE '):
            _, kind, tick = line.split()
            upstream.append((kind, int(tick)))
        if line.startswith('SCATTER '):
            _, kind, *fields = line.split()
            scatter.append((kind, *map(int, fields)))
        if not line.startswith('CONTROL '):
            continue
        _, kind, raw_tick, *fields = line.split()
        tick = int(raw_tick)
        values = tuple(map(int, fields))
        if kind == 'start':
            require(start is None and not values, 'duplicate or malformed program start')
            start = tick
        elif kind == 'result':
            require(result is None and len(values) == 2, 'duplicate or malformed program result')
            result = tick, *values
        else:
            client, *fields = values
            require(0 <= client < 3 and start is not None and tick >= start, 'invalid LC event')
            if kind == 'call':
                require(client not in open_calls, f'new CALL before LC {client} retired')
                open_calls[client] = {'client': client}
                scopes.append(open_calls[client])
            require(client in open_calls, f'LC {client} event without CALL')
            open_calls[client].setdefault(kind, []).append((tick, *fields))
            if kind == 'terminal':
                del open_calls[client]
    require(passed and start is not None and result is not None and not open_calls and program is not None,
            'incomplete programmed FFN trace')
    require(len(scopes) == 192, 'expected all 192 native calls')
    return scopes, start, result, program, admission, upstream, scatter


def first_ready(edges, ticks, mask, release):
    index = bisect_right(ticks, release) - 1
    require(index >= 0, 'missing P readiness at release')
    for tick, range_ready, exec_ready in edges[index:]:
        if range_ready & exec_ready & mask == mask:
            return max(tick, release)
    raise ValueError('no common P readiness after release')


def controller_triggers(upstream):
    """Derive each release from producer handshakes and the fixture's rules."""
    events = iter(upstream)

    def accept(kind):
        seen, tick = next(events, ('missing', -1))
        require(seen == kind, f'expected {kind} producer handshake, saw {seen}')
        return tick

    require(all(a[1] < b[1] for a, b in zip(upstream, upstream[1:])),
            'producer handshakes are out of order')
    trigger = accept('start')
    produced = committed = 0
    releases = {}
    for session in range(1, GATE_UP_STRIPES + 1):
        # The ring advances through DECIDE and STRIPE_SEND, then the
        # registered gather presents the work one edge after acceptance.
        releases[session] = trigger, 3
        trigger = accept('scatter')
        produced += min(STRIPE_COLUMNS, GATE_UP_COLUMNS - produced)
        while produced - committed >= MID_COLUMNS:
            trigger = accept('mid')
            committed += MID_COLUMNS
    require(produced == committed == GATE_UP_COLUMNS, 'incomplete Mid production')
    for _ in range(committed // MID_COLUMNS * 16):
        trigger = accept('mid_read')
    for group in range(DOWN_GROUPS):
        # Fixture switches to Down after the last Mid read ACK and samples
        # readiness one edge later. Other groups follow the prior DONE.
        releases[GATE_UP_STRIPES + group + 1] = trigger, 2 if group == 0 else 1
        trigger = accept('down_done')
    require(next(events, None) is None, 'unexpected additional producer handshake')
    return releases


def scatter_problem(fragments, mode, producer_ready):
    service = scatter_service(fragments, mode)
    resources = {r: 1 for phase in service['phases'] for r in phase['claims']}
    resources.update(service['hold_claims'])
    windows, values, inputs, outputs = {}, {}, {}, {}

    def window(client, address):
        site = f'P{client}'
        name = f'{site}:{address}'
        windows[name] = {'site': site, 'offset': address * 16, 'bytes': 16}
        return name

    for fragment in fragments:
        for word in range(fragment.words):
            source = window(fragment.client, fragment.scratch + word)
            destination = window(0, fragment.destination(word))
            require(destination not in outputs, 'scatter writes the same ring word twice')
            values[source] = 16
            inputs[source] = outputs[destination] = source

    def action(name, ticks, stage, after=()):
        return {'id': name, 'after': after,
                'bindings': [{'id': name, 'site': 'P0', 'ticks': ticks, 'resources': [],
                              'nets': [], 'scratch_words': 0, 'event_stages': [stage]}]}

    tasks = [action('producer', producer_ready, {'service': 'producer'}),
             action('scatter', service['ticks'], {'service': 'scatter', 'inputs': inputs, 'outputs': outputs},
                    after=('producer',))]
    hardware = {'resources': resources, 'nets': {},
                'sites': {f'P{p}': {'bytes': 16384, 'words': 1024} for p in range(P_COUNT)},
                'event_model': {'kind': 'qualified-event-model-v1', 'timing': 'replay',
                                'value_bytes': values, 'windows': windows, 'initial_copies': inputs,
                                'routes': {}, 'services': {'producer': {'ticks': producer_ready, 'claims': {}},
                                                           'scatter': service}}}
    return tasks, hardware


def check_scatter(scopes, upstream, observed, mode):
    by_session = {}
    for scope in scopes:
        done, session, _, _ = scope['done'][0]
        if session <= GATE_UP_STRIPES:
            owners = by_session.setdefault(session, {})
            require(scope['client'] not in owners, 'duplicate P completion in stripe')
            owners[scope['client']] = done

    generation = words = cursor = 0
    commits = []
    latencies = []
    for session in range(1, GATE_UP_STRIPES + 1):
        completion = by_session.get(session, {})
        require(set(completion) == set(range(P_COUNT)), f'incomplete P completions for stripe {session}')
        first = STRIPE_COLUMNS * (session - 1)
        fragments = stripe_fragments(first, min(STRIPE_COLUMNS, GATE_UP_COLUMNS - first))
        ready = max(completion.values()) + 1
        tasks, hardware = scatter_problem(fragments, mode, ready)
        plan = search(tasks, hardware, width=1)
        verify(tasks, hardware, (), plan)
        starts = {p['kind']: p['start'] for p in plan['tasks'][-1]['evaluation']['events'][0]['phases']}
        stripe_events = []
        for index, fragment in enumerate(fragments):
            prefix = f'fragment{index}'
            generation += 1
            stripe_events.append(('start', starts[f'{prefix}.start'], session, generation, fragment.client,
                                  fragment.way, fragment.first, fragment.scratch, fragment.ring, fragment.words))
            for word in range(fragment.words):
                name = f'{prefix}.word{word}'
                tag = generation << 16 | word
                stripe_events.extend((
                    ('read', starts[f'{name}.read'], fragment.scratch + word, tag),
                    ('response', starts[f'{name}.response'], tag),
                    ('write', starts[f'{name}.write'], fragment.destination(word), tag),
                    ('ack', starts[f'{name}.ack'], tag),
                ))
            stripe_events.append(('done', starts[f'{prefix}.done'], fragment.words, 0))
            words += fragment.words
        for expected in stripe_events:
            actual = observed[cursor] if cursor < len(observed) else None
            require(actual == expected, f'stripe {session} scatter differs: expected {expected}, saw {actual}')
            cursor += 1
        commits.append(starts['commit'])
        latencies.append(starts['commit'] - ready)

    require(cursor == len(observed), 'unexpected scatter trace entries')
    require([tick for kind, tick in upstream if kind == 'scatter'] == commits, 'scatter commit differs')
    predicted = iter(commits)
    releases = [(kind, next(predicted) if kind == 'scatter' else tick) for kind, tick in upstream]
    return releases, {'stripes': len(commits), 'fragments': generation, 'words': words,
                      'min_cycles': min(latencies), 'max_cycles': max(latencies)}


def replay_group(group, trigger, delay, is_down):
    """Use the same qualified event IR and checker as DP for one scope group."""
    origin = min(trigger, *(offer for offer, _ in group.values())) - 1
    services, tasks = {}, []
    hardware = {
        'resources': {f'P{client}': 1 for client in range(P_COUNT)},
        'sites': {'P0': {'words': 0, 'bytes': 0}}, 'nets': {},
        'event_model': {'kind': 'qualified-event-model-v1', 'timing': 'replay',
                        'routes': {}, 'windows': {}, 'value_bytes': {}, 'services': services},
    }

    def add(name, phases, waits=()):
        ticks = sum(t for _, t, _ in phases)
        services[name] = {'ticks': ticks, 'claims': {}}
        if len(phases) == 1:
            services[name]['claims'] = dict.fromkeys(phases[0][2], 1)
        else:
            services[name]['phases'] = [{'kind': kind, 'ticks': t, 'claims': dict.fromkeys(resources, 1)}
                                         for kind, t, resources in phases]
        tasks.append({'id': name, 'event_after': list(waits),
                      'bindings': [{'id': name, 'site': 'P0', 'ticks': ticks, 'resources': [], 'nets': [],
                                    'scratch_words': 0, 'event_stages': [{'service': name}]}]})

    def edge(task, source, target):
        return {'task': task, 'from': [0, source], 'to': [0, target]}

    add('controller', (('producer', trigger - origin, ()), ('release', delay, ())))
    if is_down:
        for client, (offer, _) in group.items():
            add(f'descriptor{client}', (('stage', offer - origin, ()),))
        waits = [edge('controller', 'release', 'stage')]
        waits.extend(edge(f'descriptor{client}', 'stage', 'stage') for client in group)
        add('dispatch', (('stage', 1, tuple(hardware['resources'])),), waits)
    else:
        for client, (offer, _) in group.items():
            add(f'P{client}', (('descriptor', offer - origin, ()), ('dispatch', 1, (f'P{client}',))),
                (edge('controller', 'release', 'dispatch'),))
    for width in (1, 8):
        plan = search(tasks, hardware, width=width)
        verify(tasks, hardware, (), plan)
        rows = {row['id']: row['evaluation']['events'][0] for row in plan['tasks']}
        for client, (_, actual) in group.items():
            event = rows['dispatch'] if is_down else rows[f'P{client}']['phases'][-1]
            require(origin + event['start'] == actual, f'candidate replay admission differs for P{client}')


def check_admission(scopes, transfers, admission, upstream=None):
    edges = admission['ready']
    require(edges and all(len(row) == 3 and 0 <= row[1] <= ALL_P and 0 <= row[2] <= ALL_P
                          for row in edges), 'missing or invalid P readiness trace')
    ticks = [row[0] for row in edges]
    require(ticks[0] == 0 and all(a < b for a, b in zip(ticks, ticks[1:])),
            'unordered or truncated P readiness trace')
    expected_sessions = (
        ('stripe', range(1, GATE_UP_STRIPES + 1)),
        ('down', range(GATE_UP_STRIPES + 1, GATE_UP_STRIPES + DOWN_GROUPS + 1)),
    )
    release = {}
    for kind, sessions in expected_sessions:
        rows = admission[kind]
        require(all(len(row) == 2 for row in rows) and
                [session for _, session in rows] == list(sessions) and
                all(a[0] < b[0] for a, b in zip(rows, rows[1:])), f'invalid {kind} releases')
        # The registered Gate/Up gather first asserts project_valid after
        # accepting the stripe. Down's fixture waits one edge on phase entry;
        # after subsequent groups it samples readiness in the same cycle.
        for tick, session in rows:
            release[session] = tick + (kind == 'stripe' or session == GATE_UP_STRIPES + 1)

    by_session = {}
    for scope, grants in zip(scopes, transfers):
        session = scope['offer'][0][1]
        group = by_session.setdefault(session, {})
        require(scope['client'] not in group, 'duplicate P in admission group')
        group[scope['client']] = grants[-1].end, scope['dispatch'][0][0]
    require(by_session.keys() == release.keys(), 'admission session coverage differs')
    triggers = controller_triggers(upstream) if upstream is not None else None
    if triggers is not None:
        require({session: tick + delay for session, (tick, delay) in triggers.items()} == release,
                'producer-derived controller release differs')

    report = {kind: {'calls': 0, 'waiting_calls': 0, 'max_wait': 0,
                     'max_controller_wait': 0, 'max_peer_wait': 0, 'max_node_wait': 0}
              for kind, _ in expected_sessions}
    for session, group in by_session.items():
        require(set(group) == set(range(P_COUNT)), f'missing P in session {session}')
        is_down = session > GATE_UP_STRIPES
        last_descriptor = max(offer for offer, _ in group.values())
        for client, (offer, actual) in group.items():
            descriptor = last_descriptor if is_down else offer
            eligible = max(descriptor, release[session])
            predicted = first_ready(edges, ticks, ALL_P if is_down else 1 << client, eligible)
            require(predicted == actual, f'admission timing differs for session {session}, P{client}: '
                    f'expected {predicted}, saw {actual}')
            stats = report['down' if is_down else 'stripe']
            stats['calls'] += 1
            stats['waiting_calls'] += predicted > offer
            stats['max_wait'] = max(stats['max_wait'], predicted - offer)
            stats['max_controller_wait'] = max(stats['max_controller_wait'], max(0, release[session] - offer))
            stats['max_peer_wait'] = max(stats['max_peer_wait'], eligible - max(offer, release[session]))
            stats['max_node_wait'] = max(stats['max_node_wait'], predicted - eligible)
        if triggers is not None:
            replay_group(group, *triggers[session], is_down)
    return report


def check(source, mode, seed, *, admission=False, phase_release=False, scatter=False):
    scopes, start, result, program, sampled_admission, upstream, observed_scatter = read_trace(source)
    transfers, terminals = [], []
    sequence = [0] * 3
    read_bytes = write_bytes = 0
    for index, scope in enumerate(scopes):
        client = scope['client']
        sequence[client] += 1
        serial = sequence[client]
        prefix = f'CALL {index + 1}, LC {client}'
        require(all(len(scope.get(event, ())) == count for event, count in
                    (('call', 1), ('fetch_valid', 2), ('fetch', 2), ('fetch_return', 2),
                     ('offer', 1), ('dispatch', 1), ('done', 1), ('terminal', 1))),
                f'{prefix} missing or duplicated events')
        (call,), = scope['call']
        (offer, offer_owner), = scope['offer']
        (dispatch, dispatch_owner), = scope['dispatch']
        (done, done_owner, reads, writes), = scope['done']
        (terminal,), = scope['terminal']
        require(offer_owner == dispatch_owner == done_owner == serial and offer <= dispatch <= done < terminal,
                f'{prefix} service ownership or boundaries differ')
        read_bytes += reads + 128
        write_bytes += writes
        addr = 4096 + 128 * index
        expected = ((serial * 2, addr), (serial * 2 + 1, addr + 64))
        require(tuple(row[1:] for row in scope['fetch_valid']) ==
                tuple(row[1:] for row in scope['fetch']) == expected, f'{prefix} descriptor identity differs')
        require(sorted(row[1] for row in scope['fetch_return']) == [serial * 2, serial * 2 + 1],
                f'{prefix} returned tags differ')
        require(tuple(row[0] for row in scope['fetch_valid']) ==
                (call + CALL_TO_FETCH, scope['fetch'][0][0] + 1), f'{prefix} source VALID timing differs')
        transfers.append(Operation((
            Phase('decode CALL', CALL_TO_FETCH),
            Phase('descriptor DMA', 1, dma_read=Read(client, addr, 128, 2)),
            Phase('CRC and service offer', DESCRIPTOR_CHECK_TICKS),
        ), release=call))
        terminals.append(Operation((
            Phase('terminal packet and receive bubble', TERMINAL_FRAME_WITH_BUBBLE, (('MC.rx', 1),), client),
        ), release=done + DONE_TO_TERMINAL_FRAME))

    profile = Profile.from_spec({'ffn_provider': {'mode': mode, 'seed': seed}})
    grants = replay(transfers + terminals, {'MC.rx': 1}, dma_profile=profile)
    for scope, transfer, terminal in zip(scopes, grants[:len(scopes)], grants[len(scopes):]):
        beats = transfer[1].dma_beats
        require(tuple(beat.reserved for beat in beats) == tuple(row[0] for row in scope['fetch'])
                and sorted((beat.delivered, scope['fetch'][i][1]) for i, beat in enumerate(beats)) ==
                scope['fetch_return'], 'descriptor DMA handshakes differ')
        require(transfer[-1].end == scope['offer'][0][0], 'CRC or service offer timing differs')
        require(terminal[0].start + TERMINAL_EOP_OFFSET == scope['terminal'][0][0],
                'terminal arbitration or framing differs')
    require((int(program['calls']), int(program['confirmed_reads']), int(program['confirmed_writes'])) ==
            (len(scopes), read_bytes, write_bytes) and result[1:] == (read_bytes, write_bytes),
            'program byte accounting differs')
    require(result[0] > max(s['terminal'][0][0] for s in scopes), 'program result preceded child retirement')
    report = {'calls': len(scopes), 'descriptor_beats': 2 * len(scopes), 'start': start,
              'result_accept': result[0], 'read_bytes': read_bytes, 'write_bytes': write_bytes,
              'longest_service_offer_wait': max(s['dispatch'][0][0] - s['offer'][0][0] for s in scopes),
              'longest_done_to_terminal': max(s['terminal'][0][0] - s['done'][0][0] for s in scopes)}
    if scatter:
        upstream, report['scatter'] = check_scatter(scopes, upstream, observed_scatter, mode)
    if admission or phase_release or scatter:
        report['admission'] = check_admission(scopes, grants[:len(scopes)], sampled_admission,
                                              upstream if phase_release or scatter else None)
    if phase_release or scatter:
        report['phase_replay_calls_per_strategy'] = len(scopes)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    prepare = sub.add_parser('instrument')
    prepare.add_argument('source', type=Path)
    prepare.add_argument('destination', type=Path)
    verify = sub.add_parser('check')
    verify.add_argument('log', type=Path)
    verify.add_argument('--mode', type=int, choices=(0, 1), required=True)
    verify.add_argument('--seed', type=int, default=25001)
    verify.add_argument('--admission', action='store_true')
    verify.add_argument('--phase-release', action='store_true')
    verify.add_argument('--scatter', action='store_true')
    args = parser.parse_args()
    if args.action == 'instrument':
        instrument(args.source, args.destination)
    else:
        with args.log.open(encoding='utf-8') as source:
            print(json.dumps(check(source, args.mode, args.seed, admission=args.admission,
                                   phase_release=args.phase_release, scatter=args.scatter), indent=2))


if __name__ == '__main__':
    main()
