"""Small explicitly enumerable electrical networks; not training workloads."""
import random
from model import digest


def tiny(seed=0):
    components, taps = {}, {}
    for c in ["d0", "d1", "t0", "t1", "A", "B", "C", "D"]:
        kind = "output" if c.startswith("d") else "input" if c.startswith("t") else "wire"
        components[c] = {"kind": kind, "width": 16,
                         "driver": c if kind == "output" else None,
                         "length_units": 3 if kind == "wire" else 0}
        for k in range(2 if kind == "wire" else 1):
            taps[f"{c}:{k}"] = {"component": c, "site": [k, 0],
                                  "capacity": 3 if kind == "wire" else 1}
    pairs = [("d0:0", "A:0"), ("d1:0", "B:0"), ("A:1", "t0:0"),
             ("B:1", "t1:0"), ("A:1", "C:0"), ("C:1", "t0:0"),
             ("B:1", "D:0"), ("D:1", "t1:0"), ("A:0", "D:0"),
             ("B:0", "C:0"), ("C:1", "D:1")]
    rng = random.Random(seed)
    cons = {f"j{i}": {"a": a, "b": b, "kind": "exposed_join", "cost_units": 1}
            for i, (a, b) in enumerate(pairs) if seed == 0 or rng.random() > 0.17}
    base = {"components": components, "taps": taps, "connectors": cons,
            "limits": {"custom_connector_budget": 11}}
    nets = [{"driver": "d0", "sinks": ["t0"], "width": 16},
            {"driver": "d1", "sinks": ["t1"], "width": 16}]
    return base, nets


def solution(base, keys):
    return {"base_sha256": digest(base), "connectors": keys}
