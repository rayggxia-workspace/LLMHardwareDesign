"""Joint service binding, time/address allocation, spill and static-net planning.

The solver consumes *lowered* tensor tiles and qualified service alternatives.
No op is assigned a service by name guessing. Durations are required inputs;
this module never invents throughput, memory bandwidth, or conversion hardware.
"""
from collections import defaultdict
from copy import deepcopy
import time


class Unsupported(ValueError):
    pass


def eligible(task, service, values):
    if (service['op'], service['numeric'], service.get('qualified')) != (task['op'], task['numeric'], True):
        return False
    if task.get('domain', '') != service.get('domain', ''):
        return False
    for field, names in [('input_words', task['inputs']), ('output_words', task['outputs'])]:
        if field in service and service[field] != [values[n]['words'] for n in names]:
            return False
    return task.get('attributes', {}) == service.get('attributes', {})


def check_input(graph, hardware):
    tasks = graph['tasks']
    ids = {t['id'] for t in tasks}
    if len(ids) != len(tasks):
        raise ValueError('duplicate task ID')
    services = hardware['services']
    for service in services.values():
        if any(n not in hardware['nets'] for n in service.get('nets', [])):
            raise ValueError('service refers to an undeclared connection demand')
        state = service.get('state_resource')
        if state and (state not in hardware['resources'] or hardware['resources'][state] != 1 or state in service['resources']):
            raise ValueError('macro state needs its own exclusive resource')
    from contexts import membership
    membership(graph)
    sites = set(hardware['sites']) | {hardware['external']}
    if any(int(c) < 1 for c in hardware['resources'].values()):
        raise ValueError('resource capacity must be positive')
    if any(int(s['words']) < 1 for s in hardware['sites'].values()):
        raise ValueError('S capacity must be positive')
    produced = set()
    for task in tasks:
        valid = []
        for sid in task.get('alternatives', services):
            service = services[sid]
            if eligible(task, service, graph['values']) and int(service['ticks']) > 0:
                valid.append(sid)
        if not valid:
            raise Unsupported(f"{task['id']}: no qualified {task['op']}/{task['numeric']} service")
        for name in task['outputs']:
            if name in produced:
                raise ValueError('multiple tensor producers: ' + name)
            produced.add(name)
    for name, value in graph['values'].items():
        if int(value['words']) <= 0:
            raise ValueError('nonpositive tile extent: ' + name)
        if 'producer' in value and value['producer'] not in ids:
            raise ValueError('unknown producer: ' + name)
        if 'producer' in value:
            if value.get('external_copy') or 'site' in value:
                raise ValueError('generated tile cannot claim a preexisting copy: ' + name)
            producer = next(t for t in tasks if t['id'] == value['producer'])
            if name not in producer['outputs']:
                raise ValueError('producer does not produce: ' + name)
        elif value.get('site') not in sites:
            raise ValueError('input site is unknown: ' + name)
    for task in tasks:
        for name in task['inputs'] + task['outputs']:
            if name not in graph['values']:
                raise ValueError('unknown tensor tile: ' + name)
        if any(graph['values'][n].get('producer') != task['id'] for n in task['outputs']):
            raise ValueError('task output producer mismatch')
    dependencies = {t['id']: set(t.get('after', [])) |
                    {graph['values'][v]['producer'] for v in t['inputs'] if 'producer' in graph['values'][v]}
                    for t in tasks}
    remaining = dict(dependencies)
    while remaining:
        ready = {t for t, deps in remaining.items() if not deps}
        if not ready:
            raise ValueError('cyclic task graph or unknown precedence')
        remaining = {t: deps - ready for t, deps in remaining.items() if t not in ready}
    for route in hardware['routes'].values():
        if not route.get('qualified', False):
            continue
        if not route['phases'] or any(p['ticks'] <= 0 for p in route['phases']):
            raise ValueError('route needs declared positive phase durations')
        if route.get('protocol') != 'acknowledged_copy':
            raise ValueError('route completion must acknowledge destination commit')
        if route['src'] not in sites or route['dst'] not in sites:
            raise ValueError('unknown route endpoint')
        if any(n not in hardware['nets'] for n in route.get('nets', [])):
            raise ValueError('unknown physical net')


