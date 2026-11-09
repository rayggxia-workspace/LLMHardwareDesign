"""Offline audit of exact returned evidence and current tested functional files."""
import base64,gzip,hashlib,json,re
from pathlib import Path

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
def digest(raw):return hashlib.sha256(raw).hexdigest()
index=json.loads((HERE/'index.json').read_bytes());raw={}
for name,entry in index['artifacts'].items():
 data=(HERE/name).read_bytes()
 assert digest(data)==entry['sha256'],name
 value=gzip.decompress(base64.b64decode(data)) if entry['encoding']=='gzip-base64' else data
 assert len(value)==entry['original_bytes'] and digest(value)==entry['original_sha256'],name
 run=name.split('/',1)[0];raw[run+'/'+entry['original_run_path']]=value

def read(name):return json.loads(raw[name])
latest={};audited_outputs=0
for run in index['runs']:
 name=run['run'];collection=read(name+'/collection.json');inputs=read(name+'/inputs.json')
 assert run['whole_run_passed'] and collection['whole_run_passed']
 assert run['job']['state']=='COMPLETED' and run['job']['exit_code']=='0:0'
 main=read(name+'/results/result.json')
 assert main['passed'] and not main['errors'] and main['source_commit']==inputs['source_commit']==run['source_commit']
 outputs=dict((n,h) for h,n in (line.split('  ',1) for line in raw[name+'/output-files.sha256'].decode().splitlines()))
 for key,value in raw.items():
  if key.startswith(name+'/results/'):
   assert digest(value)==outputs[key[len(name)+1:]],key
   audited_outputs+=1
 for component in ('memory','context','policy'):
  key=name+'/results/'+component+'/result.json'
  if key in raw:assert read(key)['passed'],key
 latest.update(inputs['code_sha256'])
functional={n:h for n,h in latest.items() if Path(n).suffix in ('.py','.sv','.svh','.cpp','.inc','.sh')}
for name,h in functional.items():assert digest((ROOT/name).read_bytes())==h, 'current tested source drift '+name

context=read('run10/results/context/result.json')
assert len(context['runs'])==15
summary_context=[]
for n in (1,2,8):
 rows=[json.loads(line) for line in raw[f'run10/results/context/contexts{n}-1-247.jsonl'].decode().splitlines() if line.startswith('{')]
 cases=[r for r in rows if r.get('type')=='case'];assert len(cases)==44
 improved=equal=regressed=0
 for case in cases:
  old,reload,reuse=case['routes']
  assert old['A_handshakes']==reload['A_handshakes']==reuse['A_handshakes']*n
  assert old['B_handshakes']==reload['B_handshakes']==reuse['B_handshakes']
  assert old['B_wire_bytes']==reload['B_wire_bytes']==reuse['B_wire_bytes']
  assert reload['commands']==reuse['commands']
  assert reload['cycles']==old['cycles']+2*n
  assert reuse['cycles']==reload['cycles']-(reload['A_handshakes']-reuse['A_handshakes'])
  improved+=reuse['cycles']<old['cycles'];equal+=reuse['cycles']==old['cycles'];regressed+=reuse['cycles']>old['cycles']
 summary_context.append(dict(contexts=n,cases=44,improved=improved,equal=equal,regressed=regressed))
for mode,seed in ((1,247),(2,247),(2,248)):
 base=next(r['result'] for r in context['runs'] if (r['label'],r['mode'],r['seed'])==('baseline',mode,seed))
 new=next(r['result'] for r in context['runs'] if (r['label'],r['mode'],r['seed'])==('legacy_candidate',mode,seed))
 assert base==new

group=read('run11/results/result.json')['components']['group']['measurements']
assert len(group)==18
for r in group:
 s=r['segments'];assert r['B']==8*s and r['stores']==16
 assert r['A']==(s if r['opt'] else 8*s) and r['wide']==s*(9 if r['opt'] else 16)
 assert r['cycles']==r['output_cycles']+r['release_cycles']
 assert (r['release_cycles']>0)==bool(r['opt'])
memory=read('run11/results/memory/result.json')
assert len(memory['runs'])==18
policy=read('run10/results/policy/result.json')
assert len(policy['measurements'])==12 and len(policy['negative_controls'])==2
summary=dict(passed=True,curated_artifacts=len(index['artifacts']),returned_output_sha_checks=audited_outputs,
 current_functional_source_sha_checks=len(functional),runs=index['runs'],context_cases=summary_context,
 group=[r for r in group if r['mode']==1],policy=policy['comparisons'],
 memory=[r for r in memory['runs'] if r['reset_mode']==1],
 scope='offline provenance/work/cycle audit; complements actual server RTL, not new RTL/physical execution')
(HERE/'summary.json').write_bytes((json.dumps(summary,indent=2)+'\n').encode())
print(json.dumps({k:summary[k] for k in ('passed','curated_artifacts','returned_output_sha_checks','current_functional_source_sha_checks','context_cases')}))
