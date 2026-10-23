"""Small real grouped-GEMM capture for mainline integer requantization evaluation."""
import argparse
import gc
import importlib.util
import json
from pathlib import Path
import subprocess
import types
import torch

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('grouped_capture_candidate',HERE.parent/'gpu_grouped_repair/run.py')
grouped=importlib.util.module_from_spec(spec);spec.loader.exec_module(grouped)
common=grouped.common


@torch.inference_mode()
def main():
    p=argparse.ArgumentParser();p.add_argument('--model-dir',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();assert not a.out.exists();assert not common.git('status','--porcelain')
    model_manifest=json.loads((a.model_dir/'model-manifest.json').read_text(encoding='utf-8'))
    for name,info in model_manifest['files'].items():assert common.sha(a.model_dir/name)==info['sha256']
    a.out.mkdir(parents=True);common.configure_backend();torch.set_num_threads(4)
    free=int(subprocess.check_output(['nvidia-smi','--query-gpu=memory.free','--format=csv,noheader,nounits'],text=True).splitlines()[0])
    budget=min(9728,free-512);assert budget>0
    torch.cuda.set_per_process_memory_fraction(budget*2**20/torch.cuda.get_device_properties(0).total_memory)
    model,loading=common.load_model(a.model_dir);rows=grouped.install(model,'raw',{})
    tokenizer=common.transformers.AutoTokenizer.from_pretrained(a.model_dir,local_files_only=True)
    cfg=json.loads((HERE.parent/'gpu_model_evidence/experiment.json').read_text(encoding='utf-8'))
    ids=torch.tensor([tokenizer(cfg['long_text']*30,add_special_tokens=False)['input_ids'][:129]],device='cuda')
    q35=model.config.model_type=='qwen3_5_text'
    suffixes=('layers.0.linear_attn.in_proj_qkv','layers.0.linear_attn.in_proj_a','layers.0.mlp.down_proj') if q35 else (
        'layers.0.self_attn.q_proj','layers.0.self_attn.o_proj','layers.0.mlp.down_proj')
    current={};counts={};captures={};original_mm=torch._int_mm
    def integer_mm(a,b):
        acc=original_mm(a,b)
        if current:
            c=current['payload'];g=len(c['groups']);module=current['module']
            x=current['x'][:2,g*128:(g+1)*128].float()
            scale=x.abs().amax(-1,keepdim=True).clamp_min(1e-30)/127
            c['groups'].append({'group':g,'A':a[:min(2,current['x'].shape[0])].cpu(),
                'B':b[:,:4].cpu(),'accumulator':acc[:min(2,current['x'].shape[0]),:4].cpu(),
                'activation_scale':scale.cpu(),'weight_scale':module.wscales[g,:4].cpu()})
        return acc
    for name,module in model.named_modules():
        if not any(name.endswith(s) for s in suffixes):continue
        original=module.forward;counts[name]=0
        def wrapped(self,x,_original=original,_name=name):
            idx=counts[_name];counts[_name]+=1
            take=idx<2
            if take:
                payload={'module':_name,'call':idx,'boundary':'post activation input; INT32 partials before FP32 scale/sum',
                    'input_shape':list(x.shape),'groups':[],'bias':None if self.bias is None else self.bias[:4].cpu()}
                current.update(module=self,x=x.reshape(-1,x.shape[-1]),payload=payload)
            try:result=_original(x)
            finally:current.clear()
            if take:
                payload['output']=result.reshape(-1,result.shape[-1])[:2,:4].cpu()
                captures[f'{_name}/{idx}']=payload
            return result
        module.forward=types.MethodType(wrapped,module)
    try:
        torch._int_mm=integer_mm
        o=common.call(model,ids[:,:128],keep=1);o=common.call(model,ids[:,128:129],o.past_key_values,keep=1)
    finally:torch._int_mm=original_mm
    checks={}
    for name,c in captures.items():
        total=torch.zeros_like(c['output'],dtype=torch.float32)
        for g in c['groups']:
            exact=g['A'].long()@g['B'].long();assert torch.equal(exact,g['accumulator'].long()),name
            total.add_(g['accumulator'].float()*g['activation_scale']*g['weight_scale'])
        if c['bias'] is not None:total+=c['bias'].float()
        error=common.compare(total.half(),c['output']);assert error['max_abs']<=.02,error
        checks[name]={'groups':len(c['groups']),'exact_int64_all_partials':True,'reduction_error':error}
    assert len(captures)==6,(q35,list(captures))
    torch.save(captures,a.out/'grouped-partials.pt')
    common.save(a.out/'checks.json',checks);common.save(a.out/'inputs.json',ids.tolist())
    common.save(a.out/'manifest.json',{'source_commit':common.git('rev-parse','HEAD'),'model':model_manifest,
        'selected':'three layer0 projections, first128-token prefill and one cached token, first2 rows/4 columns, all K128 groups',
        'source_files':{str(p.relative_to(HERE.parent)):common.sha(p) for d in (HERE,HERE.parent/'gpu_grouped_repair',HERE.parent/'gpu_model_repair',HERE.parent/'gpu_model_evidence') for p in d.glob('*.py')},
        'allocator_budget_mib':budget,'offload':False,'performance_eligible':False,
        'formats':{'A':'INT8','W':'INT8','partial_acc':'INT32','scales':'FP32','partial_reduction':'FP32','output':'FP16'}})
    common.save(a.out/'artifact-index.json',{p.name:{'bytes':p.stat().st_size,'sha256':common.sha(p)} for p in a.out.iterdir() if p.is_file()})
    print(json.dumps(checks))

if __name__=='__main__':main()
