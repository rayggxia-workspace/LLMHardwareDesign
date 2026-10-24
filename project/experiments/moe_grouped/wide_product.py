"""Execute S8 digit products and byte carry recombination, never native I128.

Host NumPy implements a software reference, not an INT8 timing measurement.
The returned core count excludes digit extraction, constant shift construction,
operand transport and RNE; the service model must charge those separately.
"""
import argparse
import json
from pathlib import Path
import time

import numpy as np

from audit_io74 import need, load_json, save_json, sha, descriptor, verify_manifest


def digits(value, width):
    value = np.asarray(value)
    need(value.dtype.kind == "i", "signed integer operand")
    value = value.astype(np.int64).reshape(-1)
    need(width in (32, 64), "declared operand width")
    need(all(-(1 << (width - 1)) <= int(v) < (1 << (width - 1)) for v in value),
         "operand outside declared format")
    count = 1 + (width - 8 + 6) // 7
    result = []
    for index in range(count):
        part = value >> (7 * index)
        if index != count - 1:
            part = part & 127
        need(np.all((part >= -128) & (part <= 127)), "S8 digit")
        result.append(part.astype(np.int16))
    return result


def multiply_bytes(left, right, left_width):
    """Signed-high radix128 products with 8/16 explicit carry bytes."""
    aa, bb = digits(left, left_width), digits(right, 32)
    need(aa[0].shape == bb[0].shape, "operand count")
    nbytes = 8 if left_width == 32 else 16
    acc = np.zeros((len(aa[0]), nbytes), dtype=np.uint8)
    first = True
    for i, x in enumerate(aa):
        for j, y in enumerate(bb):
            # The operands fit signed8 and each product fits signed16.
            product = x * y
            shift = 7 * (i + j)
            carry = np.zeros(len(product), np.uint16)
            for byte in range(nbytes):
                offset = 8 * byte - shift
                if offset >= 16:
                    term = np.where(product < 0, 255, 0).astype(np.uint16)
                elif offset >= 0:
                    term = ((product >> offset) & 255).astype(np.uint16)
                elif offset > -8:
                    term = ((product.astype(np.int32) << (-offset)) & 255).astype(np.uint16)
                else:
                    term = np.zeros(len(product), np.uint16)
                if first:
                    acc[:, byte] = term.astype(np.uint8)
                else:
                    total = acc[:, byte].astype(np.uint16) + term + carry
                    acc[:, byte] = (total & 255).astype(np.uint8)
                    carry = total >> 8
            first = False
    terms = len(aa) * len(bb)
    counts = {"products": len(acc), "S8_products": len(acc) * terms,
              "byte_add_with_carry": len(acc) * (terms - 1) * nbytes,
              "core_control_slots": len(acc) * (terms - 1) * 2,
              "core_byte_lane_slots": len(acc) * (terms + (terms - 1) * (nbytes + 2)),
              "declared_output_bits": nbytes * 8}
    return acc, counts


def words(acc):
    low = np.zeros(len(acc), np.uint64)
    for index in range(8):
        low |= acc[:, index].astype(np.uint64) << (8 * index)
    if acc.shape[1] == 8:
        high = np.where((acc[:, 7] & 128) != 0, -1, 0).astype(np.int64)
    else:
        high_u = np.zeros(len(acc), np.uint64)
        for index in range(8):
            high_u |= acc[:, 8 + index].astype(np.uint64) << (8 * index)
        high = high_u.view(np.int64)
    return high, low


def main():
    parser = argparse.ArgumentParser(__doc__)
    for name in ("result", "compiled", "math-receipt", "binding", "out"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    need(not args.out.exists(), "refuse overwrite")
    binding = load_json(args.binding)
    need(binding["wide_product_sha256"] == sha(__file__)
         and binding["audit_io74_sha256"] == sha(Path(__file__).with_name("audit_io74.py")),
         "bound sources")
    _, checked = verify_manifest(args.result)
    verify_manifest(args.compiled)
    receipt = load_json(args.math_receipt)
    need(receipt["status"] == "PASS" and receipt["artifacts"] == checked,
         "independent math reception bound to exact data")
    report = load_json(args.result / "report.json")
    need(report["compiled_manifest_sha256"] == sha(args.compiled / "manifest.json"),
         "compiled source")
    with np.load(args.result / "outproj.npz", allow_pickle=False) as data:
        left = data["aligned_sum_i64"]
        expected_hi = data["rq_product_hi_i64"].reshape(-1)
        expected_lo = data["rq_product_lo_u64"].reshape(-1)
    with np.load(args.compiled / "constants.npz", allow_pickle=False) as data:
        right = np.broadcast_to(data["out_scale_q31"], left.shape).reshape(-1)
    started = time.monotonic()
    result, counts = multiply_bytes(left.reshape(-1), right, 32 if report["groups"] == 1 else 64)
    hi, lo = words(result)
    need(np.array_equal(hi, expected_hi) and np.array_equal(lo, expected_lo),
         "every signed product matches independent integer result")
    args.out.mkdir()
    np.savez_compressed(args.out / "products.npz", product_bytes=result)
    save_json(args.out / "report.json", {
        "status": "PASS_S8_BYTE_RECONSTRUCTION", "group_k": report["group_k"],
        "counts": counts, "all_products_equal": True,
        "elapsed_host_seconds": time.monotonic() - started,
        "result_manifest": descriptor(args.result / "manifest.json"),
        "compiled_manifest": descriptor(args.compiled / "manifest.json"),
        "math_receipt": descriptor(args.math_receipt),
        "limits": ["Software S8 operand/digit and byte-carry semantics, not native kernel speed or RTL.",
                   "Core counts exclude extraction, constant-shift construction, transport and RNE; service charges these separately."]})
    save_json(args.out / "manifest.json", {
        "schema": "issue74-wide-product-v1", "status": "EXECUTED", "source": binding,
        "artifacts": [{"path": name, **descriptor(args.out / name)}
                      for name in ("report.json", "products.npz")]})
    print("PASS_S8_BYTE_RECONSTRUCTION", len(result), flush=True)


if __name__ == "__main__":
    main()
