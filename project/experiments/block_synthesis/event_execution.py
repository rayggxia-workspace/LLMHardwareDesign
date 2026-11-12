"""Schedule qualified native stages and data moves against one execution state.

Resources use half-open capacity calendars. Scheduled operations keep their
reservations when another action is inserted. A window remains owned through
the consumer or destination acknowledgement. Only declared routes can move a
value. Times are integer service-model ticks, and external traffic is in bytes.
"""
from collections import Counter
from dataclasses import dataclass, replace

DDR = 'DDR'


@dataclass(frozen=True)
class Copy:
    value: str
    ready: int
    held_until: int


@dataclass(frozen=True)
class Execution:
    calendars: dict
    copies: dict
    backing: dict
    nets: frozenset = frozenset()
    read_bytes: int = 0
    write_bytes: int = 0

    def key(self):
        return (tuple(sorted(self.calendars.items())), tuple(sorted(self.copies.items())),
                tuple(sorted(self.backing.items())), self.nets)

    def after(self, tick):
        """Drop calendar history before the earliest possible next action."""
        if not tick:
            return self
        calendars = {}
        for r, intervals in self.calendars.items():
            future = tuple((max(lo, tick), hi, n) for lo, hi, n in intervals if hi > tick)
            if future:
                calendars[r] = future
        copies = {w: Copy(c.value, max(tick, c.ready), max(tick, c.held_until))
                  for w, c in self.copies.items()}
        return replace(self, calendars=calendars, copies=copies,
                       backing={v: max(tick, at) for v, at in self.backing.items()})


class Infeasible(ValueError):
    """A valid action could not execute in this particular state."""


def available(profile, limit, start, ticks, units):
    """Return the first conflicting segment's end, or the proposed start."""
    for lo, hi, occupied in profile:
        if hi <= start:
            continue
        if lo >= start + ticks:
            break
        if occupied + units > limit:
            return hi
    return start


def reserve(profile, start, end, units):
    changes = {start: units, end: -units}
    for lo, hi, occupied in profile:
        changes[lo] = changes.get(lo, 0) + occupied
        changes[hi] = changes.get(hi, 0) - occupied
    result, level = [], 0
    for at, delta in sorted(changes.items()):
        if not delta:
            continue
        if level:
            result.append((previous, at, level))
        level += delta
        previous = at
    return tuple(result)


