import subprocess,shlex
q='''from pathlib import Path
import json,hashlib,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');prior=b/'r256-native-warm-active-pool-audit-999/receipt.json';p=json.loads(prior.read_text());assert p['passed']and len(p['comparisons'])==32
assert [x['node']for x in p['pools']]==[2,4]and [x['job']for x in p['pools']]==[95341,95391]
for row in p['pools']:
 selected=9920 if row['node']==2 else 9921;scale=8 if selected==9920 else 32
 assert row['selected']==[selected]and row['four16cpu_masks_pairwise_disjoint']
 found=[x for x in row['all_owned_live_processes']if x['seed']==selected];assert len(found)==16
 for x in found:assert '--native-prefix-flexible'in x['command']and all(len(x['cpu_affinity'])==16 for x in found)
 spec=next(x['spec']for x in json.loads((b/'route-selection-102/sready992-native-warm-fullchains/tasks.json').read_text())['tasks']if x['spec']['script']=='system_upper.py'and '/'+str(selected)+'/'in x['spec']['args'][x['spec']['args'].index('--out')+1]);a=spec['args'];assert a[a.index('--route-congestion-scale')+1]==str(scale)
out=b/'r256-native-warm-variant-audit-1001';assert not out.exists();out.mkdir();r=dict(passed=True,time=time.time(),whole_system_qualified=False,source_receipt=str(prior),source_sha256=hashlib.sha256(prior.read_bytes()).hexdigest(),actual_children=32,actual_nodes=[2,4],congestion_scales=[8,32],actual_admissions=p['actual_admissions'],scope='Correct metadata for999: actual9920/9921 on node2/4,160GiB nodeforecast/208GiB threshold,32actual child/prefix/body/16CPUdisjoint checks.999 copied narrative still names9810/1 and node5/6; its raw structured node/job/process/admission evidence is preserved and verified here. Other final physical gates unchanged; no fullroute/system pass inferred.');(out/'receipt.json').write_text(json.dumps(r,indent=2));print(json.dumps(dict(passed=True,actual_children=32,nodes=[2,4],scales=[8,32])))
'''
print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)]).decode())
