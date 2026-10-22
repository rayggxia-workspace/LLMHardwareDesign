"""Independent, reduced NumPy oracle for DeepSeek-V3 inference dataflow.

Run: python -B check_deepseek_paths.py --output deepseek-correctness.json
No checkpoints, GPU libraries, network, or production implementation imports.
This checks real-valued algebra, not quantization accuracy or hardware PPA.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

UPSTREAM_COMMIT = "9b4e9788e4a3a731f7567338ed15d3ec549ce03b"
UPSTREAM_URL = f"https://github.com/deepseek-ai/DeepSeek-V3/blob/{UPSTREAM_COMMIT}/inference/model.py"
SEEDS = [19, 20261022, 314159]
ATOL = 1e-10


def rms(x):
    return x / np.sqrt(np.mean(x * x, axis=-1, keepdims=True) + 1e-6)


def rope(x, positions):
    # Independently implement ordinary two-channel rotations, not YaRN.
    assert x.shape[-1] % 2 == 0
    theta = positions[:, None] * 10000.0 ** (-np.arange(0, x.shape[-1], 2) / x.shape[-1])
    shape = [1, x.shape[1]] + [1] * (x.ndim - 3) + [x.shape[-1] // 2]
    co, si = np.cos(theta).reshape(shape), np.sin(theta).reshape(shape)
    y = np.empty_like(x)
    y[..., 0::2] = x[..., 0::2] * co - x[..., 1::2] * si
    y[..., 1::2] = x[..., 0::2] * si + x[..., 1::2] * co
    return y


def softmax(a):
    e = np.exp(a - np.max(a, axis=-1, keepdims=True))
    return e / e.sum(axis=-1, keepdims=True)


def check_close(a, b, name):
    err = float(np.max(np.abs(a - b)))
    if not np.allclose(a, b, rtol=1e-10, atol=ATOL):
        raise AssertionError(f"{name}: error {err}")
    return {"name": name, "shape": list(a.shape), "max_absolute_error": err, "pass": True}


def mla_case(seed, batch, length):
    rng = np.random.default_rng(seed)
    d, h, rq, rc, dn, dr, dv = 16, 4, 7, 5, 4, 2, 3
    x = rng.standard_normal((batch, length, d))
    wq_a = rng.standard_normal((d, rq)) / np.sqrt(d)
    wq_b = rng.standard_normal((rq, h * (dn + dr))) / np.sqrt(rq)
    wkv_a = rng.standard_normal((d, rc + dr)) / np.sqrt(d)
    uk = rng.standard_normal((h, dn, rc)) / np.sqrt(rc)
    uv = rng.standard_normal((h, dv, rc)) / np.sqrt(rc)
    wo = rng.standard_normal((h * dv, d)) / np.sqrt(h * dv)
    q = (rms(x @ wq_a) @ wq_b).reshape(batch, length, h, dn + dr)
    qn, qr = q[..., :dn], rope(q[..., dn:], np.arange(length))
    kv = x @ wkv_a
    c, kr = rms(kv[..., :rc]), rope(kv[..., rc:], np.arange(length))
    kn = np.einsum("btc,hdc->bthd", c, uk)
    value = np.einsum("btc,hvc->bthv", c, uv)
    full_key = np.concatenate((kn, np.broadcast_to(kr[:, :, None, :], (batch, length, h, dr))), axis=-1)
    full_query = np.concatenate((qn, qr), axis=-1)
    scale = (dn + dr) ** -0.5
    causal = np.arange(length)[None, :] > np.arange(length)[:, None]
    naive_logits = np.einsum("bqhd,bkhd->bqhk", full_query, full_key) * scale
    naive_logits = np.where(causal[None, :, None, :], -np.inf, naive_logits)
    naive_prob = softmax(naive_logits)
    naive = np.einsum("bqhk,bkhv->bqhv", naive_prob, value).reshape(batch, length, h * dv) @ wo
    qlatent = np.einsum("bqhd,hdc->bqhc", qn, uk)
    absorb_logits = (np.einsum("bqhc,bkc->bqhk", qlatent, c) + np.einsum("bqhr,bkr->bqhk", qr, kr)) * scale
    absorb_logits = np.where(causal[None, :, None, :], -np.inf, absorb_logits)
    absorb_prob = softmax(absorb_logits)
    latent_out = np.einsum("bqhk,bkc->bqhc", absorb_prob, c)
    absorb = np.einsum("bqhc,hvc->bqhv", latent_out, uv).reshape(batch, length, h * dv) @ wo
    checks = [check_close(naive_prob, absorb_prob, "naive_absorb_probability"), check_close(naive, absorb, "naive_absorb_prefill")]

    # Incremental cache append; each query sees only its prefix, not future KV.
    cc, rr, decode_outputs = [], [], []
    for pos in range(length):
        cc.append(c[:, pos:pos + 1])
        rr.append(kr[:, pos:pos + 1])
        cp, rp = np.concatenate(cc, axis=1), np.concatenate(rr, axis=1)
        score = (np.einsum("bhc,bkc->bhk", qlatent[:, pos], cp) + np.einsum("bhr,bkr->bhk", qr[:, pos], rp)) * scale
        outc = np.einsum("bhk,bkc->bhc", softmax(score), cp)
        outv = np.einsum("bhc,hvc->bhv", outc, uv)
        decode_outputs.append(outv.reshape(batch, h * dv) @ wo)
    checks.append(check_close(naive, np.stack(decode_outputs, axis=1), "prefill_incremental_decode"))

    # Online softmax with KV tiles of three: no full score/probability tensor.
    outputs = []
    for pos in range(length):
        m = np.full((batch, h), -np.inf)
        total = np.zeros((batch, h))
        accum = np.zeros((batch, h, rc))
        for start in range(0, pos + 1, 3):
            end = min(start + 3, pos + 1)
            cb, rb = c[:, start:end], kr[:, start:end]
            score = (np.einsum("bhc,bkc->bhk", qlatent[:, pos], cb) + np.einsum("bhr,bkr->bhk", qr[:, pos], rb)) * scale
            m_new = np.maximum(m, score.max(axis=-1))
            old_factor = np.exp(m - m_new)
            p = np.exp(score - m_new[..., None])
            accum = accum * old_factor[..., None] + np.einsum("bhk,bkc->bhc", p, cb)
            total = total * old_factor + p.sum(axis=-1)
            m = m_new
        outv = np.einsum("bhc,hvc->bhv", accum / total[..., None], uv)
        outputs.append(outv.reshape(batch, h * dv) @ wo)
    checks.append(check_close(naive, np.stack(outputs, axis=1), "materialized_online_softmax"))
    return {"seed": seed, "batch": batch, "length": length, "dimensions": {"d": d, "heads": h, "q_rank": rq, "kv_rank": rc, "non_rope": dn, "rope": dr, "value": dv}, "checks": checks}


def routing_case(seed, tokens):
    rng = np.random.default_rng(seed + 101)
    d, experts, groups, group_topk, topk, scale = 16, 16, 4, 2, 3, 2.5
    x = rng.standard_normal((tokens, d))
    w = rng.standard_normal((d, experts)) / np.sqrt(d)
    bias = rng.uniform(-0.15, 0.15, experts)
    scores = 1.0 / (1.0 + np.exp(-(x @ w)))
    selection_scores = scores + bias
    grouped = selection_scores.reshape(tokens, groups, experts // groups)
    group_scores = np.sort(grouped, axis=-1)[..., -2:].sum(axis=-1)
    allowed_groups = np.argsort(-group_scores, axis=-1)[:, :group_topk]
    allowed = np.any(np.arange(groups)[None, :, None] == allowed_groups[:, None, :], axis=-1)
    filtered = np.where(np.repeat(allowed, experts // groups, axis=1), selection_scores, -np.inf)
    ids = np.argsort(-filtered, axis=-1)[:, :topk]
    raw = np.take_along_axis(scores, ids, axis=-1)
    weights = scale * raw / raw.sum(axis=-1, keepdims=True)
    # A separate scalar/list oracle, no reuse of vectorized top-k masks.
    ref_ids, ref_weights = [], []
    for token in range(tokens):
        groups_sorted = sorted(range(groups), key=lambda g: sum(sorted(float(scores[token, e] + bias[e]) for e in range(g * 4, g * 4 + 4))[-2:]), reverse=True)
        allowed_experts = [e for g in groups_sorted[:group_topk] for e in range(g * 4, g * 4 + 4)]
        selected = sorted(allowed_experts, key=lambda e: float(scores[token, e] + bias[e]), reverse=True)[:topk]
        normalizer = sum(float(scores[token, e]) for e in selected)
        ref_ids.append(selected)
        ref_weights.append([scale * float(scores[token, e]) / normalizer for e in selected])
    if not np.array_equal(ids, ref_ids):
        raise AssertionError("grouped expert selection differs from scalar oracle")
    checks = [check_close(weights, np.asarray(ref_weights), "unbiased_combination_weights"), check_close(weights.sum(axis=-1), np.full(tokens, scale), "routing_weight_sum")]
    # Negative control: adding routing bias to combination weights must change results.
    wrong_raw = np.take_along_axis(selection_scores, ids, axis=-1)
    wrong_weights = scale * wrong_raw / wrong_raw.sum(axis=-1, keepdims=True)
    negative_delta = float(np.max(np.abs(weights - wrong_weights)))
    if negative_delta <= 1e-6:
        raise AssertionError("bias misuse negative control lacks sensitivity")
    occupancy = np.bincount(ids.ravel(), minlength=experts)
    return {"seed": seed, "tokens": tokens, "experts": experts, "groups": groups, "topk_groups": group_topk, "topk_experts": topk, "route_scale": scale, "selected_experts_match_scalar_oracle": True, "checks": checks, "negative_control_biased_combination_max_delta": negative_delta, "negative_control_detected": True, "expert_occupancy": occupancy.tolist()}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    mla = [mla_case(seed, batch, length) for seed in SEEDS for batch, length in [(1, 1), (1, 7), (2, 19)]]
    routing = [routing_case(seed, length) for seed in SEEDS for length in [1, 7, 19]]
    results = {
        "schema": "deepseek-reduced-inference-algebra-v1", "status": "PASS",
        "observed_utc": datetime.now(timezone.utc).isoformat(),
        "python": platform.python_version(), "numpy": np.__version__, "dtype": "float64", "atol": ATOL,
        "source_script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "upstream_reference": {"url": UPSTREAM_URL, "commit": UPSTREAM_COMMIT, "mla_lines": [396, 497], "gate_lines": [535, 598]},
        "mla_cases": mla, "routing_cases": routing,
        "check_counts": {"mla_numeric_comparisons": len(mla) * 4, "routing_numeric_comparisons": len(routing) * 2, "routing_index_exact_checks": len(routing), "bias_negative_controls": len(routing)},
        "analytic_v3_cache": {"heads": 128, "non_rope_dim": 128, "rope_dim": 64, "value_dim": 128, "kv_rank": 512, "layers": 61, "bytes_per_element_assumed": 2, "compressed_elements_per_token_layer": 512 + 64, "naive_expanded_elements_per_token_layer": 128 * (128 + 64 + 128), "compressed_bytes_per_token_all_layers": 61 * (512 + 64) * 2, "compressed_bytes_b1_t8192_all_layers": 8192 * 61 * (512 + 64) * 2, "includes_metadata_scaling_allocator": False},
        "scope_limits": ["No weight checkpoint or real model accuracy", "Independent equations, not an execution of upstream PyTorch/Triton", "Float64 only; no BF16/FP8/FP4 validation", "Ordinary 2D RoPE; YaRN scaling not implemented", "No sparse attention, KV paging, tensor parallelism or all-to-all execution", "No hardware area, frequency, energy, latency or throughput measurements", "Training execution excluded"],
    }
    args.output.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": results["status"], "checks": results["check_counts"], "output": str(args.output), "script_sha256": results["source_script_sha256"], "output_sha256": hashlib.sha256(args.output.read_bytes()).hexdigest()}))


if __name__ == "__main__":
    main()
