"""Build replay intents from bound actions and project simulated grants back."""
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, replace

from dma_read import receipt_json
from event_execution import Copy, DDR, PhaseEdge, capacity_profile, window_phase_indices
from event_replay import Operation, Phase, replay_branch
from ffn_mid import MidTile
from ffn_program_cost import Program
from sram_feeder import receipt_json as sram_receipts


@dataclass(frozen=True)
class Decision:
    row: dict
    predecessors: frozenset[str]
    event_after: tuple[PhaseEdge, ...] = ()

    def key(self):
        events = self.row['evaluation']['events']
        return (self.row['id'], self.row['binding'], self.predecessors, self.event_after,
                tuple((event['route'], event['value'], event['src'], event['dst'], event.get('output_eviction'))
                      if event['kind'] == 'move' else (event['service'],)
                      for event in events))


def accesses(event):
    if event['kind'] == 'stage':
        return event['inputs'], event['outputs']
    return {event['src']: event['value']}, {event['dst']: event['value']}


def event_operation(model, event):
    if event['kind'] == 'stage':
        service = model.services[event['service']]
        if 'phases' in service:
            phases = tuple(Phase.from_spec(p['kind'], p['ticks'], p) for p in service['phases'])
            return Operation(phases, holds=tuple(sorted(service.get('hold_claims', {}).items())))
        phase = Phase.from_spec('stage', service['ticks'], service)
        if 'ffn_mid' in service:
            phase = replace(phase, mid_tile=MidTile.from_spec(service['ffn_mid']))
        if 'sram_access' in service:
            phase = replace(phase, sram_access=model.sram_access(service, event['inputs'], event['outputs']))
        if 'ffn_activation' in service:
            phase = replace(phase, activation=model.activation_window(service, event['inputs'], event['outputs']))
        if 'ffn_program' in service:
            phase = replace(phase, ffn_program=Program.from_spec(service['ffn_program']))
        return Operation((phase,))
    route = model.routes[event['route']]
    size = model.sizes[event['value']]
    ticks = route['setup'] + (size + route['bytes_per_tick'] - 1) // route['bytes_per_tick']
    data = Phase.from_spec('data', ticks, route)
    if 'typed_dma' in route:
        data = replace(data, dma_read=model.dma_read(route, event['value']))
    if 'phases' not in route:
        return Operation((data,))
    profile = route['phases']
    issue = Phase.from_spec('issue', profile['issue']['ticks'], profile['issue'])
    ack = Phase.from_spec('ack', profile['ack']['ticks'], profile['ack'])
    return Operation((issue, data, ack), holds=tuple(sorted(profile['hold_claims'].items())))


def intents(model, decisions):
    operations = []
    last_stage = {}
    named_phases = {}
    writers = {}
    readers = {}
    stores = {}
    for decision in decisions:
        boundary = {last_stage[name] for name in decision.predecessors}
        phase_waits = defaultdict(set)
        activation_waits = defaultdict(dict)
        for edge in decision.event_after:
            parent = named_phases[edge.task][edge.source]
            if edge.load is None:
                phase_waits[edge.target].add(parent)
            else:
                activation_waits[edge.target][edge.load] = parent
        stages = {}
        stage_index = -1
        pending_moves = set()
        for event in decision.row['evaluation']['events']:
            index = len(operations)
            operation = event_operation(model, event)
            final = len(operation.phases) - 1
            terminal = index, final
            is_stage = event['kind'] == 'stage'
            read, write, publish = (window_phase_indices(model.services[event['service']])
                                    if is_stage else (None, 0, final))
            inputs, outputs = accesses(event)
            dependencies = [set() for _ in operation.phases]
            activation_after = ()
            dependencies[0].update(boundary)
            for window, value in inputs.items():
                if window == DDR:
                    if value not in model.initial.backing:
                        dependencies[0].add(stores[value])
                elif window in writers:
                    dependencies[read or 0].add(writers[window])
            for window in outputs.keys() - {DDR}:
                if window in writers:
                    dependencies[write].add(writers[window])
                dependencies[write].update(readers.get(window, ()))
            if is_stage:
                stage_index += 1
                for j, phase in enumerate(operation.phases):
                    location = stage_index, phase.name
                    stages[location] = index, j
                    dependencies[j].update(phase_waits.get(location, ()))
                    if location in activation_waits:
                        lanes = activation_waits[location]
                        activation_after = tuple(lanes[lane] for lane in sorted(lanes))
                # Descriptor/setup phases may run while the input delivery is
                # in flight if the contract identifies a later capture phase.
                dependencies[read or 0].update(pending_moves)
                pending_moves.clear()
                boundary = {terminal}
            elif 'output_eviction' not in event:
                pending_moves.add(terminal)
            phase_after = tuple(map(frozenset, dependencies)) if any(dependencies) else ()
            operations.append(replace(operation, phase_after=phase_after, activation_after=activation_after))
            for window in inputs.keys() - outputs.keys() - {DDR}:
                readers.setdefault(window, set()).add((index, final if read is None else read))
            for window in outputs.keys() - {DDR}:
                writers[window] = index, publish
                readers.pop(window, None)
            if DDR in outputs:
                stores.setdefault(outputs[DDR], terminal)
        for covered in decision.row['covers']:
            last_stage[covered] = terminal
            named_phases[covered] = stages
        last_stage[decision.row['id']] = terminal
        named_phases[decision.row['id']] = stages
    return operations


