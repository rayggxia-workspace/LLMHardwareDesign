from pathlib import Path
import json,hashlib,time,sys,traceback
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');root=b/'r256-composition-453';out=b/'r256-final-chain-binding-audit-864';assert not out.exists();out.mkdir();sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();r=dict(passed=False,whole_system_qualified=False,time=time.time(),candidates=[])
sys.path.insert(0,str(b/'source-537/project/experiments/control_v1'));from boundary_links import verilog
try:
 graph=root/'topology/boundary-graph.json';assert sha(graph)=='49ba0e348f3583f6facdf60e771fe6f1329b46fe5aac872c3828d4b61ddb1a68';signal=json.loads(graph.read_text());assert len(signal['instances'])==345 and'macro_r'in signal['instances']
 mappings=[('sready855-native-prefix-fullchains',[8560,8561])]
 for record,seeds in mappings:
  tasks=json.loads((b/'route-selection-102'/record/'tasks.json').read_text())['tasks']
  for seed in seeds:
   candidates=[t for t in tasks if('-'+str(seed))in Path(t['path']).stem];assert len(candidates)==7
   for t in candidates:assert sha(t['path'])==t['sha256']
   route=next(t['spec']for t in candidates if t['spec']['script']=='system_upper.py');assert '--route-ordinary-endpoint-escape'in route['args']and '--route-weighted-bidirectional'in route['args']and '--route-trace-phases'in route['args']and route['args'][route['args'].index('--seed')+1]=='4662'and route['args'][route['args'].index('--route-ordinary-zero-maze')+1]=='16384'and '--route-native-prefix-first'in route['args']and route['args'][route['args'].index('--route-pin-access')+1]=={8560:'all',8561:'after-native'}[seed]and route['forecast_gib']==64;assert str(b/'r256-native-prefix-regression-855/receipt.json')in route['requires'];assert str(b/'r256-maze-legacy45-byte-audit-858/receipt.json')in route['requires'];joint=next(t['spec']for t in candidates if'--acceptance'in t['spec']['args']);a=joint['args'];cp=Path(a[a.index('--acceptance')+1]);cfg=json.loads(cp.read_text());assert set(cfg)=={'geometry','pg_audit','function_run','topology','signal_graph','timing'}and set(cfg['timing'])=={'low','base','high'}
   scene=root/'upper-candidates'/str(seed);assert cfg['geometry']==str(scene/'geometry')and cfg['pg_audit']==str(scene/'pg-audit')and a[a.index('--route')+1]==str(scene/'route')and a[a.index('--graph')+1]==str(scene/'route/physical-graph.json')and a[a.index('--out')+1]==str(scene/'delivery')
   assert cfg['signal_graph']==str(graph);topology=Path(cfg['topology']);module=json.loads(topology.read_text())['modules']['control_system'];assert{n:v['type']for n,v in module['cells'].items()}==signal['instances']
   fn=Path(cfg['function_run']);fr=json.loads((fn/'receipt.json').read_text());assert fr['passed']and fr['R_integrated']and fr['real_program_count']==8 and fr['physical_instances']==345 and fr['inputs'][str(graph)]==sha(graph)and fr['inputs'][str(topology)]==sha(topology)
   for name,d in fr['initial_results'].items():assert d['passed']and d['real_compositions']==8 and d['cpu_tensor_moves']==0 and d==json.loads((fn/name).read_text())
   assert(fn/'actual-qualified-top.v').read_text()==verilog(module)
   for variant,path in cfg['timing'].items():assert Path(path).parent==scene/'timing' and Path(path).name==variant
   assert set(fr['initial_results'])=={'initial-1-162.json','initial-2-162.json','initial-2-163.json'}
   geometry=next(t['spec']for t in candidates if '-geometry-'in Path(t['path']).stem);pg=next(t['spec']for t in candidates if '-pg-'in Path(t['path']).stem)
   assert geometry['args'][geometry['args'].index('--out')+1]==cfg['geometry']and pg['args'][pg['args'].index('--out')+1]==cfg['pg_audit']and pg['args'][pg['args'].index('--pg-audit')+1]==cfg['geometry']
   for variant,path in cfg['timing'].items():
    t=next(t['spec']for t in candidates if t['spec']['script']=='system_sta.py'and t['spec']['args'][t['spec']['args'].index('--rc-variant')+1]==variant);ta=t['args'];assert ta[ta.index('--out')+1]==path and ta[ta.index('--upper-geometry')+1]==cfg['geometry']and'--stitch-native-access'in ta and'--audit-native-coverage'in ta
   for folder in ['r256-padding-program-events-473','r256-padding-program-event-audit-480']:
    p=b/folder/'receipt.json';assert str(p)in route['requires']and json.loads(p.read_text())['passed']
   for key in ['--reuse-placement','--route-residual-budget']:
    value=route['args'][route['args'].index(key)+1];assert('5380'in value)
   r['candidates'].append(dict(candidate=seed,config=str(cp),config_sha256=sha(cp),source_roots=sorted(set(t['spec']['source_root']for t in candidates)),function_folder=str(fn),function_receipt_sha256=sha(fn/'receipt.json'),topology_sha256=sha(topology),signal_graph_sha256=sha(graph),states=345,programs=8,current453_top_verilog_exact=True,trace_and_audit_route_prerequisites=True,own_future_geometry_pg_all3timing_paths=True,seven_specs_unchanged=True))
 r.update(passed=True,scope='Read-only final-chain binding audit of current S5380 native-first/pin-reservation candidates8560/8561 and14 immutable task specifications. Exact6key acceptance schema, own future real route/geometry/PG/low-base-high/delivery paths, current453 graph/345statehosts/R256, actual current453 three-initial8program function receipt and exact wired top, actual473/480 trajectory/audit route prerequisites all checked. No future route, geometry, PG, timing or system result is inherited, fabricated or executed by this audit; queued chains still must pass original final gates in compute jobs.')
except BaseException as e:r.update(error=str(e),traceback=traceback.format_exc());raise
finally:(out/'receipt.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps(dict(passed=r['passed'],candidate_count=len(r['candidates']),specifications=7*len(r['candidates']),current_function_folders=sorted(set(x['function_folder']for x in r['candidates'])))))
