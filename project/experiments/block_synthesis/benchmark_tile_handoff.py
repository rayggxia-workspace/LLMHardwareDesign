"""Compare tile publication and placement with the same work and hardware.

Times describe the declared test services. This is an Algo1 model benchmark.
"""
import argparse
import json

from cover_frontier import search
from run import compile_event_ir
from verify_cover_frontier import verify


def binding(name, site, stages):
    return {'id': name, 'site': site, 'ticks': 1, 'resources': [], 'nets': [],
            'scratch_words': 0, 'event_stages': stages}


def stage(service, *, inputs=None, outputs=None):
    return {'service': service, 'inputs': inputs or {}, 'outputs': outputs or {}}


def task(name, *bindings, after=()):
    return {'id': name, 'after': after, 'bindings': bindings}


def window(site, offset, size):
    return {'site': site, 'offset': offset, 'bytes': size}


def hardware(sites, resources, windows, values, services, *, routes=None, backing=()):
    return {
        'sites': {site: {'bytes': size, 'words': size // 16} for site, size in sites.items()},
        'resources': dict.fromkeys(resources, 1),
        'nets': {},
        'event_model': {
            'kind': 'qualified-event-model-v1',
            'timing': 'replay',
            'windows': windows,
            'value_bytes': values,
            'services': services,
            'routes': routes or {},
            'initial_backing': list(backing),
        },
    }


def run(tasks, hw):
    plan = search(tasks, hw, width=8, ready_limit=None)
    verify(tasks, hw, (), plan)
    return plan, {row['id']: row for row in plan['tasks']}


def handoff(early):
    windows = {f'tile-{i}': window('P0', 16 * i, 16) for i in range(2)}
    services = {
        'produce': {
            'ticks': 6, 'claims': {}, 'hold_claims': {'result': 1},
            'phases': [
                {'kind': 'compute', 'ticks': 3, 'claims': {'M': 1}},
                {'kind': 'publish', 'ticks': 1, 'claims': {'S': 1}},
                {'kind': 'retire', 'ticks': 2, 'claims': {}},
            ],
            'window_phases': {'write': 'publish', 'publish': 'publish', 'result_hold': 'result'},
        },
        'consume': {'ticks': 2, 'claims': {'E': 1, 'S': 1}},
    }
    hw = hardware({'P0': 32}, ('M', 'E', 'S', 'result'), windows,
                  dict.fromkeys(windows, 16), services)
    producer = task('producer', binding('producer', 'P0', [
        stage('produce', outputs={name: name}) for name in windows]))
    consumers = [
        task(f'consumer-{i}', binding('consume', 'P0', [stage('consume', inputs={name: name})]),
             after=() if early else ('producer',))
        for i, name in enumerate(windows)
    ]
    if early:
        for i, consumer in enumerate(consumers):
            consumer['event_after'] = [{'task': 'producer', 'from': [i, 'publish'], 'to': [0, 'stage']}]
    result = compile_event_ir({'tasks': [producer, *consumers]}, hw, emit_dependencies=True)
    plan = result['plan']
    rows = {row['id']: row for row in plan['tasks']}
    operations = result['phase_dependencies']['operations']
    waits = {entry['task']: entry['phases'][0]['wait_for'] for entry in operations
             if entry['task'] != 'producer'}
    writes = rows['producer']['evaluation']['events']
    tiles = []
    for i, write in enumerate(writes):
        commit = next(phase for phase in write['phases'] if phase['kind'] == 'publish')
        read = rows[f'consumer-{i}']
        prerequisites = [[operations[parent]['id'], operations[parent]['phases'][phase]['event']]
                         for parent, phase in waits[read['id']]]
        expected = [[i, 'publish']] if early else [[i, 'publish'], [1, 'retire']]
        if set(map(tuple, expected)) != set(map(tuple, prerequisites)):
            raise ValueError(f'unexpected command prerequisites for tile {i}: {prerequisites}')
        tiles.append({'write_start': commit['start'], 'publish': commit['end'],
                      'producer_retire': write['end'], 'consume_start': read['start'],
                      'last_read': read['end'],
                      'waits_for': prerequisites})
    boundaries = sorted({tile[key] for tile in tiles for key in ('write_start', 'last_read')})
    peak = max(sum(16 for tile in tiles if tile['write_start'] <= tick < tile['last_read'])
               for tick in boundaries)
    return {'ticks': plan['makespan'], 'peak_live_tile_bytes': peak,
            'wait_owner': 'Algo1 dependency', 'tiles': tiles}


def placement(pressure):
    windows = {site: window(site, 0, 64) for site in ('P0', 'P1', 'P2')}
    services = {
        'dot0': {'ticks': 8, 'claims': {'M0': 1}},
        'dot1': {'ticks': 8, 'claims': {'M1': 1}},
        'use': {'ticks': 1, 'claims': {}},
    }
    routes = {
        site: {'src': 'DDR', 'dst': site, 'setup': 0, 'bytes_per_tick': 8,
               'claims': {bus: 1, f'{site}.S': 1}}
        for site, bus in (('P0', 'DDR0'), ('P1', 'DDR1'), ('P2', 'DDR1'))
    }
    hw = hardware(dict.fromkeys(windows, 64),
                  ('DDR0', 'DDR1', 'M0', 'M1', 'P0.S', 'P1.S', 'P2.S'),
                  windows, dict.fromkeys(('lhs', 'rhs', 'background'), 64),
                  services, routes=routes, backing=('rhs', 'background'))
    hw['event_model']['initial_copies'] = {'P0': 'lhs'}
    left = task('a', binding('on-P0', 'P0', [stage('dot0', inputs={'P0': 'lhs'})]))
    options = [binding('on-P0', 'P0', [stage('dot0', inputs={'P0': 'rhs'})]),
               binding('on-P1', 'P1', [stage('dot1', inputs={'P1': 'rhs'})])]
    background = task('0-background', binding('load', 'P2', [
        stage('use', inputs={'P2': 'background'})]))
    if pressure:
        hw['event_model']['routes']['P2']['setup'] = 12
    extra = [background] if pressure else []
    scores = {}
    for option in options:
        plan, _ = run([*extra, left, task('b', option)], hw)
        scores[option['id']] = plan['makespan']
    plan, rows = run([*extra, left, task('b', *options)], hw)
    return {'ticks': plan['makespan'], 'selected': rows['b']['binding'],
            'fixed_binding_ticks': scores, 'ddr_read_bytes': plan['external_read_bytes']}


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('case', choices=('handoff', 'placement'))
    args = cli.parse_args()
    if args.case == 'handoff':
        result = {'barrier': handoff(False), 'tile': handoff(True)}
    else:
        result = {'idle': placement(False), 'shared_channel': placement(True)}
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
