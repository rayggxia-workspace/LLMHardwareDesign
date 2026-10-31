#!/usr/bin/env python3
"""真实Qwen3.5首层权重+确定性测试输入，导出R边界与官方递推真值；不是完整模型推理。"""
import pathlib,json,os,struct,hashlib,torch,numpy as np
from safetensors import safe_open
from transformers import AutoConfig
from transformers.models.qwen3_5 import modeling_qwen3_5 as impl
torch.set_num_threads(int(os.environ.get('SLURM_CPUS_PER_TASK','8')));torch.manual_seed(153)
root=pathlib.Path(os.environ['ROOT']);out=root/'gdn-boundary-r2';out.mkdir(exist_ok=False)
source=pathlib.Path('/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/models/qwen35-4b-851bf6e8')
config=AutoConfig.from_pretrained(source,local_files_only=True).text_config
module=impl.Qwen3_5GatedDeltaNet(config,0).float().eval();weights={}
prefix='model.language_model.layers.0.linear_attn.'
for path in sorted(source.glob('*.safetensors')):
    with safe_open(str(path),framework='pt',device='cpu') as f:
        for key in f.keys():
            if key.startswith(prefix):weights[key[len(prefix):]]=f.get_tensor(key).float()
module.load_state_dict(weights,strict=True)
captured={};original=impl.torch_chunk_gated_delta_rule
def capture(query,key,value,g,beta,**kwargs):
    captured.update(q=query.detach(),k=key.detach(),v=value.detach(),g=g.detach(),beta=beta.detach())
    return original(query,key,value,g,beta,**kwargs)
impl.torch_chunk_gated_delta_rule=capture
with torch.inference_mode():module(torch.randn(1,4,config.hidden_size)*0.1)
impl.torch_chunk_gated_delta_rule=original
q,k,v,g,beta=(captured[x] for x in ('q','k','v','g','beta'))
with torch.inference_mode():
    expected,state=impl.torch_recurrent_gated_delta_rule(q,k,v,g,beta,output_final_state=True,use_qk_l2norm_in_kernel=True)
    chunk,_=original(q,k,v,g,beta,output_final_state=True,use_qk_l2norm_in_kernel=True)
q=impl.l2norm(q,dim=-1,eps=1e-6)/(q.shape[-1]**0.5);k=impl.l2norm(k,dim=-1,eps=1e-6)
steps,heads,dim,value_dim=v.shape[1],v.shape[2],k.shape[-1],v.shape[-1];exponent=-24
def enc(t,scale,dtype):
    raw=torch.round(t*scale).numpy();info=np.iinfo(dtype)
    if np.any(raw<info.min) or np.any(raw>info.max):raise ValueError('R boundary clipping')
    return raw.astype(dtype).tobytes()
with (out/'inputs.bin').open('wb') as f:
    f.write(struct.pack('<IIIIIi',0x47444e31,steps,heads,dim,value_dim,exponent))
    for step in range(steps):
        for head in range(heads):
            f.write(enc(q[0,step,head],16384,'<i2'));f.write(enc(k[0,step,head],16384,'<i2'))
            f.write(enc(v[0,step,head],2**-exponent,'<i4'))
            f.write(enc(g[0,step,head].exp(),2**31,'<u4'));f.write(enc(beta[0,step,head],2**31,'<u4'))
expected.numpy().astype('<f4').tofile(out/'reference_output.bin');state.numpy().astype('<f4').tofile(out/'reference_state.bin')
receipt={'scope':'real checkpoint layer0 GDN inputs; seeded hidden test stimulus; R core only, NOT full Qwen3.5 inference',
         'source':str(source),'seed':153,'steps':steps,'heads':heads,'key_dim':dim,'value_dim':value_dim,'state_exponent':exponent,
         'official_chunk_recurrent_maxabs':float((chunk-expected).abs().max()),
         'weight_sha256':hashlib.sha256(b''.join(t.contiguous().numpy().tobytes() for _,t in sorted(weights.items()))).hexdigest(),
         'implementation_sha256':hashlib.sha256(pathlib.Path(impl.__file__).read_bytes()).hexdigest(),
         'torch':torch.__version__,'transformers':__import__('transformers').__version__}
(out/'export_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt),flush=True)
