"""Small-shape algebra checks, independent of the project's cost ledger.

No official checkpoint, trained-model quality, cycle timing, memory traffic,
hardware precision, backward pass or PPA is evaluated by this module.
Arrays use token-major [T,H,D]; GQA heads share KV in contiguous groups.
"""

import hashlib
import json
from pathlib import Path
import numpy as np


def _arrays(*values):
    arrays = [np.asarray(value) for value in values]
    if any(array.dtype not in (np.dtype("float32"), np.dtype("float64")) for array in arrays):
        raise ValueError("only explicit float32/float64 inputs are supported")
    if len({array.dtype for array in arrays}) != 1:
        raise ValueError("all operands must have the same dtype")
    if any(not np.isfinite(array).all() for array in arrays):
        raise ValueError("nonfinite input")
    return arrays


def _silu(x):
    positive = x >= 0
    result = np.empty_like(x)
    result[positive] = x[positive] / (1 + np.exp(-x[positive]))
    exp_x = np.exp(x[~positive])
    result[~positive] = x[~positive] * exp_x / (1 + exp_x)
    return result


def _swiglu_inputs(x, wg, wu, wd):
    x, wg, wu, wd = _arrays(x, wg, wu, wd)
    if (any(array.ndim != 2 for array in (x, wg, wu, wd)) or wg.shape != wu.shape
            or x.shape[1] != wg.shape[0] or wg.shape[1] != wd.shape[0]
            or min(*x.shape, *wg.shape, *wd.shape) < 1):
        raise ValueError("incompatible SwiGLU shapes")
    return x, wg, wu, wd


def swiglu_materialized(x, wg, wu, wd):
    x, wg, wu, wd = _swiglu_inputs(x, wg, wu, wd)
    return (_silu(x @ wg) * (x @ wu)) @ wd


def swiglu_tiled(x, wg, wu, wd, hidden_tile=4):
    x, wg, wu, wd = _swiglu_inputs(x, wg, wu, wd)
    if type(hidden_tile) is not int or hidden_tile < 1:
        raise ValueError("hidden_tile must be a positive integer")
    output = np.zeros((x.shape[0], wd.shape[1]), dtype=x.dtype)
    for start in range(0, wg.shape[1], hidden_tile):
        stop = min(start + hidden_tile, wg.shape[1])
        gate = _silu(x @ wg[:, start:stop])
        up = x @ wu[:, start:stop]
        output += (gate * up) @ wd[start:stop]
    return output


def _positions(query_count, key_count, query_offset):
    if (type(query_offset) is not int or query_offset < 0
            or query_offset + query_count > key_count):
        raise ValueError("query_offset must locate the query suffix inside the KV sequence")
    return np.arange(query_count) + query_offset


def _softmax(scores, query_offset):
    # Reference always builds the complete score matrix and mask.
    qpos = _positions(scores.shape[0], scores.shape[-1], query_offset)
    mask = np.arange(scores.shape[-1])[None, :] <= qpos[:, None]
    masked = np.where(mask[:, None, :], scores, -np.inf)
    maxima = np.max(masked, axis=-1, keepdims=True)
    exponentials = np.exp(masked - maxima)
    return exponentials / np.sum(exponentials, axis=-1, keepdims=True)


def _gqa_inputs(q, k, v, query_offset):
    q, k, v = _arrays(q, k, v)
    if (any(array.ndim != 3 for array in (q, k, v))
            or k.shape[:2] != v.shape[:2] or q.shape[-1] != k.shape[-1]
            or min(*q.shape, *k.shape, *v.shape) < 1 or q.shape[1] % k.shape[1]):
        raise ValueError("incompatible GQA shapes or head grouping")
    _positions(q.shape[0], k.shape[0], query_offset)
    return q, k, v


def gqa_full(q, k, v, *, query_offset=0):
    q, k, v = _gqa_inputs(q, k, v, query_offset)
    group_size = q.shape[1] // k.shape[1]
    # Reference uses physical replication; streaming below uses head indexing.
    expanded_k = np.repeat(k, group_size, axis=1)
    expanded_v = np.repeat(v, group_size, axis=1)
    scores = np.einsum("qhd,khd->qhk", q, expanded_k) / np.asarray(np.sqrt(q.shape[-1]), dtype=q.dtype)
    return np.einsum("qhk,khd->qhd", _softmax(scores, query_offset), expanded_v)


