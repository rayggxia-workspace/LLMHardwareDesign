"""Independent Issue74 complete Granite MoE integer mathematics.

There are no producer imports.  Full artifacts are received on the authorized
server; local tests exercise only bounded synthetic values.
"""
import argparse
import ast
from collections import Counter
from decimal import Decimal, localcontext, ROUND_HALF_EVEN
from fractions import Fraction
from functools import lru_cache
import hashlib
import json
import math
from pathlib import Path
import shutil

import numpy as np

from audit_io74 import (checked, descriptor, divided_rne, load_json, need,
                        rational_rne, replace_artifact_hash, save_json, sha,
                        shift_rne, source_binding, square_root, verify_manifest)


I64 = (1 << 63) - 1
REVISION = "a02780686e08a03fe0d2679a293b5c74a90efa89"


def arrays(path):
    with np.load(path, allow_pickle=False) as source:
        answer = {key: source[key] for key in source.files}
    need(all(a.dtype.kind != "O" for a in answer.values()), "no object arrays")
    return answer


def array_sha(value):
    value = np.ascontiguousarray(value)
    prefix = str(value.dtype).encode() + json.dumps(list(value.shape), separators=(",", ":")).encode()
    return hashlib.sha256(prefix + value.tobytes()).hexdigest()


def equal(actual, expected, label):
    need(actual.dtype == expected.dtype and actual.shape == expected.shape
         and np.array_equal(actual, expected), "integer stage " + label)


def magnitude(value):
    value = np.asarray(value)
    need(value.dtype.kind in "iu" and value.size > 0, "nonempty integer replay input")
    lo, hi = int(value.min()), int(value.max())
    need(-(1 << 63) < lo and hi <= I64, "symmetric checked I64 replay domain")
    return max(-lo, hi)


def i32(value):
    value = np.asarray(value)
    need(value.dtype.kind in "iu" and int(value.min(initial=0)) >= -(1 << 31)
         and int(value.max(initial=0)) < 1 << 31, "I32 stage guard")
    return value.astype(np.int32)


