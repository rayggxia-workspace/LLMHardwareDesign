"""Server-only exact original input extraction: never put MID, A8 or delta in executable input."""
import argparse,hashlib,json,struct
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[3]
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def bound(p):
 m=json.loads((p/'manifest.json').read_text())
 for e in m['artifacts']:
  if sha(p/e['path'])!=e['sha256']:raise ValueError('source artifact '+str(p/e['path']))
 return m
def main():
 p=argparse.ArgumentParser();p.add_argument('--old',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(exist_ok=False);compiled=a.old/'granite-compiled01';bound(compiled);sources=[{'path':str(compiled),'manifest_sha256':sha(compiled/'manifest.json')}];cases=[]
 with np.load(compiled/'constants.npz',allow_pickle=False)as const:
  table=const['silu_lut_q12'].astype('<i4').tobytes()+const['route_exp2_q24'].astype('<u4').tobytes();assert len(table)==73736;(a.out/'lut.bin').write_bytes(table+bytes(131072-len(table)))
  for L in(0,13):
   folder=a.old/f'granite-l{L}-r16-evaluation01';bound(folder);report=json.loads((folder/'report.json').read_text());assert(report['router_bits'],report['split'],report['tokens'])==(16,'evaluation',72);sources.append({'path':str(folder),'manifest_sha256':sha(folder/'manifest.json'),'runtime_sha256':sha(folder/'runtime.npz')})
   with np.load(folder/'runtime.npz',allow_pickle=False)as z:
    for t in(0,64,71):
     name=f'L{L}T{t}';ids=z['router.ids'][t];weights=const[f'L{L}.down_w8'][ids];mant=const[f'L{L}.down_mant_q31'][ids];exps=const[f'L{L}.down_exp'][ids];records=np.zeros((1536,8,33,16),np.uint8);records[:,:,1:]=weights.transpose(1,0,2).reshape(1536,8,32,16).view(np.uint8)
     for row in range(1536):
      for rank in range(8):records[row,rank,0]=np.frombuffer(struct.pack('<ihhHiH',int(mant[rank,row]),int(exps[rank,row]),0,int(z['router.gate_q15'][t,rank]),int(z['residual_q12'][t,row]),0),np.uint8)
     gup=np.stack([z['expert_gate_q12'][t],z['expert_up_q12'][t]],axis=1).astype('<i4');assert gup.shape==(8,2,512);(a.out/(name+'-gateup.bin')).write_bytes(gup.tobytes());(a.out/(name+'-records.bin')).write_bytes(records.tobytes());(a.out/(name+'-gamma.bin')).write_bytes(const[f'L{L}.next_gamma_q20'].astype('<i4').tobytes())
     cases.append({'name':name,'layer':L,'token':t,'runtime':str(folder),'runtime_sha256':sha(folder/'runtime.npz'),'compiled':str(compiled),'compiled_manifest_sha256':sha(compiled/'manifest.json'),'ids':ids.astype(int).tolist(),'coefficient':int(const['residual_multiplier_q20']),'gateup':name+'-gateup.bin','records':name+'-records.bin','gamma':name+'-gamma.bin','revision':'a02780686e08a03fe0d2679a293b5c74a90efa89'})
 (a.out/'cases.json').write_text(json.dumps(cases,indent=2)+'\n');(a.out/'vectors.tsv').write_text(''.join(' '.join([c['name'],*[str(a.out/c[k])for k in('gateup','records','gamma')],str(a.out/'lut.bin'),str(c['coefficient'])])+'\n'for c in cases));bd=json.loads((ROOT/'binding.json').read_text());fs=[f for f in a.out.iterdir()if f.is_file()];(a.out/'manifest.json').write_text(json.dumps({'status':'PACKED_ORIGINAL_GATEUP_NO_MID_A8_DELTA','source':bd,'external_sources':sources,'artifacts':[{'path':f.name,'bytes':f.stat().st_size,'sha256':sha(f)}for f in fs]},indent=2)+'\n');print('PACKED_ORIGINAL_GATEUP_NO_MID_A8_DELTA')
if __name__=='__main__':main()
