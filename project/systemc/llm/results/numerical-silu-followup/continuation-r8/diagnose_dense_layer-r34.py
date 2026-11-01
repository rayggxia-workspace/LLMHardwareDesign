"""Same-input first-token dense layer oracle; original/quantized weights are separate.

This runs only in independent validation, never in the SystemC prediction path.
The first-token attention has one V per KV head, repeated across query groups.
"""
import argparse, json, math, pathlib, struct, os
os.environ['HF_HUB_OFFLINE']='1';os.environ['TRANSFORMERS_OFFLINE']='1'
import numpy as np
import torch
from safetensors import safe_open
from model_support import canonical

def metric(a,b):
    a=a.flatten().double();b=b.flatten().double()
    return dict(cosine=float(torch.dot(a,b)/(a.norm()*b.norm()+1e-30)),
                relative_l2=float((a-b).norm()/(b.norm()+1e-30)),
                actual_norm=float(a.norm()),reference_norm=float(b.norm()),
                max_absolute=float((a-b).abs().max()))

def main():
    ap=argparse.ArgumentParser();ap.add_argument('checkpoint');ap.add_argument('run');ap.add_argument('layer',type=int)
    a=ap.parse_args();torch.set_num_threads(1);cp=pathlib.Path(a.checkpoint);run=pathlib.Path(a.run)
    export=json.loads((cp/'export_receipt.json').read_text());cfg=export['config'];family=cfg['model_type'];layer=a.layer
    assert family in ('phi3','qwen2','qwen3','gemma3_text')
    md=dict(line.split()for line in (cp/'metadata.txt').read_text().splitlines());prefix='model.layers.%d.'%layer
    weights={};qweights={};global_weight={};qglobal={}
    for p in sorted(pathlib.Path(export['model_path']).glob('*.safetensors')):
        with safe_open(str(p),framework='pt',device='cpu')as f:
            for original in f.keys():
                name=canonical(original,family)
                if name is None or not(name.startswith(prefix)or name=='model.norm.weight'):continue
                v=f.get_tensor(original).double()
                if family=='gemma3_text'and name.endswith('norm.weight'):v=v+1
                if name.startswith(prefix):weights[name[len(prefix):]]=v
                else:global_weight[name]=v
    raw=np.memmap(cp/'weights.bin',dtype='<i2',mode='r')
    group_scales={}
    if (cp/'weights.scales').exists():
        for line in (cp/'weights.scales').read_text().splitlines():
            name,count,*exps=line.split();assert len(exps)==int(count)
            group_scales[name]=np.array(list(map(int,exps)))
    for line in (cp/'weights.index').read_text().splitlines():
        name,rows,cols,exp,off=line.split()
        if not(name.startswith(prefix)or name=='model.norm.weight'):continue
        rows,cols,exp,off=map(int,(rows,cols,exp,off))
        values=raw[off//2:off//2+rows*cols].astype('float64').reshape(rows,cols)
        exponents=group_scales[name][np.arange(rows)//8,None] if name in group_scales else exp
        v=torch.from_numpy(np.ldexp(values,exponents))
        if rows==1:v=v.flatten()
        if name.startswith(prefix):qweights[name[len(prefix):]]=v
        else:qglobal[name]=v
    def trace(name):
        p=run/('stage-'+name+'.bin');b=p.read_bytes();e,n=struct.unpack_from('<iI',b)
        offset=8
        if e==-2147483648:
            e=np.frombuffer(b,dtype='<i4',offset=offset,count=n).copy();offset+=4*n
        return torch.from_numpy(np.ldexp(np.frombuffer(b,dtype='<i2',offset=offset,count=n).astype('float64'),e))
    h=cfg['hidden_size'];ref=np.memmap(cp/'reference_hidden.bin',dtype='<f4',mode='r').reshape(-1,cfg['num_hidden_layers']+1,h)
    reference_input=torch.from_numpy(ref[0,layer].astype('float64'));reference_output=torch.from_numpy(ref[0,layer+1].astype('float64'))
    eps=cfg['rms_norm_eps'];kv=int(md['kv_heads']);heads=int(md['heads']);dim=int(md['head_dim']);last=layer+1==cfg['num_hidden_layers']
    def norm(x,g):return x/torch.sqrt(x.square().mean()+eps)*g.flatten()
    def linear(x,w,name):
        y=torch.nn.functional.linear(x,w[name+'.weight'])
        return y+w[name+'.bias'].flatten()if name+'.bias'in w else y
    def forward(x,w,global_w,overrides=None):
        stages={};overrides=overrides or {}
        def put(name,y):stages[name]=overrides.get(name,y);return stages[name]
        nx=put('inputnorm',norm(x,w['input_layernorm.weight']))
        v=linear(nx,w,'self_attn.qkv_proj')[-kv*dim:]if family=='phi3'else linear(nx,w,'self_attn.v_proj')
        v=put('v',v);av=put('av',v.reshape(kv,dim).repeat_interleave(heads//kv,0).flatten())
        out=linear(av,w,'self_attn.o_proj')
        if family=='gemma3_text':out=norm(out,w['post_attention_layernorm.weight'])
        out=put('o',out);res=put('residual',x+out)
        post=put('postnorm',norm(res,w['pre_feedforward_layernorm.weight'if family=='gemma3_text'else'post_attention_layernorm.weight']))
        if family=='phi3':gp,up=linear(post,w,'mlp.gate_up_proj').chunk(2)
        else:gp=linear(post,w,'mlp.gate_proj');up=linear(post,w,'mlp.up_proj')
        gp=put('gp',gp);up=put('up',up)
        gate=put('gate',torch.nn.functional.gelu(gp,approximate='tanh')if family=='gemma3_text'else torch.nn.functional.silu(gp))
        product=put('product',gate*up);down=linear(product,w,'mlp.down_proj')
        if family=='gemma3_text':down=norm(down,w['post_feedforward_layernorm.weight'])
        down=put('down',down);y=put('layer-result',res+down)
        if last:y=put('final-post-norm',norm(y,global_w['model.norm.weight']))
        return y,stages
    x=trace('input');result={'scope':'conditional first-token oracle, independent from SystemC runtime','family':family,'layer_index':layer,'last_layer':last,'chains':{}}
    for tag,w,gw in [('original',weights,global_weight),('quantized',qweights,qglobal)]:
        for input_tag,inp in [('reference_input',reference_input),('systemc_input',x)]:
            y,stages=forward(inp,w,gw)
            result['chains'][tag+'_'+input_tag]=metric(y,reference_output)
            if input_tag=='systemc_input':
                result[tag+'_stages_chain']={n:metric(trace(n),v)for n,v in stages.items()if(run/('stage-'+n+'.bin')).exists()}
                result[tag+'_single_stage_injection']={}
                for n in stages:
                    if n in ('layer-result','final-post-norm')or not(run/('stage-'+n+'.bin')).exists():continue
                    yy,_=forward(x,w,gw,{n:trace(n)})
                    result[tag+'_single_stage_injection'][n]=metric(yy,y)
    if (run/'stage-final-pre-norm.bin').exists():
        for tag,gw in [('original',global_weight),('quantized',qglobal)]:
            result['conditional_final_norm_'+tag]=metric(trace('final-post-norm'),norm(trace('final-pre-norm'),gw['model.norm.weight']))
    path=run/'dense-diagnostic.json'
    with path.open('x')as f:json.dump(result,f,indent=2)
    print(json.dumps(result['chains'],indent=2),flush=True)
if __name__=='__main__':main()
