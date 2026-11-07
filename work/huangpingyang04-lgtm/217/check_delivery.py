"""Read-only verification of the committed copper result package."""
from hashlib import sha256
import json
import math
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def rows(path, header=False):
    result = {}
    with path.open() as stream:
        if header:
            next(stream)
        for line in stream:
            name, *values = line.split()
            assert name not in result
            result[name] = list(map(float, values))
    return result


def close(a, b):
    assert math.isclose(a, b, rel_tol=1e-10, abs_tol=1e-10), (a, b)


def main():
    for line in (ROOT / "SHA256SUMS").read_text().splitlines():
        want, name = line.split(maxsplit=1)
        assert digest(ROOT / name) == want, name
    proof = json.loads((ROOT / "comparison.json").read_text())
    assert proof["passed"] and proof["nets"] == 2491
    assert digest(ROOT / "net-comparison.tsv") == proof["net_comparison_sha256"]
    run = json.loads((ROOT / "run.json").read_text())
    params_name = "project/experiments/m11_m12_rcx/copper/parameters.json"
    assert run["archived_source_sha256"][params_name] == proof["inputs"]["parameters_sha256"]
    base = rows(REPO / "work/huangpingyang04-lgtm/215/net-rc.tsv")
    table = rows(ROOT / "net-comparison.tsv", header=True)
    assert len(base) == len(table) == 2491 and set(base) == set(table)
    for name in base:
        for a, b in zip(table[name][:3], base[name][:3]):
            close(a, b)
    signatures = set()
    for i, (case, info) in enumerate(proof["cases"].items()):
        path = ROOT / case
        observed = rows(path / "readback/totals.tsv")
        rb = json.loads((path / "readback/readback.json").read_text())
        assert rb == info["readback"] and rb["passed"]
        assert (rb["net_count"], rb["terminals"], rb["resistor_edges"], rb["mutual_net_pairs"],
                rb["mutual_node_pairs"], rb["projected_crossing_pairs_verified"]) == (
                    2491, 4982, 16414, 586172, 8234564, 18329)
        assert info["maximum_capacitance_change_ff"] == 0
        assert info["maximum_analytic_edge_error"] <= 6e-6
        assert digest(path / "controls/summary.json") == info["controls_sha256"]
        assert all(v["passed"] for v in json.loads((path / "controls/summary.json").read_text())["nets"].values())
        assert set(observed) == set(base)
        for net, values in observed.items():
            close(table[net][3 + i], values[0])
            assert 0 < values[0] < base[net][0]
            assert values[1:] == base[net][1:]
        signatures.add(info["non_res_sections_sha256"])
    assert len(signatures) == 1
    # Independently check that the delivered rule changes only top-layer R columns.
    old = (REPO / "project/experiments/m11_m12_rcx/candidate/research12.rules").read_text().splitlines()
    new = (ROOT / "cu-main/copper.rules").read_text().splitlines()
    assert len(old) == len(new)
    layer, changed = "", 0
    for a, b in zip(old, new):
        if a.startswith("Metal "):
            layer = a.split()[1]
        if layer in ("11", "12") and re.match(r"^[0-9.+-]", a):
            x, y = a.split(), b.split()
            assert x[:3] == y[:3]
            close(float(y[3]), float(x[3]) * .34)
            changed += 1
        else:
            assert a == b
    assert changed == 1046
    print("PASS: hashes, 2491 per-net comparisons, 4 full readbacks, 16 controls, fixed C, and Cu R-only rule delta")


if __name__ == "__main__":
    main()
