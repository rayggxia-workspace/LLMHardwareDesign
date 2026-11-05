import subprocess,shlex
q=r'''from pathlib import Path
import json,hashlib,time,sys
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');root=b/'r256-composition-359';folder=root/'function';out=b/'r256-reset53-final-function-audit-392';assert not out.exists();sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();r=json.loads((folder/'receipt.json').read_text());assert r['passed']and r['R_integrated']and r['scene']=='r256-seven-native/2'and r['physical_instances']==345 and r['actual_final_leaf_count']==23 and r['real_program_count']==8
results=r['initial_results'];assert set(results)=={'initial-1-162.json','initial-2-162.json','initial-2-163.json'}
for name,value in results.items():
 assert value==json.loads((folder/name).read_text())and value['passed']and value['cpu_tensor_moves']==0 and value['real_compositions']==8
 cmd=[c for c in r['commands']if c['log']==name];assert len(cmd)==1 and cmd[0]['returncode']==0 and cmd[0]['sha256']==sha(folder/name)
assert len({json.dumps(v,sort_keys=True)for v in results.values()})==1
inputs=json.loads((folder/'hierarchical-inputs.json').read_text());manifest=json.loads((root/'selected/physical.json').read_text());assert set(inputs)==set(manifest['leaves']);bindings={str(folder/'receipt.json'):sha(folder/'receipt.json')};views={}
for top,row in manifest['leaves'].items():
 delivery=Path(row['fixed_pg_delivery']['path']);assert sha(delivery)==row['fixed_pg_delivery']['sha256'];v=json.loads(delivery.read_text())['full_final_netlist'];used=inputs[top];assert v['passed']and used['only_compiler_partition_comment_added']and used['original_sha256']==v['full_view_sha256']==sha(v['full_view'])
 assert r['inputs'][used['original']]==used['original_sha256'];views[top]=v['full_view_sha256'];bindings[str(delivery)]=sha(delivery)
sys.path.insert(0,str(b/'source-358/project/experiments/control_v1'));from boundary_links import verilog
topology=json.loads((root/'topology/topology.json').read_text())['modules']['control_system'];assert (folder/'actual-qualified-top.v').read_text()==verilog(topology)
for p in [folder/'actual-qualified-top.v',folder/'hierarchical-inputs.json',root/'selected/physical.json',root/'topology/topology.json',root/'topology/boundary-graph.json']:bindings[str(p)]=sha(p)
out.mkdir();(out/'receipt.json').write_text(json.dumps(dict(passed=True,whole_system_qualified=False,time=time.time(),actual_new_scene='r256-seven-native/2',physical_instances=345,final_leaf_types=23,programs=8,initial_results=results,inputs=bindings,actual_fixed_pg_full_view_sha256=views,scope='Actual reset53 current359 eight-program final-cell simulations passed all three independent initialization runs. Exact current wired top and all23 selected finalPG complete-view hashes independently rechecked. No old273 program substitution. Zero-delay numerical/program evidence only; full actual M11/M12 geometry/PG/threeRC300MHz and joint delivery still required.'),indent=2));print(json.dumps(dict(passed=True,initial_results=results,views=len(views),whole_system_qualified=False)))
'''
compile(q,'function392','exec');print(subprocess.check_output(['ssh','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=45).decode())
