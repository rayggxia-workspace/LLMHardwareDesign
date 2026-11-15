"""Check the grants in an emitted replay trace against the arbitration contract."""
from collections import Counter, defaultdict, deque
from dataclasses import asdict
from heapq import heapify, heappop, heappush

from dma_read import ReadFabric, ready_mask, receipt_json
from event_execution import Model, phase_edges
from event_replay import phase_dependencies
from event_replay_plan import Decision, intents
from ffn_program_cost import ActiveProgram


def verify_grants(tasks, hardware, rows):
    model = Model(hardware)
    for task in tasks:
        for binding in task['bindings']:
            model.validate_binding(binding)
            edges = phase_edges(task)
            for edge in edges:
                model.validate_phase(binding, edge.target)
            model.validate_activation_edges(binding, edges)
    by_task = {task['id']: task for task in tasks}
    decisions = [Decision(row, frozenset(by_task[row['id']].get('after', ())),
                          phase_edges(by_task[row['id']])) for row in rows]
    operations = intents(model, decisions)
    events = [event for row in rows for event in row['evaluation']['events']]
    # Use only reported intervals to derive eligibility and releases. No call
    # to the planner, its checkpoint reconstruction, or its grant loop.
    ready_at = defaultdict(list)
    release_at = defaultdict(list)
    issue_expires = defaultdict(list)
    dma_launches = defaultdict(list)
    dma_expected = {}
    program_launches = {}
    sram = defaultdict(list)
    ticks = set()
    for i, (operation, event) in enumerate(zip(operations, events)):
        phases = event.get('phases', (event,))
        for j, (phase, interval) in enumerate(zip(operation.phases, phases)):
            parents = phase_dependencies(operations, i, j)
            ready = max([0 if j else operation.release] + [
                events[p].get('phases', (events[p],))[q]['end'] for p, q in parents])
            start, end = interval['start'], interval['end']
            if start < ready:
                raise ValueError('grant precedes phase dependency')
            if model.snapshot and phase.sram_access is None and end - start != phase.ticks:
                raise ValueError('snapshot phase duration differs')
            if phase.mid_tile is not None and phase.mid_tile.run(start)[0] != end:
                raise ValueError('FFN Mid completion differs')
            if phase.activation is not None:
                retirements = tuple(events[p].get('phases', (events[p],))[q]['end']
                                    for p, q in operation.activation_after)
                expected = phase.activation.receipt(start, retirements)
                if event['activation'] != expected or end != expected['proof'] + 1:
                    raise ValueError('FFN activation handshakes or proof differ')
            if phase.ffn_program is not None:
                if model.dma_profile is None:
                    check_program(phase.ffn_program.receipt(start), end, event['ffn_program'])
                else:
                    if start in program_launches:
                        raise ValueError('two FFN programs were launched on the same edge')
                    program_launches[start] = phase.ffn_program, end, event['ffn_program']
            claims = phase.claims + (operation.holds if j == 0 else ())
            releases = phase.claims + (operation.holds if j == len(phases) - 1 else ())
            ready_at[ready].append((phase.priority, ready, i, j, start, claims, phase.ready_window))
            release_at[end].extend(releases)
            ticks.update((ready, start, end))
            if phase.dma_read is not None:
                key = i, j
                dma_launches[start].append((key, phase.dma_read))
                dma_expected[key] = end, event['dma_beats']
            if phase.sram_access is not None:
                sram[phase.sram_access.site].append((start, i, j, end, phase.sram_access, event.get('sram_beats')))
            for resource, units in phase.claims:
                if resource in model.issue_rates:
                    expires = start + model.issue_rates[resource][0]
                    issue_expires[expires].append((resource, units))
                    ticks.add(expires)

    free = model.capacity.copy()
    issue_count = Counter()
    waiting = []
    edges = list(ticks)
    heapify(edges)
    while edges:
        tick = heappop(edges)
        for resource, units in release_at[tick]:
            free[resource] += units
        for resource, units in issue_expires[tick]:
            issue_count[resource] -= units
        pending = sorted(waiting + ready_at[tick])
        waiting = []
        for request in pending:
            _, _, _, _, start, claims, gate = request
            can_start = all(free[resource] >= units for resource, units in claims)
            can_start = can_start and all(
                resource not in model.issue_rates or issue_count[resource] + units <= model.issue_rates[resource][1]
                for resource, units in claims)
            if can_start and gate is not None:
                opens = gate.next_tick(tick)
                if opens > tick:
                    if opens not in ticks:
                        heappush(edges, opens)
                        ticks.add(opens)
                    can_start = False
            if start < tick or can_start != (start == tick):
                raise ValueError(f'arbitration grant differs at tick {tick}')
            if can_start:
                for resource, units in claims:
                    free[resource] -= units
                    if resource in model.issue_rates:
                        issue_count[resource] += units
            else:
                waiting.append(request)
    if waiting or free != model.capacity or any(issue_count.values()):
        raise ValueError('arbitration trace did not drain')
    if dma_launches or program_launches:
        verify_dma(model.dma_profile, dma_launches, dma_expected, program_launches)
    for site, jobs in sram.items():
        verify_sram(model.sram_profiles[site], jobs, snapshot=model.snapshot)