class IntegerMath:
    """A separate floor-quotient and integer-bit reference implementation."""
    def __init__(self):
        self.counts = Counter()

    def shift(self, value, shift):
        value = np.asarray(value)
        magnitude(value)
        value = value.astype(np.int64)
        shift = int(shift)
        need(-127 <= shift <= 255, "runtime shift bound")
        self.counts["rne64"] += value.size
        if shift < 0:
            need(magnitude(value) * (1 << -shift) <= I64, "I64 alignment guard")
            return value * (1 << -shift)
        if shift == 0:
            return value.copy()
        if shift >= 63:
            return np.asarray([shift_rne(int(v), shift) for v in value.flat],
                              np.int64).reshape(value.shape)
        quotient, remainder = np.divmod(value, 1 << shift)
        half = 1 << (shift - 1)
        return quotient + ((remainder > half) | ((remainder == half) & ((quotient & 1) != 0)))

    def product(self, left, right):
        left, right = np.asarray(left), np.asarray(right)
        need(magnitude(left) * magnitude(right) <= I64, "I64 product guard")
        self.counts["mul32"] += int(np.prod(np.broadcast_shapes(left.shape, right.shape)))
        return left.astype(np.int64) * right.astype(np.int64)

    def add(self, left, right):
        left, right = np.asarray(left), np.asarray(right)
        need(magnitude(left) + magnitude(right) <= I64, "I64 prefix guard")
        self.counts["add64"] += int(np.prod(np.broadcast_shapes(left.shape, right.shape)))
        return left.astype(np.int64) + right.astype(np.int64)

    def dynamic(self, x, bits=8):
        x = np.asarray(x)
        need(x.ndim == 2 and bits in (8, 16), "dynamic integer row quantization")
        limit = (1 << (bits - 1)) - 1
        code = np.empty(x.shape, np.int8 if bits == 8 else np.int16)
        shifts = np.empty(len(x), np.int16)
        for index, row in enumerate(x):
            shift = 0
            candidate = self.shift(row, shift)
            while magnitude(candidate) > limit:
                shift += 1
                candidate = self.shift(row, shift)
            code[index], shifts[index] = candidate, shift
        return code, shifts

    def norm(self, x, gamma_q20, epsilon_q24):
        x, gamma = np.asarray(x), np.asarray(gamma_q20)
        need(x.ndim == 2 and gamma.shape == (x.shape[-1],), "full RMSNorm group")
        result = np.empty(x.shape, np.int64)
        sums, means, denominators = [], [], []
        for index, row in enumerate(x):
            total = sum(int(v) * int(v) for v in row)
            need(0 <= total < 1 << 128, "U128 norm sumsq")
            mean, _ = divmod(total, len(row))
            variance = mean + int(epsilon_q24)
            need(0 < variance << 40 < 1 << 128, "U128 norm radicand")
            denominator = square_root(variance << 40, 128)
            sums.append(total)
            means.append(variance)
            denominators.append(denominator)
            for column, value in enumerate(row):
                numerator = int(value) * int(gamma[column]) * (1 << 12)
                need(abs(numerator) < 1 << 127, "signed I128 norm numerator guard")
                result[index, column] = divided_rne(numerator, denominator, 128)
        self.counts.update(norm_square32=x.size, normadd128=x.size-len(x),
                           division128=x.size+len(x), isqrt128=len(x))
        # Python integer witnesses do not invent a serialized object NPZ format.
        return i32(result), {"sumsq": sums, "variance": means, "denominator": denominators}

    def linear(self, x, w8, q31, exponent):
        x, weight = np.asarray(x), np.asarray(w8)
        q31, exponent = np.asarray(q31), np.asarray(exponent)
        need(x.ndim == weight.ndim == 2 and x.shape[-1] == weight.shape[-1]
             and weight.dtype == np.int8 and magnitude(weight) <= 127,
             "complete symmetric W8 matrix")
        need(q31.shape == exponent.shape == (weight.shape[0],), "peroutput static Q31 metadata")
        code, delta = self.dynamic(x, 8)
        need(weight.shape[-1] * 127 * 127 <= (1 << 31) - 1, "all-prefix INT32 dot bound")
        dot = code.astype(np.int64) @ weight.astype(np.int64).T
        self.counts["matrix_mac"] += x.shape[0] * weight.shape[0] * weight.shape[1]
        result = np.empty(dot.shape, np.int64)
        all_products = np.empty(dot.shape, np.int64)
        for row in range(len(x)):
            products = self.product(dot[row], q31)
            all_products[row] = products
            for column, value in enumerate(products):
                result[row, column] = shift_rne(int(value),
                    31 - int(exponent[column]) - int(delta[row]))
        return i32(result), {"a8": code, "delta": delta, "dot": i32(dot), "products": all_products}

    def silu(self, x, table):
        x, table = np.asarray(x), np.asarray(table)
        need(table.shape == (16385,) and table.dtype == np.int32, "complete frozen SiLU LUT")
        lo, hi = -(32 << 12), 32 << 12
        index = self.shift(np.clip(x, lo, hi).astype(np.int64) - lo, 4)
        values = table[index]
        values = np.where(x < lo, 0, np.where(x > hi, x, values))
        self.counts["silu_reads32"] += x.size
        return i32(values), index.astype(np.int16)

    def router(self, norm_q12, weight, exponent, bits, exp2_q24):
        """All40 logits,actual top8 and integer gates from the current norm."""
        x, w, exponent = np.asarray(norm_q12), np.asarray(weight), np.asarray(exponent)
        limit = (1 << (bits - 1)) - 1
        need(bits in (8, 16) and x.ndim == w.ndim == 2 and x.shape[1] == w.shape[1]
             and w.shape[0] == 40 and exponent.shape == (40,)
             and w.dtype == (np.int8 if bits == 8 else np.int16)
             and magnitude(w) <= limit, "complete typed router matrix")
        code, delta = self.dynamic(x, bits)
        need(w.shape[1] * limit * limit < 1 << 63, "full router dot I64 bound")
        dots = code.astype(np.int64) @ w.astype(np.int64).T
        self.counts["router_s8_mac"] += x.shape[0] * w.shape[0] * w.shape[1] * (1 if bits == 8 else 9)
        partials = np.empty((0, len(x), 40), np.int32)
        if bits == 16:
            # This contract is explicitly signed-magnitude radix128, in
            # contrast to the signed-high lowering of general wide scalars.
            left = [(((np.abs(code.astype(np.int64)) >> (7*i)) & 127)
                     * np.sign(code)).astype(np.int8) for i in range(3)]
            right = [(((np.abs(w.astype(np.int64)) >> (7*i)) & 127)
                      * np.sign(w)).astype(np.int8) for i in range(3)]
            partials = []
            reconstructed = np.zeros(dots.shape, np.int64)
            for i in range(3):
                for j in range(3):
                    part = i32(left[i].astype(np.int64) @ right[j].astype(np.int64).T)
                    partials.append(part)
                    reconstructed = self.add(reconstructed, self.shift(part, -7*(i+j)))
            equal(reconstructed, dots.astype(np.int64), "all-row R16 nine-dot reconstruction")
            partials = np.stack(partials)
        common = np.empty(dots.shape, np.int64)
        common_exp = np.empty(len(x), np.int16)
        smallest = int(exponent.min())
        for column in range(40):
            common[:, column] = self.shift(dots[:, column], -(int(exponent[column])-smallest))
        values = delta.astype(np.int64) - 12 + smallest
        need(values.min(initial=0) >= -(1 << 15) and values.max(initial=0) < 1 << 15,
             "I16 common logit exponent guard")
        common_exp[:] = values
        ids, gates, indices = [], [], []
        table = np.asarray(exp2_q24)
        need(table.shape == (2049,) and table.dtype == np.uint32
             and int(table.min()) > 0, "full integer exp2 LUT")
        for row, unit in zip(common, common_exp):
            selected = sorted(range(40), key=lambda idx: (-int(row[idx]), idx))[:8]
            index = []
            for idx in selected:
                diff = int(row[idx]) - int(row[selected[0]])
                product = checked(diff * 1549082005, 128)
                grid = shift_rne(product, 23-int(unit))
                index.append(-min(0, max(-2048, grid)))
            values = [int(table[i]) for i in index]
            denominator = sum(values)
            gate = [divided_rne(v << 15, denominator, 128) for v in values]
            gate[0] += 32768-sum(gate)
            need(min(gate) >= 0 and max(gate) <= 32768 and sum(gate) == 32768,
                 "Q15 rounded gate mass and domain")
            ids.append(selected)
            gates.append(gate)
            indices.append(index)
        return {"input_code": code, "input_delta": delta, "dot": dots,
                "common_logits": common, "common_exp": common_exp,
                "ids": np.asarray(ids, np.uint8), "gate_q15": np.asarray(gates, np.uint16),
                "lut_index": np.asarray(indices, np.int16), "partials": partials}

    def merge(self, expert_q12, gate_q15):
        expert, gate = np.asarray(expert_q12), np.asarray(gate_q15)
        need(expert.ndim == 3 and gate.shape == expert.shape[:2] and expert.shape[1] == 8,
             "complete eight-expert weighted merge")
        need(gate.dtype.kind in "iu" and int(gate.min()) >= 0 and
             np.all(gate.astype(np.int64).sum(axis=1) == 32768), "exact Q15 gate mass")
        total = np.zeros((expert.shape[0], expert.shape[2]), np.int64)
        prefixes = []
        for rank in range(8):
            product = self.product(expert[:, rank], gate[:, rank, None])
            total = product.copy() if rank == 0 else self.add(total, product)
            prefixes.append(total.copy())
        return i32(self.shift(total, 15)), np.stack(prefixes, axis=1)


