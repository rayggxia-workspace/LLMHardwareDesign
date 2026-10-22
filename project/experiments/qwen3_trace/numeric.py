"""Teacher-forced, FP32 CPU cache equivalence checks; no hooks or timing claims.

This module stores metrics and hashes, never model activations or historical cache
copies.  The two negative controls own fresh caches.  A failed negative control
means the intended corruption was not demonstrated, rather than a model failure.
"""

from __future__ import annotations

import hashlib
import math
from typing import Any


PROFILE = "qwen3-fp32-cpu-cache-equivalence-v1"


def _tensor_metrics(actual: Any, reference: Any, atol: float, rtol: float) -> dict:
    import torch

    result = {
        "shape": list(actual.shape),
        "reference_shape": list(reference.shape),
        "dtype": str(actual.dtype),
        "reference_dtype": str(reference.dtype),
        "finite": bool(torch.isfinite(actual).all() and torch.isfinite(reference).all()),
        "max_abs": None,
        "relative_l2": None,
        "match": False,
    }
    if actual.shape != reference.shape or not result["finite"]:
        return result
    difference = actual.detach().to(torch.float64) - reference.detach().to(torch.float64)
    error_norm = float(torch.linalg.vector_norm(difference).item())
    reference_norm = float(torch.linalg.vector_norm(reference.detach().to(torch.float64)).item())
    result["max_abs"] = float(difference.abs().max().item()) if difference.numel() else 0.0
    # A zero reference has no relative error scale: report None unless exact.
    result["relative_l2"] = error_norm / reference_norm if reference_norm else (0.0 if not error_norm else None)
    result["match"] = actual.dtype == reference.dtype == torch.float32 and bool(
        torch.allclose(actual, reference, atol=atol, rtol=rtol, equal_nan=False)
    )
    return result


def _top1(tensor: Any) -> dict:
    import torch

    flat = tensor.detach().reshape(-1)
    if not flat.numel() or not bool(torch.isfinite(flat).all()):
        return {"id": None, "value": None, "gap": None}
    values, indices = torch.topk(flat, k=min(2, flat.numel()))
    return {
        "id": int(indices[0].item()),
        "value": float(values[0].item()),
        "gap": float((values[0].double() - values[1].double()).item()) if values.numel() > 1 else None,
    }


def _hash_tensor(tensor: Any) -> str:
    # The dtype and shape are checked separately.  numpy preserves raw FP32 bits,
    # including signed zero, unlike numeric equality or allclose.
    raw = tensor.detach().contiguous().numpy().tobytes(order="C")
    return hashlib.sha256(raw).hexdigest()


def _cache_snapshot(cache: Any, prefix_length: int) -> list[dict]:
    records = []
    for index, layer in enumerate(cache.layers):
        for field in ("keys", "values"):
            tensor = getattr(layer, field)
            if tensor is None or tensor.ndim != 4 or tensor.shape[-2] < prefix_length:
                raise ValueError(f"layer {index} {field}: missing/short/non-4D cache prefix")
            prefix = tensor[..., :prefix_length, :]
            records.append({
                "layer": index, "field": field, "prefix_length": prefix_length,
                "shape": list(prefix.shape), "dtype": str(prefix.dtype),
                "sha256": _hash_tensor(prefix),
            })
    return records


def _prefix_integrity(before: list[dict], cache: Any) -> dict:
    details = []
    for old in before:
        result = dict(old)
        try:
            tensor = getattr(cache.layers[old["layer"]], old["field"])
            if tensor is None or tensor.ndim != 4 or tensor.shape[-2] < old["prefix_length"]:
                raise ValueError("missing/short/non-4D cache prefix")
            prefix = tensor[..., :old["prefix_length"], :]
            result["after_sha256"] = _hash_tensor(prefix)
            result["unchanged"] = (
                list(prefix.shape) == old["shape"]
                and str(prefix.dtype) == old["dtype"]
                and result["after_sha256"] == old["sha256"]
            )
        except Exception as exc:
            result["unchanged"] = False
            result["error"] = f"{type(exc).__name__}: {exc}"
        details.append(result)
    return {"unchanged": bool(details) and all(x["unchanged"] for x in details), "fields": details}


