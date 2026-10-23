"""Real-weight Qwen repair: disjoint calibration, ablations and actual INT8 matrices.

Auxiliary math remains explicitly floating point; this is not full-integer inference.
"""
import argparse
import gc
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import time
import traceback
import types

import numpy as np
import pyarrow.parquet as pq
import torch
import torch.nn.functional as F
import transformers

HERE=Path(__file__).resolve().parent
_spec=importlib.util.spec_from_file_location('gpu_evidence_protocol',HERE.parent/'gpu_model_evidence/run.py')
_evidence=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(_evidence)
save,sha,git,compare,output_metrics,cache_tensors,cache_info,snapshot=(getattr(_evidence,n) for n in
    ('save','sha','git','compare','output_metrics','cache_tensors','cache_info','snapshot'))


def dataset_tokens(tokenizer,data,cfg):
    manifest=json.loads((data/'manifest.json').read_text(encoding='utf-8'))
    assert manifest['revision']==cfg['revision']
    result={}
    for split in ('train','test'):
        assert sha(data/f'{split}.parquet')==manifest['files'][split]['sha256']
        rows=pq.read_table(data/f'{split}.parquet').column('text').to_pylist()
        nonempty=[i for i,t in enumerate(rows) if t.strip()]
        samples=[]
        for index in np.linspace(0,len(nonempty)-1,cfg['samples_per_split']+2,dtype=int)[1:-1]:
            start=nonempty[index]; end=start; text=''; ids=[]
            while len(ids)<cfg['prediction_tokens']+1:
                assert end<len(rows),'insufficient tail text'
                text+=rows[end]+'\n'; end+=1
                ids=tokenizer(text,add_special_tokens=False)['input_ids']
            samples.append({'start_row':start,'end_row_exclusive':end,
                'token_ids':ids[:cfg['prediction_tokens']+1]})
        result[split]=samples
    return {'dataset':manifest,'sampling':cfg['selection'],'splits':result}


def configure_backend():
    from transformers.integrations import sdpa_attention
    sdpa_attention.use_gqa_in_sdpa=lambda attention_mask,key,value:False
    torch.backends.cuda.enable_flash_sdp(False)
    torch.backends.cuda.enable_mem_efficient_sdp(True)
    torch.backends.cuda.enable_cudnn_sdp(False)
    torch.backends.cuda.enable_math_sdp(False)
    torch.backends.cuda.matmul.allow_tf32=False


def load_model(path):
    from transformers import AutoModelForCausalLM,Qwen3_5ForCausalLM,Qwen3_5TextConfig
    raw=json.loads((path/'config.json').read_text(encoding='utf-8'))
    kw=dict(dtype=torch.float16,device_map={'':'cuda:0'},local_files_only=True,
        trust_remote_code=False,attn_implementation='sdpa',output_loading_info=True)
    if raw['model_type']=='qwen3_5':
        model,info=Qwen3_5ForCausalLM.from_pretrained(path,config=Qwen3_5TextConfig(**raw['text_config']),**kw)
    else: model,info=AutoModelForCausalLM.from_pretrained(path,**kw)
    assert not any(info.get(n) for n in ('missing_keys','mismatched_keys','error_msgs')),info
    assert all(t.device.type=='cuda' for t in model.parameters())
    return model.eval(),info


def call(model,ids,cache=None,keep=0):
    return model(ids,past_key_values=cache,use_cache=True,logits_to_keep=keep)


