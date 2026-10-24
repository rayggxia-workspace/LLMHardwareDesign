"""Integer causal convolution history with fixed calibration scales; SiLU remains an explicit FP64 bridge.
W8 per channel; H8 or H16 per channel; full four-tap I32 dot with Python-int oracle. No target timing.
"""
import argparse,hashlib,io,json,math,os,platform,time,zipfile
from pathlib import Path
import numpy as np
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,x):Path(p).write_text(json.dumps(x,indent=2,allow_nan=False)+'\n',newline='\n')
def npz(path,arrays):
 with zipfile.ZipFile(path,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6)as z:
  for k,v in sorted(arrays.items()):
   s=io.BytesIO();np.save(s,np.asarray(v),allow_pickle=False);i=zipfile.ZipInfo(k+'.npy',(2026,10,24,0,0,0));i.compress_type=zipfile.ZIP_DEFLATED;z.writestr(i,s.getvalue())
def exponent(x,limit,axis):
 maximum=np.max(np.abs(np.asarray(x,dtype=np.float64)),axis=axis)
 return np.where(maximum>0,np.ceil(np.log2(np.maximum(maximum,1e-300)/limit)),0).astype(np.int16)
def encode(x,e,limit):
 before=np.rint(np.ldexp(np.asarray(x,dtype=np.float64),-np.asarray(e,dtype=np.int64)))
 count=int(np.count_nonzero((before>limit)|(before<-limit)))
 return np.clip(before,-limit,limit).astype(np.int16 if limit>127 else np.int8),count
def silu(x):
 x=np.asarray(x,dtype=np.float64);sig=np.empty_like(x);positive=x>=0
 sig[positive]=1/(1+np.exp(-x[positive]));z=np.exp(x[~positive]);sig[~positive]=z/(1+z)
 return x*sig
def err(x,y):
 d=np.asarray(x,dtype=np.float64)-y
 return {'relative_l2':float(np.linalg.norm(d)/max(np.linalg.norm(y),1e-30)),'max_abs':float(np.max(np.abs(d)))}
def run_chain(raw,initial,w):
 if raw.ndim!=3 or initial.shape!=(*raw.shape[:2],4)or w.shape!=(raw.shape[1],4):raise ValueError('shape')
 if not np.issubdtype(raw.dtype,np.integer)or not np.issubdtype(initial.dtype,np.integer)or w.dtype!=np.int8:raise ValueError('integer formats')
 history=initial.copy();states=[history.copy()];acc=[];oracle_terms=0
 for t in range(raw.shape[2]):
  history=np.concatenate([history[:,:,1:],raw[:,:,t:t+1]],axis=2)
  dot=np.sum(history.astype(np.int32)*w[None,:,:].astype(np.int32),axis=2,dtype=np.int32)
  exact=np.array([[sum(int(history[b,c,j])*int(w[c,j])for j in range(4))for c in range(raw.shape[1])]for b in range(raw.shape[0])],dtype=np.int64)
  if not np.array_equal(dot.astype(np.int64),exact):raise OverflowError('I32 dot')
  oracle_terms+=exact.size*4;acc.append(dot);states.append(history.copy())
 return np.stack(acc,axis=2),np.stack(states),oracle_terms
def to_qkv(y):
 if y.shape!=(1,512,32):raise ValueError('captured full selected group')
 q=np.repeat(y[:,:128,:].transpose(0,2,1)[:,:,None,:],2,axis=2)
 k=np.repeat(y[:,128:256,:].transpose(0,2,1)[:,:,None,:],2,axis=2)
 v=y[:,256:,:].reshape(1,2,128,32).transpose(0,3,1,2)
 return {'query':q,'key':k,'value':v}
