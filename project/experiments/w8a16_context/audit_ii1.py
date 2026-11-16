"""Independently audit source/receipts and actual RF accept/retire time lines."""
import argparse
import base64
import csv
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import tarfile


def unpack(data):
    with tarfile.open(fileobj=io.BytesIO(data), mode='r:gz') as archive:
        files = {}
        for m in archive:
            assert m.isfile() and not PurePosixPath(m.name).is_absolute() and '..' not in PurePosixPath(m.name).parts
            files[m.name] = archive.extractfile(m).read()
        return files


def audit(run):
    receipt = json.loads((run / 'recovery.json').read_text(encoding='utf-8'))
    assert 'COMPLETED' in receipt['sacct'] and 'FAILED' not in receipt['sacct']
    if (run / 'receipts-parts.json').exists():
        manifest = json.loads((run / 'receipts-parts.json').read_text(encoding='utf-8'))
        pieces = []
        for part in manifest['parts']:
            data = (run / part['path']).read_bytes()
            assert len(data) == part['bytes'] and hashlib.sha256(data).hexdigest() == part['sha256']
            pieces.append(data)
        encoded = b''.join(pieces)
        assert hashlib.sha256(encoded).hexdigest() == manifest['base64_sha256']
    else:
        encoded = (run / 'receipts.tar.gz.b64').read_bytes()
    raw = base64.b64decode(encoded, validate=True)
    assert hashlib.sha256(raw).hexdigest() == receipt['receipts_sha256']
    logs = unpack(raw)
    assert {p: hashlib.sha256(v).hexdigest() for p, v in logs.items()} == receipt['members']
    raw_source = (run / 'source.tar.gz').read_bytes()
    assert hashlib.sha256(raw_source).hexdigest() == receipt['package_sha256']
    source = unpack(raw_source)
    assert source['source/source-commit.txt'].decode().strip() == receipt['source_commit']
    for row in source['source.sha256'].decode().splitlines():
        sha, path = row.split('  ', 1)
        assert hashlib.sha256(source['source/'+path]).hexdigest() == sha
    rows = []
    for seed in range(25001, 25007):
        prefix = f'seed-{seed}/'
        result = json.loads(logs[prefix+'result.json'])
        assert result['seed'] == seed and result['initializations'] == 3
        assert result['finite_pipeline_owners'] == 3 and result['same_owner_head_II'] == 1
        for path, sha in result['hashes'].items():
            assert hashlib.sha256(logs[prefix+path]).hexdigest() == sha
        assert b'%Warning' not in logs[prefix+'build.log'] and b'%Warning' not in logs[prefix+'scale-build.log']
        for initial in range(3):
            events = list(csv.reader(logs[prefix+f'context-timing-{initial}.csv'].decode().splitlines()))
            accepted = [r for r in events if r[0] == 'ACCEPT']
            retired = [r for r in events if r[0] == 'RETIRE']
            assert len(accepted) == len(retired) == result['vectors']
            assert [int(r[2]) for r in accepted] == [int(r[2]) for r in retired] == list(range(result['vectors']))
            at = {r[2]: r for r in accepted}
            for r in retired:
                assert int(r[1])-int(at[r[2]][1]) >= (3 if at[r[2]][3] == '2' else 1)
            head_chains = 0
            for start in range(len(accepted)-7):
                chain = accepted[start:start+8]
                if all(r[3] == '2' and r[6] == '16' and int(r[5]) == 16*i and int(r[1]) == int(chain[0][1])+i for i, r in enumerate(chain)):
                    result_chain = retired[start:start+8]
                    assert all(int(r[1]) == int(result_chain[0][1])+i for i, r in enumerate(result_chain))
                    head_chains += 1
            assert head_chains > 0
            increments = {}
            for r in accepted: increments[int(r[1])] = increments.get(int(r[1]), 0)+1
            for r in retired: increments[int(r[1])] = increments.get(int(r[1]), 0)-1
            live = peak = 0
            for cycle, increment in sorted(increments.items()):
                live += increment;peak = max(peak, live)
                assert 0 <= live <= 3
            assert live == 0 and peak == 3
            name = 'simulation.log' if initial == 0 else f'simulation-{initial}.log'
            assert b'peak_head_run=8 peak_inflight=3' in logs[prefix+name]
            scale_name = 'scale-simulation.log' if initial == 0 else f'scale-simulation-{initial}.log'
            assert b'PASS scale ' in logs[prefix+scale_name]
            rows.append(dict(seed=seed, initial=initial, commands=result['vectors'], II1_head_chains=head_chains, max_packet_owners=peak))
    return dict(passed=True, source_commit=receipt['source_commit'], job=int(receipt['submit'].split()[-1]),
                context_runs=len(rows), standalone_scale_runs=len(rows), rows=rows,
                new_SRAM_bytes=0, arithmetic_metadata_pipeline_bits=930,
                qualification='finite RF/scale unit only; actual full-M/guard and 300MHz physical qualification separate')


if __name__ == '__main__':
    p = argparse.ArgumentParser();p.add_argument('--run', type=Path, required=True)
    args = p.parse_args();result = audit(args.run)
    (args.run / 'audit.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({k: v for k,v in result.items() if k != 'rows'}))