class Planner:
    def __init__(self, graph, hardware, wire_budget=None, fixed=None, hint=None, tied=()):
        from ortools.sat.python import cp_model
        check_input(graph, hardware)
        self.cp = cp_model
        self.model = cp_model.CpModel()
        self.g, self.h = graph, hardware
        self.tasks = {t['id']: t for t in graph['tasks']}
        self.consumers = defaultdict(list)
        for tid, task in self.tasks.items():
            for name in set(task['inputs']):
                self.consumers[name].append(tid)
        self.services = hardware['services']
        self.routes = {k: r for k, r in hardware['routes'].items() if r.get('qualified')}
        self.fixed = fixed or {}
        self.tied = [list(family) for family in tied]
        self.claims = defaultdict(list)
        self.allocations = defaultdict(list)
        self.jobs, self.moves, self.copies = {}, [], []
        self.users = defaultdict(list)
        self.spills = {}
        self.net_users = defaultdict(list)
        self.route_users = defaultdict(list)
        self.copy_seq = 0
        self.horizon = max(1, sum(max(
            int(s['ticks']) for s in self.services.values()
            if s['op'] == t['op'] and s['numeric'] == t['numeric'] and s.get('qualified'))
            for t in graph['tasks']))
        route_max = max((sum(p['ticks'] for p in r['phases']) for r in self.routes.values()), default=0)
        self.horizon += route_max * (3 * sum(len(t['inputs']) for t in graph['tasks']) + len(graph['values']) + 1)
        self.makespan = self.integer('makespan')
        self._jobs()
        self._contexts()
        for family in tied:
            if len(family) < 2:
                continue
            first = self.jobs[family[0]]['choices']
            for tid in family[1:]:
                other = self.jobs[tid]['choices']
                if set(first) != set(other):
                    raise ValueError('tied task alternatives differ')
                for sid in first:
                    self.model.add(first[sid] == other[sid])
        self._inputs()
        self._memory()
        self._resources()
        self._nets(wire_budget)
        if hardware.get('external_capacity_words') is not None:
            external_flags = defaultdict(list)
            for m in self.moves:
                if m['dst'] == hardware['external']:
                    external_flags[m['value']].append(m['on'])
            footprint = [o['words'] for o in graph.get('external_objects', {}).values()]
            for name, v in graph['values'].items():
                if v.get('site') == hardware['external'] or v.get('external_copy'):
                    footprint.append(v['words'])
                elif external_flags[name]:
                    on = self.boolean('external-region:' + name)
                    self.model.add_max_equality(on, external_flags[name])
                    footprint.append(v['words'] * on)
            self.model.add(sum(footprint) <= hardware['external_capacity_words'])
        ends = [j['end'] for j in self.jobs.values()]
        ends += [m['end'] for m in self.moves if m.get('final')]
        self.model.add_max_equality(self.makespan, ends or [0])
        # Latency is primary. Secondary traffic/wire optimization is performed
        # only after a proven optimum, keeping the reported bound in ticks.
        # Static resources have a hard budget, not an arbitrary cycles/wire sum.
        self.traffic = sum(m['words'] * m['on'] for m in self.moves
                           if self.h['external'] in (m['src'], m['dst']))
        self.traffic += sum(self.services[sid].get('external_read_words', 0) * on
                            for job in self.jobs.values() for sid, on in job['choices'].items())
        self.model.minimize(self.makespan)
        if hint:
            for tid, row in hint['tasks'].items():
                if tid in self.jobs:
                    for sid, on in self.jobs[tid]['choices'].items():
                        self.model.add_hint(on, int(sid == row['service']))
                    self.model.add_hint(self.jobs[tid]['start'], row['start'])

    def integer(self, name):
        return self.model.new_int_var(0, self.horizon, name)

    def boolean(self, name):
        return self.model.new_bool_var(name)

    def conjunction(self, *items, name):
        on = self.boolean(name)
        self.model.add_bool_and(list(items)).only_enforce_if(on)
        self.model.add_bool_or([v.Not() for v in items] + [on])
        return on

    def gated_end(self, end, on, name):
        result = self.integer(name)
        self.model.add(result == end).only_enforce_if(on)
        self.model.add(result == 0).only_enforce_if(on.Not())
        return result

    def claim(self, resource, start, end, on, name, demand=1):
        if resource not in self.h['resources']:
            raise ValueError('undeclared resource: ' + resource)
        duration = self.integer(name + ':duration')
        self.model.add(duration == end - start).only_enforce_if(on)
        interval = self.model.new_optional_interval_var(start, duration, end, on, name)
        self.claims[resource].append((interval, demand, start, end, on, name))

    def _jobs(self):
        for tid, task in self.tasks.items():
            start, end = self.integer(tid + ':start'), self.integer(tid + ':end')
            choices = {}
            candidates = task.get('alternatives', self.services)
            if tid in self.fixed:
                if self.fixed[tid] not in candidates:
                    raise ValueError('fixed binding is not a task alternative: ' + tid)
                candidates = [self.fixed[tid]]
            for sid in candidates:
                service = self.services[sid]
                if not eligible(task, service, self.g['values']):
                    continue
                on = self.boolean(tid + ':' + sid)
                choices[sid] = on
                for net in service.get('nets', []):
                    self.net_users[net].append(on)
                self.model.add(end == start + service['ticks']).only_enforce_if(on)
                for resource in service['resources']:
                    self.claim(resource, start, end, on, tid + ':' + resource)
                scratch = service.get('scratch_words', 0)
                if scratch:
                    self.allocate(service['site'], tid + ':scratch:' + sid, scratch, start, end, on)
                if tid in self.fixed:
                    self.model.add(on == int(sid == self.fixed[tid]))
            self.model.add_exactly_one(list(choices.values()))
            self.jobs[tid] = {'start': start, 'end': end, 'choices': choices}
        for tid, task in self.tasks.items():
            for prior in task.get('after', []):
                self.model.add(self.jobs[tid]['start'] >= self.jobs[prior]['end'])

    def _contexts(self):
        from contexts import membership
        member = membership(self.g)
        for number, group in enumerate(self.g.get('state_groups', [])):
            choices = []
            for tid in group['tasks']:
                by_resource = defaultdict(list)
                for sid, on in self.jobs[tid]['choices'].items():
                    resource = self.services[sid].get('state_resource')
                    if not resource:
                        raise ValueError('state group contains a stateless service')
                    by_resource[resource].append(on)
                choices.append(by_resource)
            common = set.intersection(*(set(c) for c in choices))
            if not common:
                self.model.add(False)  # e.g. incompatible fixed LNS bindings
                continue
            start, end = self.integer(f'context:{number}:start'), self.integer(f'context:{number}:end')
            self.model.add_min_equality(start, [self.jobs[t]['start'] for t in group['tasks']])
            self.model.add_max_equality(end, [self.jobs[t]['end'] for t in group['tasks']])
            for resource in set.union(*(set(c) for c in choices)):
                on = self.boolean(f'context:{number}:{resource}')
                if resource not in common:
                    self.model.add(on == 0)
                for c in choices:
                    self.model.add(sum(c.get(resource, [])) == on)
                if resource in common:
                    self.claim(resource, start, end, on, f'context:{number}:{resource}')
        for tid, job in self.jobs.items():
            if tid in member:
                continue
            for sid, on in job['choices'].items():
                resource = self.services[sid].get('state_resource')
                if resource:
                    self.claim(resource, job['start'], job['end'], on, tid + ':state')

    def owner_choices(self, value):
        if 'producer' not in value:
            return [(value['site'], None)]
        job = self.jobs[value['producer']]
        by_site = defaultdict(list)
        for sid, on in job['choices'].items():
            by_site[self.services[sid]['site']].append(on)
        result = []
        for site, members in by_site.items():
            on = self.boolean(f"owner:{value['producer']}:{site}:{len(self.copies)}")
            self.model.add(on == sum(members))
            result.append((site, on))
        return result

    def move(self, value_name, src, dst, ready, on, *, final=False):
        value = self.g['values'][value_name]
        copy_id = f'copy-{self.copy_seq}'
        self.copy_seq += 1
        options = []
        for rid, route in self.routes.items():
            if (route['src'], route['dst']) != (src, dst):
                continue
            if not route.get('min_words', 1) <= value['words'] <= route.get('max_words', 1):
                continue
            selected = self.boolean(f'move:{len(self.moves)}:{rid}')
            phase_rows, prior = [], ready
            for index, phase in enumerate(route['phases']):
                start, end = self.integer(f'{rid}:{len(self.moves)}:{index}:s'), self.integer(f'{rid}:{len(self.moves)}:{index}:e')
                self.model.add(start >= prior).only_enforce_if(selected)
                self.model.add(end == start + phase['ticks']).only_enforce_if(selected)
                self.model.add(start == 0).only_enforce_if(selected.Not())
                self.model.add(end == 0).only_enforce_if(selected.Not())
                for resource in phase.get('resources', []):
                    self.claim(resource, start, end, selected, f'move:{len(self.moves)}:{index}:{resource}')
                phase_rows.append({'name': phase['name'], 'start': start, 'end': end})
                prior = end
            row = {'value': value_name, 'src': src, 'dst': dst, 'route': rid, 'copy_id': copy_id,
                   'on': selected, 'start': phase_rows[0]['start'], 'end': prior,
                   'phases': phase_rows, 'words': value['words'], 'final': final}
            for hold in route.get('holds', []):
                first = phase_rows[hold.get('first_phase', 0)]['start']
                self.claim(hold['resource'], first, prior, selected, f'hold:{len(self.moves)}:{hold["resource"]}')
            self.moves.append(row)
            self.route_users[rid].append(selected)
            for net in route.get('nets', []):
                self.net_users[net].append(selected)
            options.append(row)
        self.model.add(sum(o['on'] for o in options) == on)
        if not options:
            return {'start': 0, 'end': 0, 'copy_id': copy_id}
        start, end = self.integer('move-start'), self.integer('move-end')
        self.model.add(start == sum(o['start'] for o in options))
        self.model.add(end == sum(o['end'] for o in options))
        return {'start': start, 'end': end, 'copy_id': copy_id}

    def allocate(self, site, name, words, start, end, on, value=None, origin=None):
        if site == self.h['external']:
            return
        capacity = int(self.h['sites'][site]['words'])
        if words > capacity:
            self.model.add(on == 0)
            return
        addr = self.model.new_int_var(0, capacity - words, name + ':address')
        self.allocations[site].append({'id': name, 'value': value, 'origin': origin, 'words': words, 'start': start,
                                      'end': end, 'on': on, 'address': addr})

    def _inputs(self):
        ext = self.h['external']
        # Producers reserve their output before execution. The source lease ends
        # only after local consumption, acknowledged copies, or acknowledged spill.
        for name, value in self.g['values'].items():
            for src, owner_on in self.owner_choices(value):
                if owner_on is None:
                    owner_on = self.model.new_constant(1)
                ready = self.jobs[value['producer']]['end'] if 'producer' in value else 0
                begin = self.jobs[value['producer']]['start'] if 'producer' in value else 0
                end_users = [self.gated_end(ready, owner_on, name + ':produced')]
                spill_on = self.boolean(f'spill:{name}:{src}')
                self.model.add(spill_on <= owner_on)
                spill_users = []
                if src != ext and not value.get('external_copy', False):
                    spill = self.move(name, src, ext, ready, spill_on)
                    external_ready = spill['end']
                    end_users.append(self.gated_end(spill['end'], spill_on, name + ':spill-ack'))
                else:
                    external_ready = ready if src == ext else 0
                    self.model.add(spill_on == 0)
                self.spills[name, src] = spill_on
                shared = defaultdict(list)
                for tid in self.consumers[name]:
                    task = self.tasks[tid]
                    consumer = self.jobs[tid]
                    for sid, bind in consumer['choices'].items():
                        dst = self.services[sid]['site']
                        pair = self.conjunction(owner_on, bind, name=f'pair:{name}:{src}:{tid}:{sid}')
                        direct = self.boolean(f'direct:{name}:{src}:{tid}:{sid}')
                        reload = self.boolean(f'reload:{name}:{src}:{tid}:{sid}')
                        self.model.add(direct + reload == pair)
                        if src == ext:
                            self.model.add(reload == 0)
                        if src == dst:
                            self.model.add(consumer['start'] >= ready).only_enforce_if(direct)
                            end_users.append(self.gated_end(consumer['end'], direct, name + ':local-use'))
                        else:
                            private = self.boolean(f'private:{name}:{src}:{tid}:{sid}')
                            common = self.boolean(f'shared:{name}:{src}:{tid}:{sid}')
                            self.model.add(private + common == direct)
                            copy = self.move(name, src, dst, ready, private)
                            self.model.add(consumer['start'] >= copy['end']).only_enforce_if(private)
                            end_users.append(self.gated_end(copy['end'], private, name + ':copy-ack'))
                            self.allocate(dst, f'{name}:direct:{tid}:{sid}:{src}', value['words'], copy['start'], consumer['end'], private, name, copy['copy_id'])
                            shared['direct', dst].append((common, consumer))
                        if src != ext:
                            private = self.boolean(f'private-reload:{name}:{src}:{tid}:{sid}')
                            common = self.boolean(f'shared-reload:{name}:{src}:{tid}:{sid}')
                            self.model.add(private + common == reload)
                            copy = self.move(name, ext, dst, external_ready, private)
                            self.model.add(consumer['start'] >= copy['end']).only_enforce_if(private)
                            self.allocate(dst, f'{name}:reload:{tid}:{sid}:{src}', value['words'], copy['start'], consumer['end'], private, name, copy['copy_id'])
                            shared['reload', dst].append((common, consumer))
                            if not value.get('external_copy', False):
                                self.model.add(reload <= spill_on)
                                spill_users.append(reload)
                for (kind, dst), members in shared.items():
                    on = self.boolean(f'shared-copy:{name}:{src}:{dst}:{kind}')
                    self.model.add_max_equality(on, [m[0] for m in members])
                    copy = self.move(name, src if kind == 'direct' else ext, dst,
                                     ready if kind == 'direct' else external_ready, on)
                    until = self.integer(f'shared-copy-end:{name}:{src}:{dst}:{kind}')
                    self.model.add_max_equality(until, [self.gated_end(c['end'], selected, name + ':shared-user')
                                                      for selected, c in members])
                    for selected, consumer in members:
                        self.model.add(consumer['start'] >= copy['end']).only_enforce_if(selected)
                    self.allocate(dst, f'{name}:shared:{src}:{dst}:{kind}', value['words'],
                                  copy['start'], until, on, name, copy['copy_id'])
                    if kind == 'direct':
                        end_users.append(self.gated_end(copy['end'], on, name + ':shared-ack'))
                if src != ext and not value.get('external_copy', False):
                    self.model.add(spill_on <= sum(spill_users))
                if name in self.g.get('outputs', []):
                    dst = value.get('output_site')
                    if dst is None:
                        raise ValueError('missing output_site: ' + name)
                    if dst != src:
                        if dst != ext:
                            raise Unsupported('final foreign-S output must have an explicit consumer task')
                        final_copy = self.move(name, src, dst, ready, owner_on, final=True)
                        end_users.append(self.gated_end(final_copy['end'], owner_on, name + ':final-ack'))
                    elif dst != ext:
                        end_users.append(self.gated_end(self.makespan, owner_on, name + ':final-local'))
                lease_end = self.integer(name + ':' + src + ':lease-end')
                self.model.add_max_equality(lease_end, end_users)
                origin = ('producer:' + value['producer']) if 'producer' in value else 'initial'
                self.allocate(src, name + ':source', value['words'], begin, lease_end, owner_on, name, origin)

    def _memory(self):
        for site, rows in self.allocations.items():
            times, addresses = [], []
            for index, row in enumerate(rows):
                duration = self.integer(f'memory:{site}:{index}:length')
                self.model.add(duration == row['end'] - row['start']).only_enforce_if(row['on'])
                times.append(self.model.new_optional_interval_var(row['start'], duration, row['end'], row['on'], f'memory:{site}:{index}:time'))
                addresses.append(self.model.new_optional_fixed_size_interval_var(row['address'], row['words'], row['on'], f'memory:{site}:{index}:address'))
            self.model.add_no_overlap_2d(times, addresses)

    def _resources(self):
        for resource, rows in self.claims.items():
            capacity = self.h['resources'][resource]
            if capacity == 1:
                self.model.add_no_overlap([r[0] for r in rows])
            else:
                self.model.add_cumulative([r[0] for r in rows], [r[1] for r in rows], capacity)

    def _nets(self, budget):
        self.net_on = {}
        for net, users in self.net_users.items():
            on = self.boolean('net:' + net)
            self.model.add_max_equality(on, users)
            self.net_on[net] = on
        self.wire_cost = sum(self.h['nets'][net]['cost'] * on for net, on in self.net_on.items()
                             if not self.h['nets'][net].get('fixed', False))
        if budget is not None:
            self.model.add(self.wire_cost <= budget)
        for left, right in self.h.get('incompatible_nets', []):
            if left in self.net_on and right in self.net_on:
                self.model.add(self.net_on[left] + self.net_on[right] <= 1)
        route_on = {}
        for rid, users in self.route_users.items():
            on = self.boolean('route:' + rid)
            self.model.add_max_equality(on, users)
            route_on[rid] = on
        for left, right in self.h.get('incompatible_routes', []):
            if left in route_on and right in route_on:
                self.model.add(route_on[left] + route_on[right] <= 1)

    def solve(self, seconds=30, workers=1):
        solver = self.cp.CpSolver()
        solver.parameters.max_time_in_seconds = seconds
        solver.parameters.num_search_workers = workers
        solver.parameters.random_seed = 219
        started = time.monotonic()
        status = solver.solve(self.model)
        primary_bound = solver.best_objective_bound
        primary_status = solver.status_name(status)
        # The secondary solve cannot sacrifice latency. If interrupted, retain
        # the already valid primary incumbent rather than returning UNKNOWN.
        secondary_status = None
        if status == self.cp.OPTIMAL:
            optimum = solver.value(self.makespan)
            self.model.add(self.makespan == optimum)
            wire_max = sum(n['cost'] for n in self.h['nets'].values() if not n.get('fixed'))
            self.model.minimize(self.traffic * (wire_max + 1) + self.wire_cost)
            extra = self.cp.CpSolver()
            extra.parameters.CopyFrom(solver.parameters)
            extra.parameters.max_time_in_seconds = max(0.01, seconds - (time.monotonic() - started))
            second = extra.solve(self.model)
            secondary_status = extra.status_name(second)
            if second in (self.cp.OPTIMAL, self.cp.FEASIBLE):
                solver = extra
        result = {'status': primary_status, 'secondary_status': secondary_status, 'seconds': time.monotonic() - started,
                  'best_bound': primary_bound,
                  'conflicts': solver.num_conflicts, 'branches': solver.num_branches}
        result['proof_scope'] = {'fixed_bindings': self.fixed, 'tied_bindings': self.tied,
                                 'bound_unit': 'ticks', 'graph': 'this lowered candidate only'}
        if status not in (self.cp.OPTIMAL, self.cp.FEASIBLE):
            return result
        value = solver.value
        result.update(makespan=value(self.makespan), wire_cost=value(self.wire_cost),
                      external_words=value(self.traffic), tasks={}, moves=[], allocations=[], claims=[],
                      nets=sorted(n for n, on in self.net_on.items() if value(on)))
        for tid, job in self.jobs.items():
            sid = next(s for s, on in job['choices'].items() if value(on))
            result['tasks'][tid] = {'service': sid, 'site': self.services[sid]['site'],
                                    'start': value(job['start']), 'end': value(job['end'])}
        for row in self.moves:
            if value(row['on']):
                result['moves'].append({k: v for k, v in row.items() if k not in {'on', 'start', 'end', 'phases'}} |
                    {'start': value(row['start']), 'end': value(row['end']),
                     'phases': [{**p, 'start': value(p['start']), 'end': value(p['end'])} for p in row['phases']]})
        for site, rows in self.allocations.items():
            for row in rows:
                if value(row['on']):
                    result['allocations'].append({**{k: v for k, v in row.items() if k not in {'on', 'start', 'end', 'address'}},
                        'site': site, 'start': value(row['start']), 'end': value(row['end']), 'address': value(row['address'])})
        for resource, rows in self.claims.items():
            for _, demand, start, end, on, name in rows:
                if value(on):
                    result['claims'].append({'resource': resource, 'demand': demand,
                                            'start': value(start), 'end': value(end), 'name': name})
        from seed import external_regions
        result['external_regions'] = external_regions(self.g, self.h, result)
        return result


