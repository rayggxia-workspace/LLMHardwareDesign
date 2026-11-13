"""Read-only source/hash/conservation audit of the actual S32 ring copier."""
import argparse
import hashlib
import json
from pathlib import Path
from audit_p_scope import unpack


def audit(root, receipt_cache=None):
    rows = []
    for row in json.loads((root / 'index.json').read_text(encoding='utf-8'))['runs']:
        source, logs = (unpack(root, row, kind, receipt_cache) for kind in ('source', 'receipts'))
        assert source['source/source-commit.txt'].decode().strip() == row['source_commit']
        for name, digest in json.loads(logs['receipts-manifest.json']).items():
            assert hashlib.sha256(logs[name]).hexdigest() == digest
        for line in logs['source.sha256'].decode().splitlines():
            digest, name = line.split('  ', 1)
            assert hashlib.sha256(source['source/' + name]).hexdigest() == digest
        reports = [json.loads(v) for k, v in logs.items() if k.endswith('/result.json')]
        if row['state'] == 'COMPLETED':
            assert len(reports) == 6 and {r['seed'] for r in reports} == set(range(25001, 25007))
            for r in reports:
                prefix = f"seed-{r['seed']}/"
                assert b'%Warning' not in logs[prefix + 'build.log']
                for name, digest in r['hashes'].items():
                    assert hashlib.sha256(logs[prefix + name]).hexdigest() == digest
                same_modes = (0, 1) if 'same_s' in r['results'][0] else (0,)
                assert {(x.get('same_s', 0), x['mode'], x['initial']) for x in r['results']} == {
                    (same, m, i) for same in same_modes for m in range(2) for i in range(3)}
                for x in r['results']:
                    text = logs[prefix + x['log']].decode()
                    banks = 4 if x.get('same_s') == 1 else 8
                    assert f'PASS s32_stripe_joint legal=28 bad=2 actual_banks={banks} extra_SRAM=0' in text
                    if banks == 4:
                        assert 'memories[1].storage' in text and 'memories[0].storage' not in text
                    events = [line for line in text.splitlines() if line.startswith('STRIPE_REAL_S ')]
                    assert len(events) == 28
                    for event in events:
                        f = dict(v.split('=') for v in event.split()[1:])
                        assert int(f.get('same_s', 0)) == x.get('same_s', 0)
                        assert int(f['mode']) == x['mode'] and int(f['case']) not in (27, 28)
                        assert 0 < int(f['words']) <= 16
                        assert int(f['words']) == int(f['reads']) == int(f['writes']) == int(f['ACK'])
                        assert int(f['cycles']) > 0
        else:
            assert not reports and b'%Warning-UNUSEDSIGNAL' in logs['seed-25001/build.log']
        rows.append(dict(job=row['job'], state=row['state'], trials=sum(len(r['results']) for r in reports)))
    return dict(passed=True, runs=rows, qualification='Actual finite stripe copier on one shared or two independent S ports; caller still owns G-consumer window lifetime, not full FFN or physical qualification')


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--receipt-cache', type=Path)
    args = p.parse_args()
    print(json.dumps(audit(args.root, args.receipt_cache)))
