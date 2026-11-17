from pathlib import Path
import re,json
r=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/U-canonical-source-inputs');ds={}
for x in ('before','after'):
 t=(r/(x+'.def')).read_text();s=re.search(r'\nNETS\s+\d+\s*;(.*?)\nEND NETS',t,re.S)[1];ds[x]={m[1]:m[2] for m in re.finditer(r'^\s*-\s+(\S+)\s+(.*?);\s*$',s,re.M|re.S)}
a=ds['before'].keys()-ds['after'].keys();b=ds['after'].keys()-ds['before'].keys();print(json.dumps(dict(counts={x:len(d) for x,d in ds.items()},before_only={n:ds['before'][n] for n in a},after_only={n:ds['after'][n] for n in b}),indent=2))
