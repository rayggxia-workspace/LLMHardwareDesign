"""Real-checkpoint quantization screen; NOT the integer N/E/KV RTL pipeline.

Static per-linear activation scales are calibrated on separate prompts. All
nonlinear operations remain floating point. Report quality rather than asserting
that arbitrary INT8 activation quantization is lossless.
"""
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import time
import torch
from transformers import AutoModelForCausalLM,AutoTokenizer


def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(8<<20),b''):h.update(block)
    return h.hexdigest()


def main(checkpoint,out,weight_policy='pow2'):
    assert os.environ.get('SLURM_JOB_ID')
    out.mkdir(exist_ok=False);torch.set_num_threads(4)
    t=time.time()
    tokenizer=AutoTokenizer.from_pretrained(checkpoint,local_files_only=True,trust_remote_code=False)
    model=AutoModelForCausalLM.from_pretrained(checkpoint,local_files_only=True,trust_remote_code=False,
        dtype=torch.float32,attn_implementation='eager').eval()
    assert model.config.hidden_size==2048 and model.config.num_hidden_layers==36
    calibrate=['A language model predicts the next word.','Digital circuits use gates and registers.']
    prompts=['Hello','The capital of France is','A transistor can act as','Explain why the sky looks blue']
    maxima={};handles=[]
    modules={n:m for n,m in model.named_modules() if isinstance(m,torch.nn.Linear)}
    def collect(name):
        def hook(_module,inputs):maxima[name]=max(maxima.get(name,0),float(inputs[0].abs().max()))
        return hook
    for name,m in modules.items():handles.append(m.register_forward_pre_hook(collect(name)))
    with torch.no_grad():
        for text in calibrate:
            ids=tokenizer(text,return_tensors='pt');model(**ids,use_cache=False)
    for h in handles:h.remove()
    ids=[tokenizer(p,return_tensors='pt') for p in prompts]
    def forward():
        with torch.no_grad():return [model(**x,use_cache=False).logits[0,-1].double().clone() for x in ids]
    reference=forward()
    weight_metadata={}
    with torch.no_grad():
        for name,m in modules.items():
            maximum=m.weight.abs().amax(dim=1,keepdim=True).clamp_min(1e-30)
            exponents=torch.ceil(torch.log2(maximum/127))
            scale=torch.pow(2.0,exponents) if weight_policy=='pow2' else maximum/127
            m.weight.copy_(torch.round(m.weight/scale).clamp(-127,127)*scale)
            weight_metadata[name]=dict(channels=m.out_features,K=m.in_features,min_exponent=int(exponents.min()),max_exponent=int(exponents.max()))
    rows=[]
    for bits,policy in ((32,'none'),(8,'calibrated'),(16,'calibrated'),(8,'dynamic'),(16,'dynamic')):
        handles=[]
        if bits!=32:
            for name,m in modules.items():
                bound=max(maxima[name],1e-30)/((1<<(bits-1))-1)
                exponent=int(torch.ceil(torch.log2(torch.tensor(bound))))
                scale=2.0**exponent if weight_policy=='pow2' else bound
                def hook(_module,inputs,scale=scale,bits=bits,policy=policy):
                    x=inputs[0]
                    if policy=='dynamic':
                        maximum=x.abs().amax(dim=-1,keepdim=True).clamp_min(1e-30)
                        scale=torch.pow(2.0,torch.ceil(torch.log2(maximum/((1<<(bits-1))-1)))) if weight_policy=='pow2' else maximum/((1<<(bits-1))-1)
                    q=torch.round(x/scale).clamp(-(1<<(bits-1)),(1<<(bits-1))-1)
                    return (q*scale,)+inputs[1:]
                handles.append(m.register_forward_pre_hook(hook))
        actual=forward()
        for h in handles:h.remove()
        metrics=[]
        for prompt,a,r in zip(prompts,actual,reference):
            metrics.append(dict(prompt=prompt,cosine=float(torch.dot(a,r)/(a.norm()*r.norm())),
                                top1_match=bool(a.argmax()==r.argmax()),reference_top1=int(r.argmax()),candidate_top1=int(a.argmax()),
                                normalized_RMSE=float((a-r).square().mean().sqrt()/r.square().mean().sqrt())))
        rows.append(dict(weight_bits=8,weight_scale_policy=weight_policy,activation_bits=bits,activation_policy=policy,metrics=metrics))
    result=dict(passed=True,scope='real Qwen2.5-3B teacher-forced last-logit quantization screen; floating nonlinear/KV path, no RTL equivalence or perplexity',
                calibration_prompts=calibrate,evaluation_prompts=prompts,rows=rows,weight_metadata=weight_metadata,
                activation_maxima=maxima,seconds=time.time()-t,job=os.environ['SLURM_JOB_ID'],
                versions={p:importlib.metadata.version(p) for p in ('torch','transformers','safetensors')},
                checkpoint_sha256={p.name:digest(p) for p in checkpoint.iterdir() if p.suffix in ('.json','.safetensors')})
    (out/'quality.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(rows=rows,seconds=result['seconds'])),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--checkpoint',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--weight-policy',choices=('pow2','linear'),default='pow2')
    a=p.parse_args();main(a.checkpoint,a.out,a.weight_policy)
