"""Small native-model cache/mask/GQA adapter checks, not real-checkpoint inference."""
import argparse,hashlib,inspect,json,os,platform,time
from pathlib import Path
import numpy as np
import torch
import transformers
from capture import allowed_mask,compare,digest,save

def one(family):
 if family=='gemma':
  from transformers.models.gemma3 import modeling_gemma3 as impl
  from transformers import Gemma3TextConfig
  cfg=Gemma3TextConfig(vocab_size=128,hidden_size=16,intermediate_size=32,num_attention_heads=2,num_key_value_heads=1,head_dim=8,num_hidden_layers=6,sliding_window=4)
  cls=impl.Gemma3ForCausalLM
 elif family=='phi':
  from transformers.models.phi3 import modeling_phi3 as impl
  from transformers import Phi3Config
  cfg=Phi3Config(vocab_size=128,hidden_size=16,intermediate_size=32,num_attention_heads=2,num_key_value_heads=1,num_hidden_layers=2,max_position_embeddings=128,original_max_position_embeddings=128,pad_token_id=0)
  cls=impl.Phi3ForCausalLM
 elif family=='qwen25':
  from transformers.models.qwen2 import modeling_qwen2 as impl
  from transformers import Qwen2Config
  cfg=Qwen2Config(vocab_size=128,hidden_size=16,intermediate_size=32,num_attention_heads=2,num_key_value_heads=1,num_hidden_layers=2)
  cls=impl.Qwen2ForCausalLM
 else:
  from transformers.models.qwen3_5 import modeling_qwen3_5 as impl
  from transformers import Qwen3_5TextConfig
  cfg=Qwen3_5TextConfig(vocab_size=128,hidden_size=32,intermediate_size=64,num_hidden_layers=4,num_attention_heads=4,num_key_value_heads=2,head_dim=8,linear_key_head_dim=8,linear_value_head_dim=8,linear_num_key_heads=2,linear_num_value_heads=4,linear_conv_kernel_dim=4,layer_types=['linear_attention']*3+['full_attention'],rope_parameters={'rope_type':'default','rope_theta':10000.,'partial_rotary_factor':1.,'mrope_section':[1,1,2]})
  cls=impl.Qwen3_5ForCausalLM
 cfg._attn_implementation='eager';torch.manual_seed(20261023);model=cls(cfg).eval();original=impl.eager_attention_forward;sig=inspect.signature(original);checks=[];end=0
 def observe(module,q,k,v,*args,**kwargs):
  result=original(module,q,k,v,*args,**kwargs);bound=sig.bind(module,q,k,v,*args,**kwargs);bound.apply_defaults()
  mask=bound.arguments.get('attention_mask');qn,kn=q.shape[-2],k.shape[-2];window=getattr(module,'sliding_window',None)
  allowed=allowed_mask(np.arange(end-qn,end),np.arange(end-kn,end),window)
  if mask is None:assert allowed.all()
  else:assert np.array_equal(mask[0,0,:,:kn].numpy()==0,allowed)
  h=q.shape[1]//k.shape[1];qa=q[0,:h].double().numpy();ka=k[0,0].double().numpy();va=v[0,0].double().numpy()
  scores=(qa@ka.T)*float(bound.arguments['scaling']);scores=np.where(allowed[None],scores,-np.inf);scores-=scores.max(-1,keepdims=True)
  p=np.exp(scores);p/=p.sum(-1,keepdims=True);expected=p@va;actual=result[0][0,:,:h].permute(1,0,2).double().numpy()
  assert np.allclose(expected,actual,atol=1e-5,rtol=1e-4)
  checks.append({'layer':module.layer_idx,'q_tokens':qn,'key_tokens':kn,'window':window,'GQA':h,'error':compare(actual,expected)})
  return result
 impl.eager_attention_forward=observe
 try:
  ids=torch.arange(12)[None,:]+1
  with torch.inference_mode():
   end=12;full=model(ids,use_cache=True);ref=full.logits.detach().clone();cache=None;pieces=[]
   for begin,stop in [(0,8),(8,9),(9,10),(10,11),(11,12)]:
    end=stop;out=model(ids[:,begin:stop],past_key_values=cache,use_cache=True);cache=out.past_key_values;pieces.append(out.logits)
   got=torch.cat(pieces,dim=1);error=compare(got.numpy(),ref.numpy());assert torch.allclose(got,ref,atol=1e-5,rtol=1e-4)
   if family=='qwen35':
    for name in ['conv_states','recurrent_states']:
     a=getattr(cache.layers[0],name);b=getattr(full.past_key_values.layers[0],name);assert torch.allclose(a,b,atol=1e-5,rtol=1e-4)
  return {'model':family,'status':'PASS','GQA_checks':checks,'logits':error,'implementation_sha256':digest(inspect.getfile(impl)),'config':cfg.to_dict()}
 finally:impl.eager_attention_forward=original

def main():
 p=argparse.ArgumentParser();p.add_argument('--family',choices=['legacy','modern'],required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 if a.out.exists():raise ValueError('refuse overwrite')
 if int(os.environ.get('SLURM_CPUS_PER_TASK','0'))<4:raise ValueError('allocated Slurm CPUs required')
 torch.set_num_threads(4);torch.set_num_interop_threads(1);start=time.monotonic()
 result={'status':'ERROR','scope':'tiny random native adapter check, not full checkpoint or model quality','torch':torch.__version__,'transformers':transformers.__version__,'host':platform.node(),'cases':[]}
 try:
  for family in (['gemma','phi']if a.family=='legacy'else['qwen25','qwen35']):result['cases'].append(one(family))
  result['status']='PASS'
 except Exception as exc:
  import traceback
  result['error']={'type':type(exc).__name__,'message':str(exc),'traceback':traceback.format_exc()}
 result['seconds']=time.monotonic()-start;save(a.out,result);print(json.dumps({'status':result['status'],'family':a.family,'seconds':result['seconds']}))
 if result['status']!='PASS':raise SystemExit(1)
if __name__=='__main__':main()
