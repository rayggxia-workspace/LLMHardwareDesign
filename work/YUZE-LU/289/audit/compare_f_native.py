from pathlib import Path
import re,json,hashlib
root=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117');old=Path('/public/home/yuzelu/project-circuit/main-blockv2-f300-side-01/native-openroad-drc.rpt');new=root/'gs/candidate-S-minimal-localv4/parent-F-eco-h20-v4/native-drc.rpt'
def records(p):return {x.strip() for x in p.read_text().split('violation type:') if x.strip()}
a,b=map(records,[old,new]);result=dict(baseline_count=len(a),candidate_count=len(b),shared=len(a&b),added=sorted(b-a),removed=sorted(a-b),sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [old,new]});(root/'audit/F-native-marker-diff.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))

