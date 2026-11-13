"""Compare two FFN COPY launch policies using archived #251 handshakes."""
import argparse
from copy import deepcopy
import json
from pathlib import Path

from cover_frontier import search
from ffn_a import A_BASE, P_COUNT, WORDS
from verify_cover_frontier import verify


def problem(mode, header, source, source_word, offsets):
    ports = {f'P{p}.S.port': 1 for p in range(P_COUNT)}
    if source == 'U':
        ports['U.S.port'] = 1
    hardware = {'resources': ports, 'nets': {},
                'sites': {site: {'bytes': 16384, 'words': 1024} for site in ('P0', 'P1', 'P2', 'U')}}
    windows = {'source': {'site': source, 'offset': source_word * 16, 'bytes': WORDS * 16}}
    outputs = {f'A{p}': 'tile' for p in range(P_COUNT)}
    windows.update({name: {'site': f'P{p}', 'offset': A_BASE * 16, 'bytes': WORDS * 16}
                    for p, name in enumerate(outputs)})
    spec = hardware['event_model'] = {
        'kind': 'qualified-event-model-v1', 'timing': 'replay', 'windows': windows,
        'value_bytes': {'tile': WORDS * 16}, 'routes': {}, 'initial_copies': {'source': 'tile'},
        'services': {'header': {'ticks': header, 'claims': {}}, 'consume': {'ticks': 1, 'claims': {}}},
    }

    def binding(name, inputs=None, outputs=None, ticks=1):
        return {'id': name, 'site': 'P0', 'ticks': ticks, 'resources': [], 'nets': [], 'scratch_words': 0,
                'event_stages': [{'service': name, 'inputs': inputs or {}, 'outputs': outputs or {}}]}

    candidates = []
    for delay, name in enumerate(('on-time', 'one-tick-later')):
        spec['services'][name] = {
            'ticks': 1, 'claims': ports,
            'ffn_activation': {'mode': mode, 'copy_delay': delay, 'load_offsets': offsets},
        }
        candidates.append(binding(name, {'source': 'tile'}, outputs))
    return ([{'id': 'header', 'bindings': [binding('header', ticks=header)]},
             {'id': 'activation', 'after': ['header'], 'bindings': candidates},
             {'id': 'consume', 'after': ['activation'], 'bindings': [binding('consume', outputs)]}],
            hardware)


def observed(path, scope, k):
    with path.open(encoding='utf-8') as source:
        return activation_receipt(source, scope, k)


def activation_receipt(source, scope, k):
    wanted = {'copy': 'writes', 'ack': 'write_acks', 'read': 'reads', 'response': 'read_acks'}
    beats = {name: [] for name in wanted.values()}
    loads, proofs = {}, set()
    tags = {}
    details = {}
    for line in source:
        if not line.startswith(('AREAD ', 'K_PROFILE ', 'PISSUE aload ')):
            continue
        if line.startswith('K_PROFILE '):
            fields = dict(field.split('=') for field in line.split()[1:])
            if (int(fields['scope']), int(fields['k'])) == (scope, k):
                details['header'] = int(fields['header'])
            continue
        _, kind, *fields = line.split()
        if kind in ('prefix',):
            continue
        row = list(map(int, fields))
        if kind == 'start' and tuple(row[1:3]) == (scope, k):
            details['copy_start'], tags['copy'] = row[0], row[3]
        elif kind == 'load' and tuple(row[2:4]) == (scope, k):
            loads[row[1]] = row[0]
            tags['read'] = row[4]
        elif kind == 'aload' and tuple(row[2:4]) == (scope, k):
            proofs.add(row[0])
        elif kind == 'done' and row[1] == tags.get('copy'):
            details['copy_done'] = row[0]
        elif kind == 'source' and row[-1] >> 16 == tags.get('copy') and 'source' not in details:
            details['source'] = 'U' if row[1] == P_COUNT else f'P{row[1]}'
            details['source_word'] = row[2]
        elif kind in wanted and len(proofs) == 0:
            tag = tags.get('copy' if kind in ('copy', 'ack') else 'read')
            if row[-1] >> 16 == tag and (kind in ('copy', 'ack') or row[0] >= loads.get(row[1], row[0] + 1)):
                beats[wanted[kind]].append(row[:-1])
        if len(proofs) == 1 and 'header' in details and all(len(rows) == P_COUNT * WORDS for rows in beats.values()):
            break
    details['loads'] = [loads[p] for p in range(P_COUNT)]
    details['proof'], = proofs
    return {**details, **{kind: sorted(rows) for kind, rows in beats.items()}}


def compare(baseline, candidate, scope, k, mode):
    receipts = [observed(path, scope, k) for path in (baseline, candidate)]
    first, second = receipts
    context = ('header', 'source', 'source_word', 'loads')
    if any(first[field] != second[field] for field in context):
        raise ValueError('archived candidates have different entry state')
    header = first['header']
    tasks, hardware = problem(mode, header, first['source'], first['source_word'],
                              tuple(load - header for load in first['loads']))
    for binding, receipt in zip(tasks[1]['bindings'], receipts):
        forced = deepcopy(tasks)
        forced[1]['bindings'] = [binding]
        result = search(forced, hardware, width=1)
        verify(forced, hardware, (), result)
        event = result['tasks'][1]['evaluation']['events'][0]
        expected = {key: receipt[key] for key in event['activation']}
        actual = {key: sorted(value) if key in ('writes', 'reads', 'write_acks', 'read_acks') else value
                  for key, value in event['activation'].items()}
        if actual != expected or result['tasks'][2]['start'] != receipt['proof'] + 1:
            raise ValueError(f'FFN activation evidence differs for {binding["id"]}')
    preferred = tasks[1]['bindings'][min(range(2), key=lambda i: receipts[i]['proof'])]['id']
    for width in (1, 8):
        result = search(tasks, hardware, width=width)
        verify(tasks, hardware, (), result)
        if result['tasks'][1]['binding'] != preferred:
            raise ValueError('FFN candidate ranking differs')
    return {'scope': scope, 'k': k, 'copy_done': [r['copy_done'] for r in receipts],
            'proof': [r['proof'] for r in receipts], 'selected': preferred}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('baseline', type=Path)
    parser.add_argument('candidate', type=Path)
    parser.add_argument('scope', type=int)
    parser.add_argument('k', type=int)
    parser.add_argument('mode', type=int)
    args = parser.parse_args()
    print(json.dumps(compare(args.baseline, args.candidate, args.scope, args.k, args.mode)))
