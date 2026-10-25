"""Read-only frozen inputs. Pack only A/W/scales/gates/residual, never computed acc."""
import argparse,json,hashlib,struct
from pathlib import Path
import numpy as np
from inputs import sha,bound

def main():
 p=argparse.ArgumentParser();p.add_argument('--old',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(exist_ok=False);compiled=a.old/'granite-compiled01';bound(compiled);cases=[]
 with np.load(compiled/'constants.npz',allow_pickle=False)as const:
  for layer in(0,13):
   folder=a.old/f'granite-l{layer}-r16-evaluation01';bound(folder)
   with np.load(folder/'runtime.npz',allow_pickle=False)as z:
    for token in(0,64,71):
     name=f'L{layer}T{token}';ids=z['router.ids'][token];aa=z['mid_a8'][token];w=const[f'L{layer}.down_w8'][ids];mant=const[f'L{layer}.down_mant_q31'][ids];exp=const[f'L{layer}.down_exp'][ids]
     shifts=31-exp.astype(np.int32)-z['mid_delta'][token,:,None].astype(np.int32)
     if shifts.min()<0 or shifts.max()>32767:raise ValueError('physical signed16 scale shift')
     blocks=np.zeros((1536,8,65,16),np.uint8);blocks[:,:,1:,:8]=aa.reshape(1,8,64,8).view(np.uint8);blocks[:,:,1:,8:]=w.transpose(1,0,2).reshape(1536,8,64,8).view(np.uint8)
     mult=int(const['residual_multiplier_q20'])
     for row in range(1536):
      for rank in range(8):blocks[row,rank,0]=np.frombuffer(struct.pack('<ihHiI',int(mant[rank,row]),int(shifts[rank,row]),int(z['router.gate_q15'][token,rank]),int(z['residual_q12'][token,row]),mult),np.uint8)
     path=a.out/(name+'.bin');path.write_bytes(blocks.tobytes());gamma=const[f'L{layer}.next_gamma_q20'].astype('<i4').tobytes().hex()
     expected={'acc':z['down_acc32'][token].T.astype(int).tolist(),'down':z['down_q12'][token].T.astype(int).tolist(),'joined':z['layer_output_q12'][token].astype(int).tolist(),'norm':z['next_norm_q12'][token].astype(int).tolist()}
     ep=a.out/(name+'-original.json');ep.write_text(json.dumps(expected)+'\n')
     cases.append({'name':name,'payload':path.name,'payload_bytes':path.stat().st_size,'payload_sha256':sha(path),'gamma':gamma,'original':ep.name,'original_sha256':sha(ep),'runtime_sha256':sha(folder/'runtime.npz'),'compiled_manifest_sha256':sha(compiled/'manifest.json'),'revision':'a02780686e08a03fe0d2679a293b5c74a90efa89','layer':layer,'token':token,'ids':ids.astype(int).tolist()})
 (a.out/'cases.json').write_text(json.dumps(cases,indent=2)+'\n')
 with(a.out/'vectors.tsv').open('w')as f:
  for c in cases:f.write(c['name']+' '+str(a.out/c['payload'])+' '+c['gamma']+'\n')
 files=[p for p in a.out.iterdir()if p.is_file()]
 (a.out/'manifest.json').write_text(json.dumps({'status':'PACKED_NO_HOST_INTERMEDIATE_MATH','cases':6,'K':512,'H':1536,'experts':8,'artifacts':[{'path':p.name,'bytes':p.stat().st_size,'sha256':sha(p)}for p in files]},indent=2)+'\n');print('PACKED',len(cases))
if __name__=='__main__':main()
