from pathlib import Path
import subprocess,shlex,sys
n=int(sys.argv[1])if len(sys.argv)>1 else 757
q=r'''from pathlib import Path
import json,time,hashlib,statistics
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');out=b/('r256-pair-window-phase-comparison-'+str(N));assert not out.exists();out.mkdir();samples={};windows={};files=[]
for tag in [7200,7370,7371]:
 data={};last_windows=[]
 for p in(b/'r256-composition-453/upper-candidates'/str(tag)/'route').glob('trial-*/router.log'):
  raw=p.read_bytes();target=out/str(tag)/(p.parent.name+'.log');target.parent.mkdir(exist_ok=True);target.write_bytes(raw);files.append(dict(path=str(p),snapshot=str(target),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()));starts={}
  for line in raw.decode().splitlines():
   try:d=json.loads(line)
   except ValueError:continue
   if'weighted_window_branches'in d:last_windows.append(dict(trial=p.parent.name,**d))
   if'routing_phase_event'not in d:continue
   key=(p.parent.name,d['round'],d['net'])
   if d['routing_phase_event']=='start':starts[key]=d;continue
   if key not in starts:continue
   a=starts.pop(key)
   if a['round']==8 and not a['wire_limited']and a['terminal_groups']==2:data[key]=(d['monotonic_ns']-a['monotonic_ns'])/1e9
 samples[tag]=data;windows[str(tag)]=last_windows
rows=[]
for tag in [7370,7371]:
 keys=sorted(set(samples[7200])&set(samples[tag]));rows.append(dict(candidate=tag,paired_completed_calls=len(keys),baseline_sum_seconds=sum(samples[7200][k]for k in keys),candidate_sum_seconds=sum(samples[tag][k]for k in keys),pairs=[dict(trial=k[0],round=k[1],net=k[2],baseline_seconds=samples[7200][k],candidate_seconds=samples[tag][k])for k in keys]))
r=dict(passed=True,time=time.time(),whole_system_qualified=False,comparisons=rows,files=files,window_counters=windows,scope='Software per-net monotonic durations only. Compare actual completed matching trial/round8/net ordinary-pair calls, identical inputs/RNG4662 and actual CLI/source bindings751. Baseline7200 source717 unbounded,7370/7371 source735 margin64/256 on different c64 nodes. Incomplete/unrecorded calls omitted; no whole-round share, statistical speed guarantee, convergence, same returned path, final route or physical qualification claim. Preserve all partial log bytes.')
(out/'receipt.json').write_text(json.dumps(r,indent=2));print(json.dumps([dict(candidate=x['candidate'],paired_completed_calls=x['paired_completed_calls'],baseline_sum_seconds=x['baseline_sum_seconds'],candidate_sum_seconds=x['candidate_sum_seconds'])for x in rows]))
'''.replace('N)',str(n)+')')
compile(q,'remotecompare','exec');z=subprocess.run(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True);print(z.stdout);print(z.stderr[-1000:]if z.returncode else'');assert not z.returncode
