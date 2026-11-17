import pathlib,json,subprocess,concurrent.futures,time
p=pathlib.Path(__file__).resolve().parent;graphs=json.loads((p/'graphs.json').read_text());dest=p/'all-nodes';dest.mkdir(exist_ok=True)
jobs=[(key,off) for key in graphs for off in [.125,.0625]]
def run(job):
 key,off=job;g=graphs[key];tag=key+'-'+str(off);f=dest/(tag+'.json')
 if f.exists() and f.stat().st_size:
  r=json.loads(f.read_text());assert len(r['nodes'])==len(g['nodes']);return {'case':tag,'exit':0,'reused':True}
 start=time.time()
 with f.open('w') as out,(dest/(tag+'.log')).open('w') as log:
  rc=subprocess.call([str(p/'node_edge'),str(p/('field-'+g['scheme']+'.in')),str(g['master']),'8',str(104729+4099*g['master']),str(1<<18),str(off),str(p/(key+'.edges'))],stdout=out,stderr=log)
 return {'case':tag,'exit':rc,'seconds':time.time()-start}
results=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
 for i,r in enumerate(pool.map(run,jobs),1):results.append(r);print(i,len(jobs),r,flush=True)
(p/'all-node-status.json').write_text(json.dumps(results,indent=2));assert all(r['exit']==0 for r in results)
print('ALL_1292_NODE_FIELDS_COMPLETE',flush=True)
