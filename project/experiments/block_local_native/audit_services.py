"""Offline source/log audit and immutable measured S request fixtures."""
import argparse
import hashlib
import json
from pathlib import Path
import re
from audit_range import unpack


def quant_trace(log, known):
    generation = 2 if known else 1
    events = []
    summary = None
    for line in log.decode().splitlines():
        if line.startswith('QUANTIZER_EVENT '):
            fields = dict(v.split('=', 1) for v in line.split()[1:])
            tag = int(fields['tag'], 16)
            if tag >> 16 == generation:
                events.append(dict(cycle=int(fields['cycle']), event=fields['kind'],
                    write=int(fields['write']), tag=tag,
                    address=int(fields['address']) if 'address' in fields else None))
        if line.startswith('QUANTIZER_REAL_S '):
            fields = dict(v.split('=', 1) for v in line.split()[1:])
            if int(fields['known']) == int(known) and int(fields['shift']) == 0:
                summary = {k: int(v) for k, v in fields.items()}
    assert summary and events
    requests = {e['tag']: e for e in events if e['event'] == 'REQ'}
    returns = {e['tag']: e for e in events if e['event'] == 'ACK'}
    assert len(requests) == len(returns) == (48 if known else 80)
    assert set(requests) == set(returns)
    assert sum(e['write'] for e in requests.values()) == 16
    first = min(e['cycle'] for e in requests.values())
    assert first == summary['first_request']
    outstanding = peak = 0
    # A return can retire concurrently with a new accepted request. Count by
    # cycle rather than arbitrary print order in the Verilog scoreboard.
    for cycle in sorted({e['cycle'] for e in events}):
        outstanding -= sum(e['event'] == 'ACK' for e in events if e['cycle'] == cycle)
        assert outstanding >= 0
        outstanding += sum(e['event'] == 'REQ' for e in events if e['cycle'] == cycle)
        peak = max(peak, outstanding)
        assert outstanding <= 2
    assert outstanding == 0 and peak == 2
    assert summary['occupied_cycles'] == (58 if known else 93)
    assert summary['cmd_to_done'] == (60 if known else 95)
    rows = [dict(request_offset=e['cycle'] - first, response_offset=returns[tag]['cycle'] - first,
        write=e['write'], address=e['address'], kind=(tag >> 14) & 3, index=(tag >> 8) & 63)
        for tag, e in sorted(requests.items(), key=lambda item: item[1]['cycle'])]
    return dict(known_producer_shift=known, summary=summary, max_outstanding=peak, transactions=rows,
        source_log_sha256=hashlib.sha256(log).hexdigest())


def audit(root, output):
    reports = []
    fixtures = None
    for r in json.loads((root / 'index.json').read_text(encoding='utf-8'))['runs']:
        src, logs = unpack(root, r, 'source'), unpack(root, r, 'receipts')
        assert src['source/source-commit.txt'].decode().strip() == r['source_commit']
        for name, sha in json.loads(logs['receipts-manifest.json']).items():
            assert hashlib.sha256(logs[name]).hexdigest() == sha
        for line in logs['source.sha256'].decode().splitlines():
            sha, name = line.split('  ', 1)
            assert hashlib.sha256(src['source/' + name]).hexdigest() == sha
            assert src['source/' + name] == logs['source/' + name]
        results = [json.loads(v) for k, v in logs.items() if k.endswith('/result.json')]
        if r['state'] == 'FAILED':
            assert not results
            assert any(b'%Error:' in v or b'Traceback' in v for k, v in logs.items() if k.endswith('.log'))
        else:
            assert len(results) == 6 and {x['seed'] for x in results} == set(range(25001, 25007))
            for result in results:
                prefix = f'seed-{result["seed"]}/'
                for name, sha in result['hashes'].items():
                    assert hashlib.sha256(logs[prefix + name]).hexdigest() == sha
                if r['family'] == 'gscale':
                    assert result['runs'] == 15
                    assert b'%Warning' not in logs[prefix + 'lint.log']
                    for initial in (0, 1, 2):
                        for mode in (0, 1, 2, 3, 4):
                            assert b'G_SCALE_PASS ' in logs[prefix + f'mode-{mode}-initial-{initial}.log']
                else:
                    assert b'%Warning' not in logs[prefix + 'build.log']
                    for v in result['results']:
                        assert logs[prefix + f'initial-{v["initial"]}.log'].decode().strip() == v['receipt']
                        assert v['receipt'].startswith('PASS ')
                    if r['family'] == 'quant' and r['job'] != 102147:
                        assert b'%Warning' not in logs[prefix + 'real-build.log']
                        for initial in (0, 1, 2):
                            for mode in (0, 1):
                                raw = logs[prefix + f'real-{mode}-{initial}.log']
                                assert b'PASS quantizer_real_s cases=12' in raw
                                if r['job'] == 102168 and mode == 0:
                                    for known in (False, True):
                                        quant_trace(raw, known)
                        if 'joint-build.log' in result['hashes']:
                            assert b'%Warning' not in logs[prefix + 'joint-build.log']
                            for initial in (0, 1, 2):
                                for mode in (0, 1):
                                    assert b'PASS quant_a_joint cases=12' in logs[prefix + f'joint-{mode}-{initial}.log']
            if r['job'] == 102168:
                fixtures = dict(schema='native-a16-quant-s128-events/1', job=r['job'], source_commit=r['source_commit'],
                    qualification='actual original local_s_base and four banks, functional 10ns clock, no 300MHz STA; isolated service schedule must be arbitrated with other clients',
                    payload_register_bytes=32, new_SRAM_bytes=0, provider_response_owner_slots=2,
                    frames=[quant_trace(logs['seed-25001/real-0-0.log'], known) for known in (False, True)])
        reports.append(dict(job=r['job'], family=r['family'], state=r['state'], seeds=len(results)))
    if output is not None:
        assert fixtures, 'measured trace not found'
        output.write_text(json.dumps(fixtures, indent=2) + '\n', encoding='utf-8')
    return dict(passed=True, runs=reports)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--fixture', type=Path)
    a = p.parse_args()
    print(json.dumps(audit(a.root, a.fixture)))