def norm_trace(values):
    out = {}
    for label, key in (("sumsq", "sumsq"), ("variance", "variance")):
        out[label+"_lo_u64"] = np.asarray([v & ((1 << 64)-1) for v in values[key]], np.uint64)
        out[label+"_hi_u64"] = np.asarray([v >> 64 for v in values[key]], np.uint64)
    out["denominator_u64"] = np.asarray(values["denominator"], np.uint64)
    return out


def replay(residual, const, spec, layer, bits):
    """Recompute the whole cut; no captured integer intermediate is trusted."""
    eng = IntegerMath()
    key = "L%d." % layer
    need(np.asarray(residual).shape == (72, 1536), "bounded full residual cut")
    x = i32(residual)
    trace = {"residual_q12": x}
    n, stats = eng.norm(x, const[key+"post_gamma_q20"], spec["epsilon_q24"])
    trace["norm_q12"] = n
    trace.update({"post_norm."+name: value for name, value in norm_trace(stats).items()})
    route = eng.router(n, const[key+"router_w%d" % bits], const[key+"router_exp%d" % bits],
                       bits, const["route_exp2_q24"])
    trace.update({"router."+name: value for name, value in route.items()})
    a8, delta = eng.dynamic(n, 8)
    trace.update(expert_input_a8=a8, expert_input_delta=delta)
    gate_up_dot = np.zeros((72, 8, 1024), np.int32)
    gate_up_product = np.zeros((72, 8, 1024), np.int64)
    gate_up = np.zeros_like(gate_up_dot)
    ids = route["ids"]
    need(const[key+"gate_up_w8"].shape == (40, 1024, 1536)
         and const[key+"down_w8"].shape == (40, 1536, 512), "all40 real expert matrices")
    for expert in range(40):
        token, rank = np.where(ids == expert)
        if token.size == 0:
            continue
        value, witness = eng.linear(n[token], const[key+"gate_up_w8"][expert],
                                   const[key+"gate_up_mant_q31"][expert], const[key+"gate_up_exp"][expert])
        equal(witness["a8"], a8[token], "router and selected expert share current norm input")
        equal(witness["delta"], delta[token], "shared expert input scale")
        gate_up_dot[token, rank], gate_up_product[token, rank], gate_up[token, rank] = (
            witness["dot"], witness["products"], value)
    gate, up = gate_up[:, :, :512], gate_up[:, :, 512:]
    activated, index = eng.silu(gate, const["silu_lut_q12"])
    mid_product = eng.product(activated, up)
    mid = i32(eng.shift(mid_product, 12))
    mid_a8, mid_delta = eng.dynamic(mid.reshape(-1, 512), 8)
    mid_a8, mid_delta = mid_a8.reshape(72, 8, 512), mid_delta.reshape(72, 8)
    down_dot = np.zeros((72, 8, 1536), np.int32)
    down_product = np.zeros((72, 8, 1536), np.int64)
    down = np.zeros_like(down_dot)
    for expert in range(40):
        token, rank = np.where(ids == expert)
        if token.size == 0:
            continue
        value, witness = eng.linear(mid[token, rank], const[key+"down_w8"][expert],
                                   const[key+"down_mant_q31"][expert], const[key+"down_exp"][expert])
        equal(witness["a8"], mid_a8[token, rank], "selected expert complete mid A8")
        equal(witness["delta"], mid_delta[token, rank], "selected expert current mid scale")
        down_dot[token, rank], down_product[token, rank], down[token, rank] = (
            witness["dot"], witness["products"], value)
    merge_product = eng.product(down, route["gate_q15"][:, :, None])
    merged, prefixes = eng.merge(down, route["gate_q15"])
    scaled = i32(eng.shift(eng.product(merged, const["residual_multiplier_q20"]), 20))
    joined = i32(eng.add(x, scaled))
    next_norm, stats = eng.norm(joined, const[key+"next_gamma_q20"], spec["epsilon_q24"])
    trace.update(gate_up_acc32=gate_up_dot, gate_up_RQ_product64=gate_up_product,
                 gate_up_q12=gate_up, expert_gate_q12=gate, expert_up_q12=up,
                 expert_silu_q12=activated, silu_lut_index=index, mid_product64=mid_product,
                 expert_mid_q12=mid, mid_a8=mid_a8, mid_delta=mid_delta,
                 down_acc32=down_dot, down_RQ_product64=down_product, down_q12=down,
                 merge_product64=merge_product, merge_prefix64=prefixes, moe_q12=merged,
                 scaled_moe_q12=scaled, layer_output_q12=joined, next_norm_q12=next_norm)
    trace.update({"next_norm."+name: value for name, value in norm_trace(stats).items()})
    return trace, eng.counts


