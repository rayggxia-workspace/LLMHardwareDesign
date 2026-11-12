"""Build replay intents from bound actions and project simulated grants back."""
from collections import Counter, defaultdict
from dataclasses import dataclass, replace

from event_execution import Copy, DDR, capacity_profile
from event_replay import Operation, Phase, replay


@dataclass(frozen=True)
class Decision:
    row: dict
    predecessors: frozenset[str]

    def key(self):
        events = self.row['evaluation']['events']
        return (self.row['id'], self.row['binding'], self.predecessors,
                tuple((event['route'], event['value'], event['src'], event['dst'])
                      if event['kind'] == 'move' else (event['service'],)
                      for event in events))


def accesses(event):
    if event['kind'] == 'stage':
        return event['inputs'], event['outputs']
    return {event['src']: event['value']}, {event['dst']: event['value']}


def event_operation(model, event, dependencies):
    if event['kind'] == 'stage':
        service = model.services[event['service']]
        if 'phases' in service:
            phases = tuple(Phase.from_spec(p['kind'], p['ticks'], p) for p in service['phases'])
            return Operation(phases, dependencies, holds=tuple(sorted(service.get('hold_claims', {}).items())))
        return Operation((Phase.from_spec('stage', service['ticks'], service),), dependencies)
    route = model.routes[event['route']]
    size = model.sizes[event['value']]
    ticks = route['setup'] + (size + route['bytes_per_tick'] - 1) // route['bytes_per_tick']
    data = Phase.from_spec('data', ticks, route)
    if 'phases' not in route:
        return Operation((data,), dependencies)
    profile = route['phases']
    issue = Phase.from_spec('issue', profile['issue']['ticks'], profile['issue'])
    ack = Phase.from_spec('ack', profile['ack']['ticks'], profile['ack'])
    return Operation((issue, data, ack), dependencies, holds=tuple(sorted(profile['hold_claims'].items())))


def intents(model, decisions):
    operations = []
    last_stage = {}
    writers = {}
    readers = {}
    stores = {}
    for decision in decisions:
        boundary = {last_stage[name] for name in decision.predecessors}
        pending_moves = set()
        for event in decision.row['evaluation']['events']:
            index = len(operations)
            inputs, outputs = accesses(event)
            dependencies = set(boundary)
            for window, value in inputs.items():
                if window == DDR:
                    if value not in model.initial.backing:
                        dependencies.add(stores[value])
                elif window in writers:
                    dependencies.add(writers[window])
            for window in outputs.keys() - {DDR}:
                if window in writers:
                    dependencies.add(writers[window])
                dependencies.update(readers.get(window, ()))
            if event['kind'] == 'stage':
                dependencies.update(pending_moves)
                pending_moves.clear()
                boundary = {index}
            else:
                pending_moves.add(index)
            operations.append(event_operation(model, event, frozenset(dependencies)))
            for window in inputs.keys() - outputs.keys() - {DDR}:
                readers.setdefault(window, set()).add(index)
            for window in outputs.keys() - {DDR}:
                writers[window] = index
                readers.pop(window, None)
            if DDR in outputs:
                stores.setdefault(outputs[DDR], index)
        for covered in decision.row['covers']:
            last_stage[covered] = index
        last_stage[decision.row['id']] = index
    return operations


def retime(model, decisions, proposed, previous=()):
    operations = intents(model, decisions)
    trace = replay(operations, model.capacity, previous=previous, issue_rates=model.issue_rates)
    grants = iter(zip(operations, trace))
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
            if len(phases) > 1:
                actual['phases'] = phases
            occupy(operation.holds, start, end)
            inputs, outputs = accesses(event)
            for window in inputs.keys() - {DDR}:
                copies[window] = replace(copies[window], held_until=max(copies[window].held_until, end))
            for window, value in outputs.items():
                if window == DDR:
                    backing[value] = min(end, backing.get(value, end))
                else:
                    copies[window] = Copy(value, end, end)
            events.append(actual)
        rows.append({**row, 'start': min(event['start'] for event in events),
                     'end': events[-1]['end'], 'evaluation': {**detail, 'events': events}})
    calendars = {resource: capacity_profile(changes) for resource, changes in occupancy.items()}
    return replace(proposed, copies=copies, backing=backing, calendars=calendars), rows, trace
