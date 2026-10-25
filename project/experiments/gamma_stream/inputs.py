"""Server-only selection/encoding of existing data; never downloads or loads a model."""
import argparse,hashlib,json,math
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[3]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def put(p,x):p.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n',encoding='utf-8')
def encode(a,q):
 a=np.asarray(a,dtype=np.float64);v=np.rint(a*(2**q))
 if not np.all(np.isfinite(v)) or np.any(v<-(1<<31)) or np.any(v>=(1<<31)):raise ValueError('encoding overflow/nonfinite')
 return v.astype('<i4')
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--old',type=Path,required=True);ap.add_argument('--gemma',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
 bd=json.loads((ROOT/'binding.json').read_text())
 for path,h in bd['sources'].items():
  if sha(ROOT/path)!=h:raise ValueError('source SHA')
 om=json.loads((a.old/'manifest.json').read_text())
 if om['status']!='PASS_PHYSICAL_REPACK_ROUNDTRIP':raise ValueError('old physical accepted status')
 for e in om['artifacts']:
  if sha(a.old/e['path'])!=e['sha256']:raise ValueError('old actual bytes '+e['path'])
 gm=json.loads((a.gemma/'manifest.json').read_text());desc=gm['artifacts']['selected-raw.npz'];npz=a.gemma/'selected-raw.npz'
 if gm['status']!='PASS' or gm['model']!={'id':'google/gemma-3-4b-it','revision':'093f9f388b31de276ce2de164bdc2081324b9767'}:raise ValueError('frozen Gemma')
 if npz.stat().st_size!=desc['bytes'] or sha(npz)!=desc['sha256']:raise ValueError('Gemma byte SHA')
 impl=Path(gm['implementation']['path'])
 if sha(impl)!=gm['implementation']['sha256'] or gm['implementation']['sha256']!='b92013d0558381b76b0f74d2b30890cd3aaa9daa58a269d7a12b5a5c5a8e9eb7':raise ValueError('exact original implementation')
 source=impl.read_text();section=source[source.index('class Gemma3RMSNorm'):source.index('class Gemma3RotaryEmbedding')]
 if 'output = output * (1.0 + self.weight.float())' not in section:raise ValueError('effective gamma formula')
 if gm['config']['text_config']['rms_norm_eps']!=1e-6:raise ValueError('epsilon binding')
 a.out.mkdir(parents=True,exist_ok=False);cases=[];old=json.loads((a.old/'cases.json').read_text())
 if len(old)!=6:raise ValueError('six complete Granite cases')
 for c in old:
  cases.append({'name':c['name'],'kind':'chain','h':1536,'epsilon':17,'coefficient':c['coefficient'],'gamma':c['gamma'],'x':'-','payload0':str(a.old/c['payload0']),'payload1':str(a.old/c['payload1']),'source_case':c,'source_kind':'actual Granite complete M chain'})
 with np.load(npz,allow_pickle=False)as z:
  selected=[]
  for layer in (0,5):
   prefix=f'prefix128.norm.layer{layer}.input_layernorm'
   if prefix+'.input'not in z:raise ValueError('explicit evaluation source key '+prefix)
   xx=z[prefix+'.input'];yy=z[prefix+'.output'];raw=z[f'norm_weight.layer{layer}.input_layernorm'];positions=z[prefix+'.rows_within_call']
   if xx.shape[1:]!=(2560,)or yy.shape!=xx.shape or raw.shape!=(2560,):raise ValueError('full hidden axis')
   row=0;x=encode(xx[row],12);g=encode(1.+raw.astype(np.float64),20)
   fp=xx[row].astype(np.float64);effective=1.+raw.astype(np.float64);native=yy[row].astype(np.float64);recomputed=fp/np.sqrt(np.mean(fp*fp)+1e-6)*effective
   rel=float(np.linalg.norm(recomputed-native)/max(np.linalg.norm(native),1e-30))
   if rel>1e-5:raise ValueError('source effective gamma native mismatch')
   name=f'gemma-layer{layer}-row{int(positions[row])}'
   fpfile=name+'-native.json';put(a.out/fpfile,{'x':fp.tolist(),'effective_gamma':effective.tolist(),'captured_native':native.tolist(),'raw_gamma':raw.astype(float).tolist()})
   c={'name':name,'kind':'norm','h':2560,'epsilon':17,'coefficient':0,'gamma':g.tobytes().hex(),'x':x.tobytes().hex(),'payload0':'-','payload1':'-','native':fpfile,'source_kind':'actual Gemma evaluation full norm row','source_key':prefix,'row':row,'source_token_position':int(positions[row]),'effective_gamma':'1+raw_weight','native_formula_relative_l2':rel}
   cases.append(c);selected.append({'name':name,'input_shape':list(xx.shape),'raw_weight_sha256':hashlib.sha256(raw.tobytes()).hexdigest(),'row':row,'key':prefix})
 for name,x,g,eps in [('synthetic-zero',np.zeros(2560,dtype='<i4'),np.full(2560,1<<20,dtype='<i4'),17),('synthetic-tile-distinct',np.asarray([(i*7919)%65537-32768 for i in range(2560)],dtype='<i4'),np.asarray([(i%17-8)*(1<<18)for i in range(2560)],dtype='<i4'),17),('synthetic-signed-extrema',np.asarray([-(1<<31)if i%2 else(1<<31)-1 for i in range(2560)],dtype='<i4'),np.asarray([-(1<<31)if i%3 else(1<<31)-1 for i in range(2560)],dtype='<i4'),17),('synthetic-zero-den',np.zeros(2560,dtype='<i4'),np.full(2560,1<<20,dtype='<i4'),0)]:
  cases.append({'name':name,'kind':'norm','h':2560,'epsilon':eps,'coefficient':0,'gamma':g.tobytes().hex(),'x':x.tobytes().hex(),'payload0':'-','payload1':'-','source_kind':'explicit synthetic boundary'})
 put(a.out/'cases.json',cases)
 (a.out/'vectors93.tsv').write_text(''.join(f"{c['name']} {int(c['kind']=='norm')} {c['h']} {c['epsilon']} {c['coefficient']} {c['payload0']} {c['payload1']} {c['gamma']} {c['x']}\n"for c in cases))
 put(a.out/'manifest.json',{'schema':'gamma93-input-v1','status':'PASS_VERIFIED_INPUTS_NOT_RTL','source':bd,'old_root':str(a.old),'old_manifest_sha256':sha(a.old/'manifest.json'),'gemma_root':str(a.gemma),'gemma_manifest_sha256':sha(a.gemma/'manifest.json'),'gemma_npz':desc,'gemma_implementation':gm['implementation'],'gemma_model':gm['model'],'selected':selected,'encoding':'independent per-value RNE FP64 x*2^12 and (1+raw_gamma)*2^20 to I32; no saturation; epsilon17. Encoding/FP quality is offline, RTL integer only.','artifacts':[{'path':p.name,'bytes':p.stat().st_size,'sha256':sha(p)}for p in sorted(a.out.iterdir())if p.is_file()]})
 print('PASS_VERIFIED_INPUTS_NOT_RTL')
if __name__=='__main__':main()