def gqa_streaming(q, k, v, *, query_offset=0, query_tile=2, key_tile=4):
    q, k, v = _gqa_inputs(q, k, v, query_offset)
    if any(type(tile) is not int or tile < 1 for tile in (query_tile, key_tile)):
        raise ValueError("tile sizes must be positive integers")
    output = np.empty((q.shape[0], q.shape[1], v.shape[-1]), dtype=q.dtype)
    head_map = np.arange(q.shape[1]) // (q.shape[1] // k.shape[1])
    scale = np.asarray(np.sqrt(q.shape[-1]), dtype=q.dtype)
    for qstart in range(0, q.shape[0], query_tile):
        qend = min(qstart + query_tile, q.shape[0])
        qt = q[qstart:qend]
        maximum = np.full(qt.shape[:2], -np.inf, dtype=q.dtype)
        normalizer = np.zeros(qt.shape[:2], dtype=q.dtype)
        accumulator = np.zeros((*qt.shape[:2], v.shape[-1]), dtype=q.dtype)
        qpositions = np.arange(qstart, qend) + query_offset
        for start in range(0, k.shape[0], key_tile):
            stop = min(start + key_tile, k.shape[0])
            keys, values = k[start:stop, head_map], v[start:stop, head_map]
            scores = np.einsum("qhd,khd->qhk", qt, keys) / scale
            if not np.isfinite(scores).all():
                raise ValueError("score overflow")
            permitted = np.arange(start, stop)[None, :] <= qpositions[:, None]
            scores = np.where(permitted[:, None, :], scores, -np.inf)
            new_maximum = np.maximum(maximum, scores.max(axis=-1))
            factor = np.zeros_like(maximum)
            existing = np.isfinite(maximum)
            factor[existing] = np.exp(maximum[existing] - new_maximum[existing])
            safe_maximum = np.where(np.isfinite(new_maximum), new_maximum, 0)
            probabilities = np.exp(scores - safe_maximum[..., None])
            accumulator = accumulator * factor[..., None] + np.einsum("qhk,khd->qhd", probabilities, values)
            normalizer = normalizer * factor + probabilities.sum(axis=-1)
            maximum = new_maximum
        if np.any(normalizer <= 0):
            raise ValueError("attention row has no unmasked key")
        output[qstart:qend] = accumulator / normalizer[..., None]
    return output


def _mla_inputs(q_content, latent, w_key, w_value, q_rope, k_rope, query_offset):
    q, c, wk, wv, qr, kr = _arrays(q_content, latent, w_key, w_value, q_rope, k_rope)
    if (q.ndim != 3 or c.ndim != 2 or wk.ndim != 3 or wv.ndim != 3
            or qr.ndim != 3 or kr.ndim != 2 or q.shape[:2] != qr.shape[:2]
            or q.shape[1] != wk.shape[0] or wk.shape[:2] != wv.shape[:2]
            or c.shape[1] != wk.shape[1] or q.shape[2] != wk.shape[2]
            or qr.shape[2] != kr.shape[1] or c.shape[0] != kr.shape[0]
            or min(*q.shape, *c.shape, *wk.shape, *wv.shape, *qr.shape, *kr.shape) < 1):
        raise ValueError("incompatible MLA factor shapes")
    _positions(q.shape[0], c.shape[0], query_offset)
    return q, c, wk, wv, qr, kr


def mla_expanded(q_content, latent, w_key, w_value, q_rope, k_rope, *, query_offset=0):
    """q_rope/k_rope are already position-transformed, independent content axes."""
    q, c, wk, wv, qr, kr = _mla_inputs(q_content, latent, w_key, w_value, q_rope, k_rope, query_offset)
    keys = np.einsum("lc,hcd->lhd", c, wk)
    values = np.einsum("lc,hcv->lhv", c, wv)
    content_score = np.einsum("qhd,lhd->qhl", q, keys)
    positional_score = np.einsum("qhr,lr->qhl", qr, kr)
    scale = np.asarray(np.sqrt(q.shape[-1] + qr.shape[-1]), dtype=q.dtype)
    probabilities = _softmax((content_score + positional_score) / scale, query_offset)
    return np.einsum("qhl,lhv->qhv", probabilities, values)


