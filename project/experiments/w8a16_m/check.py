"""Independent integer/Fraction vectors for candidate group M and scale RTL.

Run on a Slurm compute node. This is unit evidence, not full-model or physical
qualification. No Torch/Numpy dependency and no use of the RTL rounding method.
"""
import argparse
from fractions import Fraction
import hashlib
import json
import os
from pathlib import Path
import random
import subprocess


def pack(fields):
    value = 0
    for width, item in fields:
        value = (value << width) | (int(item) & ((1 << width) - 1))
    return value


def vec(values, width):
    return sum((int(v) & ((1 << width) - 1)) << (width * i)
               for i, v in enumerate(values))


def fp16_exact(bits):
    exponent, fraction = (bits >> 10) & 31, bits & 1023
    if bits >> 15 or exponent == 31 or bits & 32767 == 0:
        raise ValueError("scale must be positive finite nonzero")
    mantissa, shift = (fraction, -24) if exponent == 0 else (fraction + 1024, exponent - 25)
    return Fraction(mantissa * (1 << max(0, shift)), 1 << max(0, -shift))


def s32(value):
    if not -(1 << 31) <= value < (1 << 31):
        raise ValueError("S32 overflow")
    return value


def scale_reference(partials, scales, previous, bias, count, first, final, shift):
    result = [0] * 8
    try:
        if not 1 <= count <= 8 or not 0 <= shift <= 17:
            raise ValueError("descriptor")
        for i in range(count):
            term = s32(round(Fraction(partials[i]) * fp16_exact(scales[i]) * (1 << shift)))
            result[i] = s32(term + (0 if first else previous[i]))
            if final:
                result[i] = s32(result[i] + bias[i])
    except ValueError:
        return [0] * 8, 1
    return result, 0


def write_vectors(path, values, width):
    path.write_text("".join(f"{v:0{(width + 3)//4}x}\n" for v in values), encoding="ascii")


def generate_scale(rng, root):
    rows = []
    edges = [-(1 << 31), -(1 << 29), -32768, -17, -5, -3, -1, 0,
             1, 3, 5, 17, 32767, (1 << 29), (1 << 31) - 1]
    scaleset = [0, 1, 1023, 1024, 0x1000, 0x3000, 0x3400, 0x3800,
                0x3C00, 0x3C01, 0x4000, 0x7BFF, 0x7C00, 0x7E00, 0x8001, 0xBC00]
    for tag in range(4096):
        count = rng.choice([0, 1, 2, 7, 8, 9]) if tag % 7 == 0 else rng.randrange(1, 9)
        first, final = rng.randrange(2), rng.randrange(2)
        shift = rng.choice([0, 1, 2, 7, 16, 17, 18, 63]) if tag % 5 == 0 else rng.randrange(18)
        ps = [rng.choice(edges) if tag % 3 else rng.randrange(-(1 << 31), 1 << 31) for _ in range(8)]
        scales = [rng.choice(scaleset) if tag % 4 else rng.randrange(1, 0x7C00) for _ in range(8)]
        previous = [rng.choice(edges) for _ in range(8)]
        bias = [rng.choice(edges) for _ in range(8)]
        expected, error = scale_reference(ps, scales, previous, bias, count, first, final, shift)
        rows.append(pack([(32, tag), (4, count), (1, first), (1, final), (6, shift),
                          (256, vec(ps, 32)), (128, vec(scales, 16)),
                          (256, vec(previous, 32)), (256, vec(bias, 32)),
                          (256, vec(expected, 32)), (1, error)]))
    # Directed positive/negative ties, subnormal scales, exact output bounds,
    # prefix overflow before bias, and invalid inactive lanes. Fraction.round
    # remains the oracle, independently of signed shift/remainder RTL.
    for partial in [-2147483648, -9, -7, -5, -3, -1, 0, 1, 3, 5, 7, 9, 2147483647]:
        for scale in [1, 1024, 0x3400, 0x3800, 0x3C00, 0x4000]:
            for shift in [0, 1, 17]:
                for first, final, prior, add_bias in [(1, 0, 0, 0), (0, 1, -1, 1),
                                                     (0, 1, 2147483647, -2147483647)]:
                    ps, scales = [partial] + [0] * 7, [scale] + [0x7C00] * 7
                    previous, bias = [prior] * 8, [add_bias] * 8
                    expected, error = scale_reference(ps, scales, previous, bias, 1, first, final, shift)
                    rows.append(pack([(32, len(rows)), (4, 1), (1, first), (1, final), (6, shift),
                                      (256, vec(ps, 32)), (128, vec(scales, 16)),
                                      (256, vec(previous, 32)), (256, vec(bias, 32)),
                                      (256, vec(expected, 32)), (1, error)]))
    write_vectors(root / "scale.hex", rows, 1197)
    return len(rows), sum(not (row & 1) for row in rows)


