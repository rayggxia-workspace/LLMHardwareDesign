from pathlib import Path
import json,gzip,base64,re,sys,copy,collections,hashlib
from decimal import Decimal
sys.path.insert(0,'project/experiments/block_v1')
from native_escape import parse,emit
base=Path('work/YUZE-LU/121/review-20261028');src=base/'v-410-residual-def-447';records={n:base64.b64decode(v).decode()for n,v in json.loads(gzip.decompress((src/'records.json.gz').read_bytes())).items()};tech=next((base/'v-410-bend-clearance-429').rglob('native.tech.lef'));vias={}
for m in re.finditer(r'(?ms)^VIA (via\d+_\d+) DEFAULT\s*\n(.*?)^END \1\s*$',tech.read_text()):
 layers={};layer=None
 for line in m[2].splitlines():
  q=re.match(r'\s*LAYER (\w+) ;',line)
  if q:layer=q[1];continue
  q=re.match(r'\s*RECT ([-\d.]+) ([-\d.]+) ([-\d.]+) ([-\d.]+) ;',line)
  if q:assert layer not in layers;layers[layer]=tuple(int(Decimal(v)*2000)for v in q.groups())
 vias[m[1]]=layers
report=next((base/'v-410-safe-subset-445').rglob('native-whole-drc.rpt')).read_text();original={n:parse(s)for n,s in records.items()};mods={};proposals=[];reject=[]
def merged(it):
 out=[]
 for a,b in sorted(it):
  if out and a<=out[-1][1]:out[-1]=(out[-1][0],max(b,out[-1][1]))
  else:out.append((a,b))
 return out
def contains(box,rects):
 x,y,X,Y=box;xs=sorted({x,X}|{v for a,b,c,d in rects for v in (a,c)if x<v<X})
 return all(any(b<=y and d>=Y for b,d in merged((b,d)for a,b,c,d in rects if a<=lo and c>=hi))for lo,hi in zip(xs,xs[1:]))
def rects(paths,layer):
 out=[]
 for i,p in enumerate(paths):
  if p['via']:
   if layer not in vias[p['via']]:continue
   x,y,_=p['points'][0];a,b,c,d=vias[p['via']][layer];out.append((x+a,y+b,x+c,y+d))
  elif p['layer']==layer:
   (x,y,e),(X,Y,E)=p['points'];h=70;ea=h if e is None else e;eb=h if E is None else E
   if x==X:out.append((x-h,min(y,Y)-(ea if y<Y else eb),X+h,max(y,Y)+(eb if y<Y else ea)))
   else:out.append((min(x,X)-(ea if x<X else eb),y-h,max(x,X)+(eb if x<X else ea),Y+h))
 return out
for marker,s in enumerate(report.split('violation type: ')[1:]):
 m=re.search(r'bbox = \(([^,]+), ([^)]+)\) - \(([^,]+), ([^)]+)\) on Layer (\w+)',s);x,y,X,Y=[int(Decimal(v)*2000)for v in m.groups()[:4]];layer=m[5];n=re.findall(r'net:([^\s]+)',s)[0];paths=original[n][1];union=rects(paths,layer);candidates=[]
 for i,p in enumerate(paths):
  if not p['via']or layer not in vias[p['via']]:continue
  cx,cy,_=p['points'][0];local=mods.get((n,i),vias[p['via']])[layer];a,b,c,d=[local[j]+(cx if j%2==0 else cy)for j in range(4)]
  options=[]
  if c==x and b<=y and d>=Y:options.append((a,b,X,d))
  if a==X and b<=y and d>=Y:options.append((x,b,c,d))
  if d==y and a<=x and c>=X:options.append((a,b,c,Y))
  if b==Y and a<=x and c>=X:options.append((a,y,c,d))
  for box in options:
   if not contains(box,union):continue
   localbox=tuple(box[j]-(cx if j%2==0 else cy)for j in range(4));area=(box[2]-box[0])*(box[3]-box[1])-(c-a)*(d-b);candidates.append((area,i,localbox))
 if not candidates:reject.append(dict(marker=marker,net=n,layer=layer,reason='No exact boundary via enclosure extension contained in original same-net wire/via union'));continue
 area,i,box=min(candidates);p=paths[i];old=mods.setdefault((n,i),dict(vias[p['via']]));previous=old[layer];old[layer]=box;proposals.append(dict(marker=marker,net=n,layer=layer,path=i,via=p['via'],old_rectangle=previous,new_rectangle=box,added_union_area=0))
changed={}
for (n,i),layers in mods.items():
 assert any(layers[l]!=vias[original[n][1][i]['via']][l]for l in layers)
 changed.setdefault(n,[]).append(dict(path=i,original_via=original[n][1][i]['via'],rectangles=layers))
plan=dict(source_report_sha256=hashlib.sha256(report.encode()).hexdigest(),tech_lef_sha256=hashlib.sha256(tech.read_bytes()).hexdigest(),source_def_index_sha256=hashlib.sha256((src/'index.json').read_bytes()).hexdigest(),proposals=proposals,rejected=reject,nets={n:dict(header=original[n][0],original_paths=original[n][1],changes=changes)for n,changes in changed.items()},scope='Finite actual445 marker-driven blockvia realization proposal; no wire/anchor/cut/cell/pin/PG edits, every planned added via-metal rectangle exactly contained in original same-net conductor union. Independent identity-clone/native/fullDEF/actualODB geometry/completeGDS XOR/deck/RC gates remain required. Diagnostic only.')
Path('.local/issue121/via453-plan.json').write_bytes((json.dumps(plan,indent=2)+'\n').encode());print('proposals',len(proposals),'nets',len(changed),'via definitions',len(mods),'rejected',len(reject),collections.Counter(p['layer']for p in proposals))
