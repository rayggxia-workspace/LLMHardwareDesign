"""Immutable bounded evidence for GDS import/deck and current physical gates."""
from pathlib import Path
import argparse,datetime,gzip,hashlib,json,subprocess,tarfile

ROOT=Path('/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027')
JOBS=['92690','92691','92700','92714','92721','92781','92783','92792','92794','92795','92798']


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(4*1024*1024),b''):h.update(chunk)
    return h.hexdigest()


def collect(name):
    assert name.replace('-','').isalnum()
    out=ROOT/'gate_milestones'/name;out.mkdir(parents=True,exist_ok=False)
    patterns=['streamout/costed-r0[12]/*/*','streamout/costed-r0[12]/pack.json',
      'tool_api/streamout-reader-r0[123]/*','logs/streamout-reader-api-r0[123]-*.log',
      'logs/costed-gds-r0[12]-*.log','logs/stream-pack-costed-r0[12]-*.log',
      'checkpoint_route/r01/*','trials/access-r03/llaccel_aux-C/execution.json',
      'trials/access-r03/llaccel_aux-C/stages.tsv','finalized/access-r03/llaccel_aux-C/*',
      'escape_fixtures/gemm-r01/*/execution.json','escape_fixtures/gemm-r02/*/execution.json',
      'escape_fixtures/mxu-r01/*/execution.json']
    records=[]
    for p in sorted(set(p for pattern in patterns for p in ROOT.glob(pattern) if p.is_file())):
        a=p.stat();r={'source':str(p),'bytes':a.st_size}
        keep=p.suffix in ['.json','.log','.tcl','.txt','.tsv','.csv','.drc','.lyt'] and a.st_size<=8*1024*1024
        keep=keep and not any(s in p.name for s in ['.cells.','.pdn.','whole_access.tsv','selected_access.tsv','paths.json'])
        if not keep:
            r['storage']='REMOTE_ONLY_INDEXED'
            # Finished execution receipts already index their large output SHA;
            # don't hash a live multi-GB ODB/GDS or copy it into Git.
            records.append(r);continue
        raw=p.read_bytes();b=p.stat()
        if (a.st_size,a.st_mtime_ns)!=(b.st_size,b.st_mtime_ns):
            r['storage']='CHANGING_ACTIVE_FILE_OMITTED';records.append(r);continue
        rel=p.relative_to(ROOT).as_posix()+'.gz';q=out/rel;q.parent.mkdir(parents=True,exist_ok=True)
        with q.open('xb') as f,gzip.GzipFile(filename='',mode='wb',fileobj=f,mtime=0) as z:z.write(raw)
        r.update({'storage':'LOSSLESS_SNAPSHOT','relative':rel,'sha256':hashlib.sha256(raw).hexdigest(),'stored_sha256':sha(q)})
        records.append(r)
    scheduler=subprocess.check_output(['sacct','-j',','.join(JOBS),'--parsable2','--format=JobIDRaw,JobName,State,Elapsed,ExitCode']).decode()
    (out/'scheduler.tsv').write_text(scheduler)
    meta={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_root':str(ROOT),
      'scope':'GATE_EVIDENCE_NOT_FULL_PHYSICAL_QUALIFICATION','full_qualification':False,
      'records':records,'running_snapshot_not_terminal_evidence':True}
    (out/'snapshot.json').write_text(json.dumps(meta,indent=2)+'\n')
    with tarfile.open(str(out)+'.tar.gz','x:gz') as f:f.add(str(out),arcname=name)
    print('GATE_MILESTONE',str(out)+'.tar.gz',len(records),'indexed files')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('name');a=p.parse_args();collect(a.name)
