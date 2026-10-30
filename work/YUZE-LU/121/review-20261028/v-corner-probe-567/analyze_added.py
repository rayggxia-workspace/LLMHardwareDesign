"""Locate patch nets named by actual newly introduced native markers."""
import hashlib,json,re,sys
from pathlib import Path
folder=Path(__file__).resolve().parent
root=folder.parents[4]
sys.path.insert(0,str(root/'project/experiments/block_v1'))
from revision300_v_corner_probe import violations
old=folder.parent/'v-physical-localization-557/block-v1-20261030-557/tasks/revision300-v-spacing-localize/native-whole-drc.rpt'
new=folder/'block-v1-20261030-566/tasks/revision300-v-corner-probe/corner-native-drc.rpt'
patches=folder/'block-v1-20261030-566/tasks/revision300-v-corner-probe/candidate-rectangles.json'
added=violations(new.read_text())-violations(old.read_text())
nets={name.replace('\\','')for block in added for name in re.findall(r'net:(\S+)',block)}
d=json.loads(patches.read_text());rejected=[r for r in d['chosen']if r['net'].replace('\\','')in nets]
assert sum(added.values())==22 and rejected
result=dict(passed=True,diagnostic_only=True,physical_qualified=False,
            added_native_markers=[dict(text=k,count=v)for k,v in added.items()],
            added_count=sum(added.values()),affected_normalized_net_names=sorted(nets),
            rejected_patch_indices=[r['index']for r in rejected],retained_patch_count=len(d['chosen'])-len(rejected),
            input_sha256={str(p.relative_to(folder.parent)):hashlib.sha256(p.read_bytes()).hexdigest()for p in (old,new,patches)},
            helper_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            dependency_sha256=hashlib.sha256((root/'project/experiments/block_v1/revision300_v_corner_probe.py').read_bytes()).hexdigest(),
            scope='Reject every patch on every net named by a new actual native marker. No rule waiver. Retained patches require a fresh unmodified whole native DRC and exact DEF checks.')
(folder/'added-marker-analysis.json').write_bytes((json.dumps(result,indent=2)+'\n').encode())
print({k:v for k,v in result.items()if k in ('added_count','rejected_patch_indices','retained_patch_count')})
