"""Exact source-bound adapter: replace precombined shift with raw units for RTL."""
import argparse,json,struct
from pathlib import Path
import numpy as np
from inputs import sha,bound

def main():
 p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--old',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(exist_ok=False);bound(a.input);compiled=a.old/'granite-compiled01';bound(compiled);cases=json.loads((a.input/'cases.json').read_text());deltas={}
 for layer in(0,13):
  folder=a.old/f'granite-l{layer}-r16-evaluation01';bound(folder)
  with np.load(folder/'runtime.npz',allow_pickle=False)as z:deltas[layer]=z['mid_delta'].copy()
 with np.load(compiled/'constants.npz',allow_pickle=False)as const:
  for c in cases:
   layer=c['layer'];token=c['token'];payload=bytearray((a.input/c['payload']).read_bytes());exps=const[f'L{layer}.down_exp'][c['ids']];ds=deltas[layer][token];coefficient=None
   for row in range(1536):
    for rank in range(8):
     offset=(row*8+rank)*65*16;mant,shift,gate,res,coef=struct.unpack('<ihHiI',payload[offset:offset+16]);exp=int(exps[rank,row]);delta=int(ds[rank]);assert shift==31-exp-delta
     if coefficient is None:coefficient=coef
     assert coef==coefficient
     payload[offset:offset+16]=struct.pack('<ihhHiH',mant,exp,delta,gate,res,0)
   target=a.out/c['payload'];target.write_bytes(payload);c['payload_sha256']=sha(target);c['coefficient']=coefficient;c['format']='S32 mantQ31 / S16 weight exponent / S16 A delta / U16 gateQ15 / S32 residualQ12 / reserved0. RTL derives 31-exp-delta and guards/clamps using exact64RNE rule.'
   (a.out/c['original']).write_bytes((a.input/c['original']).read_bytes())
 (a.out/'cases.json').write_text(json.dumps(cases,indent=2)+'\n')
 (a.out/'vectors.tsv').write_text(''.join(c['name']+' '+str(a.out/c['payload'])+' '+c['gamma']+' '+str(c['coefficient'])+'\n'for c in cases))
 fs=[f for f in a.out.iterdir()if f.is_file()];(a.out/'manifest.json').write_text(json.dumps({'status':'RAW_UNITS_PACKED_NOT_COMPUTED_ACC','cases':6,'source_input_manifest_sha256':sha(a.input/'manifest.json'),'artifacts':[{'path':f.name,'bytes':f.stat().st_size,'sha256':sha(f)}for f in fs]},indent=2)+'\n');print('RAW_UNITS_PACKED',len(cases))
if __name__=='__main__':main()
