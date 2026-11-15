"""Finite macro contexts that survive several separately scheduled commands.

These are generated compiler constraints, not new user-authored hardware.
An M result or an R dot/update context must not migrate or be overwritten
while memory traffic between its commands is pending.
"""


def membership(graph):
    result = {}
    ids = {t['id'] for t in graph['tasks']}
    for index, group in enumerate(graph.get('state_groups', [])):
        tasks = group['tasks']
        if not tasks or len(set(tasks)) != len(tasks) or any(t not in ids or t in result for t in tasks):
            raise ValueError('invalid or overlapping macro context group')
        for tid in tasks:
            result[tid] = index
    return result


def serial_order(graph):
    """Topological order with each stateful program kept together in a seed.

    The general solver may overlap independent programs. The cheap seed
    deliberately keeps a context program contiguous to avoid clobbering it.
    """
    member = membership(graph)
    tasks = {t['id']: t for t in graph['tasks']}
    groups = {}
    for tid in tasks:
        key = ('state', member[tid]) if tid in member else ('task', tid)
        groups.setdefault(key, []).append(tid)
    owner = {tid: key for key, tids in groups.items() for tid in tids}
    dependencies = {tid: set(t.get('after', [])) | {graph['values'][n]['producer']
                    for n in t['inputs'] if 'producer' in graph['values'][n]}
                    for tid, t in tasks.items()}
    order, done, pending = [], set(), list(groups)
    while pending:
        ready = [key for key in pending if all(p in done or owner[p] == key
                 for tid in groups[key] for p in dependencies[tid])]
        if not ready:
            raise ValueError('context programs need interleaving; use the general planner')
        key = ready[0]
        local = list(groups[key])
        while local:
            candidates = [tid for tid in local if dependencies[tid] <= done]
            if not candidates:
                raise ValueError('cycle inside macro context')
            tid = candidates[0]
            order.append(tid)
            done.add(tid)
            local.remove(tid)
        pending.remove(key)
    return order


def claims(graph, hardware, planned):
    """Return context reservations for a constructive plan."""
    member = membership(graph)
    result = []
    for group in graph.get('state_groups', []):
        rows = [planned[tid] for tid in group['tasks']]
        resources = {hardware['services'][r['service']].get('state_resource') for r in rows}
        if len(resources) != 1 or None in resources:
            raise ValueError('macro context migrated or lacks a state resource')
        result.append({'resource': resources.pop(), 'start': min(r['start'] for r in rows),
                       'end': max(r['end'] for r in rows), 'demand': 1})
    for tid, row in planned.items():
        resource = hardware['services'][row['service']].get('state_resource')
        if resource and tid not in member:
            result.append({'resource': resource, 'start': row['start'], 'end': row['end'], 'demand': 1})
    return result
