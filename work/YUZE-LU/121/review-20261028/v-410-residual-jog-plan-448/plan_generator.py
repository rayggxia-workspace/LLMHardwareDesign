from pathlib import Path
import json,gzip,base64,re,sys,copy,collections,hashlib
from decimal import Decimal
sys.path.insert(0,'project/experiments/block_v1')
from native_escape import parse,signature,emit,on_segment,path_length
base=Path('work/YUZE-LU/121/review-20261028');source=base/'v-410-residual-def-447';records={n:base64.b64decode(v).decode()for n,v in json.loads(gzip.decompress((source/'records.json.gz').read_bytes())).items()};original={n:parse(v)for n,v in records.items()};current={n:copy.deepcopy(v[1])for n,v in original.items()}
tech=next((base/'v-410-bend-clearance-429').rglob('native.tech.lef'));text=tech.read_text();vias={}
for m in re.finditer(r'(?ms)^VIA (via\d+_\d+) DEFAULT\s*\n(.*?)^END \1\s*$',text):
 layers={};layer=None
 for line in m[2].splitlines():
  q=re.match(r'\s*LAYER (\w+) ;',line)
  if q:layer=q[1];continue
  q=re.match(r'\s*RECT ([-\d.]+) ([-\d.]+) ([-\d.]+) ([-\d.]+) ;',line)
  if q:assert layer not in layers;layers[layer]=tuple(int(Decimal(v)*2000)for v in q.groups())
 vias[m[1]]=layers
assert vias['via2_5']['metal3']==(-140,-70,140,70)
report=next((base/'v-410-safe-subset-445').rglob('native-whole-drc.rpt')).read_text();proposals=[];reject=[]
def boxes(paths):
 rows=[]
 for i,p in enumerate(paths):
  if p['via']in vias and 'metal3'in vias[p['via']]:
   x,y,_=p['points'][0];a,b,c,d=vias[p['via']]['metal3'];rows.append((i,(x+a,y+b,x+c,y+d)))
 return rows
for index,mark in enumerate(report.split('violation type: ')[1:]):
 m=re.search(r'bbox = \(([^,]+), ([^)]+)\) - \(([^,]+), ([^)]+)\) on Layer (\w+)',mark);x,y,X,Y=[int(Decimal(v)*2000)for v in m.groups()[:4]]
 if m[5]!='metal3':continue
 n=re.findall(r'net:([^\s]+)',mark);assert len(n)==1;n=n[0];paths=current[n]
 try:
  left=[r for r in boxes(paths)if r[1][2]==x and r[1][1]<=y and r[1][3]>=Y];right=[r for r in boxes(paths)if r[1][0]==X and r[1][1]<=y and r[1][3]>=Y];assert len(left)==len(right)==1,'No unique via-enclosure pair'
  feasible=[]
  for side,(i,a),(other_i,b)in [('right',right[0],left[0]),('left',left[0],right[0])]:
   p=paths[i];via_layer=int(p['layer'][5:]);assert via_layer in (2,3);other_layer='metal2'if via_layer==2 else'metal4';cx,cy,ext=p['points'][0];assert ext is None
   gap=b[0]-(cx+70)if side=='left'else(cx-70)-b[2]
   if gap<140:continue
   for direction,delta in [(1,b[3]+140-a[1]),(-1,b[1]-140-a[3])]:
    if delta*direction<=0 or delta%10:continue
    target=(cx,cy+delta)
    legs=[j for j,r in enumerate(paths)if r['layer']==other_layer and not r['via']and r['points'][0][0]==r['points'][1][0]==cx and on_segment((cx,cy),r)and on_segment(target,r)]
    if not legs:continue
    feasible.append((0 if side=='right'else 1,0 if direction==1 else 1,abs(delta),i,delta,target,legs))
  assert feasible,'No supported existing-leg move with legal M3 jog gap'
  _,_,_,i,delta,target,legs=min(feasible);result=copy.deepcopy(paths);old=result[i]['points'][0];result[i]['points'][0]=(target[0],target[1],None)
  covered=any(r['layer']=='metal3'and not r['via']and on_segment(old[:2],r)and on_segment(target,r)for r in paths)
  if not covered:result.append(dict(layer='metal3',points=[old,(*target,None)],via=None))
  assert [r['via']for r in paths if r['via']]==[r['via']for r in result if r['via']]
  assert signature([r for j,r in enumerate(paths)if j!=i])==signature([r for j,r in enumerate(result)if j!=i and j<len(paths)])
  current[n]=result;proposals.append(dict(marker=index,net=n,moved_via_index=i,via=paths[i]['via'],old=old,new=(*target,None),delta_y_dbu=delta,existing_other_layer_legs=legs,added_m3_jog=not covered))
 except AssertionError as e:reject.append(dict(marker=index,net=n,reason=str(e)))
nets={n:dict(header=original[n][0],original_paths=original[n][1],final_paths=paths)for n,paths in current.items()if signature(paths)!=signature(original[n][1])}
plan=dict(source_def_index_sha256=hashlib.sha256((source/'index.json').read_bytes()).hexdigest(),source_report_sha256=hashlib.sha256(next((base/'v-410-safe-subset-445').rglob('native-whole-drc.rpt')).read_bytes()).hexdigest(),tech_lef_sha256=hashlib.sha256(tech.read_bytes()).hexdigest(),proposals=proposals,rejected=reject,nets=nets,scope='One bounded plan per supported M3 marker: move via along an already-existing adjacent-layer vertical wire, retain every original wire and add only an M3 vertical jog. M1/cell/ports unchanged. Native fullDRC/readback/connectivity still required; current423 not edited.')
Path('.local/issue121/jog448-plan.json').write_bytes((json.dumps(plan,indent=2)+'\n').encode());print('proposals',len(proposals),'nets',len(nets),'rejected',len(reject),collections.Counter(r['reason']for r in reject))
