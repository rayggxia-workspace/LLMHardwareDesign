"""Pinned GPU evidence. Native, integer-matrix mixed, and state fake-quant are distinct."""
import argparse
from contextlib import contextmanager
import csv
import gc
import hashlib
import inspect
import json
from pathlib import Path
import subprocess
import sys
import time
import traceback
import types
import weakref
from collections import Counter

import torch
import torch.nn.functional as F
import transformers
from torch.utils._python_dispatch import TorchDispatchMode
from torch.utils._pytree import tree_flatten
from transformers import AutoTokenizer, AutoModelForCausalLM

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def save(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + '\n', encoding='utf-8')


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda: f.read(8 << 20), b''):
            h.update(b)
    return h.hexdigest()


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, text=True).strip()


def record(t):
    return {'shape': list(t.shape), 'dtype': str(t.dtype), 'logical_bytes': t.numel()*t.element_size(),
            'storage_bytes': t.untyped_storage().nbytes(), 'stride': list(t.stride())}


def compare(a, b):
    a, b = a.float(), b.float()
    finite = bool(torch.isfinite(a).all() and torch.isfinite(b).all())
    if not finite:
        return {'finite': False, 'max_abs': None, 'relative_l2': None}
    return {'finite': True, 'max_abs': float((a-b).abs().max()),
            'relative_l2': float((a-b).norm()/b.norm().clamp_min(1e-30))}


def cache_tensors(cache):
    if cache is None:
        return
    for i, layer in enumerate(cache.layers):
        for attr in ('keys', 'values', 'conv_states', 'recurrent_states'):
            v = getattr(layer, attr, None)
            if isinstance(v, torch.Tensor):
                yield f'{i}/{attr}', v
            elif isinstance(v, (tuple, list)):
                for j, t in enumerate(v):
                    if isinstance(t, torch.Tensor):
                        yield f'{i}/{attr}/{j}', t


def snapshot(cache):
    return {n: t.detach().cpu().clone() for n, t in cache_tensors(cache)}


def cache_info(cache):
    rows = {n: record(t) for n, t in cache_tensors(cache)}
    unique = {t.untyped_storage().data_ptr(): t.untyped_storage().nbytes() for _, t in cache_tensors(cache)}
    return {'tensors': rows, 'logical_bytes': sum(x['logical_bytes'] for x in rows.values()),
            'unique_storage_bytes': sum(unique.values()), 'measured_traffic_bytes': None}


