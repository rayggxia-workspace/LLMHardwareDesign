import json,pathlib
p=pathlib.Path(__file__).parent
e=json.loads((p/'endpoints.json').read_text());r={}
for b in ['C','U']:
 terms={}
 for l in (p/(b+'-ports.tsv')).read_text().splitlines():
  a=l.split('\t')
  if a[0]=='term':terms[a[1]]=a[2:]
 errors=[]
 for role,expected in [('outputs','OUTPUT'),('inputs','INPUT')]:
  for name in e['ports'][b+'0'][role]:
   t=terms.get(name)
   if not t or t[0]!=expected:errors.append([name,expected,t])
 r[b]=dict(checked=306,errors=errors)
(p/'directions-check.json').write_text(json.dumps(r,indent=2)+'\n');print(r)
