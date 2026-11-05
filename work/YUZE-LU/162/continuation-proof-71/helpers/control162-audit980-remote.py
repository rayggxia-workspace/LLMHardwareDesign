from pathlib import Path
import json,hashlib,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');old=b/'source-947';new=b/'source-972';reg=b/'r256-native-warm-regression-973';out=b/'r256-native-warm-source-audit-980';assert not out.exists();sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
root=json.loads((reg/'receipt.json').read_text());assert root['passed']and root['stage']=='native-warm-focused-regression-only';child=reg/'native-warm/receipt.json';assert root['inputs'][str(child)]==sha(child);r=json.loads(child.read_text());assert r['passed']and not r['whole_system_qualified']and not r['route_qualified']and len(r['full_route_positives'])==2 and len(r['rejected'])==16 and r['native_zero_global_failure_rejected']
for p,v in r['inputs'].items():assert sha(p)==v
for x in r['full_route_positives']:assert x['proof']['final_conflicts']==0 and x['proof']['native_prefix_proof']['final_native_paths_changed']>0
a=json.loads((old/'source-manifest.json').read_text());z=json.loads((new/'source-manifest.json').read_text());changed={p for p,v in z['files'].items()if a['files'].get(p)!=v};assert changed=={'project/experiments/control_v1/'+n for n in ['tree_router.cpp','tree_router_cpp.py','system_upper.py','native_prefix_seed.h','native_warm_regression.py']};assert set(a['files'])<=set(z['files'])and len(z['files'])==1010
assert json.loads((new/'freeze-import.json').read_text())['archive_sha256']=='dbee549d02c668de6c6a1c6f4ac33227af8f67dddfe8bb1ef51ad542e70fd093'
for p,v in z['files'].items():assert sha(new/p)==v
rules=b/'backout980.json';cfg=json.loads(rules.read_text());rows=[]
for name,changes in cfg['rules'].items():
 original=old/'project/experiments/control_v1'/name;current=new/'project/experiments/control_v1'/name;s=current.read_text()
 if name=='system_upper.py':assert s.count(cfg['dispatch'])==1;s=s.replace(cfg['dispatch'],'',1)
 for a,z in reversed(changes):assert s.count(z)==1,(name,z);s=s.replace(z,a,1)
 assert s==original.read_text();rows.append(dict(name=name,previous_sha256=sha(original),current_sha256=sha(current),remove_only_warm_seed_additions_recovers_previous_byte_exact=True))
invariants=json.loads((b/'r256-pin-release-source-audit-950/receipt.json').read_text())['invariants']+[dict(name='pin_release_regression.py',sha256=sha(new/'project/experiments/control_v1/pin_release_regression.py'))]
for x in invariants:assert sha(new/'project/experiments/control_v1'/x['name'])==sha(old/'project/experiments/control_v1'/x['name'])==x['sha256']
out.mkdir();result=dict(passed=True,time=time.time(),whole_system_qualified=False,source_files=1010,unchanged_manifest_files=1005,changed_files=sorted(changed),backouts=rows,invariants=invariants,full_route_positive=2,rejected=16,old71_actual_replays=True,old_release2_actual_bytes_exact=True,inputs={str(rules):sha(rules),str(child):sha(child),str(reg/'receipt.json'):sha(reg/'receipt.json'),str(new/'source-manifest.json'):sha(new/'source-manifest.json')},scope='Exact source/actual warm-seed tests: upper native paths movable, original finite budget/all landings and all final geometry/PG/3RC300MHz gates unchanged. Independent complete routes and strict seed identities. No fullscene qualification inferred.')
(out/'receipt.json').write_text(json.dumps(result,indent=2));print(json.dumps(dict(passed=True,source_files=1010,unchanged=1005,backouts=3,invariants=21,positives=2,rejected=16)))
