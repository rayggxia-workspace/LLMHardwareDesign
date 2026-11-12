"""Schedule qualified native stages and data moves against one execution state.

Resources use half-open capacity calendars. Scheduled operations keep their
reservations when another action is inserted. A window remains owned through
the consumer or destination acknowledgement. Only declared routes can move a
value. Times are integer service-model ticks, and external traffic is in bytes.
"""
from collections import Counter
from dataclasses import dataclass, replace

from dma_read import Profile, Read

DDR = 'DDR'


def backing_bytes(spec, values):
    addresses = (spec.get('typed_dma') or {}).get('addresses', {})
    sizes = spec['value_bytes']
    return sum(sizes[value] * (len(addresses[value]) if isinstance(addresses.get(value), dict) else 1)
               for value in values)


def window_phase_indices(service):
    """Return the read, write and publish phase indexes for native SRAM."""
    phases = service.get('phases', ())
    window_phases = service.get('window_phases', {})
    indexes = {phase['kind']: index for index, phase in enumerate(phases)}
    return (indexes.get(window_phases.get('read')), indexes.get(window_phases.get('write'), 0),
            indexes.get(window_phases.get('publish'), max(0, len(phases) - 1)))


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
    return capacity_profile(changes)


def capacity_profile(changes):
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
        self.issue_rates = {}
        for resource, rate in self.spec.get('issue_rates', {}).items():
            if (resource not in self.capacity or set(rate) != {'window_ticks', 'max_issues'}
                    or any(type(n) is not int or n < 1 for n in rate.values())):
                raise ValueError('invalid issue rate')
            self.issue_rates[resource] = rate['window_ticks'], rate['max_issues']
        self.windows = self.spec['windows']
        self.sizes = self.spec['value_bytes']
        self.services = self.spec['services']
        self.routes = self.spec['routes']
        dma = self.spec.get('typed_dma')
        self.dma_profile = Profile.from_spec(dma) if dma is not None else None
        self.dma_addresses = {} if dma is None else dma.get('addresses', {})
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
            if 'typed_dma' in route:
                self.validate_dma_route(route)
            self.routes_by_sites.setdefault(endpoints, []).append(name)
        for service in self.services.values():
            if type(service['ticks']) is not int or service['ticks'] < 1:
                raise ValueError('invalid native stage duration')
            self.validate_service(service)
            if 'phases' in service:
                self.validate_stage_phases(service)
            elif 'hold_claims' in service or 'window_phases' in service:
                raise ValueError('native stage holds and window phases require phases')
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
        self.validate_dma_addresses(set(external))
        if self.external_capacity is not None and (
                type(self.external_capacity) is not int or self.external_capacity < 0
                or backing_bytes(self.spec, external) > self.external_capacity):
            raise ValueError('invalid external backing capacity')
        self.initial = Execution({}, copies, dict.fromkeys(external, 0))

    def validate_service(self, service):
        if type(service.get('priority', 0)) is not int:
            raise ValueError('invalid native arbitration priority')
        if any(type(n) is not int or n < 1 or n > self.capacity.get(r, 0)
               or r in self.issue_rates and n > self.issue_rates[r][1]
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
        if holds.keys() & self.issue_rates.keys():
            raise ValueError('rate-limited issue ports cannot be held between phases')
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

    def validate_dma_route(self, route):
        params = route['typed_dma']
        if (self.dma_profile is None or route['src'] != DDR or 'phases' not in route
                or not isinstance(params, dict) or params.keys() - {'replica'} != {'client', 'record_beats'}
                or type(params['client']) is not int or type(params['record_beats']) is not int
                or not isinstance(params.get('replica', 'primary'), str) or not params.get('replica', 'primary')
                or not Read(params['client'], 0, 64 * params['record_beats'], params['record_beats']).valid()):
            raise ValueError('invalid typed DMA read route')

    def validate_dma_addresses(self, initial):
        if not isinstance(self.dma_addresses, dict) or self.dma_addresses.keys() - self.sizes.keys():
            raise ValueError('invalid typed DMA address map')
        regions = []
        for value, item in self.dma_addresses.items():
            replicas = isinstance(item, dict)
            if replicas and (value not in initial or not item or any(not isinstance(n, str) or not n for n in item)):
                raise ValueError('typed DMA replicas require named, initialized backing')
            for address in item.values() if replicas else (item,):
                if (type(address) is not int or address % 64
                        or not 0 <= address < address + self.sizes[value] <= 2**64):
                    raise ValueError('invalid typed DMA address map')
                regions.append((address, address + self.sizes[value], replicas))
        high = named_high = 0
        for start, end, named in sorted(regions):
            if start < named_high or named and start < high:
                raise ValueError('typed DMA backing replicas overlap physical ranges')
            high = max(high, end)
            if named:
                named_high = end

    def dma_read(self, route, value):
        params = route.get('typed_dma')
        if params is None:
            return None
        address = self.dma_addresses.get(value)
        name = params.get('replica', 'primary')
        if isinstance(address, dict):
            address = address.get(name)
        elif name != 'primary':
            address = None
        if address is None:
            raise Infeasible('typed DMA value needs a physical backing address for this route')
        read = Read(params['client'], address, self.sizes[value], params['record_beats'])
        if not read.valid():
            raise Infeasible('value does not fit typed DMA record geometry')
        return read

    def validate_stage_phases(self, service):
        phases = service['phases']
        holds = service.get('hold_claims', {})
        self.validate_service({'claims': holds})
        if holds.keys() & self.issue_rates.keys():
            raise ValueError('rate-limited issue ports cannot be held between phases')
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
        timing = service.get('window_phases', {})
        if (not isinstance(timing, dict) or timing.keys() - {'read', 'write', 'publish', 'result_hold'}
                or any(not isinstance(timing[field], str) or timing[field] not in names
                       for field in ('read', 'write', 'publish') if field in timing)
                or ('write' in timing) != ('publish' in timing)):
            raise ValueError('invalid SRAM window phases')
        _, write, publish = window_phase_indices(service)
        result_hold = timing.get('result_hold')
        if (publish < write or ((write or 'result_hold' in timing)
                                and (not isinstance(result_hold, str) or result_hold not in holds))):
            raise ValueError('deferred write requires a result hold and later publish')

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
        self.dma_read(route, value)
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
            if self.external_capacity is not None and backing_bytes(self.spec, backing) > self.external_capacity:
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

    def move_options(self, state, value, sources, dst, ready):
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
        return [item[-2:] for item in sorted(choices, key=lambda item: item[:5])]

    def best_move(self, state, value, sources, dst, ready, choose=None):
        options = self.move_options(state, value, sources, dst, ready)
        if not options:
            raise Infeasible('no legal move')
        return options[0] if choose is None else choose(options)

    def vacant(self, state, window, ready, protected, events, choose=None):
        old = state.copies.get(window)
        if old is None:
            return state, ready
        ready = max(ready, old.held_until)
        if (old.value in protected and old.value not in state.backing
                and not any(w != window and c.value == old.value for w, c in state.copies.items())):
            state, event = self.best_move(state, old.value, [window], DDR, ready, choose)
            events.append(event)
            ready = event['end']
        return state, ready

    def ensure(self, state, window, value, ready, protected, events, policy, choose=None):
        old = state.copies.get(window)
        if old and old.value == value and policy != 'backing':
            return state
        state, ready = self.vacant(state, window, ready, protected, events, choose)
        sources = [w for w, c in state.copies.items() if c.value == value and w != window]
        if policy == 'backing':
            if value not in state.backing:
                state, event = self.best_move(state, value, sources + ([window] if old and old.value == value else []),
                                              DDR, ready, choose)
                events.append(event)
                ready = event['end']
            sources = []
        if value in state.backing and policy != 'resident':
            sources.append(DDR)
        direct = self.move_options(state, value, sources, window, ready)
        choices = [(moved, [event]) for moved, event in direct]
        if policy == 'any' and value not in state.backing:
            # A dirty value may be cheaper to hand off via a real STORE/LOAD
            # than to wait for an occupied cross-site port.
            stores = self.move_options(state, value, sources, DDR, ready)
            for written, store in stores if choose is not None else stores[:1]:
                loads = self.move_options(written, value, [DDR], window, store['end'])
                choices.extend((loaded, [store, load]) for loaded, load in loads)
        if not choices:
            raise Infeasible('no legal input delivery')
        choices.sort(key=lambda item: (
            item[1][-1]['end'], item[0].read_bytes + item[0].write_bytes,
            self.wire_cost(item[0].nets)))
        selected, moves = choices[0] if choose is None else choose(choices)
        events.extend(moves)
        return selected

    def expand(self, state, binding, ready, protected, *, choose=None):
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
                                    stage.get('input_policy', 'any'), choose)
            start_at = max([ready] + [state.copies[w].ready for w in inputs])
            for value in inputs.values():
                remaining[value] -= 1
                if remaining[value] == 0:
                    del remaining[value]
            for window in outputs:
                evict_at = len(events)
                state, at = self.vacant(state, window, start_at, protected | remaining.keys(), events, choose)
                if 'write' in service.get('window_phases', {}) and len(events) > evict_at:
                    events[-1] = {**events[-1], 'output_eviction': window}
                start_at = max(start_at, at)
            state = self.add_nets(state, service.get('nets', ()))
            phases = ()
            if 'phases' in service:
                spec = tuple((p['kind'], p['ticks'], p['claims']) for p in service['phases'])
                state, start, end, phases = self.book_phases(
                    state, start_at, spec, service.get('hold_claims', {}))
            else:
                state, start, end = self.book(state, service['claims'], start_at, service['ticks'])
            read, _, publish = window_phase_indices(service)
            read_end = end if read is None else phases[read]['end']
            visible = phases[publish]['end'] if phases else end
            copies = state.copies.copy()
            for w in inputs:
                copies[w] = replace(copies[w], held_until=max(copies[w].held_until, read_end))
            for w, value in outputs.items():
                copies[w] = Copy(value, visible, visible)
            state = replace(state, copies=copies, read_bytes=state.read_bytes + service.get('read_bytes', 0),
                            write_bytes=state.write_bytes + service.get('write_bytes', 0))
            event = {'kind': 'stage', 'service': stage['service'], 'start': start, 'end': end,
                     'inputs': inputs, 'outputs': outputs}
            if phases:
                event['phases'] = phases
            events.append(event)
            ready = end
        return state, events