def mla_latent(q_content, latent, w_key, w_value, q_rope, k_rope, *, query_offset=0):
    """Absorb key projection and defer value projection; not a memory-cost model.

    This algebra check still materializes scores. It does not implement an
    official MLA kernel, query compression, output projection, or full RoPE.
    """
    q, c, wk, wv, qr, kr = _mla_inputs(q_content, latent, w_key, w_value, q_rope, k_rope, query_offset)
    absorbed_q = np.einsum("qhd,hcd->qhc", q, wk)
    content_score = np.einsum("qhc,lc->qhl", absorbed_q, c)
    positional_score = np.einsum("qhr,lr->qhl", qr, kr)
    scale = np.asarray(np.sqrt(q.shape[-1] + qr.shape[-1]), dtype=q.dtype)
    probabilities = _softmax((content_score + positional_score) / scale, query_offset)
    latent_context = np.einsum("qhl,lc->qhc", probabilities, c)
    return np.einsum("qhc,hcv->qhv", latent_context, wv)


def _error(actual, reference):
    if actual.shape != reference.shape or not np.isfinite(actual).all() or not np.isfinite(reference).all():
        raise AssertionError("shape mismatch or nonfinite output")
    absolute = float(np.max(np.abs(actual.astype(np.float64) - reference.astype(np.float64))))
    normalized = absolute / (1 + float(np.max(np.abs(reference))))
    return {"max_abs": absolute, "max_abs_over_1_plus_reference_max": normalized}


