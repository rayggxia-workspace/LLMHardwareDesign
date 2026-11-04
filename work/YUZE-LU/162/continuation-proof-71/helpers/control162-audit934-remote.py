from pathlib import Path
import json,hashlib,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');old=b/'source-901';new=b/'source-926';reg=b/'r256-native-refresh-regression-927';out=b/'r256-native-refresh-source-audit-934';assert not out.exists();sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
rr=json.loads((reg/'receipt.json').read_text());assert rr['passed']and rr['stage']=='native-refresh-focused-regression-only';child=reg/'native-refresh/receipt.json';assert rr['inputs'][str(child)]==sha(child);r=json.loads(child.read_text());assert r['passed']and len(r['positive'])==2 and len(r['legacy71_actual_byte_replays'])==71 and len(r['new_rejections'])==6 and len(r['invariants'])==19
for key,value in r['inputs'].items():assert sha(key)==value
a=json.loads((old/'source-manifest.json').read_text());z=json.loads((new/'source-manifest.json').read_text());changed={p for p,v in z['files'].items()if a['files'].get(p)!=v};assert changed=={'project/experiments/control_v1/'+n for n in ['tree_router.cpp','tree_router_cpp.py','system_upper.py','native_refresh_regression.py']};assert set(a['files'])<=set(z['files'])
rules=b/'backout934.json';config=json.loads(rules.read_text());rows=[]
for name,changes in config['rules'].items():
 original=old/'project/experiments/control_v1'/name;current=new/'project/experiments/control_v1'/name;s=current.read_text()
 if name=='system_upper.py':assert s.count(config['dispatch'])==1;s=s.replace(config['dispatch'],'',1)
 for a,z in reversed(changes):assert s.count(z)==1,(name,z);s=s.replace(z,a,1)
 assert s==original.read_text();rows.append(dict(name=name,original_sha256=sha(original),current_sha256=sha(current),remove_only_refresh_additions_recovers_original_byte_exact=True))
for x in r['invariants']:assert sha(new/'project/experiments/control_v1'/x['name'])==sha(old/'project/experiments/control_v1'/x['name'])==x['sha256']
for p in r['positive']:
 assert p['proof']['native_prefix_proof']['frozen_prefix_matches_full_route'];assert any(t['native_full_refresh']and t['removed_trees']==12 for t in p['proof']['native_prefix_proof']['refresh_trace'])
out.mkdir();result=dict(passed=True,time=time.time(),whole_system_qualified=False,source_files=1007,unchanged_manifest_files=1003,changed_files=sorted(changed),backouts=rows,invariants=r['invariants'],actual_new_positives=2,actual_legacy_byte_replays=71,actual_new_rejections=6,prior45_reused_not_reexecuted=r['reused_prior_45_rejections'],inputs={str(rules):sha(rules),str(child):sha(child),str(reg/'receipt.json'):sha(reg/'receipt.json'),str(new/'source-manifest.json'):sha(new/'source-manifest.json')},scope='Actual927 focused source-bound test results checked: two final independently checked native refresh8/16 fixtures,71actual previous route/log/prefix/plan byte replays and six new negatives. Previously passed901 complete suite/45negative reused explicitly.19 original helper/physics/test files unchanged; all three production files exactly recover old901 by removing only refresh additions. No final gate, macro, wire budget, layer geometry or native physical view changes. No fullscene physical qualification inferred.')
(out/'receipt.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(passed=True,positives=2,legacy_actual_byte_replays=71,new_negatives=6,unchanged=1003,exact_backouts=3,invariants=19)))
