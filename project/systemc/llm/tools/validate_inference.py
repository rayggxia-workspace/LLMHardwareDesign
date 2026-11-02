#!/usr/bin/env python3
"""独立FP32参考对照。输入若已分叉，按SystemC实际prefix重跑参考，不错误比较不同prefix。
只输出数值证据；torch绝不供给SystemC运行时的激活或token预测。
"""
import argparse,json,os,pathlib,struct,hashlib
os.environ.setdefault('HF_HUB_OFFLINE','1')
os.environ.setdefault('TRANSFORMERS_OFFLINE','1')
import numpy as np
import torch
from transformers import AutoModelForCausalLM,AutoTokenizer

def tensors(path):
    data=path.read_bytes();offset=0;values=[]
    while offset<len(data):
        exponent,count=struct.unpack_from('<iI',data,offset);offset+=8
        if exponent == -2147483648:
            exponent=np.frombuffer(data,dtype='<i4',count=count,offset=offset).copy();offset+=4*count
        a=np.frombuffer(data,dtype='<i2',count=count,offset=offset).astype(np.float64);offset+=2*count
        values.append(np.ldexp(a,exponent))
    return values

def metric(a,b):
    a=np.asarray(a,dtype=np.float64);b=np.asarray(b,dtype=np.float64)
    return {'cosine':float(np.dot(a,b)/(np.linalg.norm(a)*np.linalg.norm(b)+1e-30)),
            'relative_l2':float(np.linalg.norm(a-b)/(np.linalg.norm(b)+1e-30)),
            'max_absolute':float(np.max(np.abs(a-b)))}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('checkpoint');ap.add_argument('run');a=ap.parse_args()
    cp=pathlib.Path(a.checkpoint);run=pathlib.Path(a.run)
    export=json.loads((cp/'export_receipt.json').read_text());receipt=json.loads((run/'systemc_receipt.json').read_text())
    logits=tensors(run/'systemc_logits.bin');hidden=tensors(run/'systemc_hidden.bin')
    steps=len(logits);inputs=receipt['inputs'];cfg=export['config'];layers=cfg['num_hidden_layers'];h=cfg['hidden_size'];v=cfg['vocab_size']
    torch.set_num_threads(int(os.environ.get('SLURM_CPUS_PER_TASK','8')))
    same_prefix=inputs==export['reference_inputs'][:steps]
    if same_prefix:
        ref_logits=np.fromfile(cp/'reference_logits.bin',dtype='<f4').reshape(-1,v)[:steps]
        ref_hidden=np.fromfile(cp/'reference_hidden.bin',dtype='<f4').reshape(-1,layers+1,h)[:steps]
    else:
        if cfg['model_type'] in ('phi3','gemma3_text','qwen3_5_text','falcon_h1','llama'):
            from model_support import load_reference
            model=load_reference(export['model_path'])
        else:
            model=AutoModelForCausalLM.from_pretrained(export['model_path'],local_files_only=True,dtype=torch.float32,attn_implementation='eager').eval()
        cache=None;ref_logits=[];ref_hidden=[]
        with torch.inference_mode():
            for token in inputs:
                y=model(input_ids=torch.tensor([[token]]),past_key_values=cache,use_cache=True,output_hidden_states=True);cache=y.past_key_values
                ref_logits.append(y.logits[0,-1].numpy());ref_hidden.append(np.stack([x[0,-1].numpy() for x in y.hidden_states]))
        ref_logits=np.stack(ref_logits);ref_hidden=np.stack(ref_hidden)
    tokenizer=AutoTokenizer.from_pretrained(export['model_path'],local_files_only=True)
    result={'checkpoint':export['model_path'],'reference':'original stored FP32 parameters; eager; actual SystemC input prefix',
            'input_scope':export.get('scope','legacy export: see journal/source provenance'),
            'same_prefix_as_original_greedy_reference':same_prefix,'systemc_generated':receipt['generated'],
            'systemc_text':tokenizer.decode(receipt['generated']),
            'independent_greedy_reference_generated':export['reference_generated'],
            'independent_greedy_reference_text':export['reference_text'],'steps':[],'hashes':{}}
    for step in range(steps):
        pred=int(np.argmax(logits[step]));ref=int(np.argmax(ref_logits[step]));top=np.argsort(ref_logits[step])[-5:][::-1]
        result['steps'].append({'step':step,'input':inputs[step],'systemc_next':pred,'reference_same_prefix_next':ref,
                                'top1_equal':pred==ref,'logits':metric(logits[step],ref_logits[step]),
                                'reference_top5':top.tolist(),'hidden':[metric(hidden[step*(layers+1)+i],ref_hidden[step,i]) for i in range(layers+1)]})
    hash_paths=[cp/'weights.bin',cp/'weights.index',cp/'metadata.txt',cp/'export_receipt.json',run/'systemc_logits.bin',run/'systemc_hidden.bin',run/'systemc_receipt.json']
    if (cp/'weights.scales').exists():hash_paths.append(cp/'weights.scales')
    if (cp/'parameters.scales').exists():hash_paths.append(cp/'parameters.scales')
    for p in hash_paths:
        digest=hashlib.sha256()
        with p.open('rb') as f:
            for block in iter(lambda:f.read(8*1024*1024),b''):digest.update(block)
        result['hashes'][str(p)]=digest.hexdigest()
    (run/'validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('steps','hashes')},ensure_ascii=False),flush=True)
    print('TOP1',sum(x['top1_equal'] for x in result['steps']),'/',steps,flush=True)
    print('LOGIT_COSINE',[x['logits']['cosine'] for x in result['steps']],flush=True)
if __name__=='__main__':main()
