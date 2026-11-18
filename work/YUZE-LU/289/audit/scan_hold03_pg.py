import pathlib,re,json
p=pathlib.Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/gs/candidate-S-hold08-v3/parent-F-eco-h20-v4/candidate.def');active=False;net=None;hits=[]
for line in p.read_text().splitlines():
 if line.startswith('SPECIALNETS '):active=True
 if line.startswith('END SPECIALNETS'):active=False
 if not active:continue
 m=re.match(r'\s*- (\S+)',line)
 if m:net=m[1]
 if not ('metal9' in line or 'via8_' in line or 'via9_' in line):continue
 for x,y in re.findall(r'\(\s*(\d+)\s+(\d+)\s*\)',line):
  x,y=int(x),int(y)
  if 438190<x<467790 and 1145340<y<1165340:hits.append(dict(net=net,line=line.strip(),x=x,y=y))
print(json.dumps(hits,indent=2))
