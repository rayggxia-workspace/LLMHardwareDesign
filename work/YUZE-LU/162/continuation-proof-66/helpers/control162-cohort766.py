from pathlib import Path
import json,hashlib,time
h=Path(__file__).parent;out=h/'LLMHardwareDesign-worktrees/issue-162-control/work/YUZE-LU/162/continuation-proof-66';index=out/'index.json';d=json.loads(index.read_text(encoding='utf-8'));bound={r['relative']:r for r in d['rows']};result=[]
for tag in [7200,7370,7371,7580,7581]:
 base=out/('r256-pair-window-phase-comparison-757/7200'if tag==7200 else'r256-composition-453/upper-candidates/'+str(tag)+'/route');pattern='trial-*.log'if tag==7200 else'trial-*/router.log';rounds={};inputs=[]
 for p in base.glob(pattern):
  raw=p.read_bytes();rel=p.relative_to(out).as_posix();digest=hashlib.sha256(raw).hexdigest();assert bound[rel]['sha256']==digest;inputs.append(dict(relative=rel,sha256=digest))
  trial=int((p.stem if tag==7200 else p.parent.name).split('-')[1])
  if trial>=16:continue
  for line in raw.decode().splitlines():
   try:r=json.loads(line)
   except ValueError:continue
   if'conflict_nodes'in r:rounds.setdefault(r['round'],{})[trial]=r['excess_occupancy']
 complete=[dict(round=k,initial_trials=16,mean_excess=sum(v.values())/16,min_excess=min(v.values()),max_excess=max(v.values()))for k,v in sorted(rounds.items())if set(v)==set(range(16))]
 result.append(dict(candidate=tag,input_logs=inputs,complete_initial16=complete))
r=dict(time=time.time(),whole_system_qualified=False,derived_from_copied_raw_only=True,candidates=result,scope='Independent local aggregation of actual captured complete round/excess lines, initial16 attempts only; each raw Git-proof SHA checked. Baseline7200 from757 snapshot, other candidates from756 later snapshot. Only completed16-member rounds included. No zero-conflict route, whole-round runtime comparison, convergence or physical qualification inferred.')
target=out/'cohort-comparison-from-raw.json';assert not target.exists();target.write_bytes((json.dumps(r,indent=2)+'\n').encode())
helper=out/'helpers'/Path(__file__).name;helper.write_bytes(Path(__file__).read_bytes())
for p in [target,helper]:d['helpers'].append(dict(relative=p.relative_to(out).as_posix(),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
index.write_bytes((json.dumps(d,indent=2)+'\n').encode());print(json.dumps([dict(candidate=x['candidate'],latest=x['complete_initial16'][-1:] )for x in result]))
