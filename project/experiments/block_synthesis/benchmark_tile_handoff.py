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


def handoff(policy):
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
    producers = [task('producer', binding('producer', 'P0', [
        stage('produce', outputs={name: name}) for name in windows]))]
    if policy == 'command':
        # This profile models independently acknowledged tile commands.
        # Their final phase is the publish event; command cleanup is not a
        # consumer prerequisite for such a service.
        service = services['produce']
        service['phases'].pop()
        service['ticks'] = 4
        producers = [task(f'producer-{i}', binding('produce', 'P0', [
            stage('produce', outputs={name: name})])) for i, name in enumerate(windows)]
    consumers = [
        task(f'consumer-{i}', binding('consume', 'P0', [stage('consume', inputs={name: name})]),
             after={'tile': (), 'barrier': ('producer',),
                    'command': (f'producer-{i}',)}[policy])
        for i, name in enumerate(windows)
    ]
    if policy == 'tile':
        for i, consumer in enumerate(consumers):
            consumer['event_after'] = [{'task': 'producer', 'from': [i, 'publish'], 'to': [0, 'stage']}]
    model = {'tasks': [*producers, *consumers]}
    result = compile_event_ir(model, hw, emit_dependencies=True, emit_outputs=policy == 'command')
    plan = result['plan']
    rows = {row['id']: row for row in plan['tasks']}
    operations = result['phase_dependencies']['operations']
    blockers = result['phase_dependencies']['completion_only_blockers']
    waits = {entry['task']: entry['phases'][0]['wait_for'] for entry in operations
             if entry['task'].startswith('consumer-')}
    writes = [event for producer in producers for event in rows[producer['id']]['evaluation']['events']]
    tiles = []
    for i, write in enumerate(writes):
        commit = next(phase for phase in write['phases'] if phase['kind'] == 'publish')
        read = rows[f'consumer-{i}']
        prerequisites = [[operations[parent]['task'], operations[parent]['phases'][phase]['event']]
                         for parent, phase in waits[read['id']]]
        expected = {'tile': [['producer', 'publish']],
                    'barrier': [['producer', 'publish'], ['producer', 'retire']],
                    'command': [[f'producer-{i}', 'publish']]}[policy]
        if sorted(expected) != sorted(prerequisites):
            raise ValueError(f'unexpected command prerequisites for tile {i}: {prerequisites}')
        tiles.append({'write_start': commit['start'], 'publish': commit['end'],
                      'producer_retire': write['end'], 'consume_start': read['start'],
                      'last_read': read['end'],
                      'waits_for': prerequisites})
    boundaries = sorted({tile[key] for tile in tiles for key in ('write_start', 'last_read')})
    peak = max(sum(16 for tile in tiles if tile['write_start'] <= tick < tile['last_read'])
               for tick in boundaries)
    if len(blockers) != {'tile': 2, 'barrier': 2, 'command': 0}[policy]:
        raise ValueError(f'unexpected command ABI blockers: {blockers}')
    report = {'ticks': plan['makespan'], 'peak_live_tile_bytes': peak,
              'wait_owner': 'Algo1 dependency', 'tiles': tiles,
              'completion_only_blockers': blockers}
    if policy == 'command':
        outputs = result['outputs']
        dispatch = outputs['program']['mother'][:-1]
        if outputs['program']['source'] != outputs['wiring']['source']:
            raise ValueError('control and wiring outputs do not share provenance')
        by_task = {row['task_id']: row for row in dispatch}
        for i in range(2):
            if by_task[f'consumer-{i}']['wait_for'] != [by_task[f'producer-{i}']['sequence']]:
                raise ValueError('control IR lost its tile completion dependency')
        report['control_dispatch'] = [{'task': row['task_id'], 'wait_for': row['wait_for']} for row in dispatch]
    else:
        from event_deploy import emit

        try:
            emit(model['tasks'], hw, (), plan)
        except ValueError as error:
            if 'command completion cannot preserve' not in str(error):
                raise
        else:
            raise ValueError('control IR silently replaced a phase wait')
    return report


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
        result = {policy: handoff(policy) for policy in ('barrier', 'tile', 'command')}
    else:
        result = {'idle': placement(False), 'shared_channel': placement(True)}
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
