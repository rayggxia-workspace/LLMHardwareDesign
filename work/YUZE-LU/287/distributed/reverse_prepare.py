import pathlib,json,re,math
p=pathlib.Path(__file__).resolve().parent
exec((p/'fast_prepare.py').read_text().split("runner(p/'fast-pilot.tcl'")[0])
graphs=json.loads((p/'graphs-rcx.json').read_text());done=set()
for log in list((p/'sta').glob('worker-*.log'))+list(p.glob('fast-worker-*.log')):done.update((k,int(f)) for k,f in re.findall(r'^FINISHED (\S+) (\d+)$',log.read_text(),re.M))
pending=[k for k in graphs if any((k,f) not in done for f in [200,300])];keys=pending[len(pending)//2:]
jobs=[(key,f,p/'spef'/(key+'.spef')) for key in keys for f in [200,300] if (key,f) not in done]
for i in range(8):runner(p/('reverse-worker-%d.tcl'%i),[j for j in jobs if keys.index(j[0])%8==i],p/'sta-reverse')
(p/'reverse-job-index.json').write_text(json.dumps({'completed_before':len(done),'cases':[(k,f) for k,f,_ in jobs]},indent=2))
print(len(jobs),'tail cases on second node')
