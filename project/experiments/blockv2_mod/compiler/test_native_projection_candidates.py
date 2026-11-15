import json,sys,struct
from pathlib import Path
from math import prod
from collections import Counter
from native_projection_candidates import candidate
from native_wiring import merge,selected_plan
from pack_native_projections import projection_size,ORDINARY
g=json.loads(Path(sys.argv[1]).read_text());recipes=json.loads(Path(sys.argv[2]).read_text())
h=json.loads(Path('hardware/blockv2-mod-nine.json').read_text())
regions={};base=0x10000000
for name,v in g['values'].items():
 size=4*prod(v['shape']);regions[name]={'value':name,'base':base,'bytes':size,'element_bytes':4,'exponent':-16}
 base+=(size+8191)//8192*8192
weights={}
for t in recipes['tasks']:
 if t['kind']!='MatMul':continue
 for tile in t['tiles']:
  name=tile['weight']['value']
  if name in weights:continue
  k,n=g['values'][name]['shape'];size=projection_size(n,k,base,ORDINARY)
  weights[name]={'shape':[n,k],'format':ORDINARY,'base':base,'bytes':size}
  base+=(size+8191)//8192*8192
counts=Counter();samples={}
for source in ('U0','U1'):
 identities={'first_session':1,'generation':1,'job':1,'epoch':1,'tensor':1,'version':1,'rf_object_base':0,'record_sequence_base':0}
 for task in recipes['tasks']:
  if task['kind']!='MatMul':continue
  c=candidate(task,source=source,target='P0',regions=regions,weights=weights,hardware=h,identities=identities)
  by={call['index']:call for call in c['calls']}
  for call in c['calls']:
   assert all(i<call['index'] for i in call['after'])
   if call['direction']=='supply':
    p=by[call['index']-1];assert p['direction']=='compute' and p['after']==call['after']
    # Neither service waits for the other's terminal.
    assert p['index'] not in call['after'] and call['index'] not in p['after']
    desc=bytes.fromhex(p['descriptor_hex']);feed=bytes.fromhex(call['descriptor_hex'])
    schema=json.loads(Path('/public/home/yuzelu/project-circuit/issue260-product-retirement-V6JR7Km4/source/project/experiments/block_local_native/p_scope128.json').read_text())
    fields={x['name']:x for x in schema['fields']}
    key=fields['input_key'];pkey=int.from_bytes(desc[key['offset']:key['offset']+key['bytes']],'little')
    assert pkey==int.from_bytes(feed[24:40],'little')
    assert struct.unpack_from('<H',feed,20)[0]==880
    store=by[call['index']+1]
    assert set(store['after'])=={call['index'],p['index']}
   counts[call['direction']]+=1
  assert c['connections'][0]['source']==source and c['connections'][0]['target']=='P0'
  identities.update(first_session=c['next_session'],tensor=c['next_tensor'],record_sequence_base=c['next_record_sequence'])
  counts['MatMul/'+source]+=1
  samples.setdefault(source,c)
wiring=selected_plan([samples['U0'],samples['U0']])
assert wiring['bindings']
try:merge(wiring['bindings'],samples['U1'])
except ValueError as e:assert 'static wiring conflict' in str(e)
else:raise AssertionError('two U drivers were admitted on one static P sink')
out=Path(sys.argv[3]);out.mkdir()
(out/'sample-selected-wiring.json').write_text(json.dumps(wiring,indent=2)+'\n')
for name,c in samples.items():(out/(name+'-projection.json')).write_text(json.dumps(c,indent=2)+'\n')
report={'passed':True,'counts':dict(counts),'scope':'all graph MatMul candidates encoded with diagnostic weight/storage metadata; paired U/P dependencies and exact candidate wiring verified. No weight images, global plan or joined RTL execution claimed.',
        'machine_package_complete':False}
(out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
