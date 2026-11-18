import json,collections
from pathlib import Path
r=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/u-macro-pdn-v1')
def nets(name):
 return {s[0]:set(s[2:]) for line in (r/(name+'-nets.tsv')).read_text().splitlines() if (s:=line.split('\t'))[0] in ('VDD','VSS')}
a,b=nets('before'),nets('after')
inst={s[0]:s[1] for line in (r/'after-instances.tsv').read_text().splitlines() if (s:=line.split('\t'))}
o={}
for rail in a:
 added=b[rail]-a[rail];removed=a[rail]-b[rail]
 counts=collections.Counter(inst.get(x[5:].rsplit('/',1)[0],'<bterm>') for x in added)
 o[rail]=dict(before=len(a[rail]),after=len(b[rail]),added=len(added),removed=sorted(removed),added_master_counts=dict(counts))
out=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/U-PG-terminal-delta.json');out.write_text(json.dumps(o,indent=2));print(json.dumps(o,indent=2))
