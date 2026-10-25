"""Server-only extraction: existing coefficients, no model evaluation or host R outputs."""
import argparse,hashlib,json,struct
from pathlib import Path
import numpy as np
from fixtures import fixtures
ROOT=Path(__file__).resolve().parents[3]
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def put(p,x):Path(p).write_text(json.dumps(x,sort_keys=True,indent=2)+"\n",newline="\n")
def checked(root):
 m=json.loads((root/'manifest.json').read_text())
 for e in m['artifacts']:
  p=root/e['path'];assert p.stat().st_size==e['bytes'] and sha(p)==e['sha256'],str(p)
 return m
def main():
 p=argparse.ArgumentParser();p.add_argument('--old',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
 old=a.old/'falcon-full-32-guard_rescale01';comp=a.old/'falcon-compiled01';om=checked(old);cm=checked(comp)
 report=json.loads((old/'report.json').read_text());assert report['mode']=='full' and report['state_bits']==32 and report['policy']=='guard_rescale' and report['committed_tokens']==72
 assert report['compiled_manifest_sha256']==sha(comp/'manifest.json')
 with np.load(old/'runtime.npz',allow_pickle=False) as z,np.load(comp/'constants.npz',allow_pickle=False) as c:
  names=['x_q12','b_q12','c_q12','dt_q20','alpha_q31','state_initial','state_final','state_units_trace','scan_q12'];v={k:z[k] for k in names};u=c['state_s32_exponents'];skip=c['skip_q20']
  assert v['state_initial'].shape==(32,128,256) and not v['state_initial'].any();assert np.array_equal(v['state_units_trace'][0],u)
  heads=[0];changed=np.flatnonzero(v['state_units_trace'][-1]!=u)
  if 0 not in changed and len(changed):heads.append(int(changed[0]))
  events=json.loads((old/'transactions.json').read_text());wide=[{'token':tx['token'],'attempt':at['attempt'],'error':at['wide_error']} for tx in events['tokens'] for at in tx['attempts'] if at['wide_error'] is not None]
  assert not wide,'cross-head wide guard must be reconciled explicitly'
  details=[]
  for h in heads:
   x=v['x_q12'][:,h,:];b=v['b_q12'];cc=v['c_q12'];dt=v['dt_q20'][:,h];alpha=v['alpha_q31'][:,h]
   assert x.shape==(72,128) and b.shape==cc.shape==(72,256) and dt.shape==alpha.shape==(72,)
   image=bytearray(1<<20)
   for t in range(72):
    q=struct.pack('<IIIIiIiI',0x52393943,t,h,0,int(dt[t]),int(alpha[t]),int(skip[h]),0)
    q+=x[t].astype('<i4').tobytes()+b[t].astype('<i4').tobytes()+cc[t].astype('<i4').tobytes();assert len(q)==2592
    off=0xb0000+t*2592;image[off:off+2592]=q
   (a.out/f'head{h}.bin').write_bytes(image)
   np.savez_compressed(a.out/f'head{h}-old.npz',scan=v['scan_q12'].reshape(72,32,128)[:,h,:],final=v['state_final'][h],units=v['state_units_trace'][:,h])
   details.append({'head':h,'initial_unit':int(u[h]),'steps':72,'rescale_events_from_original_unit_trace':int(v['state_units_trace'][-1,h]-u[h]),'source_state_sha256':hashlib.sha256(v['state_final'][h].astype('<i4').tobytes()).hexdigest()})
 synthetics=fixtures(a.out)
 m={'synthetic_fixtures':synthetics,'original_cross_head_wide_guard_events':wide,'schema':'r99-input-v1','status':'VERIFIED_COEFFICIENTS_NOT_RTL','source':json.loads((ROOT/'binding.json').read_text()),'old_manifest_sha256':sha(old/'manifest.json'),'compiled_manifest_sha256':sha(comp/'manifest.json'),'old_source':om['source'],'heads':details,'selection':'head0; if no original unit growth add smallest head with original unit growth, before new errors','old_global_epoch':report['final_epoch'],'head_local_epoch_is_not_global':True,'artifacts':[{'path':q.name,'bytes':q.stat().st_size,'sha256':sha(q)} for q in sorted(a.out.iterdir())]};put(a.out/'manifest.json',m);print(json.dumps(details))
if __name__=='__main__':main()
