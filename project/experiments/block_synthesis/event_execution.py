"""Schedule qualified native stages and data moves against one execution state.

Resources use half-open capacity calendars. Scheduled operations keep their
reservations when another action is inserted. A window remains owned through
the consumer or destination acknowledgement. Only declared routes can move a
value. Times are integer service-model ticks, and external traffic is in bytes.
"""
from dataclasses import dataclass, replace

DDR = 'DDR'


def stage_graph(stages):
    """Return the declared stages and dependencies, preserving legacy serial lists."""
    graph = {}
    explicit = any('id' in stage or 'after' in stage for stage in stages)
    for index, stage in enumerate(stages):
        name = stage.get('id') if explicit else index
        parents = tuple(stage.get('after', ())) if explicit else ((index - 1,) if index else ())
        if (explicit and (not isinstance(name, str) or not name) or name in graph
                or len(set(parents)) != len(parents) or any(parent not in graph for parent in parents)):
            raise ValueError('invalid event stage identity or topological order')
        graph[name] = (stage, parents)
    return graph


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
    def __init__(self, hardware, *, wire_budget=None, required_nets=(), route_admission=None):
        self.spec = hardware['event_model']
        self.capacity = hardware['resources']
        self.windows = self.spec['windows']
        self.sizes = self.spec['value_bytes']
        self.services = self.spec['services']
        self.routes = self.spec['routes']
        self.product_interfaces = 'physical_interface_issues' in self.spec
        interface_issues = self.spec.get('physical_interface_issues', {})
        logical_issues = self.spec.get('logical_control_issues', {})
        self.unqualified_routes = interface_issues.get('routes', {}).keys() | logical_issues.get('routes', {}).keys()
        self.unqualified_services = (interface_issues.get('services', {}).keys() |
                                     logical_issues.get('services', {}).keys())
        self.routes_by_sites = {}
        self.live_out = frozenset(self.spec.get('live_out', ()))
        self.external_capacity = self.spec.get('external_capacity_bytes')
        self.nets = hardware['nets']
        self.fixed = frozenset(n for n, item in self.nets.items() if item.get('fixed'))
        self.net_dependencies = {name: frozenset(item['requires']) for name, item in self.nets.items()
                                 if item.get('requires')}
        if any(not deps <= self.nets.keys() for deps in self.net_dependencies.values()):
            raise ValueError('required connection is missing from the hardware budget')
        self.conflicts = tuple(frozenset(pair) for pair in hardware.get('incompatible_nets', ()))
        self.wire_budget = wire_budget
        self.route_admission = route_admission
        self.required_nets = frozenset(required_nets)
        self.excluded_nets = frozenset(self.spec.get('excluded_nets', ()))
        if not self.excluded_nets <= self.nets.keys() or self.excluded_nets & self.fixed:
            raise ValueError('event trial excludes an unknown or fixed net')
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
            if name not in self.unqualified_routes:
                self.routes_by_sites.setdefault(endpoints, []).append(name)
        for service in self.services.values():
            if type(service['ticks']) is not int or service['ticks'] < 1:
                raise ValueError('invalid native stage duration')
            self.validate_service(service)
            for field in ('read_bytes', 'write_bytes'):
                count = service.get(field, 0)
                if type(count) is not int or count < 0:
                    raise ValueError('invalid native stage traffic')
            if (service.get('read_bytes') or service.get('write_bytes')) and not service['claims']:
                raise ValueError('external native stage must reserve a resource')
            indexed = service.get('indexed_read')
            if indexed and (indexed['table'] not in self.spec.get('initial_backing', ())
                            or self.sizes[indexed['table']] != indexed['rows'] * indexed['row_words'] * 16
                            or service.get('read_bytes') != indexed['indices'] * indexed['row_words'] * 16):
                raise ValueError('indexed stage does not bind the declared external table and traffic')
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
            if set(item) != {'ticks', 'claims'} or type(item['ticks']) is not int or item['ticks'] < 1:
                raise ValueError('invalid phased route endpoint')
            self.validate_service(item)
            used.update(item['claims'])
        if used & holds.keys():
            raise ValueError('phased route cannot claim a hold resource again')

    def validate_copy(self, window, value):
        if window not in self.windows or value not in self.sizes:
            raise ValueError('unknown window or value')
        if self.sizes[value] > self.windows[window]['bytes']:
            raise ValueError('value does not fit its window')

    def validate_binding(self, binding):
        stages = binding.get('event_stages')
        if not stages:
            raise ValueError('event mode requires explicit qualified stages for every binding')
        ends, ancestors = {}, {}
        writers = {}
        for name, (stage, parents) in stage_graph(stages).items():
            ends[name] = self.services[stage['service']]['ticks'] + max((ends[p] for p in parents), default=0)
            ancestors[name] = set(parents).union(*(ancestors[p] for p in parents))
            if stage.get('input_policy', 'any') not in ('any', 'resident', 'backing'):
                raise ValueError('unknown input policy')
            inputs, outputs = stage.get('inputs', {}), stage.get('outputs', {})
            for window, value in (*inputs.items(), *outputs.items()):
                self.validate_copy(window, value)
            if inputs.keys() & outputs.keys():
                raise ValueError('in-place native stages require a separate storage contract')
            indexed = self.services[stage['service']].get('indexed_read')
            if indexed and (len(inputs) != 1 or len(outputs) != 1
                            or self.sizes[next(iter(inputs.values()))] != indexed['indices'] * indexed['index_bits'] // 8
                            or self.sizes[next(iter(outputs.values()))] != indexed['indices'] * indexed['row_words'] * 16):
                raise ValueError('indexed stage requires a correctly sized index and destination')
            for value in inputs.values():
                if value in writers and not writers[value] & ancestors[name]:
                    raise ValueError('stage input missing its producer dependency')
            for value in outputs.values():
                writers.setdefault(value, set()).add(name)
            if 'copy_sites' in self.services[stage['service']]:
                source, destinations = self.services[stage['service']]['copy_sites']
                if (len(inputs) != 1 or {self.windows[w]['site'] for w in inputs} != {source}
                        or sorted(self.windows[w]['site'] for w in outputs) != sorted(destinations)
                        or set(outputs.values()) != set(inputs.values())):
                    raise ValueError('COPY stage changes identity or endpoint')
        if not 0 < binding['ticks'] <= max(ends.values()):
            raise ValueError('invalid optimistic stage bound')

    def network_closure(self, nets):
        if not self.net_dependencies:
            return nets
        closed = set(nets)
        pending = list(nets)
        while pending:
            more = self.net_dependencies.get(pending.pop(), frozenset()) - closed
            closed.update(more)
            pending.extend(more)
        return frozenset(closed)

    def wire_cost(self, nets):
        return sum(self.nets[n]['cost'] for n in self.network_closure(nets) - self.fixed)

    def add_nets(self, state, nets):
        combined = state.nets | frozenset(nets)
        needed = self.network_closure(combined | self.required_nets)
        if (needed & self.excluded_nets or any(pair <= needed | self.fixed for pair in self.conflicts)
                or self.wire_budget is not None and self.wire_cost(needed) > self.wire_budget
                or self.route_admission is not None and not self.route_admission(needed)):
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
        holds = profile['hold_claims']
        while True:
            booked = state
            trace = []
            at = ready
            for kind, duration, claims in (
                ('issue', profile['issue']['ticks'], profile['issue']['claims']),
                ('data', ticks, route['claims']),
                ('ack', profile['ack']['ticks'], profile['ack']['claims']),
            ):
                booked, start, at = self.book(booked, claims, at, duration)
                trace.append({'kind': kind, 'start': start, 'end': at})
            begin = trace[0]['start']
            conflict_end = max((available(state.calendars.get(resource, ()),
                                          self.capacity[resource], begin, at - begin, units)
                                for resource, units in holds.items()), default=begin)
            if conflict_end == begin:
                booked, _, _ = self.book(booked, holds, begin, at - begin)
                return booked, begin, at, trace
            # Recompute the phases at the next opportunity. The earlier wait for
            # the data bus may disappear, allowing a shorter credit reservation.
            ready = conflict_end

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

    def moves(self, state, value, sources, dst, ready):
        destination = DDR if dst == DDR else self.windows[dst]['site']
        for src in sources:
            site = DDR if src == DDR else self.windows[src]['site']
            for route in self.routes_by_sites.get((site, destination), ()):
                try:
                    yield self.move(state, value, src, dst, ready, route)
                except Infeasible:
                    continue

    def vacancies(self, state, window, ready, protected, events):
        old = state.copies.get(window)
        if old is None:
            yield state, ready, events
            return
        ready = max(ready, old.held_until)
        if (old.value in protected and old.value not in state.backing
                and not any(w != window and c.value == old.value for w, c in state.copies.items())):
            for new, event in self.moves(state, old.value, (window,), DDR, ready):
                yield new, event['end'], (*events, event)
        else:
            yield state, ready, events

    def deliveries(self, state, window, value, ready, protected, events, policy):
        old = state.copies.get(window)
        if old and old.value == value and policy != 'backing':
            yield state, events
            return
        for vacant, at, prefix in self.vacancies(state, window, ready, protected, events):
            sources = tuple(w for w, c in vacant.copies.items() if c.value == value and w != window)
            if policy != 'backing':
                direct = (*sources, DDR) if value in vacant.backing and policy != 'resident' else sources
                for loaded, load in self.moves(vacant, value, direct, window, at):
                    yield loaded, (*prefix, load)
            elif value in vacant.backing:
                for loaded, load in self.moves(vacant, value, (DDR,), window, at):
                    yield loaded, (*prefix, load)
            if policy == 'resident' or value in vacant.backing:
                continue
            spill_sources = (*sources, window) if old and old.value == value else sources
            for written, store in self.moves(vacant, value, spill_sources, DDR, at):
                for loaded, load in self.moves(written, value, (DDR,), window, store['end']):
                    yield loaded, (*prefix, store, load)

    def stage_choices(self, state, stage, ready, protected, events):
        if stage['service'] in self.unqualified_services:
            return
        service = self.services[stage['service']]
        if self.product_interfaces:
            from event_physical_contract import stage_is_local

            if not stage_is_local(self.windows, service, stage):
                return
        inputs, outputs = stage.get('inputs', {}), stage.get('outputs', {})
        policy = stage.get('input_policy', 'any')

        def prepare(index, current, trace):
            if index == len(inputs):
                yield current, trace
                return
            window, value = operands[index]
            for loaded, path in self.deliveries(current, window, value, ready,
                                                 protected | input_values, trace, policy):
                yield from prepare(index + 1, loaded, path)

        def clear(index, current, at, trace):
            if index == len(destinations):
                yield current, at, trace
                return
            for vacant, available_at, path in self.vacancies(current, destinations[index], at,
                                                             protected | input_values, trace):
                yield from clear(index + 1, vacant, available_at, path)

        operands, destinations = tuple(inputs.items()), tuple(outputs)
        input_values = set(inputs.values())
        try:
            state = self.add_nets(state, service.get('nets', ()))
        except Infeasible:
            return
        for loaded, input_events in prepare(0, state, events):
            start_at = max([ready] + [loaded.copies[w].ready for w in inputs])
            for vacant, at, trace in clear(0, loaded, start_at, input_events):
                booked, start, end = self.book(vacant, service['claims'], at, service['ticks'])
                copies = booked.copies.copy()
                for w in inputs:
                    copies[w] = replace(copies[w], held_until=max(copies[w].held_until, end))
                for w, value in outputs.items():
                    copies[w] = Copy(value, end, end)
                booked = replace(booked, copies=copies,
                                 read_bytes=booked.read_bytes + service.get('read_bytes', 0),
                                 write_bytes=booked.write_bytes + service.get('write_bytes', 0))
                event = {'kind': 'stage', 'service': stage['service'], 'start': start, 'end': end,
                         'inputs': inputs, 'outputs': outputs}
                yield booked, (*trace, event)

    def expand_choices(self, state, binding, ready, protected):
        """Enumerate feasible successors before scoring a complete action."""
        graph = stage_graph(binding['event_stages'])
        protected = protected | self.live_out
        try:
            state = self.add_nets(state, binding['nets'])
        except Infeasible:
            return

        # Traverse iteratively: measured recipes can contain hundreds of serial stages.
        stack = [(state, {}, ())]
        while stack:
            current, ends, events = stack.pop()
            if len(ends) == len(graph):
                yield current, list(events)
                continue
            for name, (stage, parents) in reversed(graph.items()):
                if name in ends or any(parent not in ends for parent in parents):
                    continue
                future_values = {value for other, (entry, _) in graph.items()
                                 if other != name and other not in ends
                                 for value in entry.get('inputs', {}).values()}
                at = max((ends[parent] for parent in parents), default=ready)
                for booked, trace in self.stage_choices(current, stage, at, protected | future_values, ()):
                    if isinstance(name, str):
                        trace = tuple({**event, 'stage_id': name} for event in trace)
                    stack.append((booked, {**ends, name: trace[-1]['end']}, (*events, *trace)))

    def expand(self, state, binding, ready, protected):
        """Return the best complete successor for a stand-alone service evaluation."""
        def score(item):
            execution, events = item
            return (max(event['end'] for event in events),
                    execution.read_bytes + execution.write_bytes, self.wire_cost(execution.nets))

        best = min(self.expand_choices(state, binding, ready, protected), key=score, default=None)
        if best is None:
            raise Infeasible('no legal event expansion')
        return best
