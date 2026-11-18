from pathlib import Path
import json,hashlib,re
p=Path.cwd();model=json.loads((p/'models.json').read_text());rows=lambda path:{a[0]:a[1:] for a in (line.split('\t') for line in path.read_text().splitlines())}
source=rows(p/'source-topology.tsv');base=rows(p/'topology-before.tsv');after=rows(p/'topology-after.tsv');assert source.keys()==base.keys()==after.keys()
baseplan={line.split('\t')[0]:line.split('\t')[1:] for line in Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/c-v28-combined-size-plan.tsv').read_text().splitlines()[1:]}
plan={line.split('\t')[0]:line.split('\t')[1:] for line in (p/'plan.tsv').read_text().splitlines()[1:]};protected=set((p/'protected-instances.txt').read_text().splitlines())
for name in source:
 a,b,c=source[name],base[name],after[name];assert a[1:]==b[1:]==c[1:],('Coordinates/orientation/pin-net change',name)
 if a[0]!=b[0]:assert name not in protected and baseplan[name]==[a[0],b[0]] and model['models'][a[0]]['pins']==model['models'][b[0]]['pins']
 if b[0]!=c[0]:assert name not in protected and plan[name]==[b[0],c[0]] and c[0] in model['choices'][b[0]] and model['models'][b[0]]['pins']==model['models'][c[0]]['pins']
assert {n for n in source if source[n][0]!=base[n][0]}==set(baseplan)
assert {n for n in base if base[n][0]!=after[n][0]}==set(plan)
names=['target_slack_ns','global_wns_ns','global_tns_ns','global_whs_ns','setup_count','hold_count','cap_count','slew_count','fanout_count']
values={phase:list(map(float,(p/(phase+'-metrics.tsv')).read_text().split())) for phase in ('source','baseline','final')}
assert all(len(x)==9 for x in values.values());b=values['baseline'];f=values['final']
assert all(f[i]>=b[i]-1e-6 for i in range(4)) and all(f[i]<=b[i] for i in range(4,9)),(b,f)
for phase in values:
 text=(p/(phase+'-target.rpt')).read_text();match=re.search(r'([-+]?\d+\.\d+)\s+slack \((?:MET|VIOLATED)\)',text);assert match and abs(float(match[1])-values[phase][0])<1e-6,('Target units/report mismatch',phase)
assert (p/'geometry-before.tsv').read_bytes()==(p/'geometry-after.tsv').read_bytes()
assert (p/'inputs-before.sha256').read_bytes()==(p/'inputs-after.sha256').read_bytes()
files=[p/n for n in ('models.json','base59-function-proof.json','choices.tcl','source-topology.tsv','topology-before.tsv','topology-after.tsv','plan.tsv','trials.tsv','source-metrics.tsv','baseline-metrics.tsv','final-metrics.tsv','source-target.rpt','baseline-target.rpt','final-target.rpt','geometry-before.tsv','geometry-after.tsv','protected-instances.txt','best.odb','best.v','planning.tcl','inputs-before.sha256','inputs-after.sha256')]
result=dict(diagnostic_completed=True,backend_accepted=False,static_wire_model_only=True,metrics={k:dict(zip(names,v)) for k,v in values.items()},additional_target_plan=plan,additional_changed_count=len(plan),base59_separately_proved=True,all_instance_coordinates_orientations_pin_net_bindings_preserved=True,FF_clock_cone_macros_selected153_preserved=True,per_cell_stateless_same_family_function_direction_tristate_signatures_equal=True,scope='Bounded to mem_wr_address[63], both up/down sizing allowed. Target changes cannot regress global setup WNS/TNS/count, hold WHS/count or cap/slew/fanout relative to explicit after-59 baseline. Qualified original wire RC is held fixed for sensitivity planning only; no legalization, reroute, new extracted timing or backend pass implied.',hashes={str(q):hashlib.sha256(q.read_bytes()).hexdigest() for q in files})
(p/'planning-receipt.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:result[k] for k in ('metrics','additional_changed_count','additional_target_plan')},indent=2))
