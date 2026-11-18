from pathlib import Path
from collections import Counter
import re,json
p=Path(__file__).parent
s=(p/'c-v17-remaining-hold.rpt').read_text()
r=[]
for x in s.split('Startpoint: ')[1:]:
 m=re.search(r'Endpoint: (\S+)',x);w=re.search(r'(-?[\d.]+)\s+slack \(VIOLATED\)',x)
 if m and w:r.append(dict(start=x.splitlines()[0],endpoint=m.group(1),slack=float(w.group(1))))
print('paths',len(r),'input',sum('(input port' in x['start'] for x in r))
print(Counter(re.sub(r'\[.*','',x['start']) for x in r).most_common(15))
(p/'c-v17-hold-endpoints.json').write_text(json.dumps(r,indent=2))