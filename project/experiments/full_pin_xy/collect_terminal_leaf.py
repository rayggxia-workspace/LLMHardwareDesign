"""Small additive terminal receipt; no new P&R and no old snapshot replacement."""
from pathlib import Path
import argparse,datetime,gzip,hashlib,json,tarfile
ROOT=Path('/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027')


def collect(case,revision,name):
    assert case in ['act','mxu','opentpu_aux','gemm','vector','llaccel_aux']
    assert all(v.replace('-','').isalnum() for v in [revision,name])
    leaf=case+'-C';trial=ROOT/'trials'/revision/leaf;final=ROOT/'finalized'/revision/leaf
    a=json.loads((trial/'execution.json').read_text());b=json.loads((final/'execution.json').read_text());assert a.get('finished_utc')
    out=ROOT/'terminal_updates'/name;out.mkdir(parents=True,exist_ok=False);records=[]
    for directory,names in [(trial,['execution.json','timing.setup.txt','timing.hold.txt','timing.checks.txt','stages.tsv','before.pins.tsv','after.pins.tsv']),
                            (final,['execution.json','pins.tsv','independent.drc','drc.log','whole_access.json','selected_access.json','technology.tsv'])]:
        for filename in names:
            p=directory/filename
            if not p.exists():continue
            stat=p.stat();content=p.read_bytes();assert stat.st_size==p.stat().st_size and stat.st_mtime_ns==p.stat().st_mtime_ns
            rel=p.relative_to(ROOT).as_posix()+'.gz';dest=out/rel;dest.parent.mkdir(parents=True,exist_ok=True)
            with dest.open('xb') as raw,gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=0) as f:f.write(content)
            records.append({'source':str(p),'relative':rel,'bytes':len(content),'sha256':hashlib.sha256(content).hexdigest(),'stored_sha256':hashlib.sha256(dest.read_bytes()).hexdigest()})
    index={'case':case,'revision':revision,'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
           'scope':'ADDITIVE_TERMINAL_RECEIPTS_ONLY_NOT_FULL_PHYSICAL_QUALIFICATION','records':records,
           'source_original_trial_job':a.get('scheduler_job'),'independent_job':b.get('scheduler_job'),
           'native_DRC_count':b.get('independent_DRC_count'),'whole_geometry':b.get('whole_access',{}).get('pass'),'full_qualification':False}
    (out/'index.json').write_text(json.dumps(index,indent=2)+'\n')
    with tarfile.open(str(out)+'.tar.gz','x:gz') as t:t.add(str(out),arcname=name)
    print(str(out)+'.tar.gz')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('case');p.add_argument('revision');p.add_argument('name');a=p.parse_args();collect(a.case,a.revision,a.name)
