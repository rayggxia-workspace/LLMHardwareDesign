"""Compare DP read receipts with the #251 typed DMA RTL probe."""
import argparse
from dataclasses import dataclass
import json
from pathlib import Path

from cover_frontier import search
from verify_cover_frontier import verify


@dataclass(frozen=True)
class Request:
    release: int
    client: int
    address: int
    size: int = 128
    record_beats: int = 2


OLD = (Request(1, 7, 0), Request(1, 8, 0x100))
CASES = {'old': (OLD, (), ()), 'added': ((*OLD, Request(1, 0, 0x200)), (), ())}
for blocked in (0, 1):
    for client in (0, 1):
        CASES[f'blocked-{blocked}-client-{client}'] = (
            (*OLD, Request(1, client, 0x200)), (), ((0, 20, 4095 ^ (1 << blocked)),))
CASES['pressure'] = (
    tuple(Request(1 + client % 3, client, 0x10000 * client + (0x800 if client % 2 else 0),
                  1280 if client < 9 else 64 * (17 + client % 2),
                  2 if client < 9 else 17 + client % 2) for client in range(12)),
    ((3, 30, 0), (30, 45, 10), (45, 60, 9)),
    ((3, 65, 0), (65, 80, 4080)),
)
RETURN_LATENCY = (3, 5)


def event_input(requests, ddr_stalls=(), client_stalls=(), alternatives=None):
    alternatives = alternatives or {}
    tasks, sites, resources, routes, windows, sizes, addresses = [], {}, {}, {}, {}, {}, {}
    for index, read in enumerate(requests):
        site, value = f'P{index}', f'v{index}'
        ack = f'{site}.write'
        sites[site] = {'bytes': read.size, 'words': read.size // 16}
        resources[ack] = 1
        windows[site] = {'site': site, 'offset': 0, 'bytes': read.size}
        sizes[value] = read.size
        addresses[value] = read.address
        for client in (read.client, *alternatives.get(index, ())):
            routes[f'{site}.read-{client}'] = {
                'src': 'DDR', 'dst': site, 'claims': {}, 'setup': 0, 'bytes_per_tick': 64,
                'typed_dma': {'client': client, 'record_beats': read.record_beats},
                'phases': {'issue': {'ticks': read.release, 'claims': {}},
                           'ack': {'ticks': 1, 'claims': {ack: 1}}, 'hold_claims': {}},
            }
        tasks.append({'id': f'read-{index:02}', 'bindings': [
            {'id': 'use', 'site': site, 'ticks': 1, 'resources': [], 'nets': [], 'scratch_words': 0,
             'event_stages': [{'service': 'use', 'inputs': {site: value}}]}]})
    hardware = {
        'sites': sites, 'resources': resources, 'nets': {},
        'event_model': {
            'kind': 'qualified-event-model-v1', 'timing': 'replay', 'windows': windows,
            'value_bytes': sizes, 'routes': routes, 'services': {'use': {'ticks': 1, 'claims': {}}},
            'initial_backing': list(sizes),
            'typed_dma': {'return_latency': RETURN_LATENCY, 'ddr_ready': ddr_stalls,
                          'client_ready': client_stalls, 'addresses': addresses},
        },
    }
    return tasks, hardware


def moves_by_task(plan):
    return {int(row['id'].split('-')[1]): row['evaluation']['events'][0] for row in plan['tasks']}


def write_stimulus(directory):
    for name, (reads, ddr_stalls, client_stalls) in CASES.items():
        rows = [RETURN_LATENCY, (len(ddr_stalls),), *ddr_stalls, (len(client_stalls),), *client_stalls, (len(reads),)]
        rows.extend((read.release, read.client, read.address, read.size, read.record_beats) for read in reads)
        with (directory / f'{name}.stim').open('x', encoding='ascii') as output:
            output.writelines(' '.join(map(str, row)) + '\n' for row in rows)


def check_case(directory, name):
    reads, ddr_stalls, client_stalls = CASES[name]
    tasks, hardware = event_input(reads, ddr_stalls, client_stalls)
    plan = search(tasks, hardware, width=1)
    verify(tasks, hardware, (), plan)
    moves = moves_by_task(plan)
    for index, read in enumerate(reads):
        if moves[index]['phases'][1]['start'] != read.release:
            raise ValueError(f'{name} source release differs')
    columns = ('address', 'channel', 'entry', 'reserved', 'offer', 'issue', 'captured', 'delivered')
    expected = {(index, beat['address']): tuple(beat[key] for key in columns)
                for index, move in moves.items() for beat in move['dma_beats']}
    observed = {}
    with (directory / f'{name}.csv').open(encoding='ascii') as source:
        for line in source:
            index, *beat = map(int, line.strip().split(','))
            key = index, beat[0]
            if key in observed:
                raise ValueError(f'{name} duplicate RTL beat {key}')
            observed[key] = tuple(beat)
    for key in sorted(expected.keys() | observed.keys()):
        if observed.get(key) != expected.get(key):
            raise ValueError(f'{name} {key}: RTL={observed.get(key)}, DP={expected.get(key)}')
    return {'beats': len(expected), 'ticks': plan['makespan'], 'read_bytes': plan['external_read_bytes'],
            'read_1_first_reservation': moves[1]['dma_beats'][0]['reserved'],
            'max_offer_wait': max(beat['issue'] - beat['offer'] for move in moves.values()
                                  for beat in move['dma_beats']),
            'max_skid_wait': max(beat['delivered'] - beat['captured'] for move in moves.values()
                                 for beat in move['dma_beats'])}


def check(directory):
    results = {name: check_case(directory, name) for name in CASES}
    if results['old']['read_1_first_reservation'] >= results['added']['read_1_first_reservation']:
        raise ValueError('new read must delay the reservation of an old read')
    choices = {}
    for blocked in (0, 1):
        reads, ddr_stalls, client_stalls = CASES[f'blocked-{blocked}-client-0']
        tasks, hardware = event_input(reads, ddr_stalls, client_stalls, alternatives={2: (1,)})
        costs = [results[f'blocked-{blocked}-client-{c}']['ticks'] for c in (0, 1)]
        client = 1 - blocked
        if costs[client] >= costs[blocked]:
            raise ValueError('RTL client backpressure did not change candidate ranking')
        for width in (1, 8):
            plan = search(tasks, hardware, width=width)
            verify(tasks, hardware, (), plan)
            if (moves_by_task(plan)[2]['route'], plan['makespan']) != (f'P2.read-{client}', costs[client]):
                raise ValueError('search did not choose the faster RTL candidate')
        choices[f'client_{blocked}_blocked'] = {'client_0_ticks': costs[0], 'client_1_ticks': costs[1],
                                                'chosen_client': client}
    return {'cases': results, 'choices': choices}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare', 'check'))
    parser.add_argument('directory', type=Path)
    args = parser.parse_args()
    if args.action == 'prepare':
        args.directory.mkdir(exist_ok=True)
        write_stimulus(args.directory)
    else:
        print(json.dumps(check(args.directory), indent=2))


if __name__ == '__main__':
    main()
