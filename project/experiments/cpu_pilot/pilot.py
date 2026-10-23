"""Pinned real-weight CPU pilot; executed inside a bounded Slurm allocation."""
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import statistics
import sys
import time

HERE = Path(__file__).resolve().parent


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda: f.read(8 << 20), b''):
            h.update(b)
    return h.hexdigest()


def save(path, data):
    path = Path(path)
    temporary = path.with_suffix('.partial')
    temporary.write_text(json.dumps(data, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    temporary.replace(path)


def measure(torch, actual, expected, config, dtype):
    actual, expected = actual.float(), expected.float()
    error = actual - expected
    relative = (error.square().mean().sqrt() / expected.square().mean().sqrt().clamp_min(1e-30)).item()
    finite = bool(torch.isfinite(actual).all() and torch.isfinite(expected).all())
    fp32_close = bool(torch.allclose(actual, expected, atol=config['fp32_atol'], rtol=config['fp32_rtol']))
    return {'elements': actual.numel(), 'max_abs': error.abs().max().item(),
            'relative_rmse': relative, 'finite': finite,
            'argmax_agreement': (actual.argmax(-1) == expected.argmax(-1)).float().mean().item(),
            'fp32_close': fp32_close,
            'pilot_gate': finite and (fp32_close if dtype == 'float32' else
                                     relative <= config['bf16_split_relative_rmse_budget'])}


def main():
    import resource
    p = argparse.ArgumentParser()
    p.add_argument('--model-dir', required=True, type=Path)
    p.add_argument('--inputs', required=True, type=Path)
    p.add_argument('--binding', required=True, type=Path)
    p.add_argument('--out', required=True, type=Path)
    p.add_argument('--threads', required=True, type=int)
    p.add_argument('--dtype', required=True, choices=['float32', 'bfloat16'])
    a = p.parse_args()
    if a.out.exists():
        raise ValueError('refusing existing output')
    a.out.mkdir(parents=True)
    c = json.loads((HERE / 'experiment.json').read_text(encoding='utf-8'))
    binding = json.loads(a.binding.read_text(encoding='utf-8'))
    for name, expected in binding['source_files'].items():
        if sha(HERE / name) != expected:
            raise ValueError('source binding ' + name)
    expected_inputs = binding['input_sha256']
    if sha(a.inputs) != expected_inputs:
        raise ValueError('token binding')
    manifest = json.loads((a.model_dir.parent / 'manifest.json').read_text(encoding='utf-8'))
    for name, expected in manifest.items():
        if name.startswith('model/'):
            f = a.model_dir.parent / name
            if f.stat().st_size != expected['bytes'] or sha(f) != expected['sha256']:
                raise ValueError('model hash ' + name)
    if a.threads not in c['threads'] or a.threads > int(os.environ.get('SLURM_CPUS_PER_TASK', '0')):
        raise ValueError('thread allocation')
    affinity = sorted(os.sched_getaffinity(0))
    if len(affinity) < a.threads:
        raise ValueError('affinity smaller than thread count')
    import torch
    import transformers
    from transformers import AutoModelForCausalLM
    from transformers.cache_utils import DynamicCache
    if torch.__version__ != c['torch'] or transformers.__version__ != c['transformers']:
        raise ValueError('framework version')
    torch.set_num_threads(a.threads)
    torch.set_num_interop_threads(1)
    torch.manual_seed(53)
    torch.use_deterministic_algorithms(True)
    tokens = torch.tensor(json.loads(a.inputs.read_text(encoding='utf-8'))['input_ids'], dtype=torch.long)[None]
    start = time.perf_counter()
    model = AutoModelForCausalLM.from_pretrained(a.model_dir, local_files_only=True,
        trust_remote_code=False, dtype=getattr(torch, a.dtype), attn_implementation=c['attention']).eval()
    load_seconds = time.perf_counter() - start
    record = {'schema': c['schema'], 'source': binding, 'command': sys.argv,
        'dtype': a.dtype, 'threads': a.threads, 'hostname': platform.node(),
        'python': sys.version, 'affinity': affinity, 'slurm_job': os.environ.get('SLURM_JOB_ID'),
        'packages': {x: importlib.metadata.version(x) for x in ['torch', 'transformers', 'numpy',
            'safetensors', 'tokenizers', 'huggingface-hub']},
        'torch_config': torch.__config__.show(), 'load_seconds': load_seconds,
        'cpuinfo': Path('/proc/cpuinfo').read_text(), 'scope': c['scope']}
    with torch.inference_mode():
        n, d, chunk = c['correctness_prefix'], c['correctness_suffix'], c['chunk_size']
        full = model(input_ids=tokens[:, :n+d], use_cache=True)
        prefix = model(input_ids=tokens[:, :n], use_cache=True)
        cached = model(input_ids=tokens[:, n:n+d], past_key_values=prefix.past_key_values, use_cache=True)
        record['cached_logits'] = measure(torch, cached.logits, full.logits[:, n:], c, a.dtype)
        cache = DynamicCache(config=model.config)
        chunk_logits = []
        for begin in range(0, n+d, chunk):
            out = model(input_ids=tokens[:, begin:min(begin+chunk, n+d)], past_key_values=cache, use_cache=True)
            cache = out.past_key_values
            chunk_logits.append(out.logits)
        record['chunk_logits'] = measure(torch, torch.cat(chunk_logits, dim=1), full.logits, c, a.dtype)
        record['cache_layers'] = []
        for i in range(model.config.num_hidden_layers):
            fk, fv = full.past_key_values[i]
            ck, cv = cached.past_key_values[i]
            hk, hv = cache[i]
            record['cache_layers'].append({'layer': i, 'shape': list(fk.shape),
                'cached_k': measure(torch, ck, fk, c, a.dtype),
                'cached_v': measure(torch, cv, fv, c, a.dtype),
                'chunk_k': measure(torch, hk, fk, c, a.dtype),
                'chunk_v': measure(torch, hv, fv, c, a.dtype)})
        record['all_semantic_gates'] = (record['cached_logits']['pilot_gate'] and record['chunk_logits']['pilot_gate']
            and all(x[key]['pilot_gate'] for x in record['cache_layers']
                    for key in ('cached_k', 'cached_v', 'chunk_k', 'chunk_v')))
        save(a.out / 'correctness.json', record)
        del full, prefix, cached, cache, chunk_logits, out
        # Uninstrumented timed calls; fixed teacher-forced tokens, not sampled output.
        timings = []
        for length in c['prefill_tokens']:
            for repeat in range(-1, c['repeats']):
                start = time.perf_counter()
                out = model(input_ids=tokens[:, :length], use_cache=True)
                prefill_time = time.perf_counter() - start
                cache = out.past_key_values
                del out
                per_token = []
                for step in range(c['decode_tokens']):
                    start = time.perf_counter()
                    out = model(input_ids=tokens[:, length+step:length+step+1], past_key_values=cache,
                                use_cache=True)
                    cache = out.past_key_values
                    per_token.append(time.perf_counter() - start)
                    del out
                del cache
                if repeat >= 0:
                    timings.append({'prefix_tokens': length, 'repeat': repeat,
                        'prefill_seconds': prefill_time, 'prefill_tokens_per_second': length / prefill_time,
                        'decode_token_seconds': per_token,
                        'decode_tokens_per_second': len(per_token) / sum(per_token)})
        record['timings'] = timings
        record['peak_rss_kib_process_lifetime'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        record['timing_summary'] = {str(length): {
            key: statistics.median(x[key] for x in timings if x['prefix_tokens'] == length)
            for key in ('prefill_seconds', 'prefill_tokens_per_second', 'decode_tokens_per_second')}
            for length in c['prefill_tokens']}
        save(a.out / 'result.json', record)
    print(json.dumps({'dtype': a.dtype, 'threads': a.threads, 'gate': record['all_semantic_gates'],
                      'timings': record['timing_summary']}), flush=True)


if __name__ == '__main__':
    main()
