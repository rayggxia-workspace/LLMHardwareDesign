"""Bounded long-prefix real state-update inputs, independent FP64 replay."""
import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import torch

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('long_state_reference',HERE.parent/'gpu_state_repair/run.py')
state=importlib.util.module_from_spec(spec);spec.loader.exec_module(state)
common=state.common


def replay(payload):
    q,k,v=(payload[n].double().transpose(1,2) for n in ('query','key','value'))
    q=q*torch.rsqrt((q*q).sum(-1,keepdim=True)+1e-6)/(q.shape[-1]**.5)
    k=k*torch.rsqrt((k*k).sum(-1,keepdim=True)+1e-6)
    g,b=(payload[n].double().transpose(1,2) for n in ('g','beta'))
    s=payload['initial_state'].double().clone();outputs=[]
    for i in range(q.shape[2]):
        s=s*g[:,:,i].exp()[...,None,None]
        prediction=torch.einsum('bhkv,bhk->bhv',s,k[:,:,i])
        correction=(v[:,:,i]-prediction)*b[:,:,i,None]
        s=s+torch.einsum('bhk,bhv->bhkv',k[:,:,i],correction)
        outputs.append(torch.einsum('bhkv,bhk->bhv',s,q[:,:,i]))
    out=torch.stack(outputs,dim=2).transpose(1,2)
    return state.compare(out,payload['output']),state.compare(s,payload['final_state'])


@torch.inference_mode()
def main():
    p=argparse.ArgumentParser();p.add_argument('--model-dir',type=Path);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--replay',type=Path);a=p.parse_args();assert not a.out.exists()
    if a.replay:
        captures=torch.load(a.replay,weights_only=True);checks={n:replay(v) for n,v in captures.items()}
        assert all(e['finite'] and e['relative_l2']<1e-4 for pair in checks.values() for e in pair)
        state.save(a.out,checks);print('FP64 independent replays',len(checks));return
    assert not state.git('status','--porcelain');a.out.mkdir(parents=True)
    manifest=json.loads((a.model_dir/'model-manifest.json').read_text(encoding='utf-8'))
    for n,info in manifest['files'].items():assert state.sha(a.model_dir/n)==info['sha256']
    common.configure_backend();torch.backends.cudnn.allow_tf32=False;torch.set_num_threads(4)
    free=int(subprocess.check_output(['nvidia-smi','--query-gpu=memory.free','--format=csv,noheader,nounits'],text=True).splitlines()[0])
    torch.cuda.set_per_process_memory_fraction(min(11776,free-512)*2**20/torch.cuda.get_device_properties(0).total_memory)
    model,loading=common.load_model(a.model_dir);state.fp32_compute(model)
    tokenizer=common.transformers.AutoTokenizer.from_pretrained(a.model_dir,local_files_only=True)
    cfg=json.loads((HERE.parent/'gpu_model_evidence/experiment.json').read_text(encoding='utf-8'))
    length=len(tokenizer(cfg['long_text'],add_special_tokens=False)['input_ids'])
    ids=torch.tensor([tokenizer(cfg['long_text']*(8225//length+2),add_special_tokens=False)['input_ids'][:8225]],device='cuda')
    from transformers.models.qwen3_5 import modeling_qwen3_5 as impl
    ctx={'end':0,'layer':None};captures={};handles=[];originals={}
    for i,layer in enumerate(model.model.layers):
        if hasattr(layer,'linear_attn'):
            def prehook(m,args,_i=i):ctx['layer']=_i
            handles.append(layer.linear_attn.register_forward_pre_hook(prehook))
    for name in ('torch_chunk_gated_delta_rule','torch_recurrent_gated_delta_rule'):
        original=getattr(impl,name);originals[name]=original
        def wrapped(*args,_original=original,**kwargs):
            result=_original(*args,**kwargs)
            if ctx['layer'] in (0,14,30) and ctx['end'] in (2048,2049,8192,8193):
                head_indices=torch.tensor([0,31],device=args[0].device)
                payload={n:t.index_select(2,head_indices).cpu() for n,t in zip(('query','key','value'),args)}
                payload.update({n:kwargs[n].index_select(2,head_indices).cpu() for n in ('g','beta')})
                payload['initial_state']=kwargs['initial_state'].index_select(1,head_indices).cpu()
                payload['output']=result[0].index_select(2,head_indices).cpu()
                payload['final_state']=result[1].index_select(1,head_indices).cpu()
                captures[f'layer{ctx["layer"]}-end{ctx["end"]}']=payload
            return result
        setattr(impl,name,wrapped)
    try:
        for end in (2048,8192):
            # Separate prefix runs preserve exact final256-token window boundaries.
            cache=None
            for pos in range(0,end,256):
                ctx['end']=pos+256;o=common.call(model,ids[:,pos:pos+256],cache,keep=1);cache=o.past_key_values
            ctx['end']=end+1;o=common.call(model,ids[:,end:end+1],cache,keep=1)
            del o,cache
    finally:
        for n,fn in originals.items():setattr(impl,n,fn)
        for h in handles:h.remove()
    assert len(captures)==12,list(captures)
    torch.save(captures,a.out/'long-state-inputs.pt')
    del model;torch.cuda.empty_cache()
    checks={n:replay(v) for n,v in captures.items()}
    assert all(e['finite'] and e['relative_l2']<1e-4 for pair in checks.values() for e in pair),checks
    state.save(a.out/'checks.json',checks);state.save(a.out/'inputs.json',ids.tolist())
    state.save(a.out/'manifest.json',{'source_commit':state.git('rev-parse','HEAD'),'model':manifest,
        'boundary':'Before FP32 QK L2 normalization and q/sqrt(d), post convolution/sigmoid/log-decay; selected heads independent in this update',
        'layers':[0,14,30],'head_indices':[0,31],'prefill_window':256,'endpoints':[2048,2049,8192,8193],
        'compute':'FP32; checkpoint storage FP16; efficient SDPA; no offload','performance_eligible':False,
        'source_files':{str(p.relative_to(HERE.parent)):state.sha(p) for d in (HERE,HERE.parent/'gpu_state_repair',HERE.parent/'gpu_model_repair',HERE.parent/'gpu_model_evidence') for p in d.glob('*.py')}})
    state.save(a.out/'artifact-index.json',{p.name:{'bytes':p.stat().st_size,'sha256':state.sha(p)} for p in a.out.iterdir() if p.is_file()})
    print('captured/replayed',len(captures),'selected long-prefix states')

if __name__=='__main__':main()
