"""Full 3--4B checkpoint weight conversion and measured module calibration.

No smaller model substitution. Weight-only accuracy is reported separately
from native-activation/full-hardware correctness.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path

os.environ['HF_HUB_OFFLINE']='1'
os.environ['TRANSFORMERS_OFFLINE']='1'
import numpy as np
import torch
from transformers import AutoModelForCausalLM

from quantization import quantize


def main():
    p=argparse.ArgumentParser();p.add_argument('checkpoint');p.add_argument('output',type=Path)
    a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(exist_ok=False)
    torch.set_num_threads(int(os.environ.get('SLURM_CPUS_PER_TASK','4')))
    m=AutoModelForCausalLM.from_pretrained(a.checkpoint,local_files_only=True,
        torch_dtype=torch.float32,attn_implementation='eager').eval()
    count=sum(p.numel() for p in m.parameters())
    if not 3_000_000_000<=count<=4_100_000_000:raise ValueError('formal model must have 3--4B parameters')
    samples=[[[1,2]],[[3,4]],[[42,43]]]
    stats={};hooks=[]
    def observe(name,value):
        if not isinstance(value,torch.Tensor) or not value.is_floating_point():return
        if not torch.isfinite(value).all():raise ValueError('nonfinite calibration at '+name)
        maximum=float(value.detach().abs().max())
        row=stats.setdefault(name,{'shape':list(value.shape),'max_abs':0.,'observations':0})
        row['max_abs']=max(row['max_abs'],maximum);row['observations']+=1
    def hook(name):
        def run(module,ins,out):
            for i,v in enumerate(ins):observe(name+':input'+str(i),v)
            if isinstance(out,torch.Tensor):observe(name+':output',out)
        return run
    for name,module in m.named_modules():
        if isinstance(module,torch.nn.Linear) or module.__class__.__name__.endswith(('RMSNorm','SiLU')):
            hooks.append(module.register_forward_hook(hook(name)))
    with torch.no_grad():
        reference=[m(input_ids=torch.tensor(ids),use_cache=False).logits.detach().numpy().copy() for ids in samples]
    for h in hooks:h.remove()
    parameters={};folder=a.output/'weights';folder.mkdir()
    with torch.no_grad():
        for name,param in m.named_parameters():
            maximum=float(param.abs().max()); exponent=math.ceil(math.log2(maximum/32767)) if maximum else 0
            path=folder/(hashlib.sha256(name.encode()).hexdigest()[:24]+'.npy')
            target=np.lib.format.open_memmap(str(path),mode='w+',dtype='<i2',shape=tuple(param.shape))
            source=param.detach().numpy().reshape(-1);dest=target.reshape(-1)
            error=0.;clipped=0;digest=hashlib.sha256()
            for start in range(0,len(source),1<<20):
                end=min(start+(1<<20),len(source))
                q,receipt=quantize(source[start:end],exponent=exponent,lanes=2)
                dest[start:end]=q;digest.update(q.tobytes())
                error=max(error,receipt['max_abs_error']);clipped+=receipt['clipped_elements']
                # Actual dequantized weights are used by the next full-model run.
                source[start:end]=q.astype(np.float32)*math.ldexp(1.,exponent)
            target.flush()
            parameters[name]={'shape':list(param.shape),'format':{'bits':16,'exponent':exponent,'lanes':2},
                'file':str(path),'raw_sha256':digest.hexdigest(),'max_abs_error':error,'clipped_elements':clipped}
            print('WEIGHT',name,exponent,error,flush=True)
    with torch.no_grad():
        actual=[m(input_ids=torch.tensor(ids),use_cache=False).logits.detach().numpy().copy() for ids in samples]
    checks=[]
    for ids,x,y in zip(samples,reference,actual):
        rel=float(np.linalg.norm(y-x)/max(float(np.linalg.norm(x)),1e-30))
        top=bool(np.array_equal(np.argmax(x,axis=-1),np.argmax(y,axis=-1)))
        checks.append({'ids':ids,'relative_l2':rel,'max_abs':float(np.abs(y-x).max()),
            'top1_equal':top,'passed':rel<=.01 and top})
    for v in stats.values():
        v['symmetric_s16_exponent']=math.ceil(math.log2(v['max_abs']/32767)) if v['max_abs'] else 0
        v['exceeds_native_q5_10']=v['max_abs']>32767/1024
    report={'status':'weight_only_accuracy_passed' if all(c['passed'] for c in checks) else 'weight_only_accuracy_failed',
        'parameter_count':count,'checkpoint':a.checkpoint,'samples':checks,'parameters':parameters,'module_calibration':stats,
        'predeclared_weight_only_criterion':'relative L2 <= 0.01 and identical argmax at both positions for all three inputs',
        'scope':'whole 3B forward with actual quantized weights, float activations; not native activation or hardware qualification',
        'torch':torch.__version__,'numpy':np.__version__}
    (a.output/'calibration.json').write_text(json.dumps(report,indent=2)+'\n')
    np.savez(a.output/'logits.npz',**{f'{kind}{i}':x for kind,seq in [('reference',reference),('weight_quantized',actual)] for i,x in enumerate(seq)})
    print(json.dumps({k:v for k,v in report.items() if k not in ('parameters','module_calibration')}),flush=True)


if __name__=='__main__':main()
