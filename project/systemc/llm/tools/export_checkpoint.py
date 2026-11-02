#!/usr/bin/env python3
"""只读既有真实检查点；离线量化权重，并独立生成FP32逐token参考。
训练权重和PyTorch参考只作为输入/真值，不参与C++积木运行时的点积。
"""
import argparse,hashlib,json,math,os,pathlib,time
os.environ.setdefault('PYTHONDONTWRITEBYTECODE','1')
os.environ.setdefault('HF_HUB_OFFLINE','1')
os.environ.setdefault('TRANSFORMERS_OFFLINE','1')
import numpy as np
import torch
from safetensors import safe_open
from transformers import AutoConfig,AutoTokenizer,AutoModelForCausalLM

def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for chunk in iter(lambda:f.read(8*1024*1024),b''):h.update(chunk)
    return h.hexdigest()

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--model',required=True);ap.add_argument('--out',required=True);ap.add_argument('--prompt',default='The capital of France is');ap.add_argument('--new-tokens',type=int,default=3);a=ap.parse_args()
    torch.set_num_threads(int(os.environ.get('SLURM_CPUS_PER_TASK','8')))
    src=pathlib.Path(a.model);out=pathlib.Path(a.out);out.mkdir(parents=True,exist_ok=False)
    cfg=AutoConfig.from_pretrained(src,local_files_only=True);c=getattr(cfg,'text_config',cfg)
    if c.model_type not in ('qwen3','qwen2','llama','granitemoe'):raise ValueError('Dense exporter family not yet implemented: '+c.model_type)
    paths=sorted(src.glob('*.safetensors'));report={'model_path':str(src),'scope':'real full checkpoint; offline S16 export; independent FP32 cached reference','config':c.to_dict(),'source_files':[],'tensors':[],'torch':torch.__version__,'transformers':__import__('transformers').__version__}
    index=[];offset=0
    with open(out/'weights.bin','wb') as raw:
        for path in paths:
            report['source_files'].append({'path':str(path),'bytes':path.stat().st_size,'sha256':sha(path)})
            with safe_open(str(path),framework='pt',device='cpu') as sf:
                for name in sf.keys():
                    value=sf.get_tensor(name).float().contiguous()
                    if value.ndim not in (1,2) and not(c.model_type=='granitemoe' and value.ndim==3):raise ValueError('Unmapped checkpoint tensor '+name+str(value.shape))
                    peak=float(value.abs().max())
                    # Qwen3的Q/K norm gamma可能超过31.999；不硬塞N的Q5.10端口。
                    # gamma保持动态S16尺度，运行时N先单位gamma归一化，再由E乘真实gamma。
                    exponent=math.ceil(math.log2(peak/16383)) if peak else -14
                    scaled=torch.round(value/math.ldexp(1.0,exponent));clipped=int(((scaled>32767)|(scaled< -32768)).sum())
                    data=scaled.clamp(-32768,32767).to(torch.int16).numpy().astype('<i2',copy=False)
                    rows,cols=(int(value.numel()//value.shape[-1]),int(value.shape[-1])) if value.ndim>=2 else (1,int(value.numel()))
                    raw.write(data.tobytes());index.append((name,rows,cols,exponent,offset));offset+=data.nbytes
                    report['tensors'].append({'name':name,'shape':list(value.shape),'exponent':exponent,'clipped':clipped})
    (out/'weights.index').write_text('\n'.join(' '.join(map(str,row)) for row in index)+'\n')
    head=int(getattr(c,'head_dim',None) or c.hidden_size//c.num_attention_heads)
    rope=getattr(c,'rope_parameters',None) or {}
    if rope.get('rope_type','default')!='default':raise ValueError('Unimplemented RoPE rule '+str(rope))
    theta=rope.get('rope_theta',getattr(c,'rope_theta',None))
    if theta is None:raise ValueError('missing RoPE theta; no silent default')
    md={'family':c.model_type,'hidden':c.hidden_size,'intermediate':c.intermediate_size,'layers':c.num_hidden_layers,'heads':c.num_attention_heads,'kv_heads':c.num_key_value_heads,'head_dim':head,'vocab':c.vocab_size,'eps':c.rms_norm_eps,'theta':theta,'rotary_dim':head,'qk_norm':int(c.model_type=='qwen3'),'tied':int(c.tie_word_embeddings),'new_tokens':a.new_tokens}
    for name,default in [('attention_multiplier',1/math.sqrt(head)),('embedding_multiplier',1),('residual_multiplier',1),('logits_scaling',1),('num_local_experts',0),('num_experts_per_tok',0)]:md[name]=getattr(c,name,default)
    (out/'metadata.txt').write_text('\n'.join(f'{k} {v}' for k,v in md.items())+'\n')
    tokenizer=AutoTokenizer.from_pretrained(src,local_files_only=True)
    prompt=tokenizer.encode(a.prompt,add_special_tokens=False)
    if not prompt:raise ValueError('empty prompt')
    (out/'prompt.txt').write_text(' '.join(map(str,prompt))+'\n')
    print('EXPORT',offset,'bytes',len(index),'tensors',flush=True)
    # 参考执行与量化导出分开。加载FP32原权重，绝不读取weights.bin当作独立真值。
    model=AutoModelForCausalLM.from_pretrained(src,local_files_only=True,dtype=torch.float32,attn_implementation='eager').eval()
    cache=None;generated=[];all_input=[];reference_ids=[];started=time.time()
    with torch.inference_mode(),open(out/'reference_logits.bin','wb') as logits_file,open(out/'reference_hidden.bin','wb') as hidden_file:
        for step in range(len(prompt)+a.new_tokens-1):
            token=prompt[step] if step<len(prompt) else generated[-1];all_input.append(token)
            y=model(input_ids=torch.tensor([[token]]),past_key_values=cache,use_cache=True,output_hidden_states=True)
            cache=y.past_key_values;logits=y.logits[0,-1].float();pred=int(logits.argmax());reference_ids.append(pred)
            logits_file.write(logits.numpy().astype('<f4').tobytes())
            # hidden_states[0]为embedding，各层边界逐项保留；最后一项包含模型末尾RMS。
            for hidden in y.hidden_states:hidden_file.write(hidden[0,-1].float().numpy().astype('<f4').tobytes())
            if step>=len(prompt)-1:generated.append(pred)
            print('REFERENCE',step,token,'->',pred,flush=True)
    report.update({'prompt':a.prompt,'prompt_ids':prompt,'reference_inputs':all_input,'reference_next_ids':reference_ids,'reference_generated':generated,'reference_text':tokenizer.decode(generated),'reference_seconds':time.time()-started,'weights_sha256':sha(out/'weights.bin')})
    (out/'export_receipt.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print('REFERENCE_TEXT',report['reference_text'],flush=True)
if __name__=='__main__':main()
