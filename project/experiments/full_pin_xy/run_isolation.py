from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import os,subprocess,json,re
from run_exports import ROOT,CFG,IMAGE,BIN,sha
DRIVER=Path(__file__).resolve().parent
out=ROOT/'isolation/r01/act';out.mkdir(parents=True,exist_ok=False)
src=Path(CFG['physical_blocks']['act']['odb']);source_hash=sha(src)
common=['singularity','exec','--cleanenv','--bind','/public/home/yuzelu/project-circuit:/public/home/yuzelu/project-circuit:ro','--home',str(ROOT/'home'),'--pwd',str(out)]
env='PINXY_ODB={},PINXY_ISOLATION_OUT={},PINXY_LIBS_TCL={},PINXY_SDC={},PINXY_DRIVER={},PINXY_RELOCATIONS={}'.format(src,out,ROOT/'trials/r02/act-A/libs.tcl',src.parent/'6_final.sdc',DRIVER,ROOT/'inputs/trial-inputs-r04/act-A.tcl')
for mode in ['NO_LIB','WITH_LIB']:
    with (out/(mode+'.log')).open('x') as f:subprocess.run(common+['--env',env+',PINXY_ISOLATION_MODE='+mode,IMAGE,BIN,'-threads','1','-exit',str(DRIVER/'isolate_database_stages.tcl')],stdout=f,stderr=subprocess.STDOUT,check=True)
def one(p):
    dest=out/(p.stem+'.independent.drc')
    en='PINXY_DRC_ODB={},PINXY_TOP_LAYER=10,PINXY_DRC_OUT={}'.format(p,dest)
    with (out/(p.stem+'.drc.log')).open('x') as f:r=subprocess.run(common+['--env',en,IMAGE,BIN,'-threads','1','-exit',str(DRIVER/'independent_drc.tcl')],stdout=f,stderr=subprocess.STDOUT)
    count=len(re.findall(r'^violation type:',dest.read_text(),re.M)) if dest.exists() else None
    return p.name,{'returncode':r.returncode,'DRC_count':count,'odb_sha256':sha(p),'tech_sha256':sha(p.with_suffix('.tech.tsv')),'access_sha256':sha(out/(p.stem+'.access.tsv'))}
with ThreadPoolExecutor(max_workers=2) as pool:result=dict(pool.map(one,sorted(out.glob('*.odb'))))
assert sha(src)==source_hash
rec={'source':str(src),'source_sha256':source_hash,'source_unchanged':True,'scheduler_job':os.environ['SLURM_JOB_ID'],'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),'stages':result}
(out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n');print(json.dumps(result,indent=2),flush=True)
