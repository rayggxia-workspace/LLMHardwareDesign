import json,sys,struct
from pathlib import Path
from math import prod
from collections import Counter
from native_ffn_candidates import candidate,workspace_requirements
from native_wiring import selected_plan
from pack_native_projections import projection_size,ORDINARY
graph=json.loads(Path(sys.argv[1]).read_text());recipes=json.loads(Path(sys.argv[2]).read_text())
hardware=json.loads(Path('hardware/blockv2-mod-nine.json').read_text())
schema=json.loads(Path('/public/home/yuzelu/project-circuit/issue260-product-retirement-V6JR7Km4/source/project/experiments/block_local_native/p_scope128.json').read_text())
fields={x['name']:x for x in schema['fields']}
def field(raw,name):
 f=fields[name];return int.from_bytes(raw[f['offset']:f['offset']+f['bytes']],'little')
regions={};base=0x10000000
for name,v in graph['values'].items():
 size=4*prod(v['shape']);regions[name]={'value':name,'base':base,'bytes':size,'element_bytes':4,'exponent':-16}
 base+=(size+8191)//8192*8192
for task in recipes['tasks']:
 if task['kind']=='SwiGLUFFN':
  for name,req in workspace_requirements(task).items():
   size=req['elements']*4;regions[name]={'value':name,'base':base,'bytes':size,'element_bytes':4,'exponent':-16}
   base+=(size+8191)//8192*8192
weights={}
for task in recipes['tasks']:
 if task['kind']!='SwiGLUFFN':continue
 for name in task['tiles'][0]['weights']:
  k,n=graph['values'][name]['shape'];size=projection_size(n,k,base,ORDINARY)
  weights[name]={'shape':[n,k],'format':ORDINARY,'base':base,'bytes':size}
  base+=(size+8191)//8192*8192
out=Path(sys.argv[3]);out.mkdir();counts=Counter()
for source in ('U0','U1'):
 ids={'first_session':1,'generation':1,'job':1,'epoch':1,'tensor':1,'version':1,'rf_object_base':0,'record_sequence_base':0}
 for task in recipes['tasks']:
  if task['kind']!='SwiGLUFFN':continue
  result=candidate(task,source=source,target='P0',regions=regions,weights=weights,hardware=hardware,identities=ids)
  ids=result['next_identities'];ancestors=[];scopes={}
  for call in result['calls']:
   i=call['index'];assert i==len(ancestors)
   ancestry=0
   for dep in call['after']:
    assert 0<=dep<i
    ancestry|=ancestors[dep]|(1<<dep)
   ancestors.append(ancestry);raw=bytes.fromhex(call['descriptor_hex'])
   if call['direction']=='compute':
    key=field(raw,'input_key');assert key not in scopes
    scopes[key]={'index':i,'full_k':field(raw,'full_k'),'end':0,'last_feed':None}
   elif call['direction']=='supply':
    key=int.from_bytes(raw[24:40],'little');s=scopes[key]
    first=struct.unpack_from('<H',raw,44)[0];elements=struct.unpack_from('<H',raw,22)[0]*128
    assert first==s['end'] and not (ancestry>>s['index'])&1
    if s['last_feed'] is not None:assert (ancestry>>s['last_feed'])&1
    s['end']+=elements;s['last_feed']=i
   elif call['direction']=='gated_compute':
    assert raw[:4]==b'GSM1' and struct.unpack_from('<4H',raw,16)==(0,32,64,32)
   counts[call['direction']]+=1
  assert all(s['end']==s['full_k'] for s in scopes.values())
  last_ancestry=ancestors[-1]
  assert all((last_ancestry>>s['index'])&1 and (last_ancestry>>s['last_feed'])&1 for s in scopes.values())
  assert selected_plan([result])['bindings']
  counts['SwiGLUFFN/'+source]+=1
  if counts['SwiGLUFFN/'+source]==1:(out/(source+'-ffn-candidate.json')).write_text(json.dumps(result,indent=2)+'\n')
report={'passed':True,'counts':dict(counts),'scope':'all full-graph FFN native candidate command DAGs, bounded K chunks and static endpoint bindings; diagnostic allocations/weight metadata, not joined RTL or global Algo1 execution',
        'machine_package_complete':False}
(out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
