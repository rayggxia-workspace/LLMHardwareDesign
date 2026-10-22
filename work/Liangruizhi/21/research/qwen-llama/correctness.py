"""Reproducible synthetic prefill/decode subgraph correctness.

Uses NumPy and synthetic tensors only; no weights, training or hardware timing.
Run python -B correctness.py --config tiny-benchmarks.json --out results.json.
"""
import hashlib,json,time,pathlib
import numpy as np
import argparse
here=pathlib.Path(__file__).resolve().parent
parser=argparse.ArgumentParser(description='Synthetic inference subgraph partition/state correctness; no model weights.')
parser.add_argument('--config',type=pathlib.Path,default=here/'tiny-benchmarks.json')
parser.add_argument('--out',type=pathlib.Path,default=here/'correctness-results.json')
args=parser.parse_args()
config_path=args.config.resolve()
output_path=args.out.resolve()
configs=json.loads(config_path.read_text())['cases']
rng=np.random.default_rng(20261022)
records=[]
bench_started=time.perf_counter()
def digest_arrays(*arrays):
 h=hashlib.sha256()
 for a in arrays:
  h.update(str((a.shape,str(a.dtype))).encode());h.update(np.ascontiguousarray(a).tobytes())
 return h.hexdigest()
def check(name,a,b,shape,inputs):
 error=float(np.max(np.abs(a-b))) if a.size else 0.
 assert error<5e-11,(name,error)
 records.append(dict(name=name,shape=shape,max_absolute_error=error,tolerance=5e-11,input_sha256=inputs))
def softmax(x):
 e=np.exp(x-x.max(axis=-1,keepdims=True));return e/e.sum(axis=-1,keepdims=True)
def sigmoid(x):return 1/(1+np.exp(-x))
def silu(x):return x*sigmoid(x)
def dense_attention(q,k,v):
 hq=q.shape[1];ratio=hq//k.shape[1]
 kr=np.repeat(k,ratio,axis=1);vr=np.repeat(v,ratio,axis=1)
 scores=np.einsum('bhtd,bhsd->bhts',q,kr)/np.sqrt(q.shape[-1])
 mask=np.triu(np.ones((q.shape[2],k.shape[2]),dtype=bool),1)
 scores=np.where(mask,-np.inf,scores)
 return np.einsum('bhts,bhsd->bhtd',softmax(scores),vr)
def decoded_attention(q,k,v):
 b,hq,t,d=q.shape;out=np.empty_like(q);ratio=hq//k.shape[1]
 for i in range(t):
  for h in range(hq):
   kh=h//ratio
   scores=np.einsum('bd,bsd->bs',q[:,h,i],k[:,kh,:i+1])/np.sqrt(d)
   out[:,h,i]=np.einsum('bs,bsd->bd',softmax(scores),v[:,kh,:i+1])
 return out
def tiled_online(q,k,v,tile):
 b,hq,t,d=q.shape;out=np.empty_like(q);ratio=hq//k.shape[1]
 for batch in range(b):
  for h in range(hq):
   kh=h//ratio
   for i in range(t):
    m=-np.inf;l=0.;o=np.zeros(d)
    for s in range(0,i+1,tile):
     stop=min(i+1,s+tile)
     score=k[batch,kh,s:stop]@q[batch,h,i]/np.sqrt(d)
     nm=max(m,float(score.max()));alpha=np.exp(m-nm);p=np.exp(score-nm)
     o=alpha*o+p@v[batch,kh,s:stop];l=alpha*l+p.sum();m=nm
    out[batch,h,i]=o/l
 return out
for cfg in configs:
 for b in [1,2]:
  for t in [7,17]:
   d=cfg['dh'];hq=cfg['Hq'];hkv=cfg['Hkv']
   q=rng.normal(size=(b,hq,t,d));k=rng.normal(size=(b,hkv,t,d));v=rng.normal(size=k.shape)
   if cfg.get('qk_norm'):
    q=q/np.sqrt(np.mean(q*q,axis=-1,keepdims=True)+1e-6)
    k=k/np.sqrt(np.mean(k*k,axis=-1,keepdims=True)+1e-6)
   ref=dense_attention(q,k,v);identity=digest_arrays(q,k,v)
   dims=dict(case=cfg['id'],B=b,T=t,Hq=hq,Hkv=hkv,dh=d)
   check('prefill_vs_native_kv_token_decode',ref,decoded_attention(q,k,v),dims,identity)
   for tile in [1,4,9]:check('prefill_vs_grouped_online_softmax',ref,tiled_online(q,k,v,tile),dict(dims,tile=tile),identity)
