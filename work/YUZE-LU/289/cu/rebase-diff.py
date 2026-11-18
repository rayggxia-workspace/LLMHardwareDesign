from pathlib import Path
from collections import Counter
import sys,json
p=Path(sys.argv[1]);counts=Counter();examples=[]
left=(p/'before-instances.tsv').read_text().splitlines();right=(p/'after-instances.tsv').read_text().splitlines()
assert len(left)==len(right)
for a,b in zip(left,right):
    a=a.split('\t');b=b.split('\t');assert len(a)==len(b)==6
    if a==b:continue
    diff=tuple(i for i in range(6) if a[i]!=b[i]);counts[str(diff)]+=1
    if len(examples)<3:examples.append([a,b])
result={'instances':len(left),'changed_fields':dict(counts),'examples':examples}
(p/'diff.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