def main():
 p=argparse.ArgumentParser();p.add_argument('--capture',required=True,type=Path);p.add_argument('--out',required=True,type=Path);p.add_argument('--binding',required=True,type=Path);a=p.parse_args()
 if a.out.exists():raise ValueError('refuse overwrite')
 b=json.loads(a.binding.read_text())
 if sha(__file__)!=b['conv_sha256']:raise ValueError('source SHA')
 m=json.loads((a.capture/'manifest.json').read_text());want=m['artifacts']['state-raw.npz']
 if sha(a.capture/'state-raw.npz')!=want['sha256']:raise ValueError('capture SHA')
 z=np.load(a.capture/'state-raw.npz',allow_pickle=False);w=z['weight.conv'];ew=exponent(w,127,1);wc,wclip=encode(w,ew[:,None],127)
 arrays={'weight.codes':wc,'weight.exponent':ew};records=[];begin=time.monotonic()
 for bits in (8,16):
  limit=(1<<(bits-1))-1
  calibration=np.concatenate([z['calibration.conv.boundaries'][0],z['calibration.conv.input']],axis=2)
  ea=exponent(calibration,limit,(0,2));arrays['conv%d.activation_exponent'%bits]=ea
  for name in ('calibration','evaluation'):
   x=z[name+'.conv.input'];h=z[name+'.conv.boundaries'][0]
   xc,clip=encode(x,ea[None,:,None],limit);hc,hclip=encode(h,ea[None,:,None],limit)
   ac,hs,terms=run_chain(xc,hc,wc)
   physical=np.ldexp(ac.astype(np.float64),(ea+ew)[None,:,None]);post=silu(physical)
   truth=z[name+'.conv.output'].astype(np.float64)
   quant_hist,_=encode(z[name+'.conv.boundaries'],ea[None,None,:,None],limit)
   if not np.array_equal(hs,quant_hist):raise AssertionError('history/state projection')
   prefix='conv%d.%s.'%(bits,name)
   arrays[prefix+'input.codes']=xc;arrays[prefix+'initial.codes']=hc;arrays[prefix+'accumulator']=ac;arrays[prefix+'history.codes']=hs;arrays[prefix+'post_silu_fp64']=post
   for k,v in to_qkv(post).items():arrays[prefix+k]=v
   frames=x.shape[2];channels=x.shape[1];hist_bytes=channels*4*(bits//8);product_count=frames*channels*4
   records.append({'profile':'conv%d'%bits,'case':name,'H_bits':bits,'W_bits':8,'acc_bits':32,'source_input_clips':clip,'initial_history_clips':hclip,'weight_clips':wclip,'output':err(post,truth),'oracle_integer_terms':terms,'integer_state_values':int(hs.size),'max_abs_I32_accumulator':int(np.max(np.abs(ac.astype(np.int64)))),'worst_code_full4tap_bound':4*limit*127,'full_selected_history_bytes':hist_bytes,'full_native8192ch_history_bytes_same_format_candidate':8192*4*(bits//8),'scale_profile_bytes':channels*4,'S8_products':product_count*(3 if bits==16 else 1),'eight_lane_product_cycle_lower_bound':math.ceil(product_count*(3 if bits==16 else 1)/8),'1RW_128bit_naive_shift_history_read_write_beats_per_step':math.ceil(hist_bytes/16)*2,'ring4_candidate_read3_write1_beats_per_step':math.ceil(channels*4*(bits//8)/16),'ring_scope':'alternate physical address mapping and byte-enable/epoch cost unimplemented; native four-slot logical history retained','SiLU':'FP64 bridge; no integer sigmoid/exp or target cycle acceptance','source_quantization':'static dyadic scales compiled from independent calibration source/history only; incoming projection and output query norm/gates not integer here'})
 a.out.mkdir();npz(a.out/'conv-output.npz',arrays);save(a.out/'metrics.json',records);save(a.out/'manifest.json',{'status':'PASS','source_commit':b['commit'],'source_sha256':sha(__file__),'capture_manifest_sha256':sha(a.capture/'manifest.json'),'input_sha256':want['sha256'],'scope':__doc__,'float_boundaries':['FP32 capture -> dyadic source encoding','offline scale compiler','SiLU FP64 bridge','subsequent QK norm/decay/beta compilation remain explicit in state experiment'],'environment':{'python':platform.python_version(),'numpy':np.__version__},'seconds':time.monotonic()-begin,'artifacts':{p.name:{'bytes':p.stat().st_size,'sha256':sha(p)}for p in a.out.iterdir()if p.is_file()}})
 print(json.dumps({'status':'PASS','conditions':len(records)}))
if __name__=='__main__':main()
