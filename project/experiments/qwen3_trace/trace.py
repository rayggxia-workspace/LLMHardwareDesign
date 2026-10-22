"""Observe real eager-Qwen3 boundaries without replacing arithmetic.

The module-level eager function is temporarily wrapped in this single-process
experiment. Do not use this observer with concurrent model calls.
"""
from contextlib import contextmanager
import copy
import hashlib
import torch
from transformers.cache_utils import DynamicCache
from transformers.models.qwen3 import modeling_qwen3


def tensor_record(tensor):
    return {
        "shape": list(tensor.shape), "dtype": str(tensor.dtype),
        "numel": tensor.numel(), "itemsize": tensor.element_size(),
        "logical_bytes": tensor.numel() * tensor.element_size(),
        "storage_bytes": tensor.untyped_storage().nbytes(),
        "stride": list(tensor.stride()), "storage_offset": tensor.storage_offset(),
        "is_contiguous": tensor.is_contiguous(),
    }


def compare(actual, expected, atol, rtol):
    if actual.shape != expected.shape:
        return {"pass": False, "reason": "shape mismatch"}
    a, b = actual.detach().double(), expected.detach().double()
    finite = bool(torch.isfinite(a).all() and torch.isfinite(b).all())
    delta = (a - b).abs()
    return {
        "pass": finite and bool(torch.allclose(a, b, atol=atol, rtol=rtol)),
        "finite": finite, "max_abs": float(delta.max()) if finite else None,
        "relative_l2": (float(torch.linalg.vector_norm(a - b) /
                              torch.linalg.vector_norm(b).clamp_min(1e-30)) if finite else None),
    }


class Observer:
    def __init__(self, model, selected_layers):
        self.model = model
        self.selected = set(selected_layers)
        self.events = []
        self.samples = {}
        self.cache_matches = []
        self.active = False

    def record(self, layer, stage, tensor, sequence_axis=1):
        self.events.append({"layer": layer, "stage": stage, **tensor_record(tensor)})
        if layer in self.selected:
            sample = tensor.select(sequence_axis, tensor.shape[sequence_axis] - 1)
            self.samples[f"{layer}/{stage}"] = sample.detach().clone()

    @contextmanager
    def capture(self, cache):
        if self.active:
            raise RuntimeError("nested/concurrent observation is unsupported")
        self.active = True
        self.events, self.samples, self.cache_matches = [], {}, []
        handles = []
        original_eager = modeling_qwen3.eager_attention_forward

        def eager(module, query, key, value, *args, **kwargs):
            layer = module.layer_idx
            self.record(layer, "attention.query_post_rope", query, 2)
            self.record(layer, "attention.key_cached_post_rope", key, 2)
            self.record(layer, "attention.value_cached", value, 2)
            state = cache.layers[layer]
            mask = args[0] if args else kwargs.get("attention_mask")
            query_length, total_length = query.shape[-2], key.shape[-2]
            if mask is None:
                mask_record = {"present": False, "causal_contract": query_length == 1}
            else:
                # Record the backend's real additive mask, not a replacement.
                allowed = mask == 0
                expected_allowed = (torch.arange(total_length).unsqueeze(0) <=
                    torch.arange(total_length - query_length, total_length).unsqueeze(1))
                expected_allowed = expected_allowed.unsqueeze(0).unsqueeze(0)
                causal = (list(mask.shape) == [1, 1, query_length, total_length]
                          and torch.equal(allowed, expected_allowed)
                          and bool((mask[~allowed] < -1e20).all()))
                mask_record = {"present": True, **tensor_record(mask),
                    "sha256": hashlib.sha256(mask.detach().contiguous().numpy().tobytes()).hexdigest(),
                    "allowed_per_query": allowed.sum(dim=-1).reshape(-1).tolist(),
                    "causal_contract": bool(causal)}
            self.cache_matches.append({
                "layer": layer,
                "key_equal": bool(torch.equal(key, state.keys)),
                "value_equal": bool(torch.equal(value, state.values)),
                "key_storage_shared": key.data_ptr() == state.keys.data_ptr(),
                "value_storage_shared": value.data_ptr() == state.values.data_ptr(),
                "actual_additive_mask": mask_record,
            })
            output = original_eager(module, query, key, value, *args, **kwargs)
            self.record(layer, "attention.context_before_o_proj", output[0])
            self.events.append({"layer": layer, "stage": "attention.probabilities",
                                **tensor_record(output[1])})
            return output

        def post_hook(layer, stage):
            def hook(_module, _args, output):
                self.record(layer, stage, output)
            return hook

        def pre_hook(layer, stage):
            def hook(_module, args):
                self.record(layer, stage, args[0])
            return hook

        try:
            for i, layer in enumerate(self.model.model.layers):
                modules = {
                    "q_projection_pre_norm_rope": layer.self_attn.q_proj,
                    "k_projection_pre_norm_rope": layer.self_attn.k_proj,
                    "v_projection": layer.self_attn.v_proj,
                    "attention_output": layer.self_attn.o_proj,
                    "ffn_gate_projection": layer.mlp.gate_proj,
                    "ffn_up_projection": layer.mlp.up_proj,
                    "ffn_output": layer.mlp.down_proj,
                    "decoder_output": layer,
                }
                for stage, module in modules.items():
                    handles.append(module.register_forward_hook(post_hook(i, stage)))
                handles.append(layer.mlp.down_proj.register_forward_pre_hook(
                    pre_hook(i, "swiglu_product_before_down_proj")))
            modeling_qwen3.eager_attention_forward = eager
            yield self
        finally:
            modeling_qwen3.eager_attention_forward = original_eager
            for handle in handles:
                handle.remove()
            self.active = False