def seed_bindings(graph, hardware):
    """Cheap placement proposal; CP, not this estimate, validates legality.

    Scores use declared durations and route reachability. Resource load and
    marginal nets guide the proposal only; no estimated time is emitted.
    """
    assignments, owners, load, nets = {}, {}, defaultdict(int), set()
    from contexts import membership
    member, contexts = membership(graph), {}
    common_contexts = {}
    by_id = {t['id']: t for t in graph['tasks']}
    for number, group in enumerate(graph.get('state_groups', [])):
        choices = [{s.get('state_resource') for sid, s in hardware['services'].items()
                    if sid in by_id[tid].get('alternatives', hardware['services']) and eligible(by_id[tid], s, graph['values'])}
                   for tid in group['tasks']]
        common_contexts[number] = set.intersection(*choices) - {None}
    pending = list(graph['tasks'])
    while pending:
        ready = [t for t in pending if all(graph['values'][n].get('producer') in assignments
                 or 'producer' not in graph['values'][n] for n in t['inputs'])
                 and set(t.get('after', [])).issubset(assignments)]
        if not ready:
            raise ValueError('graph contains a cycle')
        for task in ready:
            choices = []
            for sid in task.get('alternatives', hardware['services']):
                s = hardware['services'][sid]
                if not eligible(task, s, graph['values']):
                    continue
                group = member.get(task['id'])
                if group is not None and s.get('state_resource') not in common_contexts[group]:
                    continue
                if group in contexts and s.get('state_resource') != contexts[group]:
                    continue
                movement, extra, reachable = 0, set(s.get('nets', [])), True
                for n in set(task['inputs']):
                    v = graph['values'][n]
                    src = owners.get(n, v.get('site'))
                    if src == s['site']:
                        continue
                    routes = [r for r in hardware['routes'].values() if r.get('qualified')
                              and (r['src'], r['dst']) == (src, s['site'])
                              and r.get('min_words', 1) <= v['words'] <= r.get('max_words', 1)]
                    if not routes:
                        # A two-hop external spill may still be legal. Let CP
                        # decide it; do not declare hardware infeasible here.
                        reachable = False
                        continue
                    r = min(routes, key=lambda r: sum(p['ticks'] for p in r['phases']))
                    movement += sum(p['ticks'] for p in r['phases'])
                    extra.update(r.get('nets', []))
                resource_load = max((load[r] for r in s['resources']), default=0)
                new_wire = sum(hardware['nets'][n]['cost'] for n in extra - nets
                               if not hardware['nets'][n].get('fixed'))
                choices.append(((not reachable, resource_load + s['ticks'] + movement, new_wire, sid), sid, extra))
            if not choices:
                raise Unsupported('no seed service: ' + task['id'])
            _, sid, extra = min(choices)
            s = hardware['services'][sid]
            assignments[task['id']] = sid
            if task['id'] in member:
                contexts[member[task['id']]] = s.get('state_resource')
            for n in task['outputs']:
                owners[n] = s['site']
            for r in s['resources']:
                load[r] += s['ticks']
            nets.update(extra)
            pending.remove(task)
    return assignments


