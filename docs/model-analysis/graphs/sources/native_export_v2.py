"""Native HF decoder exports. Fresh outputs; isolated environment; CPU Slurm only."""
import argparse, collections, hashlib, importlib, inspect, json, os, pathlib, time, traceback
os.environ.setdefault('PYTHONDONTWRITEBYTECODE','1')
os.environ.setdefault('HF_HUB_OFFLINE','1')
os.environ.setdefault('TRANSFORMERS_OFFLINE','1')
import numpy as np
import torch
from transformers import AutoConfig, LlamaConfig

ROOT61='/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/models/'
ROOT70='/public/home/yuzelu/RuizhiLiang/issue70-moe-hybrid-20261024/models-relay/'
MODELS={
 'qwen25':(ROOT61+'qwen25-3b-5defd279','qwen2','Qwen2DecoderLayer',0),
 'qwen3':('/public/home/yuzelu/RuizhiLiang/issue53-cpu-pilot-20261023/model','qwen3','Qwen3DecoderLayer',0),
 'llama':(None,'llama','LlamaDecoderLayer',0),
 'gemma_local':(ROOT61+'gemma3-4b-093f9f38','gemma3','Gemma3DecoderLayer',0),
 'gemma_global':(ROOT61+'gemma3-4b-093f9f38','gemma3','Gemma3DecoderLayer',5),
 'phi':(ROOT61+'phi4mini-cfbefacb','phi3','Phi3DecoderLayer',0),
 'qwen35_global':(ROOT61+'qwen35-4b-851bf6e8','qwen3_5','Qwen3_5DecoderLayer',3),
 'qwen35_linear':(ROOT61+'qwen35-4b-851bf6e8','qwen3_5','Qwen3_5DecoderLayer',0),
 'granite':(ROOT70+'granite','granitemoe','GraniteMoeDecoderLayer',0),
 'falcon':(ROOT70+'falcon','falcon_h1','FalconH1DecoderLayer',0),
}