def fake_state(cache, bits):
    metrics = []
    for n, t in cache_tensors(cache):
        if not t.numel():
            continue
        bound = (1 << (bits-1))-1
        axes = tuple(range(max(0, t.ndim-2), t.ndim))
        s = t.float().abs().amax(axes, keepdim=True).clamp_min(1e-30)/bound
        q = torch.round(t.float()/s).clamp(-bound, bound)
        deq = (q*s).to(t.dtype)
        metrics.append({'name': n, 'bits': bits, 'scale_bytes': s.numel()*4,
                        'quantized_payload_bytes': t.numel()*(bits//8), **compare(deq, t)})
        t.copy_(deq)
    return metrics


def output_metrics(candidate, reference, labels):
    c, r = candidate.float(), reference.float()
    lp, lq = F.log_softmax(r, -1), F.log_softmax(c, -1)
    kl = (lp.exp()*(lp-lq)).sum(-1).mean()
    cnll = F.cross_entropy(c.reshape(-1, c.shape[-1]), labels.reshape(-1))
    rnll = F.cross_entropy(r.reshape(-1, r.shape[-1]), labels.reshape(-1))
    return {**compare(c, r), 'mean_kl': float(kl), 'nll': float(cnll), 'reference_nll': float(rnll),
            'nll_delta': float(cnll-rnll), 'top1_agreement': float((c.argmax(-1)==r.argmax(-1)).float().mean())}


class Observer:
    """Ordered module interfaces; no inferred claim of physical bus traffic."""
    def __init__(self, model):
        self.model = model
        self.events = []
        self.handles = []

    def __enter__(self):
        from transformers.modeling_utils import ALL_ATTENTION_FUNCTIONS
        self.attention_registry = ALL_ATTENTION_FUNCTIONS
        self.original_sdpa = ALL_ATTENTION_FUNCTIONS['sdpa']
        def sdpa(module, query, key, value, *args, **kwargs):
            out = self.original_sdpa(module, query, key, value, *args, **kwargs)
            self.events.append({'event_id':len(self.events),'module':f'attention/{module.layer_idx}/sdpa',
                'class':'sdpa_interface','inputs':[record(t) for t in (query,key,value)],
                'outputs':[record(out[0])], 'boundary':'post-RoPE/cache, before GQA repeat inside SDPA',
                'measured_traffic_bytes':None})
            return out
        ALL_ATTENTION_FUNCTIONS.register('sdpa',sdpa)
        names = {id(m): n for n, m in self.model.named_modules()}
        def hook(m, args, out):
            inputs = [record(t) for t in args if isinstance(t, torch.Tensor)]
            outputs = [record(out)] if isinstance(out, torch.Tensor) else []
            self.events.append({'event_id': len(self.events), 'module': names[id(m)],
                                'class': type(m).__name__, 'inputs': inputs, 'outputs': outputs,
                                'dependency_scope': 'ordered call interfaces; residual joins require decoder semantics',
                                'measured_traffic_bytes': None})
        for n, m in self.model.named_modules():
            if n and ('layers.' in n or n.endswith('norm')):
                self.handles.append(m.register_forward_hook(hook))
        return self

    def __exit__(self, *args):
        for h in self.handles:
            h.remove()
        self.attention_registry.register('sdpa',self.original_sdpa)


class OpObserver(TorchDispatchMode):
    """Actual ATen functional interfaces, including residual adds and recurrence arithmetic.

    Tensor identity dependencies cover observed outputs; unmatched inputs are external/cache/weight.
    Does not expose operations fused inside SDPA/CUDA kernels or physical memory transactions.
    """
    def __init__(self):
        self.events=[]
        self.producers={}

    def __torch_dispatch__(self, func, types, args=(), kwargs=None):
        inputs=[t for t in tree_flatten((args,kwargs or {}))[0] if isinstance(t,torch.Tensor)]
        deps=[]
        for t in inputs:
            old=self.producers.get(id(t))
            deps.append(old[1] if old and old[0]() is t else None)
        result=func(*args,**(kwargs or {}))
        outputs=[t for t in tree_flatten(result)[0] if isinstance(t,torch.Tensor)]
        eid=len(self.events)
        self.events.append({'event_id':eid,'operator':str(func),'inputs':[record(t) for t in inputs],
            'input_producer_events':deps,'outputs':[record(t) for t in outputs],
            'logical_read_bytes':sum(t.numel()*t.element_size() for t in inputs),
            'logical_write_bytes':sum(t.numel()*t.element_size() for t in outputs),
            'measured_traffic_bytes':None})
        for t in outputs:
            self.producers[id(t)]=(weakref.ref(t),eid)
        return result


@contextmanager
def capture_delta(out):
    """Capture only layer0 first prefill/decode delta call, before internal QK normalization."""
    from transformers.models.qwen3_5 import modeling_qwen3_5 as impl
    originals = {}
    counts = {}
    for name in ('torch_chunk_gated_delta_rule', 'torch_recurrent_gated_delta_rule'):
        original = getattr(impl, name)
        originals[name] = original
        counts[name] = 0
        def wrapper(*args, _name=name, _original=original, **kwargs):
            idx = counts[_name]
            counts[_name] += 1
            take = idx == 0
            payload = {}
            if take:
                for n, t in zip(('query', 'key', 'value'), args):
                    payload[n] = t.detach().cpu().clone()
                for n in ('g', 'beta', 'initial_state'):
                    t = kwargs.get(n)
                    payload[n] = t.detach().cpu().clone() if isinstance(t, torch.Tensor) else None
                payload['use_qk_l2norm_in_kernel'] = kwargs.get('use_qk_l2norm_in_kernel')
            result = _original(*args, **kwargs)
            if take:
                payload['output'] = result[0].detach().cpu().clone()
                payload['final_state'] = result[1].detach().cpu().clone()
                torch.save(payload, out / (_name+'.pt'))
            return result
        setattr(impl, name, wrapper)
    try:
        yield
    finally:
        for n, fn in originals.items():
            setattr(impl, n, fn)
        save(out/'delta-capture.json', {'calls': counts,
             'boundary': 'layer0, native function entrance BEFORE FP32 internal QK l2norm and q/sqrt(d); g log-decay, beta sigmoid; not raw gate logits',
             'saved': 'first chunk function call and first recurrent function call only; complete state only for selected layer'})


def install_int8(model):
    rows = []
    for name, m in model.named_modules():
        if not isinstance(m, torch.nn.Linear) or name == 'lm_head':
            continue
        w = m.weight.detach().float()
        s = w.abs().amax(-1, keepdim=True).clamp_min(1e-30)/127
        q = torch.round(w/s).clamp(-127, 127).to(torch.int8)
        error = compare(q.float()*s, w)
        m.register_buffer('qweight', q.t().contiguous())
        m.register_buffer('weight_scale', s.flatten())
        m.register_parameter('weight', None)
        m.integer_stats = {'calls': 0, 'max_abs_acc': 0, 'overflow_count': 0,
                           'activation_scale_bytes_total_logical': 0, 'saturation_count': 0}
        m.capture_integer_sample = 'layers.0.' in name
        def forward(self, x):
            shape, dtype = x.shape, x.dtype
            xf = x.reshape(-1, shape[-1]).float()
            scale = xf.abs().amax(-1, keepdim=True).clamp_min(1e-30)/127
            unbounded = torch.round(xf/scale)
            qa = unbounded.clamp(-127, 127).to(torch.int8)
            pad = (-qa.shape[0]) % 8
            if pad:
                qa = F.pad(qa, (0, 0, 0, pad))
            acc = torch._int_mm(qa.contiguous(), self.qweight)
            # Exact worst-case bound prevents overflow independently of observed wraparound.
            assert shape[-1]*127*127 <= 2147483647
            stat = self.integer_stats
            stat['calls'] += 1
            stat['max_abs_acc'] = max(stat['max_abs_acc'], int(acc.abs().max()))
            stat['saturation_count'] += int((unbounded.abs()>127).sum())
            stat['activation_scale_bytes_total_logical'] += scale.numel()*4
            if self.capture_integer_sample and not hasattr(self,'integer_sample'):
                self.integer_sample={'A':qa[:2].cpu().clone(),'B':self.qweight[:,:4].cpu().clone(),
                                     'accumulator':acc[:2,:4].cpu().clone(),
                                     'A_scale':scale[:2].cpu().clone(),'W_scale':self.weight_scale[:4].cpu().clone()}
            y = acc[:xf.shape[0]].float()*scale*self.weight_scale
            if self.bias is not None:
                y += self.bias.float()
            return y.to(dtype).reshape(*shape[:-1], -1)
        m.forward = types.MethodType(forward, m)
        rows.append({'module': name, 'shape_out_in': list(w.shape), 'scale_bytes': s.numel()*4,
                     'int8_weight_bytes': q.numel(), 'weight_error': error,
                     'int32_worst_case_abs_bound': w.shape[-1]*127*127})
        del w, q, s
    torch.cuda.empty_cache()
    return rows


@torch.inference_mode()
def main():
    p = argparse.ArgumentParser()
    p.add_argument('--model-dir', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--phase', choices=['reference', 'integer'], required=True)
    p.add_argument('--reference-dir', type=Path)
    p.add_argument('--lengths', nargs='*', type=int, default=[512,2048,4096,8192])
    p.add_argument('--short-only', action='store_true')
    a = p.parse_args()
    if a.out.exists():
        raise ValueError('output exists; preserve original evidence')
    if git('status', '--porcelain'):
        raise ValueError('formal run requires clean source commit')
    cfg = json.loads((HERE/'experiment.json').read_text())
    assert torch.__version__ == cfg['torch'] and transformers.__version__ == cfg['transformers']
    manifest = json.loads((a.model_dir/'model-manifest.json').read_text())
    assert manifest['complete']
    for n, info in manifest['files'].items():
        assert sha(a.model_dir/n) == info['sha256'], n
    a.out.mkdir(parents=True)
    source = {x.name: sha(x) for x in HERE.iterdir() if x.is_file()}
    save(a.out/'run-manifest.json', {'source_commit': git('rev-parse','HEAD'), 'source_files': source,
        'model': manifest, 'command': sys.argv, 'configuration': cfg,
        'start_epoch': time.time(), 'initial_free_total_bytes': torch.cuda.mem_get_info(),
        'gpu': torch.cuda.get_device_name(), 'backend': cfg['performance']['backend'],
        'phase': a.phase, 'offload': False, 'physical_traffic_measured': False})
    torch.manual_seed(20261023)
    torch.set_num_threads(4)
    torch.backends.cuda.matmul.allow_tf32 = False
    results = {'status': 'running', 'correctness': [], 'quality': [], 'state_sensitivity': [], 'performance': [], 'failures': []}
    def checkpoint():
        save(a.out/'results.json', results)
    try:
        tokenizer = AutoTokenizer.from_pretrained(a.model_dir, local_files_only=True, trust_remote_code=False)
        raw_cfg = json.loads((a.model_dir/'config.json').read_text())
        q35 = raw_cfg['model_type'] == 'qwen3_5'
        if q35:
            from transformers import Qwen3_5ForCausalLM, Qwen3_5TextConfig
            model, loading = Qwen3_5ForCausalLM.from_pretrained(a.model_dir,
                config=Qwen3_5TextConfig(**raw_cfg['text_config']), dtype=torch.bfloat16,
                device_map={'': 'cuda:0'}, local_files_only=True, trust_remote_code=False,
                attn_implementation='sdpa', output_loading_info=True)
        else:
            model, loading = AutoModelForCausalLM.from_pretrained(a.model_dir, dtype=torch.bfloat16,
                device_map={'': 'cuda:0'}, local_files_only=True, trust_remote_code=False,
                attn_implementation='sdpa', output_loading_info=True)
        save(a.out/'loading-info.json', loading)
        if loading.get('missing_keys') or loading.get('mismatched_keys') or loading.get('error_msgs'):
            raise ValueError('incomplete language-model checkpoint load; see loading-info.json')
        model.eval()
        assert all(x.device.type == 'cuda' for x in model.parameters())
        impl = inspect.getfile(type(model))
        save(a.out/'loaded-model.json', {'class': type(model).__name__, 'config': model.config.to_dict(),
            'parameters': sum(x.numel() for x in model.parameters()), 'implementation': impl,
            'implementation_sha256': sha(Path(impl)), 'allocated_bytes': torch.cuda.memory_allocated(),
            'reserved_bytes': torch.cuda.memory_reserved()})
        def tokens(text, n):
            v = tokenizer(text*max(1,n), add_special_tokens=False, return_tensors='pt')['input_ids'][:,:n]
            assert v.shape[1] == n
            return v.to('cuda')
        ids = tokens(cfg['long_text'], max([144]+[n+32 for n in a.lengths]))
        val = [tokens(t, cfg['quality_tokens_per_text']+1) for t in cfg['validation_texts']]
        cal = [tokens(t, cfg['quality_tokens_per_text']+1) for t in cfg['calibration_texts']]
        save(a.out/'inputs.json', {'long_token_ids': ids.tolist(), 'calibration_token_ids': [v.tolist() for v in cal],
            'validation_token_ids': [v.tolist() for v in val], 'teacher_forced': True,
            'calibration': 'dynamic per-row absmax has no fitted parameters; calibration run screens finite inputs only',
            'split': 'authored disjoint source texts, no held-out threshold tuning'})
        def call(x, cache=None, keep=1):
            return model(x, past_key_values=cache, use_cache=True, logits_to_keep=keep)
        if a.phase == 'integer':
            assert a.reference_dir
            save(a.out/'quantized-matrices.json', install_int8(model))
        # Calibration executes before validation and never changes the frozen method.
        for v in cal:
            o = call(v[:,:-1])
            assert bool(torch.isfinite(o.logits).all())
            del o
        checkpoint()
        if a.phase == 'reference':
            full = []
            for j in range(17):
                o = call(ids[:,:128+j])
                full.append(o.logits.detach().cpu())
                if j==16:
                    fresh_final_state=snapshot(o.past_key_values)
                del o
            torch.save(full, a.out/'short-full-logits.pt')
            ref_state = fresh_final_state
            for kind in ('cached', 'chunked'):
                cache = None
                for start in range(0,128,128 if kind=='cached' else 32):
                    o = call(ids[:,start:start+(128 if kind=='cached' else 32)],cache)
                    cache = o.past_key_values
                seq = [o.logits.detach().cpu()]
                for j in range(16):
                    o = call(ids[:,128+j:129+j], cache)
                    cache = o.past_key_values
                    seq.append(o.logits.detach().cpu())
                errors = [compare(x,y) for x,y in zip(seq,full)]
                state = snapshot(cache)
                state_errors = [{'name':n,**compare(t,ref_state[n])} for n,t in state.items()]
                ok = all(e['finite'] and e['max_abs'] <= cfg['reference_acceptance']['logits_max_abs'] and e['relative_l2'] <= cfg['reference_acceptance']['logits_relative_l2'] for e in errors)
                ok = ok and all(e['finite'] and e['relative_l2'] <= cfg['reference_acceptance']['state_relative_l2'] for e in state_errors)
                results['correctness'].append({'mode':kind,'pass':ok,'logits':errors,'states':state_errors,'cache':cache_info(cache)})
                del o,cache,state
                checkpoint()
            del ref_state, fresh_final_state, full
            # Limited raw capture and observer run are separate from all performance samples.
            o=call(ids[:,:129]); unobserved=o.logits.detach().cpu(); del o
            if q35:
                layer0 = model.model.layers[0].linear_attn
                torch.save({n:t.detach().cpu() for n,t in layer0.named_parameters()
                            if n in ('A_log','dt_bias','conv1d.weight','conv1d.bias')},a.out/'delta-parameters.pt')
                conv_inputs=[]
                def conv_input_hook(m, args, output):
                    if len(conv_inputs)<2:
                        conv_inputs.append(output.detach().cpu().clone())
                raw_handle=layer0.in_proj_qkv.register_forward_hook(conv_input_hook)
                with capture_delta(a.out), Observer(model) as obs:
                    o=call(ids[:,:128]); cache=o.past_key_values
                    before={n:t.cpu().clone() for n,t in cache_tensors(cache) if n.startswith('0/')}
                    o=call(ids[:,128:129],cache)
                    obs_output=o.logits.detach().cpu()
                    torch.save({'before':before,'after':{n:t.cpu().clone() for n,t in cache_tensors(cache) if n.startswith('0/')}},a.out/'selected-cache.pt')
                    save(a.out/'events.json',obs.events)
                raw_handle.remove()
                torch.save(conv_inputs,a.out/'preconv-qkv.pt')
            else:
                with Observer(model) as obs:
                    o=call(ids[:,:128]); o=call(ids[:,128:129],o.past_key_values)
                    obs_output=o.logits.detach().cpu()
                    save(a.out/'events.json',obs.events)
            del o
            observed_error=compare(obs_output,unobserved)
            results['correctness'].append({'mode':'observed_vs_fresh_prefix', 'logits':observed_error,
                'pass':observed_error['finite'] and observed_error['max_abs']<=cfg['reference_acceptance']['logits_max_abs'] and observed_error['relative_l2']<=cfg['reference_acceptance']['logits_relative_l2']})
            if q35:
                del cache,before
            gc.collect(); torch.cuda.empty_cache()
            with OpObserver() as opobs:
                o=call(ids[:,:128]); o=call(ids[:,128:129],o.past_key_values)
            op_error=compare(o.logits.cpu(),unobserved)
            save(a.out/'operator-events.json',opobs.events)
            save(a.out/'operator-counts.json',dict(Counter(e['operator'] for e in opobs.events)))
            results['correctness'].append({'mode':'dispatch_observed_vs_fresh_prefix','logits':op_error,
                'pass':op_error['finite'] and op_error['max_abs']<=cfg['reference_acceptance']['logits_max_abs'] and op_error['relative_l2']<=cfg['reference_acceptance']['logits_relative_l2']})
            del o,opobs
            gc.collect();torch.cuda.empty_cache()
            checkpoint()
            if not all(x['pass'] for x in results['correctness']):
                raise ValueError('short reference continuation failed frozen acceptance; long expansion withheld')
        for i,v in enumerate(val):
            o=call(v[:,:-1],keep=0)
            logits=o.logits.detach().cpu()
            if a.phase=='reference':
                torch.save(logits,a.out/f'validation-{i}.pt')
                results['quality'].append({'sample':i,'finite':bool(torch.isfinite(logits).all()),
                    'nll':float(F.cross_entropy(logits.float().reshape(-1,logits.shape[-1]),v[:,1:].cpu().reshape(-1)))})
            else:
                r=torch.load(a.reference_dir/f'validation-{i}.pt',weights_only=True)
                m=output_metrics(logits,r,v[:,1:].cpu())
                gate=cfg['candidate_screen']
                m['screen_pass']=m['finite'] and m['mean_kl']<=gate['mean_kl_max'] and m['nll_delta']<=gate['mean_nll_delta_max'] and m['top1_agreement']>=gate['top1_agreement_min']
                results['quality'].append({'sample':i,**m})
            del o,logits
            checkpoint()
        if a.phase=='reference':
            # Quantize native cached values after every call, keeping native arithmetic.
            baseline=[]
            o=call(ids[:,:128]); cache=o.past_key_values
            for j in range(16):
                o=call(ids[:,128+j:129+j],cache); cache=o.past_key_values
                baseline.append(o.logits.detach().cpu())
            del o,cache
            for bits in cfg['candidate_state_bits']:
                o=call(ids[:,:128]); cache=o.past_key_values
                state_metrics=fake_state(cache,bits)
                errors=[]
                for j in range(16):
                    o=call(ids[:,128+j:129+j],cache); cache=o.past_key_values
                    errors.append(compare(o.logits.cpu(),baseline[j]))
                    state_metrics.extend(fake_state(cache,bits))
                results['state_sensitivity'].append({'bits':bits,'execution':'fake_quant_native_updates',
                    'logits':errors,'state_local_roundtrip':state_metrics})
                del o,cache
                checkpoint()
        else:
            save(a.out/'integer-kernel-stats.json',{n:m.integer_stats for n,m in model.named_modules() if hasattr(m,'integer_stats')})
            torch.save({n:m.integer_sample for n,m in model.named_modules() if hasattr(m,'integer_sample')},a.out/'integer-kernel-samples.pt')
        gc.collect(); torch.cuda.empty_cache()
        if not a.short_only and a.phase=='reference':
            for length in a.lengths:
                for chunk in (length, cfg['performance']['chunk']):
                    try:
                        samples=[]
                        for rep in range(-cfg['performance']['warmup'],cfg['performance']['repeats']):
                            torch.cuda.empty_cache(); torch.cuda.reset_peak_memory_stats(); torch.cuda.synchronize()
                            start=time.perf_counter(); cache=None
                            for pos in range(0,length,chunk):
                                o=call(ids[:,pos:min(pos+chunk,length)],cache); cache=o.past_key_values
                            torch.cuda.synchronize(); pref=time.perf_counter()-start
                            pre_logits=o.logits.detach().cpu()
                            start_d=time.perf_counter()
                            for j in range(32):
                                o=call(ids[:,length+j:length+j+1],cache); cache=o.past_key_values
                            torch.cuda.synchronize(); dec=time.perf_counter()-start_d
                            tail=o.logits.detach().cpu()
                            entry={'repeat':rep,'warmup':rep<0,'prefill_s':pref,'decode_s':dec,'total_s':pref+dec,
                                   'peak_allocated_bytes':torch.cuda.max_memory_allocated(),'peak_reserved_bytes':torch.cuda.max_memory_reserved(),
                                   'cache':cache_info(cache)}
                            if rep==0:
                                state=snapshot(cache)
                                if chunk==length:
                                    one=(pre_logits,tail,state)
                                else:
                                    entry['vs_one_shot']={'prefill_logits':compare(pre_logits,one[0]),'decode_logits':compare(tail,one[1]),
                                         'states':[{'name':n,**compare(t,one[2][n])} for n,t in state.items()]}
                                # Only selected checkpoints persist, not every layer/step raw states.
                                selected={n:t for n,t in state.items() if n.startswith(('0/','3/'))}
                                torch.save({'prefill_logits':pre_logits,'decode_logits':tail,'selected_cache':selected},a.out/f'long-{length}-chunk{chunk}.pt')
                                del state
                            samples.append(entry)
                            del o,cache
                        results['performance'].append({'prefix':length,'chunk':chunk,'phase':a.phase,'samples':samples,'observers':False})
                        if chunk!=length:
                            # Sensitivity runs are never counted as performance samples.
                            for bits in cfg['candidate_state_bits']:
                                cache=None; stats={}
                                for pos in range(0,length,cfg['performance']['chunk']):
                                    o=call(ids[:,pos:min(pos+cfg['performance']['chunk'],length)],cache);cache=o.past_key_values
                                    for m in fake_state(cache,bits):
                                        stats[m['name']]=max(stats.get(m['name'],0),m['relative_l2'])
                                for j in range(32):
                                    o=call(ids[:,length+j:length+j+1],cache);cache=o.past_key_values
                                    for m in fake_state(cache,bits):
                                        stats[m['name']]=max(stats.get(m['name'],0),m['relative_l2'])
                                state=snapshot(cache)
                                results['state_sensitivity'].append({'prefix':length,'bits':bits,
                                    'execution':'fake_quant_native_updates', 'rounding_boundary':'each 256-token prefill call and each decode token',
                                    'final_logits_vs_one_shot':compare(o.logits.cpu(),one[1]),
                                    'final_state_vs_one_shot':[{'name':n,**compare(t,one[2][n])} for n,t in state.items()],
                                    'max_local_roundtrip_relative_l2':stats})
                                del o,cache,state
                                checkpoint()
                            del one
                    except Exception as exc:
                        results['failures'].append({'prefix':length,'chunk':chunk,'phase':a.phase,'error':repr(exc),'traceback':traceback.format_exc()})
                        for key in ('o','cache','one'):
                            if key in locals():
                                if key=='o': o=None
                                elif key=='cache': cache=None
                                else: one=None
                        gc.collect(); torch.cuda.empty_cache()
                    checkpoint()
        results['status']='completed_with_failures' if results['failures'] else 'completed'
        checkpoint()
        rows=[]
        for case in results['performance']:
            for s in case['samples']:
                rows.append({**{k:case[k] for k in ('prefix','chunk','phase')},**{k:s[k] for k in ('repeat','warmup','prefill_s','decode_s','total_s','peak_allocated_bytes','peak_reserved_bytes')}})
        if rows:
            with (a.out/'timings.csv').open('w',newline='') as f:
                w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    except Exception as exc:
        results['status']='failed'
        results['failures'].append({'error':repr(exc),'traceback':traceback.format_exc()})
        checkpoint()
        raise
    finally:
        save(a.out/'artifact-index.json',{str(p.relative_to(a.out)):{'bytes':p.stat().st_size,'sha256':sha(p)} for p in a.out.rglob('*') if p.is_file() and p.name!='artifact-index.json'})


if __name__=='__main__':
    main()
