"""Qwen state diagnosis: FP32 compute reference and isolated state round-trip experiments."""
import argparse
import gc
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import traceback
import types
import torch
import torch.nn.functional as F

HERE=Path(__file__).resolve().parent
_spec=importlib.util.spec_from_file_location('qwen_quality_repair',HERE.parent/'gpu_model_repair/run.py')
common=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(common)
save,sha,git,compare,cache_tensors,cache_info,snapshot=(getattr(common,n) for n in
    ('save','sha','git','compare','cache_tensors','cache_info','snapshot'))


def fp32_compute(model):
    """Keep resident large checkpoint weights FP16; cast each current matrix on GPU.

    Activations/accumulation/conv/attention/recurrence are FP32. This preserves the
    loaded checkpoint values and saves storage, without CPU weight offload.
    """
    for module in model.modules():
        if isinstance(module,torch.nn.Linear):
            def forward(self,x):
                return F.linear(x.float(),self.weight.float(),None if self.bias is None else self.bias.float())
            module.forward=types.MethodType(forward,module)
        elif isinstance(module,torch.nn.Embedding):
            def forward(self,x):
                return F.embedding(x,self.weight,self.padding_idx,self.max_norm,self.norm_type,
                    self.scale_grad_by_freq,self.sparse).float()
            module.forward=types.MethodType(forward,module)
        else:
            for p in module.parameters(recurse=False):p.data=p.data.float()


def kind(name):
    if '/keys' in name or '/values' in name:return 'kv'
    return 'conv' if 'conv_states' in name else 'recurrent'