def dump(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf-8')
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()

def config_for(name):
 path,mod,cls,idx=MODELS[name]
 if path:
  c=AutoConfig.from_pretrained(path,local_files_only=True)
  c=getattr(c,'text_config',c)
 else:
  c=LlamaConfig(hidden_size=2048,intermediate_size=8192,num_hidden_layers=16,num_attention_heads=32,num_key_value_heads=8,head_dim=64,vocab_size=128256,max_position_embeddings=131072,rope_theta=500000.0,rope_scaling={'factor':32.0,'high_freq_factor':4.0,'low_freq_factor':1.0,'original_max_position_embeddings':8192,'rope_type':'llama3'},tie_word_embeddings=True)
 c._attn_implementation='eager'
 return c

def load_layer_weights(layer,path,idx):
 if path is None:return {'loaded':False,'reason':'No existing Llama checkpoint on this host; exact documented config, seeded parameters.'}
 from safetensors import safe_open
 base=pathlib.Path(path); state={}; files=[]; prefix=None
 for f in sorted(base.glob('*.safetensors')):
  with safe_open(str(f),framework='pt',device='cpu') as sf:
   keys=[k for k in sf.keys() if f'.layers.{idx}.' in k and 'vision' not in k]
   if not keys:continue
   files.append({'path':str(f),'size':f.stat().st_size})
   for k in keys:
    # Strip only the matching decoder prefix; do not import vision tensors.
    marker=f'.layers.{idx}.'; suffix=k.split(marker,1)[1]
    if suffix in state:raise ValueError('Duplicate tensor binding: '+k)
    if suffix in layer.state_dict():state[suffix]=sf.get_tensor(k).float()
    elif suffix=='block_sparse_moe.router.layer.weight':state['block_sparse_moe.router.weight']=sf.get_tensor(k).float()
    elif suffix=='block_sparse_moe.input_linear.weight':
     target=layer.state_dict()['block_sparse_moe.experts.gate_up_proj'];state['block_sparse_moe.experts.gate_up_proj']=sf.get_tensor(k).float().reshape(target.shape)
    elif suffix=='block_sparse_moe.output_linear.weight':
     target=layer.state_dict()['block_sparse_moe.experts.down_proj'];state['block_sparse_moe.experts.down_proj']=sf.get_tensor(k).float().reshape(target.shape)
 missing,unexpected=layer.load_state_dict(state,strict=False)
 if missing or unexpected:raise ValueError(f'Incomplete checkpoint binding: missing={missing}, unexpected={unexpected}')
 return {'loaded':True,'matched_tensors':len(state),'missing':missing,'unexpected':unexpected,'files':files,'tensor_sha256':hashlib.sha256(b''.join(t.contiguous().numpy().tobytes() for _,t in sorted(state.items()))).hexdigest()}

class Wrapped(torch.nn.Module):
 def __init__(self,layer,name):super().__init__();self.layer=layer;self.name=name
 def forward(self,x,mask,cos,sin):
  kw=dict(hidden_states=x,attention_mask=mask,past_key_values=None,use_cache=False,position_embeddings=(cos,sin))
  if self.name.startswith('gemma'):
   kw.pop('position_embeddings');kw['position_embeddings_global']=(cos,sin);kw['position_embeddings_local']=(cos,sin)
  if self.name=='falcon':kw['mamba_attention_mask']=None
  if self.name=='qwen35_linear':kw['attention_mask']=None
  y=self.layer(**kw)
  return y[0] if isinstance(y,tuple) else y

def graph_json(m):
 import onnx
 vi={v.name:v for v in list(m.graph.input)+list(m.graph.output)+list(m.graph.value_info)}
 def shape(n):
  if n not in vi:return None
  return [d.dim_value if d.HasField('dim_value') else d.dim_param or '?' for d in vi[n].type.tensor_type.shape.dim]
 producer={o:f'n{i:05d}' for i,n in enumerate(m.graph.node) for o in n.output}
 nodes=[{'id':f'n{i:05d}','name':n.name,'op':n.op_type,'domain':n.domain,'inputs':list(n.input),'outputs':list(n.output),'shapes':{o:shape(o) for o in n.output},'attributes':{a.name:str(onnx.helper.get_attribute_value(a))[:240] for a in n.attribute if a.name!='value'}} for i,n in enumerate(m.graph.node)]
 edges=[{'source':producer[t],'target':f'n{i:05d}','tensor':t} for i,n in enumerate(m.graph.node) for t in n.input if t in producer]
 return {'nodes':nodes,'edges':edges,'inputs':[{'name':x.name,'shape':shape(x.name)} for x in m.graph.input],'outputs':[{'name':x.name,'shape':shape(x.name)} for x in m.graph.output],'initializer_count':len(m.graph.initializer),'op_histogram':dict(collections.Counter(n.op_type for n in m.graph.node))}

def main():
 a=argparse.ArgumentParser();a.add_argument('--root',type=pathlib.Path,required=True);a.add_argument('--model',choices=MODELS,required=True);args=a.parse_args();out=args.root/args.model;out.mkdir(exist_ok=False,parents=True)
 receipt={'model':args.model,'started':time.time(),'source_sha256':sha(__file__),'status':'started','scope':'Native full decoder layer; actual config and checkpoint tensors where available; B1 S2 FP32 eager prefill; dropout disabled. Not a full-network or cached-state export.'}
 try:
  torch.set_num_threads(int(os.environ.get('SLURM_CPUS_PER_TASK','8')));torch.manual_seed(20261026)
  c=config_for(args.model);dump(out/'config.json',c.to_dict());p,mod,cls,idx=MODELS[args.model]
  impl=importlib.import_module(f'transformers.models.{mod}.modeling_{mod}')
  receipt['implementation_file']=impl.__file__;receipt['implementation_sha256']=sha(impl.__file__);receipt['versions']={'torch':torch.__version__,'transformers':__import__('transformers').__version__}
  layer=getattr(impl,cls)(c,idx).float().eval()
  if args.model=='falcon':
   layer.mamba.register_buffer('mup_vector',impl.compute_mup_vector(c),persistent=False)
   receipt['model_level_setup']='Registered nonpersistent mup_vector using the original FalconH1Model setup function.'
  receipt['weights']=load_layer_weights(layer,p,idx);wrapped=Wrapped(layer,args.model).eval()
  h=c.hidden_size;d=getattr(c,'head_dim',None) or h//c.num_attention_heads;rd=int(d*getattr(c,'partial_rotary_factor',1.0))
  if mod=='qwen3_5':rd=int(d*(getattr(c,'rope_parameters',{}) or {}).get('partial_rotary_factor',getattr(c,'partial_rotary_factor',1.0)))
  x=torch.randn(1,2,h)*0.1;mask=torch.tensor([[[[0.,-1e9],[0.,0.]]]]);phase=torch.randn(1,2,rd);inputs=(x,mask,phase.cos(),phase.sin())
  t=time.time()
  with torch.no_grad():expected=wrapped(*inputs).numpy()
  if not np.isfinite(expected).all():raise ValueError('Native reference contains nonfinite output')
  receipt['native_seconds']=time.time()-t
  restore=None
  if args.model=='qwen35_linear':
   original=impl.torch_chunk_gated_delta_rule
   def recurrent_lowering(*a,chunk_size=64,**kw):return impl.torch_recurrent_gated_delta_rule(*a,**kw)
   impl.torch_chunk_gated_delta_rule=recurrent_lowering
   restore=lambda:setattr(impl,'torch_chunk_gated_delta_rule',original)
   receipt['export_adapter']='Native chunked prefill uses unsupported linalg_solve_triangular; export only replaces delta-rule core with the official token-recurrent equivalent. Native references still use the original chunk algorithm.'
  if args.model=='granite':
   import types
   experts=layer.block_sparse_moe.experts;original=experts.forward
   def gathered_experts(self,hidden_states,top_k_index,top_k_weights):
    gu=self.gate_up_proj[top_k_index];dw=self.down_proj[top_k_index]
    fused=torch.matmul(gu,hidden_states[:,None,:,None]).squeeze(-1)
    gate,up=fused.chunk(2,dim=-1);mid=torch.nn.functional.silu(gate)*up
    result=torch.matmul(dw,mid.unsqueeze(-1)).squeeze(-1)
    return (result*top_k_weights.unsqueeze(-1)).sum(dim=1)
   experts.forward=types.MethodType(gathered_experts,experts)
   restore=lambda:setattr(experts,'forward',original)
   receipt['export_adapter']='Replaced expert Python dispatch with dynamic Gather of all checkpoint expert weights and batched MatMul; TopK indices remain live tensors, not frozen selected branches. Native references use original expert implementation.'
  if restore:
   with torch.no_grad():adapted=wrapped(*inputs).numpy()
   np.testing.assert_allclose(adapted,expected,rtol=3e-4,atol=3e-4);receipt['adapter_native_maxabs']=float(np.max(np.abs(adapted-expected)))
  try:torch.onnx.export(wrapped,inputs,str(out/'raw.onnx'),input_names=['x','mask','cos','sin'],output_names=['y'],opset_version=17,dynamo=False,do_constant_folding=False,export_params=True)
  finally:
   if restore:restore()
  import onnx,onnxruntime as ort,onnxsim
  raw=onnx.load(str(out/'raw.onnx'));onnx.checker.check_model(raw);raw=onnx.shape_inference.infer_shapes(raw)
  dump(out/'raw.graph.json',graph_json(raw));receipt['raw_nodes']=len(raw.graph.node)
  session_options=ort.SessionOptions();session_options.intra_op_num_threads=torch.get_num_threads();session_options.inter_op_num_threads=1
  feed={n:t.numpy() for n,t in zip(['x','mask','cos','sin'],inputs)}
  rs=ort.InferenceSession(str(out/'raw.onnx'),sess_options=session_options,providers=['CPUExecutionProvider']);actual=rs.run(None,{v.name:feed[v.name] for v in rs.get_inputs()})[0]
  np.testing.assert_allclose(actual,expected,rtol=3e-4,atol=3e-4);receipt['raw_native_maxabs']=float(np.max(np.abs(actual-expected)))
  receipt['onnxsim_version']=onnxsim.__version__;sim,ok=onnxsim.simplify(raw,check_n=0);receipt['onnxsim_check']=bool(ok);receipt['onnxsim_check_note']='Internal random execution disabled to respect allocated thread count; explicit ORT checks below use 3 seeds and bounded threads.'
  if not ok:raise ValueError('onnxsim equivalence check returned false')
  onnx.checker.check_model(sim);onnx.save(sim,str(out/'simplified.onnx'));dump(out/'simplified.graph.json',graph_json(onnx.shape_inference.infer_shapes(sim)));receipt['simplified_nodes']=len(sim.graph.node)
  ss=ort.InferenceSession(str(out/'simplified.onnx'),sess_options=session_options,providers=['CPUExecutionProvider']);errors=[]
  for seed in [17,31,73]:
   torch.manual_seed(seed);test=(torch.randn_like(x)*0.1,mask,phase.cos(),phase.sin());tf={n:t.numpy() for n,t in zip(['x','mask','cos','sin'],test)}
   with torch.no_grad():ref=wrapped(*test).numpy()
   r0=rs.run(None,{v.name:tf[v.name] for v in rs.get_inputs()})[0];r1=ss.run(None,{v.name:tf[v.name] for v in ss.get_inputs()})[0]
   np.testing.assert_allclose(r0,ref,rtol=3e-4,atol=3e-4);np.testing.assert_allclose(r1,r0,rtol=1e-5,atol=1e-5);errors.append({'seed':seed,'raw_native_maxabs':float(np.max(np.abs(r0-ref))),'sim_raw_maxabs':float(np.max(np.abs(r1-r0)))})
  receipt['validation']=errors;receipt['status']='pass'
 except Exception as e:
  receipt['status']='failed';receipt['error']=repr(e);receipt['traceback']=traceback.format_exc();print(receipt['traceback'],flush=True)
 finally:
  receipt['finished']=time.time();receipt['artifacts']={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in out.iterdir() if p.is_file()};dump(out/'receipt.json',receipt);print(json.dumps(receipt,ensure_ascii=False),flush=True)

if __name__=='__main__':main()