for cfg in configs:
 d=cfg['D'];f=cfg.get('F',cfg.get('Fe'));m=19
 x=rng.normal(size=(m,d));wg=rng.normal(size=(d,f))/np.sqrt(d)
 wu=rng.normal(size=(d,f))/np.sqrt(d);wd=rng.normal(size=(f,d))/np.sqrt(f)
 ref=(silu(x@wg)*(x@wu))@wd;identity=digest_arrays(x,wg,wu,wd)
 for tile in [1,7,13]:
  out=np.zeros_like(ref)
  for s in range(0,f,tile):
   end=min(f,s+tile);out+=(silu(x@wg[:,s:end])*(x@wu[:,s:end]))@wd[s:end]
  check('swiglu_intermediate_channel_partition',ref,out,dict(case=cfg['id'],M=m,D=d,F=f,tile=tile),identity)
for cfg in [c for c in configs if 'E' in c]:
 e,d,f,top=cfg['E'],cfg['D'],cfg['Fe'],cfg['top_k'];m=19
 x=rng.normal(size=(m,d));wg=rng.normal(size=(e,d,f))/np.sqrt(d)
 wu=rng.normal(size=(e,d,f))/np.sqrt(d);wd=rng.normal(size=(e,f,d))/np.sqrt(f)
 for mode in ['random','concentrated']:
  logits=rng.normal(size=(m,e)) if mode=='random' else np.broadcast_to(-np.arange(e,dtype=float),(m,e)).copy()
  probability=softmax(logits)
  indices=np.argsort(-probability,axis=-1,kind='stable')[:,:top]
  scores=np.take_along_axis(probability,indices,axis=-1);scores/=scores.sum(axis=-1,keepdims=True)
  weights=np.zeros((m,e));np.put_along_axis(weights,indices,scores,axis=-1)
  reference=np.zeros((m,d))
  for expert in range(e):reference+=weights[:,expert,None]*((silu(x@wg[expert])*(x@wu[expert]))@wd[expert])
  dispatched=np.zeros_like(reference)
  for token in range(m):
   for rank in range(top):
    expert=indices[token,rank]
    dispatched[token]+=scores[token,rank]*((silu(x[token]@wg[expert])*(x[token]@wu[expert]))@wd[expert])
  extra_arrays=[]
  if cfg.get('shared_expert'):
   sf=cfg['shared_Fe'];sg=rng.normal(size=(d,sf))/np.sqrt(d);su=rng.normal(size=(d,sf))/np.sqrt(d)
   sd=rng.normal(size=(sf,d))/np.sqrt(sf);gate=rng.normal(size=(d,1))/np.sqrt(d)
   shared=(silu(x@sg)*(x@su))@sd*sigmoid(x@gate)
   reference+=shared;dispatched+=shared
   extra_arrays=[sg,su,sd,gate]
  check('moe_topk_mask_vs_dispatch_scatter',reference,dispatched,dict(case=cfg['id'],mode=mode,M=m,D=d,E=e,top_k=top,Fe=f,always_on_shared=cfg.get('shared_expert',False)),digest_arrays(x,wg,wu,wd,logits,*extra_arrays))
def recurrent(q,k,v,g,beta,state):
 state=state.copy();outputs=[]
 for t in range(q.shape[2]):
  state*=np.exp(g[:,:,t,None,None])
  memory=np.einsum('bhkv,bhk->bhv',state,k[:,:,t])
  delta=(v[:,:,t]-memory)*beta[:,:,t,None]
  state+=np.einsum('bhk,bhv->bhkv',k[:,:,t],delta)
  outputs.append(np.einsum('bhk,bhkv->bhv',q[:,:,t],state))
 return np.stack(outputs,axis=2),state
