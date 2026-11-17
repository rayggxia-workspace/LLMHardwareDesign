from pathlib import Path
import re,json,difflib
r=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117');base=r/'u-physical/rcx-def-uncached-119788/normal'
pts=[(243,60.5),(55,120.5),(811,771.7),(647,851.6),(669.2,892.5),(677.2,892.5)]
results=[]
for label in ('before','after'):
 text=(base/(label+'.def')).read_text().split('\nNETS ',1)[1].split('\nEND NETS',1)[0]
 for e in re.finditer(r'^\s*-\s+(\S+)\s+(.*?);\s*$',text,re.M|re.S):
  net,body=e.groups()
  for m in re.finditer(r'(?:\+ ROUTED|\bNEW)\s+(\S+)\s+(.*?)(?=\bNEW|$)',body,re.S):
   layer,seq=m.groups()
   if layer!='metal10':continue
   pp=[];prev=None
   for p in re.finditer(r'\(\s*(\*|-?\d+)\s+(\*|-?\d+)(?:\s+(-?\d+))?\s*\)',seq):
    x,y,ext=p.groups();pt=(prev[0] if x=='*' else int(x),prev[1] if y=='*' else int(y));pp.append((pt[0]/2000,pt[1]/2000,None if ext is None else int(ext)/2000));prev=pt
   if not pp:continue
   for i,(x,y) in enumerate(pts):
    if min(p[0] for p in pp)-1<=x<=max(p[0] for p in pp)+1 and min(p[1] for p in pp)-1<=y<=max(p[1] for p in pp)+1:
     results.append(dict(source=label,marker=i,net=net,layer=layer,points=pp,route=seq.strip()))
out=r/'audit/U-v17-m10-endpoints.json';out.write_text(json.dumps(dict(marker_centers=pts,routes=results),indent=2));print(json.dumps(dict(marker_centers=pts,routes=results),indent=2))
