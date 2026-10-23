"""Long-context grouped INT8 matrix quality; not a performance benchmark."""
import argparse
import gc
import importlib.util
import json
from pathlib import Path
import subprocess
import traceback
import torch

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('long_grouped_shared',HERE.parent/'gpu_grouped_repair/run.py')
grouped=importlib.util.module_from_spec(spec);spec.loader.exec_module(grouped)
common=grouped.common


@torch.inference_mode()
def main():
    p=argparse.ArgumentParser();p.add_argument('--model-dir',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--reference-dir',type=Path,required=True);p.add_argument('--reference-8192',type=Path)
    p.add_argument('--group-k',type=int,choices=[32,128],required=True);p.add_argument('--lengths',nargs='+',type=int,default=[512,2048,4096,8192])
    p.add_argument('--batched-integer',action='store_true')
    p.add_argument('--fused-integer',action='store_true')
    a=p.parse_args();assert not a.out.exists();assert not common.git('status','--porcelain')
    manifest=json.loads((a.model_dir/'model-manifest.json').read_text(encoding='utf-8'))
    for n,info in manifest['files'].items():assert common.sha(a.model_dir/n)==info['sha256'],n
    native_manifest=json.loads((a.reference_dir/'run-manifest.json').read_text(encoding='utf-8'))
    assert native_manifest['runtime_dtype']=='fp16' and native_manifest['sdpa_backend_enforced']=='efficient'
    assert native_manifest['model']==manifest
    a.out.mkdir(parents=True);common.configure_backend();torch.set_num_threads(4)
    free=int(subprocess.check_output(['nvidia-smi','--query-gpu=memory.free','--format=csv,noheader,nounits'],text=True).splitlines()[0])
    budget=min(11776,free-512);torch.cuda.set_per_process_memory_fraction(budget*2**20/torch.cuda.get_device_properties(0).total_memory)
    source={str(p.relative_to(HERE.parent)):common.sha(p) for d in (HERE,HERE.parent/'gpu_grouped_repair',HERE.parent/'gpu_model_repair',HERE.parent/'gpu_model_evidence',HERE.parent/'gpu_batched_integer') for p in d.glob('*.py')}
    common.save(a.out/'manifest.json',{'source_commit':common.git('rev-parse','HEAD'),'source_files':source,'model':manifest,
        'group_k':a.group_k,'W':'INT8 per-output/K group','A':'INT8 per-token/K group','acc':'INT32 partials',
        'scales_partial_sum':'FP32','output':'FP16','state_nonlinear_attention':'native float',
        'sdpa':'efficient_only_explicit_repeat_kv','offload':False,'performance_eligible':False,
        'allocator_budget_mib':budget,'physical_free_mib_at_start':free,'command':subprocess.list2cmdline(__import__('sys').argv)})
    results={'status':'running','short':[],'long':[],'failures':[]}
    def checkpoint():common.save(a.out/'results.json',results)
    try:
        model,loading=common.load_model(a.model_dir);common.save(a.out/'loading.json',loading)
        if a.batched_integer or a.fused_integer:
            backend_file='fused.py' if a.fused_integer else 'kernel.py'
            spec=importlib.util.spec_from_file_location('long_batched_int8',HERE.parent/'gpu_batched_integer'/backend_file)
            backend=importlib.util.module_from_spec(spec);spec.loader.exec_module(backend)
            matrices=backend.install(model,'raw',{},a.group_k)
            common.save(a.out/'integer-backend.json',model.integer_backend_receipt)
        else:matrices=grouped.install(model,'raw',{},a.group_k)
        common.save(a.out/'matrices.json',matrices)
        ids_data=json.loads((a.reference_dir/'inputs.json').read_text(encoding='utf-8'))['long_token_ids']
        ids=torch.tensor(ids_data,device='cuda');assert ids.shape[1]>=max(a.lengths)+32
        common.save(a.out/'inputs.json',{'teacher_forced':True,'token_ids':ids_data})
        def call(x,cache=None):return common.call(model,x,cache,keep=1)
        full=[]
        for j in range(17):
            o=call(ids[:,:128+j]);full.append(o.logits.cpu())
            if j==16:short_state=common.snapshot(o.past_key_values)
            del o
        for chunk in (128,32):
            cache=None
            for pos in range(0,128,chunk):o=call(ids[:,pos:pos+chunk],cache);cache=o.past_key_values
            errors=[common.compare(o.logits.cpu(),full[0])]
            for j in range(16):
                o=call(ids[:,128+j:129+j],cache);cache=o.past_key_values;errors.append(common.compare(o.logits.cpu(),full[j+1]))
            se=[{'name':n,**common.compare(t.cpu(),short_state[n])} for n,t in common.cache_tensors(cache)]
            results['short'].append({'chunk':chunk,'logits':errors,'states':se,'logits_pass':all(e['finite'] and e['relative_l2']<=.02 and e['max_abs']<=.5 for e in errors),
                'states_pass':all(e['finite'] and e['relative_l2']<=.02 for e in se)})
            checkpoint();del o,cache
        del full,short_state;gc.collect();torch.cuda.empty_cache()
        if not all(row['logits_pass'] and row['states_pass'] for row in results['short']):
            raise ValueError('short INT8 mixed continuation failed; long expansion withheld')
        for length in a.lengths:
            one=None
            for chunk in (length,256):
                gc.collect();torch.cuda.empty_cache()
                try:
                    torch.cuda.reset_peak_memory_stats();cache=None
                    for pos in range(0,length,chunk):o=call(ids[:,pos:min(pos+chunk,length)],cache);cache=o.past_key_values
                    prefill=o.logits.cpu()
                    for j in range(32):o=call(ids[:,length+j:length+j+1],cache);cache=o.past_key_values
                    tail=o.logits.cpu();states=common.snapshot(cache)
                    row={'prefix':length,'decode':32,'chunk':chunk,'cache':common.cache_info(cache),
                        'peak_allocated_bytes':torch.cuda.max_memory_allocated(),'finite':bool(torch.isfinite(tail).all())}
                    native_dir=a.reference_8192 if length==8192 and a.reference_8192 else a.reference_dir
                    native=torch.load(native_dir/f'long-{length}-chunk{chunk}.pt',weights_only=True)
                    native_inputs=json.loads((native_dir/'inputs.json').read_text(encoding='utf-8'))['long_token_ids']
                    assert native_inputs[0][:length+32]==ids_data[0][:length+32]
                    # Distribution-only long diagnostic; dense held-out NLL is measured separately.
                    row['vs_native']={}
                    for name,c,r in [('prefill',prefill,native['prefill_logits']),('decode',tail,native['decode_logits'])]:
                        metric=common.output_metrics(c,r,torch.zeros(c.shape[:-1],dtype=torch.long))
                        for k in ('nll','reference_nll','nll_delta'):metric.pop(k)
                        row['vs_native'][name]=metric
                    row['vs_native_selected_states']=[{'name':n,**common.compare(states[n],t)} for n,t in native['selected_cache'].items()]
                    if chunk==length:one=(prefill,tail,states)
                    elif one:
                        row['vs_one_shot']={'prefill':common.compare(prefill,one[0]),'decode':common.compare(tail,one[1]),
                            'states':[{'name':n,**common.compare(t,one[2][n])} for n,t in states.items()]}
                    results['long'].append(row)
                    torch.save({'prefill_logits':prefill,'decode_logits':tail},a.out/f'long-{length}-chunk{chunk}.pt')
                    del o,cache,states,native
                except Exception as exc:
                    results['failures'].append({'prefix':length,'chunk':chunk,'error':repr(exc),'traceback':traceback.format_exc()});o=None;cache=None
                checkpoint()
            one=None;gc.collect();torch.cuda.empty_cache()
        common.save(a.out/'integer-stats.json',{n:m.stats for n,m in model.named_modules() if hasattr(m,'stats')})
        results['status']='completed_with_failures' if results['failures'] else 'completed';checkpoint()
    except Exception as exc:
        results['status']='failed';results['failures'].append({'error':repr(exc),'traceback':traceback.format_exc()});checkpoint();raise
    finally:
        common.save(a.out/'source-at-end.json',{'files_unchanged':all(common.sha(HERE.parent/n)==digest for n,digest in source.items())})
        common.save(a.out/'artifact-index.json',{p.name:{'bytes':p.stat().st_size,'sha256':common.sha(p)} for p in a.out.iterdir() if p.is_file() and p.name!='artifact-index.json'})

if __name__=='__main__':main()
