"""Price the archived 2048-element native N row with phase-specific operands."""
import argparse
from hashlib import sha256
import json
from pathlib import Path

from run import compile_event_ir


def archived_row(directory):
    raw = (directory / 'result/native-command-program.json').read_bytes()
    commands = [row for row in json.loads(raw) if row['task'] == 'rms@row0']
    groups = (commands[:1], commands[1:257], commands[257:258], commands[258:])
    geometry = ((0x100, 1, 0, 1), (0x81, 1, 0, 256), (2, 0, 0, 1), (0x85, 2, 1, 256))
    if any(len(rows) != count or any((r['lane'], r['mode'], r['meta'], r['sources'], r['store'])
                                     != (1, 1, meta, sources, store) for r in rows)
           for rows, (meta, sources, store, count) in zip(groups, geometry)):
        raise ValueError('archived native RMS commands differ')
    for index, (stats, scale) in enumerate(zip(groups[1], groups[3])):
        if (stats['chunk'] != index or scale['chunk'] != index
                or stats['src_words'][0] != scale['src_words'][0]):
            raise ValueError('native RMS replay did not reread the statistics input in order')
    ticks = [sum(row['ticks'] for row in rows) for rows in groups]
    plan = json.loads((directory / 'result/plan.json').read_bytes())
    reference = plan['tasks']['rms@row0']
    log = (directory / 'native.log').read_bytes()
    marker = f'NATIVE_ROWS_PASS rms_elements=2048 softmax_elements=16 residual_elements=2048 cycles={plan["makespan"]}'
    if sum(ticks) != reference['end'] - reference['start'] or log.count(marker.encode()) != 3:
        raise ValueError('archived RMS command time or row qualification differs')
    return ticks, sha256(raw).hexdigest(), sha256(log).hexdigest()


def problem(ticks, resident, *, late_input):
    port, context, ddr = 'U.S.port', 'U.N.context', 'DDR'
    size = 4096
    windows = {name: {'site': 'U', 'offset': i * size, 'bytes': size}
               for i, name in enumerate(('x', 'gamma', 'y'))}
    windows['epsilon'] = {'site': 'U', 'offset': 3 * size, 'bytes': 16}
    values = {name: window['bytes'] for name, window in windows.items()}
    phases = [{'kind': name, 'ticks': duration, 'claims': {} if name == 'factor' else {port: 1}}
              for name, duration in zip(('begin', 'stats', 'factor', 'scale'), ticks)]
    # This case gives the dispatched N commands priority over the DMA copy
    # on the modeled SRAM port. The transfer can use the factor interval.
    phases[0]['priority'] = -1
    phases[1]['priority'] = -1
    norm = {'ticks': sum(ticks), 'claims': {}, 'phases': phases, 'hold_claims': {context: 1},
            'window_phases': {'input_reads': {'x': ['stats', 'scale'], 'epsilon': ['begin', 'begin'],
                                              'gamma': ['scale' if late_input else 'begin', 'scale']},
                              'write': 'scale', 'publish': 'scale', 'result_hold': context}}
    services = {'rms': norm}
    copies = {'x': 'x', 'epsilon': 'epsilon'}
    if resident:
        copies['gamma'] = 'gamma'
    hardware = {'sites': {'U': {'words': 1024, 'bytes': 16384}}, 'nets': {},
                'resources': dict.fromkeys((port, context, ddr), 1),
                'event_model': {'kind': 'qualified-event-model-v1', 'timing': 'replay',
                                'windows': windows, 'value_bytes': values,
                                'services': services, 'initial_copies': copies,
                                'initial_backing': ['gamma'], 'live_out': ['y'],
                                'routes': {'load': {'src': ddr, 'dst': 'U', 'setup': 0,
                                                    'bytes_per_tick': 64, 'claims': {port: 1, ddr: 1}}}}}
    binding = {'id': 'rms', 'site': 'U', 'ticks': sum(ticks), 'resources': [], 'nets': [], 'scratch_words': 0,
               'event_stages': [{'service': 'rms', 'inputs': {w: w for w in ('x', 'gamma', 'epsilon')},
                                 'outputs': {'y': 'y'}}]}
    return {'tasks': [{'id': 'rms', 'bindings': [binding]}]}, hardware


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('--resident', action='store_true')
    args = parser.parse_args()
    ticks, commands, native = archived_row(args.archive)
    result = {}
    for late in (False, True):
        model, hardware = problem(ticks, args.resident, late_input=late)
        plan = compile_event_ir(model, hardware, width=1)['plan']
        events = plan['tasks'][0]['evaluation']['events']
        result['late' if late else 'entry'] = {'end': plan['makespan'], 'phases': events[-1]['phases'],
                                              'moves': [[e['start'], e['end']] for e in events[:-1]],
                                              'read': plan['external_read_bytes']}
    base = sum(ticks)
    expected = base if args.resident else base + 64
    if (result['entry']['end'], result['late']['end']) != (expected, base):
        raise ValueError(f'RMS phase timing differs: {result}')
    if not args.resident and (result['late']['moves'] != [[sum(ticks[:2]), sum(ticks[:2]) + 64]]
                              or result['entry']['read'] != 4096 or result['late']['read'] != 4096):
        raise ValueError(f'RMS DMA did not use the modeled factor interval: {result}')
    print(json.dumps({'commands': commands, 'native_log': native, 'resident': args.resident, **result},
                     sort_keys=True))


if __name__ == '__main__':
    main()
