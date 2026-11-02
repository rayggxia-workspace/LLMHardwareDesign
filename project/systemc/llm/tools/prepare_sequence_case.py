"""New multi-token/longer case from immutable quantized weights and original FP32 reference."""
import argparse,json,math,os,shutil,time
from pathlib import Path
os.environ['HF_HUB_OFFLINE']='1';os.environ['TRANSFORMERS_OFFLINE']='1'
import torch
from transformers import AutoTokenizer,AutoModelForCausalLM
from export_checkpoint import sha
from model_support import load_reference

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('checkpoint',type=Path);ap.add_argument('output',type=Path)
    ap.add_argument('--prompt',required=True);ap.add_argument('--new-tokens',type=int,default=8)
    a=ap.parse_args();torch.set_num_threads(1)
    ex=json.loads((a.checkpoint/'export_receipt.json').read_text());family=ex['config']['model_type']
    for row in ex['source_files']:
        p=Path(row['path']);assert p.stat().st_size==row['bytes']and sha(p)==row['sha256'],'original source changed'
    assert sha(a.checkpoint/'weights.bin')==ex['weights_sha256'],'quantized export changed'
    if (a.checkpoint/'weights.scales').exists():assert sha(a.checkpoint/'weights.scales')==ex['weight_scales_sha256']
    if (a.checkpoint/'parameters.scales').exists():assert sha(a.checkpoint/'parameters.scales')==ex['parameter_scales_sha256']
    tok=AutoTokenizer.from_pretrained(ex['model_path'],local_files_only=True)
    prompt=tok.encode(a.prompt,add_special_tokens=False)
    if not prompt or a.new_tokens<1:raise ValueError('empty sequence')
    a.output.mkdir(exist_ok=False)
    if family=='granitemoe':
        model=AutoModelForCausalLM.from_pretrained(ex['model_path'],local_files_only=True,dtype=torch.float32,attn_implementation='eager').eval()
    else:model=load_reference(ex['model_path'])
    md=dict(line.split()for line in (a.checkpoint/'metadata.txt').read_text().splitlines())
    md['new_tokens']=str(a.new_tokens);steps=len(prompt)+a.new_tokens-1
    rows=[line.split()for line in (a.checkpoint/'weights.index').read_text().splitlines()]
    rope_names=[r[0]for r in rows if r[0].startswith('rope.')]
    rope_stats=[]
    if rope_names:
        # A new file retains the previous weight bytes and appends new static
        # position tables. No mutation of old checkpoints or guessed RoPE.
        shutil.copyfile(a.checkpoint/'weights.bin',a.output/'weights.bin')
        offset=(a.output/'weights.bin').stat().st_size;rotary=model.model.rotary_emb
        head=int(md['head_dim']);z=torch.zeros(1,1,head)
        with (a.output/'weights.bin').open('ab')as f:
            for row in rows:
                if row[0]not in rope_names:continue
                layer=int(row[0].split('.')[1]);kind=md.get('layer_type_'+str(layer),'full_attention');table=[]
                for pos in range(steps):
                    ids=torch.tensor([[pos]])
                    if family=='qwen3_5_text':ids=ids.unsqueeze(0).expand(3,-1,-1)
                    with torch.no_grad():
                        cos,sin=rotary(z,ids,kind)if family=='gemma3_text'else rotary(z,ids)
                    cos=cos.reshape(-1,cos.shape[-1])[0];sin=sin.reshape(-1,sin.shape[-1])[0];dim=cos.numel()
                    table.append(torch.cat((cos[:dim//2],sin[:dim//2])))
                value=torch.stack(table).float();peak=float(value.abs().max());e=math.ceil(math.log2(peak/16383))if peak else -14
                q=torch.round(torch.ldexp(value,torch.tensor(-e)))
                if bool(((q< -32768)|(q>32767)).any()):raise ValueError('RoPE clips')
                raw=q.to(torch.int16).numpy().astype('<i2',copy=False).tobytes();f.write(raw)
                row[:]=[row[0],str(steps),str(dim),str(e),str(offset)];offset+=len(raw)
                rope_stats.append(dict(name=row[0],positions=steps,dim=dim,exponent=e,bytes=len(raw)))
                md['rotary_dim_'+str(layer)]=str(dim)
                for tensor in ex['tensors']:
                    if tensor['name']==row[0]:tensor.update(shape=[steps,dim],exponent=e,clipped=0)
    else:(a.output/'weights.bin').symlink_to((a.checkpoint/'weights.bin').resolve())
    if (a.checkpoint/'weights.scales').exists():(a.output/'weights.scales').symlink_to((a.checkpoint/'weights.scales').resolve())
    if (a.checkpoint/'parameters.scales').exists():(a.output/'parameters.scales').symlink_to((a.checkpoint/'parameters.scales').resolve())
    (a.output/'weights.index').write_text('\n'.join(' '.join(r)for r in rows)+'\n')
    (a.output/'metadata.txt').write_text('\n'.join(k+' '+v for k,v in md.items())+'\n')
    (a.output/'prompt.txt').write_text(' '.join(map(str,prompt))+'\n')
    cache=None;inputs=[];predictions=[];generated=[];started=time.time()
    with torch.inference_mode(),(a.output/'reference_logits.bin').open('xb')as lf,(a.output/'reference_hidden.bin').open('xb')as hf:
        for step in range(steps):
            token=prompt[step]if step<len(prompt)else generated[-1];inputs.append(token)
            y=model(input_ids=torch.tensor([[token]]),past_key_values=cache,use_cache=True,output_hidden_states=True)
            cache=y.past_key_values;logits=y.logits[0,-1].float();pred=int(logits.argmax());predictions.append(pred)
            lf.write(logits.numpy().astype('<f4').tobytes())
            for h in y.hidden_states:hf.write(h[0,-1].float().numpy().astype('<f4').tobytes())
            if step>=len(prompt)-1:generated.append(pred)
    ex.pop('reference_reused_from',None)
    ex.update(prompt=a.prompt,prompt_ids=prompt,reference_inputs=inputs,reference_next_ids=predictions,
      reference_generated=generated,reference_text=tok.decode(generated),reference_seconds=time.time()-started,
      weights_sha256=sha(a.output/'weights.bin'),sequence_case_parent=str(a.checkpoint.resolve()),
      sequence_case_parent_receipt_sha256=sha(a.checkpoint/'export_receipt.json'),sequence_case_tool_sha256=sha(Path(__file__)),
      sequence_rope_tables=rope_stats,sequence_new_tokens=a.new_tokens)
    (a.output/'export_receipt.json').write_text(json.dumps(ex,indent=2,ensure_ascii=False)+'\n')
    print('SEQUENCE_REFERENCE',family,len(prompt),'prompt positions',steps,'total',generated,flush=True)
if __name__=='__main__':main()