def retime(model, decisions, proposed, previous=None):
    operations = intents(model, decisions)
    trace = replay_branch(operations, model.capacity, previous=previous, issue_rates=model.issue_rates,
                          dma_profile=model.dma_profile, sram_profiles=model.sram_profiles)
    grants = iter(zip(operations, trace.grants))
    copies = model.initial.copies.copy()
    backing = model.initial.backing.copy()
    occupancy = defaultdict(Counter)
    rows = []

    def occupy(claims, start, end):
        for resource, units in claims:
            occupancy[resource][start] += units
            occupancy[resource][end] -= units

    for decision in decisions:
        row = decision.row
        detail = row['evaluation']
        events = []
        for event in detail['events']:
            operation, schedule = next(grants)
            start, end = schedule[0].start, schedule[-1].end
            actual = {**event, 'start': start, 'end': end}
            phases = []
            for phase, grant in zip(operation.phases, schedule):
                occupy(phase.claims, grant.start, grant.end)
                phases.append({'kind': phase.name, 'start': grant.start, 'end': grant.end})
                if grant.dma_beats:
                    actual['dma_beats'] = receipt_json(grant.dma_beats)
                if grant.sram_beats:
                    actual['sram_beats'] = sram_receipts(phase.sram_access, grant.sram_beats)
                if phase.activation is not None:
                    retirements = tuple(trace.grants[i][j].end for i, j in operation.activation_after)
                    actual['activation'] = phase.activation.receipt(start, retirements)
                if grant.ffn_program is not None:
                    actual['ffn_program'] = asdict(grant.ffn_program)
            if len(phases) > 1:
                actual['phases'] = phases
            occupy(operation.holds, start, end)
            inputs, outputs = accesses(event)
            read, _, publish = (window_phase_indices(model.services[event['service']])
                                if event['kind'] == 'stage' else (None, 0, len(schedule) - 1))
            read_end = end if read is None else schedule[read].end
            for window in inputs.keys() - {DDR}:
                copies[window] = replace(copies[window], held_until=max(copies[window].held_until, read_end))
            for window, value in outputs.items():
                if window == DDR:
                    backing[value] = min(end, backing.get(value, end))
                else:
                    visible = schedule[publish].end
                    copies[window] = Copy(value, visible, visible)
            events.append(actual)
        rows.append({**row, 'start': min(event['start'] for event in events),
                     'end': events[-1]['end'], 'evaluation': {**detail, 'events': events}})
    calendars = {resource: capacity_profile(changes) for resource, changes in occupancy.items()}
    return replace(proposed, copies=copies, backing=backing, calendars=calendars), rows, trace


def delivery_at(model, decisions, candidate, previous, fixed_operations):
    """Trial an unfinished binding through its most recent transport choice."""
    operations = intents(model, (*decisions, candidate))
    trace = replay_branch(operations, model.capacity, previous=previous, issue_rates=model.issue_rates,
                          dma_profile=model.dma_profile, sram_profiles=model.sram_profiles,
                          save_checkpoints=False)
    return max(grants[-1].end for grants in trace.grants[fixed_operations:])
