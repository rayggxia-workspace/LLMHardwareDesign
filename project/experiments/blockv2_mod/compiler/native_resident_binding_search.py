"""Bounded state-aware binding refinement of a legal range-frontier order.

The original DP explores ready ranges and bindings. This second beam compares
bindings against actual committed SRAM state in that order, retaining the
original binding sequence as a non-regression alternative. No optimality claim.
"""
from copy import deepcopy
from native_range_residency import rewrite
from native_macro_work import measure

def refine(tasks,base_plan,get_candidate,*,width=4):
 table={t['id']:t for t in tasks}
 def initial():return {'resident':{},'ends':{},'resources':{},'rows':[],'bindings':{},'makespan':0,'traffic':0,'saved':0}
 def step(state,name,binding):
  task=table[name];candidate=get_candidate(name,binding['id'])
  transformed,resident=rewrite(candidate,state['resident']);work=measure(transformed)
  start=max([state['ends'][p] for p in task['after']]+[state['resources'].get(r,0) for r in binding['resources']]+[0])
  end=start+work['work_units']
  b={**binding,'ticks':work['work_units'],
     'external_read_words':(work['descriptor_bytes']+work['ddr_read_bytes_upper']+15)//16,
     'external_write_words':(work['ddr_write_bytes']+15)//16}
  result={'resident':resident,'ends':dict(state['ends'],**{name:end}),'resources':dict(state['resources']),
    'rows':state['rows']+[{'id':name,'binding':b['id'],'site':b['site'],'start':start,'end':end}],
    'bindings':dict(state['bindings'],**{name:b}),'makespan':max(state['makespan'],end),
    'traffic':state['traffic']+b['external_read_words']+b['external_write_words'],
    'saved':state['saved']+len(transformed['resident_load_elisions'])}
  for r in b['resources']:result['resources'][r]=end
  return result
 beam=[initial()];baseline=initial()
 for row in base_plan['tasks']:
  name=row['id'];choices=table[name]['bindings']
  baseline=step(baseline,name,next(b for b in choices if b['id']==row['binding']))
  next_states=[step(state,name,b) for state in beam for b in choices]
  next_states.append(baseline)
  # Equal progress; resource clocks and resident words distinguish future cost.
  unique={}
  for state in next_states:
   key=(tuple(sorted(state['resources'].items())),
        tuple((o,tuple(sorted(w.items()))) for o,w in sorted(state['resident'].items())))
   rank=(state['makespan'],state['traffic'])
   if key not in unique or rank<(unique[key]['makespan'],unique[key]['traffic']):unique[key]=state
  beam=sorted(unique.values(),key=lambda s:(s['makespan'],s['traffic']))[:width]
 best=min(beam+[baseline],key=lambda s:(s['makespan'],s['traffic']))
 resolved=[{**t,'bindings':[best['bindings'][t['id']]]} for t in tasks]
 plan={**base_plan,'tasks':best['rows'],'makespan':best['makespan'],'external_words':best['traffic'],
       'wire_cost':0,'resident_load_elisions':best['saved'],
       'residency_refinement':{'width':width,'order':'bounded ready-range DP order',
        'original_binding_sequence_retained':True,'global_optimum_proven':False}}
 return resolved,plan
