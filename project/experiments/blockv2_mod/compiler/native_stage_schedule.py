"""Schedule actual CALL stages under single-command local-controller contracts.

A controller/SRAM owner is reusable after its last actual CALL, not after an
unrelated owner's tail. A shared DDR workspace remains leased for the action.
No overlap inside a busy CALL or undeclared macro access is assumed.
"""
from native_macro_work import measure

def reserve(calls, resource_ends, predecessor_end=0, shared_keys=(), *, cost_model='structural/1'):
 resources=dict(resource_ends);ends=[];starts=[]
 entry=max([predecessor_end]+[resources.get(k,0) for k in shared_keys])
 for i,call in enumerate(calls):
  if any(not 0<=j<i for j in call['after']):raise ValueError('invalid stage dependency')
  start=max([entry,resources.get(call['group'],0)]+[ends[j] for j in call['after']])
  duration=measure({'calls':[dict(call,index=0,after=[])]},cost_model=cost_model)['work_units']
  ends.append(start+duration);starts.append(start);resources[call['group']]=ends[-1]
 end=max(ends,default=entry)
 for key in shared_keys:resources[key]=end
 return {'resources':resources,'start':min(starts,default=entry),'end':end,'call_ends':ends}

def dependencies(calls, first, predecessor_calls, resource_tails, shared_keys=()):
 tails={k:set(v) for k,v in resource_tails.items()};rows=[]
 entry=set(predecessor_calls)
 for key in shared_keys:entry.update(tails.get(key,()))
 for i,call in enumerate(calls):
  after=entry|tails.get(call['group'],set())|{first+j for j in call['after']}
  if any(j>=first+i for j in after):raise ValueError('stage schedule cycle')
  rows.append(dict(call,index=first+i,after=sorted(after)))
  tails[call['group']]={first+i}
 terminal={first+i for i in range(len(calls))}
 for call in calls:
  terminal.difference_update(first+j for j in call['after'])
 if not calls:terminal=entry
 for key in shared_keys:tails[key]=set(terminal)
 return rows,tails,terminal

def verify_construction(order,after):
 chosen=set()
 for task in order:
  if task in chosen:raise ValueError('duplicate construction action')
  missing=set(after[task])-chosen
  if missing:raise ValueError('consumer selected before producer: '+task)
  chosen.add(task)
 if chosen!=set(after):raise ValueError('incomplete construction')
 return {'producer_before_consumer':True,'actions':len(chosen)}

def completion_hints(calls,*,cost_model='structural/1'):
 ends=[]
 for i,c in enumerate(calls):
  if any(not 0<=j<i for j in c['after']):raise ValueError('invalid global CALL DAG')
  duration=measure({'calls':[dict(c,index=0,after=[])]},cost_model=cost_model)['work_units']
  ends.append(duration+max((ends[j] for j in c['after']),default=0))
 return ends
