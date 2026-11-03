from pathlib import Path
import json,hashlib,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');root=b/'r256-composition-453';record=b/'route-selection-102/sready484-search-phase-profile';assert not record.exists();sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();record.mkdir();rows=[];trials=[]
for i in range(16):
 folder=root/'upper-candidates/4760/route'/('trial-'+str(i));inp=folder/'input.txt';raw=(folder/'router.log').read_bytes();lines=raw.splitlines(keepends=True);prefix=b'';found=False
 for line in lines:
  prefix+=line
  if line.startswith(b'{'):
   d=json.loads(line)
   if d.get('round')==6 and 'conflict_nodes'in d:found=True;break
 assert found
 target=record/('trial-'+str(i)+'-first7rounds.stdout');target.write_bytes(prefix);trials.append(dict(input=str(inp),input_sha256=sha(inp),reference_prefix=str(target),reference_prefix_sha256=sha(target)))
cpp=b/'source-474/project/experiments/control_v1/tree_router.cpp';config=record/'profile-config.json';config.write_text(json.dumps(dict(schema='bounded-phase7-profile/1',max_seconds=900,source_cpp=str(cpp),source_cpp_sha256=sha(cpp),trials=trials),indent=2))
def put(name,spec):
 p=b/'dynamic-05/node4/pending'/(name+'.json');assert not p.exists();tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(spec));tmp.rename(p);rows.append(dict(path=str(p),sha256=sha(p),spec=spec))
put('00-f-sready484-bounded-search-phase-profile',dict(script='search_phase_profile.py',source_root=str(b/'source-483'),forecast_gib=32,requires=[],args=['--config',str(config),'--out',str(b/'r256-search-phase-profile-484')]))
template=[x for x in json.loads((b/'route-selection-102/sready476-controlled-high-weight/tasks.json').read_text())['tasks']if '-4760'in Path(x['path']).stem];assert len(template)==7
target=root/'acceptance-4850.json';assert not target.exists();target.write_text((root/'acceptance-4760.json').read_text().replace('/upper-candidates/4760/','/upper-candidates/4850/'))
for old in template:
 spec=json.loads(json.dumps(old['spec']))
 for key in ['args','requires']:spec[key]=[x.replace('/upper-candidates/4760/','/upper-candidates/4850/').replace('acceptance-4760.json','acceptance-4850.json')for x in spec[key]]
 if spec['script']=='system_upper.py':
  a=spec['args'];assert a[a.index('--seed')+1]=='4661'and a[a.index('--route-heuristic-weight')+1]=='128';a[a.index('--route-heuristic-weight')+1]='256'
 put(Path(old['path']).stem.replace('sready476','sready485').replace('4760','4850'),spec)
(record/'tasks.json').write_text(json.dumps(dict(time=time.time(),tasks=rows,whole_system_qualified=False,scope='Own node4 single16CPU slot: bounded software phase diagnosis first, then actual453 full7stage candidate4850 with all original geometry/PG/low-base-high300MHz/function/joint gates. Same placement4610/RNG4661/cost2/scale1/critical-first/8million labels/64attempts16active as4661/4760; only initial weight256 differs. No claim speed, convergence, infeasibility or qualification. Original4010 partial failures retained; no foreign task affected.'),indent=2));print(json.dumps(dict(queued=len(rows),diagnostic_trials=len(trials),candidate=4850)))
