"""Six G table sizes; fixed S32-state/Mid32, model, scales and quality gates."""
import hashlib,json,math,os,sys,time
from pathlib import Path
HERE=Path(__file__).resolve().parent
rank=int(os.environ['SLURM_PROCID']);entries=(2049,1025,513,257,129,65)[rank]
ROOT=HERE/f'case-{rank}-LUT{entries}';ROOT.mkdir(exist_ok=False)
SOURCE=Path('/public/home/yuzelu/project-circuit/issue248-stream-quant-20261110-38/source/project/experiments/stream_quant_synthesis')
sys.path.insert(0,str(SOURCE))
import numpy as np
import torch
from torch_contract import narrow_linear,rne
import closure_numeric as num
torch.set_num_threads(10);torch.set_num_interop_threads(1)
stride=2048//(entries-1);shift=10+(stride.bit_length()-1);step=1<<shift
LUT=torch.tensor(num.G_LUT[::stride],dtype=torch.int64);assert len(LUT)==entries
config=dict(entries=entries,LUT_bits=32,logical_bytes=entries*4,interpolation='integer RNE linear',input_frac=16,output_frac=16,step_raw=step,
 state_bits=32,Mid_bits=32,CPUs=10,job=os.environ['SLURM_JOB_ID'])
(ROOT/'config.json').write_text(json.dumps(config,indent=2)+'\n')
(ROOT/'source-commit.txt').write_bytes((HERE/'source-commit.txt').read_bytes())

def activation(raw,count=entries):
 stride2=2048//(count-1);ss=10+stride2.bit_length()-1;unit=1<<ss
 table=torch.tensor(num.G_LUT[::stride2],dtype=torch.int64)
 off=(raw+(16<<16)).clamp(0,32<<16);idx=off//unit;f=off%unit
 v=table[idx]+rne((table[(idx+1).clamp_max(count-1)]-table[idx])*f,torch.tensor(ss))
 return torch.where(raw<=-(16<<16),torch.zeros_like(v),torch.where(raw>=(16<<16),raw,v))

def scalar(raw,count=entries):
 raw=int(raw)
 if raw<=-(16<<16):return 0
 if raw>=(16<<16):return raw
 stride2=2048//(count-1);ss=10+stride2.bit_length()-1
 i,f=divmod(raw+(16<<16),1<<ss)
 return num.G_LUT[i*stride2]+num.rne((num.G_LUT[(i+1)*stride2]-num.G_LUT[i*stride2])*f,ss)

def G32(gate,up,lut,stats):
 a=gate._closure_raw;b=up._closure_raw;v=activation(a)
 assert (v>=-(1<<31)).all() and (v<(1<<31)).all()
 mid=rne(v*b,torch.tensor(16))
 assert (mid>=-(1<<31)).all() and (mid<(1<<31)).all()
 stats['values']+=a.numel();stats['gate_max_abs']=max(stats['gate_max_abs'],float(gate.abs().max()))
 stats['up_max_abs']=max(stats['up_max_abs'],float(up.abs().max()))
 out=mid.double().div(1<<16).float();out._closure_raw=mid;out._closure_frac=16
 return out

def preflight(payload):
 raw=torch.arange(-(32<<16),(32<<16)+1,16,dtype=torch.int64)
 got=activation(raw)
 assert torch.equal(got[::16],torch.tensor([scalar(x) for x in raw[::16].tolist()]))
 # Boundary neighbours and adversarial rounding points are explicit.
 special=torch.tensor([-(1<<31),-1048577,-1048576,-1048575,-step//2,-1,0,1,step//2,1048575,1048576,1048577,(1<<31)-1])
 assert torch.equal(activation(special),torch.tensor([scalar(x) for x in special.tolist()]))
 x=raw.double()/(1<<16);ref=x/(1+torch.exp(-x))
 err=(got.double()/(1<<16)-ref).abs()
 report=dict(config=config,math_points=raw.numel(),max_abs_math_error=float(err.max()),
  math_RMSE=float(torch.sqrt((err**2).mean())),max_abs_vs_2049=float((got-activation(raw,2049)).abs().max())/(1<<16),FFN=[])
 captures=np.load('/public/home/yuzelu/project-circuit/issue248-narrow-20261110-01/frozen-inputs.npz')
 for layer,batch in ((0,0),(2,0),(17,3),(35,5)):
  raw=torch.from_numpy(captures[f'layer{layer}_batch{batch}'])[None,:]
  def call(raw,role):
   x=raw.double().div(1<<16).float();x._closure_raw=raw;x._closure_frac=16
   node=f'model.layers.{layer}.mlp.{role}_proj'
   return narrow_linear(x,payload[node],None,{},node,32)._closure_raw
  gate,up=call(raw,'gate'),call(raw,'up')
  act=activation(gate)
  assert torch.equal(act.reshape(-1),torch.tensor([scalar(x) for x in gate.reshape(-1).tolist()]))
  mid=rne(act*up,torch.tensor(16));oldmid=rne(activation(gate,2049)*up,torch.tensor(16))
  out=call(mid,'down');base=call(oldmid,'down');delta=(out-base).double()
  report['FFN'].append(dict(layer=layer,batch=batch,outputs=out.numel(),max_abs_error_vs_2049=float(delta.abs().max())/(1<<16),
   relative_L2_vs_2049=float(torch.sqrt((delta**2).sum()/(base.double()**2).sum())),
   exact_fraction=float((out==base).double().mean())))
 report['passed']=True
 (ROOT/'preflight.json').write_text(json.dumps(report,indent=2)+'\n')
 print('PREFLIGHT_PASS',entries,report['max_abs_math_error'],flush=True)

code=(HERE/'quality_base.py').read_text()
anchor="name=f'W8A{bits}-g{group}-G32-head16-S{width}state-Mid32'"
assert code.count(anchor)==1
code=code.replace(anchor,anchor[:-1]+f'-LUT{entries}'+"'",1)
(ROOT/'expanded-quality-source.py').write_text(code)
ns=dict(__name__='small_g_quality',__file__=str(SOURCE/'closure_quality.py'),narrow_linear=narrow_linear,preflight=preflight)
exec(compile(code,str(ROOT/'expanded-quality-source.py'),'exec'),ns)
ns['G32']=G32
print('CONFIG_BEGIN',rank,entries,flush=True)
ns['main'](ROOT)
p=ROOT/'quality/closure-quality.json';r=json.loads(p.read_text());r['G_table']=config
p.write_text(json.dumps(r,indent=2)+'\n')
