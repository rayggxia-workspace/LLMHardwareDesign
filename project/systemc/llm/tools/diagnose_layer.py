#!/usr/bin/env python3
"""FP32第一层内部hook，对齐真实SystemC首层trace，定位首个错误算子。"""
import pathlib,json,os,sys,numpy as np,torch
from transformers import AutoModelForCausalLM
from validate_inference import tensors,metric
cp=pathlib.Path(sys.argv[1]);run=pathlib.Path(sys.argv[2]);export=json.loads((cp/'export_receipt.json').read_text())
torch.set_num_threads(int(os.environ.get('SLURM_CPUS_PER_TASK','8')))
model=AutoModelForCausalLM.from_pretrained(export['model_path'],local_files_only=True,dtype=torch.float32,attn_implementation='eager').eval()
layer=model.model.layers[0];values={}
def hook(name):
    def record(module,args,y):values[name]=y.detach().flatten().numpy()
    return record
def pre(name):
    def record(module,args):values[name]=args[0].detach().flatten().numpy()
    return record
for key,module in [('inputnorm',layer.input_layernorm),('q',layer.self_attn.q_proj),('k',layer.self_attn.k_proj),('v',layer.self_attn.v_proj),('o',layer.self_attn.o_proj),('postnorm',layer.post_attention_layernorm),('gp',layer.mlp.gate_proj),('up',layer.mlp.up_proj),('down',layer.mlp.down_proj),('layer',layer)]:module.register_forward_hook(hook(key))
layer.self_attn.o_proj.register_forward_pre_hook(pre('av'));layer.post_attention_layernorm.register_forward_pre_hook(pre('residual'));layer.mlp.down_proj.register_forward_pre_hook(pre('product'))
with torch.inference_mode():model(input_ids=torch.tensor([[export['prompt_ids'][0]]]))
values['gate']=values['gp']/(1+np.exp(-values['gp']))
result={}
for name,expected in values.items():
    p=run/('stage-'+name+'.bin')
    if not p.exists():continue
    actual=tensors(p)[0];result[name]=metric(actual,expected)
    print(name,result[name],'norm ratio',np.linalg.norm(actual)/np.linalg.norm(expected),flush=True)
(run/'diagnostic.json').write_text(json.dumps(result,indent=2)+'\n')
