from pathlib import Path
import json,hashlib
p=Path.cwd();models=json.loads((p/'models.json').read_text());rows=lambda f:{z[0]:z[1:] for z in [x.split('\t') for x in f.read_text().splitlines()]};a=rows(p/'topology-before.tsv');b=rows(p/'topology-after.tsv');assert set(a)==set(b)
plan={x.split('\t')[0]:x.split('\t')[1:] for x in (p/'plan.tsv').read_text().splitlines()[1:]};protected=set((p/'protected-instances.txt').read_text().splitlines());changed={}
for n,x in a.items():
 y=b[n];assert x[1:]==y[1:],('location/orientation/connectivity changed',n)
 if x[0]!=y[0]:
  assert n not in protected and plan[n]==[x[0],y[0]]
  assert y[0] in models['choices'][x[0]] and models['models'][x[0]]['pins']==models['models'][y[0]]['pins'];changed[n]=[x[0],y[0]]
assert set(changed)==set(plan)
base=list(map(float,(p/'baseline-metrics.tsv').read_text().split()));final=list(map(float,(p/'final-metrics.tsv').read_text().split()));assert final[0]>=base[0]-1e-6 and final[1]>=base[1]-1e-6 and final[2]<=base[2] and final[3]<=base[3]
files=[p/n for n in ['models.json','choices.tcl','input.odb','topology-before.tsv','topology-after.tsv','plan.tsv','trials.tsv','baseline-metrics.tsv','final-metrics.tsv','best.odb','best.v','final-hold.rpt','greedy.tcl','inputs-before.sha256']]
r=dict(diagnostic_completed=True,backend_accepted=False,static_wire_model_only=True,baseline_metrics=dict(zip(['wns_ns','tns_ns','cap_count','slew_count','setup_count'],base)),final_metrics=dict(zip(['wns_ns','tns_ns','cap_count','slew_count','setup_count'],final)),sized_instances=changed,changed_count=len(changed),all_other_masters_unchanged=True,all_instance_locations_orientations_pin_to_net_connections_unchanged=True,clock_tree_and_all_top_output_drivers_unchanged=True,sizing_function_proof='Every changed cell is stateless and has exact equal per-pin direction/function/three-state signature in actual Liberty; all pins/topology unchanged.',scope='Bounded greedy resizing on actual negative max paths with source routed SPEF re-evaluated after each swap. Requires physical legalization, route, fresh extraction, timing/electrical and final formal gates before acceptance.',hashes={str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in files});(p/'receipt.json').write_text(json.dumps(r,indent=2));print(json.dumps({k:r[k] for k in ['baseline_metrics','final_metrics','changed_count']},indent=2))

assert final[5]>=base[5]-1e-6 and final[6]>=base[6]-1e-6 and final[7]<=base[7] and final[8]>=base[8]-1e-6
r['extended_metrics_fields']=['setup_wns','setup_tns','cap_count','slew_count','setup_count','hold_wns','hold_tns','hold_count','target_trace_slack'];r['extended_baseline_metrics']=base;r['extended_final_metrics']=final;r['scope']+=' Source baseline already includes frozen 59-instance plan; exploratory AOI221_X4 requires original-library fixture acceptance.'
(p/'receipt.json').write_text(json.dumps(r,indent=2))
