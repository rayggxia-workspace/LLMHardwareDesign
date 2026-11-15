"""Initial frozen KV or causally chained committed KV for standard history512/2."""
import argparse,json,os,subprocess,sys
from pathlib import Path
import numpy as np
import onnx
from onnx import numpy_helper
from native_package_runtime import load
from macro_assets import filehash
from value_layout import contiguous_runs
p=argparse.ArgumentParser()
p.add_argument('package',type=Path);p.add_argument('output',type=Path)
p.add_argument('--static-package',type=Path,required=True);p.add_argument('--static-assets',type=Path,required=True)
p.add_argument('--previous-execution',type=Path);p.add_argument('--previous-package',type=Path)
p.add_argument('--previous-assets',type=Path)
a=p.parse_args();m,payload,_=load(a.package);storage=json.loads(payload['storage.json'])
history=513 if a.previous_execution else 512
graphdir=Path('evidence/joint-frontier/decode512-standard')/f'graph-{history}'
graph=json.loads((graphdir/'native-recipe-graph.json').read_text())
source=Path('evidence')/('cached-decode-graph-114373' if history==513 else 'cached-decode-graph-114372')
if filehash(source/'decode.onnx')!=m['graph_sha256']:raise ValueError('wrong history graph')
past={f'past_{i}_{k}' for i in range(36) for k in ('key','value')}
if set(graph['inputs'])-{'input_ids'}!=past:raise ValueError('unexpected state input set')
if history==513:
 if not a.previous_package or not a.previous_assets:raise ValueError('step2 requires actual step1 state and token')
 sm,sp,_=load(a.previous_package)
 sgdir=Path('evidence/joint-frontier/decode512-standard/graph-512')
 sg=json.loads((sgdir/'native-recipe-graph.json').read_text());sl=json.loads((sgdir/'native-value-layout.json').read_text())
 if sm['graph_sha256']!=sg['source_model_sha256']:raise ValueError('step1 not history512')
 src=json.loads(sp['storage.json']);states={}
 for name in sorted(past):
  present=name.replace('past_','present_',1)
  if present not in sg['outputs']:raise ValueError('missing prior present state')
  view=sl['values'][present];region=src['regions'][view['root']];dest=storage['regions'][name]
  if view['shape']!=graph['values'][name]['shape'] or region['exponent']!=dest['exponent']:raise ValueError('KV shape/format mismatch')
  states[name]={'source_value':present,'source_root':view['root'],'source_base':region['base'],'shape':view['shape'],'exponent':region['exponent'],'destination_base':dest['base'],'bytes':dest['bytes'],'runs':[{'destination_element':x,'source_element':y,'elements':n} for x,y,n in contiguous_runs(view)]}
 bridge=a.output.parent/(a.output.name+'-bridge.json')
 bridge.write_text(json.dumps({'schema':'native-stage-state-bridge/1','source_plan_sha256':sm['plan_sha256'],'destination_plan_sha256':m['plan_sha256'],'states':states},indent=2)+'\n')
 state=a.output.parent/(a.output.name+'-state')
 subprocess.run([sys.executable,'tlm/materialize_phase_state.py',str(bridge),str(a.previous_execution.parent/'committed-state.bin'),str(a.previous_execution),str(state)],check=True)
 subprocess.run([sys.executable,'tlm/prepare_macro_decode_assets.py',str(a.previous_package),str(a.previous_assets),str(sgdir/'native-recipe-graph.json'),str(a.previous_execution),str(state/'runtime-inputs.json'),str(a.package),str(source/'decode.onnx'),str(a.output),'--logits-value','logits'],check=True)
else:
 om,op,_=load(a.static_package);old=json.loads(op['storage.json']);assets=json.loads(a.static_assets.read_text())
 if assets['plan_sha256']!=om['plan_sha256']:raise ValueError('static source binding')
 oldrows={r['name']:r for r in assets['regions']}
 model=onnx.load(source/'decode.onnx');constants={v.name:numpy_helper.to_array(v) for v in model.graph.initializer}
 for n in model.graph.node:
  if n.op_type=='Constant' and not n.input:
   attrs={x.name:x for x in n.attribute}
   if set(attrs)=={'value'}:constants[n.output[0]]=numpy_helper.to_array(attrs['value'].t)
 a.output.mkdir(parents=True,exist_ok=False);rows=[]
 for i,req in enumerate(storage['runtime_asset_requirements']):
  region=req['region'] if req['kind']=='input_tensor' else req
  name=region['value'] if req['kind']=='input_tensor' else req['graph_value']
  target=a.output/f'asset-{i:04d}.bin';raw=None
  if name in past:raw=bytes(region['bytes']);origin={'standard_quick_frozen_zero_KV':True,'history_positions':512}
  elif name=='input_ids':raw=np.array([840],dtype='<i4').tobytes();origin={'token':840}
  elif name in constants:
   q=np.rint(constants[name].astype(np.float64)*2.0**(-region['exponent']))
   if not np.isfinite(q).all() or np.any(q<-(1<<31)) or np.any(q>=1<<31):raise ValueError('constant clipping')
   raw=q.astype('<i4').tobytes();origin={'onnx_constant':name}
  else:
   row=oldrows[name];sourcefile=a.static_assets.parent/row['file']
   if 'checkpoint_tensor' not in row['origin'] or filehash(sourcefile)!=row['sha256']:raise ValueError('not sealed static checkpoint data')
   if req['kind']=='input_tensor' and old['regions'][name]['exponent']!=region['exponent']:raise ValueError('static tensor exponent mismatch')
   if req['kind']=='packed_weight' and any(old['weights'][name][k]!=req[k] for k in ('shape','format','bytes')):raise ValueError('weight format mismatch')
   if row['bytes']!=(region['bytes']+63)//64*64:raise ValueError('static extent mismatch')
   os.link(sourcefile,target);origin=dict(row['origin'])
  if raw is not None:
   if len(raw)!=region['bytes']:raise ValueError('input extent mismatch')
   target.write_bytes(raw+bytes((-len(raw))%64))
  rows.append({'name':name,'base':region['base'],'bytes':target.stat().st_size,'file':target.name,'sha256':filehash(target),'origin':origin})
 result={'schema':'macro-runtime-assets/1','plan_sha256':m['plan_sha256'],'graph_sha256':m['graph_sha256'],'hardware_sha256':m['payloads']['hardware.json']['sha256'],'checkpoint_files_sha256':assets['checkpoint_files_sha256'],'regions':rows,'scenario_scope':'PR260 frozen-zero history512, initial token840; step2 must consume committed state'}
 (a.output/'assets.json').write_text(json.dumps(result,indent=2)+'\n')
