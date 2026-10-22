"""Functional float64 dataflow check; NOT bit-/cycle-accurate hardware simulation."""
import math
import random
import numpy as np
from validate import validate_mapping


def check(workload_name, workload, mapping, base, solution, seed):
    mapping_result = validate_mapping(base, workload, mapping)
    if not mapping_result["valid"]:
        raise ValueError("invalid frozen capability mapping: " + str(mapping_result["errors"]))
    rng = random.Random(seed)
    x = [[rng.uniform(-0.5, 0.5) for _ in range(4)] for _ in range(2)]
    ws = {n: [[rng.uniform(-0.5, 0.5) for _ in range(4)] for _ in range(4)]
          for n, op in workload["ops"].items() if op == "matmul"}
    # Array expressions are intentionally independent of the graph interpreter.
    xx = np.array(x)
    ww = {k: np.array(v) for k, v in ws.items()}
    silu = lambda a: a / (1 + np.exp(-a))
    if workload_name == "ffn":
        reference = silu(xx @ ww["m0"]) @ ww["m1"]
    elif workload_name == "gated_ffn":
        reference = (silu(xx @ ww["m0"]) * (xx @ ww["m1"])) @ ww["m2"]
    elif workload_name == "residual_ffn":
        reference = silu(xx @ ww["m0"]) @ ww["m1"] + xx
    elif workload_name == "fork_add":
        reference = ((xx @ ww["m0"]) + (xx @ ww["m1"])) @ ww["m2"]
    else:
        raise ValueError(workload_name)
    graph = {c: set() for c in base["components"]}
    for key in solution["connectors"]:
        con = base["connectors"][key]
        a, b = [base["taps"][con[k]]["component"] for k in ("a", "b")]
        graph[a].add(b)
        graph[b].add(a)

    def source(pin):
        seen, stack, drivers = set(), [pin], []
        while stack:
            c = stack.pop()
            if c in seen:
                continue
            seen.add(c)
            if base["components"][c]["driver"]:
                drivers.append(base["components"][c]["driver"])
            stack.extend(graph[c] - seen)
        if len(drivers) != 1:
            raise ValueError("dataflow must have exactly one driver")
        return drivers[0]

    values = {"S0.o": x}
    pending = dict(workload["ops"])
    while pending:
        progress = False
        for node, op in list(pending.items()):
            block = mapping[node]
            sources = [source(block+".a")]
            if op in ("mul", "add"):
                sources.append(source(block+".b"))
            if any(s not in values for s in sources):
                continue
            a = values[sources[0]]
            if op == "matmul":
                w = ws[node]
                out = [[sum(a[i][k]*w[k][j] for k in range(4))
                        for j in range(4)] for i in range(2)]
            elif op == "silu":
                out = [[v/(1+math.exp(-v)) for v in row] for row in a]
            else:
                b = values[sources[1]]
                out = [[u*v if op == "mul" else u+v for u, v in zip(ar, br)]
                       for ar, br in zip(a, b)]
            values[block+".o"] = out
            del pending[node]
            progress = True
        if not progress:
            raise ValueError("unresolved/cyclic functional dataflow")
    result = np.array(values[source("S1.a")])
    error = float(np.max(np.abs(result-reference)))
    if not np.isfinite(error) or error > 1e-12:
        raise AssertionError(f"numeric mismatch {error}")
    return {"passed": True, "max_abs_error": error, "shape": [2, 4],
            "semantics": "software_float64_no_quantization", "seed": seed}
