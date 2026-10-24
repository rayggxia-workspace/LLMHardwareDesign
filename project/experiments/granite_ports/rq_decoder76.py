"""Independent S64 RNE control decoding; no producer imports or float math."""
import hashlib
import json

from audit_io76 import checked, need, shift_rne


FEE_VERSION = "NONNEGATIVE_MIN128_FOUR_TYPED_PLUS_FLAG_TEST76_V1"


def decode(raw):
    raw = checked(raw, 64)
    need(raw >= 0, "negative RQ shift needs separately implemented left-shift path")
    # This is the independent mathematical value, not a free hardware opcode.
    # The target must pay cmp + two sub + max, flags IO and controller guard.
    return min(raw, 128)


def rounded_s64(product, raw):
    product = checked(product, 64)
    raw = checked(raw, 64)
    need(raw >= 0, "nonnegative RQ right shift")
    if raw >= 64:
        # |S64| <= 2^63. At raw64 the only equality is S64_MIN / 2^64
        # = -1/2; ties-to-even selects0. Larger shifts are strictly within1/2.
        return 0
    return shift_rne(product, raw)


def verify_alias(product, raw, published):
    chosen = decode(raw)
    original, decoded = rounded_s64(product, raw), rounded_s64(product, chosen)
    need(type(published) is int and original == decoded == published, "original/decoded exact RNE and published integer code")
    return chosen


def array_hash(a):
    import numpy as np
    a = np.ascontiguousarray(a)
    h = hashlib.sha256(str(a.dtype).encode()+json.dumps(list(a.shape), separators=(",", ":")).encode())
    h.update(a.tobytes()); return h.hexdigest()


def reconstruct(trace, const, layer, source):
    """Independently reconstruct all raw/decoded controls and changed witnesses."""
    import numpy as np
    evidence = {"schema": "granite-rq-decoder76-v1", "fee_version": FEE_VERSION,
                "raw_formula": "31-weight_exponent_I16-current_activation_delta_I16",
                "decoded_formula": "128-max(128-raw_shift,0), guarded raw_shift>=0",
                "proof": "For signed S64 n and s>=64, |n|/2**s<=1/2; the only equality is I64_MIN at s64, tie-to-even zero. Hence all s>128 may map to128 exactly.",
                "target_policy": "all outputs execute cmp/sub/max/sub and explicit flag consumption; no observed-position shortcut",
                "observer_cost": "hashes/histograms/equality witnesses are offline observations, not target operations",
                "operations": {}, "source": source}
    ids = trace["router.ids"]
    need(ids.shape == (72, 8) and np.all((ids >= 0) & (ids < 40)), "decoder actual complete expert IDs")
    zero_checked = 0
    for which, outputs in (("gate_up", 1024), ("down", 1536)):
        exponents = const[f"L{layer}.{which}_exp"]
        product_key, published_key = which+"_RQ_product64", which+"_q12"
        product, published = trace[product_key], trace[published_key]
        need(exponents.dtype == np.int16 and exponents.shape == (40, outputs)
             and product.dtype == np.int64 and published.dtype == np.int32
             and product.shape == published.shape == (72, 8, outputs), "decoder original exponent/product/published formats")
        raw = np.empty(product.shape, np.int64)
        for token in range(72):
            for rank in range(8):
                d = int(trace["expert_input_delta"][token]) if which == "gate_up" else int(trace["mid_delta"][token, rank])
                need(0 <= d <= 128, "decoder current activation unit range")
                raw[token, rank] = 31-exponents[int(ids[token, rank])].astype(np.int64)-d
        need(np.all(raw >= 0), "negative RQ shift needs separately implemented left-shift path")
        # Independent piecewise form; the target pays an explicit four-op graph.
        decoded = np.where(raw > 128, np.int64(128), raw)
        need(np.all((decoded >= 0) & (decoded <= 128)), "decoded RNE control domain")
        zero_mask = raw >= 64
        need(np.all(published[zero_mask] == 0), "full S64 large-right-shift zero proof and actual published code")
        zero_checked += int(np.count_nonzero(zero_mask))
        changed = []
        for token, rank, output in np.argwhere(raw != decoded):
            t, r, c = int(token), int(rank), int(output)
            n, shift, value = int(product[t, r, c]), int(raw[t, r, c]), int(published[t, r, c])
            chosen = verify_alias(n, shift, value)
            d = int(trace["expert_input_delta"][t]) if which == "gate_up" else int(trace["mid_delta"][t, r])
            changed.append({"token": t, "phase": "prefill64" if t < 64 else "decode8", "rank": r,
                            "expert": int(ids[t, r]), "output": c, "weight_exponent_I16": int(exponents[int(ids[t, r]), c]),
                            "activation_delta_I16": d, "raw_shift": shift, "decoded_shift": chosen, "RQ_product_S64": n,
                            "original_RNE": rounded_s64(n, shift), "decoded_RNE": rounded_s64(n, chosen), "published_Q12": value})
        def histogram(value):
            values, counts = np.unique(value, return_counts=True)
            return {str(int(k)): int(v) for k, v in zip(values, counts)}
        evidence["operations"][which] = {
            "shape": list(raw.shape), "actual_outputs": int(raw.size), "raw_minimum": int(np.min(raw)), "raw_maximum": int(np.max(raw)),
            "decoded_minimum": int(np.min(decoded)), "decoded_maximum": int(np.max(decoded)), "negative_count": 0,
            "changed_count": len(changed), "raw_histogram": histogram(raw), "decoded_histogram": histogram(decoded),
            "raw_array_sha256": array_hash(raw), "decoded_array_sha256": array_hash(decoded),
            "raw_token_rank_sha256": [[array_hash(raw[t, r]) for r in range(8)] for t in range(72)],
            "decoded_token_rank_sha256": [[array_hash(decoded[t, r]) for r in range(8)] for t in range(72)],
            "source_product_key": product_key, "source_published_key": published_key,
            "source_product_array_sha256": array_hash(product), "source_published_array_sha256": array_hash(published),
            "changed_positions": changed, "unchanged_positions_identical_shift": int(raw.size)-len(changed)}
    return evidence, zero_checked
