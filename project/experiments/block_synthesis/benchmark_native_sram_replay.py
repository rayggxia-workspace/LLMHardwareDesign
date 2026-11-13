"""Compare state-dependent SRAM replay against the #251 RTL probe logs."""
import argparse
import json
from pathlib import Path

from cover_frontier import search
from verify_cover_frontier import verify


# Each pair is (requests, first tick at which the downstream takes responses).
CASES = (
    ((3, 0), (0, 0)),
    ((3, 0), (3, 0)),
    ((3, 0), (3, 6)),
    ((3, 9), (3, 6)),
    ((3, 0), (1, 0)),
    ((7, 0), (0, 0)),
    ((3, 0), (1, 9)),
    ((7, 0), (0, 9)),
)
def binding(name, service, inputs=None, outputs=None):
    return {'id': name, 'site': 'P0', 'ticks': 1, 'resources': [], 'nets': [], 'scratch_words': 0,
            'event_stages': [{'service': service, 'inputs': inputs or {}, 'outputs': outputs or {}}]}


def event_input(mode, *, compare=False):
    (narrow, n_open), (wide, w_open) = CASES[mode]
    stops = sorted({0, n_open, w_open})
    ready = [[a, b, int(a >= n_open) + 2 * int(a >= w_open)] for a, b in zip(stops, stops[1:])]
    spec = {'kind': 'qualified-event-model-v1', 'timing': 'replay', 'windows': {},
            'value_bytes': {}, 'routes': {}, 'services': {}, 'initial_copies': {},
            'sram_feeders': {'P0': {'ready': ready}}}
    hardware = {'sites': {'P0': {'bytes': 16384, 'words': 1024}}, 'resources': {}, 'nets': {},
                'event_model': spec}
    for kind in ('read-narrow', 'read-wide', 'write-narrow'):
        spec['services'][kind] = {'ticks': 1, 'claims': {}, 'sram_access': kind}

    def window(word, words, initialized):
        name = f'word-{word}'
        spec['windows'][name] = {'site': 'P0', 'offset': 16 * word, 'bytes': 16 * words}
        spec['value_bytes'][name] = 16 * words
        if initialized:
            spec['initial_copies'][name] = name
        return {name: name}

    tasks = []
    for i in range(3):
        bind = binding('write', 'write-narrow', outputs=window(16 + i, 1, False))
        tasks.append({'id': f'narrow-{i}', 'bindings': [bind]})
    if compare:
        row = window(0, 4, True)
        tasks.append({'id': 'read-row', 'bindings': [binding('wide', 'read-wide', inputs=row),
                                                     binding('narrow', 'read-narrow', inputs=row)]})
    elif narrow > 3:
        for i in range(4):
            bind = binding('read', 'read-narrow', inputs=window(i, 1, True))
            tasks.append({'id': f'narrow-{i + 3}', 'bindings': [bind]})
    elif wide:
        row = window(0, 4, True)
        for i in range(wide):
            tasks.append({'id': f'wide-{i}', 'bindings': [binding('read', 'read-wide', inputs=row)]})
    return tasks, hardware


def plan(mode, *, compare=False, width=1):
    tasks, hardware = event_input(mode, compare=compare)
    result = search(tasks, hardware, width=width, ready_limit=1)
    verify(tasks, hardware, (), result)
    return result


def predict(mode):
    result = plan(mode)
    return {(port, int(index), name): beat[name]
            for row in result['tasks']
            for port, index in (row['id'].split('-'),)
            for beat in row['evaluation']['events'][0]['sram_beats']
            for name in ('issue', 'ack')}


def check_trace(mode, lines):
    observed = {}
    passes = []
    for line in lines:
        if line.startswith('PASS '):
            passes.append(line.strip())
        if line.startswith('TRACE '):
            _, port, index, event, tick = line.split()
            key = port, int(index), event
            if key in observed:
                raise ValueError(f'mode {mode} duplicate handshake {key}')
            observed[key] = int(tick)
    if passes != [f'PASS mode={mode}']:
        raise ValueError(f'mode {mode} missing unique RTL PASS')
    expected = predict(mode)
    for key in sorted(observed.keys() | expected.keys()):
        if observed.get(key) != expected.get(key):
            raise ValueError(f'mode {mode} {key}: RTL={observed.get(key)}, replay={expected.get(key)}')
    return {'handshakes': len(observed), 'end': max(observed.values()),
            'old_first_issue': observed['narrow', 0, 'issue'],
            'old_last_ack': observed['narrow', 2, 'ack']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('log_dir', type=Path, help='directory containing native-sram-mode-*.log')
    args = parser.parse_args()
    outcomes = []
    for mode in range(len(CASES)):
        with (args.log_dir / f'native-sram-mode-{mode}.log').open(encoding='utf-8') as source:
            outcomes.append(check_trace(mode, source))
    pairs = {}
    for mode, narrow, selected in ((4, 5, 'wide'), (6, 7, 'narrow')):
        for width in (1, 8):
            result = plan(mode, compare=True, width=width)
            row = result['tasks'][-1]
            expected = min(outcomes[mode]['end'], outcomes[narrow]['end'])
            if (row['binding'], result['makespan']) != (selected, expected + 1):
                raise ValueError(f'mode {mode} DP ranking differs from archived RTL')
        pairs[mode] = {'wide_ack': outcomes[mode]['end'], 'narrow_ack': outcomes[narrow]['end'],
                       'selected': selected}
    print(json.dumps({'cases': outcomes, 'choices': pairs}, indent=2))


if __name__ == '__main__':
    main()
