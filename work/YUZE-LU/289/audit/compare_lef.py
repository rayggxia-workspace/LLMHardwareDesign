import sys,json,re,hashlib
from pathlib import Path
from decimal import Decimal

def parse(p):
 d=dict(size=None,terms={},pins={},obs={});pin=None;obs=False;layer=None
 if p.suffix=='.tsv':
  for l in p.read_text().splitlines():
   a=l.split('\t');tag=a.pop(0)
   if tag=='MASTER':d['size']=list(map(int,a[1:]))
   if tag=='TERM':d['terms'][a[0]]=a[1:]
   if tag=='PIN':d['pins'].setdefault(a[0],[]).append([a[1],*map(int,a[2:])])
   if tag=='OBS':d['obs'].setdefault(a[0],[]).append(list(map(int,a[1:])))
 else:
  cv=lambda x:int(Decimal(x)*2000)
  for l in p.read_text().splitlines():
   a=l.strip().replace(';','').split()
   if not a:continue
   if a[0]=='SIZE':d['size']=[cv(a[1]),cv(a[3])]
   elif a[0]=='PIN':pin=a[1];d['terms'][pin]=[None,None];obs=False
   elif a[0]=='DIRECTION' and pin:d['terms'][pin][0]=a[1]
   elif a[0]=='USE' and pin:d['terms'][pin][1]=a[1]
   elif a[0]=='OBS':obs=True;pin=None
   elif a[0]=='LAYER':layer=a[1]
   elif a[0]=='RECT':
    r=list(map(cv,a[1:]));assert len(r)==4
    if obs:d['obs'].setdefault(layer,[]).append(r)
    elif pin:d['pins'].setdefault(pin,[]).append([layer,*r])
   elif a[0] in ('POLYGON','PATH','VIA'):raise ValueError(('Unsupported shape',l))
   elif a[0]=='END' and len(a)>1 and pin==a[1]:pin=None
 for k in d['pins']:d['pins'][k]=sorted(d['pins'][k])
 return d

def subtract(r,o):
 x0,y0,x1,y1=r;a,b,c,d=o
 a=max(a,x0);b=max(b,y0);c=min(c,x1);d=min(d,y1)
 if a>=c or b>=d:return [r]
 return [q for q in [[x0,y0,a,y1],[c,y0,x1,y1],[a,y0,c,b],[a,d,c,y1]] if q[0]<q[2] and q[1]<q[3]]
if __name__ == "__main__":
 oldp,newp,out=map(Path,sys.argv[1:]);old,new=map(parse,[oldp,newp]);uncovered={}
 for layer,rects in new['obs'].items():
  oldrects=old['obs'].get(layer,[])
  for r in rects:
   pieces=[r]
   for o in oldrects:
    pieces=[v for q in pieces for v in subtract(q,o)]
    if not pieces:break
   if pieces:uncovered.setdefault(layer,[]).extend(pieces)
 result=dict(old=str(oldp),new=str(newp),sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [oldp,newp]},size_exact=old['size']==new['size'],terms_exact=old['terms']==new['terms'],pins_exact=old['pins']==new['pins'],old_obs_covers_new=not uncovered,uncovered_piece_counts={k:len(v) for k,v in uncovered.items()},uncovered_obs_samples={k:v[:20] for k,v in uncovered.items()},pin_differences={k:dict(old=old['pins'].get(k),new=new['pins'].get(k)) for k in old['pins'].keys()|new['pins'].keys() if old['pins'].get(k)!=new['pins'].get(k)})
 result['term_direction_exact']={k:v[0] for k,v in old['terms'].items()}=={k:v[0] for k,v in new['terms'].items()}
 result['term_type_differences']={k:dict(old=old['terms'].get(k),new=new['terms'].get(k)) for k in old['terms'].keys()|new['terms'].keys() if old['terms'].get(k)!=new['terms'].get(k)}
 result['compatible']=all(result[k] for k in ['size_exact','term_direction_exact','pins_exact','old_obs_covers_new']);out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k not in ['uncovered_obs_samples','pin_differences','sha256']}))
