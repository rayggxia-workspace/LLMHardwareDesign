from pathlib import Path
import re,json
r=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117');base=r/'u-physical/rcx-def-uncached-119788/normal'
pts=[(243.0,60.5),(55.0,120.5),(811.0,771.7),(647.0,851.6),(669.2,892.5),(677.2,892.5)]
targets={0:'i289_repeater_store124_net',1:'net22175',2:'net38689',3:r'e_out_data\[26\]',4:'net38652',5:'net38650'}
via={}
for s in (r/'audit/U-antenna/guard-v1-map/vias.tsv').read_text().splitlines():
 n,l,*_=s.split('\t')
 if l.startswith('metal'):via.setdefault(n,set()).add(l)
rows=[]
for label in ('before','after'):
 text=(base/(label+'.def')).read_text().split('\nNETS ',1)[1].split('\nEND NETS',1)[0]
 for e in re.finditer(r'^\s*-\s+(\S+)\s+(.*?);\s*$',text,re.M|re.S):
  net,body=e.groups()
  if net not in targets.values():continue
  marker=next(i for i,n in targets.items() if n==net);cx,cy=pts[marker]
  for m in re.finditer(r'(?:\+ ROUTED|\bNEW)\s+(\S+)\s+(.*?)(?=\bNEW|$)',body,re.S):
   layer,seq=m.groups();prev=None;pe=None
   for t in re.finditer(r'\(\s*(\*|-?\d+)\s+(\*|-?\d+)(?:\s+(-?\d+))?\s*\)|(\S+)',seq):
    x,y,ext,n=t.groups()
    if x is not None:
     pt=(prev[0] if x=='*' else int(x),prev[1] if y=='*' else int(y));ce=None if ext is None else int(ext)
     if prev and layer=='metal10':
      a,b=prev[0]/2000,prev[1]/2000;c,d=pt[0]/2000,pt[1]/2000
      if min(a,c)-.5<=cx<=max(a,c)+.5 and min(b,d)-.5<=cy<=max(b,d)+.5:
       rows.append(dict(source=label,marker=marker,net=net,layer=layer,start=[a,b,None if pe is None else pe/2000],end=[c,d,None if ce is None else ce/2000]))
     prev=pt;pe=ce
    elif n in via:
     layers=via[n];assert layer in layers and len(layers)==2,(layer,n,layers);layer=next(l for l in layers if l!=layer);pe=None
    else:assert n in ('TAPER','+','USE','SIGNAL'),n
p=r/'audit/U-v17-m10-endpoints-v2.json';p.write_text(json.dumps(dict(marker_centers=pts,routes=rows),indent=2));print(json.dumps(rows,indent=2))
