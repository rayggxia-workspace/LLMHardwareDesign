import subprocess,shlex
q=r'''from pathlib import Path
import json,hashlib,sys,copy,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');source=b/'source-358';sys.path.insert(0,str(source/'project/experiments/control_v1'));from system_upper import priority_outputs
from boundary_links import validate
manifest=json.loads((b/'r256-composition-359/selected/physical.json').read_text())
p=b/'r256-composition-359/topology/boundary-graph.json';g=json.loads(p.read_text());legacy={'macro_1','macro_2','macro_3','macro_4','macro_t'};old=['net_'+bit for bit,c in g['connections'].items()if c['driver']['instance']in legacy];new=['net_'+bit for bit,c in g['connections'].items()if c['driver']['instance']=='macro_r'];actual=priority_outputs(g)
assert len(old)==583 and len(new)==646 and len(actual)==len(set(actual))==1229;assert set(actual)==set(old)|set(new)and[n for n in actual if n not in set(new)]==old
failure=b/'r256-reset53-priority-isolated-failure-375.json';assert not failure.exists();bad=copy.deepcopy(g);bad['instances'].pop('macro_r');actual_isolated=priority_outputs(bad);assert len(actual_isolated)==583;failure.write_text(json.dumps(dict(whole_system_qualified=False,isolated_helper_accepted_invalid_owner_list=True,returned_legacy_outputs=len(actual_isolated),scope='Initial isolated-function negative test omitted mandatory full closed-scene validation. It failed as a test harness assumption, not as a passed whole routing gate. Actual system_upper validates full graph before priority selection; corrected pipeline check must reject.'),indent=2))
rejected=[]
for name,change in [('missing-actual-R-output',lambda x:x['connections'].pop(new[0][4:])),('wrong-scene',lambda x:x.update(scene='r256-seven-native/1')),('missing-R-owner',lambda x:x['instances'].pop('macro_r'))]:
 bad=copy.deepcopy(g);change(bad)
 try:validate(manifest,bad);priority_outputs(bad)
 except AssertionError:rejected.append(name)
 else:raise AssertionError('Accepted wrong actual priority '+name)
folder=b/'r256-reset53-priority-regression-375';assert not folder.exists();folder.mkdir();sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();report=dict(passed=True,whole_system_qualified=False,actual_scene=g['scene'],actual_legacy_priority_count=583,actual_R_priority_count=646,total=1229,all_actual_R_members_included=True,legacy_members_and_relative_order_preserved=True,negative_controls_rejected=rejected,inputs={str(p):sha(p),str(source/'project/experiments/control_v1/system_upper.py'):sha(source/'project/experiments/control_v1/system_upper.py'),str(source/'project/experiments/control_v1/r256_scene.py'):sha(source/'project/experiments/control_v1/r256_scene.py')},scope='Current actual reset53 graph priority membership/order and negative controls only, no physical qualification. All candidates still require complete geometry/PG/three-RC/300MHz/final-program gates.');(folder/'receipt.json').write_text(json.dumps(report,indent=2)+'\n');print('current priority',1229,'actualR',646,'all negative',len(rejected))
'''
compile(q,'priority375','exec');print(subprocess.check_output(['ssh','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=40).decode())
