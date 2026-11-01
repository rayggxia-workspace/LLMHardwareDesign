"""Export true text checkpoints, fixed RoPE parameters, and independent FP32 truth."""
import argparse, hashlib, json, math, os, pathlib, time
import numpy as np
import torch
from transformers import AutoTokenizer
from model_support import config_for, load_reference, source_tensors
from export_checkpoint import sha

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--model',required=True);ap.add_argument('--out',required=True)
    ap.add_argument('--prompt',default='Hello');ap.add_argument('--new-tokens',type=int,default=3)
    a=ap.parse_args();torch.set_num_threads(int(os.environ.get('SC_EXPORT_THREADS','4')))
    src=pathlib.Path(a.model);out=pathlib.Path(a.out);out.mkdir(parents=True,exist_ok=False)
    c=config_for(src);family=c.model_type
    if family not in ('phi3','gemma3_text','qwen3_5_text','falcon_h1','llama'):
        raise ValueError('unsupported family '+family)
    tok=AutoTokenizer.from_pretrained(src,local_files_only=True)
    prompt=tok.encode(a.prompt,add_special_tokens=False)
    if not prompt or a.new_tokens<1:raise ValueError('empty run')
    steps=len(prompt)+a.new_tokens-1
    model=load_reference(src)
    head=getattr(c,'head_dim',None) or c.hidden_size//c.num_attention_heads
    md=dict(family=family,hidden=c.hidden_size,intermediate=c.intermediate_size,layers=c.num_hidden_layers,
            heads=c.num_attention_heads,kv_heads=c.num_key_value_heads,head_dim=head,vocab=c.vocab_size,
            eps=c.rms_norm_eps,new_tokens=a.new_tokens,qk_norm=int(family in ('gemma3_text','qwen3_5_text')),
            tied=int(c.tie_word_embeddings),theta=1,rotary_dim=head)
    for key,default in [('attention_multiplier',head**-.5),('embedding_multiplier',1),('residual_multiplier',1),('logits_scaling',1),
                        ('attention_in_multiplier',1),('attention_out_multiplier',1),('ssm_in_multiplier',1),('ssm_out_multiplier',1),
                        ('key_multiplier',1),('lm_head_multiplier',1),('sliding_window',0),('linear_num_key_heads',0),
                        ('linear_num_value_heads',0),('linear_key_head_dim',0),('linear_value_head_dim',0),
                        ('mamba_n_heads',0),('mamba_d_head',0),('mamba_d_state',0),('mamba_n_groups',0),('mamba_d_ssm',0)]:
        md[key]=getattr(c,key,default) or default
    if family=='gemma3_text':
        md['embedding_multiplier']=math.sqrt(c.hidden_size)
        md['attention_multiplier']=c.query_pre_attn_scalar**-.5
    if family=='falcon_h1':md['attention_multiplier']=1
    for i,v in enumerate(getattr(c,'ssm_multipliers',[])):md['ssm_multiplier_'+str(i)]=v
    for i,v in enumerate(getattr(c,'mlp_multipliers',[])):md['mlp_multiplier_'+str(i)]=v
    types=getattr(c,'layer_types',['full_attention']*c.num_hidden_layers)
    for i,t in enumerate(types):md['layer_type_'+str(i)]=t
    report=dict(model_path=str(src),scope='true checkpoint, complete TEXT decoder only; vision/MTP excluded',
                config=c.to_dict(),source_files=[],tensors=[],parameter_preparation=[],
                torch=torch.__version__,transformers=__import__('transformers').__version__)
    for p in sorted(src.glob('*.safetensors')):report['source_files'].append(dict(path=str(p),bytes=p.stat().st_size,sha256=sha(p)))
    index=[];offset=0
    with (out/'weights.bin').open('wb') as f:
        def emit(name,value,note=None):
            nonlocal offset
            value=value.float().contiguous()
            peak=float(value.abs().max());e=math.ceil(math.log2(peak/16383)) if peak else -14
            scaled=torch.round(value/math.ldexp(1.,e))
            if bool(((scaled>32767)|(scaled< -32768)).any()):raise ValueError('export clips '+name)
            raw=scaled.to(torch.int16).numpy().astype('<i2',copy=False).tobytes()
            rows=value.numel()//value.shape[-1] if value.ndim>1 else 1
            index.append((name,rows,value.shape[-1],e,offset));offset+=len(raw);f.write(raw)
            report['tensors'].append(dict(name=name,shape=list(value.shape),exponent=e,clipped=0))
            if note:report['parameter_preparation'].append(dict(name=name,operation=note))
        for original,name,value in source_tensors(src,family):
            # Static parameter transforms are explicit. Runtime norm/matmul never uses FP32 truth.
            note=None
            if family in ('gemma3_text','qwen3_5_text') and name.endswith('norm.weight') and '.linear_attn.norm.' not in name:
                value=value+1;note='effective gamma = 1 + stored gamma'
            if name.endswith('.A_log'):
                emit(name.replace('A_log','A_exp'),value.exp(),'offline exp of static A_log')
                continue
            if '.conv1d.weight' in name:
                value=value.squeeze(1)
            emit(name,value,note)
        # Use exact installed official RoPE construction, not a guessed theta/default.
        rotary=model.model.rotary_emb
        z=torch.zeros(1,1,head)
        for i,t in enumerate(types):
            if t=='linear_attention':continue
            rows=[]
            for pos in range(steps):
                ids=torch.tensor([[pos]])
                if family=='qwen3_5_text':ids=ids.unsqueeze(0).expand(3,-1,-1)
                with torch.no_grad():
                    cos,sin=rotary(z,ids,t) if family=='gemma3_text' else rotary(z,ids)
                cos=cos.reshape(-1,cos.shape[-1])[0];sin=sin.reshape(-1,sin.shape[-1])[0]
                dim=cos.numel();rows.append(torch.cat((cos[:dim//2],sin[:dim//2])))
            emit('rope.'+str(i),torch.stack(rows),'official static cos/sin by text token position; no image/video positions')
            md['rotary_dim_'+str(i)]=dim
    (out/'weights.index').write_text('\n'.join(' '.join(map(str,row)) for row in index)+'\n')
    (out/'metadata.txt').write_text('\n'.join(f'{k} {v}' for k,v in md.items())+'\n')
    (out/'prompt.txt').write_text(' '.join(map(str,prompt))+'\n')
    cache=None;generated=[];inputs=[];preds=[];started=time.time()
    with torch.inference_mode(),(out/'reference_logits.bin').open('wb') as lf,(out/'reference_hidden.bin').open('wb') as hf:
        for step in range(steps):
            token=prompt[step] if step<len(prompt) else generated[-1];inputs.append(token)
            y=model(input_ids=torch.tensor([[token]]),past_key_values=cache,use_cache=True,output_hidden_states=True)
            cache=y.past_key_values;logits=y.logits[0,-1].float();pred=int(logits.argmax());preds.append(pred)
            lf.write(logits.numpy().astype('<f4').tobytes())
            for h in y.hidden_states:hf.write(h[0,-1].float().numpy().astype('<f4').tobytes())
            if step>=len(prompt)-1:generated.append(pred)
            print('REFERENCE',family,step,token,pred,flush=True)
    report.update(prompt=a.prompt,prompt_ids=prompt,reference_inputs=inputs,reference_next_ids=preds,
                  reference_generated=generated,reference_text=tok.decode(generated),reference_seconds=time.time()-started,
                  weights_sha256=sha(out/'weights.bin'),exporter_sha256=sha(__file__))
    (out/'export_receipt.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print('EXPORT_COMPLETE',family,offset,report['reference_text'],flush=True)
if __name__=='__main__':main()