def perturb(cache,state_kind,bits):
    records=[];bound=(1<<(bits-1))-1
    for name,t in cache_tensors(cache):
        if kind(name)!=state_kind or not t.numel():continue
        # KV per-head/token vector; recurrent per-head/key row; conv per-channel.
        scale=t.float().abs().amax(-1,keepdim=True).clamp_min(1e-30)/bound
        raw=(t.float()/scale).round();q=raw.clamp(-bound,bound)
        deq=(q*scale).to(t.dtype)
        records.append({'name':name,'bits':bits,'payload_bytes':t.numel()*(bits//8),
            'scale_bytes':scale.numel()*4,'native_dtype':str(t.dtype),'native_bytes':t.numel()*t.element_size(),
            'saturation_count':int((raw.abs()>bound).sum()),**compare(deq,t)})
        t.copy_(deq)
    return records


def state_compare(cache,reference):
    rows=[]
    for name,t in cache_tensors(cache):
        ref=reference[name]
        rows.append({'name':name,'kind':kind(name),**compare(t.cpu(),ref),
            'reference_norm':float(ref.float().norm()),'elements':ref.numel()})
    return rows


def state_pass(rows):return all(r['finite'] and r['relative_l2']<=.02 for r in rows)
def logits_pass(row):return row['finite'] and row['relative_l2']<=.02 and row['max_abs']<=.5


@torch.inference_mode()
def main():
    p=argparse.ArgumentParser();p.add_argument('--model-dir',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True);p.add_argument('--compute',choices=['fp16','fp32'],default='fp32')
    p.add_argument('--lengths',nargs='*',type=int,default=[512,2048,4096])
    p.add_argument('--perturb-lengths',nargs='*',type=int,default=[128,2048])
    p.add_argument('--vram-budget-mib',type=int,default=11776)
    a=p.parse_args();assert not a.out.exists();assert not git('status','--porcelain')
    manifest=json.loads((a.model_dir/'model-manifest.json').read_text(encoding='utf-8'));assert manifest['complete']
    for n,info in manifest['files'].items():assert sha(a.model_dir/n)==info['sha256'],n
    a.out.mkdir(parents=True)
    free=int(subprocess.check_output(['nvidia-smi','--query-gpu=memory.free','--format=csv,noheader,nounits'],text=True).splitlines()[0])
    budget=min(a.vram_budget_mib,free-512);assert budget>0
    torch.cuda.set_per_process_memory_fraction(budget*2**20/torch.cuda.get_device_properties(0).total_memory)
    common.configure_backend();torch.backends.cudnn.allow_tf32=False;torch.set_num_threads(4)
    source={p.name:sha(p) for p in HERE.iterdir() if p.is_file()}
    save(a.out/'manifest.json',{'source_commit':git('rev-parse','HEAD'),'source_files':source,'model':manifest,
        'command':sys.argv,'weight_storage':'FP16 checkpoint on GPU','compute':a.compute,
        'auxiliary':'native floating point; no integer claim','sdpa':'efficient_only_explicit_repeat_kv',
        'offload':False,'allocator_budget_mib':budget,'physical_free_mib_at_start':free,
        'state_rounding':'isolated kind, symmetric dynamic scale on last axis; fake quant, native update',
        'acceptance':{'logits_max_abs':.5,'logits_relative_l2':.02,'each_state_relative_l2':.02},
        'performance_eligible':False})
    results={'status':'running','continuation':[],'sensitivity':[],'failures':[]}
    def checkpoint():save(a.out/'results.json',results)
    try:
        tokenizer=common.transformers.AutoTokenizer.from_pretrained(a.model_dir,local_files_only=True)
        cfg=json.loads((HERE.parent/'gpu_model_evidence/experiment.json').read_text(encoding='utf-8'))
        n=max([144]+[n+32 for n in a.lengths+a.perturb_lengths])
        base_length=len(tokenizer(cfg['long_text'],add_special_tokens=False)['input_ids'])
        ids=torch.tensor([tokenizer(cfg['long_text']*(n//max(1,base_length)+2),add_special_tokens=False)['input_ids'][:n]],device='cuda')
        assert ids.shape[1]==n;save(a.out/'inputs.json',{'teacher_forced':True,'token_ids':ids.tolist()})
        model,loading=common.load_model(a.model_dir);save(a.out/'loading.json',loading)
        if a.compute=='fp32':fp32_compute(model)
        def call(x,cache=None):return common.call(model,x,cache,keep=1)
        full=[]
        for j in range(17):
            o=call(ids[:,:128+j]);full.append(o.logits.cpu())
            if j==16:reference=snapshot(o.past_key_values)
            del o
        for chunk in (128,32):
            cache=None
            for pos in range(0,128,chunk):o=call(ids[:,pos:pos+chunk],cache);cache=o.past_key_values
            errors=[compare(o.logits.cpu(),full[0])]
            for j in range(16):
                o=call(ids[:,128+j:129+j],cache);cache=o.past_key_values
                errors.append(compare(o.logits.cpu(),full[j+1]))
            states=state_compare(cache,reference)
            results['continuation'].append({'prefix':128,'decode':16,'chunk':chunk,'logits':errors,'states':states,
                'pass':all(logits_pass(e) for e in errors) and state_pass(states),'cache':cache_info(cache)})
            checkpoint();del o,cache
        del reference,full;gc.collect();torch.cuda.empty_cache()
        for length in a.lengths:
            reference=None;reference_logits=None;reference_prefill=None
            for chunk in (length,256):
                try:
                    torch.cuda.reset_peak_memory_stats();cache=None
                    for pos in range(0,length,chunk):o=call(ids[:,pos:min(pos+chunk,length)],cache);cache=o.past_key_values
                    prefill=o.logits.cpu()
                    for j in range(32):o=call(ids[:,length+j:length+j+1],cache);cache=o.past_key_values
                    row={'prefix':length,'decode':32,'chunk':chunk,'peak_allocated_bytes':torch.cuda.max_memory_allocated(),'cache':cache_info(cache)}
                    if chunk==length:
                        reference=snapshot(cache);reference_logits=o.logits.cpu();reference_prefill=prefill
                    elif reference is not None:
                        states=state_compare(cache,reference);le=compare(o.logits.cpu(),reference_logits);pe=compare(prefill,reference_prefill)
                        row.update({'states':states,'decode_logits':le,'prefill_logits':pe,
                            'pass':state_pass(states) and logits_pass(le) and logits_pass(pe)})
                    results['continuation'].append(row);del o,cache
                except Exception as exc:
                    results['failures'].append({'prefix':length,'chunk':chunk,'error':repr(exc),'traceback':traceback.format_exc()})
                    o=None;cache=None
                gc.collect();torch.cuda.empty_cache();checkpoint()
            del reference,reference_logits,reference_prefill
        for length in a.perturb_lengths:
            cache=None
            for pos in range(0,length,256):o=call(ids[:,pos:min(pos+256,length)],cache);cache=o.past_key_values
            baseline=[]
            for j in range(32):o=call(ids[:,length+j:length+j+1],cache);cache=o.past_key_values;baseline.append(o.logits.cpu())
            reference=snapshot(cache);del o,cache
            kinds=sorted({kind(name) for name in reference})
            for state_kind in kinds:
                for bits in (8,16):
                    cache=None;local={};errors=[]
                    for pos in range(0,length,256):
                        o=call(ids[:,pos:min(pos+256,length)],cache);cache=o.past_key_values
                        for r in perturb(cache,state_kind,bits):local[r['name']]=r
                    for j in range(32):
                        o=call(ids[:,length+j:length+j+1],cache);cache=o.past_key_values
                        errors.append(compare(o.logits.cpu(),baseline[j]))
                        for r in perturb(cache,state_kind,bits):
                            old=local[r['name']];r['relative_l2']=max(old['relative_l2'],r['relative_l2']);local[r['name']]=r
                    states=state_compare(cache,reference)
                    results['sensitivity'].append({'prefix':length,'decode':32,'kind':state_kind,'bits':bits,
                        'execution':'fake_quant_native_update','logits':errors,'states':states,'local_roundtrip':list(local.values()),
                        'logits_pass':all(logits_pass(e) for e in errors),'states_pass':state_pass(states)})
                    del o,cache;gc.collect();torch.cuda.empty_cache();checkpoint()
            del baseline,reference
        results['status']='completed_with_failures' if results['failures'] else 'completed';checkpoint()
    except Exception as exc:
        results['status']='failed';results['failures'].append({'error':repr(exc),'traceback':traceback.format_exc()});checkpoint();raise
    finally:
        save(a.out/'source-at-end.json',{'files_unchanged':source=={p.name:sha(p) for p in HERE.iterdir() if p.is_file()}})
        save(a.out/'artifact-index.json',{p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in a.out.iterdir() if p.is_file() and p.name!='artifact-index.json'})

if __name__=='__main__':main()
