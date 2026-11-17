import pathlib,json,subprocess,concurrent.futures,os
p=pathlib.Path(__file__).resolve().parent;g=json.loads((p/'graphs.json').read_text())
selected=['A-n14653','A-n14598','B-n14653','B-n14598','B-G-S-22','B-G-S-33']
jobs=[(key,offset) for key in selected for offset in [.25,.125,.0625]]
def run(job):
 key,off=job;v=g[key];prefix=os.getenv('PROJECTION_PREFIX','');tag=prefix+key+'-'+str(off)
 with (p/(tag+'.json')).open('w') as f,(p/(tag+'.log')).open('w') as log:
  args=[str(p/('node_edge' if prefix else 'node_row')),str(p/('field-'+v['scheme']+'.in')),str(v['master']),'2',str(104729+4099*v['master']),str(1<<18),str(off)]
  if prefix:args.append(str(p/(key+'.edges')))
  r=subprocess.call(args,stdout=f,stderr=log)
 print(tag,r,flush=True);return dict(case=tag,exit=r)
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:result=list(pool.map(run,jobs))
(p/(os.getenv('PROJECTION_PREFIX','')+'pilot-status.json')).write_text(json.dumps(result,indent=2));assert all(r['exit']==0 for r in result)
