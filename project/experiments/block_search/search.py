"""Bounded frontier mapping with interval resource and tensor-lifetime checks.

This is an analytical scheduling prototype. It emits no executable LC image.
Topological decision order is fixed; execution intervals may overlap. Beam
pruning and greedy earliest-slot scheduling do not preserve optimality.
"""
import argparse
import copy
from dataclasses import dataclass, field
import hashlib
import heapq
import itertools
import json
import math
from pathlib import Path
import time

INF = 10**30


class Unsupported(ValueError):
    pass


def load(path):
    path = Path(path)
    if path.suffix in ('.yaml', '.yml'):
        import yaml
        return yaml.safe_load(path.read_text())
    return json.loads(path.read_text())


def import_onnx(path, weight_names=()):
    import onnx
    from onnx import numpy_helper
    model = onnx.shape_inference.infer_shapes(onnx.load(str(path), load_external_data=False))
    sizes, shapes, dtypes = {}, {}, {}
    constants = set(weight_names) | {v.name for v in model.graph.initializer}
    for v in itertools.chain(model.graph.input, model.graph.output, model.graph.value_info):
        shape = [d.dim_value if d.HasField('dim_value') else None
                 for d in v.type.tensor_type.shape.dim]
        shapes[v.name] = shape
        dtype = v.type.tensor_type.elem_type
        dtypes[v.name] = onnx.TensorProto.DataType.Name(dtype)
        if all(d is not None and d >= 0 for d in shape):
            sizes[v.name] = math.prod(shape) * __import__('numpy').dtype(
                onnx.helper.tensor_dtype_to_np_dtype(dtype)).itemsize
    for v in model.graph.initializer:
        shapes[v.name] = list(v.dims)
        dtypes[v.name] = onnx.TensorProto.DataType.Name(v.data_type)
        sizes[v.name] = math.prod(v.dims) * __import__('numpy').dtype(
            onnx.helper.tensor_dtype_to_np_dtype(v.data_type)).itemsize
    tasks, producer = [], {}
    for i, n in enumerate(model.graph.node):
        # Only Constant itself is unconditionally compile-time. Shape/Cast etc
        # require registered services unless an upstream optimizer folded them.
        if n.op_type == 'Constant':
            constants.update(n.output)
            for attr in n.attribute:
                if attr.name == 'value':
                    shapes[n.output[0]] = list(attr.t.dims)
                    sizes[n.output[0]] = math.prod(attr.t.dims) * __import__('numpy').dtype(
                        onnx.helper.tensor_dtype_to_np_dtype(attr.t.data_type)).itemsize
            continue
        outputs = [v for v in n.output if v]
        missing = [v for v in outputs if v not in sizes]
        if missing:
            raise Unsupported(f'Unresolved output shape: node {i} {n.op_type}: {missing}')
        inputs = [v for v in n.input if v]
        work = max([sizes[v] // 4 for v in outputs] + [1])
        if n.op_type in ('MatMul', 'Gemm') and inputs and inputs[0] in shapes:
            k = shapes[inputs[0]][-1]
            if k:
                work *= 2 * k
        task = {'id': f'n{i}', 'op': n.op_type, 'inputs': inputs,
                'outputs': outputs, 'work': work,
                'dependencies': sorted({producer[v] for v in inputs if v in producer}),
                'dtype': dtypes.get(outputs[0], 'UNKNOWN')}
        tasks.append(task)
        producer.update({v: task['id'] for v in outputs})
    used = {v for t in tasks for v in t['inputs']}
    # Zero-sized auxiliary objects may carry metadata. Unknown activations
    # must not silently become zero-byte transfers.
    missing = used - sizes.keys() - constants
    if missing:
        raise Unsupported('Unresolved input sizes: ' + repr(sorted(missing)[:12]))
    return {'tasks': tasks, 'sizes': sizes, 'weights': sorted(constants),
            'inputs': [v.name for v in model.graph.input if v.name not in constants],
            'outputs': [v.name for v in model.graph.output],
            'source': str(path), 'source_sha256': hashlib.sha256(Path(path).read_bytes()).hexdigest()}


def earliest(cal, resources, after, duration):
    t = after
    while True:
        conflicts = [end for r in resources for start, end in cal.get(r, ())
                     if start < t + duration and t < end]
        if not conflicts:
            return t
        t = max(conflicts)


def reserve(cal, resources, start, end):
    for r in resources:
        cal.setdefault(r, []).append((start, end))


def memory_ok(allocs, capacity):
    events = []
    for a in allocs.values():
        if a['end'] > a['start']:
            events.extend(((a['start'], a['bytes']), (a['end'], -a['bytes'])))
    count = peak = 0
    for _, delta in sorted(events):
        count += delta
        peak = max(peak, count)
    return peak <= capacity, peak


@dataclass
class State:
    cal: dict = field(default_factory=dict)
    allocations: dict = field(default_factory=dict)
    objects: dict = field(default_factory=dict)
    wires: frozenset = frozenset()
    schedule: list = field(default_factory=list)
    finish: int = 0
    wire_cost: float = 0


def paths(arch, src, dst):
    if src == dst:
        return [[]]
    result, counter = [], itertools.count()
    queue = [(0, next(counter), src, frozenset([src]), [])]
    while queue and len(result) < arch.get('route_candidates', 2):
        cost, _, here, seen, route = heapq.heappop(queue)
        if here == dst:
            result.append(route)
            continue
        for edge in arch['links']:
            if edge.get('enabled', True) and edge['src'] == here and edge['dst'] not in seen:
                heapq.heappush(queue, (cost + edge['latency_cycles'], next(counter),
                                      edge['dst'], seen | {edge['dst']}, route + [edge]))
    return result


def extend(state, task, impl, graph, arch, remaining):
    """Generate route alternatives; actual bus IDs determine static reuse."""
    owner = impl['instance']
    produced = state.objects
    transfers = []
    for tensor in dict.fromkeys(task['inputs']):
        if tensor in graph['weights']:
            source, valid = arch['external_memory'], 0
        elif tensor in produced:
            source, valid = produced[tensor]['owner'], produced[tensor]['ready']
        else:
            source, valid = arch['external_memory'], 0
        alternatives = paths(arch, source, owner)
        if not alternatives:
            return []
        transfers.append((tensor, source, valid, alternatives))
    # Bound combinations explicitly. This cap is part of the heuristic,
    # not a proof that remaining route combinations cannot be useful.
    combinations = itertools.islice(itertools.product(*(t[3] for t in transfers)),
                                    arch.get('route_combinations', 4))
    result = []
    for combination in combinations:
        s = copy.deepcopy(state)
        cal = s.cal
        before = 0
        copies = []
        for (tensor, source, valid, _), route in zip(transfers, combination):
            size = graph['sizes'].get(tensor, 0)
            if not route:
                before = max(before, valid)
                continue
            duration = sum(e['latency_cycles'] + math.ceil(size / e['bytes_per_cycle'])
                           for e in route)
            resources = sorted({r for e in route for r in e['resources']})
            start = earliest(cal, resources, valid, duration)
            end = start + duration
            reserve(cal, resources, start, end)
            before = max(before, end)
            copies.append({'tensor': tensor, 'start': start, 'end': end,
                           'bytes': size, 'src': source, 'dst': owner,
                           'resources': resources, 'links': [e['id'] for e in route]})
            for edge in route:
                if not edge.get('fixed', False) and edge['id'] not in s.wires:
                    s.wire_cost += edge['static_cost']
                    s.wires |= {edge['id']}
        duration = impl.get('setup_cycles', 0) + math.ceil(task['work']/impl['work_per_cycle'])
        duration = max(1, duration)
        resources = impl['resources']
        start = earliest(cal, resources, before, duration)
        end = start + duration
        reserve(cal, resources, start, end)
        # Source remains leased through transfer completion or local compute.
        for tensor in set(task['inputs']):
            if tensor in s.objects:
                obj = s.objects[tensor]
                release = end if obj['owner'] == owner else max(
                    c['end'] for c in copies if c['tensor'] == tensor)
                obj['last_use'] = max(obj['last_use'], release)
                if remaining[tensor] == 0:
                    s.allocations[obj['owner']][tensor]['end'] = obj['last_use']
        scratch = impl.get('workspace_bytes', 0)
        # Nonlocal activations must fit at the consumer until completion.
        incoming = sum(graph['sizes'][v] for v in set(task['inputs'])
                       if v not in graph['weights'] and
                       (v not in s.objects or s.objects[v]['owner'] != owner))
        scratch += incoming + min(impl.get('weight_window_bytes', 0),
                                 sum(graph['sizes'].get(v, 0) for v in task['inputs']
                                     if v in graph['weights']))
        # Conservative: reserve incoming working buffers from earliest copy.
        s.allocations.setdefault(owner, {})['scratch:'+task['id']] = {
            'bytes': scratch, 'start': min([c['start'] for c in copies] + [start]), 'end': end}
        for tensor in task['outputs']:
            s.allocations[owner][tensor] = {'bytes': graph['sizes'][tensor],
                                          'start': start, 'end': INF}
            s.objects[tensor] = {'owner': owner, 'ready': end, 'last_use': end}
            if remaining.get(tensor, 0) == 0 and tensor not in graph['outputs']:
                s.allocations[owner][tensor]['end'] = end
        legal = all(memory_ok(a, arch['instances'][inst]['capacity_bytes'])[0]
                    for inst, a in s.allocations.items())
        if not legal:
            continue
        s.schedule.append({'task': task['id'], 'op': task['op'], 'instance': owner,
                           'service': impl['id'], 'start': start, 'end': end,
                           'resources': resources, 'transfers': copies})
        s.finish = max(s.finish, end)
        # Only live objects survive in the search frontier. Allocation history
        # remains for independent temporal-capacity verification.
        s.objects = {k: v for k,v in s.objects.items()
                     if remaining.get(k, 0) or k in graph['outputs']}
        result.append(s)
    return result


def fingerprint(s):
    # Full calendars/lifetimes matter. A smaller key would be unsafe merging.
    return json.dumps([s.cal, s.allocations, s.objects, sorted(s.wires)], sort_keys=True)


def compile_graph(graph, arch, width=16, penalty=1., allow_estimates=False, greedy_guard=True):
    started = time.perf_counter()
    if not allow_estimates and not arch.get('qualified_numeric', False):
        raise Unsupported('Hardware numeric services are analytical/unqualified; use explicit --allow-estimates')
    ids = [t['id'] for t in graph['tasks']]
    if len(set(ids)) != len(ids):
        raise Unsupported('Duplicate task IDs')
    seen = set()
    for task in graph['tasks']:
        if not set(task.get('dependencies', ())).issubset(seen):
            raise Unsupported('Tasks must be topologically ordered')
        seen.add(task['id'])
    remaining = {}
    for t in graph['tasks']:
        for v in set(t['inputs']):
            remaining[v] = remaining.get(v, 0)+1
    states = [State()]
    guard = states[0]
    stats = {'expanded': 0, 'merged': 0, 'pruned': 0}
    for k, task in enumerate(graph['tasks']):
        for v in set(task['inputs']):
            remaining[v] -= 1
        candidates = [s for s in arch['services'] if task['op'] in s['ops'] and
                      task.get('dtype', 'FLOAT') in s.get('dtypes', ['FLOAT'])]
        if not candidates:
            raise Unsupported(f'No registered service: {task["id"]} {task["op"]} {task.get("dtype")}')
        next_states, guard_children = {}, []
        for state in states:
            for impl in candidates:
                for child in extend(state, task, impl, graph, arch, remaining):
                    stats['expanded'] += 1
                    key = fingerprint(child)
                    if key in next_states:
                        stats['merged'] += 1
                    else:
                        next_states[key] = child
                    if state is guard:
                        guard_children.append(next_states[key])
        if not next_states:
            return {'status': 'search_exhausted', 'at': task['id'], 'index': k,
                    'reason': 'No feasible extension among retained candidates; not a global infeasibility proof',
                    'statistics': stats, 'seconds': time.perf_counter()-started}
        ordered = sorted(next_states.values(), key=lambda s: s.finish+penalty*s.wire_cost)
        # Diversity by installed connection union; still an approximation.
        selected, groups = [], set()
        for s in ordered:
            if s.wires not in groups:
                selected.append(s)
                groups.add(s.wires)
                if len(selected) >= max(1, width//2):
                    break
        chosen = {id(s) for s in selected}
        selected += [s for s in ordered if id(s) not in chosen][:width-len(selected)]
        if greedy_guard and guard_children:
            guard = min(guard_children,key=lambda s:s.finish+penalty*s.wire_cost)
            if all(s is not guard for s in selected):
                selected[-1] = guard
        stats['pruned'] += len(ordered)-len(selected)
        states = selected
    best = min(states, key=lambda s: s.finish+penalty*s.wire_cost)
    plan = {'status': 'analytical_plan', 'executable': False,
            'latency_cycles': best.finish, 'static_cost': best.wire_cost,
            'objective': best.finish+penalty*best.wire_cost,
            'static_links': sorted(best.wires), 'schedule': best.schedule,
            'memory': best.allocations, 'statistics': stats,
            'seconds': time.perf_counter()-started, 'beam_width': width,
            'greedy_guard': greedy_guard,
            'source_sha256': graph.get('source_sha256'),
            'qualification': arch.get('evidence', 'unspecified'),
            'limitations': ['fixed topological decision order; earliest-slot scheduling',
                            'no automatic tensor tiling or spill; capacity violations rejected',
                            'registered single-node services; no compound pattern covering yet',
                            'analytical route/compute costs; no RTL/STA or instruction generation']}
    verify(plan, graph, arch)
    return plan


def verify(plan, graph, arch):
    """Replay legality independent of beam ranking and transition ordering."""
    tasks = {t['id']:t for t in graph['tasks']}
    calls = {c['task']:c for c in plan['schedule']}
    assert set(calls) == set(tasks), 'Incomplete coverage'
    by_resource = {}
    for call in calls.values():
        for operation in call['transfers'] + [call]:
            assert operation['start'] >= 0 and operation['end'] > operation['start']
            for resource in operation['resources']:
                by_resource.setdefault(resource, []).append((operation['start'],operation['end']))
        for dep in tasks[call['task']].get('dependencies', ()):
            assert calls[dep]['end'] <= call['start'], 'Dependency violation'
        for transfer in call['transfers']:
            assert transfer['end'] <= call['start'], 'Input arrival violation'
    for intervals in by_resource.values():
        intervals.sort()
        assert all(a[1] <= b[0] for a,b in zip(intervals,intervals[1:])), 'Resource overlap'
    for inst, allocs in plan['memory'].items():
        assert memory_ok(allocs,arch['instances'][inst]['capacity_bytes'])[0], 'Capacity violation'
    produced = {v:calls[t['id']] for t in graph['tasks'] for v in t['outputs']}
    for call in calls.values():
        for tensor in set(tasks[call['task']]['inputs']):
            if tensor not in produced:
                continue
            producer = produced[tensor]
            alloc = plan['memory'][producer['instance']][tensor]
            matching = [t for t in call['transfers'] if t['tensor']==tensor]
            if matching:
                assert all(t['start']>=producer['end'] for t in matching), 'Early source read'
                release = max(t['end'] for t in matching)
            else:
                assert producer['instance']==call['instance'], 'Missing transfer'
                release = call['end']
            assert alloc['end'] >= release, 'Source released before consumption/ACK'
    actual = {e for c in calls.values() for t in c['transfers'] for e in t['links']}
    fixed = {e['id'] for e in arch['links'] if e.get('fixed', False)}
    assert actual-fixed == set(plan['static_links']), 'Static connection mismatch'
    plan['replay_checks'] = 'coverage/dependencies/arrival/resource-exclusion/capacity/static-union passed'


def main():
    p = argparse.ArgumentParser()
    p.add_argument('model')
    p.add_argument('hardware')
    p.add_argument('output')
    p.add_argument('--beam', type=int, default=16)
    p.add_argument('--penalty', type=float, default=1.)
    p.add_argument('--allow-estimates', action='store_true')
    p.add_argument('--no-greedy-guard', action='store_true')
    a = p.parse_args()
    if a.beam < 1 or a.penalty < 0:
        p.error('beam must be positive and penalty nonnegative')
    graph = import_onnx(a.model) if a.model.endswith('.onnx') else load(a.model)
    result = compile_graph(graph, load(a.hardware), a.beam, a.penalty, a.allow_estimates,
                           not a.no_greedy_guard)
    Path(a.output).write_text(json.dumps(result,indent=2))


if __name__ == '__main__':
    main()
