"""Read frozen source databases in a new allocation; never mutate a source database."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import subprocess,os,json,hashlib,gzip,datetime

ROOT=Path.cwd().resolve()
ALLOWED=Path('/public/home/yuzelu/PingyangHuang').resolve()
assert ALLOWED in ROOT.parents and ROOT.name=='full-pin-20261027'
CFG=json.loads((ROOT/'inputs/sources.json').read_text())
IMAGE='/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif'
BIN='/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad'
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for chunk in iter(lambda:f.read(4*1024*1024),b''):h.update(chunk)
    return h.hexdigest()
def command(cid,src,script):
    return ['singularity','exec','--cleanenv','--bind','/public/home/yuzelu/project-circuit:/public/home/yuzelu/project-circuit:ro',
            '--bind','/public/home/yuzelu/PingyangHuang/issue-55:/public/home/yuzelu/PingyangHuang/issue-55:ro',
            '--home',str(ROOT/'home'),'--pwd',str(ROOT),'--env',f'PINXY_CASE={cid},PINXY_ODB={src},OMP_NUM_THREADS=1,PYTHONDONTWRITEBYTECODE=1',
            IMAGE,BIN,'-threads','1','-no_init','-exit',str(ROOT/'code'/script)]
def one(cid):
    spec=CFG['physical_blocks'][cid];src=Path(spec['odb']);st=src.stat();observed=sha(src)
    assert observed==spec['expected_sha256'],(cid,'source hash changed')
    receipt={'case':cid,'source':str(src),'source_sha256':observed,'source_stat':[st.st_size,st.st_mtime_ns,st.st_ino],
             'scheduler_job':os.environ['SLURM_JOB_ID'],'allocation_cpus':os.environ.get('SLURM_CPUS_PER_TASK'),'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    for script in ['export_odb.tcl','export_anchors.tcl']:
        log=ROOT/'logs'/f'{cid}-{script}.log'
        with log.open('x') as f:subprocess.run(command(cid,src,script),stdout=f,stderr=subprocess.STDOUT,check=True)
        text=log.read_text();assert 'EXPORT_COMPLETE' in text or 'ANCHORS_COMPLETE' in text,(cid,script,text[-1000:])
    st2=src.stat();assert (st.st_size,st.st_mtime_ns,st.st_ino)==(st2.st_size,st2.st_mtime_ns,st2.st_ino)
    out=ROOT/'exports'/cid;receipt['outputs']={}
    for p in out.glob('*.tsv'):
        dest=p.with_suffix('.tsv.gz')
        with p.open('rb') as inp,dest.open('xb') as raw,gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=0) as dst:
            for chunk in iter(lambda:inp.read(4*1024*1024),b''):dst.write(chunk)
        receipt['outputs'][dest.name]={'bytes':dest.stat().st_size,'sha256':sha(dest)}
    receipt['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();receipt['status']='PASS_READONLY_EXTRACTION_ONLY'
    (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');return cid

if __name__=='__main__':
    ids=[c for c,s in CFG['physical_blocks'].items() if not s['reuse_existing_candidates']]
    with ThreadPoolExecutor(max_workers=2) as pool:
        for c in pool.map(one,ids):print('EXPORTED',c,flush=True)
    spec=CFG['physical_blocks']['mxu']
    with (ROOT/'logs/tool-probe.log').open('x') as f:subprocess.run(command('probe',spec['odb'],'tool_probe.tcl'),stdout=f,stderr=subprocess.STDOUT,check=True)
    print('ALL_READONLY_EXPORTS_COMPLETE',flush=True)
