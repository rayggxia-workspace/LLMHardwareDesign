"""Abstract, passive, indivisible-conductor fabric. No physical PPA model."""
from __future__ import annotations

import hashlib
import itertools
import json
import random
from collections import defaultdict


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False).encode()).hexdigest()


def make_fabric(tracks=2, span=1, access=4, endpoint_capacity=3):
    """Coordinates are abstract sites, NOT DRC/legal manufacturing geometry.

    A component is one permanently connected bundle. Each bit has identical
    connectivity; all bundles are 16 bits. A tap is explicitly exposed. There
    is no implicit connection at geometric crossings or component interiors.
    """
    if any(type(v) is not int or v <= 0 for v in (tracks, span, access, endpoint_capacity)):
        raise ValueError("fabric parameters must be positive integers")
    components, taps, connectors, blocks = {}, {}, {}, {}

    def component(name, points, length, kind="wire", driver=None):
        components[name] = {"kind": kind, "width": 16, "length_units": length,
                            "driver": driver}
        names = []
        for i, point in enumerate(points):
            tap = f"{name}:{i}"
            taps[tap] = {"component": name, "site": list(point),
                         "capacity": endpoint_capacity if kind == "wire" else 1}
            names.append(tap)
        return names

    sites = defaultdict(list)
    for lane in range(tracks):
        for y in range(4):
            for x in range(0, 4, span):
                end = min(4, x + span)
                ts = component(f"H{lane}.{x}.{y}", [(x, y), (end, y)], end-x)
                for t in ts:
                    sites[tuple(taps[t]["site"])].append(t)
        for x in range(5):
            for y in range(0, 3, span):
                end = min(3, y + span)
                ts = component(f"V{lane}.{x}.{y}", [(x, y), (x, end)], end-y)
                for t in ts:
                    sites[tuple(taps[t]["site"])].append(t)

    def connect(a, b, kind, cost=1):
        a, b = sorted((a, b))
        name = a + "~" + b
        connectors[name] = {"a": a, "b": b, "kind": kind, "cost_units": cost}

    for ts in sites.values():
        for a, b in itertools.combinations(sorted(ts), 2):
            if taps[a]["component"] != taps[b]["component"]:
                connect(a, b, "exposed_join")
    positions = {"S0": (0, 0), "S1": (4, 3), "C0": (1, 0),
                 "C1": (3, 0), "C2": (1, 3), "C3": (3, 3),
                 "V0": (2, 1), "V1": (2, 2)}
    wire_taps = sorted(taps)
    for block, pos in positions.items():
        blocks[block] = {"type": block[0], "site": list(pos),
                         "operations": ["matmul"] if block[0] == "C" else
                         ["silu", "mul", "add"] if block[0] == "V" else ["io"]}
        for port in ("o", "a", "b"):
            pin = block + "." + port
            t = component(pin, [pos], 0, "output" if port == "o" else "input",
                          pin if port == "o" else None)[0]
            # Inputs need different access preferences, but have identical
            # declared budgets. The port access inventory is frozen, not chosen
            # in response to a task or a test-set result.
            ranked = sorted(wire_taps, key=lambda w: (
                abs(taps[w]["site"][0]-pos[0])+abs(taps[w]["site"][1]-pos[1]),
                (0 if (w.startswith("H") == (port != "b")) else 1), w))
            for w in ranked[:access]:
                distance = sum(abs(a-b) for a, b in zip(taps[w]["site"], pos))
                connect(t, w, "pin_access", 1+distance)
    return {"schema": 1, "model": "abstract-passive-bundles-v1",
            "parameters": {"tracks": tracks, "span": span, "access": access,
                           "endpoint_capacity": endpoint_capacity},
            "blocks": blocks, "components": components, "taps": taps,
            "connectors": connectors,
            "limits": {"custom_connector_budget": 160},
            "assumptions": ["16-bit bundles have identical per-bit connectivity",
                            "all non-port wire components are passive",
                            "all output stubs remain potential active drivers",
                            "tap sites are abstract, not PDK-verified interfaces",
                            "weights and control/clock/PG distribution unmodeled"]}


WORKLOADS = {
    "ffn": {"split": "design", "ops": {"m0": "matmul", "v0": "silu", "m1": "matmul"},
            "edges": [("x", "m0", "a"), ("m0", "v0", "a"),
                      ("v0", "m1", "a"), ("m1", "y", "a")]},
    "gated_ffn": {"split": "design", "ops": {"m0": "matmul", "m1": "matmul",
                    "v0": "silu", "v1": "mul", "m2": "matmul"},
                  "edges": [("x", "m0", "a"), ("x", "m1", "a"),
                            ("m0", "v0", "a"), ("v0", "v1", "a"),
                            ("m1", "v1", "b"), ("v1", "m2", "a"), ("m2", "y", "a")]},
    "residual_ffn": {"split": "held_out", "ops": {"m0": "matmul", "v0": "silu",
                       "m1": "matmul", "v1": "add"},
                     "edges": [("x", "m0", "a"), ("m0", "v0", "a"),
                               ("v0", "m1", "a"), ("m1", "v1", "a"),
                               ("x", "v1", "b"), ("v1", "y", "a")]},
    "fork_add": {"split": "held_out", "ops": {"m0": "matmul", "m1": "matmul",
                  "v0": "add", "m2": "matmul"},
                 "edges": [("x", "m0", "a"), ("x", "m1", "a"),
                           ("m0", "v0", "a"), ("m1", "v0", "b"),
                           ("v0", "m2", "a"), ("m2", "y", "a")]}}


def mappings(workload):
    ms = [n for n, op in workload["ops"].items() if op == "matmul"]
    vs = [n for n, op in workload["ops"].items() if op != "matmul"]
    for cs in itertools.permutations(["C0", "C1", "C2", "C3"], len(ms)):
        for vv in itertools.permutations(["V0", "V1"], len(vs)):
            yield {"x": "S0", "y": "S1", **dict(zip(ms, cs)), **dict(zip(vs, vv))}


def seeded_mapping(workload, seed):
    options = list(mappings(workload))
    return options[random.Random(seed).randrange(len(options))]


def demands(workload, mapping):
    nets = {}
    for src, dst, port in workload["edges"]:
        driver = mapping[src] + ".o"
        nets.setdefault(driver, {"driver": driver, "sinks": [], "width": 16})
        nets[driver]["sinks"].append(mapping[dst] + "." + port)
    return list(nets.values())
