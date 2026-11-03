"""Read completed actual DRC source pairs and locations; never infer qualification."""
from pathlib import Path
import subprocess,shlex,json

q=r'''from pathlib import Path
import json,hashlib,re,collections,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');folder=b/'router-full-cugr-snapshot-181';receipt=folder/'receipt.json'
if not receipt.exists():print(json.dumps(dict(ready=False)));raise SystemExit()
r=json.loads(receipt.read_text());assert r['passed']and r['stage']=='bounded-routing-diagnostic-only'
path=folder/'drc.rpt';raw=path.read_bytes();digest=hashlib.sha256(raw).hexdigest();assert r['outputs'][path.name]==digest
c=b/'s-ready-composition-01/1391';graph=json.loads((c/'topology/boundary-graph.json').read_text());placement_path=c/'upper-candidates/1513/route/placement.json';p=json.loads(placement_path.read_text());W,H=p['width_um'],p['height_um']
lines=[s.strip()for s in raw.decode().splitlines()if s.strip()];assert len(lines)%3==0
types=collections.Counter();pairs=collections.Counter();owners=collections.Counter();source_kinds=collections.Counter();bins=collections.Counter();examples=[]
for i in range(0,len(lines),3):
 a,src,box=lines[i:i+3];assert a.startswith('violation type: ')and src.startswith('srcs: '),(i,a,src)
 match=re.fullmatch(r'bbox = \(\s*([-\d.]+),\s*([-\d.]+)\) - \(\s*([-\d.]+),\s*([-\d.]+)\) on Layer (\S+)',box);assert match,(i,box)
 x0,y0,x1,y1=map(float,match.groups()[:4]);layer=match.group(5);kind=a.split(': ',1)[1];types[kind+'/'+layer]+=1
 tokens=src[len('srcs: '):].split();source_kinds['+'.join(sorted(set(t.split(':',1)[0]for t in tokens)))]+=1
 nets=re.findall(r'\bnet:(\S+)',src);drivers=[]
 for net in nets:
  if net.startswith('net_')and net[4:]in graph['connections']:driver=graph['connections'][net[4:]]['driver']['instance']
  else:driver='unmapped:'+net
  drivers.append(driver);owners[driver]+=1
 if kind=='Short':pairs[' | '.join(sorted(drivers))or src]+=1
 x=max(0,min(15,int((x0+x1)*8/W)));y=max(0,min(15,int((y0+y1)*8/H)));bins[str(x)+','+str(y)]+=1
 if len(examples)<24 and kind=='Short':examples.append(dict(type=kind,layer=layer,sources=tokens,drivers=drivers,bbox_um=[x0,y0,x1,y1]))
assert sum(types.values())==len(lines)//3
print(json.dumps(dict(ready=True,captured_at=time.time(),whole_system_qualified=False,report=dict(path=str(path),bytes=len(raw),sha256=digest,receipt_sha256=hashlib.sha256(receipt.read_bytes()).hexdigest()),graph_sha256=hashlib.sha256((c/'topology/boundary-graph.json').read_bytes()).hexdigest(),placement_sha256=hashlib.sha256(placement_path.read_bytes()).hexdigest(),total_violations=len(lines)//3,violation_types=dict(types),source_kinds=dict(source_kinds),top_short_driver_pairs=pairs.most_common(40),top_driver_appearances=owners.most_common(40),bins16=dict(bins),die_um=[W,H],examples=examples,scope='Completed original-source full-scene bounded DRC snapshot. Every3-line actual violation parsed/count conserved; pair classification uses exact original boundary-net driver ownership. Short driver labels identify nets, not physical short position/cause. Diagnostic only; original full geometry/PG/RC qualification still mandatory.')))
'''
d=json.loads(subprocess.check_output(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=45))
if d['ready']:
    out=Path(r'D:\Data\电路实验\control162-short-diagnostic182.json');assert not out.exists();out.write_text(json.dumps(d,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in d.items()if k not in ['bins16','examples']}))
    print(json.dumps(d['examples'][:4]))
else:print(json.dumps(d))
