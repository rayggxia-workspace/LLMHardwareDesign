"""Offline byte-exact audit of the actual 16-bank COPY/A joint receipts."""
import argparse
import hashlib
import json
from pathlib import Path
from audit_p_scope import unpack


def audit(root, receipt_cache=None):
    rows = []
    for row in json.loads((root / 'index.json').read_text(encoding='utf-8'))['runs']:
        with_g = row['family'] == 'gcopy-a'
        with_window = row['family'] == 'copywin'
        with_lookahead = row['family'] == 'copylook'
        with_distributed = row['family'] == 'distmid'
        src = unpack(root, row, 'source')
        logs = unpack(root, row, 'receipts', receipt_cache)
        assert src['source/source-commit.txt'].decode().strip() == row['source_commit']
        manifest = json.loads(logs['receipts-manifest.json'])
        for path, digest in manifest.items():
            assert hashlib.sha256(logs[path]).hexdigest() == digest
        for line in logs['source.sha256'].decode().splitlines():
            digest, name = line.split('  ', 1)
            assert hashlib.sha256(src['source/' + name]).hexdigest() == digest
        reports = [json.loads(v) for k, v in logs.items() if k.endswith('/result.json')]
        if row['state'] == 'COMPLETED':
            assert len(reports) == 6 and {r['seed'] for r in reports} == set(range(25001, 25007))
            for r in reports:
                prefix = f"seed-{r['seed']}/"
                assert b'%Warning' not in logs[prefix + 'build.log']
                for name, digest in r['hashes'].items():
                    assert hashlib.sha256(logs[prefix + name]).hexdigest() == digest
                assert {(x['initial'], x['mode']) for x in r['results']} == {(i, m) for i in range(3) for m in range(2)}
                for x in r['results']:
                    text = logs[prefix + x['log']].decode()
                    prefix_pass = 'PASS g_quant_copy_a_joint' if with_g else 'PASS quant_copy_a_joint'
                    if with_window:
                        prefix_pass = 'PASS copy_window_a_joint'
                    if with_lookahead:
                        prefix_pass = 'PASS copy_lookahead_joint'
                    if with_distributed:
                        prefix_pass = 'PASS distributed_mid_joint tiles=86 down_sweeps=6'
                    suffix = ' extra_SRAM=0'
                    if with_lookahead:
                        suffix = ' two_live_pairs=6 overwritten_S_words=576' + suffix
                    elif with_window:
                        suffix = ' overwritten_S_words=576' + suffix
                    if with_distributed:
                        assert prefix_pass + ' cases=516 actual_banks=16 shared_header_data_wires=1 A_uses=3096 two_live_pairs=258 overwritten_S_words=24768 directory_entries=86 private_S_bytes=16384 extra_SRAM=0' in text
                    else:
                        assert prefix_pass + ' cases=12 actual_banks=16 shared_header_data_wires=1 A_uses=72' + suffix in text
                    event_name = 'G_COPY_A_REAL_S ' if with_g else 'COPY_A_REAL_S '
                    if with_window:
                        event_name = 'COPY_WINDOW_REAL_S '
                    if with_lookahead:
                        event_name = 'COPY_LOOKAHEAD_REAL_S '
                    if with_distributed:
                        event_name = 'DISTRIBUTED_MID_REAL_S '
                    events = [line for line in text.splitlines() if line.startswith(event_name)]
                    assert len(events) == (516 if with_distributed else 12)
                    for i, event in enumerate(events):
                        fields = dict(v.split('=') for v in event.split()[1:])
                        assert int(fields['case']) == i and int(fields['mode']) == x['mode']
                        expected_uses = (12 if i % 2 else 0) if with_lookahead or with_distributed else 6
                        assert [int(fields[k]) for k in ('headers', 'U_reads', 'P_writes', 'A_reads', 'A_uses')] == [6, 16, 48, 48, expected_uses]
                        assert int(fields.get('total_cycle', fields.get('cycle', 0))) > 0
                        if with_g and row['job'] >= 102319:
                            assert [int(fields[k]) for k in ('G_reads','G_writes','G_ACK','G_packets')] == [64,32,96,64]
                            assert int(fields['total_cycle']) > int(fields['quant_copy_a_cycle']) > 0
        else:
            assert not reports
            assert any(b'Cannot find file' in v or b'%Warning' in v or b'copy terminal conservation' in v or b'Too many digits for 32 bit number' in v or b'window test must retain live internal A leases' in v or b'A load identity' in v or b'COPY/S/A watchdog' in v
                       for k, v in logs.items() if k.endswith('.log'))
        rows.append(dict(job=row['job'], state=row['state'], trials=sum(len(r['results']) for r in reports)))
    return dict(passed=True, runs=rows, qualification='Functional actual S/COPY/A only, not MC/LC/M or 300MHz')


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--receipt-cache', type=Path)
    args = p.parse_args()
    print(json.dumps(audit(args.root, args.receipt_cache)))
