import pathlib,subprocess,concurrent.futures,json
p=pathlib.Path(__file__).resolve().parent
assert json.loads((p/'sta-pilot-validation.json').read_text())['passed']
def run(i):
 with (p/'sta'/('worker-%d.log'%i)).open('w') as f:
  rc=subprocess.call(['/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad','-no_init','-threads','2','-exit',str(p/'sta'/('worker-%d.tcl'%i))],stdout=f,stderr=subprocess.STDOUT)
 return dict(worker=i,exit=rc)
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:result=list(pool.map(run,range(8)))
(p/'sta-all-status.json').write_text(json.dumps(result,indent=2));assert all(x['exit']==0 for x in result)
print('ALL_1292_STA_COMPLETE',flush=True)