def affine_segmented(q,k,v,g,beta,state,chunk):
 b,h,t,dk=q.shape;dv=v.shape[-1];state=state.copy();out=np.empty((b,h,t,dv))
 for start in range(0,t,chunk):
  initial=state.copy();prefix_a=np.broadcast_to(np.eye(dk),(b,h,dk,dk)).copy();prefix_b=np.zeros_like(state)
  for i in range(start,min(t,start+chunk)):
   ki=k[:,:,i];vi=v[:,:,i];be=beta[:,:,i]
   at=np.exp(g[:,:,i,None,None])*(np.eye(dk)-be[:,:,None,None]*np.einsum('bhk,bhl->bhkl',ki,ki))
   bt=be[:,:,None,None]*np.einsum('bhk,bhv->bhkv',ki,vi)
   prefix_a=at@prefix_a;prefix_b=at@prefix_b+bt
   state=prefix_a@initial+prefix_b
   out[:,:,i]=np.einsum('bhk,bhkv->bhv',q[:,:,i],state)
 return out,state
for cfg in [c for c in configs if 'linear_Hv' in c]:
 b,t,hk,hv,dk,dv=2,17,cfg['linear_Hk'],cfg['linear_Hv'],cfg['linear_dk'],cfg['linear_dv']
 q=rng.normal(size=(b,hk,t,dk));k=rng.normal(size=q.shape)
 q/=np.sqrt(np.sum(q*q,axis=-1,keepdims=True)+1e-6)*np.sqrt(dk)
 k/=np.sqrt(np.sum(k*k,axis=-1,keepdims=True)+1e-6)
 q=np.repeat(q,hv//hk,axis=1);k=np.repeat(k,hv//hk,axis=1)
 v=rng.normal(size=(b,hv,t,dv));g=-np.logaddexp(0,rng.normal(size=(b,hv,t)))*.2
 beta=sigmoid(rng.normal(size=(b,hv,t)));state=rng.normal(size=(b,hv,dk,dv))*.1
 ref,ref_state=recurrent(q,k,v,g,beta,state);identity=digest_arrays(q,k,v,g,beta,state)
 for chunk in [1,5,9]:
  out,end=affine_segmented(q,k,v,g,beta,state,chunk)
  check('gated_delta_recurrence_vs_affine_prefix_output',ref,out,dict(case=cfg['id'],B=b,T=t,Hv=hv,dk=dk,dv=dv,chunk=chunk),identity)
  check('gated_delta_final_matrix_state',ref_state,end,dict(case=cfg['id'],chunk=chunk),identity)
 channels=2*hk*dk+hv*dv;kernel=cfg['conv_kernel']
 z=rng.normal(size=(b,channels,t));w=rng.normal(size=(channels,kernel))
 padded=np.pad(z,((0,0),(0,0),(kernel-1,0)))
 ref=np.stack([np.einsum('bck,ck->bc',padded[:,:,i:i+kernel],w) for i in range(t)],axis=2)
 for chunk in [1,5,9]:
  history=np.zeros((b,channels,kernel-1));ys=[]
  for start in range(0,t,chunk):
   for i in range(start,min(t,start+chunk)):
    window=np.concatenate([history,z[:,:,i:i+1]],axis=2)
    ys.append(np.einsum('bck,ck->bc',window,w));history=window[:,:,1:].copy()
  check('depthwise_causal_conv_chunk_handoff',ref,np.stack(ys,axis=2),dict(case=cfg['id'],B=b,T=t,channels=channels,kernel=kernel,chunk=chunk),digest_arrays(z,w))
report=dict(status='pass',count=len(records),max_absolute_error=max(r['max_absolute_error'] for r in records),
 elapsed_seconds=time.perf_counter()-bench_started,seed=20261022,numpy_version=np.__version__,
 config_sha256=hashlib.sha256(config_path.read_bytes()).hexdigest(),
 source_sha256=hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),
 records=records,scope='Float64 mathematical subgraph correctness on synthetic weights/tensors only. Attention Q/K supplied after positional transform; no complete model logits, real inference runtime/throughput, trained router distribution, backward execution, silicon area, power or timing claim.',
 partition_effect='Checks legal mathematical cuts/reordering and persistent state handoff; physical partition selection still needs a storage/interconnect/technology cost model.')
output_path.parent.mkdir(parents=True,exist_ok=True)
output_path.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k!='records'}))
