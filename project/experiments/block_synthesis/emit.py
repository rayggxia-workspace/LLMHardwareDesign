"""Emit event-level service requests and exact static-net demands.

These are compiler IR artifacts, not asserted executable MC/LC binaries.
Each native ABI needs an encoder and program replay before deployment.
"""
from collections import defaultdict


def emit(graph, hardware, plan):
    ext = hardware['external']
    allocations = defaultdict(list)
    for a in plan['allocations']:
        if a['value'] is not None:
            allocations[a['site'], a['value']].append(a)
    external = {r['value']: r for r in plan['external_regions']}
    copies = {m['copy_id']: m for m in plan['moves']}

    def operand(name, site, start, end, *, target=False, origin=None):
        if site == ext:
            r = external[name]
            result = {'value': name, 'site': site, 'address_words': r['address_words'], 'words': r['words']}
            if not target:
                v = graph['values'][name]
                stores = [m for m in plan['moves'] if m['value'] == name and m['dst'] == ext and m['end'] <= start]
                result['available_event'] = ('initial:' + name if v.get('site') == ext or v.get('external_copy')
                                             else 'ack:' + min(stores, key=lambda m: m['end'])['copy_id'])
            return result
        rows = [a for a in allocations[site, name] if a['start'] <= start and a['end'] >= end]
        if origin is not None:
            rows = [a for a in rows if a['origin'] == origin]
        # A value can have a second allocation reserved before its copy
        # commits. Select an actually initialized materialization.
        def ready(a):
            o = a['origin']
            if o == 'initial':
                return True
            if o.startswith('producer:'):
                return plan['tasks'][o[len('producer:'):]]['end'] <= start
            return o in copies and copies[o]['end'] <= start
        a = next((a for a in rows if ready(a)), rows[0])
        o = a['origin']
        event = ('done:' + o[len('producer:'):]) if o.startswith('producer:') else ('initial:' + name if o == 'initial' else 'ack:' + o)
        result = {'value': name, 'site': site, 'address_words': a['address'], 'words': a['words']}
        if not target:
            result['available_event'] = event
        return result

    requests = []
    for task in graph['tasks']:
        row = plan['tasks'][task['id']]
        inputs = [operand(n, row['site'], row['start'], row['end']) for n in task['inputs']]
        outputs = [operand(n, row['site'], row['start'], row['end'], target=True, origin='producer:' + task['id']) for n in task['outputs']]
        requests.append({'id': task['id'], 'kind': 'service', 'service': row['service'],
            'owner': hardware['services'][row['service']].get('controller'),
            'wait_for': sorted({v['available_event'] for v in inputs if 'available_event' in v} |
                               {'done:' + p for p in task.get('after', [])}),
            'inputs': inputs, 'outputs': outputs, 'complete_event': 'done:' + task['id'],
            'planned_interval': [row['start'], row['end']]})
    for m in plan['moves']:
        source = operand(m['value'], m['src'], m['start'], m['end'])
        requests.append({'id': m['copy_id'], 'kind': 'copy', 'route': m['route'],
            'source': source, 'destination': operand(m['value'], m['dst'], m['start'], m['end'], target=True, origin=m['copy_id']),
            'wait_for': [source['available_event']] if 'available_event' in source else [],
            'complete_event': 'ack:' + m['copy_id'], 'source_lease_through': 'ack:' + m['copy_id'],
            'planned_interval': [m['start'], m['end']]})
    demands = [{'id': n, **hardware['nets'][n]} for n in plan['nets']]
    return {'program_ir': {'requests': requests, 'status': 'requires native ABI and event/resource ordering lowering'},
            'wiring': {'nets': demands, 'selected_routes': sorted({m['route'] for m in plan['moves']}),
                       'all_pins_bound': all('driver' in n and 'sinks' in n for n in demands),
                       'physical_signoff': False}}