def _layout(model: Any) -> dict:
    config = model.config
    heads = int(config.num_attention_heads)
    return {
        "layers": int(config.num_hidden_layers),
        "kv_heads": int(getattr(config, "num_key_value_heads", heads)),
        "head_dim": int(getattr(config, "head_dim", config.hidden_size // heads)),
    }


def _new_cache(model: Any, layout: dict) -> Any:
    from transformers import DynamicCache

    cache = DynamicCache(config=model.config)
    if len(cache.layers) != layout["layers"]:
        raise ValueError("DynamicCache layer count differs from model configuration")
    if any(bool(getattr(layer, "is_sliding", False)) for layer in cache.layers):
        raise ValueError("this profile supports full-attention cache layers only")
    if any(getattr(layer, name) is not None for layer in cache.layers for name in ("keys", "values")):
        raise ValueError("a newly constructed DynamicCache is already populated")
    return cache


def _compare_caches(actual: Any, reference: Any, length: int, layout: dict, atol: float, rtol: float) -> dict:
    import torch

    fields = []
    errors = []
    expected = [1, layout["kv_heads"], length, layout["head_dim"]]
    if len(actual.layers) != layout["layers"] or len(reference.layers) != layout["layers"]:
        errors.append("cache layer count differs from configuration")
    for index in range(layout["layers"]):
        for field in ("keys", "values"):
            record = {"layer": index, "field": field, "expected_shape": expected}
            try:
                left = getattr(actual.layers[index], field)
                right = getattr(reference.layers[index], field)
                if left is None or right is None:
                    raise ValueError("uninitialized cache")
                record.update(_tensor_metrics(left, right, atol, rtol))
                record["layout_valid"] = (
                    list(left.shape) == list(right.shape) == expected
                    and left.device.type == right.device.type == "cpu"
                    and left.dtype == right.dtype == torch.float32
                    and actual.get_seq_length(index) == reference.get_seq_length(index) == length
                )
                record["match"] = record["match"] and record["layout_valid"]
            except Exception as exc:
                record.update(match=False, finite=False, layout_valid=False,
                              error=f"{type(exc).__name__}: {exc}")
            fields.append(record)
    return {
        "match": not errors and all(field["match"] for field in fields),
        "finite": all(field["finite"] for field in fields),
        "errors": errors, "fields": fields,
    }


def _comparison(logits: Any, cache: Any, reference_logits: Any, reference_cache: Any,
                length: int, layout: dict, atol: float, rtol: float) -> dict:
    logit_metrics = _tensor_metrics(logits, reference_logits, atol, rtol)
    logit_metrics["top1"] = _top1(logits)
    logit_metrics["reference_top1"] = _top1(reference_logits)
    logit_metrics["top1_agrees"] = logit_metrics["top1"]["id"] == logit_metrics["reference_top1"]["id"]
    kv = _compare_caches(cache, reference_cache, length, layout, atol, rtol)
    return {"match": logit_metrics["match"] and kv["match"],
            "finite": logit_metrics["finite"] and kv["finite"], "logits": logit_metrics, "cache": kv}


def _call(model: Any, ids: Any, cache: Any, past_length: int, *, wrong_position: bool = False) -> Any:
    import torch

    length = ids.shape[1]
    positions = torch.arange(past_length, past_length + length, dtype=torch.long, device="cpu")
    outputs = model(
        input_ids=ids,
        attention_mask=torch.ones((1, past_length + length), dtype=torch.long, device="cpu"),
        position_ids=torch.zeros((1, length), dtype=torch.long, device="cpu") if wrong_position else positions.unsqueeze(0),
        cache_position=positions,
        past_key_values=cache,
        use_cache=True,
        return_dict=True,
        logits_to_keep=1,
        output_attentions=False,
        output_hidden_states=False,
    )
    if outputs.past_key_values is not cache:
        raise ValueError("model returned a different cache object")
    if (outputs.logits.ndim != 3 or list(outputs.logits.shape[:2]) != [1, 1]
            or outputs.logits.dtype != torch.float32 or outputs.logits.device.type != "cpu"):
        raise ValueError("expected FP32 CPU last-token logits with [1,1,vocabulary] layout")
    return outputs.logits[:, -1, :]


def _validate(model: Any, input_ids: Any, prefix: int, steps: int, atol: float, rtol: float) -> dict:
    import torch

    if isinstance(prefix, bool) or not isinstance(prefix, int) or prefix < 2:
        raise ValueError("prefix must be an integer >= 2 (two nonempty chunks)")
    if isinstance(steps, bool) or not isinstance(steps, int) or steps < 1:
        raise ValueError("steps must be a positive integer")
    for name, value in (("atol", atol), ("rtol", rtol)):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
            raise ValueError(f"{name} must be finite and nonnegative")
    if (not isinstance(input_ids, torch.Tensor) or input_ids.ndim != 2 or input_ids.shape[0] != 1
            or input_ids.shape[1] < prefix + steps or input_ids.dtype != torch.long
            or input_ids.device.type != "cpu"):
        raise ValueError("input_ids must be CPU int64 [1,T], T >= prefix + steps")
    if model.training:
        raise ValueError("model must already be in eval mode")
    for name, tensor in list(model.named_parameters()) + list(model.named_buffers()):
        if tensor.device.type != "cpu" or (tensor.is_floating_point() and tensor.dtype != torch.float32):
            raise ValueError(f"model tensor {name!r} is not CPU/FP32")
    hook_names = ("_forward_hooks", "_forward_pre_hooks", "_backward_hooks", "_backward_pre_hooks")
    for name, module in model.named_modules():
        if any(getattr(module, hook, {}) for hook in hook_names):
            raise ValueError(f"model module {name!r} has registered hooks")
    from torch.nn.modules import module as module_api
    if any(getattr(module_api, name, {}) for name in (
        "_global_forward_hooks", "_global_forward_pre_hooks", "_global_backward_hooks", "_global_backward_pre_hooks"
    )):
        raise ValueError("global module hooks are registered")
    layout = _layout(model)
    if any(value < 1 for value in layout.values()) or layout["kv_heads"] < 2:
        raise ValueError("profile requires positive dimensions and at least two KV heads for the swap control")
    return layout


def run_numeric(model: Any, input_ids: Any, prefix: int = 32, steps: int = 16,
                atol: float = 1e-4, rtol: float = 1e-4) -> dict:
    """Return JSON-safe per-step evidence, including failures and negative controls.

    Extra supplied tokens are ignored and counted. The default chunk lengths are
    exactly 16+16. Every full-prefix reference uses a new, independently populated
    cache. No model hooks are installed or removed, and model mode/dtype are not
    altered. This checks numerical/cache semantics, not hardware performance.
    """
    def safe_parameter(value: Any) -> Any:
        if isinstance(value, (bool, int, str)) or value is None:
            return value
        if isinstance(value, float) and math.isfinite(value):
            return value
        return repr(value)

    result = {
        "profile": PROFILE, "status": "FAIL",
        "tolerances": {"atol": safe_parameter(atol), "rtol": safe_parameter(rtol),
                       "rule": "abs(a-r) <= atol + rtol*abs(r), every element"},
        "reference": "fresh DynamicCache and full prefix at every compared length",
        "execution": "CPU FP32 eval inference_mode; teacher-forced; no hooks; no timing claim",
        "interpretation": "tolerance equivalence for fixed supplied tokens; top1/gap are diagnostics, not a greedy-generation guarantee",
        "positive_paths": {"single_prefill": [], "chunked_prefill": []},
        "negative_controls": [], "failures": [],
        "totals": {"positive_checks": 0, "positive_passed": 0, "negative_controls": 0,
                   "negative_passed": 0, "failure_records": 0},
    }
    try:
        import torch
        import transformers

        layout = _validate(model, input_ids, prefix, steps, atol, rtol)
        result["setup"] = {
            "prefix": prefix, "steps": steps, "chunk_lengths": [prefix // 2, prefix - prefix // 2],
            "supplied_tokens": input_ids.shape[1], "used_tokens": prefix + steps,
            "ignored_tokens": input_ids.shape[1] - prefix - steps, "cache_layout": layout,
            "torch_version": torch.__version__, "transformers_version": transformers.__version__,
            "cpu_threads": torch.get_num_threads(), "cpu_interop_threads": torch.get_num_interop_threads(),
            "float32_matmul_precision": torch.get_float32_matmul_precision(),
            "autocast": "CPU autocast explicitly disabled for all forwards",
            "attention_implementation": getattr(model.config, "_attn_implementation", None),
            "logits_projection": "logits_to_keep=1; all new-token hidden states and KV are still computed",
            "input_ids_sha256": _hash_tensor(input_ids[:, :prefix + steps]),
        }
        caches = {name: _new_cache(model, layout) for name in result["positive_paths"]}
    except Exception as exc:
        # Even invalid setup is an evidence object rather than a discarded run.
        result["failures"].append({"stage": "setup", "error": f"{type(exc).__name__}: {exc}"})
        result["totals"]["failure_records"] = 1
        return result

    def reference(length: int) -> tuple[Any, Any]:
        cache = _new_cache(model, layout)
        logits = _call(model, input_ids[:, :length], cache, 0)
        return logits, cache

    def record_failure(stage: str, exc: Exception, **context: Any) -> None:
        result["failures"].append({"stage": stage, **context, "error": f"{type(exc).__name__}: {exc}"})

    alive = {name: True for name in caches}

    def step_path(name: str, start: int, end: int, ref: tuple[Any, Any] | None) -> None:
        record = {"input_start": start, "input_end": end, "prefix_length": end, "passed": False}
        result["positive_paths"][name].append(record)
        if not alive[name]:
            record["error"] = "blocked by an earlier execution error in this path"
            return
        try:
            before = _cache_snapshot(caches[name], start) if start else None
            logits = _call(model, input_ids[:, start:end], caches[name], start)
            if before is not None:
                record["prefix_integrity"] = _prefix_integrity(before, caches[name])
            else:
                record["prefix_integrity"] = {"unchanged": True, "fields": [], "empty_prefix": True}
            if ref is None:
                record["error"] = "full-prefix reference failed at this length"
                return
            record["comparison"] = _comparison(logits, caches[name], ref[0], ref[1], end, layout, atol, rtol)
            record["passed"] = record["prefix_integrity"]["unchanged"] and record["comparison"]["match"]
            if not record["passed"]:
                result["failures"].append({"stage": "positive_comparison", "path": name, "prefix_length": end})
        except Exception as exc:
            alive[name] = False
            record["error"] = f"{type(exc).__name__}: {exc}"
            record_failure("positive_execution", exc, path=name, prefix_length=end)

    def get_reference(length: int) -> tuple[Any, Any] | None:
        try:
            return reference(length)
        except Exception as exc:
            record_failure("reference_execution", exc, prefix_length=length)
            return None

    with torch.inference_mode(), torch.autocast(device_type="cpu", enabled=False):
        split = prefix // 2
        ref = get_reference(split)
        step_path("chunked_prefill", 0, split, ref)
        del ref
        ref = get_reference(prefix)
        step_path("single_prefill", 0, prefix, ref)
        step_path("chunked_prefill", split, prefix, ref)
        del ref
        for offset in range(steps):
            length = prefix + offset + 1
            ref = get_reference(length)
            for name in caches:
                step_path(name, length - 1, length, ref)
            del ref
        # Release positives before controls; no reference/cache history is kept.
        del caches

        for kind in ("wrong_decode_position_zero", "swap_one_layer_kv_heads"):
            control = {"name": kind, "passed": False, "detected": False, "prefix_length": prefix + 1}
            result["negative_controls"].append(control)
            try:
                cache = _new_cache(model, layout)
                initial_logits = _call(model, input_ids[:, :prefix], cache, 0)
                base_logits, base_cache = reference(prefix)
                control["baseline"] = _comparison(initial_logits, cache, base_logits, base_cache, prefix, layout, atol, rtol)
                del base_logits, base_cache, initial_logits
                if kind == "swap_one_layer_kv_heads":
                    layer_index = layout["layers"] // 2
                    layer = cache.layers[layer_index]
                    permutation = torch.arange(layout["kv_heads"], dtype=torch.long)
                    permutation[0], permutation[1] = 1, 0
                    before_mutation = _cache_snapshot(cache, prefix)
                    # index_select allocates independent tensors; this cache has
                    # never been shared with a positive or reference invocation.
                    layer.keys = layer.keys.index_select(1, permutation)
                    layer.values = layer.values.index_select(1, permutation)
                    after_mutation = _cache_snapshot(cache, prefix)
                    control["mutation"] = {
                        "layer": layer_index, "heads": [0, 1], "fields": ["keys", "values"],
                        "changed_prefix_hashes": [
                            {"layer": old["layer"], "field": old["field"],
                             "before_sha256": old["sha256"], "after_sha256": new["sha256"]}
                            for old, new in zip(before_mutation, after_mutation) if old["sha256"] != new["sha256"]
                        ],
                    }
                else:
                    control["mutation"] = {"position_ids": [[0]], "cache_position": [prefix],
                                           "correct_position_ids": [[prefix]]}
                before = _cache_snapshot(cache, prefix)
                logits = _call(model, input_ids[:, prefix:prefix + 1], cache, prefix,
                               wrong_position=(kind == "wrong_decode_position_zero"))
                control["prefix_integrity"] = _prefix_integrity(before, cache)
                ref_logits, ref_cache = reference(prefix + 1)
                comparison = _comparison(logits, cache, ref_logits, ref_cache, prefix + 1, layout, atol, rtol)
                control["comparison"] = comparison
                changed = []
                if not comparison["logits"]["match"]:
                    changed.append("logits")
                changed.extend(f"layer_{field['layer']}.{field['field']}" for field in comparison["cache"]["fields"]
                               if not field["match"])
                control["changed_fields"] = changed
                # Nonfinite values or malformed cache layouts are failures, not
                # successful detections of the controlled semantic error.
                layouts_valid = all(field["layout_valid"] for field in comparison["cache"]["fields"])
                control["detected"] = bool(changed) and comparison["finite"] and layouts_valid
                mutation_valid = kind != "swap_one_layer_kv_heads" or len(control["mutation"]["changed_prefix_hashes"]) == 2
                control["passed"] = (
                    control["baseline"]["match"] and control["detected"]
                    and control["prefix_integrity"]["unchanged"] and mutation_valid
                )
                del cache, logits, ref_logits, ref_cache
            except Exception as exc:
                control["error"] = f"{type(exc).__name__}: {exc}"
                record_failure("negative_execution", exc, control=kind)
            if not control["passed"]:
                result["failures"].append({"stage": "negative_control", "control": kind})

    positive_records = [record for records in result["positive_paths"].values() for record in records]
    result["totals"] = {
        "positive_checks": len(positive_records),
        "positive_passed": sum(record["passed"] for record in positive_records),
        "negative_controls": len(result["negative_controls"]),
        "negative_passed": sum(record["passed"] for record in result["negative_controls"]),
        "failure_records": len(result["failures"]),
    }
    result["status"] = "PASS" if (not result["failures"] and all(record["passed"] for record in positive_records)
                                     and all(record["passed"] for record in result["negative_controls"])) else "FAIL"
    return result