def forward(model, ids, cache, start, end):
    return model(
        input_ids=ids[:, start:end], past_key_values=cache, use_cache=True,
        attention_mask=torch.ones((1, end), dtype=torch.long),
        position_ids=torch.arange(start, end).unsqueeze(0),
        cache_position=torch.arange(start, end), logits_to_keep=1,
    )


def audit_events(events, config, query_length, total_length):
    """Independently bind stage labels to observed shapes for every layer."""
    h, f, q, kv, d = (config.hidden_size, config.intermediate_size,
                      config.num_attention_heads, config.num_key_value_heads,
                      config.head_dim)
    expected = {
        "q_projection_pre_norm_rope": [1, query_length, q * d],
        "k_projection_pre_norm_rope": [1, query_length, kv * d],
        "v_projection": [1, query_length, kv * d],
        "attention_output": [1, query_length, h],
        "ffn_gate_projection": [1, query_length, f],
        "ffn_up_projection": [1, query_length, f],
        "ffn_output": [1, query_length, h],
        "decoder_output": [1, query_length, h],
        "swiglu_product_before_down_proj": [1, query_length, f],
        "attention.query_post_rope": [1, q, query_length, d],
        "attention.key_cached_post_rope": [1, kv, total_length, d],
        "attention.value_cached": [1, kv, total_length, d],
        "attention.context_before_o_proj": [1, query_length, q, d],
        "attention.probabilities": [1, q, query_length, total_length],
    }
    seen = set()
    failures = []
    for event in events:
        key = (event["layer"], event["stage"])
        shape = expected.get(event["stage"])
        product = 1
        for dim in event["shape"]:
            product *= dim
        valid = (key not in seen and 0 <= event["layer"] < config.num_hidden_layers
                 and shape == event["shape"] and event["dtype"] == "torch.float32"
                 and event["itemsize"] == 4 and event["numel"] == product
                 and event["logical_bytes"] == 4 * product)
        if not valid:
            failures.append({"key": list(key), "reason": "shape/stage/bytes/duplicate"})
        seen.add(key)
    required = {(i, stage) for i in range(config.num_hidden_layers) for stage in expected}
    if seen != required:
        failures.append({"reason": "missing/unexpected events", "missing": len(required - seen)})
    return {"pass": not failures, "events": len(events), "failures": failures}


