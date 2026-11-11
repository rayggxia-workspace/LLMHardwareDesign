"""Consume measurements bound to an earlier route and propose a new upper overlay."""
import math

from check import digest
from geometry import need
from repeaters import check_allocations
from resource_search import route_resources


def repair(spec, data, previous, feedback, **options):
    check_allocations(spec, data, previous)
    need(not previous['failed'], 'measurements require a complete route')
    need(feedback.get('schema_version') == 'upper-route-feedback/1'
         and feedback.get('route_sha256') == digest(previous['physical_routes']),
         'stale measured route feedback')
    need(isinstance(feedback.get('evidence'), str) and bool(feedback['evidence']),
         'measured feedback requires an evidence reference')
    logical = sorted(n['id'] for n in spec['nets'])
    stages = {n['id'] for n in previous['physical_spec']['nets'] if n['sinks']}
    targets = set()
    bounds = {'capacitance': 'max', 'slew': 'max', 'fanout': 'max', 'setup': 'min', 'hold': 'min'}
    for entry in feedback['violations']:
        stage = entry['segment']
        metric, actual, limit = entry['metric'], entry['measured'], entry['limit']
        need(metric in bounds and stage in stages, 'unknown measured stage or metric')
        need(all(type(v) in (float, int) and math.isfinite(v) for v in (actual, limit)),
             'invalid measured value')
        need(actual > limit if bounds[metric] == 'max' else actual < limit, 'feedback is not a violation')
        for segment in [stage, *entry.get('related_segments', [])]:
            need(segment in stages, 'unknown affected stage')
            targets.add(logical[int(segment.split('/')[1])])
    need(targets, 'no measured violations to repair')
    candidate = route_resources(spec, data, previous=previous, targets=targets, **options)
    changed = (not candidate['failed']
               and candidate['physical_routes']['routes'] != previous['physical_routes']['routes'])
    if not changed:
        candidate = dict(previous)
    candidate['repair'] = {'feedback_sha256': digest(feedback), 'target_nets': sorted(targets),
                           'status': 'requires_new_extraction' if changed else 'no_alternative_found'}
    return candidate
