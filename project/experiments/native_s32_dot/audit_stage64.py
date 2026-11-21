"""Offline audit: each MC landing slot stays live through every true S ACK."""
import argparse
from collections import deque
import csv
import io
import json
from pathlib import Path
import re

from audit import read_run


def audit_trace(data):
    live = {}
    result = []
    current = None
    for row in csv.reader(io.StringIO(data.decode())):
        cycle, kind, tag = int(row[0]), row[1], int(row[2])
        values = tuple(map(int, row[3:]))
        if kind == 'CMD':
            dst, first, words, admitted = values
            assert tag not in live and len(live) < 2
            live[tag] = dict(dst=dst, first=first, words=words, admit=bool(admitted),
                             requests=[], pending=deque(), ack_mask=0, cancel=False, failed=False)
            continue
        record = live[tag]
        if kind == 'CANCEL':
            assert record['admit'] and not record['cancel']
            record['cancel'] = True
        elif kind == 'REJECT':
            assert record['admit'] and 'raw' not in record
            record['failed'] = True
            record['rejected'] = True
        elif kind == 'RAW_FIRST':
            assert current is None and record['admit'] and 'raw' not in record
            assert values == (record['words'],)
            current = tag
            record['raw'] = cycle
        elif kind == 'SREQ':
            assert current == tag
            ordinal = len(record['requests'])
            assert len(record['pending']) < 2 and ordinal < record['words']
            assert values == (record['dst'] + ordinal,)
            record['pending'].append(ordinal)
            record['requests'].append(cycle)
        elif kind == 'SACK':
            assert current == tag and len(values) == 1 and record['pending']
            ordinal = record['pending'].popleft()
            assert cycle - record['requests'][ordinal] >= 2
            if values[0]:
                record['failed'] = True
            else:
                record['ack_mask'] |= 1 << ordinal
            record['last_ack'] = cycle
        elif kind == 'RAW_ACK':
            assert current == tag and not record['pending']
            assert values == (len(record['requests']),) and 'raw' in record
            assert cycle > record.get('last_ack', record['raw'])
            record['raw_ack'] = cycle
            current = None
        elif kind == 'DONE':
            assert not record['pending']
            assert values == (int(record['cancel']), int(record['failed'] or not record['admit']), record['ack_mask'])
            if record['admit'] and not record.get('rejected'):
                assert cycle > record['raw_ack']
                if not record['failed'] and not record['cancel']:
                    assert len(record['requests']) == record['words']
                    assert record['ack_mask'] == (1 << record['words']) - 1
                    result.append(dict(words=record['words'], first=record['first'],
                                       raw_to_release=record['raw_ack'] - record['raw'],
                                       raw_to_take=cycle - record['raw'],
                                       requests=[t-record['raw'] for t in record['requests']],
                                       last_S_ACK=record['last_ack']-record['raw']))
            else:
                assert not record['requests'] and 'raw' not in record
            del live[tag]
        else:
            raise AssertionError(row)
    assert not live and current is None and len(result) == 96
    return result


def audit(directory):
    info, files, _ = read_run(directory)
    failed_launch = info['job'] == '102464'
    expected_terminals = 103 if info['job']=='102465' else 104
    rows = []
    profiles = []
    for seed in range(25201, 25207):
        prefix = f'seed-{seed}/'
        if failed_launch:
            assert b'Exited with exit code 2' in files[f'seed-{seed}.log']
            assert prefix + 'result.json' not in files
            continue
        report = json.loads(files[prefix + 'result.json'])
        assert report['passed'] and report['real_S'] and report['seed'] == seed and len(report['affinity']) == 10
        assert b'%Warning' not in files[prefix + 'build.log']
        assert {(r['mode'], r['initial']) for r in report['tests']} == {(m, i) for m in range(2) for i in range(3)}
        for test in report['tests']:
            mode = test['mode']
            raw_log = files.get(prefix + test['log'], files.get(prefix + test['log'] + '.tail', b''))
            match = re.search(rb'PASS dot S128 stage64 mode=(\d+) req=(\d+) ack=(\d+) raw=(\d+) done=(\d+) readback=(\d+) peak=(\d+) held=(\d+) two=(\d+):(\d+) four=(\d+):(\d+) cycles=(\d+)', raw_log)
            assert match
            m, req, ack, raw, done, readback, peak, held, lo2, hi2, lo4, hi4, cycles = map(int, match.groups())
            assert m == mode and req == ack == readback and raw == 99 and done == expected_terminals and peak == 2 and held > 0
            assert mode or (lo2, hi2, lo4, hi4) == (5, 5, 7, 7)
            rows.append(dict(seed=seed, mode=m, initial=test['initial'], S_requests=req, S_acks=ack,
                             raw_returns=raw, terminations=done, S_readback=readback, max_pending=peak,
                             held_cycles=held, two_word_release=[lo2, hi2], four_word_release=[lo4, hi4], cycles=cycles))
            path = prefix + f'timing-{m}-{test["initial"]}.csv'
            if path in files:
                frames = audit_trace(files[path])
                for words in (2, 4):
                    cohort = [f for f in frames if f['words'] == words]
                    assert len(cohort) == 48
                    assert {f['first'] for f in cohort} == ({0, 2} if words == 2 else {0})
                    if not mode:
                        assert all(f['requests'] == list(range(1, words + 1)) and
                                   f['last_S_ACK'] == words + 2 and f['raw_to_release'] == words + 3 for f in cohort)
                    profiles.append(dict(seed=seed, mode=mode, words=words, count=len(cohort),
                                         min_release=min(f['raw_to_release'] for f in cohort),
                                         max_release=max(f['raw_to_release'] for f in cohort)))
    assert len(rows) == (0 if failed_launch else 36)
    return dict(passed=not failed_launch, job=info['job'], source_commit=info['source_commit'],
                source_archive_sha256=info['source_archive_sha256'], receipts_archive_sha256=info['receipts_archive_sha256'],
                rows=rows, traced_groups=profiles, added_SRAM_B=0, local_payload_register_B=0,
                scope='Actual original four-bank S SRAM, held MC-interface peer, descriptor/cancel/OOO/ACK audit. No real MC mux or 300MHz claim.',
                failure='Pinned runner rejected unregistered checker before HDL build.' if failed_launch else None)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', required=True, type=Path)
    args = parser.parse_args()
    report = audit(args.run)
    (args.run / 'audit.json').write_text(json.dumps(report, indent=2) + '\n', newline='\n')
    print(json.dumps(dict(job=report['job'], passed=report['passed'], runs=len(report['rows']), groups=report['traced_groups'])))
