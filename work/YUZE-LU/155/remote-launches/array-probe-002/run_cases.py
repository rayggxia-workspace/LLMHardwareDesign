import concurrent.futures,subprocess,os,json,time
from pathlib import Path
out=Path.cwd();cases=[(2,9),(2,31),(4,31)]
def run(case):
 wpr,stages=case;name='wpr%d-stages%d'%case;env=os.environ.copy();env['OPENRAM_TMP']=str(out/('tmp-'+name));Path(env['OPENRAM_TMP']).mkdir(exist_ok=False)
 cmd=['python3','-u','source/project/experiments/s_sram/diagnose_array.py','--words-per-row',str(wpr),'--stages',str(stages),'--out',str(out/name)]
 t=time.monotonic()
 with (out/(name+'-launch.log')).open('w') as f:p=subprocess.run(cmd,env=env,stdout=f,stderr=subprocess.STDOUT)
 r=dict(case=name,returncode=p.returncode,seconds=time.monotonic()-t)
 (out/(name+'-execution.json')).write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True);return r
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:results=list(pool.map(run,cases))
(out/'execution.json').write_text(json.dumps(dict(scope='Execution only; select cases only from native and independent checks',results=results),indent=2)+'\n')
