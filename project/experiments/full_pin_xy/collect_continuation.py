"""Snapshot bounded continuation evidence without altering jobs or physical sources.

Native databases/SPEF remain remotely indexed; exact text is losslessly gzipped.
Active/changed files are explicitly omitted, never interpreted as a passing run.
"""
from pathlib import Path
import argparse, datetime, gzip, hashlib, json, tarfile

ROOT=Path('/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027')


def collect(name):
    assert name.replace('-','').isalnum()
    out=ROOT/'continuation_snapshots'/name;out.mkdir(parents=True,exist_ok=False)
    paths=[]
    patterns=['trials/act-access-r03/*','finalized/act-access-r03/*','trials/access-r03/*','finalized/access-r03/*',
              'trials/llsys-pg-r03/*','finalized/llsys-pg-r03/*','escape_fixtures/r03/*','escape_fixtures/r04/*',
              'escape_pg_repair/*/*','escape_spacing_reroute/*/*','leaf_timing_models/r04/*',
              'upper_layer_probe/r01','upper_layer_probe/r01/model','upper_layer_validation/r01','leaf_diagnosis/r01/*',
              'escape_fixtures/gemm-r01/*','leaf_timing_models/r05/*',
              'parents/r07/*','parents/ll-r01/*','parent_rc_sta/r02/*']
    for pattern in patterns:paths.extend(p for p in ROOT.glob(pattern) if p.is_dir())
    records=[]
    for directory in sorted(set(paths)):
        for p in sorted(directory.iterdir()):
            if not p.is_file():continue
            stat=p.stat();rec={'source':str(p),'bytes':stat.st_size,'source_mtime_ns':stat.st_mtime_ns}
            suffix=p.suffix
            keep=suffix in ['.json','.txt','.tcl','.tsv','.csv','.log','.drc','.lib','.lef'] or p.name in ['whole_access.tsv.gz','access.tsv.gz']
            keep=keep and 'paths.json' not in p.name and 'fingerprint' not in p.name and stat.st_size<40*1024*1024
            if not keep:
                rec['storage']='REMOTE_ONLY_INDEXED';records.append(rec);continue
            content=p.read_bytes();after=p.stat()
            if (stat.st_mtime_ns,stat.st_size)!=(after.st_mtime_ns,after.st_size):
                rec['storage']='CHANGING_ACTIVE_FILE_OMITTED';records.append(rec);continue
            relative=p.relative_to(ROOT);dst=out/relative
            dst.parent.mkdir(parents=True,exist_ok=True)
            if suffix!='.gz':
                dst=dst.with_name(dst.name+'.gz')
                with dst.open('xb') as raw,gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=0) as stream:stream.write(content)
            else:dst.write_bytes(content)
            rec.update({'storage':'LOSSLESS_SNAPSHOT','relative':dst.relative_to(out).as_posix(),
                        'sha256':hashlib.sha256(content).hexdigest(),'stored_sha256':hashlib.sha256(dst.read_bytes()).hexdigest()})
            records.append(rec)
    metadata={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_root':str(ROOT),
              'scope':'Partial snapshot permitted; native execution receipts and terminal scheduler states are separate. No passing state inferred from file presence.',
              'records':records}
    (out/'snapshot.json').write_text(json.dumps(metadata,indent=2)+'\n')
    with tarfile.open(str(out)+'.tar.gz','x:gz') as archive:archive.add(str(out),arcname=name)
    print(str(out)+'.tar.gz',len(records),'indexed files')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('name');collect(p.parse_args().name)
