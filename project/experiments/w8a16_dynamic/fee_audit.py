"""Audit the reused-binary N8 layout experiment from recovered bytes only."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import tarfile
from recover import receipts


def audit(run):
    recovery,files=receipts(run)
    assert 'COMPLETED' in recovery['sacct'] and 'FAILED' not in recovery['sacct']
    raw=(run/'source.tar.gz').read_bytes()
    assert hashlib.sha256(raw).hexdigest()==recovery['source_archive_sha256']
    with tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz') as archive:
        sources={m.name:archive.extractfile(m).read() for m in archive if m.isfile()}
    for line in sources['source.sha256'].decode().splitlines():
        sha,path=line.split('  ',1);assert hashlib.sha256(sources[path]).hexdigest()==sha
    rows=[]
    for seed in range(25001,25007):
        prefix=f'fees-{seed}/';report=json.loads(files[prefix+'result.json'])
        assert report['passed'] and len(report['runs'])==6
        assert report['M_provider']['commit']=='f08aefb93df071535f461da24b6829c5949bf5bf'
        vector=files[prefix+'vectors.txt'];assert hashlib.sha256(vector).hexdigest()==report['vector_sha256']
        lines=iter(vector.decode().splitlines());expected=[];shapes=[]
        for header in lines:
            k,n,shift,major=map(int,header.split());shapes.append([k,n,shift,major])
            for _ in range(k+k*n+1):next(lines)
            expected.extend(int(next(lines),16) for _ in range(((k+127)//128)*15))
        assert shapes==[[128,8,24,0],[128,8,24,1],[512,8,24,1]] and len(expected)==90
        for measured in report['runs']:
            data=files[prefix+measured['log']];assert hashlib.sha256(data).hexdigest()==measured['sha256']
            log=data.decode();assert '%Error' not in log and 'PASS dynamic_product cases=3 partials=90 ' in log
            raw=[int(v,16) for v in re.findall(r'JOINT_RAW cycle=\d+ record=\d+ value=([0-9a-f]+)',log)]
            assert raw==expected
            req=re.findall(r'JOINT_S_REQ cycle=(\d+) owner=(\d+) address=(\d+)',log)
            ack=re.findall(r'JOINT_S_ACK cycle=(\d+)',log)
            assert len(req)==len(ack)==25920 and all(int(a)<1024 for _,_,a in req)
            assert all(int(b)>=int(a)+2 for (a,_,_),b in zip(req,ack))
            returns=re.findall(r'JOINT_LOCAL_MC_RETURN cycle=\d+ tag=(\d+)',log)
            offers=re.findall(r'JOINT_LOCAL_MC_REQ cycle=\d+ channel=\d+ tag=(\d+)',log)
            assert offers==returns and len(returns)==1530
            assert log.count('final=1 address=300')==3 and log.count('final=1 address=301')==3
            cost=measured['record_costs'];assert len(cost)==90
            assert all(r['partial_to_raw']==r['begin_to_raw']+2 for r in cost)
            if measured['ideal']:assert all(r['begin_to_raw']==1256 for r in cost)
            rows.append(dict(seed=seed,initial=measured['initial'],ideal=measured['ideal'],
                minimum=min(r['begin_to_raw'] for r in cost),maximum=max(r['begin_to_raw'] for r in cost),
                binary_sha256=report['binary_sha256']))
    return dict(passed=True,job=recovery['job'],archive_sha256=recovery['archive_sha256'],rows=rows,
                full_N8_QK_AV_BEGIN_to_raw_ideal_cycles=1256,
                source='Actual unchanged Slurm102326 M binary f08 plus actual fourbank S and typed LOCAL_S_PACK64',
                qualification='Synthetic enlarged N8/K512 shapes built from real B1/S2 witness. Not actual decode512 tensors, deployed LC program, wholemodel quality or physical qualification.')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);args=p.parse_args()
    result=audit(args.run);(args.run/'audit.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(passed=True,job=result['job'],runs=len(result['rows']),ideal_cycles=1256)))
