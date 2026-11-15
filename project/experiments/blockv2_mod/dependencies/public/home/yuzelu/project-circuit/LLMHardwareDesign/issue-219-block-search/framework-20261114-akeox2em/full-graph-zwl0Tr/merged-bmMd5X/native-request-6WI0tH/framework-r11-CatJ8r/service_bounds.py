"""Optimistic duration endpoints shared by all search policies and bounds.

A cooperative compound's declared native recipe ticks still describe its
uncontended child work. Summing those is not a duration lower bound when its
registered FCFS phases can overlap. Ignore channel contention for a safe
endpoint, while actual transitions always execute the exact phase model.
"""


def optimistic_ticks(binding, *, warm=True):
    def endpoint(b):return b.get('warm_ticks',b['ticks']) if warm else b['ticks']
    if 'phase_execution' in binding:
        return max(endpoint(c['binding']) for c in binding['parallel_shards']['children'])
    return endpoint(binding)
