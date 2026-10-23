"""Independent real-input binding: exact Fraction quantization, no run/core imports."""
from fractions import Fraction
import hashlib
import io
import json
import math
from pathlib import Path
import sys
import zipfile
import numpy as np

root = Path(__file__).resolve().parents[3]
directory = Path(sys.argv[1])
cfg = json.loads((root / "project/experiments/kv_scale/experiment.json").read_text())
raw = (root / cfg["source_archive"]).read_bytes()
assert hashlib.sha256(raw).hexdigest() == cfg["source_archive_sha256"]
with zipfile.ZipFile(io.BytesIO(raw)) as z:
    raw = z.read(cfg["capture_member"])
assert hashlib.sha256(raw).hexdigest() == cfg["capture_sha256"]
inputs = np.load(io.BytesIO(raw), allow_pickle=False)
cases = json.loads((directory / "integers.json").read_text())
reports = json.loads((directory / "numeric.json").read_text())
report_by_key = {(r["name"], r["block"], r["probability_bits"], r["input_profile"]): r for r in reports}

def power(e):
    return Fraction(2**e) if e >= 0 else Fraction(1, 2**-e)

def exponent(rows):
    peak = max(abs(v) for row in rows for v in row)
    if not peak:
        return -24
    e = -120
    while peak > 127 * power(e):
        e += 1
    return e

values = scale_checks = 0
for c in cases:
    name = c["name"]
    q, k, v = ([[[Fraction(float(x)) for x in row] for row in inputs[name+"."+field]]
               for field in ("query", "key", "value")])
    report = report_by_key[(name, c["block"], c["probability_bits"], c["input_profile"])]
    g = [0] * len(q[0])
    if c["input_profile"] == "offline_dyadic_QK_balance":
        g = [max(-8, min(8, round(0.5*math.log2(float(max(abs(row[d]) for row in k))
                       / float(max(abs(row[d]) for row in q)))))) for d in range(len(q[0]))]
        assert g == report["balance_exponents_i8"]
        q = [[x*power(g[d]) for d, x in enumerate(row)] for row in q]
        k = [[x*power(-g[d]) for d, x in enumerate(row)] for row in k]
    for field, data in (("q", q), ("k", k), ("v", v)):
        width = 1 if field == "q" else c["block"]
        exps = c[field + "_exponents"]
        for start in range(0, len(data), width):
            e = exponent(data[start:start+width])
            assert e == exps[start // width]
            scale_checks += 1
            for t in range(start, min(start+width, len(data))):
                expected = [max(-127, min(127, round(x / power(e)))) for x in data[t]]
                assert expected == c[field + "_i8"][t]
                values += len(expected)
    positions = inputs[name+".query_positions"]
    assert c["allowed"] == [[t <= int(pos) for t in range(len(k))] for pos in positions]

print(json.dumps({"status": "PASS", "case_count": len(cases), "exact_input_values": values,
    "scale_exponents": scale_checks, "source_archive_sha256": cfg["source_archive_sha256"],
    "capture_sha256": cfg["capture_sha256"], "method": "Fraction of observed FP32, scalar max and dyadic scale; no target quantizer imports"}))
