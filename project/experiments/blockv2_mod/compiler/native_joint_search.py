"""Joint ready-range, native binding, dirty retention and last-reader search."""
from dataclasses import dataclass
from functools import lru_cache
from hashlib import sha256
from collections import defaultdict
from pathlib import Path
import gzip,json,struct
from native_dirty_memory import transform
from native_macro_work import measure

def digest(value):return sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def input_pages(task,regions):
 pages=set()
 for tile in task['tiles']:
  for access in tile.get('read',[])+tile.get('key_rows',[])+tile.get('value_rows',[]):
   base=regions[access['root']]['base'];size=regions[access['root']]['element_bytes']
   for s in access['segments']:
    a=base+s['source_element']*size;b=a+s['elements']*size
    pages.update(range(a//512*512,((b+511)//512)*512,512))
 return pages

@dataclass
class History:
 previous:object
 task:int
 binding:str
 keep:bool

def select(frontend,directory,*,depth=2,width=4,ready_limit=4,exports=(),progress=print):
 if not frontend.joint or frontend.range_tiles!=1:raise ValueError('joint native ranges required')
 directory=Path(directory);manifest=json.loads((directory/'manifest.json').read_text())
 if manifest['graph_sha256']!=frontend.graph_hash or manifest['storage']!=frontend.storage or manifest['hardware']!=frontend.hardware:raise ValueError('candidate inputs differ')
 rows=[r for r in manifest['tasks'] if r['kind']!='View'];names=[r['id'] for r in rows];ids={n:i for i,n in enumerate(names)}
 tasks=[frontend.tasks[n] for n in names];regions=frontend.storage['regions'];count=len(tasks)
 capacities={o:frontend.hardware['macro_instances'][g['private_sram']]['source_profile']['capacity_bytes']//16 for o,g in frontend.hardware['control_groups'].items()}
 deps=[sum(1<<ids[n] for n in frontend.after[t['id']]) for t in tasks]
 children=[[] for _ in tasks]
 for i,t in enumerate(tasks):
  for p in frontend.after[t['id']]:children[ids[p]].append(i)
 read_pages=[input_pages(t,regions) for t in tasks];produced={};users=defaultdict(int)
 for i,task in enumerate(tasks):
  for a in read_pages[i]:users[a]|=1<<i
  for tile in task['tiles']:
   w=tile['write'];r=regions[w['value']];a=r['base']+w['element_offset']*r['element_bytes'];b=a+w['elements']*r['element_bytes']
   for address in range(a//512*512,((b+511)//512)*512,512):
    if address not in produced:produced[address]=len(produced)
 export_pages=set()
 for value in exports:
  r=regions[value];export_pages.update(range(r['base']//512*512,((r['base']+r['bytes']+511)//512)*512,512))
 def parent_of(t):return t.get('source_operator',t.get('range_parent',t['id']))
 parents={parent_of(t) for t in tasks}
 parent_parts={p:sum(1<<i for i,t in enumerate(tasks) if parent_of(t)==p) for p in parents}
 parent_deps={p:set() for p in parents}
 for i,t in enumerate(tasks):
  p=parent_of(t)
  for dep in frontend.after[t['id']]:
   q=parent_of(frontend.tasks[dep])
   if p!=q:parent_deps[p].add(q)
 parent_order=[]
 def visit(p):
  if p in parent_order:return
  for q in sorted(parent_deps[p]):visit(q)
  parent_order.append(p)
 for p in sorted(parents):visit(p)
 @lru_cache(maxsize=256)
 def legal(done):
  longest={}
  for p in parent_order:
   bits=parent_parts[p];opened=bool(done&bits) and done&bits!=bits
   longest[p]=int(opened)+max((longest[q] for q in parent_deps[p]),default=0)
   if longest[p]>depth:return False
  return True
 @lru_cache(maxsize=32)
 def candidates(i):
  path=directory/rows[i]['candidate_file']
  if sha256(path.read_bytes()).hexdigest()!=rows[i]['candidate_sha256']:raise ValueError('candidate seal')
  task=tasks[i]
  workspace=frontend.storage['candidate_workspaces'].get(task.get('storage_parent',task.get('range_parent',task['id'])))
  with gzip.open(path,'rt') as stream:result=[json.loads(line) for line in stream]
  for c in result:
   keys=[]
   if workspace is not None:
    for call in c['calls']:
     raw=bytes.fromhex(call['descriptor_hex']);schema=int.from_bytes(raw[:4],'little')
     offset=112 if schema==0x3152504d else 24 if schema in (0x314c5244,0x31535744) else None
     if offset is not None:
      address=struct.unpack_from('<Q',raw,offset)[0]
      if workspace['base']<=address<workspace['base']+workspace['bytes']:
       keys=['DDR_workspace:'+str(workspace['base'])];break
   c.update(_input_pages=read_pages[i],_capacity_words=capacities,_workspace=workspace,_workspace_keys=keys)
  return result
 # Costs are a structural proxy, not calibrated cycle predictions.
 minimum=[];baseline=[];candidate_owners=[]
 for i in range(count):
  options=candidates(i);costs=[measure(c) for c in options]
  candidate_owners.append({o for c in options for o in c['groups']})
  minimum.append(min(c['work_units'] for c in costs))
  baseline.append(min(c['ddr_read_bytes_upper']+c['ddr_write_bytes'] for c in costs))
  if i%2000==0:progress(json.dumps({'cost_inputs_loaded':i,'of':count}))
 all_min=sum(minimum);all_bytes=sum(baseline)
 ready=tuple(i for i,p in enumerate(deps) if not p)
 initial={'done':0,'ready':ready,'state':{'memory':{},'backed':0},'ends':{},'resources':{},
  'time':0,'bytes':0,'remaining':all_min,'remaining_bytes':all_bytes,'history':None}
 beam=[initial];expanded=0
 for step in range(count):
  next_beam=[]
  for label in beam:
   # Prefer a ready consumer of resident data, but retain other ready actions.
   resident={v['address'] for pages in label['state']['memory'].values() for v in pages.values()}
   def preference(i):
    # A producer can unlock a consumer of a dirty resident sibling.
    # This is a tie breaker, never a fabricated latency or traffic saving.
    unlocked=sum(len(read_pages[c]&resident) for c in children[i]
     if deps[c] & (label['done'] | (1<<i)) == deps[c])
    return -(len(read_pages[i]&resident)+unlocked),i
   choices=[i for i in sorted(label['ready'],key=preference) if legal(label['done']|(1<<i))][:ready_limit]
   for i in choices:
    done=label['done']|1<<i
    if not legal(done):continue
    for candidate in candidates(i):
     for keep in (True,False):
      encoded,state,events=transform(candidate,label['state'],keep=keep,produced=produced,users=users,done=done,exports=export_pages)
      work=measure(encoded);owners={c['group'] for c in encoded['calls']}|set(candidate['groups'])
      resource_keys=owners|set(candidate['_workspace_keys'])
      start=max([label['ends'][p] for p in frontend.after[names[i]]]+[label['resources'].get(o,0) for o in resource_keys]+[0])
      end=start+work['work_units'];resources={**label['resources'],**{o:end for o in resource_keys}}
      ends={**label['ends'],names[i]:end}
      # Retain only completion times still referenced by an unscheduled consumer.
      for parent in frontend.after[names[i]]:
       if all(done>>child&1 for child in children[ids[parent]]):ends.pop(parent,None)
      ready=set(label['ready']);ready.remove(i)
      ready.update(c for c in children[i] if deps[c]&done==deps[c])
      by_owner={o:{v['address'] for v in pages.values()} for o,pages in state['memory'].items()}
      credit=sum(max((len(read_pages[c]&by_owner.get(o,set())) for o in candidate_owners[c]),default=0) for c in ready)
      next_beam.append({'done':done,'ready':tuple(sorted(ready)),'state':state,'ends':ends,'resources':resources,
       'time':max(label['time'],end),'bytes':label['bytes']+work['ddr_read_bytes_upper']+work['ddr_write_bytes'],
       'remaining':label['remaining']-minimum[i],'remaining_bytes':label['remaining_bytes']-baseline[i],
       'history':History(label['history'],i,candidate['binding'],keep),
       'handoff_priority':preference(i)[0],'ready_resident_credit':credit})
      expanded+=1
  if not next_beam:raise ValueError('joint frontier exhausted at '+str(step))
  # DDR objective. Remaining baseline normalizes unequal work at equal task count.
  next_beam.sort(key=lambda s:(s['bytes']+s['remaining_bytes'],s.get('handoff_priority',0),-s.get('ready_resident_credit',0),s['time']+s['remaining']//9))
  beam=next_beam[:width]
  if step%100==0:progress(json.dumps({'joint_step':step,'of':count,'expanded':expanded,'ddr_proxy':beam[0]['bytes']}))
 best=min(beam,key=lambda s:(s['bytes'],s['time']))
 actions=[];history=best['history']
 while history:actions.append(history);history=history.previous
 actions.reverse()
 return emit(frontend,actions,tasks,rows,candidates,produced,users,export_pages,depth,width,expanded,best,progress=progress)

def emit(frontend,actions,tasks,rows,candidates,produced,users,exports,depth,width,expanded,best,progress=print):
 state={'memory':{},'backed':0};done=0;identities=dict(frontend.initial_ids)
 calls=[];selected=[];events=[];ends={};owner_ends={};connections={}
 for action in actions:
  i=action.task;task=tasks[i];options=frontend.options(task)
  ordinal=next(j for j,c in enumerate(candidates(i)) if c['binding']==action.binding)
  original=frontend.encode(task,options[ordinal],identities)
  identities.update(original.get('next_identities',{}))
  original['_input_pages']=candidates(i)[ordinal]['_input_pages']
  original['_capacity_words']=candidates(i)[ordinal]['_capacity_words']
  original['_workspace']=candidates(i)[ordinal]['_workspace']
  original['_workspace_keys']=candidates(i)[ordinal]['_workspace_keys']
  done|=1<<i
  c,state,trace=transform(original,state,keep=action.keep,produced=produced,users=users,done=done,exports=exports)
  owners={call['group'] for call in c['calls']}|set(c['groups'])
  # Re-admit rewritten descriptors, including any spill from another owner.
  from native_candidate_resources import admit
  c['groups']=sorted(owners)
  c['srams']={frontend.hardware['control_groups'][o]['private_sram']:{'word':0,'words':original['_capacity_words'][o]} for o in owners}
  c['required_registered_adapters']=sorted(set(c['required_registered_adapters'])|{n for n,a in frontend.hardware['adapter_instances'].items() if a['control_owner'] in owners and a.get('macro') in c['srams']})
  c=admit(c,frontend.hardware)
  external=set()
  for parent in frontend.after[task['id']]:external.update(ends[parent])
  resource_keys=owners|set(original['_workspace_keys'])
  for owner in resource_keys:external.update(owner_ends.get(owner,()))
  first=len(calls)
  for call in c['calls']:
   copy=dict(call,index=len(calls),source_task=task['id'])
   copy['after']=[first+j for j in call['after']] if call['after'] else sorted(external)
   calls.append(copy)
  terminal={len(calls)-1} if c['calls'] else external
  ends[task['id']]=terminal
  for owner in resource_keys:owner_ends[owner]=terminal
  for edge in original.get('connections',[]):connections[digest(edge)]=edge
  cost=measure(c);events.append({'source_task':task['id'],'events':trace})
  selected.append({'source_task':task['id'],'binding':action.binding,'keep':action.keep,
   'first_call':first,'call_count':len(c['calls']),'groups':sorted(owners),
   'resources':sorted(set(c['required_macro_leases']+c['required_controller_leases']+c['required_registered_adapters']+original['_workspace_keys'])),
   'work_estimate':cost})
  for pages in state['memory'].values():
   for page in pages.values():
    address=page['address']
    if address in exports and address in produced and not(state['backed']>>produced[address]&1):
     raise ValueError('exported output left dirty')
  if len(selected)%1000==0:progress(json.dumps({'emitted_ranges':len(selected),'of':len(actions),'calls':len(calls)}))
 actual_bytes=sum(x['work_estimate']['ddr_read_bytes_upper']+x['work_estimate']['ddr_write_bytes'] for x in selected)
 if actual_bytes!=best['bytes']:raise ValueError('selected native replay differs from searched traffic')
 result={'schema':'macro-native-selected-plan/1','graph_sha256':frontend.graph_hash,'selection':selected,
  'calls':calls,'storage':frontend.storage,'hardware':frontend.hardware,
  'wiring':{'connections':list(connections.values()),'physical_binding_complete':False,
            'scope':'selected actual macro endpoint requirements; product assembly binding required'},
  'search_hardware':{'topology_id':frontend.hardware['native_dispatch_overlay']['topology_id']},
  'search_plan':{'status':'planned','algorithm':'joint-native-dirty-range-beam/1','depth':depth,'width':width,
   'depth_unit':'source_graph_operator','expanded':expanded,'ddr_bytes_upper':actual_bytes,'makespan_proxy':best['time'],'global_optimum_proven':False},
  'search_verification':{'emission_traffic_matches_search':True,'independent_execution_pending':True},
  'dirty_lifecycle':events,'exported_pages':sorted(exports),'delivery_accepted':False,'timing_calibrated':False,
  'timing_scope':'structural work proxy; no cycle/throughput claim','wire_optimization_performed':False,
  'range_tiles':1,'range_parts':frontend.range_parts,'joint':True,
  'view_aliases':{n:t['alias'] for n,t in frontend.tasks.items() if t['kind']=='View'}}
 for a in exports:
  if a in produced and not(state['backed']>>produced[a]&1):raise ValueError('missing final exported DDR commit')
 result['plan_sha256']=digest(result);return result
