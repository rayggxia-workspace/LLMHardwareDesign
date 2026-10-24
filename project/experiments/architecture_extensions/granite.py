"""Bounded Granite MoE capture and software-integer boundary experiment (Issue70).

No remote code, training, full-model quantization, or hardware timing claim.
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
import zipfile

import numpy as np


TEXTS = {
    'calibration': 'A hardware researcher checks integer matrix multiplication and memory access. '
        'Each token chooses several experts. Record the input, routing scores, selected experts, '
        'normalization and output. Calibration data must remain separate from evaluation data. '
        'A reproducible experiment fixes the model revision, source code and input tokens. ',
    'evaluation': 'Compute a short numerical example and explain its steps. A library stores '
        'books on several shelves. Eight selected workers each process part of a request and '
        'combine their answers. The implementation must preserve ordering, scales and exact '
        'integer accumulation while reporting any clipping or approximation. '
}


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(8 << 20), b''):
            h.update(block)
    return h.hexdigest()


def save(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False, default=str) + '\n',
                          encoding='utf-8', newline='\n')


def deterministic_npz(path, arrays):
    with zipfile.ZipFile(path, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=3) as z:
        for key, value in sorted(arrays.items()):
            b = io.BytesIO()
            np.save(b, np.asarray(value), allow_pickle=False)
            info = zipfile.ZipInfo(key + '.npy', (2026, 10, 24, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, b.getvalue())


def error(actual, expected):
    a = np.asarray(actual, dtype=np.float64)
    b = np.asarray(expected, dtype=np.float64)
    if a.shape != b.shape or not np.isfinite(a).all() or not np.isfinite(b).all():
        raise ValueError('non-finite or mismatched comparison')
    return {'relative_l2': float(np.linalg.norm(a-b) / max(np.linalg.norm(b), 1e-30)),
            'max_abs': float(np.max(np.abs(a-b)))}


def source_binding(path):
    binding = json.loads(Path(path).read_text(encoding='utf-8'))
    expected = binding.get('granite_sha256', binding.get('sources', {}).get('granite.py'))
    if expected is None or digest(__file__) != expected:
        raise ValueError('granite.py binding SHA mismatch/missing')
    if not binding.get('commit'):
        raise ValueError('binding commit missing')
    return binding


def artifact(path, kind):
    return {'path': Path(path).name, 'sha256': digest(path), 'bytes': Path(path).stat().st_size,
            'kind': kind}


def expert_weights(moe):
    """Accept only two documented HF layouts, then require full MoE replay agreement."""
    if hasattr(moe, 'experts') and hasattr(moe.experts, 'gate_up_proj'):
        router = moe.router.weight
        up, down = moe.experts.gate_up_proj, moe.experts.down_proj
        layout = 'experts.gate_up_proj/down_proj;router.weight'
    elif hasattr(moe, 'input_linear') and hasattr(moe, 'output_linear'):
        router = moe.router.layer.weight
        up, down = moe.input_linear.weight, moe.output_linear.weight
        layout = 'input_linear/output_linear;router.layer.weight'
    else:
        raise ValueError('unreviewed Granite expert/router layout')
    if up.ndim != 3 or down.ndim != 3 or router.ndim != 2:
        raise ValueError('unexpected expert tensor rank')
    e, two_i, h = up.shape
    if two_i % 2 or tuple(down.shape) != (e, h, two_i//2) or tuple(router.shape) != (e, h):
        raise ValueError('unexpected expert layout dimensions')
    return router, up, down, layout


def capture(args):
    import torch
    import torch.nn.functional as F
    import transformers
    from transformers import AutoConfig, AutoModelForCausalLM, AutoTokenizer

    binding = source_binding(args.binding)
    if args.out.exists():
        raise ValueError('refuse overwrite')
    if args.prefill != 64 or args.decode != 8:
        raise ValueError('frozen minimal protocol is B1/prefill64/decode8')
    if args.threads > int(os.environ.get('SLURM_CPUS_PER_TASK', str(args.threads))):
        raise ValueError('thread allocation exceeded')
    torch.set_num_threads(args.threads)
    torch.set_num_interop_threads(1)
    torch.manual_seed(20261024)
    torch.use_deterministic_algorithms(True)
    cfg = AutoConfig.from_pretrained(args.model, local_files_only=True, trust_remote_code=False)
    if (cfg.model_type, cfg.num_local_experts, cfg.num_experts_per_tok, cfg.hidden_size,
            cfg.intermediate_size) != ('granitemoe', 40, 8, 1536, 512):
        raise ValueError('not the frozen Granite3.1-3B-A800M configuration')
    args.out.mkdir(parents=True)
    start = time.monotonic()
    manifest = {'schema_version': 1, 'kind': 'granite_capture', 'status': 'ERROR',
        'source': {'commit': binding['commit'], 'granite_sha256': digest(__file__),
                   'binding_sha256': digest(args.binding)}, 'model_revision': binding.get('model_revision', 'pending-verification'),
        'scope': 'one complete layer0 MoE; full model FP32 CPU correctness only',
        'host': platform.node(), 'versions': {'torch': torch.__version__, 'numpy': np.__version__,
            'transformers': transformers.__version__, 'python': sys.version},
        'precision': {'source': str(getattr(cfg, 'dtype', getattr(cfg, 'torch_dtype', None))),
            'reference_execution': 'CPU FP32 cast of source weights; eager attention'},
        'threads': args.threads, 'config': cfg.to_dict(), 'artifacts': [], 'performance_eligible': False}
    try:
        files = {}
        for p in sorted(args.model.iterdir()):
            if p.is_file() and (p.suffix in ('.safetensors', '.json', '.model', '.txt')
                                or p.name == 'tokenizer.json'):
                files[p.name] = {'bytes': p.stat().st_size, 'sha256': digest(p)}
        manifest['model_files'] = files
        model, loading = AutoModelForCausalLM.from_pretrained(args.model, local_files_only=True,
            trust_remote_code=False, use_safetensors=True, dtype=torch.float32,
            attn_implementation='eager', output_loading_info=True)
        if any(loading.get(k) for k in ('missing_keys', 'mismatched_keys', 'error_msgs')):
            raise ValueError('incomplete loading ' + str(loading))
        model.eval()
        moe = model.model.layers[0].block_sparse_moe
        r, up, down, layout = expert_weights(moe)
        impl = Path(inspect.getfile(type(moe)))
        manifest['implementation'] = {'path': str(impl), 'sha256': digest(impl),
                                      'moe_class': type(moe).__name__, 'layout': layout}
        (args.out/'granitemoe-implementation.py').write_bytes(impl.read_bytes())
        tokenizer = AutoTokenizer.from_pretrained(args.model, local_files_only=True, trust_remote_code=False)
        arrays = {'router_weight': r.detach().cpu().numpy(), 'gate_up_weight': up.detach().cpu().numpy(),
                  'down_weight': down.detach().cpu().numpy()}
        traces = []
        enabled = [False]
        def hook(module, inputs, outputs):
            if not enabled[0]:
                return
            x = inputs[0].detach().reshape(-1, cfg.hidden_size)
            y = outputs[0] if isinstance(outputs, tuple) else outputs
            logits = F.linear(x, r)
            values, ids = torch.topk(logits, cfg.num_experts_per_tok, dim=-1)
            weights = torch.softmax(values, dim=-1, dtype=torch.float32)
            manual = torch.zeros_like(x)
            for expert in range(cfg.num_local_experts):
                token, rank = torch.where(ids == expert)
                if token.numel():
                    gate, value = F.linear(x[token], up[expert]).chunk(2, dim=-1)
                    ey = F.linear(F.silu(gate)*value, down[expert])
                    manual.index_add_(0, token, ey * weights[token, rank, None])
            replay = error(manual.detach().numpy(), y.detach().reshape_as(x).numpy())
            if replay['relative_l2'] > 2e-5 or replay['max_abs'] > 2e-3:
                raise ValueError('full MoE replay disagrees; layout/router semantics not accepted ' + str(replay))
            traces.append({'x': x.cpu().numpy(), 'y': y.detach().reshape_as(x).cpu().numpy(),
                'router_logits': logits.cpu().numpy(), 'top8_ids': ids.cpu().numpy(),
                'top8_weights': weights.cpu().numpy(), 'replay': replay})
        handle = moe.register_forward_hook(hook)
        cases = {}
        with torch.inference_mode():
            for name, text in TEXTS.items():
                ids = tokenizer.encode(text*5, add_special_tokens=True)[:72]
                if len(ids) != 72:
                    raise ValueError('fixed text too short')
                tokens = torch.tensor([ids], dtype=torch.long)
                traces.clear(); enabled[0] = True
                full = model(input_ids=tokens, use_cache=False).logits.detach()
                enabled[0] = False
                tr = traces[0]
                for k, v in tr.items():
                    if k != 'replay':
                        arrays[name+'_'+k] = v
                arrays[name+'_tokens'] = np.asarray(ids, dtype=np.int64)
                pref = model(input_ids=tokens[:,:64], use_cache=True)
                past = pref.past_key_values
                decoded = []
                for i in range(64, 72):
                    one = model(input_ids=tokens[:,i:i+1], past_key_values=past, use_cache=True)
                    past = one.past_key_values
                    decoded.append(one.logits.detach())
                cached = torch.cat([pref.logits.detach(), *decoded], dim=1)
                past = None; chunks = []
                for i in range(0,72,16):
                    chunk = model(input_ids=tokens[:,i:i+16], past_key_values=past, use_cache=True)
                    past = chunk.past_key_values
                    chunks.append(chunk.logits.detach())
                chunked = torch.cat(chunks, dim=1)
                ce, he = error(cached.numpy(), full.numpy()), error(chunked.numpy(), full.numpy())
                passed = all(z['relative_l2'] <= 2e-4 and z['max_abs'] <= 2e-3 for z in (ce, he))
                arrays[name+'_logits_last'] = full[0,-1].numpy()
                cases[name] = {'tokens': ids, 'text': text, 'batch': 1, 'prefill': 64,
                    'decode': 8, 'decode_mode': 'fixed teacher-forced continuation; not generated quality',
                    'cached': ce, 'chunk16': he, 'moe_replay': tr['replay'], 'passed': passed}
        handle.remove()
        deterministic_npz(args.out/'capture.npz', arrays)
        manifest['cases'] = cases
        manifest['correctness_gate'] = {'relative_l2_max': 2e-4, 'max_abs_max': 2e-3,
                                         'passed': all(c['passed'] for c in cases.values())}
        manifest['status'] = 'PASS' if manifest['correctness_gate']['passed'] else 'FAIL'
        for name, kind in [('capture.npz', 'complete_layer0_moe'), ('granitemoe-implementation.py', 'framework_source')]:
            manifest['artifacts'].append(artifact(args.out/name, kind))
    finally:
        manifest['seconds'] = time.monotonic() - start
        save(args.out/'manifest.json', manifest)
    if manifest['status'] != 'PASS':
        raise RuntimeError('reference correctness failed; preserve receipt, do not accept quantization')


def rne_shift(value, shift):
    """Signed unbounded Python oracle: ties to even; negative shift is exact left shift."""
    value, shift = int(value), int(shift)
    if shift <= 0:
        return value << -shift
    sign = -1 if value < 0 else 1
    q, r = divmod(abs(value), 1 << shift)
    half = 1 << (shift-1)
    return sign * (q + int(r > half or (r == half and (q & 1))))


def quantize(x, scale=None):
    x = np.asarray(x, dtype=np.float64)
    if not np.isfinite(x).all():
        raise ValueError('nonfinite quantization')
    if scale is None:
        scale = np.maximum(np.max(np.abs(x), axis=-1, keepdims=True)/127., 2.**-40)
    scale = np.asarray(scale, dtype=np.float64)
    if not np.isfinite(scale).all() or np.any(scale <= 0):
        raise ValueError('invalid scale')
    raw = np.rint(x/scale)
    sat = int(np.count_nonzero((raw < -127) | (raw > 127)))
    return np.clip(raw, -127, 127).astype(np.int8), scale, sat


def stable_topk(logits, k=8):
    logits = np.asarray(logits, dtype=np.float64)
    if not np.isfinite(logits).all() or logits.ndim != 2:
        raise ValueError('router logits')
    ids = np.argsort(-logits, axis=-1, kind='stable')[:,:k]
    v = np.take_along_axis(logits, ids, axis=1)
    weights = np.exp(v-np.max(v, axis=1, keepdims=True))
    weights /= weights.sum(axis=1, keepdims=True)
    return ids, weights


def checked_dot(a, w):
    a = np.asarray(a); w = np.asarray(w)
    if a.dtype != np.int8 or w.dtype != np.int8 or a.shape[-1] != w.shape[-1]:
        raise ValueError('W8A8 dot format')
    bound = np.sum(np.abs(w.astype(np.int64)), axis=-1)*127
    if np.any(bound > 2**31-1):
        raise OverflowError('INT32 mathematical dot bound')
    acc = a.astype(np.int64) @ w.astype(np.int64).T
    if np.any(acc < -(2**31)) or np.any(acc > 2**31-1):
        raise OverflowError('INT32 dot')
    return acc, bound


def q31_coefficients(ratio):
    ratio = np.asarray(ratio, dtype=np.float64)
    if not np.isfinite(ratio).all() or np.any(ratio < 0):
        raise ValueError('RQ ratio')
    mantissa, exponent = np.frexp(ratio)
    multiplier = np.rint(mantissa * (2.**31)).astype(np.int64)
    # Normalize the rare rounded-to-2**31 mantissa to unsigned-31-bit magnitude.
    rollover = multiplier == 2**31
    multiplier[rollover] //= 2
    exponent[rollover] += 1
    return multiplier, (31-exponent).astype(np.int16)


def requantize(value, multiplier, shift, bits=32):
    value, multiplier, shift = np.broadcast_arrays(value, multiplier, shift)
    out = np.empty(value.shape, dtype=np.int64)
    sat = 0
    lo, hi = -(2**(bits-1)), 2**(bits-1)-1
    for idx in np.ndindex(value.shape):
        product = int(value[idx])*int(multiplier[idx])
        if not -(2**63) <= product <= 2**63-1:
            raise OverflowError('RQ wide product')
        q = rne_shift(product, int(shift[idx]))
        sat += int(q < lo or q > hi)
        out[idx] = min(hi, max(lo, q))
    return out, sat


def silu(x):
    x = np.asarray(x, dtype=np.float64)
    ex = np.exp(-np.abs(x))
    sigmoid = np.where(x >= 0, 1/(1+ex), ex/(1+ex))
    return x*sigmoid


def numeric(args):
    binding = source_binding(args.binding)
    if args.out.exists():
        raise ValueError('refuse overwrite')
    cm = json.loads((args.capture/'manifest.json').read_text())
    if cm['status'] != 'PASS' or not cm['correctness_gate']['passed']:
        raise ValueError('capture correctness not passed')
    for rec in cm['artifacts']:
        if digest(args.capture/rec['path']) != rec['sha256']:
            raise ValueError('capture artifact SHA '+rec['path'])
    source = np.load(args.capture/'capture.npz', allow_pickle=False)
    r = source['router_weight'].astype(np.float64)
    up = source['gate_up_weight'].astype(np.float64)
    down = source['down_weight'].astype(np.float64)
    if (r.shape, up.shape, down.shape) != ((40,1536),(40,1024,1536),(40,1536,512)):
        raise ValueError('capture layer0 shapes')
    args.out.mkdir(parents=True)
    start = time.monotonic()
    data = {}; witnesses = {'schema_version':1,'dots':[],'requants':[],'routing':[],'merges':[]}
    positions = np.asarray([60,61,62,63,64,65,66,67], dtype=np.int64)
    x = source['evaluation_x'][positions].astype(np.float64)
    fp_y = source['evaluation_y'][positions].astype(np.float64)
    fp_logits = source['evaluation_router_logits'][positions].astype(np.float64)
    fp_ids, fp_gates = stable_topk(fp_logits)
    # Calibration observes only the first 64 calibration tokens, never evaluation.
    calx = source['calibration_x'][:64].astype(np.float64)
    cal_scale_x = max(float(np.max(np.abs(calx)))/127.,2.**-40)
    cal_ids = source['calibration_top8_ids'][:64]
    cal_mid_max = 0.
    for e in np.unique(cal_ids):
        ti = np.flatnonzero(np.any(cal_ids == e, axis=1))
        z = calx[ti] @ up[e].T
        mid = silu(z[:,:512])*z[:,512:]
        cal_mid_max = max(cal_mid_max, float(np.max(np.abs(mid))))
    cal_scale_mid = max(cal_mid_max/127., 2.**-40)
    common_max = max(float(np.max(np.abs(source['calibration_y'][:64]))),2.**-40)
    common_exp = int(np.ceil(np.log2(common_max/(2.**23))))
    common_unit = 2.**common_exp
    wr, sr, _ = quantize(r)
    wu, su, _ = quantize(up)
    wd, sd, _ = quantize(down)
    data.update(positions=positions, router_logits_fp=fp_logits, route_ids_fp=fp_ids,
                route_weights_fp=fp_gates, reference_output=fp_y,
                common_unit_exp=np.asarray(common_exp,dtype=np.int16))
    dot_count = 0
    def dot_witness(a, w, acc, label):
        nonlocal dot_count
        if dot_count >= 32:
            return
        i = dot_count; dot_count += 1
        data['a8_'+str(i)] = np.asarray(a,dtype=np.int8)
        data['w8_'+str(i)] = np.asarray(w,dtype=np.int8)
        data['acc_'+str(i)] = np.asarray(acc,dtype=np.int64)
        witnesses['dots'].append({'a':'a8_'+str(i),'w':'w8_'+str(i),'acc':'acc_'+str(i),
            'bound':int(127*np.abs(np.asarray(w,dtype=np.int64)).sum()), 'label':label,
            'accumulator':'INT32 mathematical result stored int64 for checking'})
    cases = []
    for activation in ('dynamic_row','calibration_tensor'):
        ax, sx, input_sat = quantize(x, None if activation=='dynamic_row' else cal_scale_x)
        # Broadcast scale uniformly per row while preserving exact actual metadata.
        sx = np.broadcast_to(sx,(len(x),1)).copy()
        router_acc, rb = checked_dot(ax,wr)
        q_logits = router_acc.astype(np.float64)*sx*sr.T
        q_ids, q_gates = stable_topk(q_logits)
        data['router_logits_q_'+activation] = q_logits
        data['route_ids_q_'+activation] = q_ids
        data['route_weights_q_'+activation] = q_gates
        data['input_codes_'+activation] = ax
        data['input_scales_'+activation] = sx
        witnesses['routing'].append({'logits_fp':'router_logits_fp', 'logits_q':'router_logits_q_'+activation,
            'ids_fp':'route_ids_fp','ids_q':'route_ids_q_'+activation,'k':8,
            'tie_rule':'descending score, lower expert index first','activation':activation})
        for j in range(4):
            dot_witness(ax[0],wr[j],router_acc[0,j],activation+'/router/'+str(j))
        set_changes = [len(set(a)^set(b))//2 for a,b in zip(fp_ids,q_ids)]
        for route_mode in ('route_fixed_diagnostic','route_recomputed'):
            ids, gates = (fp_ids, fp_gates) if route_mode=='route_fixed_diagnostic' else (q_ids,q_gates)
            pred = np.zeros_like(fp_y)
            all_acc = np.zeros((len(x),8,1536),dtype=np.int64)
            all_coeff = np.zeros((len(x),8,1536),dtype=np.float64)
            intermediate_sat = 0
            max_acc = int(np.max(np.abs(router_acc)))
            for e in np.unique(ids):
                ti, rank = np.where(ids==e)
                au, _ = checked_dot(ax[ti],wu[e])
                max_acc = max(max_acc,int(np.max(np.abs(au))))
                z = au.astype(np.float64)*sx[ti]*su[e].T
                mid = silu(z[:,:512])*z[:,512:]
                am, sm, sat = quantize(mid,None if activation=='dynamic_row' else cal_scale_mid)
                sm = np.broadcast_to(sm,(len(ti),1)).copy()
                intermediate_sat += sat
                ad, _ = checked_dot(am,wd[e])
                max_acc = max(max_acc,int(np.max(np.abs(ad))))
                physical = sm*sd[e].T
                ey = ad.astype(np.float64)*physical
                for ii, rr, yy, aa, ss in zip(ti,rank,ey,ad,physical):
                    pred[ii] += yy*gates[ii,rr]
                    all_acc[ii,rr] = aa
                    all_coeff[ii,rr] = ss/common_unit
                # Complete actual dots, not sampled/truncated K.
                for j in range(2):
                    dot_witness(ax[ti[0]],wu[e,j],au[0,j],activation+'/'+route_mode+'/gate_up/'+str(e)+'/'+str(j))
                    dot_witness(am[0],wd[e,j],ad[0,j],activation+'/'+route_mode+'/down/'+str(e)+'/'+str(j))
            mult, shifts = q31_coefficients(all_coeff)
            aligned, rq_sat = requantize(all_acc,mult,shifts,32)
            gate_q15 = np.rint(gates*32768.).astype(np.int64)
            weighted = np.sum(aligned*gate_q15[:,:,None],axis=1,dtype=np.int64)
            if np.any(np.abs(aligned.astype(object)*gate_q15[:,:,None].astype(object)) > 2**63-1):
                raise OverflowError('weighted product')
            output = np.empty_like(weighted)
            merge_sat = 0
            for idx in np.ndindex(weighted.shape):
                exact_sum = sum(int(aligned[idx[0],k,idx[1]])*int(gate_q15[idx[0],k]) for k in range(8))
                if not -(2**63) <= exact_sum < 2**63:
                    raise OverflowError('wide weighted merge')
                if exact_sum != int(weighted[idx]):
                    raise OverflowError('software sum wrap')
                q = rne_shift(exact_sum,15)
                merge_sat += int(q < -(2**31) or q > 2**31-1)
                output[idx] = min(2**31-1,max(-(2**31),q))
            tag = activation+'__'+route_mode
            data['output_fp_bridge__'+tag] = pred
            data['output_common_s32__'+tag] = output
            # Preserve a complete 8-expert/H1536 merge for every candidate, not one column.
            p = 'merge_'+str(len(witnesses['merges']))
            for name, value in [('acc',all_acc[0]),('multiplier',mult[0]),('shift',shifts[0]),
                                ('aligned',aligned[0]),('gate_q15',gate_q15[0]),
                                ('weighted_sum',weighted[0]),('out',output[0])]:
                data[p+'_'+name] = value
            witnesses['merges'].append({'label':tag,'acc':p+'_acc','multiplier':p+'_multiplier',
                'shift':p+'_shift','aligned':p+'_aligned','gate_q15':p+'_gate_q15',
                'weighted_sum':p+'_weighted_sum','out':p+'_out','bits':32,'gate_shift':15,
                'common_unit_exp':common_exp,'shape':[8,1536], 'token_position':60})
            for j in range(8):
                i = len(witnesses['requants'])
                for suffix, value in [('a',all_acc[0,0,j]),('m',mult[0,0,j]),
                                      ('s',shifts[0,0,j]),('out',aligned[0,0,j])]:
                    data['rq_'+suffix+'_'+str(i)] = np.asarray(value,dtype=np.int64)
                witnesses['requants'].append({'value':'rq_a_'+str(i),'multiplier':'rq_m_'+str(i),
                    'shift':'rq_s_'+str(i),'out':'rq_out_'+str(i),'bits':32,
                    'definition':'satS32(RNE(value*multiplier / 2**shift)); shift already includes Q31'})
            counts = np.bincount(ids.ravel(),minlength=40)
            for phase, sl in [('prefill',slice(0,4)),('decode',slice(4,8))]:
                local_counts = np.bincount(ids[sl].ravel(),minlength=40)
                cases.append({'activation':activation,'route':route_mode,'phase':phase,
                    'positions':positions[sl].tolist(),'tokens':4,'selected_experts':ids[sl].tolist(),
                    'expert_accesses':local_counts.tolist(),'unique_experts':int(np.count_nonzero(local_counts)),
                    'router_replaced_experts_per_token':set_changes[sl],
                    'router_changed_tokens':int(np.count_nonzero(np.asarray(set_changes[sl]))),
                    'fp_bridge_error':error(pred[sl],fp_y[sl]),
                    'common_s32_error':error(output[sl].astype(np.float64)*common_unit,fp_y[sl]),
                    'common_vs_fp_bridge':error(output[sl].astype(np.float64)*common_unit,pred[sl]),
                    'input_saturation_total_8tokens':input_sat,'intermediate_saturation_total_8tokens':intermediate_sat,
                    'rq_saturation_total_8tokens':rq_sat,'merge_saturation_total_8tokens':merge_sat,
                    'max_abs_matrix_acc_total_8tokens':max_acc,
                    'route_weight_q15_sum_error':(gate_q15[sl].sum(axis=1)-32768).tolist(),
                    'logical_payload_per_token':{'input_once_A8':1536,'input_duplicated_8_A8':8*1536,
                        'expert_return_S32':8*1536*4,'merged_S32':1536*4,
                        'route_ids_uint8':8,'route_weights_Q15_uint16':16,
                        'input_scale_fp64':8,'return_scale_fp64_per_coordinate':8*1536*8,
                        'RQ_Q31mult_uint32_shift_int16_per_coordinate':8*1536*6,
                        'common_unit_int16':2},
                    'expert_W8_unique_payload_lower_bound':int(np.count_nonzero(local_counts))*(1024*1536+1536*512),
                    'expert_W8_payload_no_reuse_each_access':32*(1024*1536+1536*512),
                    'expert_Wscale_fp64_per_unique_lower_bound':int(np.count_nonzero(local_counts))*(1024+1536)*8,
                    'matrix_MACs':{'router':4*1536*40,'experts':32*(1024*1536+1536*512)},
                    'weight_reuse_qualification':'unique lower bound needs grouping/residency; no realized cache traffic claimed',
                    'physical_transport':'unmeasured; header/padding/packing/multicast implementation not included'})
    if len(witnesses['dots']) != 32 or len(witnesses['requants']) != 32:
        raise ValueError('incomplete witness set')
    deterministic_npz(args.out/'witnesses.npz',data)
    save(args.out/'witnesses.json',witnesses)
    metrics = {'schema_version':1,'cases':cases,'calibration':{'tokens':64,
        'source':'calibration first64 only; no evaluation quality selection',
        'input_static_scale':cal_scale_x,'intermediate_static_scale':cal_scale_mid,
        'common_unit_exp':common_exp,'common_S32_calibration_target_bits':23},
        'contract':{'matrix':'symmetric W8A8 [-127,127], no zero point; INT32 bound checked before dot',
            'weight_scales':'dynamic offline maxabs/per expert/per output row, FP64 metadata',
            'activation_scales':'dynamic per token row or separate calibration tensor static',
            'rounding':'RNE ties-even, saturation explicit; INT32 dots computed using int64 NumPy software',
            'router':'W8A8 logits -> FP64 scale bridge -> stable top8 -> FP64 softmax',
            'nonlinear':'FP64 SiLU and elementwise gate*up bridge, then A8 RNE/saturation',
            'merge':'S32 common power2 units, Q31 multiplier+int16 shift RQ; Q0.15 gates; checked S64 products/sum; RNE15/S32sat',
            'fallbacks':['softmax','SiLU','activation scale selection/division','Q31 parameter synthesis'],
            'cost_unqualified':['target wide multiply lowering','division/exp/SFU','physical ports/banks/fabric','end-to-end quality/PPA'],
            'witnesses':'32 full-K actual dots,32 RQs,4 full-H1536 eight-expert merges; independent receiver required'},
        'decision_scope':'route_fixed is diagnostic, not dynamic MoE claim; no full-model quality or hardware speed claim'}
    save(args.out/'metrics.json',metrics)
    manifest = {'schema_version':1,'kind':'granite_numeric','status':'EXECUTED',
        'source':{'commit':binding['commit'],'granite_sha256':digest(__file__),
                  'binding_sha256':digest(args.binding),'capture_manifest_sha256':digest(args.capture/'manifest.json'),
                  'capture_source':cm['source']},'capture':str(args.capture),
        'model_revision':cm['model_revision'],'host':platform.node(),'numpy':np.__version__,
        'seconds':time.monotonic()-start,'artifacts':[artifact(args.out/x,k) for x,k in
            [('metrics.json','structured_metrics'),('witnesses.json','independent_schema'),('witnesses.npz','actual_integer_witnesses')]],
        'acceptance':'software integer references executed; application quality/hardware qualification not accepted'}
    save(args.out/'manifest.json',manifest)


def main():
    p = argparse.ArgumentParser(__doc__)
    sub = p.add_subparsers(dest='command', required=True)
    c = sub.add_parser('capture')
    c.add_argument('--model', type=Path, required=True)
    c.add_argument('--out', type=Path, required=True)
    c.add_argument('--binding', type=Path, required=True)
    c.add_argument('--threads', type=int, default=8)
    c.add_argument('--prefill', type=int, default=64)
    c.add_argument('--decode', type=int, default=8)
    n = sub.add_parser('numeric')
    n.add_argument('--capture',type=Path,required=True)
    n.add_argument('--binding',type=Path,required=True)
    n.add_argument('--out',type=Path,required=True)
    a = p.parse_args()
    (capture if a.command=='capture' else numeric)(a)


if __name__ == '__main__':
    main()
