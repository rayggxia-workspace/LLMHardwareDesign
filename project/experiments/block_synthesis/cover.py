"""Bounded chain-cover DP over explicitly qualified service patterns.

The DP proposes covers. Joint timing/storage/wire legality is decided by the
planner, not by adding the DP scores. Beam pruning forfeits global optimality.
"""
from collections import defaultdict
from copy import deepcopy

from solver import eligible, Unsupported


def chains(graph):
    tasks = {t['id']: t for t in graph['tasks']}
    users = defaultdict(set)
    for t in tasks.values():
        for n in t['inputs']:
            users[n].add(t['id'])
    successor, predecessor = {}, {}
    for t in tasks.values():
        if len(t['outputs']) != 1:
            continue
        n = t['outputs'][0]
        if n in graph.get('outputs', []) or len(users[n]) != 1:
            continue
        nxt = next(iter(users[n]))
        # A join is a boundary: do not hide storage/consumer dependencies.
        parents = {graph['values'][v].get('producer') for v in tasks[nxt]['inputs']
                   if graph['values'][v].get('producer')}
        if parents == {t['id']}:
            successor[t['id']], predecessor[nxt] = nxt, t['id']
    result = []
    seen = set()
    for t in tasks.values():
        if t['id'] in predecessor:
            continue
        row, tid = [], t['id']
        while tid not in seen:
            seen.add(tid)
            row.append(tasks[tid])
            if tid not in successor:
                break
            tid = successor[tid]
        result.append(row)
    if len(seen) != len(tasks):
        raise ValueError('cycle in model graph')
    return result


def _matches(segment, service):
    return (service.get('qualified') and service.get('pattern') == [t['op'] for t in segment]
            and service.get('pattern_domains', [''] * len(segment)) == [t.get('domain', '') for t in segment]
            and service.get('pattern_numeric') == [t['numeric'] for t in segment]
            and service.get('pattern_attributes') == [t.get('attributes', {}) for t in segment])


def propose_covers(graph, hardware, limit=8):
    if limit < 1:
        raise ValueError('cover limit must be positive')
    choices = [(0, [])]
    context_members = {tid for g in graph.get('state_groups', []) for tid in g['tasks']}
    for chain in chains(graph):
        dp = [[] for _ in range(len(chain) + 1)]
        dp[0] = [(0, [])]
        for end in range(1, len(chain) + 1):
            candidates = []
            one = chain[end-1]
            services = [s for s in hardware['services'].values() if eligible(one, s, graph['values'])]
            if services:
                duration = min(s['ticks'] for s in services)
                candidates += [(score + duration, rows + [(one, [one['id']])]) for score, rows in dp[end-1]]
            for start in range(end-1):
                segment = chain[start:end]
                if any(t['id'] in context_members for t in segment):
                    continue  # Do not erase a persistent-state boundary.
                internal = {n for t in segment[:-1] for n in t['outputs']}
                if any(n in graph.get('outputs', []) for n in internal):
                    continue
                groups = defaultdict(list)
                for sid, service in hardware['services'].items():
                    if not _matches(segment, service):
                        continue
                    bindings = service.get('pattern_inputs')
                    if bindings is None:
                        continue
                    ins = [segment[i]['inputs'][j] for i, j in bindings]
                    if any(n in internal for n in ins):
                        raise ValueError('fusion input binding refers to a hidden internal value')
                    # Include every externally required operand. Omitting one
                    # is a semantic change, not a legal fusion.
                    external = {v for t in segment for v in t['inputs']} - internal
                    if set(ins) != external:
                        raise ValueError('fusion does not cover all external operands')
                    fused = {'id': 'cover:' + segment[0]['id'] + ':' + segment[-1]['id'],
                             'domain': service.get('domain', ''),
                             'op': service['op'], 'numeric': service['numeric'], 'inputs': ins,
                             'outputs': segment[-1]['outputs'], 'attributes': service.get('attributes', {})}
                    if not eligible(fused, service, graph['values']):
                        continue
                    key = (fused['op'], fused['numeric'], tuple(ins))
                    groups[key].append((sid, service, fused))
                for members in groups.values():
                    fused = deepcopy(members[0][2])
                    fused['alternatives'] = [m[0] for m in members]
                    duration = min(m[1]['ticks'] for m in members)
                    candidates += [(score + duration, rows + [(fused, [t['id'] for t in segment])])
                                   for score, rows in dp[start]]
            dp[end] = sorted(candidates, key=lambda c: (c[0], repr(c[1])))[:limit]
        if not dp[-1]:
            raise Unsupported('no qualified cover for chain starting ' + chain[0]['id'])
        choices = sorted([(a+b, x+y) for a, x in choices for b, y in dp[-1]],
                         key=lambda c: (c[0], repr(c[1])))[:limit]
    results = []
    original = {t['id']: t for t in graph['tasks']}
    for priority, groups in choices:
        task_owner = {tid: t['id'] for t, members in groups for tid in members}
        result = deepcopy(graph)
        result['tasks'] = []
        for task, members in groups:
            t = deepcopy(task)
            after = {task_owner[a] for tid in members for a in original[tid].get('after', [])}
            t['after'] = sorted(after - {t['id']})
            result['tasks'].append(t)
        kept = {v for t in result['tasks'] for v in t['inputs'] + t['outputs']} | set(result.get('outputs', []))
        result['values'] = {n: v for n, v in result['values'].items() if n in kept}
        for v in result['values'].values():
            if 'producer' in v:
                v['producer'] = task_owner[v['producer']]
        result['cover_trace'] = {'priority': priority, 'limit': limit,
            'groups': {t['id']: members for t, members in groups},
            'scope': 'bounded cover proposals, not globally optimal schedule DP'}
        results.append(result)
    return results
