"""Graph Attention -> explicit E32 dot, N32 softmax and DDR transfer commands."""
from math import isfinite
import json
from native_backend import NativeBackend
from native_p_candidates import _storage,_row_source,row_transfer
from e32_dot_descriptor import encode as dot
from n32_service_descriptor import encode as reduction
def workspace_bytes(task):
 context=max(t['context'] for t in task['tiles'])
 return context*512*2+2*((context+127)//128)*512
def candidate(task,*,dot_binding,n_binding,regions,hardware,workspace):
 if task['kind']!='Attention' or not task['tiles']:raise ValueError('Attention recipe required')
 e=dot_binding['control_owner'];n=n_binding['control_owner']
 if dot_binding['service_module']!='e32_dot_service_controller' or n_binding['service_module']!='n32_service_controller':
  raise ValueError('explicit dot and reduction bindings required')
 for binding,role,master in [(dot_binding,'e','e_s32_mac_ap64'),(n_binding,'n','n_s32_mod')]:
  m=hardware['macro_instances'][binding['resources'][role]]
  if m['master']!=master or m['control_owner']!=binding['control_owner']:raise ValueError('macro ownership/master mismatch')
 _storage(workspace,workspace['value'],-16)
 if workspace['bytes']<workspace_bytes(task) or workspace['base']%512:raise ValueError('Attention workspace capacity/alignment')
 for name,r in regions.items():
  if name!=workspace['value'] and r['base']<workspace['base']+workspace['bytes'] and workspace['base']<r['base']+r['bytes']:
   raise ValueError('Attention workspace overlaps graph operand')
 backend=NativeBackend(hardware['native_dispatch_overlay']);calls=[]
 max_context=max(t['context'] for t in task['tiles']);span=((max_context+127)//128)*512
 scores={'value':task['id']+':scores','base':workspace['base']+max_context*1024,'bytes':span,'element_bytes':4,'exponent':-16}
 probs={**scores,'value':task['id']+':probabilities','base':scores['base']+span}
 def append(call,part):
  calls.append(dict(call,index=len(calls),after=[] if not calls else [len(calls)-1],recipe_part=part))
 def invoke(group,raw,part,tile):
  c=backend.encode_deployment_call(group,('service_done',lambda _:raw),{'required_completion':'service_done'})
  append({'target':c.target,'group':group,'direction':'compute','operator':'Attention','tile':tile,
          'descriptor_hex':raw.hex(),'completion':c.completion},part)
 def rows_base(rows,offset,part):
  sources=[_row_source(a,regions,-16) for a in rows]
  addresses=[r['base']+off for r,off in sources]
  stride=addresses[1]-addresses[0] if len(addresses)>1 else 512
  if 0<=stride<2**32 and stride%4==0 and all(v==addresses[0]+i*stride for i,v in enumerate(addresses)):
   return addresses[0],stride
  for i,(access,(region,off)) in enumerate(zip(rows,sources)):
   append(row_transfer(backend,e,region,direction='load',sram_word=0,offset=off,value=access['value']),part)
   append(row_transfer(backend,e,workspace,direction='store',sram_word=0,offset=offset+i*512,value=workspace['value']),part)
  return workspace['base']+offset,512
 for index,tile in enumerate(task['tiles']):
  ctx=tile['context'];write=tile['write'];out=regions[write['value']]
  if not 1<=ctx<=4096 or tile['position']!=ctx-1 or write['elements']!=128 or len(tile['read'])!=1:
   raise ValueError('native causal Attention row geometry')
  if len(tile['key_rows'])!=ctx or len(tile['value_rows'])!=ctx:raise ValueError('KV row coverage')
  _storage(out,write['value'],-16)
  qr,qo=_row_source(tile['read'][0],regions,-16)
  kb,ks=rows_base(tile['key_rows'],0,'pack_keys')
  vb,vs=rows_base(tile['value_rows'],max_context*512,'pack_values')
  scale=tile['scale']
  if not isinstance(scale,(float,int)) or not isfinite(scale) or not 0<scale<=1:raise ValueError('QK scale')
  coefficient=round(scale*(1<<30))
  for first in range(0,ctx,4):
   invoke(e,dot(topology=backend.topology,k=128,columns=min(4,ctx-first),shift=16,
    result_word=first//4,a_address=qr['base']+qo,b_address=kb+first*ks,a_stride=4,b_k_stride=4,
    b_column_stride=ks,scale=coefficient,scale_shift=30),'QK',index)
  for row in range((ctx+127)//128):
   append(row_transfer(backend,e,scores,direction='store',sram_word=row*32,offset=row*512,value=scores['value']),'scores_commit')
   append(row_transfer(backend,n,scores,direction='load',sram_word=row*32,offset=row*512,value=scores['value']),'scores_load')
  invoke(n,reduction(operation='Softmax',topology=backend.topology,source_word=0,elements=ctx),'Softmax',index)
  for row in range((ctx+127)//128):
   append(row_transfer(backend,n,probs,direction='store',sram_word=row*32,offset=row*512,value=probs['value']),'probabilities_commit')
  # N32's actual probability representation is Q16, not Q31.
  for first in range(0,128,4):
   invoke(e,dot(topology=backend.topology,k=ctx,columns=4,shift=16,result_word=first//4,
    a_address=probs['base'],b_address=vb+first*4,a_stride=4,b_k_stride=vs,b_column_stride=4),'AV',index)
  append(row_transfer(backend,e,out,direction='store',sram_word=0,
   offset=write['element_offset']*4,value=write['value']),'output_commit')
 connections=list({json.dumps(c,sort_keys=True):c for c in
                   dot_binding['required_connections']+n_binding['required_connections']}.values())
 result = {'source_task':task['id'],'binding':task['id']+'@E:'+e+'@N:'+n,'groups':[e,n],
  'calls':calls,'connections':connections,
  'required_macro_leases':sorted(set(dot_binding['required_macro_leases']+n_binding['required_macro_leases']+
                                   [dot_binding['private_sram'],n_binding['private_sram']])),
  'required_registered_adapters':dot_binding['required_registered_adapters']+n_binding['required_registered_adapters'],
  'srams':{dot_binding['private_sram']:{'word':0,'words':max(32,((max_context+127)//128)*32)},
           n_binding['private_sram']:{'word':0,'words':((max_context+127)//128)*32}},
  'workspace':workspace,'completion':'last_output_DDR_commit',
  'numeric_contract':'Q16 inputs, full-K S80 dot then RNE/S32 saturation; Q30 QK scale; N32 Q16 probabilities; Q16 AV',
  'scope':'graph-derived staged native candidate; complete parent/plan/TLM acceptance still required'}
 from native_candidate_resources import admit
 return admit(result,hardware)
