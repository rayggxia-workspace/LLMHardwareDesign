"""Map full-deck antenna polygons to actual routed nets and top input pins.
Read-only inputs; no change to the DRC deck or logical qualification.
"""
from pathlib import Path
import argparse,collections,gzip,hashlib,json,math,re,xml.etree.ElementTree as ET
p=argparse.ArgumentParser();p.add_argument('--trial',required=True);p.add_argument('--candidate',required=True)
a=p.parse_args();assert re.fullmatch(r'attempt[0-9]+',a.trial);assert re.fullmatch(r'[A-Za-z0-9]+',a.candidate)
base=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-157-r-architecture')
b=base/a.trial;out=Path.cwd()/'results';out.mkdir(exist_ok=False)
df=b/'physical/flow/results/nangate45'/('rarch157_'+a.candidate)/'base/6_final.def'
xml=b/'evaluation'/(a.candidate+'-full-deck.lyrdb');data=xml.read_bytes()
def sha(f):
 h=hashlib.sha256()
 with f.open('rb')as s:
  for block in iter(lambda:s.read(1024*1024),b''):h.update(block)
 return h.hexdigest()
before=sha(df);root=ET.fromstring(data);rows=[];bins=collections.defaultdict(set)
for i,item in enumerate(root.findall('./items/item')):
 cat=item.findtext('category');m=re.fullmatch(r'METAL([0-9]+)_ANTENNA',cat);assert m,cat
 vals=[v.text for v in item.findall('./values/value')]
 poly=[v for v in vals if v.startswith('polygon: ')];assert len(poly)==1,vals
 points=[tuple(map(float,q.split(',')))for q in poly[0][10:-1].split(';')]
 xs=[q[0]for q in points];ys=[q[1]for q in points];box=[min(xs),min(ys),max(xs),max(ys)]
 rows.append(dict(id=i,category=cat,layer='metal'+m[1],polygon=points,bbox=box,values=vals,nets=set(),ports=set()))
 for x in range(math.floor(box[0]/20),math.floor(box[2]/20)+1):
  for y in range(math.floor(box[1]/20),math.floor(box[3]/20)+1):bins[('metal'+m[1],x,y)].add(i)
def inside(x,y,points):
 flag=False
 for j,(px,py)in enumerate(points):
  qx,qy=points[j-1]
  if min(px,qx)-1e-8<=x<=max(px,qx)+1e-8 and min(py,qy)-1e-8<=y<=max(py,qy)+1e-8 and abs((qx-px)*(y-py)-(qy-py)*(x-px))<1e-8:return True
  if (py>y)!=(qy>y)and x<(qx-px)*(y-py)/(qy-py)+px:flag=not flag
 return flag
def probe(layer,x,y,net,ports):
 for i in bins.get((layer,math.floor(x/20),math.floor(y/20)),()):
  r=rows[i]
  if inside(x,y,r['polygon']):r['nets'].add(net);r['ports'].update(ports)
ports={};dbu=None;mode=None;block=[]
def consume_pin(text):
 name=re.match(r'\s*-\s+(\S+)',text)[1]
 net=re.search(r'\+ NET (\S+)',text)[1];direction=re.search(r'\+ DIRECTION (\w+)',text)[1]
 pos=re.search(r'\+ (?:FIXED|PLACED)\s*\(\s*(-?\d+)\s+(-?\d+)\s*\)',text);assert pos,(name,text)
 x,y=int(pos[1])/dbu,int(pos[2])/dbu
 ports[name]=dict(name=name,net=net,direction=direction,x_um=x,y_um=y)
 if '+ LAYER metal10'in text:probe('metal10',x,y,net,[name])
def consume_net(text):
 net=re.match(r'\s*-\s+(\S+)',text)[1];pp=re.findall(r'\(\s*PIN\s+(\S+)\s*\)',text)
 for chunk in re.split(r'\+\s+(?:ROUTED|FIXED|COVER)\s+|\bNEW\s+',text)[1:]:
  layer=chunk.split()[0];prev=None
  for x,y in re.findall(r'\(\s*(\*|-?\d+)\s+(\*|-?\d+)(?:\s+-?\d+)?\s*\)',chunk):
   if prev is None and '*'in[x,y]:raise ValueError(('undefined DEF star',net))
   point=(prev[0]if x=='*'else int(x),prev[1]if y=='*'else int(y))
   probe(layer,point[0]/dbu,point[1]/dbu,net,pp)
   if prev is not None:probe(layer,(point[0]+prev[0])/(2*dbu),(point[1]+prev[1])/(2*dbu),net,pp)
   prev=point
with df.open()as f:
 for line in f:
  if line.startswith('UNITS DISTANCE MICRONS'):dbu=int(line.split()[3])
  if line.startswith('PINS '):mode='pins';continue
  if line.startswith('NETS '):mode='nets';continue
  if line.startswith('END PINS')or line.startswith('END NETS'):mode=None;continue
  if mode is None:continue
  block.append(line)
  if ';'in line:
   text=' '.join(block);(consume_pin if mode=='pins'else consume_net)(text);block=[]
assert before==sha(df)
for r in rows:r['nets']=sorted(r['nets']);r['ports']=sorted(r['ports'])
passed=all(len(r['nets'])==1 and len(r['ports'])==1 and ports[r['ports'][0]]['direction']=='INPUT'for r in rows)
targets=sorted({name for r in rows for name in r['ports']})
result=dict(passed=passed,scope='antenna polygon/net/input identification only; not physical acceptance',source_trial=a.trial,candidate=a.candidate,def_path=str(df),def_sha256=before,report_path=str(xml),report_sha256=hashlib.sha256(data).hexdigest(),items=len(rows),categories=dict(collections.Counter(r['category']for r in rows)),target_ports=[ports[n]for n in targets],unresolved=[r for r in rows if len(r['nets'])!=1 or len(r['ports'])!=1],items_mapped=rows)
(out/'ANTENNA_IO_AUDIT.json').write_text(json.dumps(result,indent=2)+'\n')
(out/'full-deck.lyrdb.gz').write_bytes(gzip.compress(data,mtime=0))
print(json.dumps(dict(passed=passed,items=len(rows),target_ports=len(targets),unresolved=len(result['unresolved']),clock_in_targets='clk'in targets)))
raise SystemExit(0 if passed else 1)
