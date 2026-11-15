"""Unified graph-to-candidates frontend. No old plans or implicit group wiring."""
from pathlib import Path
from hashlib import sha256
from collections import Counter
import json,gzip
from native_macro_storage import allocations
from native_resource_bindings import candidates as bindings
from native_control_routes import profile
from native_local_projection_candidates import candidate as projection
from native_macro_ffn_candidates import candidate as ffn
from native_macro_attention_candidates import candidate as attention
from native_macro_add_candidates import candidate as add
from native_macro_rope_candidates import candidate as rope
from native_macro_rms_candidates import candidate as rms
from native_macro_gather_candidates import candidate as gather
from native_macro_concat_candidates import candidate as concat
from native_candidate_resources import admit
from check_pr185_control_admission import validate as admit_controls
CANONICAL_OWNERS=('P0','P1','P2','C0','U0','J0','F0','U1','J1')
def graph_dependencies(recipes):
 tasks={t['id']:t for t in recipes['tasks']}
 if len(tasks)!=len(recipes['tasks']):raise ValueError('duplicate graph task')
 resolved={};visiting=set();order=[]
 def visit(name):
  if name in resolved:return resolved[name]
  if name not in tasks:raise ValueError('missing dependency '+name)
  if name in visiting:raise ValueError('cyclic graph dependency '+name)
  visiting.add(name);deps=set()
  for parent in tasks[name]['after']:
   upstream=visit(parent)
   deps.update(upstream if tasks[parent]['kind']=='View' else {parent})
  visiting.remove(name);resolved[name]=sorted(deps);order.append(name)
  return resolved[name]
 for name in tasks:visit(name)
 return tasks,resolved,order
class Frontend:
 def __init__(self,graph,recipes,layouts,hardware,services,topology,*,range_tiles=0,joint=False,independent_ranges=False):
  hashes={d['source_model_sha256'] for d in (graph,recipes,layouts)}
  if len(hashes)!=1:raise ValueError('graph/recipe/layout source mismatch')
  self.control_admission=admit_controls(hardware)
  self.hardware=json.loads(json.dumps(hardware))
  if set(hardware['control_groups'])!=set(CANONICAL_OWNERS):raise ValueError('nine control owners required')
  self.hardware['native_dispatch_overlay']=profile(self.hardware,topology,{n:i for i,n in enumerate(CANONICAL_OWNERS)})
  self.storage=allocations(graph,recipes,layouts,{'virtual_memory':{'address_bits':48}})
  self.joint=joint;self.independent_ranges=independent_ranges
  if independent_ranges and not joint:raise ValueError('independent ranges require explicit joint workspace leases')
  if joint:
   from native_joint_recipes import lower
   recipes=lower(recipes)
  self.tasks,self.after,self.order=graph_dependencies(recipes)
  self.range_tiles=range_tiles;self.range_parts={}
  if range_tiles:
   from native_range_frontier import expand
   self.tasks,self.after,self.order,self.range_parts=expand(self.tasks,self.after,self.order,tiles_per_range=range_tiles,serialize_ranges=not independent_ranges)
  self.bindings={s['module']:bindings(s,self.hardware,self.hardware['control_groups']) for s in services}
  self.graph_hash=graph['source_model_sha256']
  self.initial_ids={'first_session':1,'generation':1,'job':1,'epoch':1,'tensor':1,'version':1,
                    'rf_object_base':0,'record_sequence_base':0}
 def options(self,task):
  b=self.bindings;k=task['kind']
  if k=='Gated':return [{'binding':x} for x in b['gated_s32_service_controller']]
  if k=='MatMul':return [{'binding':x} for x in b['projection_local_service_controller']]
  if k=='SwiGLUFFN':return [{'projection_binding':p,'gated_binding':g} for p in b['projection_local_service_controller'] for g in b['gated_s32_service_controller']]
  if k=='Attention':return [{'dot_binding':e,'n_binding':n} for e in b['e32_dot_service_controller'] for n in b['n32_service_controller']]
  if k=='RMSNorm':return [{'n_binding':n,'e_binding':e} for n in b['n32_service_controller'] for e in b['rms_apply_native_service_controller']]
  if k in ('Add','RoPE'):
   name='add_s32_service_controller' if k=='Add' else 'rope_native_service_controller'
   return [{'binding':x} for x in b[name]]
  if k in ('Gather','Concat'):
   schema=0x32485447 if k=='Gather' else 0x314c5244
   return [{'owner':t['group']} for t in self.hardware['native_dispatch_overlay']['targets']
           if any(r['schema']==schema for r in t['routes'])]
  raise ValueError('no corrected native candidate family '+k)
 def encode(self,task,option,identities=None):
  k=task['kind'];s=self.storage;workspace=s['candidate_workspaces'].get(task.get('storage_parent',task.get('range_parent',task['id'])))
  regions={n:r for n,r in s['regions'].items() if workspace is None or n!=workspace['value']}
  common={'regions':regions,'hardware':self.hardware,**option}
  if k in ('MatMul','SwiGLUFFN'):
   result=(projection if k=='MatMul' else ffn)(task,**common,weights=s['weights'],
    identities=dict(identities or self.initial_ids),workspace=workspace)
  elif k in ('Attention','RMSNorm'):
   result=(attention if k=='Attention' else rms)(task,**common,workspace=workspace)
  elif k=='Gated':
   from native_macro_gated_candidates import candidate
   result=candidate(task,**common)
  else:result={'Add':add,'RoPE':rope,'Gather':gather,'Concat':concat}[k](task,**common)
  return admit(result,self.hardware)
 def export(self,out,progress=print):
  out=Path(out);out.mkdir(parents=True,exist_ok=True);rows=[];counts=Counter()
  for name in self.order:
   task=self.tasks[name]
   if task['kind']=='View':
    alias=task['alias']
    if alias['root'] not in self.storage['regions']:raise ValueError('view root has no allocation')
    rows.append({'id':name,'kind':'View','after':self.after[name],'alias':alias});counts['views']+=1;continue
   options=self.options(task)
   if not options:raise ValueError('no candidates for '+name)
   file='candidates/'+sha256(name.encode()).hexdigest()+'.jsonl.gz'
   target=out/file;target.parent.mkdir(exist_ok=True)
   summaries=[]
   with gzip.open(target,'wt') as stream:
    for option in options:
     c=self.encode(task,option)
     summaries.append({'binding':c['binding'],'calls':len(c['calls']),
      'macro_leases':c['required_macro_leases'],'controller_leases':c['required_controller_leases']})
     stream.write(json.dumps(c,separators=(',',':'))+'\n')
     counts['candidates']+=1;counts['calls']+=len(c['calls'])
   rows.append({'id':name,'kind':task['kind'],'after':self.after[name],
    'candidate_file':file,'candidate_sha256':sha256(target.read_bytes()).hexdigest(),'candidates':summaries})
   counts['tasks']+=1;counts[task['kind']+'_tasks']+=1
   if counts['tasks']%50==0:progress(json.dumps(dict(counts)))
  manifest={'schema':'macro-native-candidate-graph/1','graph_sha256':self.graph_hash,'tasks':rows,
   'counts':dict(counts),'storage':self.storage,'hardware':self.hardware,
   'independent_ranges':self.independent_ranges,'joint':self.joint,'range_tiles':self.range_tiles,'range_parts':self.range_parts,
   'whole_plan_accepted':False,'scope':'unselected candidates from one graph/base/storage; global DP, wiring and execution pending'}
  (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
  progress(json.dumps(dict(counts)));return manifest
