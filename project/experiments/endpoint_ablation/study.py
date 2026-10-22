"""Fixed maximum inventory and explicit counterfactual constraint overlays."""
from __future__ import annotations
from collections import Counter, defaultdict
from copy import deepcopy
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
FROZEN = HERE.parent / "frozen_routing"
sys.path.insert(0, str(FROZEN))
from model import WORKLOADS, demands, digest, make_fabric, seeded_mapping
from numeric import check
from router import route
from validate import validate, validate_mapping

ARMS = ("restricted", "access", "capacity", "joint")
INCLUSIONS = (("restricted", "access"), ("restricted", "capacity"),
              ("access", "joint"), ("capacity", "joint"))


def materialize(master, overlay):
    """No new conductor, driver, tap, cost, or pin capacity can be introduced."""
    if set(overlay) != {"allowed_connectors", "tap_capacities"}:
        raise ValueError("unknown overlay field")
    keys, caps = overlay["allowed_connectors"], overlay["tap_capacities"]
    if (not isinstance(keys, list) or any(not isinstance(k, str) for k in keys)
            or len(keys) != len(set(keys)) or not set(keys) <= set(master["connectors"])):
        raise ValueError("illegal allowed-connector set")
    if not isinstance(caps, dict) or set(caps) != set(master["taps"]):
        raise ValueError("capacity keys must exactly cover existing taps")
    for tap, value in caps.items():
        if type(value) is not int or not 0 < value <= master["taps"][tap]["capacity"]:
            raise ValueError("capacity must be positive and no larger than master")
        kind = master["components"][master["taps"][tap]["component"]]["kind"]
        if kind != "wire" and (value != 1 or master["taps"][tap]["capacity"] != 1):
            raise ValueError("pin capacity must remain one")
    base = deepcopy(master)
    base["connectors"] = {k: deepcopy(master["connectors"][k]) for k in sorted(keys)}
    for tap, value in caps.items():
        base["taps"][tap]["capacity"] = value
    return base


def make_inventory(tracks, span, access, wire_capacity=3, multiplier=2):
    original = make_fabric(tracks, span, access, wire_capacity)
    master = make_fabric(tracks, span, access * multiplier, wire_capacity)
    degree = Counter(t for con in master["connectors"].values() for t in (con["a"], con["b"]))
    for tap, info in master["taps"].items():
        if master["components"][info["component"]]["kind"] == "wire":
            info["capacity"] = max(wire_capacity, degree[tap])
    restricted_caps = {t: info["capacity"] for t, info in original["taps"].items()}
    maximum_caps = {t: info["capacity"] for t, info in master["taps"].items()}
    overlays = {arm: {
        "allowed_connectors": sorted(master["connectors"] if arm in ("access", "joint")
                                     else original["connectors"]),
        "tap_capacities": deepcopy(maximum_caps if arm in ("capacity", "joint") else restricted_caps)
    } for arm in ARMS}
    assert_contract(master, overlays, original)
    return master, overlays


def assert_contract(master, overlays, original=None):
    assert set(overlays) == set(ARMS)
    before = digest(master)
    effective = {arm: materialize(master, overlays[arm]) for arm in ARMS}
    assert digest(master) == before
    for a, b in INCLUSIONS:
        assert set(effective[a]["connectors"]) <= set(effective[b]["connectors"])
        for key, con in effective[a]["connectors"].items():
            assert effective[b]["connectors"][key] == con
        assert all(effective[a]["taps"][t]["capacity"] <= effective[b]["taps"][t]["capacity"]
                   for t in master["taps"])
    for a, b in (("restricted", "access"), ("capacity", "joint")):
        assert effective[a]["taps"] == effective[b]["taps"]
    for a, b in (("restricted", "capacity"), ("access", "joint")):
        assert effective[a]["connectors"] == effective[b]["connectors"]
    for base in effective.values():
        for field in ("components", "blocks", "limits", "parameters", "assumptions"):
            assert base[field] == master[field]
        assert set(base["taps"]) == set(master["taps"])
        for tap, info in base["taps"].items():
            assert {k: v for k, v in info.items() if k != "capacity"} == {
                k: v for k, v in master["taps"][tap].items() if k != "capacity"}
    if original is not None:
        for field in ("components", "blocks", "taps", "connectors", "limits"):
            assert effective["restricted"][field] == original[field], field
    return effective


