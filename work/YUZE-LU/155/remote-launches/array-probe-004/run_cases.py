import concurrent.futures,subprocess,os,json,time
from pathlib import Path
out=Path.cwd();cases=[('min',0.2091,0.005),('max',6.6912,0.16)]
def run(case):
 name,load,slew=case;env=os.environ.copy();env['OPENRAM_TMP']=str(out/('tmp-'+name));Path(env['OPENRAM_TMP']).mkdir(exist_ok=False)
 cmd=['python3','-u','source/project/experiments/s_sram/diagnose_array.py','--words-per-row','2','--stages','25','--load-ff',str(load),'--slew-ns',str(slew),'--out',str(out/name)]
 t=time.monotonic()
 with (out/(name+'-launch.log')).open('w') as f:p=subprocess.run(cmd,env=env,stdout=f,stderr=subprocess.STDOUT)
 r=dict(case=name,returncode=p.returncode,seconds=time.monotonic()-t)
 (out/(name+'-execution.json')).write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True);return r
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(run,cases))
(out/'execution.json').write_text(json.dumps(dict(scope='Execution only, not physical qualification',results=results),indent=2)+'\n')
