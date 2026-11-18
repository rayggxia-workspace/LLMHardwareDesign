import json,sys,collections
from pathlib import Path
p=Path(sys.argv[1]);top='cfj_group_c_memory_legacy';ds=[]
for lab in ('gold','gate'):
 m=json.loads((p/'formal'/f'{lab}-physical.json').read_text())['modules'][top]
 states={n:c for n,c in m['cells'].items() if 'CK' in c['connections'] and 'D' in c['connections'] and c['type'].startswith(('DFF','SDFF'))}
 aliases=collections.defaultdict(list)
 for n,w in m['netnames'].items():
  if not w['hide_name']:
   for i,b in enumerate(w['bits']):aliases[b].append(f'{n}[{i}]')
 ds.append((states,aliases))
 print(lab,'states',len(states),'types',collections.Counter(c['type'] for c in states.values()))
a,b=ds[0][0],ds[1][0]
print('intersection',len(set(a)&set(b)))
report={}
for i,(lab,x,y) in enumerate([('gold',a,b),('gate',b,a)]):
 names=sorted(set(x)-set(y)); print(lab,'unmatched',len(names))
 report[lab]=[{'name':n,'type':x[n]['type'],'q_aliases':{pin:[ds[i][1][bit] for bit in bits] for pin,bits in x[n]['connections'].items() if pin in ('Q','QN')}} for n in names]
 print(json.dumps(report[lab][:10],indent=2))
(p/'state-boundary-difference.json').write_text(json.dumps(report,indent=2))