def verify_sram(profile, jobs, *, snapshot=False):
    """Audit grants and completions with an independent FIFO timeline."""
    launches = defaultdict(list)
    claimed = {}
    for start, i, j, end, access, beats in sorted(jobs):
        width = 4 if access.wide else 1
        words = range(access.word, access.word + access.words, width)
        if snapshot:
            for index in range(len(words)):
                key = i, j, index
                claimed[key] = {'ack': end - 1} if index == len(words) - 1 else {}
                launches[start].append((int(access.wide), key))
            continue
        if not isinstance(beats, list) or len(beats) != len(words):
            raise ValueError('SRAM beat coverage differs')
        for index, (word, beat) in enumerate(zip(words, beats)):
            banks = list(range(4)) if access.wide else [word % 4]
            if (not isinstance(beat, dict) or beat.keys() != {'word', 'banks', 'issue', 'ack'}
                    or beat['word'] != word or beat['banks'] != banks
                    or any(type(beat[key]) is not int for key in ('issue', 'ack'))
                    or not start <= beat['issue'] <= beat['ack'] - 2 < end):
                raise ValueError('SRAM address, bank or beat timing differs')
            key = i, j, index
            claimed[key] = beat
            launches[start].append((int(access.wide), key))
        if beats[-1]['ack'] + 1 != end:
            raise ValueError('SRAM completion differs from final ACK')
    queued = deque(), deque()
    slots = deque(), deque()
    tick = min(launches)
    while launches or claimed:
        for port, key in launches.pop(tick, ()):
            queued[port].append(key)
        ready = ready_mask(profile, tick, 3)
        for port in range(2):
            if slots[port] and slots[port][0][0] <= tick and ready & (1 << port):
                _, key = slots[port].popleft()
                if claimed.pop(key).get('ack', tick) != tick:
                    raise ValueError(f'SRAM response ACK differs at tick {tick}')
        for port in (1, 0):
            if queued[port] and len(slots[port]) < 2:
                key = queued[port].popleft()
                if claimed[key].get('issue', tick) != tick:
                    raise ValueError(f'SRAM bank grant differs at tick {tick}')
                slots[port].append((tick + 2, key))
                break
        tick = tick + 1 if any(queued) or any(slots) else min(launches, default=tick + 1)


def check_program(cost, end, receipt):
    if receipt != asdict(cost) or end != cost.result_tick + 1:
        raise ValueError('FFN program retirement or traffic differs')


def verify_dma(profile, launches, expected, programs):
    # Follow only the emitted launch edges. The cover scheduler and its
    # speculative checkpoint play no role in this consistency check.
    fabric = ReadFabric(profile)
    tick = min((*launches, *programs))
    active = None
    while launches or programs or fabric.active or active is not None:
        for key, read in launches.pop(tick, ()):
            fabric.submit(key, read)
        if tick in programs:
            if active is not None:
                raise ValueError('FFN program overlaps another program')
            program, end, receipt = programs.pop(tick)
            active = ActiveProgram(program, tick, fabric)
        if active is None:
            reads = fabric.advance(tick) if fabric.active else ()
        else:
            cost, reads = active.advance(tick)
            if cost is not None:
                check_program(cost, end, receipt)
                active = None
        for key, receipts in reads:
            if expected.pop(key) != (tick + 1, receipt_json(receipts)):
                raise ValueError(f'typed DMA handshakes or completion differ at tick {tick}')
        tick = tick + 1 if fabric.active or active is not None else min((*launches, *programs), default=0)
    if expected:
        raise ValueError('typed DMA trace did not drain')
