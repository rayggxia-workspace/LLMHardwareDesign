"""Server-only checked physical packing, no model loading or quantization changes."""
import argparse,json,hashlib
from pathlib import Path
import numpy as np
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--old',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();m=json.loads((a.old/'manifest.json').read_text())
 for e in m['artifacts']:
  if sha(a.old/e['path'])!=e['sha256']:raise ValueError('old SHA')
 a.out.mkdir(exist_ok=False);cases=json.loads((a.old/'cases.json').read_text())
 for c in cases:
  raw=(a.old/c['payload']).read_bytes();v=np.frombuffer(raw,np.uint8).reshape(1536,8,65,16);aa=v[:,:,1:,:8].copy().reshape(1536,8,512)
  if not np.all(aa==aa[0]):raise ValueError('not shared A across H')
  weights=v[:,:,1:,8:].copy().reshape(1536,8,32,16);records=np.concatenate([v[:,:,:1],weights],axis=2)
  packed=aa[0].tobytes()+records.tobytes()
  # Reconstruct every original byte including all headers; no code changes.
  restore=np.empty_like(v);restore[:,:,0]=records[:,:,0];restore[:,:,1:,:8]=np.broadcast_to(aa[0,:,None,:].reshape(8,64,8),(1536,8,64,8));restore[:,:,1:,8:]=weights.reshape(1536,8,64,8)
  if restore.tobytes()!=raw:raise ValueError('physical roundtrip')
  c['payload0']=c['payload'];c['payload1']='cache-'+c['payload'];c['cache_initial_bytes']=4096;c['physical_roundtrip']='PASS_ALL_ORIGINAL_BYTES'
  (a.out/c['payload0']).write_bytes(raw);(a.out/c['payload1']).write_bytes(packed);(a.out/c['original']).write_bytes((a.old/c['original']).read_bytes())
 (a.out/'cases.json').write_text(json.dumps(cases,indent=2)+'\n')
 for mode in range(2):(a.out/f'vectors-c{mode}.tsv').write_text(''.join(c['name']+' '+str(a.out/c[f'payload{mode}'])+' '+c['gamma']+' '+str(c['coefficient'])+'\n'for c in cases))
 files=[f for f in a.out.iterdir()if f.is_file()];(a.out/'manifest.json').write_text(json.dumps({'status':'PASS_PHYSICAL_REPACK_ROUNDTRIP','source_manifest_sha256':sha(a.old/'manifest.json'),'artifacts':[{'path':f.name,'bytes':f.stat().st_size,'sha256':sha(f)}for f in files]},indent=2)+'\n');print('PASS_PHYSICAL_REPACK_ROUNDTRIP')
if __name__=='__main__':main()
