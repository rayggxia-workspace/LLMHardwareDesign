"""Bounded Qwen3.5 native CPU capture of a full-hidden consumer chain and actual continuous R inputs.
No new model downloads; original BF16 checkpoint computes FP32. Captures are references, not integer qualification.
"""
import argparse,hashlib,inspect,io,json,os,platform,time,traceback,zipfile
from pathlib import Path
import numpy as np
import torch
import transformers

def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb')as f:
  for b in iter(lambda:f.read(8<<20),b''):h.update(b)
 return h.hexdigest()
def save(p,x):Path(p).write_text(json.dumps(x,indent=2,allow_nan=False,default=str)+'\n',newline='\n')
def npz(p,arrays):
 with zipfile.ZipFile(p,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6)as z:
  for k,a in sorted(arrays.items()):
   buf=io.BytesIO();np.save(buf,np.asarray(a),allow_pickle=False);info=zipfile.ZipInfo(k+'.npy',(2026,10,24,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;z.writestr(info,buf.getvalue())
def main():
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--binding',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--threads',type=int,default=24);a=p.parse_args()
 if a.out.exists():raise ValueError('refuse overwrite')
 if not os.environ.get('SLURM_JOB_ID')or a.threads>int(os.environ['SLURM_CPUS_PER_TASK']):raise ValueError('Slurm allocation')
 b=json.loads(a.binding.read_text())
 for path,want in b['sources'].items():
  if sha(Path(__file__).resolve().parents[3]/path)!=want:raise ValueError('source binding '+path)
 old=json.loads((a.root/'qwen35-gqa01/manifest.json').read_text());folder=a.root/'models/qwen35-4b-851bf6e8'
 os.environ['HF_HUB_OFFLINE']='1';os.environ['TRANSFORMERS_OFFLINE']='1'
 from transformers.models.qwen3_5 import modeling_qwen3_5 as impl
 from transformers import AutoConfig,AutoTokenizer
 if sha(inspect.getfile(impl))!='b4b17fe08d8d54da34a0fce78639666279ae7fd0a9e4ec06fce6602774707ca3':raise ValueError('framework source')
 if torch.__version__!='2.10.0+cpu'or transformers.__version__!='5.20.2':raise ValueError('environment')
 receipts={}
 for name,r in old['files'].items():
  f=folder/name
  if f.stat().st_size!=r['bytes']or sha(f)!=r['sha256']:raise ValueError('model file '+name)
  receipts[name]=r
 torch.set_num_threads(a.threads);torch.set_num_interop_threads(1);torch.manual_seed(20261024);torch.use_deterministic_algorithms(True)
 a.out.mkdir();start=time.monotonic();m={'status':'ERROR','source_commit':b['commit'],'source_binding_sha256':sha(a.binding),'model':old['model'],'model_files':receipts,'implementation':old['implementation'],'versions':{'python':platform.python_version(),'torch':torch.__version__,'transformers':transformers.__version__,'numpy':np.__version__},'job':os.environ['SLURM_JOB_ID'],'threads':a.threads,'scope':__doc__,'integer_qualified':False}
 handles=[];original_recur=impl.torch_recurrent_gated_delta_rule;original_conv=impl.causal_conv1d_update
 arrays={};chain={};rarrays={};ctx={'active':False,'name':None,'begin':0,'decode':False};frames={};recur_frames=[];conv_frames=[];raw_gate_frames={'a':[],'b':[]}
 try:
  cfg=AutoConfig.from_pretrained(folder,local_files_only=True,trust_remote_code=False)
  model,loading=impl.Qwen3_5ForCausalLM.from_pretrained(folder,config=cfg.text_config,local_files_only=True,trust_remote_code=False,use_safetensors=True,dtype=torch.float32,attn_implementation='eager',output_loading_info=True)
  if any(loading.get(k)for k in ('missing_keys','mismatched_keys','error_msgs')):raise ValueError('model load')
  model.eval();tok=AutoTokenizer.from_pretrained(folder,local_files_only=True,trust_remote_code=False);layers=model.model.layers;gd=layers[0].linear_attn
  def cpu(x):return x.detach().float().cpu().contiguous().numpy().copy()
  heads=[0,1];head_ix=torch.tensor(heads);keydim=gd.key_dim;vstart=2*keydim
  channels=torch.tensor([*range(128),*range(keydim,keydim+128),*range(vstart,vstart+256)])
  chain['weight.down']=cpu(layers[3].mlp.down_proj.weight);chain['weight.next_norm']=cpu(layers[4].input_layernorm.weight);chain['weight.next_projection']=cpu(layers[4].linear_attn.in_proj_qkv.weight[:16])
  rarrays['weight.conv']=cpu(gd.conv1d.weight.squeeze(1)[channels]);rarrays['conv.channel_indices']=channels.numpy()
  rarrays['weight.A_log']=cpu(gd.A_log[head_ix]);rarrays['weight.dt_bias']=cpu(gd.dt_bias[head_ix])
  def capture_field(name,kind):
   def hook(module,args,y):
    x=args[0]if kind=='input'else y
    if ctx['name']is None:return
    if name=='projection':x=x[...,:16]
    frames.setdefault(name,[]).append(cpu(x[0]))
   return hook
  handles.append(layers[3].mlp.down_proj.register_forward_hook(capture_field('A','input')))
  handles.append(layers[3].mlp.down_proj.register_forward_hook(capture_field('down','output')))
  handles.append(layers[3].post_attention_layernorm.register_forward_hook(capture_field('residual','input')))
  handles.append(layers[4].input_layernorm.register_forward_hook(capture_field('sum','input')))
  handles.append(layers[4].input_layernorm.register_forward_hook(capture_field('norm','output')))
  handles.append(layers[4].linear_attn.in_proj_qkv.register_forward_hook(capture_field('projection','output')))
  def active_on(module,args,kwargs):ctx['active']=True
  def active_off(module,args,y):ctx['active']=False
  handles.append(gd.register_forward_pre_hook(active_on,with_kwargs=True));handles.append(gd.register_forward_hook(active_off))
  def gates(name):
   def hook(module,args,y):
    if ctx['decode']:raw_gate_frames[name].append(cpu(y[0,0,head_ix]))
   return hook
  handles.append(gd.in_proj_a.register_forward_hook(gates('a')));handles.append(gd.in_proj_b.register_forward_hook(gates('b')))
  def recur(query,key,value,g,beta,initial_state=None,**kwargs):
   take=ctx['active']and ctx['decode']
   if take:
    if initial_state is None:raise ValueError('real nonzero history required')
    snap={k:cpu(v[:, :,head_ix])for k,v in [('query',query),('key',key),('value',value)]}
    snap.update(g=cpu(g[:,:,head_ix]),beta=cpu(beta[:,:,head_ix]),initial_state=cpu(initial_state[:,head_ix]))
   out,final=original_recur(query,key,value,g,beta,initial_state=initial_state,**kwargs)
   if take:
    snap.update(output=cpu(out[:,:,head_ix]),final_state=cpu(final[:,head_ix]));recur_frames.append(snap)
   return out,final
  def conv(hidden_states,conv_state,weight,bias=None,activation=None):
   take=ctx['active']and ctx['decode']
   if take:
    snap={'input':cpu(hidden_states[:,channels]),'initial_state':cpu(conv_state[:,channels])}
   result=original_conv(hidden_states,conv_state,weight,bias,activation)
   if take:
    snap.update(output=cpu(result[:,channels]),final_state=cpu(conv_state[:,channels]));conv_frames.append(snap)
   return result
  impl.torch_recurrent_gated_delta_rule=recur;impl.causal_conv1d_update=conv
  texts={'calibration':'A technical calibration notebook describes matrix units, vector units, shared memory banks, scales and completion events. A controller reads only completed writes. Numeric contracts record rounding, saturation, code versions and input hashes. This material is calibration only. ',
         'evaluation':'A research team records water use in several gardens. Each sensor measures soil moisture every morning. The notebook preserves original observations and instrument settings. A program computes weekly summaries while retaining daily records. Reviewers verify hand calculated examples. '}
  token_records={};checks=[]
  with torch.inference_mode():
   for name,text in texts.items():
    unit=tok(text,add_special_tokens=False)['input_ids'];ids=torch.tensor([(unit*(160//len(unit)+1))[:160]])
    token_records[name]={'tokens':ids.tolist(),'sha256':hashlib.sha256(ids.numpy().tobytes()).hexdigest(),'text':text}
    frames.clear();recur_frames.clear();conv_frames.clear();raw_gate_frames['a'].clear();raw_gate_frames['b'].clear();ctx.update(name=name,begin=0,decode=False)
    out=model(input_ids=ids[:,:128],use_cache=True,logits_to_keep=1);cache=out.past_key_values
    selection=np.r_[np.arange(8),np.arange(120,128)]if name=='calibration'else np.r_[np.arange(4),np.arange(124,128)]
    label='calibration'if name=='calibration'else'prefill'
    for field,items in frames.items():chain[label+'.'+field]=items[0][selection].copy()
    chain[label+'.rows']=selection
    frames.clear()
    ctx['decode']=True
    for pos in range(128,160):
     ctx['begin']=pos
     out=model(input_ids=ids[:,pos:pos+1],past_key_values=cache,use_cache=True,cache_position=torch.tensor([pos]),position_ids=torch.tensor([[pos]]),attention_mask=torch.ones((1,pos+1),dtype=torch.long),logits_to_keep=1);cache=out.past_key_values
    if len(recur_frames)!=32 or len(conv_frames)!=32:raise ValueError('missing contiguous frames')
    if name=='evaluation':
     for field,items in frames.items():chain['decode.'+field]=np.concatenate(items,axis=0)
     chain['decode.rows']=np.arange(128,160)
    prefix=name+'.'
    for field in ('query','key','value','g','beta','output'):rarrays[prefix+field]=np.concatenate([v[field]for v in recur_frames],axis=1)
    rarrays[prefix+'initial_state']=recur_frames[0]['initial_state'];rarrays[prefix+'final_state']=recur_frames[-1]['final_state']
    rarrays[prefix+'state_boundaries']=np.stack([recur_frames[0]['initial_state'],*[v['final_state']for v in recur_frames]],axis=0)
    for i in range(31):
     if not np.array_equal(recur_frames[i]['final_state'],recur_frames[i+1]['initial_state']):raise ValueError('R continuity')
     if not np.array_equal(conv_frames[i]['final_state'],conv_frames[i+1]['initial_state']):raise ValueError('conv continuity')
    for field in ('input','output'):rarrays[prefix+'conv.'+field]=np.concatenate([v[field]for v in conv_frames],axis=2)
    rarrays[prefix+'conv.boundaries']=np.stack([conv_frames[0]['initial_state'],*[v['final_state']for v in conv_frames]],axis=0)
    for field,items in raw_gate_frames.items():rarrays[prefix+'gate_raw.'+field]=np.stack(items)
    if not np.any(rarrays[prefix+'initial_state']):raise ValueError('unexpected all-zero actual initial state')
    checks.append({'case':name,'prefix':128,'start_position':128,'end_position':160,'continuous_steps':32,'R_adjacent_boundaries_exact':31,'conv_adjacent_boundaries_exact':31,'head_to_key':{'0':0,'1':0}})
    print(json.dumps({'case':name,'status':'PASS','continuous_steps':32}),flush=True)
    ctx['name']=None;del out,cache
  for label in ('calibration','prefill','decode'):
   x=chain[label+'.residual']+chain[label+'.down'];y=chain[label+'.sum']
   if not np.array_equal(x,y):raise ValueError('exact residual topology '+label)
  npz(a.out/'consumer-raw.npz',chain);npz(a.out/'state-raw.npz',rarrays);save(a.out/'tokens.json',token_records)
  m.update(status='PASS',loading=loading,chain={'from_layer':3,'to_layer':4,'hidden_size':2560,'K':9216,'next_projection_outputs':16,'next_projection_native_outputs':8192,'norm_epsilon':1e-6,'norm_weight_contract':'effective gamma=1+stored weight','down_bias':False,'next_projection_bias':False,'selection':'cal first8/last8 prefix;eval first4/last4 prefix and all32decode','scope':'full hidden at down/residual/norm; first16 outputs of actual next projection, not full GDN'},state={'layer':0,'value_heads':heads,'key_heads':[0,0],'key_dim':128,'value_dim':128,'conv_channels':512,'native_conv_cache_slots':4,'conv_activation':'silu FP32 native reference','use_qk_l2norm':True,'checks':checks},seconds=time.monotonic()-start)
 except Exception as e:
  m['error']={'type':type(e).__name__,'message':str(e),'traceback':traceback.format_exc()};raise
 finally:
  impl.torch_recurrent_gated_delta_rule=original_recur;impl.causal_conv1d_update=original_conv
  for h in handles:h.remove()
  m['artifacts']={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)}for p in a.out.iterdir()if p.is_file()};save(a.out/'manifest.json',m)
 if m['status']!='PASS':raise RuntimeError('capture failure')
 print(json.dumps({'status':m['status'],'seconds':m['seconds']}),flush=True)
if __name__=='__main__':main()
