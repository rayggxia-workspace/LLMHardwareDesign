"""Separate observed runs: aggregate actual module/SDPA shapes, never performance data."""
import argparse
from collections import Counter
import gc
import json
from pathlib import Path
import subprocess
import time
import traceback

import torch
from transformers import AutoModelForCausalLM
from run import Observer, OpObserver, cache_info, git, save, sha, HERE


class MemoryObserver(OpObserver):
    def __torch_dispatch__(self, func, types, args=(), kwargs=None):
        before=torch.cuda.memory_allocated()
        torch.cuda.reset_peak_memory_stats()
        result=super().__torch_dispatch__(func,types,args,kwargs)
        self.events[-1]['allocator']={
            'before_allocated_bytes':before,'after_allocated_bytes':torch.cuda.memory_allocated(),
            'peak_during_operator_bytes':torch.cuda.max_memory_allocated(),
            'transient_above_before_bytes':max(0,torch.cuda.max_memory_allocated()-before),
            'scope':'PyTorch allocator only; observer run; CUDA workspace outside allocator not measured'}
        return result


class Aggregate:
    def __init__(self):
        self.count = 0
        self.rows = Counter()

    def __len__(self):
        return self.count

    def append(self, event):
        self.count += 1
        event.pop('event_id')
        self.rows[json.dumps(event, sort_keys=True)] += 1

    def export(self):
        return [dict(json.loads(k), calls=v) for k, v in self.rows.items()]


@torch.inference_mode()
def main():
    p = argparse.ArgumentParser()
    p.add_argument('--reference-dir', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--memory-short',action='store_true')
    a = p.parse_args()
    assert not git('status', '--porcelain'), 'commit source first'
    a.out.mkdir(parents=True)
    source = {x.name: sha(x) for x in HERE.iterdir() if x.is_file()}
    ref = json.loads((a.reference_dir/'run-manifest.json').read_text(encoding='utf-8'))
    directory = Path(ref['command'][ref['command'].index('--model-dir')+1])
    for name, info in ref['model']['files'].items():
        assert sha(directory/name) == info['sha256'], name
    free = int(subprocess.check_output(['nvidia-smi', '--query-gpu=memory.free', '--format=csv,noheader,nounits'], text=True).strip())
    budget = min(9728, free-512)
    torch.cuda.set_per_process_memory_fraction(budget*2**20/torch.cuda.get_device_properties(0).total_memory)
    torch.set_num_threads(4)
    torch.backends.cuda.matmul.allow_tf32 = False
    dtype = torch.float16 if ref['runtime_dtype']=='fp16' else torch.bfloat16
    raw = json.loads((directory/'config.json').read_text(encoding='utf-8'))
    kwargs = dict(dtype=dtype, device_map={'':'cuda:0'}, local_files_only=True,
                  trust_remote_code=False, attn_implementation='sdpa')
    if raw['model_type']=='qwen3_5':
        from transformers import Qwen3_5ForCausalLM, Qwen3_5TextConfig
        model = Qwen3_5ForCausalLM.from_pretrained(directory, config=Qwen3_5TextConfig(**raw['text_config']), **kwargs)
    else:
        model = AutoModelForCausalLM.from_pretrained(directory, **kwargs)
    model.eval()
    assert all(t.device.type=='cuda' for t in model.parameters())
    ids = torch.tensor(json.loads((a.reference_dir/'inputs.json').read_text())['long_token_ids'],device='cuda')
    result = dict(source_commit=git('rev-parse','HEAD'), source_files=source,
                  reference_dir=str(a.reference_dir), reference_manifest_sha256=sha(a.reference_dir/'run-manifest.json'),
                  dtype=str(dtype), backend='sdpa', budget_mib=budget, start_epoch=time.time(),
                  performance_eligible=False, measured_traffic_bytes=None, conditions=[])
    if a.memory_short:
        with MemoryObserver() as obs:
            o=model(ids[:,:128],use_cache=True,logits_to_keep=1)
            o=model(ids[:,128:129],past_key_values=o.past_key_values,use_cache=True,logits_to_keep=1)
        result.update(events=obs.events,cache=cache_info(o.past_key_values),prefix=128,decode=1,
                      files_unchanged=source=={x.name:sha(x) for x in HERE.iterdir() if x.is_file()})
        save(a.out/'observed-short-memory.json',result)
        save(a.out/'artifact-index.json',{'observed-short-memory.json':{
            'bytes':(a.out/'observed-short-memory.json').stat().st_size,
            'sha256':sha(a.out/'observed-short-memory.json')}})
        return
    for length in (512,2048,4096,8192):
        for chunk in (length,256):
            entry = dict(prefix=length,chunk=chunk,decode=32)
            obs = Observer(model)
            obs.events = Aggregate()
            cache = o = None
            torch.cuda.empty_cache(); torch.cuda.reset_peak_memory_stats()
            try:
                with obs:
                    for pos in range(0,length,chunk):
                        o=model(ids[:,pos:min(pos+chunk,length)],past_key_values=cache,use_cache=True,logits_to_keep=1)
                        cache=o.past_key_values
                    entry['prefill_cache']=cache_info(cache)
                    for j in range(32):
                        o=model(ids[:,length+j:length+j+1],past_key_values=cache,use_cache=True,logits_to_keep=1)
                        cache=o.past_key_values
                torch.cuda.synchronize()
                entry.update(status='completed',final_cache=cache_info(cache))
            except Exception as exc:
                entry.update(status='failed',error=repr(exc),traceback=traceback.format_exc())
            entry.update(events=obs.events.export(),event_count=len(obs.events),
                         peak_allocated_bytes=torch.cuda.max_memory_allocated(),peak_reserved_bytes=torch.cuda.max_memory_reserved())
            result['conditions'].append(entry)
            save(a.out/'observed-long.json',result)
            cache=o=obs=None
            gc.collect();torch.cuda.empty_cache()
    result['files_unchanged']=source=={x.name:sha(x) for x in HERE.iterdir() if x.is_file()}
    save(a.out/'observed-long.json',result)
    save(a.out/'artifact-index.json',{'observed-long.json':{'bytes':(a.out/'observed-long.json').stat().st_size,'sha256':sha(a.out/'observed-long.json')}})


if __name__=='__main__':
    main()