def no_path_certificates(base, nets):
    """Overapproximation: ignore all capacities and competition from other nets.

    Absence of a path proves only fixed-mapping infeasibility in this model.
    Presence of a path proves nothing about simultaneous multi-net feasibility.
    """
    certificates = []
    for net in nets:
        driver, sinks = net["driver"], set(net["sinks"])
        blocked = {c for c, info in base["components"].items()
                   if (info["kind"] == "output" and c != driver)
                   or (info["kind"] == "input" and c not in sinks)}
        graph = defaultdict(set)
        for con in base["connectors"].values():
            a, b = [base["taps"][con[k]]["component"] for k in ("a", "b")]
            if a not in blocked and b not in blocked:
                graph[a].add(b)
                graph[b].add(a)
        seen, stack = set(), [driver]
        while stack:
            c = stack.pop()
            if c not in seen:
                seen.add(c)
                stack.extend(graph[c] - seen)
        missing = sorted(sinks - seen)
        if missing:
            certificates.append({"driver": driver, "unreachable_sinks": missing,
                                 "reachable_components": sorted(seen)})
    return certificates


def lifted_witness(base, nets, source_solution):
    if source_solution is None:
        return None
    result = {"base_sha256": digest(base), "connectors": list(source_solution["connectors"])}
    return result if validate(base, nets, result)["valid"] else None


def classify_group(rows, bases):
    """Keep raw searches intact; imported witnesses never count as router wins."""
    by_arm = {row["arm"]: row for row in rows}
    assert set(by_arm) == set(ARMS) and len(rows) == len(ARMS)
    first = rows[0]
    workload = WORKLOADS[first["workload"]]
    nets = demands(workload, first["mapping"])
    assert all(row["mapping"] == first["mapping"] for row in rows)
    for arm in ARMS:
        row, base = by_arm[arm], bases[arm]
        row["no_path_certificates"] = no_path_certificates(base, nets)
        row["imported_witness"] = None
        if row["raw_solution"] is not None:
            row["knowledge"] = "routed"
        else:
            for source in ARMS:
                witness = lifted_witness(base, nets, by_arm[source]["raw_solution"])
                if witness is not None:
                    row["imported_witness"] = {
                        "source_arm": source, "source_effective_sha256": digest(bases[source]),
                        "solution": witness, "validation": validate(base, nets, witness),
                        "numeric": check(row["workload"], workload, row["mapping"], base, witness, row["seed"])}
                    break
            row["knowledge"] = ("known_feasible_heuristic_miss" if row["imported_witness"] else
                                "proven_no_path_fixed_mapping" if row["no_path_certificates"] else "unknown")
        if row["raw_solution"] is not None or row["imported_witness"]:
            assert not row["no_path_certificates"], "legal witness contradicts cut certificate"
    return rows


def summarize(rows, oracle_rows):
    groups = defaultdict(dict)
    for row in rows:
        groups[(row["variant"], row["workload"], row["seed"])][row["arm"]] = row
    per_arm = {arm: dict(Counter(r["knowledge"] for r in rows if r["arm"] == arm)) for arm in ARMS}
    access_certified = {arm: sum(bool(g["restricted"]["no_path_certificates"]) and
                                g[arm]["knowledge"] in ("routed", "known_feasible_heuristic_miss")
                                for g in groups.values()) for arm in ("access", "joint")}
    return {"cases": len(rows), "paired_groups": len(groups), "by_arm": per_arm,
            "no_path_to_legal_witness_fixed_mappings": access_certified,
            "numeric_checks": sum(r["raw_solution"] is not None for r in rows) +
                              sum(r["imported_witness"] is not None for r in rows),
            "oracle_rows": len(oracle_rows),
            "scope": "Synthetic constraint-overlay ablation, not physical H2/PPA or new held-out evaluation."}
