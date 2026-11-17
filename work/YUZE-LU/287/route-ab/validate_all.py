import pathlib,json,math,statistics
p=pathlib.Path(__file__).resolve().parent
jobs=json.loads((p/'inventory.json').read_text());rows={}
for j in jobs:
 r=json.loads((p/(j['scheme']+'-'+j['net']+'.summary.json')).read_text());assert r['exit']==0
 assert r['self_fF']>0 and abs(r['conservation_error_fF'])<1e-7
 rows[j['scheme'],j['master']]=r
assert len(rows)==646
pairs=[]
for (scheme,i),r in rows.items():
 for (s,j),other in rows.items():
  if s!=scheme or j<=i:continue
  a,sa=r['coupling_row'][j];b,sb=other['coupling_row'][i]
  if max(-a,-b)<5:continue
  sd=math.hypot(sa,sb);pairs.append(dict(scheme=s,a=r['net'],b=other['net'],C1_fF=-a,C2_fF=-b,delta_fF=abs(a-b),zscore=abs(a-b)/sd if sd else 0))
out=dict(expected=646,completed=len(rows),conservation_passed=True,relative_sigma_over_0_003=[r['scheme']+'/'+r['net'] for r in rows.values() if r['relative_sigma']>.003],reciprocity_nonP_pairs_over_5fF=len(pairs),reciprocity_over_3sigma=sum(x['zscore']>3 for x in pairs),reciprocity_max_z=max(x['zscore'] for x in pairs),worst_reciprocity=sorted(pairs,key=lambda x:x['zscore'],reverse=True)[:15],scope='Pairwise stochastic check on non-P rows only. Not a qualified distributed RC/SPEF matrix or dynamic SI verification.')
(p/'validation-all.json').write_text(json.dumps(out,indent=2));print(json.dumps({k:v for k,v in out.items() if k!='worst_reciprocity'},indent=2))