def run_trace(model, ids, prefix, steps, selected_layers, atol, rtol):
    records, all_events, failures = [], [], []
    observer = Observer(model, selected_layers)
    for schedule, chunks in (("single_prefill", [prefix]),
                             ("chunked_prefill", [prefix // 2, prefix - prefix // 2])):
        cache = DynamicCache(config=model.config)
        unobserved_cache = DynamicCache(config=model.config)
        cursor = 0
        for call, width in enumerate(chunks + [1] * steps):
            end = cursor + width
            baseline = forward(model, ids, unobserved_cache, cursor, end)
            with observer.capture(cache):
                actual = forward(model, ids, cache, cursor, end)
            events = observer.events
            samples = observer.samples
            cache_matches = observer.cache_matches
            validation = audit_events(events, model.config, width, end)
            instrumentation = compare(actual.logits, baseline.logits, atol, rtol)
            reference_cache = DynamicCache(config=model.config)
            with observer.capture(reference_cache):
                reference = forward(model, ids, reference_cache, 0, end)
            reference_samples = observer.samples
            boundary_comparisons = {
                key: compare(value, reference_samples[key], atol, rtol)
                for key, value in samples.items()
            }
            observed_cache_checks = []
            logical_kv, allocated_kv = 0, 0
            for i, state in enumerate(cache.layers):
                plain = unobserved_cache.layers[i]
                logical_kv += sum(t.numel() * t.element_size() for t in (state.keys, state.values))
                allocated_kv += sum(t.untyped_storage().nbytes() for t in (state.keys, state.values))
                observed_cache_checks.append({"layer": i,
                    "key_equal": bool(torch.equal(state.keys, plain.keys)),
                    "value_equal": bool(torch.equal(state.values, plain.values))})
            expected_kv = (2 * model.config.num_hidden_layers * model.config.num_key_value_heads
                           * model.config.head_dim * end * 4)
            reference_logits = compare(actual.logits, reference.logits, atol, rtol)
            good = (validation["pass"] and instrumentation["pass"]
                    and reference_logits["pass"]
                    and all(c["pass"] for c in boundary_comparisons.values())
                    and all(c["key_equal"] and c["value_equal"]
                            and c["actual_additive_mask"]["causal_contract"] for c in cache_matches)
                    and all(c["key_equal"] and c["value_equal"] for c in observed_cache_checks)
                    and logical_kv == expected_kv)
            record = {"schedule": schedule, "call": call, "start": cursor, "end": end,
                      "query_tokens": width, "pass": good, "event_validation": validation,
                      "instrumentation_logits": instrumentation,
                      "reference_logits": reference_logits,
                      "boundary_comparisons": boundary_comparisons,
                      "attention_cache_binding": cache_matches,
                      "instrumentation_cache": observed_cache_checks,
                      "logical_kv_bytes": logical_kv, "storage_kv_bytes": allocated_kv,
                      "expected_logical_kv_bytes": expected_kv}
            records.append(record)
            if not good:
                failures.append({"schedule": schedule, "call": call, "end": end})
            all_events.extend({"schedule": schedule, "call": call, "start": cursor,
                               "end": end, **event} for event in events)
            cursor = end
    first = [event for event in all_events if event["schedule"] == "single_prefill" and event["call"] == 0]
    mutations = {"missing_event": copy.deepcopy(first[:-1]),
                 "wrong_kv_head_count": copy.deepcopy(first),
                 "raw_projection_mislabeled_as_cache": copy.deepcopy(first)}
    for event in mutations["wrong_kv_head_count"]:
        if event["stage"] == "attention.key_cached_post_rope":
            event["shape"][1] = model.config.num_attention_heads
            break
    for event in mutations["raw_projection_mislabeled_as_cache"]:
        if event["stage"] == "k_projection_pre_norm_rope":
            event["stage"] = "attention.key_cached_post_rope"
            break
    negative_controls = [{"name": name, "detected": not audit_events(
        events, model.config, prefix, prefix)["pass"]} for name, events in mutations.items()]
    if not all(control["detected"] for control in negative_controls):
        failures.append({"negative_control": "undetected"})
    return {"status": "PASS" if not failures else "FAIL", "calls": records,
            "failures": failures, "events": all_events, "negative_controls": negative_controls,
            "scope": "Observed logical tensors; event-byte sums are not resident memory or hardware traffic."}
