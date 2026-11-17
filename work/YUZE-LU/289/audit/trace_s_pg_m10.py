import re,json,pathlib
base=pathlib.Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/gs/candidate-S-hold08-v3');log=(base/'parent-F-eco-h20-v4-pgfix/implementation.log').read_text()
pat=r'at \(([\d.]+)um, ([\d.]+)um\) - \(([\d.]+)um, ([\d.]+)um\), layer: metal10'
boxes=[tuple(round(float(v)*2000)-144000 for v in x) for x in re.findall(pat,log)];hits=[[] for _ in boxes]
net=None;section=None
for line in (base/'candidate.def').read_text().splitlines():
 if line.startswith('NETS '):section='signal'
 if line.startswith('SPECIALNETS '):section='PG'
 if line.startswith('END NETS') or line.startswith('END SPECIALNETS'):section=None
 if not section:continue
 m=re.match(r'\s*- (\S+)',line)
 if m:net=m[1]
 layer=re.search(r'(?:NEW|ROUTED) (metal\d+)',line)
 if not layer:continue
 coords=re.findall(r'\(\s*(-?\d+|\*)\s+(-?\d+|\*)\s*\)',line);points=[]
 for a,b in coords:
  if (a=='*' or b=='*') and not points:continue
  points.append((points[-1][0] if a=='*' else int(a),points[-1][1] if b=='*' else int(b)))
 segments=list(zip(points,points[1:])) if layer[1]=='metal10' else []
 if re.search(r'\bvia9',line):segments += [(p,p) for p in points]
 for a,b in segments:
  r=(min(a[0],b[0])-800,min(a[1],b[1])-800,max(a[0],b[0])+800,max(a[1],b[1])+800)
  for i,q in enumerate(boxes):
   if r[0]<q[2] and r[2]>q[0] and r[1]<q[3] and r[3]>q[1]:hits[i].append(dict(net=net,section=section,route=line.strip()))
print(json.dumps([dict(local_box=q,hits=h) for q,h in zip(boxes,hits)],indent=2))