def run_checks():
    """Run deterministic synthetic checks; raise if a positive/negative fails."""
    rows = []
    seeds = [7, 19, 43]
    scales = [0.01, 1.0, 4.0]

    def check(family, dtype, reference, actual, parameters, reference_same_dtype=None):
        error = _error(actual, reference)
        tolerance = 2e-11 if dtype == np.float64 else 2e-3
        if error["max_abs_over_1_plus_reference_max"] > tolerance:
            raise AssertionError((family, np.dtype(dtype).name, parameters, error))
        row = {"family": family, "dtype": np.dtype(dtype).name, **parameters,
               **error, "normalized_tolerance": tolerance}
        if reference_same_dtype is not None:
            row["same_dtype_materialized_error"] = _error(actual, reference_same_dtype)
            row["materialized_vs_float64"] = _error(reference_same_dtype, reference)
            if row["materialized_vs_float64"]["max_abs_over_1_plus_reference_max"] > tolerance:
                raise AssertionError("materialized float32 does not meet declared comparison tolerance")
        rows.append(row)

    for seed in seeds:
        rng = np.random.default_rng(seed)
        for m, d, f in [(1, 5, 7), (3, 6, 11), (7, 5, 13)]:
            base = [rng.normal(size=shape) for shape in [(m, d), (d, f), (d, f), (f, d)]]
            for scale in scales:
                for dtype in (np.float64, np.float32):
                    operands = [(array * scale).astype(dtype) for array in base]
                    reference = swiglu_materialized(*[array.astype(np.float64) for array in operands])
                    materialized = swiglu_materialized(*operands)
                    for tile in [1, 4, 6]:
                        check("swiglu", dtype, reference, swiglu_tiled(*operands, hidden_tile=tile),
                              {"seed": seed, "shape": [m, d, f], "scale": scale, "hidden_tile": tile}, materialized)
        for mode, t, length in [("prefill", 7, 7), ("decode", 1, 11), ("suffix", 3, 13)]:
            offset = length - t
            base = [rng.normal(size=shape) for shape in [(t, 6, 5), (length, 2, 5), (length, 2, 3)]]
            for scale in scales:
                for dtype in (np.float64, np.float32):
                    operands = [(array * scale).astype(dtype) for array in base]
                    reference = gqa_full(*[array.astype(np.float64) for array in operands], query_offset=offset)
                    materialized = gqa_full(*operands, query_offset=offset)
                    for tile in [1, 4, 6]:
                        actual = gqa_streaming(*operands, query_offset=offset, query_tile=2, key_tile=tile)
                        check("gqa", dtype, reference, actual,
                              {"seed": seed, "mode": mode, "q_len": t, "kv_len": length,
                               "query_offset": offset, "h_query": 6, "h_kv": 2,
                               "scale": scale, "query_tile": 2, "key_tile": tile}, materialized)
            mla_base = [rng.normal(size=shape) for shape in
                        [(t, 3, 4), (length, 5), (3, 5, 4), (3, 5, 6), (t, 3, 2), (length, 2)]]
            for scale in scales:
                for dtype in (np.float64, np.float32):
                    operands = [(array * scale).astype(dtype) for array in mla_base]
                    reference = mla_expanded(*[array.astype(np.float64) for array in operands], query_offset=offset)
                    check("mla", dtype, reference, mla_latent(*operands, query_offset=offset),
                          {"seed": seed, "mode": mode, "q_len": t, "kv_len": length,
                           "query_offset": offset, "scale": scale}, mla_expanded(*operands, query_offset=offset))

    rng = np.random.default_rng(991)
    q, k, v = [rng.normal(size=shape) for shape in [(1, 6, 5), (11, 2, 5), (11, 2, 3)]]
    correct = gqa_full(q, k, v, query_offset=10)
    negatives = []
    for name, wrong in [("wrong_gqa_group", gqa_full(q, k[:, ::-1], v[:, ::-1], query_offset=10)),
                        ("wrong_decode_causal_offset", gqa_streaming(q, k, v, query_offset=0))]:
        error = _error(wrong, correct)
        if error["max_abs_over_1_plus_reference_max"] <= 1e-4:
            raise AssertionError("negative control not detected: " + name)
        negatives.append({"name": name, "detected": True, **error})
    operands = [rng.normal(size=shape) for shape in [(1, 3, 5), (11, 5), (3, 5, 5),
                                                     (3, 5, 4), (1, 3, 2), (11, 2)]]
    correct = mla_expanded(*operands, query_offset=10)
    wrong_operands = operands[:]
    wrong_operands[2] = operands[2].swapaxes(-1, -2)
    error = _error(mla_latent(*wrong_operands, query_offset=10), correct)
    if error["max_abs_over_1_plus_reference_max"] <= 1e-4:
        raise AssertionError("MLA transpose negative control not detected")
    negatives.append({"name": "wrong_mla_key_projection_transpose", "detected": True, **error})
    summary = {}
    for family in ["swiglu", "gqa", "mla"]:
        summary[family] = {}
        for dtype in ["float64", "float32"]:
            subset = [row for row in rows if row["family"] == family and row["dtype"] == dtype]
            summary[family][dtype] = {"checks": len(subset), "max_abs": max(row["max_abs"] for row in subset),
                                      "max_normalized_error": max(row["max_abs_over_1_plus_reference_max"] for row in subset)}
    return {"status": "PASS", "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "numpy_version": np.__version__, "seeds": seeds, "scales": scales,
            "positive_checks": len(rows), "negative_controls": negatives, "summary": summary,
            "cases": rows,
            "scope": "Synthetic small-shape forward algebra only, not an official model/checkpoint run.",
            "reference_precision": "For each dtype, float64 reference is evaluated on the same already-cast inputs; float32 arithmetic error is separate from operand-quantization error.",
            "limitations": ["No FP16/BF16/INT arithmetic or hardware encoding is verified.",
                            "No training/backward, model quality, cycle timing, memory traffic or PPA.",
                            "MLA RoPE channels are supplied after positional transformation; query compression, rotary implementation and final output projection are outside scope.",
                            "MLA latent algebra still materializes scores; it is not an online MLA kernel."]}


if __name__ == "__main__":
    print(json.dumps(run_checks(), indent=2, allow_nan=False))
