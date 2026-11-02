import pathlib,sys,json,struct,math,os
os.environ['HF_HUB_OFFLINE']='1';os.environ['TRANSFORMERS_OFFLINE']='1'
import numpy as np,torch
from safetensors import safe_open
torch.set_num_threads(2)
root=pathlib.Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/systemc-llm-issue153')
cp=root/'phi-r8';run=root/('run-phi-'+sys.argv[1]);layer=30
e=json.loads((cp/'export_receipt.json').read_text());src=pathlib.Path(e['model_path']);prefix='model.layers.%d.'%layer
weights={}
for p in src.glob('*.safetensors'):
 with safe_open(str(p),framework='pt',device='cpu')as f:
  for name in f.keys():
   if name.startswith(prefix):weights[name[len(prefix):]]=f.get_tensor(name).double()
def trace(name):
 b=(run/('stage-'+name+'.bin')).read_bytes();exp,n=struct.unpack_from('<iI',b)
 return torch.from_numpy(np.ldexp(np.frombuffer(b,dtype='<i2',offset=8,count=n).astype('float64'),exp))
raw=np.memmap(cp/'weights.bin',dtype='<i2',mode='r')
qw={}
for line in (cp/'weights.index').read_text().splitlines():
 name,rows,cols,exp,off=line.split()
 if name.startswith(prefix):
  rows,cols,exp,off=map(int,(rows,cols,exp,off))
  qw[name[len(prefix):]]=torch.from_numpy(np.ldexp(raw[off//2:off//2+rows*cols].astype('float64').reshape(rows,cols),exp))
def metric(a,b):
 a=a.flatten();b=b.flatten()
 return dict(cosine=float(torch.dot(a,b)/(a.norm()*b.norm()+1e-30)),relative_l2=float((a-b).norm()/(b.norm()+1e-30)),actual_peak=float(a.abs().max()),reference_peak=float(b.abs().max()))
result={};x=trace('input');nx=trace('inputnorm');res=trace('residual');post=trace('postnorm');gp=trace('gp');up=trace('up');gate=trace('gate')
def compare(name,actual,reference):result[name]=metric(actual,reference)
eps=e['config']['rms_norm_eps']
for tag,w in [('original',weights),('quantized',qw)]:
 compare('inputnorm-'+tag,nx,x/torch.sqrt(x.square().mean()+eps)*w['input_layernorm.weight'].flatten())
 qkv=torch.nn.functional.linear(nx,w['self_attn.qkv_proj.weight'])
 compare('v-'+tag,trace('v'),qkv[-1024:])
 compare('o-'+tag,trace('o'),torch.nn.functional.linear(trace('av'),w['self_attn.o_proj.weight']))
 compare('postnorm-'+tag,post,res/torch.sqrt(res.square().mean()+eps)*w['post_attention_layernorm.weight'].flatten())
 gu=torch.nn.functional.linear(post,w['mlp.gate_up_proj.weight']);g,u=gu.chunk(2)
 compare('gp-'+tag,gp,g);compare('up-'+tag,up,u)
 compare('down-'+tag,trace('down'),torch.nn.functional.linear(trace('product'),w['mlp.down_proj.weight']))
compare('residual-E',res,x+trace('o'))
compare('silu-G-E',gate,torch.nn.functional.silu(gp))
compare('product-E',trace('product'),gate*up)
result['scope']='conditional diagnostic at layer30 step0; each local reference consumes actual SystemC stage input, not full FP32 equivalence'
with (run/'stage-diagnostic.json').open('x')as f:json.dump(result,f,indent=2)
print(json.dumps(result,indent=2),flush=True)
