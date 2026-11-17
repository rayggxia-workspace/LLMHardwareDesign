from pathlib import Path
import hashlib,json,struct,sys
paths=list(map(Path,sys.argv[1:3]));out=Path(sys.argv[3])
def canonical(p):
 raw=p.read_bytes();b=bytearray();i=0;excluded=[]
 while i<len(raw):
  n,kind,dt=struct.unpack_from('>HBB',raw,i);assert n>=4 and i+n<=len(raw)
  if kind in (1,5):
   assert dt==2 and n==28;excluded.append(dict(record=kind,length=n));b.extend(raw[i:i+4]);b.extend(bytes(n-4))
  else:b.extend(raw[i:i+n])
  i+=n
 return hashlib.sha256(b).hexdigest(),excluded
values=[canonical(p) for p in paths];r=dict(passed=values[0][0]==values[1][0],scope='Exact GDS binary records with only BGNLIB/BGNSTR timestamp payloads zeroed; all geometry, transforms, names, labels and hierarchy remain byte-exact',source_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},canonical_sha256=dict(zip(map(str,paths),(v[0] for v in values))),timestamp_record_count=[len(v[1]) for v in values]);out.write_text(json.dumps(r,indent=2));print(json.dumps(r,indent=2))