def optimize(graph, hardware, *, wire_budget=None, seconds=30, workers=1, initial=None, rounds=4):
    """Bottleneck-directed LNS; outside choices freeze, all times may propagate.

    No claim of full-model global optimality is made. Each local CP status and
    bound refers to its explicitly fixed bindings and the lowered candidate set.
    """
    began = time.monotonic()
    from verify import verify
    if initial:
        best = initial
    else:
        bindings = seed_bindings(graph, hardware)
        from seed import serial_seed, SeedFailure
        try:
            best = serial_seed(graph, hardware, bindings, wire_budget)
        except SeedFailure as exc:
            best = Planner(graph, hardware, wire_budget, fixed=bindings).solve(seconds, workers)
            best['seed_failure'] = str(exc)
        if 'tasks' not in best:
            # The cheap seed can miss a feasible binding. This fallback is a
            # bounded constraint solve, not a proof about arbitrary mappings.
            fallback = Planner(graph, hardware, wire_budget, hint=None).solve(seconds, workers)
            fallback['seed_status'] = best['status']
            best = fallback
    if 'tasks' not in best:
        return best
    verify(graph, hardware, best, wire_budget)
    history, constructive = [], []
    # Fast constructive moves give CP a useful incumbent without asking it to
    # rediscover independent-stream overlap through a large address model.
    from parallel import parallel_seed
    from seed import SeedFailure
    for bindings in [{tid: row['service'] for tid, row in best['tasks'].items()}, seed_bindings(graph, hardware)]:
        try:
            candidate = parallel_seed(graph, hardware, bindings, wire_budget)
            accepted = (candidate['makespan'], candidate['external_words'], candidate['wire_cost']) < (best['makespan'], best['external_words'], best['wire_cost'])
            constructive.append({'kind': 'construct-independent-streams', 'status': 'VERIFIED', 'accepted': accepted,
                            'before_ticks': best['makespan'], 'after_ticks': candidate['makespan']})
            if accepted:
                best = candidate
        except SeedFailure as exc:
            constructive.append({'kind': 'construct-independent-streams', 'status': 'NOT_APPLICABLE',
                            'accepted': False, 'reason': str(exc)})
    tasks = {t['id']: t for t in graph['tasks']}
    neighborhoods = []
    # A static route cannot disappear until every nonadjacent user moves.
    for net in sorted(best['nets'], key=lambda n: hardware['nets'][n]['cost'], reverse=True):
        if hardware['nets'][net].get('fixed'):
            continue
        values = {m['value'] for m in best['moves'] if net in hardware['routes'][m['route']].get('nets', [])}
        involved = {t['id'] for t in graph['tasks'] if values.intersection(t['inputs'] + t['outputs'])}
        involved.update(tid for tid, row in best['tasks'].items()
                        if net in hardware['services'][row['service']].get('nets', []))
        neighborhoods.append(('shared-net:' + net, involved))
    # Include both ends of long-lived buffers rather than their producer alone.
    for row in sorted(best['allocations'], key=lambda a: (a['end'] - a['start']) * a['words'], reverse=True):
        name = row['value']
        involved = {t['id'] for t in graph['tasks'] if name in t['inputs'] + t['outputs']}
        if involved:
            neighborhoods.append(('memory:' + name, involved))
    # Also open the jobs immediately competing for a constrained engine/LC.
    # Input copies/ACKs remain in the constraint solve and may move in time.
    resource_jobs = defaultdict(list)
    for tid, row in best['tasks'].items():
        for resource in hardware['services'][row['service']]['resources']:
            resource_jobs[resource].append(tid)
    queues = []
    for resource, tids in resource_jobs.items():
        tids.sort(key=lambda t: best['tasks'][t]['start'])
        for left, right in zip(tids, tids[1:]):
            work = best['tasks'][left]['end'] - best['tasks'][left]['start']
            involved = {left, right}
            involved.update(graph['values'][n]['producer'] for n in tasks[right]['inputs']
                            if 'producer' in graph['values'][n])
            queues.append((work, 'resource:' + resource + ':' + right, involved))
    neighborhoods += [(label, involved) for _, label, involved in sorted(queues, reverse=True)]
    # Deduplicate identical task families; alternate static connectivity and
    # lifetime pressure, rather than exhausting trivial routes first.
    unique = {}
    buckets = [[row for row in neighborhoods if row[0].startswith(prefix)]
               for prefix in ('shared-net:', 'memory:', 'resource:')]
    from itertools import zip_longest
    mixed = [row for group in zip_longest(*buckets) for row in group if row is not None]
    for label, selected in mixed:
        if selected:
            unique.setdefault(frozenset(selected), (label, selected))
    families = list(unique.values())
    for label, selected in families[:rounds]:
        selected = set(selected)
        for group in graph.get('state_groups', []):
            if selected.intersection(group['tasks']):
                selected.update(group['tasks'])
        fixed = {tid: row['service'] for tid, row in best['tasks'].items() if tid not in selected}
        tied = []
        if len(selected) > 64:
            # Keep all nonadjacent users of the static net in the move, while
            # coupling repeated bindings into template decisions. This is a
            # restricted LNS neighborhood, never a global optimality proof.
            patterns = defaultdict(list)
            for tid in sorted(selected):
                t = tasks[tid]
                alts = tuple(sorted(s for s, service in hardware['services'].items()
                                    if s in t.get('alternatives', hardware['services']) and eligible(t, service, graph['values'])))
                signature = (best['tasks'][tid]['service'], alts)
                patterns[signature].append(tid)
            tied = [members for members in patterns.values() if len(members) > 1]
        trial = Planner(graph, hardware, wire_budget, fixed=fixed, hint=best, tied=tied).solve(seconds, workers)
        accepted = False
        if 'tasks' in trial:
            verify(graph, hardware, trial, wire_budget)
            if (trial['makespan'], trial['external_words'], trial['wire_cost']) < (best['makespan'], best['external_words'], best['wire_cost']):
                best, accepted = trial, True
        history.append({'kind': label, 'open_tasks': sorted(selected), 'fixed_tasks': len(fixed),
                        'status': trial['status'], 'accepted': accepted, 'bound': trial['best_bound'],
                        'coupled_binding_families': tied})
    best = deepcopy(best)
    best['optimization_history'] = history
    best['constructive_history'] = constructive
    best['total_seconds'] = time.monotonic() - began
    best['optimality_scope'] = 'lowered choices; neighborhood bounds are conditional, not global'
    return best