class Model:
    def __init__(self, hardware, *, wire_budget=None):
        self.spec = hardware['event_model']
        self.capacity = hardware['resources']
        self.windows = self.spec['windows']
        self.sizes = self.spec['value_bytes']
        self.services = self.spec['services']
        self.routes = self.spec['routes']
        self.routes_by_sites = {}
        self.live_out = frozenset(self.spec.get('live_out', ()))
        self.external_capacity = self.spec.get('external_capacity_bytes')
        self.nets = hardware['nets']
        self.fixed = frozenset(n for n, item in self.nets.items() if item.get('fixed'))
        self.conflicts = tuple(frozenset(pair) for pair in hardware.get('incompatible_nets', ()))
        self.wire_budget = wire_budget
        if self.spec.get('kind') != 'qualified-event-model-v1':
            raise ValueError('unknown event model')
        if any(type(c) is not int or c < 1 for c in self.capacity.values()):
            raise ValueError('invalid resource capacity')
        if any(type(b) is not int or b < 1 for b in self.sizes.values()):
            raise ValueError('invalid value size')
        if not self.live_out <= self.sizes.keys():
            raise ValueError('unknown live output')
        regions = {}
        for window, info in self.windows.items():
            site, start, size = info['site'], info['offset'], info['bytes']
            total = hardware['sites'][site]['bytes']
            if (window == DDR or site == DDR or type(start) is not int or type(size) is not int
                    or size <= 0 or start < 0 or start + size > total):
                raise ValueError('window outside finite site')
            used = regions.setdefault(site, [])
            if any(start < hi and lo < start + size for lo, hi in used):
                raise ValueError('overlapping physical windows')
            used.append((start, start + size))
        for name, route in self.routes.items():
            endpoints = route['src'], route['dst']
            if endpoints == (DDR, DDR) or any(s != DDR and s not in regions for s in endpoints):
                raise ValueError('unknown route site')
            if (type(route['setup']) is not int or route['setup'] < 0
                    or type(route['bytes_per_tick']) is not int or route['bytes_per_tick'] < 1):
                raise ValueError('invalid route timing')
            self.validate_service(route)
            if 'phases' in route:
                self.validate_route_phases(route)
            self.routes_by_sites.setdefault(endpoints, []).append(name)
        for service in self.services.values():
            if type(service['ticks']) is not int or service['ticks'] < 1:
                raise ValueError('invalid native stage duration')
            self.validate_service(service)
            if 'phases' in service:
                self.validate_stage_phases(service)
            elif 'hold_claims' in service:
                raise ValueError('native stage holds require phases')
            for field in ('read_bytes', 'write_bytes'):
                count = service.get(field, 0)
                if type(count) is not int or count < 0:
                    raise ValueError('invalid native stage traffic')
            if ((service.get('read_bytes') or service.get('write_bytes'))
                    and not (service['claims'] or any(p['claims'] for p in service.get('phases', ())))):
                raise ValueError('external native stage must reserve a resource')
        copies = {}
        for w, v in self.spec.get('initial_copies', {}).items():
            self.validate_copy(w, v)
            copies[w] = Copy(v, 0, 0)
        external = self.spec.get('initial_backing', ())
        if len(set(external)) != len(external) or not set(external) <= self.sizes.keys():
            raise ValueError('invalid initial backing')
        if self.external_capacity is not None and (
                type(self.external_capacity) is not int or self.external_capacity < 0
                or sum(self.sizes[v] for v in external) > self.external_capacity):
            raise ValueError('invalid external backing capacity')
        self.initial = Execution({}, copies, dict.fromkeys(external, 0))

    def validate_service(self, service):
        if type(service.get('priority', 0)) is not int:
            raise ValueError('invalid native arbitration priority')
        if any(type(n) is not int or n < 1 or n > self.capacity.get(r, 0)
               for r, n in service['claims'].items()):
            raise ValueError('invalid native resource claim')
        if not set(service.get('nets', ())) <= self.nets.keys():
            raise ValueError('unknown native net')

    def validate_route_phases(self, route):
        phases = route['phases']
        if set(phases) != {'issue', 'ack', 'hold_claims'}:
            raise ValueError('invalid phased route')
        holds = phases['hold_claims']
        self.validate_service({'claims': holds})
        used = set(route['claims'])
        for name in ('issue', 'ack'):
            item = phases[name]
            if (set(item) - {'priority'} != {'ticks', 'claims'}
                    or type(item['ticks']) is not int or item['ticks'] < 1):
                raise ValueError('invalid phased route endpoint')
            self.validate_service(item)
            used.update(item['claims'])
        if used & holds.keys():
            raise ValueError('phased route cannot claim a hold resource again')

    def validate_stage_phases(self, service):
        phases = service['phases']
        holds = service.get('hold_claims', {})
        self.validate_service({'claims': holds})
        if not isinstance(phases, (list, tuple)) or len(phases) < 2 or service['claims']:
            raise ValueError('phased native stage must declare separate phase claims')
        names = set()
        for phase in phases:
            if (set(phase) - {'priority'} != {'kind', 'ticks', 'claims'}
                    or not isinstance(phase['kind'], str) or not phase['kind']
                    or phase['kind'] in names or type(phase['ticks']) is not int or phase['ticks'] < 1
                    or phase['claims'].keys() & holds.keys()):
                raise ValueError('invalid native service phase')
            self.validate_service(phase)
            names.add(phase['kind'])
        if sum(p['ticks'] for p in phases) != service['ticks']:
            raise ValueError('native phase durations differ from optimistic service ticks')

    def validate_copy(self, window, value):
        if window not in self.windows or value not in self.sizes:
            raise ValueError('unknown window or value')
        if self.sizes[value] > self.windows[window]['bytes']:
            raise ValueError('value does not fit its window')

    def validate_binding(self, binding):
        stages = binding.get('event_stages')
        if not stages:
            raise ValueError('event mode requires explicit qualified stages for every binding')
        lower_bound = 0
        for stage in stages:
            lower_bound += self.services[stage['service']]['ticks']
            if stage.get('input_policy', 'any') not in ('any', 'resident', 'backing'):
                raise ValueError('unknown input policy')
            inputs, outputs = stage.get('inputs', {}), stage.get('outputs', {})
            for window, value in (*inputs.items(), *outputs.items()):
                self.validate_copy(window, value)
            if inputs.keys() & outputs.keys():
                raise ValueError('in-place native stages require a separate storage contract')
            if 'copy_sites' in self.services[stage['service']]:
                source, destinations = self.services[stage['service']]['copy_sites']
                if (len(inputs) != 1 or {self.windows[w]['site'] for w in inputs} != {source}
                        or sorted(self.windows[w]['site'] for w in outputs) != sorted(destinations)
                        or set(outputs.values()) != set(inputs.values())):
                    raise ValueError('COPY stage changes identity or endpoint')
        if not 0 < binding['ticks'] <= lower_bound:
            raise ValueError('invalid optimistic stage bound')

    def wire_cost(self, nets):
        return sum(self.nets[n]['cost'] for n in nets - self.fixed)

    def add_nets(self, state, nets):
        combined = state.nets | frozenset(nets)
        if (any(pair <= combined | self.fixed for pair in self.conflicts)
                or self.wire_budget is not None and self.wire_cost(combined) > self.wire_budget):
            raise Infeasible('static net conflict or budget')
        return replace(state, nets=combined)

    def book(self, state, claims, ready, ticks):
        start = ready
        while True:
            earliest = max((available(state.calendars.get(r, ()), self.capacity[r],
                                      start, ticks, n) for r, n in claims.items()), default=start)
            if earliest == start:
                break
            start = earliest
        end = start + ticks
        calendars = state.calendars.copy()
        for r, n in claims.items():
            calendars[r] = reserve(calendars.get(r, ()), start, end, n)
        return replace(state, calendars=calendars), start, end

    def book_route(self, state, route, ready, ticks):
        if 'phases' not in route:
            booked, start, end = self.book(state, route['claims'], ready, ticks)
            return booked, start, end, ()
        profile = route['phases']
        return self.book_phases(state, ready, (
            ('issue', profile['issue']['ticks'], profile['issue']['claims']),
            ('data', ticks, route['claims']),
            ('ack', profile['ack']['ticks'], profile['ack']['claims']),
        ), profile['hold_claims'])

    def book_phases(self, state, ready, phases, holds):
        while True:
            booked = state
            trace = []
            at = ready
            for kind, duration, claims in phases:
                booked, start, at = self.book(booked, claims, at, duration)
                trace.append({'kind': kind, 'start': start, 'end': at})
            begin = trace[0]['start']
            _, hold_start, _ = self.book(state, holds, begin, at-begin)
            if hold_start == begin:
                booked, _, _ = self.book(booked, holds, begin, at-begin)
                return booked, begin, at, trace
            ready = hold_start

    def move(self, state, value, src, dst, ready, route_name):
        route = self.routes[route_name]
        size = self.sizes[value]
        ticks = route['setup'] + (size + route['bytes_per_tick'] - 1) // route['bytes_per_tick']
        state = self.add_nets(state, route.get('nets', ()))
        source_ready = state.backing[value] if src == DDR else state.copies[src].ready
        state, start, end, phases = self.book_route(state, route, max(ready, source_ready), ticks)
        copies, backing = state.copies.copy(), state.backing.copy()
        if src != DDR:
            copies[src] = replace(copies[src], held_until=max(copies[src].held_until, end))
        if dst == DDR:
            backing[value] = end
            if self.external_capacity is not None and sum(self.sizes[v] for v in backing) > self.external_capacity:
                raise Infeasible('external backing capacity')
        else:
            copies[dst] = Copy(value, end, end)
        state = replace(state, copies=copies, backing=backing,
                        read_bytes=state.read_bytes + (size if src == DDR else 0),
                        write_bytes=state.write_bytes + (size if dst == DDR else 0))
        event = {'kind': 'move', 'route': route_name, 'value': value,
                 'src': src, 'dst': dst, 'start': start, 'end': end}
        if phases:
            event['phases'] = phases
        return state, event

    def best_move(self, state, value, sources, dst, ready):
        destination = DDR if dst == DDR else self.windows[dst]['site']
        choices = []
        for src in sources:
            site = DDR if src == DDR else self.windows[src]['site']
            for route in self.routes_by_sites.get((site, destination), ()):
                try:
                    new, event = self.move(state, value, src, dst, ready, route)
                except Infeasible:
                    continue
                choices.append((event['end'], new.read_bytes + new.write_bytes,
                                self.wire_cost(new.nets), src, route, new, event))
        if not choices:
            raise Infeasible('no legal move')
        return min(choices, key=lambda item: item[:5])[-2:]

    def vacant(self, state, window, ready, protected, events):
        old = state.copies.get(window)
        if old is None:
            return state, ready
        ready = max(ready, old.held_until)
        if (old.value in protected and old.value not in state.backing
                and not any(w != window and c.value == old.value for w, c in state.copies.items())):
            state, event = self.best_move(state, old.value, [window], DDR, ready)
            events.append(event)
            ready = event['end']
        return state, ready

    def ensure(self, state, window, value, ready, protected, events, policy):
        old = state.copies.get(window)
        if old and old.value == value and policy != 'backing':
            return state
        state, ready = self.vacant(state, window, ready, protected, events)
        sources = [w for w, c in state.copies.items() if c.value == value and w != window]
        if policy == 'backing':
            if value not in state.backing:
                state, event = self.best_move(state, value, sources + ([window] if old and old.value == value else []),
                                              DDR, ready)
                events.append(event)
                ready = event['end']
            sources = []
        if value in state.backing and policy != 'resident':
            sources.append(DDR)
        choices = []
        try:
            direct, event = self.best_move(state, value, sources, window, ready)
            choices.append((direct, [event]))
        except Infeasible:
            pass
        if policy == 'any' and value not in state.backing:
            # A dirty value may be cheaper to hand off via a real STORE/LOAD
            # than to wait for an occupied cross-site port.
            try:
                written, store = self.best_move(state, value, sources, DDR, ready)
                loaded, load = self.best_move(written, value, [DDR], window, store['end'])
                choices.append((loaded, [store, load]))
            except Infeasible:
                pass
        if not choices:
            raise Infeasible('no legal input delivery')
        selected, moves = min(choices, key=lambda item: (
            item[1][-1]['end'], item[0].read_bytes + item[0].write_bytes,
            self.wire_cost(item[0].nets)))
        events.extend(moves)
        return selected

    def expand(self, state, binding, ready, protected):
        protected = protected | self.live_out
        remaining = Counter(value for stage in binding['event_stages']
                            for value in stage.get('inputs', {}).values())
        events = []
        state = self.add_nets(state, binding['nets'])
        for stage in binding['event_stages']:
            service = self.services[stage['service']]
            inputs, outputs = stage.get('inputs', {}), stage.get('outputs', {})
            for window, value in inputs.items():
                state = self.ensure(state, window, value, ready, protected | remaining.keys(), events,
                                    stage.get('input_policy', 'any'))
            start_at = max([ready] + [state.copies[w].ready for w in inputs])
            for value in inputs.values():
                remaining[value] -= 1
                if remaining[value] == 0:
                    del remaining[value]
            for window in outputs:
                state, at = self.vacant(state, window, start_at, protected | remaining.keys(), events)
                start_at = max(start_at, at)
            state = self.add_nets(state, service.get('nets', ()))
            phases = ()
            if 'phases' in service:
                spec = tuple((p['kind'], p['ticks'], p['claims']) for p in service['phases'])
                state, start, end, phases = self.book_phases(
                    state, start_at, spec, service.get('hold_claims', {}))
            else:
                state, start, end = self.book(state, service['claims'], start_at, service['ticks'])
            copies = state.copies.copy()
            for w in inputs:
                copies[w] = replace(copies[w], held_until=max(copies[w].held_until, end))
            for w, value in outputs.items():
                copies[w] = Copy(value, end, end)
            state = replace(state, copies=copies, read_bytes=state.read_bytes + service.get('read_bytes', 0),
                            write_bytes=state.write_bytes + service.get('write_bytes', 0))
            event = {'kind': 'stage', 'service': stage['service'], 'start': start, 'end': end,
                     'inputs': inputs, 'outputs': outputs}
            if phases:
                event['phases'] = phases
            events.append(event)
            ready = end
        return state, events
