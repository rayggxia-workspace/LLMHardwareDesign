"""Retain a sealed executable incumbent under the same structural objective."""
from copy import deepcopy
from native_macro_work import measure
from native_joint_search import digest
def choose(candidate,incumbent):
 for p in (candidate,incumbent):
  if p.get('plan_sha256')!=digest({k:v for k,v in p.items() if k!='plan_sha256'}):
   raise ValueError('unsealed comparison plan')
 for key in ('graph_sha256','hardware','storage'):
  if candidate[key]!=incumbent[key]:raise ValueError('incumbent input mismatch: '+key)
 def cost(p):
  totals=[measure({'calls':[dict(c,index=0,after=[])]},cost_model=candidate.get('search_plan',{}).get('cost_model','structural/1')) for c in p['calls']]
  return (sum(c['ddr_read_bytes_upper']+c['ddr_write_bytes'] for c in totals),
          sum(c['work_units'] for c in totals))
 a,b=cost(candidate),cost(incumbent)
 chosen=deepcopy(candidate if a<=b else incumbent)
 chosen['exported_values']=candidate['exported_values']
 chosen['incumbent_comparison']={'candidate_plan_sha256':candidate['plan_sha256'],
  'incumbent_plan_sha256':incumbent['plan_sha256'],'candidate_cost':a,'incumbent_cost':b,
  'selected':'joint_candidate' if a<=b else 'incumbent',
  'objective':'DDR byte upper bound, then serialized structural work; not measured throughput'}
 chosen.pop('plan_sha256');chosen['plan_sha256']=digest(chosen)
 return chosen
