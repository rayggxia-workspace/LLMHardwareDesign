"""Prepare short decode from real prefill writes, reusing sealed static images.

Host input loading/view relocation and greedy sampling are scenario preparation;
their time is excluded, not attributed to hardware execution.
"""
import argparse,json,os
from pathlib import Path
import numpy as np
import onnx
from onnx import numpy_helper
from native_package_runtime import load
from macro_assets import filehash
def main():
 p=argparse.ArgumentParser()
 for n in ('source_package','source_assets','source_graph','source_execution','state_inputs',
           'destination_package','destination_onnx','output'):p.add_argument(n,type=Path)
 p.add_argument('--logits-value',required=True)
 a=p.parse_args()
 sm,sp,_=load(a.source_package);dm,dp,_=load(a.destination_package)
 assets=json.loads(a.source_assets.read_text());execution=json.loads(a.source_execution.read_text())
 state=json.loads(a.state_inputs.read_text());graph=json.loads(a.source_graph.read_text())
 if not (sm['plan_sha256']==assets['plan_sha256']==execution['plan_sha256']==state['source_plan_sha256']):
  raise ValueError('prefill source identities disagree')
 if execution['status']!='all_instructions_executed' or state['destination_plan_sha256']!=dm['plan_sha256']:
  raise ValueError('successful prefill and matching decode required')
 if execution['committed_state']['sha256']!=state['source_state_sha256']:
  raise ValueError('state not produced by this prefill')
 if graph['source_model_sha256']!=sm['graph_sha256'] or filehash(a.destination_onnx)!=dm['graph_sha256']:
  raise ValueError('source model identity')
 value=next(v for v in execution['outputs'] if v['value']==a.logits_value)
 path=a.source_execution.parent/value['file']
 if filehash(path)!=value['sha256']:raise ValueError('prefill logits seal')
 shape=graph['values'][a.logits_value]['shape']
 if shape[0]!=1:raise ValueError('this runtime scene requires batch one')
 logits=np.fromfile(path,dtype='<i4')
 if logits.size!=np.prod(shape):raise ValueError('logits extent')
 token=int(np.argmax(logits[-shape[-1]:]))
 source_storage=json.loads(sp['storage.json']);dest_storage=json.loads(dp['storage.json'])
 old_rows={r['name']:r for r in assets['regions']}
 old_inputs={r['region']['value']:r for r in source_storage['runtime_asset_requirements'] if r['kind']=='input_tensor'}
 model=onnx.load(a.destination_onnx)
 constants={x.name:numpy_helper.to_array(x) for x in model.graph.initializer}
 for node in model.graph.node:
  if node.op_type=='Constant' and not node.input:
   attrs={x.name:x for x in node.attribute}
   if set(attrs)=={'value'}:constants[node.output[0]]=numpy_helper.to_array(attrs['value'].t)
 a.output.mkdir(exist_ok=False);rows=[]
 for i,req in enumerate(dest_storage['runtime_asset_requirements']):
  region=req['region'] if req['kind']=='input_tensor' else req
  name=region['value'] if req['kind']=='input_tensor' else req['graph_value']
  path=a.output/f'asset-{i:04d}.bin';shared=False;raw=None;origin={}
  if req['kind']=='packed_weight':
   before=source_storage['weights'][name]
   if any(before[k]!=req[k] for k in ('shape','format','bytes')):raise ValueError('static weight changed '+name)
   shared=True
  elif name in state['inputs']:
   record=state['inputs'][name];input_path=(a.state_inputs.parent/record['file']).resolve()
   if not input_path.is_relative_to(a.state_inputs.parent.resolve()) or filehash(input_path)!=record['sha256']:
    raise ValueError('state input seal/path')
   if record['shape']!=req['source_shape'] or record['exponent']!=region['exponent']:
    raise ValueError('state input shape/format')
   raw=input_path.read_bytes();origin={'committed_state_sha256':state['source_state_sha256'],'source_root':record['source_root']}
  elif name=='input_ids':
   if np.prod(req['source_shape'])!=1 or region.get('encoding')!='signed-int32-exact':raise ValueError('decode input extent')
   raw=np.array([token],dtype='<i4').tobytes();origin={'token':token,'source_logits_sha256':value['sha256']}
  elif name in constants:
   values=constants[name]
   if list(values.shape)!=req['source_shape']:raise ValueError('constant shape '+name)
   q=np.rint(values.astype(np.float64)*2.0**(-region['exponent']))
   if not np.isfinite(q).all() or np.any(q<-(1<<31)) or np.any(q>=1<<31):raise ValueError('constant clipping')
   raw=q.astype('<i4').tobytes();origin={'onnx_constant':name}
  else:
   before=old_inputs[name]
   if any(before[k]!=req[k] for k in ('source_dtype','source_shape')) or any(before['region'].get(k)!=region.get(k) for k in ('bytes','exponent','encoding')):
    raise ValueError('input format changed '+name)
   if 'checkpoint_tensor' not in old_rows[name]['origin']:raise ValueError('cannot reuse dynamic input '+name)
   shared=True
  if shared:
   row=old_rows[name];source=(a.source_assets.parent/row['file']).resolve()
   if not source.is_relative_to(a.source_assets.parent.resolve()) or filehash(source)!=row['sha256']:raise ValueError('static image seal')
   os.link(source,path);origin={'reused_asset_sha256':row['sha256'],**row['origin']}
  else:
   if len(raw)!=region['bytes']:raise ValueError('input byte extent '+name)
   path.write_bytes(raw+bytes((-len(raw))%64))
  size=(region['bytes']+63)//64*64
  if path.stat().st_size!=size:raise ValueError('asset size '+name)
  rows.append({'name':name,'base':region['base'],'bytes':size,'file':path.name,'sha256':filehash(path),'origin':origin})
 result={'schema':'macro-runtime-assets/1','plan_sha256':dm['plan_sha256'],'graph_sha256':dm['graph_sha256'],
  'hardware_sha256':dm['payloads']['hardware.json']['sha256'],'checkpoint_files_sha256':assets['checkpoint_files_sha256'],
  'regions':rows,'numerical_acceptance':False,'source_execution_plan_sha256':sm['plan_sha256'],
  'source_state_sha256':state['source_state_sha256'],'input_token':token,
  'scenario_scope':'real prefill KV; external greedy input sampling and stage loading, transition timing excluded'}
 (a.output/'assets.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({'assets':len(rows),'input_token':token,'source_state_sha256':state['source_state_sha256']}))
if __name__=='__main__':main()
