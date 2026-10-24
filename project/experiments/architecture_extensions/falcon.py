"""Bounded Falcon-H1 hybrid capture and state-storage diagnostics (Issue 70).

Native execution is FP32, converted from the downloaded source dtype. State
storage quantization uses floating coefficients and is NOT integer execution.
No downloads, CUDA kernels, environment mutations or model-quality claims.
"""
from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import math
import os
from pathlib import Path
import platform
import sys
import time

import numpy as np


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def _finite_json(value):
    if isinstance(value, dict):
        return {k: _finite_json(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [_finite_json(v) for v in value]
    if isinstance(value, float) and not math.isfinite(value):
        return "inf" if value > 0 else "-inf" if value < 0 else "nan"
    return value


def weight_headers(directory):
    """Verify source dtype from actual safetensors headers, not a model-card guess."""
    import struct
    records = []
    for path in sorted(Path(directory).glob("*.safetensors")):
        with path.open("rb") as f:
            size = struct.unpack("<Q", f.read(8))[0]
            if size > 64 * 1024 * 1024:
                raise ValueError("oversized safetensors header")
            header_bytes = f.read(size)
        header = json.loads(header_bytes)
        records.append({"file": path.name, "bytes": path.stat().st_size,
                        "header_sha256": hashlib.sha256(header_bytes).hexdigest(),
                        "tensor_dtypes": sorted({v["dtype"] for k, v in header.items() if k != "__metadata__"})})
    if not records:
        raise ValueError("source safetensors missing")
    return records


def metric(actual, reference):
    a, r = np.asarray(actual, np.float64), np.asarray(reference, np.float64)
    d = a - r
    return {"max_abs": float(np.max(np.abs(d), initial=0)),
            "relative_l2": float(np.linalg.norm(d.ravel()) / max(np.linalg.norm(r.ravel()), 1e-30))}


def recurrence(a, dt, x, b, c, skip, initial=None, *, storage_bits=None, unit=None,
               chunks=None, checkpoint=None, epoch=0, position=0):
    """FP64 Mamba-2 head; optional RNE/saturated integer *storage*, FP64 update.

    The exact evaluation order is (dt * b) * x, then a * previous + injection.
    Checkpoints carry code/state, units, epoch and absolute next position.
    Chunk boundaries have no numerical effect and never reset state.
    """
    a, dt, x, b, c = [np.asarray(z, np.float64) for z in (a, dt, x, b, c)]
    t, d, n = len(a), x.shape[1], b.shape[1]
    if (dt.shape != (t,) or x.shape != (t, d) or b.shape != (t, n)
            or c.shape != (t, n) or not all(np.all(np.isfinite(z)) for z in (a, dt, x, b, c))):
        raise ValueError("invalid coefficient shape or non-finite input")
    if np.any((a < 0) | (a > 1)) or np.any(dt < 0):
        raise ValueError("Mamba-2 coefficient domain")
    if storage_bits not in (None, 16, 32):
        raise ValueError("unsupported state storage")
    if storage_bits and (unit is None or not math.isfinite(unit) or unit <= 0):
        raise ValueError("positive frozen unit required")
    state = np.zeros((d, n), np.float64) if initial is None else np.asarray(initial, np.float64).copy()
    if state.shape != (d, n) or not np.all(np.isfinite(state)):
        raise ValueError("invalid initial state")
    if checkpoint is not None:
        if checkpoint["epoch"] != epoch or checkpoint["position"] != position:
            raise ValueError("stale epoch or wrong position")
        if checkpoint["storage_bits"] != storage_bits or checkpoint["unit"] != unit:
            raise ValueError("checkpoint format/unit mismatch")
        state = np.asarray(checkpoint["state"], np.float64).copy()
        if state.shape != (d, n):
            raise ValueError("checkpoint shape mismatch")
    if chunks is not None and (any(z <= 0 for z in chunks) or sum(chunks) != t):
        raise ValueError("chunks must cover the complete sequence")
    states, outputs, codes, saturations = [], [], [], []
    low, high = (-(1 << (storage_bits - 1)), (1 << (storage_bits - 1)) - 1) if storage_bits else (0, 0)
    for i in range(t):
        proposal = state * a[i] + (dt[i] * b[i][None, :]) * x[i][:, None]
        if not np.all(np.isfinite(proposal)):
            raise OverflowError("non-finite FP64 update bridge")
        sat = 0
        if storage_bits:
            rounded = np.rint(proposal / unit)
            sat = int(np.count_nonzero((rounded < low) | (rounded > high)))
            code = np.clip(rounded, low, high).astype(np.int16 if storage_bits == 16 else np.int32)
            state = code.astype(np.float64) * unit
            codes.append(code.copy())
        else:
            state = proposal
        states.append(state.copy())
        outputs.append(state @ c[i] + float(skip) * x[i])
        saturations.append(sat)
    checkpoint_out = {"epoch": epoch, "position": position + t, "storage_bits": storage_bits,
                      "unit": unit, "state": state.copy()}
    return {"states": np.asarray(states), "output": np.asarray(outputs),
            "codes": np.asarray(codes), "saturations": np.asarray(saturations, np.int64),
            "checkpoint": checkpoint_out}


def calibrated_unit(calibration_states, bits):
    """Power-of-two unit from separate calibration only, one complete head."""
    if bits not in (16, 32):
        raise ValueError("invalid width")
    magnitude = float(np.max(np.abs(calibration_states), initial=0))
    return 2.0 ** math.ceil(math.log2(max(magnitude, 2.0 ** -80) / ((1 << (bits - 1)) - 1)))


def costs(config, length, *, state_bits=32, conv_bits=32, kv_bits=32, scale_bits=16, state_format=None):
    """Logical bit-accurate inventory; no timing/PPA or free quantized formats."""
    h = config["mamba_n_heads"]
    d, n = config["mamba_d_head"], config["mamba_d_state"]
    inner = config.get("mamba_d_ssm") or int(config["mamba_expand"] * config["hidden_size"])
    conv = inner + 2 * config["mamba_n_groups"] * n
    layers, hidden = config["num_hidden_layers"], config["hidden_size"]
    elems = h * d * n
    state_payload = (elems * state_bits + 7) // 8
    state_format = state_format or ("FP32" if state_bits == 32 else "S16")
    head_meta = h * ((scale_bits + 7) // 8) if state_format != "FP32" else 0
    # Each candidate publishes a head unit and layer epoch/version/position.
    # Native FP32 needs the same ownership/version record but no quantization unit.
    version_meta = 24
    return {"state_bits": state_bits, "state_format": state_format, "conv_bits": conv_bits, "kv_bits": kv_bits,
            "state_elements_per_layer": elems, "state_payload_per_layer": state_payload,
            "state_units_per_layer": head_meta, "owner_epoch_version_position_per_layer": version_meta,
            "state_payload_all_layers": state_payload * layers,
            "conv_payload_per_layer": (conv * config["mamba_d_conv"] * conv_bits + 7) // 8,
            "kv_payload_per_layer": (2 * config["num_key_value_heads"] * config["head_dim"] * length * kv_bits + 7) // 8,
            "kv_append_payload_per_layer_token": (2 * config["num_key_value_heads"] * config["head_dim"] * kv_bits + 7) // 8,
            "head0_state_payload": (d * n * state_bits + 7) // 8,
            "state_rmw_payload_per_layer_token": 2 * state_payload,
            "head0_state_rmw_128bit_beats": 2 * math.ceil(d * n * state_bits / 128),
            "hybrid_norm_fanout_payload_per_layer_token_fp32": 2 * hidden * 4,
            "hybrid_branch_join_read_payload_per_layer_token_fp32": 2 * hidden * 4,
            "hybrid_join_write_payload_per_layer_token_fp32": hidden * 4,
            "mamba_gated_norm_vector_elements": inner,
            "mamba_gated_norm_raw_gate_gamma_payload_fp32": 3 * inner * 4,
            "mamba_gated_norm_group_reduction_elements": inner // config["mamba_n_groups"],
            "qualification": "Logical payload; independent format candidates, not all-integer or physical timing. Owner descriptor is a declared 24-byte record, endpoint/link packing remains separate."}


def _np(tensor):
    return tensor.detach().cpu().float().numpy().copy()


def _cache_snapshot(cache):
    """Transformers 5.20 hybrid cache: attention + convolution + recurrent."""
    layer = cache.layers[0]
    result = {}
    for src, dst in (("keys", "kv_key"), ("values", "kv_value"),
                     ("conv_states", "conv"), ("recurrent_states", "ssm")):
        value = getattr(layer, src)
        if isinstance(value, (tuple, list)):
            value = value[0]
        if value is not None:
            result[dst] = _np(value)
    return result


def _conv_coefficients(projected, mixer, config):
    """Independent NumPy FP64 causal conv/SiLU/softplus + head-0 coefficients."""
    p = np.asarray(projected, np.float64)
    inner, n, groups = mixer.intermediate_size, mixer.ssm_state_size, mixer.n_groups
    raw = p[:, inner:inner + mixer.conv_dim]
    weight = _np(mixer.conv1d.weight)[:, 0].astype(np.float64)
    bias = _np(mixer.conv1d.bias).astype(np.float64) if mixer.conv1d.bias is not None else np.zeros(mixer.conv_dim)
    k = weight.shape[1]
    padded = np.pad(raw, ((k - 1, 0), (0, 0)))
    conv = np.empty_like(raw)
    for t in range(len(raw)):
        pre = np.sum(padded[t:t + k].T * weight, axis=1) + bias
        conv[t] = pre / (1 + np.exp(-pre))
    x = conv[:, :mixer.head_dim]
    b = conv[:, inner:inner + n]
    c = conv[:, inner + groups * n:inner + groups * n + n]
    raw_dt = p[:, inner + mixer.conv_dim]
    dt = np.logaddexp(0, raw_dt + float(_np(mixer.dt_bias)[0]))
    limits = mixer.time_step_limit
    dt = np.clip(dt, limits[0], limits[1])
    a_log = float(_np(mixer.A_log)[0])
    a = np.exp(-np.exp(a_log) * dt)
    return {"a": a, "dt": dt, "x": x, "b": b, "c": c,
            "skip": np.asarray(float(_np(mixer.D)[0])), "A_log": np.asarray(a_log)}


def _w8a8(cal_x, eval_x, weight):
    """Complete K, 16 output channels; explicit INT32 accumulation, FP scales."""
    w = np.asarray(weight, np.float64)
    ws = np.maximum(np.max(np.abs(w), axis=1), 1e-30) / 127
    qw = np.clip(np.rint(w / ws[:, None]), -127, 127).astype(np.int8)
    results, arrays = [], {"weight": w, "weight_code": qw, "weight_scale": ws,
                          "calibration_input": np.asarray(cal_x, np.float64), "evaluation_input": np.asarray(eval_x, np.float64)}
    for name in ("cal_static_tensor", "eval_dynamic_row"):
        scale = (np.full((len(eval_x), 1), max(float(np.max(np.abs(cal_x))), 1e-30) / 127)
                 if name == "cal_static_tensor" else np.maximum(np.max(np.abs(eval_x), axis=1, keepdims=True), 1e-30) / 127)
        unclip = np.rint(eval_x / scale)
        qx = np.clip(unclip, -127, 127).astype(np.int8)
        # NumPy int64 supplies an independent overflow witness before INT32 cast.
        acc = qx.astype(np.int64) @ qw.astype(np.int64).T
        if np.any((acc < -(1 << 31)) | (acc > (1 << 31) - 1)):
            raise OverflowError("INT32 candidate overflow")
        dequant = acc * scale * ws[None, :]
        key = name + "_"
        arrays.update({key + "input_code": qx, key + "input_scale": scale,
                       key + "accumulator": acc.astype(np.int32), key + "dequant": dequant})
        results.append({"scheme": name, "activation_saturations": int(np.count_nonzero(np.abs(unclip) > 127)),
                        "error": metric(dequant, eval_x @ w.T), "K": w.shape[1], "outputs": w.shape[0],
                        "int32_worst_case_abs_bound": int(w.shape[1] * 127 * 127),
                        "max_actual_accumulator_abs": int(np.max(np.abs(acc))),
                        "weight_scale_bytes": int(ws.size * 8), "activation_scale_bytes": int(scale.size * 8),
                        "qualification": "Software INT32 dot reference; floating scale/dequant; no INT8 throughput claim."})
    return results, arrays


def capture(args):
    import torch
    import transformers
    from transformers import AutoConfig, AutoModelForCausalLM
    from transformers.cache_utils import DynamicCache
    from transformers.models.falcon_h1 import modeling_falcon_h1 as modeling

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=False)
    started = time.time()
    torch.set_num_threads(args.threads)
    torch.set_num_interop_threads(1)
    torch.manual_seed(args.seed)
    torch.use_deterministic_algorithms(True)
    config = AutoConfig.from_pretrained(args.weights, local_files_only=True, trust_remote_code=False)
    if config.model_type != "falcon_h1" or config.mamba_n_groups != 1:
        raise ValueError("bounded protocol requires Falcon-H1 one B/C group")
    config._attn_implementation = "eager"
    model = AutoModelForCausalLM.from_pretrained(args.weights, local_files_only=True, trust_remote_code=False,
                                               dtype=torch.float32, attn_implementation="eager").eval()
    layer, mixer = model.model.layers[0], model.model.layers[0].mamba
    rng = np.random.default_rng(args.seed)
    total = args.prefill + args.decode
    # Exact token arrays are the data version. Disjoint IDs keep calibration/eval separate.
    calibration_ids = rng.integers(100, config.vocab_size // 2, size=(1, 16), dtype=np.int64)
    evaluation_ids = rng.integers(config.vocab_size // 2, config.vocab_size - 1, size=(1, total), dtype=np.int64)
    arrays = {"calibration.tokens": calibration_ids, "evaluation.tokens": evaluation_ids}
    mode = {"name": None}
    trace_scan = {"enabled": False, "values": []}
    hooks = []

    def save_hook(name, *, before=False):
        def fn(module, values, result=None):
            if mode["name"]:
                value = values[0] if before else (result[0] if isinstance(result, tuple) else result)
                arrays[mode["name"] + "." + name] = _np(value)[0]
        return fn

    hooks += [layer.register_forward_pre_hook(save_hook("input", before=True)),
              layer.register_forward_hook(save_hook("layer_output")),
              layer.input_layernorm.register_forward_hook(save_hook("norm")),
              layer.self_attn.register_forward_hook(save_hook("attention")),
              mixer.register_forward_hook(save_hook("mamba")),
              layer.pre_ff_layernorm.register_forward_pre_hook(save_hook("pre_ff_input", before=True)),
              mixer.in_proj.register_forward_hook(save_hook("projected_raw")),
              mixer.norm.register_forward_pre_hook(save_hook("raw_scan", before=True)),
              mixer.out_proj.register_forward_pre_hook(save_hook("scan_normed", before=True))]
    def trace_scan_hook(module, values):
        if trace_scan["enabled"]:
            trace_scan["values"].append(_np(values[0]).reshape(-1, mixer.intermediate_size)[0, :mixer.head_dim])
    hooks.append(mixer.norm.register_forward_pre_hook(trace_scan_hook))
    with torch.inference_mode():
        mode["name"] = "calibration"
        model(torch.from_numpy(calibration_ids), use_cache=False, logits_to_keep=1)
        mode["name"] = "evaluation"
        full = model(torch.from_numpy(evaluation_ids), use_cache=True, logits_to_keep=1)
        arrays["evaluation.last_logits"] = _np(full.logits)
        full_snapshot = _cache_snapshot(full.past_key_values)
        for name, a in full_snapshot.items():
            arrays["full.final." + name] = a
            arrays["initial." + name] = (np.zeros(a.shape[:-2] + (0, a.shape[-1]), dtype=a.dtype)
                                          if name.startswith("kv_") else np.zeros_like(a))
        del full
        mode["name"] = None
        cached = model(torch.from_numpy(evaluation_ids[:, :args.prefill]), use_cache=True, logits_to_keep=1)
        prefix_snapshot = _cache_snapshot(cached.past_key_values)
        cache = cached.past_key_values
        del cached
        for name, a in prefix_snapshot.items():
            arrays["cached.prefix." + name] = a
        decode_logits = []
        for i in range(args.prefill, total):
            decoded = model(torch.from_numpy(evaluation_ids[:, i:i + 1]), past_key_values=cache, use_cache=True, logits_to_keep=1)
            decode_logits.append(_np(decoded.logits))
            cache = decoded.past_key_values
        arrays["cached.decode_logits"] = np.concatenate(decode_logits, axis=1)
        final_snapshot = _cache_snapshot(cache)
        for name, a in final_snapshot.items():
            arrays["cached.final." + name] = a
        continuity = {"last_logits": metric(decode_logits[-1], arrays["evaluation.last_logits"]),
                      "cache": {name: metric(final_snapshot[name], a) for name, a in full_snapshot.items()}}
        del cache, decoded

        # Replay one actual complete hybrid layer. All branches use the same true
        # layer0 input; no fabricated cross-layer/independent-window stitching.
        inputs = torch.from_numpy(arrays["evaluation.input"]).unsqueeze(0)
        # Copy shape/config for a one-layer cache: no unused 31-layer allocations.
        import copy
        one_config = copy.deepcopy(config)
        one_config.num_hidden_layers = 1
        chunk_results = {}
        for chunk in (1, 8, 16):
            trace_scan["enabled"] = chunk == 1
            hybrid_cache = DynamicCache(config=one_config)
            pieces, head_states, checkpoints = [], [], []
            for start in range(0, total, chunk):
                stop = min(start + chunk, total)
                positions = torch.arange(start, stop).unsqueeze(0)
                current = inputs[:, start:stop]
                rotary = model.model.rotary_emb(current, positions)
                key_positions = torch.arange(stop)
                causal = torch.where(key_positions[None, :] <= positions[0, :, None], 0., torch.finfo(torch.float32).min)[None, None]
                output = layer(current, attention_mask=causal, mamba_attention_mask=None,
                               position_ids=positions, past_key_values=hybrid_cache,
                               use_cache=True, position_embeddings=rotary)
                pieces.append(_np(output[0] if isinstance(output, tuple) else output)[0])
                snapshot = _cache_snapshot(hybrid_cache)
                if chunk == 1:
                    head_states.append(snapshot["ssm"][0, 0].copy())
                checkpoints.append({"owner": "layer0.hybrid", "next_position": stop, "epoch": 0, "version": stop,
                                    "descriptor_is_analysis_metadata_not_native_epoch_enforcement": True,
                                    "kv_shape": list(snapshot["kv_key"].shape), "conv_shape": list(snapshot["conv"].shape),
                                    "ssm_shape": list(snapshot["ssm"].shape)})
            outputs = np.concatenate(pieces)
            arrays[f"chunk{chunk}.output"] = outputs
            for name, a in snapshot.items():
                arrays[f"chunk{chunk}.final." + name] = a
            if chunk == 1:
                arrays["native.head0.states"] = np.asarray(head_states)
                arrays["native.head0.output"] = np.asarray(trace_scan["values"])
                baseline = outputs
                baseline_snapshot = snapshot
            chunk_results[str(chunk)] = {"output_vs_tokenwise": metric(outputs, baseline),
                "output_vs_full_layer": metric(outputs, arrays["evaluation.layer_output"]),
                "final_vs_tokenwise": {name: metric(snapshot[name], a) for name, a in baseline_snapshot.items()},
                "checkpoints": checkpoints}
        # Reset is an intentional negative, not a supported continuous execution.
        reset_output = []
        trace_scan["enabled"] = False
        for start in range(0, total, 8):
            stop = min(start + 8, total)
            current = inputs[:, start:stop]
            positions = torch.arange(start, stop).unsqueeze(0)
            rotary = model.model.rotary_emb(current, positions)
            local_pos = torch.arange(stop - start)
            mask = torch.where(local_pos[None, :] <= local_pos[:, None], 0., torch.finfo(torch.float32).min)[None, None]
            output = layer(current, attention_mask=mask, mamba_attention_mask=None, position_ids=positions,
                           past_key_values=DynamicCache(config=one_config), use_cache=True, position_embeddings=rotary)
            reset_output.append(_np(output[0] if isinstance(output, tuple) else output)[0])
        reset_error = metric(np.concatenate(reset_output), baseline)
    for hook in hooks:
        hook.remove()

    for split in ("calibration", "evaluation"):
        arrays[split + ".projected"] = arrays[split + ".projected_raw"] * _np(mixer.mup_vector)[0]
    for name, weight in (("conv_weight", mixer.conv1d.weight), ("conv_bias", mixer.conv1d.bias),
                         ("dt_bias", mixer.dt_bias), ("A_log", mixer.A_log), ("D", mixer.D),
                         ("mup_vector", mixer.mup_vector), ("gated_norm_gamma", mixer.norm.weight)):
        if weight is not None:
            arrays["weight." + name] = _np(weight)
    # Prove the parallel join using the exact captured data and configured MuP multipliers.
    join_expected = (arrays["evaluation.input"] + arrays["evaluation.mamba"] * config.ssm_out_multiplier
                     + arrays["evaluation.attention"] * config.attention_out_multiplier)
    join_error = metric(join_expected, arrays["evaluation.pre_ff_input"])
    numeric = {}
    for split in ("calibration", "evaluation"):
        coeff = _conv_coefficients(arrays[split + ".projected"], mixer, config)
        for name, a in coeff.items():
            numeric[split + "." + name] = a
        ref = recurrence(coeff["a"], coeff["dt"], coeff["x"], coeff["b"], coeff["c"], coeff["skip"])
        numeric[split + ".fp64_states"] = ref["states"]
        numeric[split + ".fp64_output"] = ref["output"]
        numeric[split + ".initial_state"] = np.zeros_like(ref["states"][0])
    numeric["native.head0.states"] = arrays["native.head0.states"]
    numeric["native.head0.output"] = arrays["native.head0.output"]
    # Whole4096 gated norm couples all32 head outputs even though each R state
    # recurrence is independent. This consumer is explicitly floating here.
    gate = arrays["evaluation.projected"][:, :mixer.intermediate_size].astype(np.float64)
    raw_scan = arrays["evaluation.raw_scan"].astype(np.float64)
    silu_gate = gate / (1 + np.exp(-gate))
    gated = raw_scan * silu_gate if not config.mamba_norm_before_gate else raw_scan
    grouped = gated.reshape(total, mixer.n_groups, -1)
    rms = grouped / np.sqrt(np.mean(grouped * grouped, axis=-1, keepdims=True) + config.rms_norm_eps)
    norm_reference = rms.reshape(total, -1) * arrays["weight.gated_norm_gamma"]
    if config.mamba_norm_before_gate:
        norm_reference *= silu_gate
    numeric["gated_norm.fp64_reference"] = norm_reference
    c = {name: numeric["evaluation." + name] for name in ("a", "dt", "x", "b", "c", "skip")}
    state_results = []
    for bits in (16, 32):
        unit = calibrated_unit(numeric["calibration.fp64_states"], bits)
        candidate = recurrence(**c, storage_bits=bits, unit=unit)
        numeric[f"S{bits}.codes"] = candidate["codes"]
        numeric[f"S{bits}.states"] = candidate["states"]
        numeric[f"S{bits}.output"] = candidate["output"]
        numeric[f"S{bits}.saturations"] = candidate["saturations"]
        numeric[f"S{bits}.unit"] = np.asarray(unit, np.float64)
        numeric[f"S{bits}.unit_exponent"] = np.asarray(int(math.log2(unit)), np.int64)
        state_results.append({"storage_bits": bits, "unit": unit, "unit_exponent": int(math.log2(unit)),
                              "unit_source": "calibration16_only", "saturations": int(candidate["saturations"].sum()),
                              "candidate_unit_format": "signed INT16 power-of-two exponent,2 bytes/head; NPZ uses int64 witness",
                              "output_error_vs_fp64": metric(candidate["output"], numeric["evaluation.fp64_output"]),
                              "final_state_error_vs_fp64": metric(candidate["states"][-1], numeric["evaluation.fp64_states"][-1]),
                              "bridge": "FP64 conv/SiLU/softplus/exp and coefficient multiplications; integer storage only"})
    # This is a projection experiment, not quantization of all branches or weights.
    projection_indices = np.concatenate((np.arange(4), np.arange(mixer.intermediate_size, mixer.intermediate_size + 4),
        np.arange(2 * mixer.intermediate_size, 2 * mixer.intermediate_size + 4),
        np.arange(mixer.intermediate_size + mixer.conv_dim, mixer.intermediate_size + mixer.conv_dim + 4)))
    w8_results, w8_arrays = _w8a8(arrays["calibration.norm"] * config.ssm_in_multiplier,
                                arrays["evaluation.norm"] * config.ssm_in_multiplier,
                                _np(mixer.in_proj.weight)[projection_indices])
    w8_arrays["projection_output_indices"] = projection_indices
    cfg = config.to_dict()
    report = {"schema": "falcon-h1-bounded-v1", "architecture": "parallel Attention + Mamba2 (not GDN)",
              "model": "tiiuae/Falcon-H1-3B-Instruct", "model_revision": args.revision,
              "source_safetensors": weight_headers(args.weights),
              "reference_dtype": "float32", "source_weights_path": str(Path(args.weights).resolve()),
              "input": {"seed": args.seed, "calibration_tokens": 16, "evaluation_tokens": total,
                        "prefill": args.prefill, "decode": args.decode, "batch": 1, "kind": "fixed disjoint random token IDs; structural diagnostics, not text quality"},
              "native_continuity": continuity, "hybrid_join": join_error, "chunk_continuity": chunk_results,
              "negative_reset": {"chunk": 8, "output_error_vs_continuous": reset_error,
                                 "detected": bool(reset_error["max_abs"] > 1e-5)},
              "state_fp64_vs_native_tokenwise": metric(numeric["evaluation.fp64_states"], arrays["native.head0.states"]),
              "output_fp64_vs_native_tokenwise": metric(numeric["evaluation.fp64_output"], arrays["native.head0.output"]),
              "gated_norm": {"norm_before_gate": config.mamba_norm_before_gate, "groups": mixer.n_groups,
                  "elements": mixer.intermediate_size, "raw_gate_gamma_bytes_fp32": 3 * mixer.intermediate_size * 4,
                  "fp64_reference_vs_native": metric(norm_reference, arrays["evaluation.scan_normed"]),
                  "bridge": "FP64 SiLU, multiply, whole-group sum/sqrt/divide/gamma; native FP32 reference; not integer path"},
              "state_storage_candidates": state_results, "projection_w8a8": w8_results,
              "projection_outputs": {"indices": projection_indices.tolist(), "sections": ["gate_first4", "x_first4", "B_first4", "dt_first4"]},
              "inventory": [costs(cfg, total), costs(cfg, total, state_bits=16, state_format="S16"),
                            costs(cfg, total, state_bits=32, state_format="S32")],
              "limits": ["One actual complete head0 D128xN256; B/C shared by all32 heads. Full-layer initial/final state and complete hybrid branches retained.",
                         "No all-integer nonlinear/recurrence or target timing/PPA proof; state-storage candidates retain FP64 bridges.",
                         "Short B1 diagnostic with calibration/evaluation separation; no application-quality or long-context acceptance.",
                         "Port figures are logical payload/128-bit beats, not a physical schedule; packet headers, scale transport and allocator behavior require a separate matched-resource model."],
              "environment": {"python": platform.python_version(), "numpy": np.__version__, "torch": torch.__version__,
                              "transformers": transformers.__version__, "threads": args.threads, "device": "cpu", "attention": "eager",
                              "modeling_source_sha256": sha(inspect.getfile(modeling)), "cache_source_sha256": sha(inspect.getfile(DynamicCache))},
              "elapsed_seconds": time.time() - started}
    np.savez_compressed(out / "capture.npz", **arrays)
    np.savez_compressed(out / "numeric.npz", **numeric)
    np.savez_compressed(out / "projection.npz", **w8_arrays)
    write_json(out / "config.json", _finite_json(cfg))
    write_json(out / "report.json", report)
    binding = json.loads(Path(args.binding).read_text(encoding="utf-8")) if args.binding else {"commit": "unbound", "files": []}
    artifacts = [{"path": p.name, "bytes": p.stat().st_size, "sha256": sha(p), "kind": "npz" if p.suffix == ".npz" else "json"}
                 for p in sorted(out.iterdir()) if p.is_file()]
    write_json(out / "manifest.json", {"schema": "falcon-h1-bounded-v1", "source": binding,
               "producer_sha256": sha(__file__), "artifacts": artifacts,
               "claims": "FP32 native continuity, independent FP64 recurrence and integer-state-storage diagnostics; not full integer hardware."})
    print(json.dumps({"out": str(out), "manifest_sha256": sha(out / "manifest.json"), "elapsed_seconds": report["elapsed_seconds"]}))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--weights", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--binding")
    p.add_argument("--revision", default="unverified")
    p.add_argument("--threads", type=int, default=8)
    p.add_argument("--prefill", type=int, default=64)
    p.add_argument("--decode", type=int, default=8)
    p.add_argument("--seed", type=int, default=7002)
    args = p.parse_args()
    if not (1 <= args.threads <= 16 and args.prefill == 64 and args.decode == 8):
        p.error("frozen bounded protocol: threads1..16, prefill64/decode8")
    capture(args)


if __name__ == "__main__":
    main()
