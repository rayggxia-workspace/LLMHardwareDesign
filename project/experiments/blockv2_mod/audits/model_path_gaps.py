"""Audit all graph tasks; never replace a failed stage with a successful whole plan."""
from pathlib import Path
from collections import Counter
import json,sys,traceback,copy,hashlib
from value_layout import build as layout
from operand_recipes import lower
from native_macro_graph import Frontend
ROOT=Path(__file__).resolve().parents[1];EV=ROOT/'evidence/architecture-revision-185'
out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=False)
hw=json.loads((ROOT/'hardware/blockv2-mod-shared-memory.json').read_text())
services=json.loads((ROOT/'hardware/service-controller-contracts.json').read_text())['services']
catalog=json.loads((EV/'remaining-benchmark-source-catalog.json').read_text())
allrows=[]
for model in catalog['model_layers']:
 for entry in model['graphs']:
  name=model['model_layer']+'-'+entry['flavor']
  folder=EV/'remaining-benchmark-conversion-115202'/name/'graph'
  g=json.loads((folder/'native-recipe-graph.json').read_text())
  producers={v:t['id'] for t in g['tasks'] for v in t['outputs']}
  bad=[]
  for v,row in g['values'].items():
   if any(type(n) is not int or n<=0 for n in row['shape']):
    bad.append({'value':v,'shape':row['shape'],'dtype':row.get('dtype'),
      'constant':row.get('constant'),'producer':producers.get(v),
      'users':[t['id'] for t in g['tasks'] if v in t['inputs']]})
  report={'case':name,'source_model_sha256':g['source_model_sha256'],
   'invalid_layout_values':bad,'tasks':[],'whole_plan_accepted':False}
  try:l=layout(g)
  except Exception as e:
   report['layout_error']=str(e);l=None
  for t in g['tasks']:
   row={'id':t['id'],'kind':t['kind'],'inputs':t['inputs'],'outputs':t['outputs'],
    'input_shapes':t.get('input_shapes'),'output_shapes':t.get('output_shapes'),
    'details':t['details'],'source_operations':t['source_operations']}
   if l is None:row['stage']='layout_blocked'
   else:
    one=dict(g,tasks=[dict(t,after=[])])
    try:
     recipe=lower(one,l);row['operand_lowered']=True
     row['tiles']=len(recipe['tasks'][0]['tiles'])
     if t['kind']=='View':row['stage']='address_view_only'
     else:
      frontend=Frontend(one,recipe,l,hw,services,18503)
      task=recipe['tasks'][0];options=frontend.options(task)
      errors=[];valid=[]
      for option in options:
       try:
        c=frontend.encode(task,option)
        valid.append({'calls':len(c['calls']),'binding':c['binding']})
       except Exception as e:errors.append({'error_type':type(e).__name__,'error':str(e)})
      row.update(stage='candidate_probe',valid_candidates=valid,errors=errors)
    except Exception as e:
     row.update(stage='isolated_task_failure',error_type=type(e).__name__,error=str(e))
   report['tasks'].append(row)
  (out/(name+'.json')).write_text(json.dumps(report,indent=2)+'\n')
  summary={'case':name,'invalid_values':len(bad),'stages':dict(Counter(t['stage'] for t in report['tasks'])),
   'failure_kinds':dict(Counter((t['kind']+': '+t.get('error','')) for t in report['tasks'] if t['stage']=='isolated_task_failure')),
   'candidate_failures':dict(Counter(t['kind']+': '+e['error'] for t in report['tasks'] for e in t.get('errors',[])))}
  allrows.append(summary);print(json.dumps(summary),flush=True)
(out/'summary.json').write_text(json.dumps({'scope':'all tasks audited; isolated candidate probes do not prove whole-graph compilation','results':allrows},indent=2)+'\n')
