import subprocess,shlex
q=r'''from pathlib import Path
import json,hashlib,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');root=b/'r256-composition-453/upper-candidates';out=b/'r256-density-live-readback-839';assert not out.exists();out.mkdir();rows=[];sha=lambda raw:hashlib.sha256(raw).hexdigest()
for tag in [6360,7780,8110,8111]:
 p=root/str(tag)/'route/trial-0/router.log';raw=p.read_bytes();snapshot=out/(str(tag)+'-trial0-router.log');snapshot.write_bytes(raw);data=[]
 for l in raw.decode().splitlines():
  if not l.startswith('{')or '"conflict_nodes"'not in l:continue
  try:d=json.loads(l)
  except ValueError:continue
  assert d['summed_tree_vertices']==d['occupied_cells']+d['excess_occupancy'];data.append(d)
 assert data;inp=p.with_name('input.txt');rows.append(dict(candidate=tag,trial=0,first=data[0],last=data[-1],snapshot=str(snapshot),snapshot_sha256=sha(raw),input=str(inp),input_sha256=sha(inp.read_bytes()),scope='One actual trial per candidate, different RNG/source configurations may apply; not a matched performance experiment or whole-scene feasibility test.'))
r=dict(passed=True,time=time.time(),whole_system_qualified=False,rows=rows,scope='Actual complete-round counters from immutable snapshots of four owned trial0 logs. Weighted runs use about5.39million summed vertices but about2.84million distinct cells at round7, leaving about2.55million excess uses despite10.92million global capacity; exact direction8 trial uses about7.92million vertices,7.01million distinct and0.916million excess at round1. This motivates testing bounded strict-zero paths into unused space rather than increasing wire cost. Global spare cells do not prove local routability or physical timing; counts are partial-run evidence only, no convergence/speed/system acceptance claim.')
(out/'receipt.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(dict(passed=True,rows=[dict(candidate=x['candidate'],last=x['last'])for x in rows])))
'''
compile(q,'density839','exec');print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)]).decode())
