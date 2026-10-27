from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import os,sys,subprocess,json,re
from run_exports import ROOT,CFG,IMAGE,BIN,sha
DRIVER=Path(__file__).resolve().parent
def one(case,rev,plan):
    src=Path(CFG['physical_blocks'][case]['odb']) if plan=='SOURCE' else ROOT/'trials'/rev/(case+'-'+plan)/'checked.odb'
    if not src.exists():print('NOT_READY',src,flush=True);return
    before=sha(src);out=ROOT/'independent_drc'/rev/(case+'-'+plan);out.mkdir(parents=True,exist_ok=False)
    env='PINXY_DRC_ODB={},PINXY_TOP_LAYER={},PINXY_DRC_OUT={}'.format(src,8 if case.endswith('_aux') else 10,out/'independent.drc')
    cmd=['singularity','exec','--cleanenv','--bind','/public/home/yuzelu/project-circuit:/public/home/yuzelu/project-circuit:ro',
        '--bind','/public/home/yuzelu/PingyangHuang/issue-55:/public/home/yuzelu/PingyangHuang/issue-55:ro','--home',str(ROOT/'home'),'--pwd',str(out),'--env',env,IMAGE,BIN,'-threads','1','-exit',str(DRIVER/'independent_drc.tcl')]
    with (out/'openroad.log').open('x') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
    assert before==sha(src)
    drc=out/'independent.drc';text=drc.read_text() if drc.exists() else ''
    count=len(re.findall(r'^violation type:',text,re.M)) if drc.exists() else None
    rec={'source_odb':str(src),'source_sha256':before,'source_unchanged':True,'scheduler_job':os.environ['SLURM_JOB_ID'],'returncode':r.returncode,
        'new_process':True,'routing_layers':'signal metal2-metal{}; clock metal4-metal{}'.format(8 if case.endswith('_aux') else 10,8 if case.endswith('_aux') else 10),'native_DRC_count':count,
        'command':cmd,'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),'report_sha256':sha(drc) if drc.exists() else None}
    (out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n');print('INDEPENDENT_DRC',case,rev,plan,r.returncode,count,flush=True)
if __name__=='__main__':
    case,rev=sys.argv[1:3];plans=sys.argv[3:]
    with ThreadPoolExecutor(max_workers=2) as pool:list(pool.map(lambda p:one(case,rev,p),plans))
