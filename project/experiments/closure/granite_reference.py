"""Issue72: immutable, explicitly typed Granite route-stability references.

Each invocation is one precision variant. Original Issue70 FAIL remains FAIL.
This is reference arithmetic, not integer deployment or quality qualification.
"""
import argparse
import hashlib
import inspect
import io
import json
import os
from pathlib import Path
import platform
import sys
import time
import traceback
import types
import zipfile
import numpy as np

REVISION = 'a02780686e08a03fe0d2679a293b5c74a90efa89'
GATE = {'relative_l2_max': 2e-4, 'max_abs_max': 2e-3}
PROFILES = ('full', 'cached64', 'chunk16')


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda: f.read(8 << 20), b''):
            h.update(b)
    return h.hexdigest()


def save(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True,
        allow_nan=False, default=str) + '\n', encoding='utf-8', newline='\n')


def npz(path, arrays):
    with zipfile.ZipFile(path, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=3) as z:
        for key, value in sorted(arrays.items()):
            b = io.BytesIO()
            np.save(b, np.asarray(value), allow_pickle=False)
            info = zipfile.ZipInfo(key + '.npy', (2026, 10, 24, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, b.getvalue())


def metric(a, b):
    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)
    if a.shape != b.shape or not a.size or not np.isfinite(a).all() or not np.isfinite(b).all():
        raise ValueError('comparison requires finite, nonempty, matching arrays')
    return {'relative_l2': float(np.linalg.norm(a-b)/max(np.linalg.norm(b), 1e-30)),
            'max_abs': float(np.max(np.abs(a-b)))}


def spans(profile, length=72):
    if profile == 'full':
        return [(0, length)]
    if profile == 'cached64':
        return [(0, 64)] + [(i, i+1) for i in range(64, length)]
    if profile == 'chunk16':
        return [(i, min(length, i+16)) for i in range(0, length, 16)]
    raise ValueError('unreviewed profile')


def routing_summary(logits, ids):
    x = np.asarray(logits)
    ids = np.asarray(ids)
    if x.ndim != 2 or x.shape[1] != 40 or ids.shape != (len(x), 8) or not np.isfinite(x).all():
        raise ValueError('complete40/top8 shape/finite')
    chosen = np.take_along_axis(x, ids, axis=1)
    if not np.array_equal(np.sort(chosen, axis=1), np.sort(x, axis=1)[:, -8:]):
        raise ValueError('router IDs not actual top8')
    if not all(len(set(row.tolist())) == 8 for row in ids):
        raise ValueError('router duplicate ID')
    sorted_x = np.sort(x, axis=1)
    margin = sorted_x[:, -8] - sorted_x[:, -9]
    return {'top8_margin': margin.tolist(), 'minimum_top8_margin': float(np.min(margin)),
            'exact_cutoff_tie_tokens': int(np.count_nonzero(margin == 0)),
            'any_exact_logit_tie_tokens': int(np.count_nonzero(np.any(np.diff(sorted_x, axis=1) == 0, axis=1)))}


