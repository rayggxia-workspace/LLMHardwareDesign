"""Independent whole-block conductor connectivity, input immutable."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import subprocess,os,json,sys
from run_exports import ROOT,IMAGE,BIN,sha
from check_access import check
DRIVER=Path(__file__).resolve().parent

def one(case,revision,plan):
    src=ROOT/'trials'/revision/(case+'-'+plan)/'checked.odb'
    if not src.exists():print('NOT_READY',src,flush=True);return
    before=sha(src);out=ROOT/'connectivity'/revision/(case+'-'+plan);out.mkdir(parents=True,exist_ok=False)
    dest=out/'whole_access.tsv.gz'
    env='PINXY_ODB={},PINXY_ACCESS_ALL=1,PINXY_ACCESS_OUT={}'.format(src,dest)
    cmd=['singularity','exec','--cleanenv','--home',str(ROOT/'home'),'--pwd',str(out),'--env',env,IMAGE,BIN,'-threads','1','-exit',str(DRIVER/'check_access_entry.tcl')]
    with (out/'export.log').open('x') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
    rec={'source_odb':str(src),'source_sha256':before,'source_unchanged':before==sha(src),'scheduler_job':os.environ['SLURM_JOB_ID'],'command':cmd,'returncode':r.returncode,'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip()}
    if r.returncode==0:
        result=check(dest,True);(out/'whole_access.json').write_text(json.dumps(result,indent=2)+'\n')
        rec['result']=result;rec['raw_export_sha256']=sha(dest)
    (out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n');print('WHOLE_CONNECTIVITY',case,plan,rec.get('result',{}).get('pass'),flush=True)
if __name__=='__main__':
    case,rev=sys.argv[1:3];plans=sys.argv[3:] or ['A','C']
    with ThreadPoolExecutor(max_workers=2) as pool:list(pool.map(lambda p:one(case,rev,p),plans))
