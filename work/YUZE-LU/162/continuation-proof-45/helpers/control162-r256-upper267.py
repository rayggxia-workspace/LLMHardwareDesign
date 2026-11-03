import subprocess,shlex
q=r'''from pathlib import Path
import json,hashlib,time,math
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');root=b/'r256-composition-274';source=b/'source-305';record=b/'route-selection-102/sready267-r256-upper';sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
if record.exists():print(json.dumps(dict(already_queued=True,record=str(record))));raise SystemExit(0)
required=[root/'selected/receipt.json',root/'topology/receipt.json',root/'native-sta/native-system-audit.json',root/'native-pin-load307/receipt.json']
ready={str(p.relative_to(b)):json.loads(p.read_text()).get('passed')if p.exists()else None for p in required}
if not all(ready.values()):print(json.dumps(dict(ready=False,dependencies=ready)));raise SystemExit(0)
manifest=root/'selected/physical.json';signal=root/'topology/boundary-graph.json';g=json.loads(signal.read_text());assert g['scene']=='r256-seven-native/1'and g['instance_count']==345 and len(g['connections'])==11122
m=json.loads(manifest.read_text());assert len(m['leaves'])==23 and m['scene']==g['scene'];pr=root/'native-pin-load307/native-pin-load.json';pin=json.loads(pr.read_text());assert json.loads((pr.parent/'receipt.json').read_text())['outputs'][pr.name]==sha(pr)
options=[]
for row in pin['placements']:
 if any(row['violations'].values()):continue
 place=Path(row['placement']);r=json.loads((place/'receipt.json').read_text());assert r['passed']and r['inputs'][str(manifest)]==sha(manifest)and r['inputs'][str(signal)]==sha(signal)
 ratio=max(max(v['optimistic_total_with_minimum_pin_ff'].values())/v['max_capacitance_ff']for v in row['rows']);options.append((ratio,place))
if not options:print(json.dumps(dict(ready=False,no_electrically_feasible_placement=True,actual_violations=[dict(placement=r['placement'],violations=r['violations'])for r in pin['placements']])));raise SystemExit(0)
chosen=min(options)[1];required+=[chosen/'receipt.json',pr];rows=[]
def add(name,script,args,deps,out,memory=32):
 p=queue/'pending'/(name+'.json');assert not p.exists()and not out.exists();spec=dict(script=script,source_root=str(source),forecast_gib=memory,requires=list(map(str,deps)),args=list(map(str,args))+['--out',str(out)]);t=p.with_suffix('.tmp');t.write_text(json.dumps(spec));t.rename(p);rows.append(dict(path=str(p),sha256=sha(p),spec=spec))
regression=b/'router-adaptive-regression-287/receipt.json';assert json.loads(regression.read_text())['passed'];required+=[regression]
for seed,weight,bidir,adaptive in [(2670,1,False,False),(2671,4,False,False),(2672,1,True,False),(2950,16,False,True),(2951,32,False,True)]:
 source=b/'source-305'
 queue=b/{2670:'dynamic-07/node7',2671:'dynamic-05/node2',2672:'dynamic-02/node3',2950:'dynamic-04/node25',2951:'dynamic-05/node4'}[seed]
 folder=root/'upper-candidates'/str(seed);route=folder/'route';geo=folder/'geometry';pg=folder/'pg-audit'
 args=['--manifest',manifest,'--graph',signal,'--pg-wrappers',root/'fixed-pg-wrappers','--pin-aware-placement','--reuse-placement',chosen,'--seed',seed,'--route-trials',16,'--route-heuristic-weight',weight,'--negotiate-priority-routes','--defer-access-vias','--lock-native-output-routes']
 if bidir:args+=['--bidirectional-two-terminal']
 if adaptive:args+=['--route-adaptive-heuristic']
 add('00-g-sready267-r256-route-'+str(seed),'system_upper.py',args,required[:4]+[chosen/'receipt.json',regression],route,32)
 common=['--manifest',manifest,'--graph',route/'physical-graph.json','--route',route]
 add('00-h-sready267-r256-geometry-'+str(seed),'system_geometry.py',common,[route/'receipt.json'],geo,64)
 add('00-i-sready267-r256-pg-'+str(seed),'system_geometry.py',common+['--pg-audit',geo],[geo/'receipt.json'],pg,32)
 timing={}
 for corner in ['low','base','high']:
  out=folder/'timing'/corner;timing[corner]=str(out)
  add('00-j-sready267-r256-sta-'+str(seed)+'-'+corner,'system_sta.py',['--manifest',manifest,'--functional-views',root/'selected/functions.json','--topology',root/'topology/topology.json','--graph',signal,'--upper-geometry',geo,'--stitch-native-access','--audit-native-coverage','--rc-variant',corner],[geo/'receipt.json',pg/'receipt.json'],out,128)
 config=root/('acceptance-'+str(seed)+'.json');assert not config.exists();config.write_text(json.dumps(dict(geometry=str(geo),pg_audit=str(pg),function_run=str(b/'r256-composition-273/function'),topology=str(root/'topology/topology.json'),signal_graph=str(signal),timing=timing),indent=2))
 add('00-k-sready267-r256-joint-'+str(seed),'system_geometry.py',common+['--acceptance',config],[geo/'receipt.json',pg/'receipt.json',b/'r256-composition-273/function/receipt.json']+[Path(p)/'native-system-audit.json'for p in timing.values()],folder/'delivery',64)
record.mkdir();(record/'tasks.json').write_text(json.dumps(dict(time=time.time(),tasks=rows,prerequisites={str(p):sha(p)for p in required},selected_placement=str(chosen),source_manifests={str(b/('source-'+n)/'source-manifest.json'):sha(b/('source-'+n)/'source-manifest.json')for n in ['305']},adaptive_regression_receipt_sha256=sha(regression),whole_system_qualified=False,scope='Five exact345-instance R256 whole-route candidates and all30 original geometry/PG/three-RC/300MHz/joint-delivery gates. Actual23 individually accepted fixedPG types and native/input-pin/upper necessary checks mandatory before dispatch. Eight actual final-cell programs may overlap but exact wired top and every final-PG full-view hash must match in original final collector. No system qualification from native or bound checks.'),indent=2));print(json.dumps(dict(ready=True,queued=len(rows),selected_placement=str(chosen))))
'''
compile(q,'upper267','exec');print(subprocess.check_output(['ssh','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=40).decode())
