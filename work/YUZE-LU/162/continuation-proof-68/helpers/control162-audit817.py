import subprocess,shlex
q=r'''from pathlib import Path
import json,hashlib,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');out=b/'r256-escape-legacy39-byte-audit-817';assert not out.exists();old=b/'r256-threshold-pattern-regression-791';new=b/'r256-endpoint-escape-regression-810';assert json.loads((new/'receipt.json').read_text())['passed'];d=json.loads((new/'directional-regression.json').read_text());assert d['passed'];w=d['weighted_bidirectional_cases'];assert w['passed']and len(w['cases'])==45 and len(w['rejected'])==22
assert sum(x['std_heap_route_and_filtered_log_exact_replay']is True for x in w['cases'])==33;assert sum(x['phase_only_exact_replay']is True for x in w['cases'])==3;assert sum(x['weight1_exact_replay']is True for x in w['cases'])==3
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();rows=[]
for p in sorted((old/'weighted-bidirectional').glob('*/router-output.txt')):
 folder=p.parent.name;np=new/'weighted-bidirectional'/folder
 assert p.read_bytes()==(np/'router-output.txt').read_bytes()
 assert(p.parent/'router-input.txt').read_bytes()==(np/'router-input.txt').read_bytes()
 filtered=lambda f:b''.join(l for l in f.read_bytes().splitlines(keepends=True)if b'routing_phase_event'not in l)
 assert filtered(p.parent/'router.log')==filtered(np/'router.log')
 rows.append(dict(folder=folder,input_sha256=sha(np/'router-input.txt'),output_sha256=sha(np/'router-output.txt'),old_output=str(p),new_output=str(np/'router-output.txt'),filtered_log_sha256=hashlib.sha256(filtered(np/'router.log')).hexdigest(),default_disabled_byte_exact=True))
assert len(rows)==39;cases=[]
for x in w['cases']:
 p=x['proof'];assert p['final_conflicts']==0 and p['independent_cross_net_occupancy']and p['independent_tree_flood'];o=p['distance_oracle'];assert o['independent_endpoint_escape_checks']==132 and o['independent_weighted_heap_order_checks']==166730 and o['independent_weighted_bidirectional_path_checks']==1200 and o['independent_resource_product_graph_checks']==120 and o['independent_bidirectional_dijkstra_checks']==100 and o['independent_directional_bidirectional_dijkstra_checks']==200
 if x['escape']:
  t=p['ordinary_endpoint_escape_trace'];cases.append(dict(mode=x['mode'],phase=x['threshold_rounds'],rounds=[r['round']for r in t],attempts=sum(r['endpoint_escape_attempts']for r in t),hits=sum(r['endpoint_escape_hits']for r in t),core_calls=sum(r['endpoint_escape_core_calls']for r in t),vertex_checks=sum(r['endpoint_escape_vertex_checks']for r in t)))
assert len(cases)==6 and sum(x['hits']for x in cases)>0
base=d['directional_bidirectional_cases'];assert len(base['cases'])==18 and sum(x['original_cost2_route_and_log_exact']is True for x in base['cases'])==6 and len(d['rejected'])==31
oldsrc=b/'source-790/project/experiments/control_v1';newsrc=b/'source-809/project/experiments/control_v1';invariants=[]
for name in ['system_geometry.py','system_sta.py','system_accept.py','final_composition.py','native_pin_load.py','native_cap_residual.py','upper_cap_bound.py','steiner_wire_bound.py','placement_residual_budget.py','resource_search.h','r256_scene.py','ordinary_zero_pattern.h','router_trial_pool.py','test_router_trial_pool.py','weighted_bidirectional.h']:
 assert sha(oldsrc/name)==sha(newsrc/name);invariants.append(dict(name=name,identical_sha256=sha(newsrc/name)))
a=(oldsrc/'tree_router.cpp').read_text();z=(newsrc/'tree_router.cpp').read_text();start='    if(pareto_wire_budget&&n<locked_count&&wire_limits[n]>=0){';end='    }else if(bidirectional_two_terminal';assert a.split(start,1)[1].split(end,1)[0]==z.split(start,1)[1].split(end,1)[0];assert a.split('struct BidirectionalSearch {',1)[1].split('\n};',1)[0]==z.split('struct BidirectionalSearch {',1)[1].split('\n};',1)[0]
out.mkdir();r=dict(passed=True,time=time.time(),whole_system_qualified=False,legacy39_byte_replays=rows,unchanged_files=invariants,original_finite_and_exact_class_unchanged=True,weighted_cases=45,old_std_heap_replays=33,trace_replays=3,weight1_replays=3,rejected_contexts=22,original_rejections=31,escape_cases=cases,regression_receipt=dict(path=str(new/'receipt.json'),sha256=sha(new/'receipt.json')),source_manifest=dict(path=str(b/'source-809/source-manifest.json'),sha256=sha(b/'source-809/source-manifest.json')),scope='Actual810 complete45case regression plus independent replay of every39 disabled-default actual output/input/filtered-log against actual791/source790. All old std byte replays and original oracles retained;132 direct escape candidate checks include unit edges/parity/obstacles/bounds/budget and shared even-proxy and occupied-source negatives per binary. Six new mixed-parity escape cases independently verified zero conflicts/physical grid edges/vias/flood/wire constraints. Fifteen final/resource/scene/prepass/pool/weighted sources and exact class/finite branch unchanged. Only bounded zero-occupancy ordinary-pair prepass; no new native block/state/storage/grid arrays or gate relaxation. Actual complete route/geometry/PG/3RC300MHz/joint evidence still required; no speed/convergence/system pass claim.')
(out/'receipt.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(dict(passed=True,legacy39_byte_replays=len(rows),cases=cases,invariants=len(invariants))))
'''
compile(q,'audit817','exec');print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)]).decode())
