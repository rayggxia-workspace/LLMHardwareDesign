"""Bounded, immutable resume snapshot; running jobs are never counted as passes."""
from pathlib import Path
import argparse,datetime,gzip,hashlib,json,subprocess,tarfile

ROOT=Path('/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027')
JOBS=['92690','92691','92700','92706','92707','92714','92721','92747','92748',
      '92749','92751','92752','92753','92757','92758','92759','92761','92762']


def collect(name,extra_jobs):
    assert name.replace('-','').isalnum() and all(j.isdigit() for j in extra_jobs)
    out=ROOT/'resume_snapshots'/name;out.mkdir(parents=True,exist_ok=False)
    patterns=['constraint_audit/r0*/*/*','constraint_audit/r0*/execution.json',
              'constraint_audit/r0*/installed_GRT_source_excerpt.txt',
              'escape_spacing_reroute/r02/act-C/*','escape_spacing_reroute/r03/act-C/*',
              'trials/local-patch-r01/llaccel_aux-C/*','finalized/local-patch-r01/llaccel_aux-C/*',
              'inputs/ll-local-patch-r01/*','leaf_eco/r0[3456789]/*/*','eco_views/r0[12]/*/*',
              'logs/rc-aware-eco-r07-*.log','logs/native-grt-eco-r08-*.log',
              'logs/isolated-vector-eco-r09-*.log','logs/costed-eco-view-*-r0[12]-*.log',
              'checkpoint_legalization/r0[12]/*','logs/checkpoint-legalization-r0[12]-*.log',
              'checkpoint_route/r01/*','logs/checkpoint-route-r01-*.log']
    paths=set(p for pattern in patterns for p in ROOT.glob(pattern) if p.is_file())
    paths.update(ROOT/'logs'/n for n in ['local-patch-r01-92747.log','local-patch-qual-r01-92748.log',
         'constraint-audit-r01-92749.log','constraint-audit-r02-92751.log','constraint-audit-r03-92752.log',
         'constraint-audit-r04-92753.log','targeted-cap-r03-92757.log','targeted-cap-r04-92758.log',
         'constraint-audit-r05-92759.log','targeted-cap-r05-92761.log','rc-aware-eco-r06-92762.log'])
    records=[]
    for p in sorted(paths):
        if not p.is_file():continue
        stat=p.stat();r={'source':str(p),'source_bytes':stat.st_size}
        # Never duplicate DB/SPEF/whole-connectivity geometry or huge cell tables.
        keep=p.suffix in ['.json','.txt','.tcl','.csv','.tsv','.log','.drc']
        keep=keep and not any(w in p.name for w in ['.cells.','.cell_cost.','.pdn.','paths.json','whole_access.tsv','selected_access.tsv'])
        keep=keep and stat.st_size<=6*1024*1024
        if not keep:r['storage']='REMOTE_ONLY_INDEXED';records.append(r);continue
        raw=p.read_bytes();after=p.stat()
        if (stat.st_size,stat.st_mtime_ns)!=(after.st_size,after.st_mtime_ns):
            r['storage']='CHANGING_ACTIVE_FILE_OMITTED';records.append(r);continue
        rel=p.relative_to(ROOT).as_posix()+'.gz';dest=out/rel;dest.parent.mkdir(parents=True,exist_ok=True)
        with dest.open('xb') as f,gzip.GzipFile(filename='',mode='wb',fileobj=f,mtime=0) as stream:stream.write(raw)
        r.update({'storage':'LOSSLESS_SNAPSHOT','relative':rel,'sha256':hashlib.sha256(raw).hexdigest(),
                  'stored_sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),
                  'note':'Stable during read only; an in-flight snapshot is not a terminal receipt.'})
        records.append(r)
    jobs=JOBS+extra_jobs
    command=['sacct','-j',','.join(jobs),'--parsable2','--format=JobIDRaw,JobName,State,Elapsed,ExitCode']
    scheduler=subprocess.check_output(command).decode()
    (out/'scheduler.tsv').write_text(scheduler)
    meta={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_root':str(ROOT),
          'scope':'RESUME_INCREMENTAL_EVIDENCE_NOT_PHYSICAL_QUALIFICATION','full_qualification':False,
          'scheduler_command':command,'records':records}
    (out/'snapshot.json').write_text(json.dumps(meta,indent=2)+'\n')
    with tarfile.open(str(out)+'.tar.gz','x:gz') as f:f.add(str(out),arcname=name)
    print('RESUME_SNAPSHOT',str(out)+'.tar.gz',len(records),'indexed files')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('name');p.add_argument('jobs',nargs='*');a=p.parse_args();collect(a.name,a.jobs)
