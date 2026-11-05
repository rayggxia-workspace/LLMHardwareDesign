import subprocess,shlex
q=r'''from pathlib import Path
import json,hashlib,subprocess,re,time,sys
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();record=b/'route-selection-102/sready354-tree-bound-retirement';assert not record.exists()
sys.path.insert(0,str(b/'source-350/project/experiments/control_v1'));from steiner_wire_bound import grid_tree_bound
proof=b/'r256-native-tree-cap-diagnostic-347/summary.json';d=json.loads(proof.read_text());assert d['executed']and not d['whole_system_qualified'];bindings={str(proof):sha(proof)}
for p,h in d['inputs'].items():assert sha(p)==h;bindings[p]=h
for placement in d['placements']:
 a=json.loads((Path(placement['placement'])/'placement.json').read_text());assert placement['violations']['high']>0
 for row in placement['rows']:
  result=grid_tree_bound(a['terminals'][row['net']]);assert result['metric_mst_grid_edges']==row['metric_MST_grid_edges']and result['necessary_wire_grid_edges']*4==row['tree_wire_lower_bound_um']
replacement=b/'route-selection-102/sready353-reset53-native/tasks.json';nr=json.loads(replacement.read_text());assert len(nr['tasks'])==7
for row in nr['tasks']:assert sha(row['path'])==row['sha256']and row['spec']['source_root']==str(b/'source-350')
record.mkdir();(record/'verified-stronger-bound.json').write_text(json.dumps(dict(time=time.time(),bound_inputs=bindings,production_helper_sha256=sha(b/'source-350/project/experiments/control_v1/steiner_wire_bound.py'),replacement_record=str(replacement),replacement_record_sha256=sha(replacement),all_four_current_placements_high_corner_impossible=True,whole_system_qualified=False,scope='All stronger report bounds reproduced through production helper. Independent exhaustive3x3 all511 terminal subsets validate lower bound against every connected edge-subgraph. This excludes these exact placements under unchanged high RC max-cap gate, not all future layouts.'),indent=2))
for node,job,queuepath,seed,source in [(2,95341,'dynamic-05/node2',2671,305),(3,95098,'dynamic-02/node3',2672,305),(4,95391,'dynamic-05/node4',2951,305),(25,95204,'dynamic-04/node25',2950,305),(7,96297,'dynamic-07/node7',2670,305),(7,96297,'dynamic-07/node7',3140,313),(7,96297,'dynamic-07/node7',3141,313),(6,95101,'dynamic-02/node6',3440,335)]:
 queue=b/queuepath;state=json.loads((queue/'queue-state.json').read_text());matches=[]
 for name in state['active']:
  p=queue/'pending'/(name+'.json');spec=json.loads(p.read_text());a=spec['args']
  if '--out'in a and a[a.index('--out')+1]==str(b/('r256-composition-274/upper-candidates/'+str(seed)+'/route')):matches.append((name,p,spec))
 assert len(matches)==1,(seed,matches);name,path,spec=matches[0];assert spec['script']=='system_upper.py'and spec['source_root']==str(b/('source-'+str(source)));args=spec['args'];out=Path(args[args.index('--out')+1]);reuse=Path(args[args.index('--reuse-placement')+1]);assert reuse.name==('3071'if seed==3440 else'3070')
 details=subprocess.check_output(['scontrol','show','job',str(job),'-o'],universal_newlines=True);assert 'UserId=yuzelu(10011)'in details and 'JobName=yzl-ctl162-'in details and 'NodeList=node'+str(node)+' 'in details
 steps=subprocess.check_output(['scontrol','show','step',str(job),'-o'],universal_newlines=True);found=[m.groups()for m in re.finditer(r'StepId=('+str(job)+r'\.\d+).*?SrunHost:Pid=(node\d+):(\d+)',steps)]
 code="import os,json;d={}"+chr(10)+"for p in "+repr([r[2]for r in found])+":"+chr(10)+" try:"+chr(10)+"  assert os.stat('/proc/'+p).st_uid==10011;d[p]=open('/proc/'+p+'/cmdline','rb').read().decode().split(chr(0))"+chr(10)+" except OSError:pass"+chr(10)+"print(json.dumps(d))"
 procs=json.loads(subprocess.check_output(['srun','--jobid='+str(job),'--overlap','-n1','-c1','python3','-c',code],universal_newlines=True));targets=[]
 for step,host,pid in found:
  cmd=procs.get(pid,[])
  if '--out'in cmd and cmd[cmd.index('--out')+1]==str(out)and str(b/('source-'+str(source)+'/project/experiments/control_v1/system_upper.py'))in cmd:targets.append(dict(step=step,host=host,pid=pid,command=cmd))
 assert len(targets)==1 and targets[0]['host']=='node'+str(node)
 log=out/'trial-0/router.log';raw=log.read_bytes();lines=raw.decode().splitlines();assert any('"routed"'in line or '"conflict_nodes"'in line for line in lines)
 row=dict(time=time.time(),target=targets[0],spec=str(path),spec_sha256=sha(path),selected_placement=str(reuse),selected_placement_sha256=sha(reuse/'placement.json'),proof=str(proof),proof_sha256=sha(proof),log_snapshot_bytes=len(raw),log_snapshot_sha256=hashlib.sha256(raw).hexdigest(),last_log_lines=lines[-3:],job_details=details,whole_system_qualified=False,reason='Exact placement mathematically fails unchanged high RC maximum capacitance even before detours/vias/coupling. Stop only this verified own search child; preserve original source/spec/all raw, parent, other tasks and external R. Registered reset53 replacement and all6 physical successor gates queued first. Original FastRoute3250/3441 and complete-path337 retained as bounded congestion diagnostics, not eligible for qualification.')
 (record/(str(seed)+'-verified-before.json')).write_text(json.dumps(row,indent=2));subprocess.run(['scancel',targets[0]['step']],check=True);(record/(str(seed)+'-cancelled.json')).write_text(json.dumps(dict(time=time.time(),step=targets[0]['step'])));print('retired electrically impossible own',seed,targets[0]['step'])
'''
compile(q,'retire354','exec');print(subprocess.check_output(['ssh','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=55).decode())