def fixed_encode(value, fraction):
    """Explicit offline FP64 compiler check, never an online scale bridge."""
    value = np.asarray(value, np.float64)
    scaled = np.ldexp(value, fraction)
    rounded = np.rint(scaled)
    need(np.isfinite(rounded).all() and rounded.min(initial=0) >= -(1 << 31)
         and rounded.max(initial=0) < 1 << 31, "offline fixed-format domain")
    return i32(rounded.astype(np.int64))


def ceil_power2(value):
    value = Fraction(value)
    need(value > 0, "positive power2 compiler ratio")
    e = value.numerator.bit_length()-value.denominator.bit_length()
    power = lambda n: Fraction(1 << n, 1) if n >= 0 else Fraction(1, 1 << -n)
    while power(e) < value:
        e += 1
    while power(e-1) >= value:
        e -= 1
    return e


def weight_compiler(raw):
    """Offline rowwise compiler, with scalar frexp/round metadata reference."""
    raw = np.asarray(raw)
    code = np.empty(raw.shape, np.int8)
    mantissa = np.empty(raw.shape[:-1], np.int32)
    exponent = np.empty(raw.shape[:-1], np.int16)
    for index in np.ndindex(raw.shape[:-2]):
        block = raw[index].astype(np.float64)
        peaks = np.max(np.abs(block), axis=1)
        scales = np.asarray([float(p)/127 if p else 1.0 for p in peaks])
        q = np.rint(block/scales[:, None])
        need(np.abs(q).max(initial=0) <= 127, "offline symmetric W8 code")
        code[index] = q.astype(np.int8)
        for row, scale in enumerate(scales):
            m, e = math.frexp(float(scale))
            m = round(m*(1 << 31))
            if m == 1 << 31:
                m //= 2
                e += 1
            checked(m, 32)
            checked(e, 16)
            mantissa[index+(row,)] = m
            exponent[index+(row,)] = e
    return code, mantissa, exponent


@lru_cache(maxsize=1)
def compiler_tables():
    """Independent Decimal70 oracle for every immutable LUT cell."""
    with localcontext() as context:
        context.prec = 70
        silu = []
        for index in range(-8192, 8193):
            x = Decimal(index)/256
            value = x/(1+(-x).exp())*4096
            silu.append(int(value.to_integral_value(rounding=ROUND_HALF_EVEN)))
        ln2 = Decimal(2).ln()
        exp2 = [int(((-Decimal(i)/128*ln2).exp()*(1 << 24)).to_integral_value(
            rounding=ROUND_HALF_EVEN)) for i in range(2049)]
    return np.asarray(silu, np.int32), np.asarray(exp2, np.uint32)


