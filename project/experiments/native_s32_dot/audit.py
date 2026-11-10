"""Offline source/member/Slurm/RTL receipt audit, without re-running numerics."""
import argparse
import base64
import hashlib
import io
import json
from pathlib import Path
import re
import tarfile


def unpack(raw):
    with tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz') as archive:
        return {m.name:archive.extractfile(m).read() for m in archive if m.isfile()}


def audit(directory):
    receipt=json.loads((directory/'recovery.json').read_text())
    pieces=[]
    for part in receipt['parts']:
        data=(directory/part['path']).read_bytes();assert hashlib.sha256(data).hexdigest()==part['sha256'];pieces.append(data)
    raw=base64.b64decode(b''.join(pieces),validate=True)
    assert hashlib.sha256(raw).hexdigest()==receipt['receipts_archive_sha256']
    files=unpack(raw)
    assert {k:hashlib.sha256(v).hexdigest() for k,v in files.items()}==receipt['members']
    source=(directory/'source.tar.gz').read_bytes()
    assert hashlib.sha256(source).hexdigest()==receipt['source_archive_sha256']
    sources=unpack(source)
    for line in sources['source.sha256'].decode().splitlines():
        digest,name=line.split('  ',1);assert hashlib.sha256(sources[name]).hexdigest()==digest
    assert sources['source-commit.txt'].decode().strip()==receipt['source_commit']
    rows=[]
    for seed in range(25201,25207):
        prefix='seed-%d/'%seed
        if prefix+'result.json' not in files:continue
        result=json.loads(files[prefix+'result.json']);assert result['seed']==seed
        assert result['job']==receipt['job'] and len(result['affinity'])==10
        assert hashlib.sha256(files[prefix+'core.txt']).hexdigest()==result['vectors_sha256']
        if not result['passed']:
            assert b'%Error' in files[prefix+'build.log']
            continue
        assert '%Warning' not in files[prefix+'build.log'].decode(errors='replace')
        for init in range(3):
            log=files[prefix+'core-%d.log'%init].decode()
            match=re.search(r'PASS native32 core accepted=(\d+) returned=(\d+) flushed=(\d+) held=(\d+) cancel_wait=(\d+) cycles=(\d+)',log)
            assert match and 'Error' not in log
            accepted,returned,flushed,held,cancel_wait,cycles=map(int,match.groups())
            assert accepted==result['commands'] and returned+flushed==accepted and held>0 and cancel_wait>0
            rows.append(dict(seed=seed,initial=init,accepted=accepted,returned=returned,flushed=flushed,held=held,cancel_wait=cancel_wait,cycles=cycles))
    success=len(rows)==18
    if not success:
        assert any(b'%Error' in data for name,data in files.items() if name.endswith('build.log'))
    result=dict(passed=success,expected_failure=not success,job=receipt['job'],source_commit=receipt['source_commit'],
                source_archive_sha256=receipt['source_archive_sha256'],receipts_archive_sha256=receipt['receipts_archive_sha256'],rows=rows,
                qualification='Core numerical/RTL candidate only; S frontend, system timing, area and physical acceptance remain unsupported.')
    (directory/'audit.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);r=audit(p.parse_args().run)
    print(json.dumps(dict(passed=r['passed'],expected_failure=r['expected_failure'],job=r['job'],rows=len(r['rows']))))