def calibrate(model,cal,cfg,out):
    values={}; handles=[]
    def hook(name):
        def capture(m,args):
            x=args[0].detach().reshape(-1,args[0].shape[-1]).float()
            maxima=x.abs().amax(0).cpu()
            if name not in values:
                values[name]={'maxima':maxima,'rows':[],'rows_count':0}
            v=values[name]; v['maxima']=torch.maximum(v['maxima'],maxima)
            # Two deterministic positions per calibration sample; 16 samples ->32 rows.
            room=cfg['calibration_rows_per_linear']-v['rows_count']
            if room>0:
                selected=x[torch.tensor([0,x.shape[0]//2],device=x.device)][:room].cpu()
                v['rows'].append(selected); v['rows_count']+=selected.shape[0]
        return capture
    for name,m in model.named_modules():
        if isinstance(m,torch.nn.Linear) and name!='lm_head':
            handles.append(m.register_forward_pre_hook(hook(name)))
    for ids in cal:
        o=call(model,ids[:,:-1],keep=1); assert torch.isfinite(o.logits).all(); del o
    for h in handles:h.remove()
    for v in values.values():v['rows']=torch.cat(v['rows'])
    torch.save(values,out/'calibration.pt')
    records=[]; factors={}
    for name,m in model.named_modules():
        if name not in values:continue
        w=m.weight.detach().float(); x=values[name]['rows'].cuda()
        target=F.linear(x,w); denom=target.square().sum().clamp_min(1e-30)
        act=values[name]['maxima'].cuda().clamp_min(1e-5)
        wmax=w.abs().amax(0).clamp_min(1e-5)
        trials=[]; best=None
        for alpha in cfg['smoothquant_alpha_candidates']:
            s=(act.pow(alpha)/wmax.pow(1-alpha)).clamp(1e-4,1e4)
            sw=w*s; ws=sw.abs().amax(-1,keepdim=True).clamp_min(1e-30)/127
            dw=(sw/ws).round().clamp(-127,127)*ws
            sx=x/s; xs=sx.abs().amax(-1,keepdim=True).clamp_min(1e-30)/127
            dx=(sx/xs).round().clamp(-127,127)*xs
            error=float((F.linear(dx,dw)-target).square().sum()/denom)
            trials.append({'alpha':alpha,'relative_output_mse':error})
            if best is None or error<best[0]:best=(error,alpha,s.cpu())
        factors[name]=best[2]
        records.append({'module':name,'selected_alpha':best[1],'trials':trials,
            'factor_bytes':best[2].numel()*4,'calibration_rows':x.shape[0]})
        del w,x,target,sw,dw,sx,dx
    torch.save(factors,out/'smooth-factors.pt')
    save(out/'calibration-selection.json',records)
    save(out/'calibration-frozen.json',{'freeze_epoch':time.time(),
        'selection_sha256':sha(out/'calibration-selection.json'),
        'factors_sha256':sha(out/'smooth-factors.pt'),'calibration_sha256':sha(out/'calibration.pt'),
        'validation_used':False,'objective':cfg['calibration_objective']})
    del values,factors;gc.collect();torch.cuda.empty_cache()


def install(model,mode,factors):
    records=[]
    for name,m in model.named_modules():
        if not isinstance(m,torch.nn.Linear) or name=='lm_head':continue
        if mode=='a8':
            def forward(self,x):
                xf=x.float();s=xf.abs().amax(-1,keepdim=True).clamp_min(1e-30)/127
                xq=((xf/s).round().clamp(-127,127)*s).to(x.dtype)
                return F.linear(xq,self.weight,self.bias)
            m.forward=types.MethodType(forward,m)
            records.append({'module':name,'mode':'activation_fake_quant_only','weight':'FP16'})
            continue
        w=m.weight.detach().float()
        smooth=factors[name].cuda() if mode=='smooth' else torch.ones(w.shape[1],device='cuda')
        w=w*smooth
        ws=w.abs().amax(-1,keepdim=True).clamp_min(1e-30)/127
        qw=(w/ws).round().clamp(-127,127).to(torch.int8)
        records.append({'module':name,'weight_shape':list(w.shape),'weight_payload_bytes':qw.numel(),
            'weight_scale_bytes':ws.numel()*4,'smoothing_factor_bytes':smooth.numel()*4 if mode=='smooth' else 0,
            'weight_relative_l2':compare(qw.float()*ws,w)['relative_l2'],
            'int32_worst_case_abs_bound':w.shape[1]*127*127})
        if mode=='w8':
            m.weight.copy_((qw.float()*ws).to(m.weight.dtype))
            del w,qw,ws,smooth
            continue
        assert w.shape[1]*127*127<=2147483647
        m.register_buffer('qweight',qw.t().contiguous());m.register_buffer('wscale',ws.flatten())
        m.register_buffer('smooth',smooth);m.register_parameter('weight',None)
        m.stats={'calls':0,'max_abs_acc':0,'saturation_count':0,'overflow_count':0,'activation_scales_logical_bytes':0}
        m.take_sample='layers.0.' in name
        def forward(self,x):
            shape=x.shape;xf=x.reshape(-1,shape[-1]).float()/self.smooth
            scale=xf.abs().amax(-1,keepdim=True).clamp_min(1e-30)/127
            raw=(xf/scale).round();qa=raw.clamp(-127,127).to(torch.int8)
            # CUDA INT8 GEMM requires M>16 on this backend, including decode/test rows.
            pad=(-qa.shape[0])%32
            if pad:qa=F.pad(qa,(0,0,0,pad))
            acc=torch._int_mm(qa.contiguous(),self.qweight)
            self.stats['calls']+=1;self.stats['max_abs_acc']=max(self.stats['max_abs_acc'],int(acc.abs().max()))
            self.stats['saturation_count']+=int((raw.abs()>127).sum())
            self.stats['activation_scales_logical_bytes']+=scale.numel()*4
            if self.take_sample and not hasattr(self,'sample'):
                self.sample={'A':qa[:2].cpu(),'B':self.qweight[:,:4].cpu(),'accumulator':acc[:2,:4].cpu()}
            y=acc[:xf.shape[0]].float()*scale*self.wscale
            if self.bias is not None:y+=self.bias.float()
            return y.to(x.dtype).reshape(*shape[:-1],-1)
        m.forward=types.MethodType(forward,m)
        del w,qw,ws,smooth
    gc.collect();torch.cuda.empty_cache()
    return records


def quality_pass(row,cfg):
    gate=cfg['quality_acceptance']
    return row['finite'] and row['mean_kl']<=gate['mean_kl_max'] and row['nll_delta']<=gate['nll_delta_max'] and row['top1_agreement']>=gate['top1_agreement_min']


@torch.inference_mode()
def main():
    p=argparse.ArgumentParser();p.add_argument('--model-dir',type=Path,required=True)
    p.add_argument('--data-dir',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--mode',choices=['reference','w8','a8','raw','smooth'],required=True)
    p.add_argument('--reference-dir',type=Path);p.add_argument('--vram-budget-mib',type=int,default=9728)
    p.add_argument('--native-compute',choices=['fp16','fp32'],default='fp16')
    p.add_argument('--canonical-causal-aux',action='store_true')
    p.add_argument('--integer-backend',choices=['scalar','batched'],default='scalar')
    p.add_argument('--protocol',type=Path)
    a=p.parse_args()
    if a.out.exists():raise ValueError('output exists')
    assert not git('status','--porcelain'),'clean committed source required'
    protocol_path=a.protocol or HERE/'protocol.json'
    cfg=json.loads(protocol_path.read_text(encoding='utf-8'))
    assert torch.__version__=='2.10.0+cu128' and transformers.__version__=='5.17.0'
    model_manifest=json.loads((a.model_dir/'model-manifest.json').read_text(encoding='utf-8'))
    assert model_manifest['complete']
    for n,info in model_manifest['files'].items():assert sha(a.model_dir/n)==info['sha256'],n
    a.out.mkdir(parents=True)
    smifree=int(subprocess.check_output(['nvidia-smi','--query-gpu=memory.free','--format=csv,noheader,nounits'],text=True).strip().splitlines()[0])
    budget=min(a.vram_budget_mib,smifree-512);assert budget>0
    torch.cuda.set_per_process_memory_fraction(budget*2**20/torch.cuda.get_device_properties(0).total_memory)
    source={p.name:sha(p) for p in HERE.iterdir() if p.is_file()}
    save(a.out/'manifest.json',{'source_commit':git('rev-parse','HEAD'),'source_files':source,
        'model':model_manifest,'protocol':cfg,'command':sys.argv,'mode':a.mode,'runtime_dtype':a.native_compute,
        'canonical_causal_aux':a.canonical_causal_aux,'integer_backend':a.integer_backend,
        'protocol_path':str(protocol_path),'protocol_sha256':sha(protocol_path),
        'sdpa_backend':'efficient_only','gqa':'explicit_repeat_kv','allocator_budget_mib':budget,
        'physical_free_mib':smifree,'offload':False,'observed_run_not_performance':True})
    results={'status':'running','quality':[],'failures':[]}
    try:
        configure_backend();torch.set_num_threads(4);torch.manual_seed(20261023)
        tokenizer=transformers.AutoTokenizer.from_pretrained(a.model_dir,local_files_only=True)
        inputs=dataset_tokens(tokenizer,a.data_dir,cfg);save(a.out/'inputs.json',inputs)
        val=[torch.tensor([s['token_ids']],device='cuda') for s in inputs['splits']['test']]
        cal=[torch.tensor([s['token_ids']],device='cuda') for s in inputs['splits']['train']]
        oldcfg=json.loads((HERE.parent/'gpu_model_evidence/experiment.json').read_text(encoding='utf-8'))
        regression=[]
        for text in oldcfg['validation_texts']:
            ids=tokenizer(text*20,add_special_tokens=False)['input_ids'][:129]
            regression.append(torch.tensor([ids],device='cuda'))
        save(a.out/'regression-inputs.json',[x.tolist() for x in regression])
        model,loading=load_model(a.model_dir);save(a.out/'loading.json',loading)
        if a.native_compute=='fp32':
            spec=importlib.util.spec_from_file_location('quality_fp32_aux',HERE.parent/'gpu_state_repair/run.py')
            aux=importlib.util.module_from_spec(spec);spec.loader.exec_module(aux);aux.fp32_compute(model)
        if a.canonical_causal_aux:
            spec=importlib.util.spec_from_file_location('quality_causal_aux',HERE.parent/'gpu_state_repair/canonical.py')
            aux=importlib.util.module_from_spec(spec);spec.loader.exec_module(aux);aux.install()
        if a.mode=='reference':calibrate(model,cal,cfg,a.out)
        else:
            assert a.reference_dir
            previous=json.loads((a.reference_dir/'manifest.json').read_text(encoding='utf-8'))
            assert previous['model']==model_manifest and previous['protocol']==cfg
            assert previous['runtime_dtype']==a.native_compute and previous['canonical_causal_aux']==a.canonical_causal_aux
            assert (a.reference_dir/'inputs.json').read_bytes()==(a.out/'inputs.json').read_bytes()
            frozen=json.loads((a.reference_dir/'calibration-frozen.json').read_text(encoding='utf-8'))
            assert sha(a.reference_dir/'smooth-factors.pt')==frozen['factors_sha256']
            factors=torch.load(a.reference_dir/'smooth-factors.pt',weights_only=True) if a.mode=='smooth' else {}
            if a.integer_backend=='batched':
                spec=importlib.util.spec_from_file_location('quality_batched_int8',HERE.parent/'gpu_batched_integer/kernel.py')
                backend=importlib.util.module_from_spec(spec);spec.loader.exec_module(backend)
                matrices=backend.install(model,a.mode,factors,cfg['group_k'])
                save(a.out/'integer-backend.json',model.integer_backend_receipt)
            else:matrices=install(model,a.mode,factors)
            save(a.out/'quantized-matrices.json',matrices)
            save(a.out/'calibration-frozen.json',frozen)
        for split,items in [('test',val),('regression',regression)]:
            for i,ids in enumerate(items):
                o=call(model,ids[:,:-1]);logits=o.logits.cpu();del o
                path=f'{split}-{i}.pt';labels=ids[:,1:].cpu()
                if a.mode=='reference':
                    torch.save(logits,a.out/path)
                    row={'finite':bool(torch.isfinite(logits).all()),'nll':float(F.cross_entropy(logits.float().reshape(-1,logits.shape[-1]),labels.flatten()))}
                else:
                    ref=torch.load(a.reference_dir/path,weights_only=True)
                    row=output_metrics(logits,ref,labels);row['pass']=quality_pass(row,cfg)
                    # Small representative outputs only; full errors are streamed.
                    if i==0:torch.save(logits,a.out/path)
                    del ref
                results['quality'].append({'split':split,'sample':i,'predictions':labels.numel(),**row})
                save(a.out/'results.json',results);del logits;gc.collect()
        stats={n:m.stats for n,m in model.named_modules() if hasattr(m,'stats')}
        save(a.out/'integer-stats.json',stats)
        if stats:
            samples={n:m.sample for n,m in model.named_modules() if hasattr(m,'sample')}
            checked={n:bool(torch.equal(s['A'].long()@s['B'].long(),s['accumulator'].long())) for n,s in samples.items()}
            assert all(checked.values());save(a.out/'integer-independent-check.json',checked)
            torch.save(samples,a.out/'integer-samples.pt')
        for split in ('test','regression'):
            rows=[r for r in results['quality'] if r['split']==split]
            aggregate={k:sum(r[k]*r['predictions'] for r in rows)/sum(r['predictions'] for r in rows)
                for k in (['nll'] if a.mode=='reference' else ['mean_kl','nll','reference_nll','nll_delta','top1_agreement'])}
            aggregate['perplexity']=float(np.exp(aggregate['nll']))
            aggregate['predictions']=sum(r['predictions'] for r in rows)
            if a.mode!='reference':aggregate['pass_all_samples']=all(r['pass'] for r in rows)
            results[split+'_aggregate']=aggregate
        results['peak_allocated_bytes']=torch.cuda.max_memory_allocated()
        results['status']='completed';save(a.out/'results.json',results)
    except Exception as exc:
        results['status']='failed';results['failures'].append({'error':repr(exc),'traceback':traceback.format_exc()})
        save(a.out/'results.json',results);raise
    finally:
        save(a.out/'source-at-end.json',{'files_unchanged':source=={p.name:sha(p) for p in HERE.iterdir() if p.is_file()}})
        save(a.out/'artifact-index.json',{p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in a.out.iterdir() if p.is_file() and p.name!='artifact-index.json'})

if __name__=='__main__':main()
