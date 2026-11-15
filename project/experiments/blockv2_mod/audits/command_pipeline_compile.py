"""Compile the two graph-derived decode shapes; never reuse a history-2 plan."""
import argparse,json,hashlib
from pathlib import Path
from native_macro_graph import Frontend
from native_joint_search import select,digest
p=argparse.ArgumentParser()
p.add_argument('history',type=int,choices=(512,513));p.add_argument('output',type=Path)
p.add_argument('--hardware',type=Path,required=True);p.add_argument('--services',type=Path,required=True)
a=p.parse_args();g=Path('evidence/joint-frontier/decode512-standard')/f'graph-{a.history}'
scenario=json.loads((g/'scenario.json').read_text())
if scenario['history_positions']!=a.history or scenario['decode_steps_total']!=2:raise ValueError('wrong scenario')
data=[json.loads((g/n).read_text()) for n in ('native-recipe-graph.json','native-operand-recipes.json','native-value-layout.json')]
past=[n for n in data[0]['inputs'] if n.startswith('past_')]
present=[n for n in data[0]['outputs'] if n.startswith('present_')]
if len(past)!=72 or len(present)!=72 or any(data[0]['values'][n]['shape'][-2]!=a.history for n in past) or any(data[0]['values'][n]['shape'][-2]!=a.history+1 for n in present):
 raise ValueError('graph tensor shapes disagree with required decode history')
hardware=json.loads(a.hardware.read_text());services=json.loads(a.services.read_text())['services']
f=Frontend(*data,hardware,services,18503,range_tiles=1,joint=True,independent_ranges=True)
a.output.mkdir(parents=True,exist_ok=False)
f.export(a.output/'candidates',progress=lambda x:print(x,flush=True))
plan=select(f,a.output/'candidates',depth=2,width=4,exports=set(data[0]['outputs']),stage_resources=True,diverse=True,objective='finish_proxy',cost_model='service-payload/2',progress=lambda x:print(x,flush=True))
plan['exported_values']=sorted(data[0]['outputs']);plan.pop('plan_sha256');plan['plan_sha256']=digest(plan)
(a.output/'plan.json').write_text(json.dumps(plan,separators=(',',':'))+'\n')
(a.output/'scenario.json').write_text(json.dumps(scenario,indent=2)+'\n')
