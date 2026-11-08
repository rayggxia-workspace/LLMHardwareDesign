"""Bounded native-command timing probe for independently owned M contexts.

Consumes the same measured templates and one-word descriptor model. This is
a timing microexperiment, not an executable data/numerical or full-system proof.
"""
import argparse
from collections import Counter
import hashlib
import heapq
import json
from pathlib import Path

from memory import descriptor_ticks


def phases(body, library, meta, memory, *, limit=100000):
    result = []
    def emit(channel, ticks, kind):
        if ticks:
            if len(result) >= limit:
                raise ValueError('bounded phase trace limit exceeded')
            result.append({'channel': channel, 'ticks': ticks, 'kind': kind})
    channel = meta['memory_group'] % memory['channels']
    load = descriptor_ticks(memory, 1, 'load', meta['io_write_ticks'])
    store = descriptor_ticks(memory, 1, 'store', meta['io_read_ticks'])
    def visit(part, stack=()):
        if 'call' in part:
            if part['call'] in stack:
                raise ValueError('recursive phase template')
            visit(library[part['call']], stack + (part['call'],))
        elif 'repeat' in part:
            if type(part['repeat']) is not int or part['repeat'] < 0 or part['repeat'] > limit:
                raise ValueError('unbounded phase repeat')
            for _ in range(part['repeat']):
                visit(part['body'], stack)
        elif 'sequence' in part:
            for child in part['sequence']:
                visit(child, stack)
        else:
            if part['macro'] not in ('M', 'IO'):
                raise ValueError('probe supports independently owned M and IO only')
            for _ in range(part['read_words']):
                emit(channel, load, 'external-load-until-S-commit')
                if part['macro'] != 'IO':
                    emit(-1, meta['io_read_ticks'], 'S-operand-read')
            emit(-1, part.get('ticks', 0), part.get('native', 'IO'))
            for _ in range(part['write_words']):
                if part['macro'] != 'IO':
                    emit(-1, meta['io_write_ticks'], 'S-result-write')
                emit(channel, store, 'external-store-until-ACK')
    visit(body)
    return result


def reference(workers, channels, *, whole_service=False):
    """Independent integer event simulator; simultaneous requests order by ID."""
    if not workers or channels < 1:
        raise ValueError('empty timing probe')
    events = [(0, i, 0) for i in range(len(workers))]
    heapq.heapify(events)
    pending = [[] for _ in range(channels)]
    busy = [False] * channels
    rows = []
    finished = {}
    if whole_service:
        free = [0] * channels
        for i, worker in enumerate(workers):
            used = {p['channel'] for p in worker if p['channel'] >= 0}
            if len(used) != 1:
                raise ValueError('whole service probe needs one channel per worker')
            c = next(iter(used)); now = free[c]
            for j, phase in enumerate(worker):
                rows.append((i, j, phase['channel'], now, now + phase['ticks']))
                now += phase['ticks']
            free[c] = now
            finished[i] = now
        return {'rows': sorted(rows), 'makespan': max(finished.values())}
    while events:
        now = events[0][0]
        ready = []
        while events and events[0][0] == now:
            _, i, j = heapq.heappop(events)
            if j:
                previous = workers[i][j - 1]
                if previous['channel'] >= 0:
                    busy[previous['channel']] = False
            if j == len(workers[i]):
                finished[i] = now
            else:
                ready.append((i, j))
        for i, j in sorted(ready):
            phase = workers[i][j]; c = phase['channel']
            if c < 0:
                end = now + phase['ticks']
                rows.append((i, j, c, now, end))
                heapq.heappush(events, (end, i, j + 1))
            else:
                heapq.heappush(pending[c], (now, i, j))
        for c in range(channels):
            if not busy[c] and pending[c]:
                _, i, j = heapq.heappop(pending[c])
                end = now + workers[i][j]['ticks']
                rows.append((i, j, c, now, end))
                busy[c] = True
                heapq.heappush(events, (end, i, j + 1))
    if any(pending) or len(finished) != len(workers):
        raise ValueError('phase oracle did not drain')
    return {'rows': sorted(rows), 'makespan': max(finished.values())}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('ir', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--groups', nargs='+', required=True)
    parser.add_argument('--repetitions', type=int, default=128)
    args = parser.parse_args()
    if not 1 <= args.repetitions <= 4096 or len(args.groups) != len(set(args.groups)):
        raise ValueError('finite repetitions and distinct control groups required')
    raw = args.ir.read_bytes(); ir = json.loads(raw); h = ir['hardware']
    from streaming_ir import repeat, seq, call
    body = seq(repeat(args.repetitions, call('partial')), call('dot_final'))
    workers = []
    for group in args.groups:
        meta = h['leaf_inventory'][group]
        if 'M' not in meta['macros'] or meta['words'] < 8:
            raise ValueError('probe requires a native M and eight private scratch words')
        workers.append(phases(body, ir['native_templates'], meta, h['virtual_memory']))
    channels = h['virtual_memory']['channels']
    args.output.mkdir(parents=True, exist_ok=False)
    source = {'workers': workers, 'channels': channels, 'groups': args.groups,
              'source_ir_sha256': hashlib.sha256(raw).hexdigest(),
              'scope': 'timing-only uncached scalar native partials; distinct LC/M/S ownership; no numerical/RTL proof',
              'energy': 'event counts only; no calibrated energy coefficients',
              'clock': 'one symbolic tick represented as one ns; no physical frequency conversion'}
    (args.output / 'probe.json').write_text(json.dumps(source, indent=2) + '\n')
    text = f'{len(workers)} {channels}\n'
    for worker in workers:
        text += str(len(worker)) + '\n'
        text += ''.join(f"{p['channel']} {p['ticks']}\n" for p in worker)
    (args.output / 'probe.txt').write_text(text)
    report = {mode: reference(workers, channels, whole_service=mode == 'whole-service')
              for mode in ('whole-service', 'descriptor-phases')}
    report['event_counts'] = dict(Counter(p['kind'] for w in workers for p in w))
    (args.output / 'reference.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: v['makespan'] for k, v in report.items() if k != 'event_counts'}))


if __name__ == '__main__':
    main()
