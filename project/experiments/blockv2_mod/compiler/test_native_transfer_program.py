import json,sys,struct
from pathlib import Path
from math import prod
from collections import Counter
from hashlib import sha256
from native_backend import NativeBackend
from native_transfer_program import load,store
from native_u_candidates import candidate
from native_gather_candidates import candidate as gather_candidate
graph=json.loads(Path(sys.argv[1]).read_text());recipes=json.loads(Path(sys.argv[2]).read_text())
profile=json.loads(Path('algo1/blockv2-mod.json').read_text());backend=NativeBackend(profile)
# Diagnostic addresses only. No claim that original FLOAT weights are S32 assets.
regions={};base=0x10000000
for name,v in graph['values'].items():
 size=4*prod(v['shape'])
 regions[name]={'value':name,'base':base,'bytes':size,'element_bytes':4,'exponent':-16}
 base+=(size+8191)//8192*8192
counts=Counter();digests=sha256();candidates=Counter();sample=None
def validate(calls,access,region):
 expected=[]
 for s in access['segments']:expected.append([s['destination_element']*4,s['source_element']*4,s['elements']*4])
 pos=0;index=0
 for call in calls:
  raw=bytes.fromhex(call['descriptor_hex']);schema,_,_,_,_=struct.unpack_from('<IHHII',raw)
  word,n,_,addr=struct.unpack_from('<HHIQ',raw,16)
  assert schema==0x31434c44
  size=n*128
  dest,source,remaining=expected[index]
  assert word*16==dest+pos and addr==region['base']+source+pos
  assert 0<size<=remaining-pos
  pos+=size
  if pos==remaining:index+=1;pos=0
 assert index==len(expected) and pos==0
for task in recipes['tasks']:
 for tile in task['tiles']:
  for a in tile.get('read',[])+tile.get('key_rows',[])+tile.get('value_rows',[]):
   if task['kind']=='Gather':continue # Index lookup is inside indexed Gather, not a counted SRAM load.
   for group in ('U0','U1'):
    calls=load(a,regions[a['root']],group=group,sram_word=0,backend=backend)
    validate(calls,a,regions[a['root']])
    counts['load_calls']+=len(calls)
    for c in calls:digests.update(bytes.fromhex(c['descriptor_hex']))
  for group in ('U0','U1'):
   calls=store(tile['write'],regions[tile['write']['value']],group=group,sram_word=0,backend=backend)
   counts['store_calls']+=len(calls)
   for c in calls:digests.update(bytes.fromhex(c['descriptor_hex']))
 if task['kind']=='Gather':
  for tile in task['tiles']:
   regions[tile['read'][0]['root']]['encoding']='signed-int32-exact'
  for group in ('U0','U1'):
   c=gather_candidate(task,group=group,regions=regions,profile=profile)
   gather_calls=[call for call in c['calls'] if call['direction']=='gather']
   assert len(gather_calls)==len(task['tiles'])
   for call,tile in zip(gather_calls,task['tiles']):
    raw=bytes.fromhex(call['descriptor_hex'])
    table,rows,index_byte,dest,prompt,flags=struct.unpack_from('<QIHHQI',raw,16)
    a=tile['read'][0]
    assert table==regions[tile['indexed_table']]['base'] and rows==tile['table_rows']
    assert prompt==regions[a['root']]['base']+4*a['segments'][0]['source_element']
    assert index_byte==8192 and dest==0 and flags==1
   assert c['runtime_input_constraints']
   candidates['Gather/'+group]+=1
 if task['kind'] in ('RMSNorm','Add'):
  for group in ('U0','U1'):
   c=candidate(task,group=group,regions=regions,profile=profile)
   assert c['calls'] and c['calls'][-1]['direction']=='store'
   candidates[task['kind']+'/'+group]+=1
   if sample is None:sample=c
out=Path(sys.argv[3]);out.mkdir()
report={'passed':True,'counts':dict(counts),'candidates':dict(candidates),'descriptor_stream_sha256':digests.hexdigest(),
 'scope':'full-graph operand transfer encoding at diagnostic S32 allocations and complete U Gather/RMS/Add candidate command sequences; not a selected global plan or prepared numerical asset image',
 'machine_package_complete':False}
(out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
(out/'sample-native-candidate.json').write_text(json.dumps(sample,indent=2)+'\n')
print(json.dumps(report))
