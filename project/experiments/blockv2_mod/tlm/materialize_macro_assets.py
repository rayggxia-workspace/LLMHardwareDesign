"""Materialize graph-bound numeric inputs and ordinary W8 images from a checkpoint.

This prepares data, never schedules an operator or supplies host-computed results.
"""
import argparse,json,hashlib
from pathlib import Path
import numpy as np
import onnx
from onnx import numpy_helper
from safetensors import safe_open
from native_package_runtime import load
from pack_checkpoint_ffn import pack_native,audit_image,sha256
def main():
 p=argparse.ArgumentParser()
 for name in ('package','graph','onnx','export_receipt','output'):p.add_argument(name,type=Path)
 p.add_argument('--tokens',type=int,nargs='+',required=True)
 a=p.parse_args();manifest,payloads,_=load(a.package)
 graph=json.loads(a.graph.read_text());receipt=json.loads(a.export_receipt.read_text())
 digest=sha256(a.onnx)
 if digest!=graph['source_model_sha256'] or digest!=receipt['onnx_sha256']:
  raise ValueError('source graph/export mismatch')
 storage=json.loads(payloads['storage.json']);checkpoint=Path(receipt['checkpoint'])
 a.output.mkdir(parents=True,exist_ok=False)
 shards=sorted(checkpoint.glob('*.safetensors'));index={}
 for shard in shards:
  with safe_open(shard,framework='pt',device='cpu') as f:
   for key in f.keys():
    if key in index:raise ValueError('duplicate checkpoint key')
    index[key]=shard
 def tensor(name):
  # The exporter wraps the HF model in a single named "model" module.
  if name not in receipt['parameters'] or not name.startswith('model.'):
   raise ValueError('source input lacks exporter parameter binding: '+name)
  key=name[len('model.'):]
  if key not in index:raise ValueError('checkpoint lacks '+key)
  with safe_open(index[key],framework='pt',device='cpu') as f:
   value=f.get_tensor(key).float().numpy()
  if list(value.shape)!=receipt['parameters'][name]['shape']:
   raise ValueError('checkpoint/export shape mismatch: '+name)
  return value,key
 model=onnx.load(a.onnx)
 constants={v.name:numpy_helper.to_array(v) for v in model.graph.initializer}
 for node in model.graph.node:
  if node.op_type=='Constant' and not node.input:
   attrs={x.name:x for x in node.attribute}
   if set(attrs)=={'value'} and len(node.output)==1:
    constants[node.output[0]]=numpy_helper.to_array(attrs['value'].t)

 recipes={r['outputs'][0]:r for r in graph['offline_weight_recipes']}
 bindings=[];sources={}
 for i,req in enumerate(storage['runtime_asset_requirements']):
  path=a.output/f'asset-{i:04d}.bin'
  if req['kind']=='packed_weight':
   name=req['graph_value'];recipe=recipes[name]
   if recipe['op']!='Transpose' or recipe['attributes']!={'perm':[1,0]} or len(recipe['inputs'])!=1:
    raise ValueError('unsupported offline weight recipe '+name)
   matrix,key=tensor(recipe['inputs'][0])
   if list(matrix.shape)!=req['shape']:raise ValueError('projection shape '+name)
   error=pack_native(matrix,path);audited=audit_image(matrix,path)
   region=req;origin={'checkpoint_tensor':key,'source_graph_input':recipe['inputs'][0],
    'weight_reconstruction_relative_l2':error,'audited_records':audited}
  else:
   region=req['region'];name=region['value']
   if name=='input_ids':
    values=np.asarray(a.tokens,dtype=np.int64).reshape(req['source_shape']);origin={'tokens':a.tokens}
   elif name in constants:
    values=constants[name];origin={'onnx_initializer':name}
   else:
    values,key=tensor(name);origin={'checkpoint_tensor':key}
   if list(values.shape)!=req['source_shape'] or not np.isfinite(values).all():
    raise ValueError('invalid numeric input '+name)
   if region.get('encoding')=='signed-int32-exact':
    quant=values.astype(np.int64)
   else:quant=np.rint(values.astype(np.float64)*2.0**(-region['exponent']))
   if np.any(quant<-(1<<31)) or np.any(quant>=(1<<31)):
    raise ValueError('input quantization clips '+name)
   raw=quant.astype('<i4').tobytes()
   path.write_bytes(raw+bytes((-len(raw))%64))
  expected=(region['bytes']+63)//64*64
  if path.stat().st_size!=expected:raise ValueError('asset extent '+name)
  bindings.append({'name':name,'base':region['base'],'bytes':expected,'file':path.name,
   'sha256':sha256(path),'origin':origin})
  print(json.dumps({'prepared':i+1,'total':len(storage['runtime_asset_requirements']),'name':name}),flush=True)
 result={'schema':'macro-runtime-assets/1','plan_sha256':manifest['plan_sha256'],
  'graph_sha256':digest,'hardware_sha256':manifest['payloads']['hardware.json']['sha256'],
  'checkpoint_files_sha256':{p.name:sha256(p) for p in [*shards,checkpoint/'config.json']},
  'regions':bindings,'numerical_acceptance':False}
 (a.output/'assets.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':main()
