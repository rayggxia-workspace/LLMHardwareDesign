from pathlib import Path
import hashlib,struct,json
root=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117');c=root/'gs/candidate-S-minimal-localv4/parent-F-eco-h20-v4'
paths=[c/x/'flow/results/nangate45/f-native-frame/base/6_final.gds' for x in ['qualification-diagnostic','qualification-final']]
def digest(p):
 h=hashlib.sha256();ignored=0
 with p.open('rb') as f:
  while True:
   header=f.read(4)
   if not header:break
   assert len(header)==4
   n,t,d=struct.unpack('>HBB',header);assert n>=4
   payload=f.read(n-4);assert len(payload)==n-4
   if t in (1,5):assert n==28 and d==2;payload=b'\0'*24;ignored+=1
   h.update(header);h.update(payload)
 return h.hexdigest(),ignored
values=[digest(p) for p in paths];r=dict(passed=values[0]==values[1],scope='All GDS records byte-identical after replacing only BGNLIB/BGNSTR date fields with zeros',files={str(p):dict(raw_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),normalized_sha256=v[0],date_records=v[1]) for p,v in zip(paths,values)})
(root/'audit/F-gds-timestamp-identity.json').write_text(json.dumps(r,indent=2));print(json.dumps(r,indent=2));assert r['passed']
