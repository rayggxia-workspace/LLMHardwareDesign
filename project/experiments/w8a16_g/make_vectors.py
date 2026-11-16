"""Produce exact oracle vectors and validate the generated constant RTL table."""
import argparse
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import random
import re

from reference import TABLE, LIMIT, activation, packet, rne

ROOT = Path(__file__).resolve().parents[3]


def packed(values):
    return sum((v & 0xffffffff) << (32*i) for i, v in enumerate(values))


def vectors():
    # A complete 128-value Mid frame: 64 consecutive two-active-lane packets.
    for i in range(64):
        yield [-LIMIT+1+i*16384, LIMIT-1-i*16384], [65536, -65536], True, 3
    special = [-(1 << 31), -LIMIT-1, -LIMIT, -LIMIT+1, -8193, -8192, -8191,
               -4097, -4096, -4095, -1, 0, 1, 4095, 4096, 4097,
               8191, 8192, 8193, LIMIT-1, LIMIT, LIMIT+1, (1 << 31)-1]
    for i, gate in enumerate(special):
        for up in [-(1 << 31), -65537, -65536, -1, 0, 1, 65535, 65536, 65537, (1 << 31)-1]:
            for gated in [False, True]:
                for mask in [0, 1, 2, 3]:
                    yield [gate, special[-i-1]], [up, -up if up != -(1 << 31) else up], gated, mask
    rng = random.Random(250257)
    for _ in range(4096):
        gates = [rng.randrange(-(1 << 31), 1 << 31) if rng.randrange(5) == 0
                 else rng.randrange(-LIMIT*2, LIMIT*2) for _ in range(2)]
        ups = [rng.randrange(-(1 << 31), 1 << 31) for _ in range(2)]
        yield gates, ups, bool(rng.randrange(2)), rng.randrange(4)
    for gates, ups in model_inputs():
        yield gates, ups, True, 3


def unpack(text, bits):
    word = int(text, 16)
    result = []
    for lane in range(2):
        value = (word >> (bits*lane)) & ((1 << bits)-1)
        result.append(value-(1 << bits) if value & (1 << (bits-1)) else value)
    return result


def model_inputs():
    source = Path(__file__).with_name("reference_source")
    provenance = json.loads((source/"model-provenance.json").read_text())
    data = (source/"model-g-vectors.txt").read_bytes()
    assert hashlib.sha256(data).hexdigest() == provenance["vector_sha256"]
    assert len(data.splitlines()) == 2048
    for name, record in provenance["members"].items():
        assert hashlib.sha256((source/name).read_bytes()).hexdigest() == record["sha256"]
    # The old packet's expected value is a wide unrounded product from LUT2049.
    # Verify its provenance numerically, then replace it with the new oracle.
    old_table = [round(x/(1+math.exp(-x))*65536) for x in (i/64-16 for i in range(2049))]
    def old_activation(value):
        if value <= -LIMIT:
            return 0
        if value >= LIMIT:
            return value
        index, fraction = divmod(value+LIMIT, 1024)
        return old_table[index]+rne((old_table[index+1]-old_table[index])*fraction, 10)
    for row in data.decode().splitlines():
        gate, up, old_product = row.split()
        gates, ups, products = unpack(gate, 32), unpack(up, 32), unpack(old_product, 64)
        assert [old_activation(g)*u for g, u in zip(gates, ups)] == products
        assert not packet(gates, ups, True, 3)[1], "real model packet exceeds Mid S32 profile"
        yield gates, ups


def check_sources():
    source = Path(__file__).with_name("reference_source")
    provenance = json.loads((source/"provenance.json").read_text())
    for name, row in provenance["members"].items():
        assert hashlib.sha256((source/name).read_bytes()).hexdigest() == row["sha256"]
    assert hashlib.sha256(Path(__file__).with_name("lut_q16.json").read_bytes()).hexdigest() == provenance["lut_sha256"]
    rtl = (ROOT/"project/rtl/w8a16_v1/g_s32.sv").read_text()
    actual = [(int(i), -int(v) if sign else int(v)) for i, sign, v in
              re.findall(r"9'd(\d+): lut = (-?)32'sd(\d+);", rtl)]
    assert actual == list(enumerate(TABLE)), "RTL table differs from frozen LUT257"
    for shift in [0, 1, 13, 16, 31, 63]:
        for v in [-2**63, -65537, -32769, -32768, -3, -1, 0, 1, 3, 32768, 65537, 2**63-1]:
            assert rne(v, shift) == round(Fraction(v, 1 << shift))
    assert activation(-LIMIT) == 0 and activation(LIMIT) == LIMIT


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    check_sources()
    values = list(vectors())
    args.out.mkdir(parents=True, exist_ok=True)
    rows = []
    faults = 0
    for gates, ups, gated, mask in values:
        result, error = packet(gates, ups, gated, mask)
        faults += error
        rows.append(f"{packed(gates):016x} {packed(ups):016x} {int(gated)} {mask:x} {packed(result):016x} {int(error)}")
    payload = (str(len(rows))+"\n"+"\n".join(rows)+"\n").encode()
    (args.out/"vectors.txt").write_bytes(payload)
    receipt = dict(passed=True, vectors=len(rows), packet_faults=faults,
        vector_sha256=hashlib.sha256(payload).hexdigest(), table_entries=len(TABLE),
        logical_table_bytes=len(TABLE)*4, rtl_table_matches=True, actual_model_packets=2048,
        actual_model_values=4096, actual_model_groups=[dict(layer=l, batch=b, packets=512) for l, b in [(0,0),(2,0),(17,3),(35,5)]],
        actual_model_scope="Exact historical gate/up tensors, not a new complete model run or complete FFN proof",
        scope="Exact scalar PR249 math, input boundaries, signed ties, packet errors; RTL execution is separate")
    (args.out/"oracle.json").write_text(json.dumps(receipt, indent=2)+"\n", encoding="utf-8", newline="\n")
    print(json.dumps(receipt))


if __name__ == "__main__":
    main()