def check_compiler(compiled, capture, layer, producer_source):
    cm, ca = verify_manifest(compiled, kind="granite-moe-compiled74-v1", statuses=("COMPILED_NOT_EXECUTED",))
    capture_manifest, capture_artifacts = verify_manifest(capture, kind="granite-moe-capture74-v1",
                                                         statuses=("CAPTURE_REFERENCE_PASS",))
    source_binding(cm, {"granite_chain_sha256": producer_source})
    need(cm["producer_sha256"] == sha(producer_source) and cm["model_revision"] == REVISION
         and cm["original_issue70_status"] == "FAIL" and cm["capture_manifest_sha256"] == sha(Path(capture)/"manifest.json"),
         "compiler actual source/capture/revision qualification")
    need(capture_manifest["model_revision"] == REVISION and capture_manifest["original_issue70_status"] == "FAIL"
         and capture_manifest["reference_self_consistency"] == "PASS"
         and capture_manifest["reference_precision"]["all_ops_FP64"] is False,
         "typed conditional reference, original FAIL retained")
    for key, description in capture_manifest["source_tensors"].items():
        need(description["dtype"] == "BF16" and description["shard_sha256"] ==
             capture_manifest["model_files"][description["shard"]]["sha256"], "actual source tensor/header shard binding "+key)
    spec, cfg = load_json(Path(compiled)/"spec.json"), load_json(Path(capture)/"config.json")
    need(spec["layers"] == cfg["layers"] == [0, 13]
         and (spec["hidden"], spec["intermediate"], spec["experts"], spec["topk"]) == (1536, 512, 40, 8)
         and cfg["residual_multiplier"] == 0.22 and cfg["rms_norm_eps"] == 1e-6
         and spec["runtime_no_float"] is True and spec["source_capture_manifest_sha256"] == sha(Path(capture)/"manifest.json"),
         "frozen actual-cut numerical contract")
    const, inputs = arrays(Path(compiled)/"constants.npz"), arrays(Path(compiled)/"inputs.npz")
    need(all(a.dtype.kind in "iu" for a in list(const.values())+list(inputs.values())), "integer-only runtime inputs/constants")
    report = load_json(Path(capture)/"report.json")
    need(report["status"] == "CAPTURE_REFERENCE_PASS" and report["original_issue70_status"] == "FAIL"
         and report["unchanged_gate"] == {"relative_l2_max": 2e-4, "max_abs_max": 2e-3}
         and len(report["checks"]) == 22, "unchanged capture replay gate and complete checks")
    need(all(r["error"]["relative_l2"] <= 2e-4 and r["error"]["max_abs"] <= 2e-3
             for r in report["checks"]), "source replay does not pass original gate")
    source = np.load(Path(capture)/"capture.npz", allow_pickle=False)
    references = np.load(Path(compiled)/"reference.npz", allow_pickle=False)
    key = "L%d." % layer
    for case in ("calibration", "evaluation"):
        tokens = source[case+".tokens"]
        need(tokens.shape == (72,) and tokens.dtype == np.int64, "B1 real72 tokens")
        equal(inputs[case+".tokens"], tokens, "compiler frozen token sequence")
        for candidate in (0, 13):
            name = case+".L%d." % candidate
            equal(inputs[name+"residual_q12"], fixed_encode(source[name+"residual"], 12),
                  "true residual fixed-format external cut")
    need(not np.array_equal(source["calibration.tokens"], source["evaluation.tokens"]), "calibration/evaluation separation")
    for case in ("calibration", "evaluation"):
        base = case+"."+key
        for field in ("residual", "norm", "router_logits", "ids", "gate", "expert_mid", "expert_down", "moe", "layer_output", "next_norm"):
            equal(references[base+field], source[base+field], "actual captured reference "+base+field)
    equal(references["weight."+key+"router"], source["weight."+key+"router"], "actual reference router weights")
    references.close()
    for name in ("post_gamma", "next_gamma"):
        raw = source["weight."+key+name]
        need(raw.shape == (1536,) and raw.dtype == np.float32, "actual BF16 gamma export")
        equal(const[key+name+"_q20"], fixed_encode(raw, 20), "static gamma Q20")
    for name, shape in (("gate_up", (40, 1024, 1536)), ("down", (40, 1536, 512))):
        raw = source["weight."+key+name]
        need(raw.shape == shape and raw.dtype == np.float32 and np.isfinite(raw).all(), "complete real40 static expert weights")
        q, m, e = weight_compiler(raw)
        equal(const[key+name+"_w8"], q, "all expert W8 "+name)
        equal(const[key+name+"_mant_q31"], m, "all expert Q31 "+name)
        equal(const[key+name+"_exp"], e, "all expert I16 exponent "+name)
    router = source["weight."+key+"router"]
    need(router.shape == (40, 1536) and router.dtype == np.float32, "actual all40 router weights")
    for bits in (8, 16):
        exps, codes = [], []
        for row in router:
            maximum = float(np.abs(row).max())
            e = ceil_power2(Fraction.from_float(maximum)/((1 << (bits-1))-1)) if maximum else 0
            need(-127 <= e <= 127, "router static exponent range")
            exps.append(e)
            codes.append(np.rint(np.ldexp(row.astype(np.float64), -e)))
        equal(const[key+"router_exp%d" % bits], np.asarray(exps, np.int16), "exact rational router power2 exponent")
        equal(const[key+"router_w%d" % bits], np.asarray(codes, np.int8 if bits == 8 else np.int16), "all static router codes")
    silu, exp2 = compiler_tables()
    equal(const["silu_lut_q12"], silu, "every Decimal SiLU LUT cell")
    equal(const["route_exp2_q24"], exp2, "every Decimal exp2 LUT cell")
    equal(const["residual_multiplier_q20"], fixed_encode(np.asarray(cfg["residual_multiplier"]), 20), "actual0.22 coefficient")
    need(spec["epsilon_q24"] == round(Fraction.from_float(cfg["rms_norm_eps"])*(1 << 24)), "actual epsilon Q24")
    source.close()
    return spec, const, inputs, cm, ca, capture_manifest, capture_artifacts


