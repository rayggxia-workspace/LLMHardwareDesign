"""Interpret every emitted row transfer and inspect compute input identities.

This is an independent addressing/dispatch check, not an arithmetic simulator.
"""
import json,sys,struct
from pathlib import Path
from math import prod
from bisect import bisect_right
from collections import Counter
from native_p_candidates import candidate
graph=json.loads(Path(sys.argv[1]).read_text());recipes=json.loads(Path(sys.argv[2]).read_text())
layouts=json.loads(Path(sys.argv[3]).read_text())['values']
profile=json.loads(Path('algo1/blockv2-mod.json').read_text())
exponents={name:-16 for name in graph['values']}
for task in graph['tasks']:
 if task['kind']=='RoPE':
  for key in ('cosine','sine'):exponents[layouts[task['details'][key]['tensor']]['root']]=-14
regions={};base=0x10000000
for name,v in graph['values'].items():
 size=4*prod(v['shape']);regions[name]={'value':name,'base':base,'bytes':size,'element_bytes':4,'exponent':exponents[name]}
 base+=(size+8191)//8192*8192
workspace={'value':'native_kv_pack','base':base,'bytes':1024*1024,'element_bytes':4,'exponent':-16}
ordered=sorted(regions.values(),key=lambda x:x['base']);starts=[x['base'] for x in ordered]
def symbols(access):
 return [(access['root'],i) for s in access['segments'] for i in range(s['source_element'],s['source_element']+s['elements'])]
counts=Counter();all_candidates=[];samples={}
for task in recipes['tasks']:
 if task['kind'] not in ('RoPE','Attention'):continue
 selected=candidate(task,group='P0',regions=regions,profile=profile,workspace=workspace)
 sram={};written={};seen_computes=set()
 def read(address):
  if workspace['base']<=address<workspace['base']+workspace['bytes']:
   if address not in written:raise AssertionError('read of uncommitted packed KV row')
   return written[address]
  reg=ordered[bisect_right(starts,address)-1]
  assert reg['base']<=address and address+512<=reg['base']+reg['bytes']
  first=(address-reg['base'])//4
  return [(reg['value'],i) for i in range(first,first+128)]
 for call in selected['calls']:
  raw=bytes.fromhex(call['descriptor_hex']);schema=int.from_bytes(raw[:4],'little')
  if schema==int.from_bytes(b'DRL1','little'):
   word=struct.unpack_from('<H',raw,16)[0];address=struct.unpack_from('<Q',raw,24)[0]
   for i,x in enumerate(read(address)):sram[4*word+i]=x
  elif schema==int.from_bytes(b'DWS1','little'):
   word=struct.unpack_from('<H',raw,16)[0];address,tag=struct.unpack_from('<QQ',raw,24)
   assert tag==address//64
   written[address]=[sram[4*word+i] for i in range(128)]
  elif schema==int.from_bytes(b'RPE1','little'):
   index=call['tile'];tile=task['tiles'][index];words=struct.unpack_from('<4H',raw,16)
   for word,access in zip(words[:3],tile['read']):
    assert [sram[4*word+i] for i in range(128)]==symbols(access)
   assert struct.unpack_from('<6b',raw,24)==(14,0,0,14,0,0)
   for i in range(128):sram[4*words[3]+i]=(tile['write']['value'],tile['write']['element_offset']+i)
   seen_computes.add(index)
  elif schema==int.from_bytes(b'ATT1','little'):
   index=call['tile'];tile=task['tiles'][index]
   context,position,q,score,work,out=struct.unpack_from('<6H',raw,16)
   coefficient,kb,vb=struct.unpack_from('<IQQ',raw,28)
   assert context==tile['context'] and position==tile['position']
   assert coefficient==round(tile['scale']*(1<<30))
   assert [sram[4*q+i] for i in range(128)]==symbols(tile['read'][0])
   for j in range(context):
    assert read(kb+512*j)==symbols(tile['key_rows'][j])
    assert read(vb+512*j)==symbols(tile['value_rows'][j])
   for i in range(128):sram[4*out+i]=(tile['write']['value'],tile['write']['element_offset']+i)
   seen_computes.add(index)
  else:raise AssertionError('unexpected native call')
  counts[call['direction']]+=1
 assert seen_computes==set(range(len(task['tiles'])))
 for tile in task['tiles']:
  w=tile['write'];address=regions[w['value']]['base']+4*w['element_offset']
  assert written[address]==[(w['value'],i) for i in range(w['element_offset'],w['element_offset']+128)]
 counts[task['kind']+'_candidates']+=1
 counts['workspace_bytes']+=selected['workspace_bytes']
 samples.setdefault(task['kind'],selected)
out=Path(sys.argv[4]);out.mkdir()
for kind,selected in samples.items():(out/(kind+'-candidate.json')).write_text(json.dumps(selected,indent=2)+'\n')
report={'passed':True,'counts':dict(counts),'scope':'all graph RoPE/Attention candidates: independent emitted-descriptor interpretation verifies transfers, computed operand identities and output coverage; arithmetic and global scheduling not executed',
        'machine_package_complete':False}
(out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
