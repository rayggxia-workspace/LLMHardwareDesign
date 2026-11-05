from pathlib import Path
import subprocess,shlex,json,hashlib,base64,time
h=Path(__file__).parent;r=h/'LLMHardwareDesign-worktrees/issue-162-control';out=r/'work/YUZE-LU/162/continuation-proof-67';assert not out.exists()
q=r'''from pathlib import Path
import json,hashlib,base64,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');files=[]
for name in ['r256-fourary-heap-regression-777','r256-fourary-source-and-regression-audit-785','r256-final-chain-binding-audit-786','r256-directional-bidirectional-active-pool-audit-787','r256-older-placement-live-readback-775']:
 assert json.loads((b/name/'receipt.json').read_text())['passed'];files+=list((b/name).rglob('*'))
for name in ['r256-router-hotspot-profile-772','r256-router-hotspot-assembly-773']:
 r=json.loads((b/name/'receipt.json').read_text());assert(r.get('record_returncode')==r.get('report_returncode')==0)if 'record_returncode'in r else(r['recorded_binary_buildid_matches_current']and r['assembly_returncode']==0);files+=list((b/name).rglob('*'))
for tag in [7780,7781]:files+=list((b/'r256-composition-453/upper-candidates'/str(tag)/'route').glob('trial-*/router.log'))
for prefix in ['sready777-','sready781-','sready782-']:
 matches=[p for p in(b/'route-selection-102').iterdir()if p.name.startswith(prefix)];assert len(matches)==1;files+=list(matches[0].rglob('*'))
files += [b/'source-776/source-manifest.json',b/'source-776/freeze-import.json']
for folder,seed in [('dynamic-06/node26',7780),('dynamic-06/node26',7781)]:
 for section in ['commands','pending']:
  for p in(b/folder/section).glob('*.json'):
   if p.stem.endswith('-'+str(seed)):files.append(p)
 files.append(b/'r256-composition-453'/('acceptance-'+str(seed)+'.json'))
rows=[]
for p in sorted(set(files)):
 if not p.is_file():continue
 raw=p.read_bytes();copy=p.suffix in ['.json','.txt','.log','.cpp','.h','.py']and len(raw)<2000000
 row=dict(relative=str(p.relative_to(b)),path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),copied=copy)
 if copy:row['base64']=base64.b64encode(raw).decode()
 rows.append(row)
print(json.dumps(dict(time=time.time(),rows=rows,whole_system_qualified=False)))
'''
compile(q,'remote-proof704','exec');d=json.loads(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=60));out.mkdir()
for row in d['rows']:
 if row['copied']:
  raw=base64.b64decode(row.pop('base64'));assert hashlib.sha256(raw).hexdigest()==row['sha256'];p=out/row['relative'];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
items={}
for n in [772,773,775,776,780,781,782,784,785,786,787,788,789]:
 for p in h.glob('control162-*.py'):
  if p.stem.endswith(str(n))or p.stem.endswith(str(n)+'-remote'):items['helpers/'+p.name]=p
for n in [768,779]:items['helpers/publication-'+str(n)+'.json']=h/('control162-git-data-publish-'+str(n))/'receipt.json'
for directory in ['control162-phase788/7780','control162-phase788/7781','control162-phase749/7580','control162-phase749/7581','control162-watch734']:
 fs=sorted((h/directory).glob('*.json'))
 for p in [fs[0],fs[-1]]:items['selected-running-snapshots/'+directory+'/'+p.name]=p
for name in ['issue-verified','pr-request','pr-verified']:items['online783/'+name+'.json']=h/('control162-online783-'+name+'.json')
items['helpers/control162-source776-prepare.py']=h/'control162-source776-prepare.py'
d['helpers']=[]
for name,p in items.items():
 raw=p.read_bytes();target=out/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw);d['helpers'].append(dict(relative=name,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
d['metadata_failures']=dict(publication768='One transient api.github.com connection error retried by existing publisher; exact final commit768 readback passed, no force.',profile_scope='495 user CPU-clock samples from one owned7370 process during5s; function percentages only that sampled interval. Assembly line percentages are function-local and not global bottleneck shares; no statistical whole-job performance claim.')
d['scope']='Actual owner-only772/773 profile/buildid/assembly motivates source776 software queue optimization. Weighted function differs only heap type; production main after selftest and14 gate/resource/scene/prepass/pool sources/original exact class/finite branch bytes unchanged. Actual777 original tests plus33 actual route and filtered-log byte replays against source735 std heap,166730 independent random/tied/extreme heap-order comparisons per binary,1200 weighted oracles/3 trace/3 weight1/12 rejects. Actual32 owned router PIDs/CPU/memory/input checks, two16CPU masks disjoint in same actualnode24 parent,14 full final-chain bindings. Only guarded own5490/5493 steps replaced; other4 legacy5491/5492/5494/5495 and other tasks/parents preserved. No new arrays, keys, domain, physical budgets or gate changes; original conservative forecasts and6x16 c96 dynamic refill. Running logs are partial software snapshots, not complete route, speed guarantee, hardware waveforms or physical qualification.'
(out/'index.json').write_bytes((json.dumps(d,indent=2)+'\n').encode());print(json.dumps(dict(rows=len(d['rows']),copied=sum(x['copied']for x in d['rows']),helpers=len(d['helpers']))))