def generate_m(rng, root, model_file):
    inputs, outputs = [], []
    serial = 0
    def beat(first, last, tag, group, offset, k, n, a, w):
        inputs.append(pack([(1, first), (1, last), (32, tag), (8, group), (8, offset),
                            (5, k), (4, n), (256, vec(a, 16)), (1024, vec(w, 8))]))
    def response(tag, n, values, error):
        outputs.append(pack([(32, tag), (4, n), (256, vec(values, 32)), (1, error)]))
    for serial in range(384):
        group = 16 if serial % 3 == 0 else 128
        n = rng.randrange(1, 9)
        sums = [0] * 8
        offset = 0
        while offset < group:
            k_count = min(16 if serial % 6 else rng.randrange(1, 17), group - offset)
            a = [rng.choice([-32768, 32767, -1, 0, 1]) if serial % 5 == 0 else rng.randrange(-32768, 32768) for _ in range(16)]
            w = [rng.choice([-128, 127, -1, 0, 1]) if serial % 5 == 0 else rng.randrange(-128, 128) for _ in range(128)]
            if offset and serial % 4 == 0:
                # Wrong-offset packet must be rejected without destroying
                # the valid partial, then the original packet is retried.
                beat(0, 0, serial, group, 0, k_count, n, a, w)
                response(serial, n, [0] * 8, 1)
            for lane in range(n):
                sums[lane] += sum(a[k] * w[lane * 16 + k] for k in range(k_count))
            beat(offset == 0, offset + k_count == group, serial, group, offset, k_count, n, a, w)
            offset += k_count
        response(serial, n, sums, 0)
        if serial % 13 == 0:
            # Idle continuation and unsupported group sizes are explicit errors.
            beat(0, 1, serial + 10000, 16, 0, 16, n, [0] * 16, [0] * 128)
            response(serial + 10000, n, [0] * 8, 1)
            beat(1, 1, serial + 20000, 32, 0, 16, n, [0] * 16, [0] * 128)
            response(serial + 20000, n, [0] * 8, 1)
            for bad_k, bad_n, bad_offset in [(0, 8, 0), (17, 8, 0), (16, 0, 0),
                                             (16, 9, 0), (16, 8, 16)]:
                beat(1, 1, serial + 30000, 16, bad_offset, bad_k, bad_n, [0] * 16, [0] * 128)
                response(serial + 30000, bad_n, [0] * 8, 1)
    # Historical actual-checkpoint A16/W8 groups from four FFNs. Recompute
    # every old 40-bit prefix independently, then check new raw S32 output.
    # Down A came from the historical Mid64 profile: this is real arithmetic
    # data, not a claim that new Mid32/small-G deployment has been verified.
    model_bytes = model_file.read_bytes()
    assert hashlib.sha256(model_bytes).hexdigest() == "e2767a3007e4dcd2249171616ec027c17067d9daac5c2af34a19404185663c83"
    def unpack_signed(text, width, count):
        bits = int(text, 16)
        result = [(bits >> (width * i)) & ((1 << width) - 1) for i in range(count)]
        return [v - (1 << width) if v & (1 << (width - 1)) else v for v in result]
    model_groups = 0
    partial = [0] * 8
    for line in model_bytes.decode("ascii").splitlines():
        ctx, first, last, k, n, offset, a_hex, w_hex, old_hex = line.split()
        first, last, k, n, offset = map(int, [first, last, k, n, offset])
        assert int(ctx) == 0 and n == 8 and k == 16
        if first:
            assert offset == 0
            partial = [0] * 8
        a, w = unpack_signed(a_hex, 16, 16), unpack_signed(w_hex, 8, 128)
        for lane in range(n):
            partial[lane] += sum(a[i] * w[lane * 16 + i] for i in range(k))
            s32(partial[lane])
        assert partial == unpack_signed(old_hex, 40, 8), "historical prefix/layout mismatch"
        beat(first, last, 50000 + model_groups, 128, offset, k, n, a, w)
        if last:
            assert offset == 112
            response(50000 + model_groups, n, partial, 0)
            model_groups += 1
    assert model_groups == 24
    write_vectors(root / "m-in.hex", inputs, 1339)
    write_vectors(root / "m-out.hex", outputs, 293)
    return len(inputs), len(outputs), model_groups


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--verilator", required=True)
    parser.add_argument("--jobs", type=int, default=10)
    args = parser.parse_args()
    if not os.environ.get("SLURM_JOB_ID"):
        raise RuntimeError("RTL execution requires a Slurm compute job")
    args.out.mkdir(parents=True, exist_ok=False)
    rng = random.Random(args.seed)
    count, valid = generate_scale(rng, args.out)
    mi, mo, model_groups = generate_m(rng, args.out,
        args.source / "project/experiments/w8a16_m/vectors/closure-m-run38.txt")
    (args.out / "counts.vh").write_text(f"`define SCALE_COUNT {count}\n`define M_IN_COUNT {mi}\n`define M_OUT_COUNT {mo}\n", encoding="ascii")
    results = {}
    for unit, rtl in [("scale", "scale_group_s32"), ("m", "m_group_s32")]:
        obj = args.out / ("obj-" + unit)
        top = "tb_" + unit
        build = [args.verilator, "--binary", "--timing", "--assert", "-Wall",
                 "-Wno-BLKSEQ", "-Wno-TIMESCALEMOD", "--top-module", top,
                 "-j", str(args.jobs), "-I" + str(args.out), "--Mdir", str(obj),
                 str(args.source / "project/rtl/w8a16_v1" / (rtl + ".sv")),
                 str(args.source / "project/experiments/w8a16_m" / ("tb_" + unit + ".sv"))]
        environment = dict(os.environ)
        environment.pop("VERILATOR_ROOT", None)
        with (args.out / (unit + "-build.log")).open("w") as log:
            subprocess.run(build, cwd=args.out, check=True, env=environment,
                           stdout=log, stderr=subprocess.STDOUT)
        process = subprocess.run([str(obj / ("V" + top))], cwd=args.out,
                                 env=environment, text=True, capture_output=True)
        (args.out / (unit + ".log")).write_text(process.stdout + process.stderr, encoding="utf-8")
        if process.returncode or "PASS " not in process.stdout:
            raise RuntimeError(f"{unit} RTL failed: {process.stdout} {process.stderr}")
        results[unit] = process.stdout.strip()
    hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in args.out.iterdir() if p.is_file()}
    report = dict(seed=args.seed, scale_vectors=count, scale_success_vectors=valid,
                  scale_fault_vectors=count-valid, m_beats=mi, m_responses=mo,
                  actual_checkpoint_raw_groups=model_groups,
                  results=results, sha256=hashes, qualification="candidate arithmetic units only; not physical, model, context-controller, or combined-program evidence")
    (args.out / "result.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