def check_runtime_source(path):
    """Check runtime call-graph functions rather than flagging the FP compiler."""
    tree = ast.parse(Path(path).read_text(encoding="utf-8-sig"))
    functions = {node.name: node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
    todo, seen = ["run_integer"], set()
    while todo:
        name = todo.pop()
        if name in seen:
            continue
        need(name in functions, "runtime function exists")
        seen.add(name)
        for node in ast.walk(functions[name]):
            need(not isinstance(node, ast.Constant) or type(node.value) is not float, "runtime FP constant")
            need(not isinstance(node, ast.Div), "runtime floating division")
            if isinstance(node, ast.Call):
                target = node.func.id if isinstance(node.func, ast.Name) else (node.func.attr if isinstance(node.func, ast.Attribute) else "")
                need(target not in {"float", "exp", "exp2", "log", "log2", "logaddexp", "sqrt", "rsqrt", "true_divide", "divide", "frexp"},
                     "runtime FP call "+target)
                if target in functions and target not in seen:
                    todo.append(target)
            if isinstance(node, ast.Attribute):
                need(node.attr not in {"float16", "float32", "float64", "bfloat16"}, "runtime floating dtype")
    need({"run_integer", "router", "router_dot", "dot8", "requant", "norm", "silu", "encode_dynamic"} <= seen,
         "complete runtime integer call graph")
    return sorted(seen)


def runtime_matches(result, expected):
    manifest, artifacts = verify_manifest(result, kind="granite-moe-run74-v1", statuses=("EXECUTED_COMPLETE",))
    actual = arrays(Path(result)/"runtime.npz")
    need(set(actual) == set(expected), "complete runtime stage set")
    for key in expected:
        equal(actual[key], expected[key], key)
    return manifest, artifacts, actual


def metric(actual, target):
    a, b = np.asarray(actual, np.float64), np.asarray(target, np.float64)
    need(a.shape == b.shape and a.size > 0 and np.isfinite(a).all() and np.isfinite(b).all(), "finite matching diagnostic")
    return {"relative_l2": float(np.linalg.norm(a-b)/max(np.linalg.norm(b), 1e-30)),
            "max_abs": float(np.abs(a-b).max())}


def metric_equal(actual, expected, label):
    need(set(actual) == set(expected) and all(math.isclose(actual[k], v, rel_tol=3e-11, abs_tol=1e-12)
                                            for k, v in expected.items()), "postrun diagnostic "+label)


def verify(result, compiled, capture, producer_source, compiler_source=None):
    result, compiled, capture = map(Path, (result, compiled, capture))
    report = load_json(result/"report.json")
    layer, bits, case = report["layer"], report["router_bits"], report["split"]
    need(layer in (0, 13) and bits in (8, 16) and case in ("calibration", "evaluation"), "predeclared8-case matrix")
    spec, const, inputs, cm, ca, cpm, cpa = check_compiler(compiled, capture, layer, compiler_source or producer_source)
    graph = check_runtime_source(producer_source)
    expected, counts = replay(inputs[case+".L%d.residual_q12" % layer], const, spec, layer, bits)
    manifest, artifacts, actual = runtime_matches(result, expected)
    source_binding(manifest, {"granite_chain_sha256": producer_source})
    need(manifest["producer_sha256"] == sha(producer_source) and manifest["compiled_manifest_sha256"] == sha(compiled/"manifest.json")
         and manifest["model_revision"] == REVISION and manifest["original_issue70_status"] == "FAIL", "runtime frozen source/compiler/revision")
    need(report["status"] == "EXECUTED_COMPLETE" and report["runtime_no_float"] is True and report["software_reference_only"] is True
         and report["tokens"] == 72 and report["prefill_tokens"] == 64 and report["decode_tokens"] == 8
         and report["complete_selected_paths"] == 576 and report["precision_contract"] == spec,
         "bounded complete integer qualification")
    ids = expected["router.ids"]
    need(report["expert_hit_counts"] == np.bincount(ids.reshape(-1), minlength=40).tolist(), "actual selected-expert workload")
    # FP references first become visible after every integer stage is received.
    ref, diag = arrays(compiled/"reference.npz"), arrays(result/"diagnostic.npz")
    base = case+".L%d." % layer
    for key, target in (("norm_q12", "norm"), ("moe_q12", "moe"), ("layer_output_q12", "layer_output"), ("next_norm_q12", "next_norm")):
        decoded = expected[key].astype(np.float64)/4096
        metric_equal(report["reference_errors"][key], metric(decoded, ref[base+target]), key)
        for phase, selection in (("prefill64", slice(0, 64)), ("decode8", slice(64, 72))):
            metric_equal(report["phase_errors"][key][phase], metric(decoded[selection], ref[base+target][selection]), key+phase)
    same_logits = (expected["norm_q12"].astype(np.float64)/4096) @ ref["weight.L%d.router" % layer].astype(np.float64).T
    need(set(diag) == {"same_current_norm_FP64_logits", "same_current_norm_FP64_ids"}, "separate postrun diagnostic archive")
    need(diag["same_current_norm_FP64_logits"].dtype == np.float64
         and diag["same_current_norm_FP64_logits"].shape == (72, 40)
         and np.allclose(diag["same_current_norm_FP64_logits"], same_logits, rtol=1e-12, atol=1e-12),
         "postrun same-input FP64 logit recomputation")
    same_ids = np.asarray([sorted(range(40), key=lambda j: (-float(row[j]), j))[:8]
                           for row in diag["same_current_norm_FP64_logits"]], np.int64)
    equal(diag["same_current_norm_FP64_ids"], same_ids, "postrun same-input FP64 IDs")
    changed = lambda target: int(np.any(np.sort(ids, axis=1) != np.sort(target, axis=1), axis=1).sum())
    need(report["route_changes_vs_native_model64"] == changed(ref[base+"ids"])
         and report["route_changes_vs_same_current_integer_norm_FP64"] == changed(same_ids)
         and report["same_input_FP64_router_is_postrun_diagnostic"] is True, "separate hidden/router error sources")
    matched_actual, matched_reference = [], []
    for token in range(72):
        for rank, expert in enumerate(ids[token]):
            matches = np.flatnonzero(ref[base+"ids"][token] == expert)
            if matches.size:
                matched_actual.append(expected["down_q12"][token, rank].astype(np.float64)/4096)
                matched_reference.append(ref[base+"expert_down"][token, int(matches[0])])
    need(report["matched_native_expert_paths"] == len(matched_actual), "matched-ID diagnostic coverage")
    if matched_actual:
        metric_equal(report["expert_down_error_matched_ID_only"], metric(matched_actual, matched_reference), "matched-ID expert error")
    else:
        need(report["expert_down_error_matched_ID_only"] is None, "empty matched-ID diagnostics")
    ops = report["ops"]
    exact_ops = {"expert_S8_MACs": 72*8*(1024*1536+1536*512),
                 "router_S8_MACs": 72*40*1536*(1 if bits == 8 else 9),
                 "norm_square32": 2*72*1536, "norm_gamma_multiply32": 2*72*1536,
                 "norm_reduce_add_U128": 2*72*1535,
                 "norm_division128_iterations": 2*72*1537*128,
                 "norm_isqrt128_iterations": 2*72*64,
                 "norm_numerator_shift_I128": 2*72*1536,
                 "norm_RNE_div_finalize_I128": 2*72*1536,
                 "router_compare_wide_candidate": 72*40*40, "router_exp2_LUT_reads": 576,
                 "router_log2e_wide_multiplications": 576, "router_Q15_exact_divisions": 576,
                 "silu_LUT_reads": 72*8*512,
                 "dynamic_absmax_elements": 2*72*1536+72*8*512,
                 "multiply_32x32": 72*8*(1024+512+1536)+72*1536,
                 "multiply_32x16": 72*8*1536,
                 "add_i64": 72*1536*9+(9*72*40 if bits == 16 else 0),
                 "RNE_shift_i64": 2804544+(9*72*40 if bits == 16 else 0)}
    exact_ops["wide_S8_digit_products"] = exact_ops["multiply_32x32"]*25+exact_ops["multiply_32x16"]*15
    exact_ops["wide_digit_shift_add"] = exact_ops["multiply_32x32"]*24+exact_ops["multiply_32x16"]*14
    if bits == 16:
        exact_ops["router_S16_full_lowered_rows"] = 72
    need(all(ops.get(name) == value for name, value in exact_ops.items()), "complete-chain arithmetic obligations")
    need(not set(ops)-set(exact_ops)-{"dynamic_scalar_RNE_probes"}, "known reported integer operations")
    nonlinear = report["nonlinear_counts"]
    need(nonlinear["silu_negative_asymptote"] == int((expected["expert_gate_q12"] < -(32 << 12)).sum())
         and nonlinear["silu_positive_identity"] == int((expected["expert_gate_q12"] > (32 << 12)).sum()), "actual SiLU outside-domain counts")
    payload = report["actual_payload"]
    values = {"runtime_npz_bytes": (result/"runtime.npz").stat().st_size,
              "one_layer_expert_W8_bytes": 94371840, "one_layer_expert_scale_bytes": 614400,
              "router_weight_bytes": const["L%d.router_w%d" % (layer, bits)].nbytes,
              "router_weight_exponent_bytes": 80, "perrow_expert_input_delta_bytes": 2,
              "pertoken_8expert_mid_delta_bytes": 16, "gate_route_payload_bytes_pertoken": 24,
              "silu_LUT_bytes": 65540, "router_exp2_LUT_bytes": 8196,
              "full_8expert_down_S32_bytes_pertoken": 49152, "full_merge_S64_bytes_pertoken": 12288}
    need(payload == values, "actual formats/metadata/states inventory")
    return {"status": "PASS", "schema": "granite-independent-receipt74-v1", "layer": layer, "router_bits": bits, "split": case,
            "tokens": 72, "complete_selected_paths": 576, "integer_stages_checked": len(expected),
            "router_full_S8_partial_outputs_checked": expected["router.partials"].size,
            "gate_up_INT32_outputs_checked": expected["gate_up_acc32"].size,
            "down_INT32_outputs_checked": expected["down_acc32"].size,
            "merge_prefix_I64_outputs_checked": expected["merge_prefix64"].size,
            "runtime_callgraph_no_FP": graph, "producer_manifest": descriptor(result/"manifest.json"),
            "compiled_manifest": descriptor(compiled/"manifest.json"), "capture_manifest": descriptor(capture/"manifest.json"),
            "artifacts": artifacts, "compiled_artifacts": ca, "capture_artifacts": cpa,
            "compiler_layer_checked": layer, "tables_checked": {"SiLU": 16385, "exp2": 2049},
            "reference_errors": report["reference_errors"], "route_changes_vs_native_model64": report["route_changes_vs_native_model64"],
            "route_changes_vs_same_current_integer_norm_FP64": report["route_changes_vs_same_current_integer_norm_FP64"],
            "limits": ["All selected8 real expert integer paths from a true external residual cut, not a complete integer model",
                       "Conditional model64 includes framework FP32 norm/RoPE/attention casts; original native FAIL retained",
                       "Compiler and postrun FP diagnostics separate; no model quality, target integer speed, RTL/PPA or physical-boundary acceptance"]}, expected


def negatives(result, expected, out):
    records = []
    for name, key in (("actual_router_ID", "router.ids"), ("integer_expert_mid", "expert_mid_q12"), ("wide_merge_prefix", "merge_prefix64")):
        destination = Path(out)/("negative-"+name)
        shutil.copytree(result, destination)
        value = arrays(destination/"runtime.npz")
        value[key].flat[0] = int(value[key].flat[0])+1
        np.savez_compressed(destination/"runtime.npz", **value)
        replace_artifact_hash(destination, "runtime.npz")
        verify_manifest(destination, statuses=("EXECUTED_COMPLETE",))
        try:
            runtime_matches(destination, expected)
        except ValueError as error:
            need(str(error).startswith("integer stage "), "negative must reach independent mathematical layer")
            records.append({"name": name, "status": "REJECTED_AFTER_SHA_REWRITE", "reason": str(error),
                            "mutated_artifact": descriptor(destination/"runtime.npz")})
        else:
            raise ValueError("mutated integer artifact accepted "+name)
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("result", "compiled", "capture", "producer-source", "binding", "out"):
        parser.add_argument("--"+key, type=Path, required=True)
    parser.add_argument("--compiler-source", type=Path)
    parser.add_argument("--skip-negatives", action="store_true")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    binding = load_json(args.binding)
    need(binding.get("receive_granite_sha256") == sha(__file__)
         and binding.get("audit_io74_sha256") == sha(Path(__file__).with_name("audit_io74.py")), "independent receiver source binding")
    receipt, expected = verify(args.result, args.compiled, args.capture, args.producer_source, args.compiler_source)
    receipt["negative_tests"] = [] if args.skip_negatives else negatives(args.result, expected, args.out)
    receipt["negative_status"] = "NOT_EXECUTED" if args.skip_negatives else "PASS_ACTUAL_SHA_REWRITE"
    receipt["source"] = binding
    save_json(args.out/"receipt.json", receipt)
    print(receipt["status"], receipt["layer"], receipt["router_bits"], receipt["split"], flush=True)


if __name__ == "__main__":
    main()
