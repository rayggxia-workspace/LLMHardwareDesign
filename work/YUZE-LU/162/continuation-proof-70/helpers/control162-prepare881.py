from pathlib import Path
import subprocess,shlex
q=r'''from pathlib import Path
import json,hashlib,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');p=b/'r256-native-prefix-path-diagnostic-873/native-prefix';parent=p/'receipt.json';assert json.loads(parent.read_text())['passed'];out=b/'r256-native-headroom-audit-881';assert not out.exists();sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();report=p/'native-prefix-diagnostics.json';assert json.loads(parent.read_text())['outputs'][report.name]==sha(report)
d=json.loads((p/'case-12/diagnostic.json').read_text());assert next(r for r in json.loads(report.read_text())['cases']if r['case']==12)==d;assert d['native_log_filtered_byte_exact']and d['main_failure_log_byte_exact'];focus={n for c in d['conflict_cells']for n in c['nets']};ends={};limits={}
with Path(d['original_input']).open()as f:
 header=list(map(int,f.readline().split()))
 for line in f:
  v=line.split();n=v[0]
  if n in focus:ends[n]=list(map(int,v[2:-1]));limits[n]=int(v[-1])
assert sha(d['snapshot_path'])==d['snapshot_sha256'];rows=[]
with Path(d['snapshot_path']).open()as f:
 count=int(f.readline());assert count==1229
 for i in range(count):
  n,k=f.readline().split();edges=set()
  for j in range(int(k)):
   raw=list(map(int,f.readline().split()));path=[tuple(raw[t:t+3])for t in range(1,len(raw),3)]
   if n in focus:
    for a,z in zip(path,path[1:]):
     if a[2]==z[2]:edges.add(tuple(sorted((a,z))))
  if n in focus:rows.append(dict(net=n,wire=len(edges),limit=limits[n],remaining=limits[n]-len(edges),hpwl=abs(ends[n][0]-ends[n][2])+abs(ends[n][1]-ends[n][3])))
assert len(rows)==32 and min(r['remaining']for r in rows)==41 and max(r['remaining']for r in rows)==200
out.mkdir();r=dict(passed=True,time=time.time(),whole_system_qualified=False,case=12,rows=rows,diagnostic_path=str(p/'case-12/diagnostic.json'),diagnostic_sha256=sha(p/'case-12/diagnostic.json'),snapshot_path=d['snapshot_path'],snapshot_sha256=d['snapshot_sha256'],parent_receipt=str(parent),parent_sha256=sha(parent),report_sha256=sha(report),scope='Read-only independent undirected same-layer edge count on actual matched failed native case12.32 conflict-involved nets have41-200 grid edges of unused original finite wire envelope. This does not prove a disjoint alternate exists; no physical budget, path, search, source or acceptance changed. Supports bounded strict-zero native candidate before original finite fallback, actual885 tests and all final gates still required. Native snapshots preserve all original11149 fixed landing constraints and exactly match original80round/failure logs.')
(out/'receipt.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(dict(passed=True,nets=len(rows),headroom_min=41,headroom_max=200)))
'''
compile(q,'headroom881','exec');Path(__file__).with_name('control162-headroom881.py').write_bytes(('import subprocess,shlex\nq='+repr(q)+'\nprint(subprocess.check_output(["ssh","yuzelu@10.129.166.172","python3 -c "+shlex.quote(q)],universal_newlines=True))\n').encode())