def route_comparison(logits_a, ids_a, logits_b, ids_b):
    a = routing_summary(logits_a, ids_a)
    b = routing_summary(logits_b, ids_b)
    changed = [len(set(x)^set(y))//2 for x, y in zip(ids_a.tolist(), ids_b.tolist())]
    return {'set_changed_tokens': int(np.count_nonzero(changed)),
            'ordered_changed_tokens': int(np.count_nonzero(np.any(ids_a != ids_b, axis=1))),
            'replaced_experts': changed, 'logits_error': metric(logits_b, logits_a),
            'full': a, 'other': b}


def high_precision_router(module, hidden_states):
    """Actual current hidden; no frozen IDs, no tolerance tie merging.

    Stable descending sort means expert index ascending only when scores equal
    exactly. All distinct near-tie values retain numerical score order.
    """
    import torch
    import torch.nn.functional as F
    logits = F.linear(hidden_states.to(torch.float64), module.weight.to(torch.float64))
    ids = torch.argsort(logits, dim=-1, descending=True, stable=True)[:, :module.top_k]
    selected = torch.gather(logits, 1, ids)
    weights = torch.softmax(selected, dim=-1).to(hidden_states.dtype)
    return ids, weights, logits


def explicit_eager_experts(module, hidden_states, top_k_index, top_k_weights):
    """Source-equivalent direct linear expert math, no grouped-mm dtype fallback.

    Preserve the installed Python expert forward's expert/within-expert ordering.
    FP64 stays FP64. Native32-eager separately checks same-input original backend.
    """
    import torch
    import torch.nn.functional as F
    result=torch.zeros_like(hidden_states)
    mask=F.one_hot(top_k_index,num_classes=module.num_experts+1).permute(2,1,0)
    hit=torch.greater(mask.sum(dim=(-1,-2)),0).nonzero()
    for idx in hit:
        idx=idx[0]
        if idx==module.num_experts:continue
        rank,token=torch.where(mask[idx])
        gate,up=F.linear(hidden_states[token],module.gate_up_proj[idx]).chunk(2,dim=-1)
        current=F.linear(module.act_fn(gate)*up,module.down_proj[idx])
        current=current*top_k_weights[token,rank,None]
        result.index_add_(0,token,current.to(result.dtype))
    if hasattr(module,'_issue72_original_forward') and not hasattr(module,'_issue72_backend_control'):
        native=module._issue72_original_forward(hidden_states,top_k_index,top_k_weights)
        module._issue72_backend_control={
            'metric':metric(result.detach().cpu().numpy(),native.detach().cpu().numpy()),
            'native':native.detach().cpu().numpy().copy(),
            'eager':result.detach().cpu().numpy().copy()}
    return result


def run(args):
    import torch
    import transformers
    from transformers import AutoModelForCausalLM
    if args.out.exists():
        raise ValueError('refuse overwrite')
    binding = json.loads(args.binding.read_text(encoding='utf-8'))
    if not binding.get('commit') or binding.get('granite_reference_sha256') != sha(__file__):
        raise ValueError('source binding missing/mismatch')
    original = json.loads((args.capture/'manifest.json').read_text())
    if original.get('kind') != 'granite_capture' or original.get('status') != 'FAIL' or original.get('model_revision') != REVISION:
        raise ValueError('requires retained original FAIL at pinned revision')
    for rec in original['artifacts']:
        p = args.capture/rec['path']
        if p.stat().st_size != rec['bytes'] or sha(p) != rec['sha256']:
            raise ValueError('original capture artifact mismatch '+rec['path'])
    for name, rec in original['model_files'].items():
        p = args.model/name
        if p.stat().st_size != rec['bytes'] or sha(p) != rec['sha256']:
            raise ValueError('pinned model file mismatch '+name)
    if args.threads < 1 or args.threads > int(os.environ.get('SLURM_CPUS_PER_TASK', str(args.threads))):
        raise ValueError('CPU allocation')
    torch.set_num_threads(args.threads)
    torch.set_num_interop_threads(1)
    torch.manual_seed(20261024)
    torch.use_deterministic_algorithms(True)
    args.out.mkdir(parents=True)
    start = time.monotonic()
    manifest = {'kind': 'granite_reference72', 'schema': 1, 'status': 'ERROR',
        'precision_variant': args.precision, 'source': binding, 'producer_sha256': sha(__file__),
        'original_capture': {'manifest_sha256': sha(args.capture/'manifest.json'),
            'status': original['status'], 'cases': original['cases'],
            'correctness_gate': original['correctness_gate']},
        'model_revision': REVISION, 'model_files': original['model_files'],
        'host': platform.node(), 'threads': args.threads,
        'versions': {'python': sys.version, 'numpy': np.__version__, 'torch': torch.__version__,
            'transformers': transformers.__version__}, 'artifacts': [],
        'claim': 'new explicitly typed reference only; original failure unchanged; no application quality or integer hardware claim'}
    try:
        dtype = torch.float64 if args.precision == 'model64' else torch.float32
        model, loading = AutoModelForCausalLM.from_pretrained(args.model, local_files_only=True,
            trust_remote_code=False, use_safetensors=True, dtype=dtype,
            attn_implementation='eager', output_loading_info=True)
        if any(loading.get(k) for k in ('missing_keys', 'mismatched_keys', 'error_msgs')):
            raise ValueError('incomplete loading '+str(loading))
        model.eval()
        layers = model.model.layers
        cfg = model.config
        if (len(layers), cfg.hidden_size, cfg.num_local_experts, cfg.num_experts_per_tok) != (32, 1536, 40, 8):
            raise ValueError('unreviewed Granite configuration')
        impl = Path(inspect.getfile(type(layers[0].block_sparse_moe)))
        if sha(impl) != original['implementation']['sha256']:
            raise ValueError('framework source differs from original capture')
        (args.out/'granitemoe-implementation.py').write_bytes(impl.read_bytes())
        manifest['implementation'] = {'sha256': sha(impl), 'source_path': str(impl)}
        manifest['precision'] = {'parameter_dtype': str(dtype),
            'router': 'native FP32 linear then float32 logits/softmax; native topk' if args.precision in ('native32','native32_eager')
                else 'FP64 linear/logits/softmax; stable descending exact-score sort; weights returned in hidden dtype',
            'framework_internal_casts_unchanged': {
                'GraniteMoeRMSNorm': 'input/variance/rsqrt FP32, return input dtype then weight multiply',
                'GraniteMoeRotaryEmbedding': 'position and inv_freq/phase/cos/sin FP32, return hidden dtype',
                'eager_attention_forward': 'attention softmax forced FP32, cast to query dtype'},
            'all_ops_fp64': False, 'integer_execution': False}
        arrays = {}
        for i, layer in enumerate(layers):
            router = layer.block_sparse_moe.router
            arrays['router_weight.'+str(i)] = router.weight.detach().cpu().numpy().copy()
            if args.precision in ('router64','model64'):
                router.forward = types.MethodType(high_precision_router, router)
        if args.precision in ('native32_eager','model64'):
            for layer in layers:
                experts=layer.block_sparse_moe.experts
                if args.precision=='native32_eager':
                    experts._issue72_original_forward=experts.forward
                experts.forward=types.MethodType(explicit_eager_experts,experts)
        manifest['expert_backend']={
            'implementation':'Issue72 explicit eager linear/SiLU/down/weighted index_add' if args.precision in ('native32_eager','model64') else 'unchanged installed framework dispatcher',
            'source_basis':'installed GraniteMoeExperts.forward Python body; implementation copy SHA recorded',
            'reason':'installed grouped_mm rejects Double; no dtype downgrade or environment modification',
            'control':'native32_eager compares first calibration full call of every layer with original dispatcher on identical current hidden/routes/gates' if args.precision=='native32_eager' else 'separate native32_eager control required; model64 alone cannot isolate backend from precision'}
        cases = {}
        for case in ('calibration', 'evaluation'):
            token_ids = original['cases'][case]['tokens']
            tokens = torch.tensor([token_ids], dtype=torch.long)
            if tokens.shape != (1, 72):
                raise ValueError('frozen case length')
            arrays[case+'.tokens'] = np.asarray(token_ids, dtype=np.int64)
            case_report = {'tokens': token_ids, 'runs': {}, 'comparisons': {}}
            for profile in PROFILES:
                trace = {}
                cursors = {i: 0 for i in range(len(layers))}
                handles = []
                router_dtypes = {}
                def append(key, value):
                    trace.setdefault(key, []).append(value.detach().cpu().numpy().copy())
                for i, layer in enumerate(layers):
                    def router_hook(module, inputs, outputs, layer_id=i):
                        if not isinstance(outputs, tuple) or len(outputs) != 3:
                            raise ValueError('unreviewed router interface')
                        ids, weights, logits = outputs
                        cursors[layer_id] += len(ids)
                        prefix = str(layer_id)+'.'
                        for key, val in (('router_input', inputs[0]), ('ids', ids), ('weights', weights), ('logits', logits)):
                            append(prefix+key, val)
                        observed = {'input': str(inputs[0].dtype), 'weight': str(module.weight.dtype),
                            'logits': str(logits.dtype), 'softmax_return': str(weights.dtype)}
                        if layer_id in router_dtypes and router_dtypes[layer_id] != observed:
                            raise ValueError('router dtype changed in profile')
                        router_dtypes[layer_id] = observed
                    def moe_hook(module, inputs, outputs, layer_id=i):
                        value = outputs[0] if isinstance(outputs, tuple) else outputs
                        append(str(layer_id)+'.moe_output', value.reshape(-1, value.shape[-1]))
                    def layer_hook(module, inputs, outputs, layer_id=i):
                        value = outputs[0] if isinstance(outputs, tuple) else outputs
                        append(str(layer_id)+'.hidden', value.reshape(-1, value.shape[-1]))
                    handles.extend([layer.block_sparse_moe.router.register_forward_hook(router_hook),
                        layer.block_sparse_moe.register_forward_hook(moe_hook), layer.register_forward_hook(layer_hook)])
                lm = []
                past = None
                try:
                    with torch.inference_mode():
                        for begin, end in spans(profile):
                            output = model(input_ids=tokens[:, begin:end], past_key_values=past, use_cache=profile!='full')
                            if profile != 'full':
                                past = output.past_key_values
                            lm.append(output.logits.detach().cpu().numpy()[0].copy())
                    if any(n != 72 for n in cursors.values()):
                        raise ValueError('incomplete layer trace')
                finally:
                    for h in handles:
                        h.remove()
                base = case+'.'+profile+'.'
                arrays[base+'lm_logits'] = np.concatenate(lm, axis=0)
                for key, values in trace.items():
                    arrays[base+key] = np.concatenate(values, axis=0)
                case_report['runs'][profile] = {'cache_spans': spans(profile),
                    'router_observed_dtypes': router_dtypes,
                    'exact_tie_rule': 'framework native torch.topk, no forced expert order' if args.precision in ('native32','native32_eager')
                        else 'descending actual FP64 score; exact ties expert index ascending only',
                    'router_summaries': {str(i): routing_summary(arrays[base+str(i)+'.logits'], arrays[base+str(i)+'.ids'])
                        for i in range(32)}}
                print(json.dumps({'case': case, 'precision': args.precision, 'profile': profile,
                    'lm_vs_full': metric(arrays[base+'lm_logits'], arrays[case+'.full.lm_logits'])}), flush=True)
                del past, output, lm, trace
            for profile in ('cached64', 'chunk16'):
                records = []
                for i in range(32):
                    p, q = case+'.full.'+str(i)+'.', case+'.'+profile+'.'+str(i)+'.'
                    records.append({'layer': i,
                        **route_comparison(arrays[p+'logits'], arrays[p+'ids'], arrays[q+'logits'], arrays[q+'ids']),
                        'router_input_error': metric(arrays[q+'router_input'], arrays[p+'router_input']),
                        'moe_output_error': metric(arrays[q+'moe_output'], arrays[p+'moe_output']),
                        'layer_hidden_error': metric(arrays[q+'hidden'], arrays[p+'hidden'])})
                e = metric(arrays[case+'.'+profile+'.lm_logits'], arrays[case+'.full.lm_logits'])
                case_report['comparisons'][profile] = {'lm_error': e,
                    'passes_unchanged_gate': e['relative_l2']<=GATE['relative_l2_max'] and e['max_abs']<=GATE['max_abs_max'],
                    'total_layer_token_set_changes': sum(r['set_changed_tokens'] for r in records), 'layers': records}
            cases[case] = case_report
        if args.precision=='native32_eager':
            controls={}
            for i,layer in enumerate(layers):
                control=layer.block_sparse_moe.experts._issue72_backend_control
                e=control['metric']
                controls[str(i)]={'error':e,'passes_same_math_control':e['relative_l2']<=2e-5 and e['max_abs']<=2e-3}
                arrays['backend_control.'+str(i)+'.native']=control['native']
                arrays['backend_control.'+str(i)+'.eager']=control['eager']
            manifest['expert_backend']['same_input_controls']=controls
            manifest['expert_backend']['all_same_math_controls_pass']=all(x['passes_same_math_control'] for x in controls.values())
        qualified = all(c['passes_unchanged_gate'] for x in cases.values() for c in x['comparisons'].values())
        report = {'precision_variant': args.precision, 'unchanged_gate': GATE, 'cases': cases,
            'reference_self_consistency': 'PASS' if qualified else 'FAIL',
            'original_capture_status': 'FAIL',
            'limits': ['Two existing 72-token texts only; no generated-token application-quality measurement',
                'router64 retains upstream FP32 perturbations; stable sort is not a near-tie tolerance',
                'model64 has documented forced FP32 framework casts; not an all-operator FP64 oracle',
                'A passing new reference cannot retroactively accept native32 or Issue70']}
        save(args.out/'report.json', report)
        npz(args.out/'trace.npz', arrays)
        manifest['status'] = 'EXECUTED_REFERENCE'
        manifest['reference_self_consistency'] = report['reference_self_consistency']
        manifest['artifacts'] = [{'path': p.name, 'bytes': p.stat().st_size, 'sha256': sha(p)} for p in
            (args.out/'report.json', args.out/'trace.npz', args.out/'granitemoe-implementation.py')]
    except Exception as e:
        manifest['error'] = {'type': type(e).__name__, 'message': str(e), 'traceback': traceback.format_exc()}
        raise
    finally:
        manifest['seconds'] = time.monotonic()-start
        save(args.out/'manifest.json', manifest)


def main():
    p = argparse.ArgumentParser(__doc__)
    p.add_argument('--model', type=Path, required=True)
    p.add_argument('--capture', type=Path, required=True)
    p.add_argument('--binding', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--threads', type=int, default=8)
    p.add_argument('--precision', choices=('native32', 'native32_eager', 'router64', 'model64'), required=True)
    run(p.parse_args())


if __name__ == '__main__':
    main()
