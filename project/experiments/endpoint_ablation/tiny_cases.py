"""Hand-constructed, exhaustively enumerable endpoint-ablation controls.

The master owns the maximum connector inventory and tap capacities. An overlay
only restricts these; it never splits a conductor, moves a tap, changes a driver,
or adds an active device. Sites are abstract labels, not manufacturing geometry.
All inputs/outputs have capacity one. A wire's two taps are permanently joined.
"""
from __future__ import annotations

import copy


ARMS = ("restricted", "access", "capacity", "joint")


def _master(name):
    return {
        "schema": 1,
        "model": "abstract-passive-bundles-v1",
        "parameters": {"fixture": name},
        "blocks": {},
        "components": {},
        "taps": {},
        "connectors": {},
        "limits": {"custom_connector_budget": 16},
        "assumptions": [
            "16-bit bundles have identical per-bit connectivity",
            "wire taps on one component are permanently connected",
            "all output stubs remain potential active drivers",
            "tap sites are abstract, not PDK-verified interfaces",
        ],
    }


def _component(master, name, kind):
    master["components"][name] = {
        "kind": kind,
        "width": 16,
        "length_units": 3 if kind == "wire" else 0,
        "driver": name if kind == "output" else None,
    }
    for i in range(2 if kind == "wire" else 1):
        master["taps"][f"{name}:{i}"] = {
            "component": name,
            "site": [i, 0],
            "capacity": 4 if kind == "wire" else 1,
        }


def _connector(master, key, a, b):
    master["connectors"][key] = {
        "a": a,
        "b": b,
        "kind": "exposed_join",
        "cost_units": 1,
    }


def _case(name, master, restricted, nets, expected):
    master["limits"]["custom_connector_budget"] = min(
        master["limits"]["custom_connector_budget"], len(master["connectors"])
    )
    expanded = sorted(master["connectors"])
    overlays = {}
    for arm in ARMS:
        relaxed = arm in ("capacity", "joint")
        capacities = {
            tap: (4 if relaxed else 3)
            if master["components"][info["component"]]["kind"] == "wire"
            else 1
            for tap, info in master["taps"].items()
        }
        overlays[arm] = {
            "allowed_connectors": expanded.copy()
            if arm in ("access", "joint") else sorted(restricted),
            "tap_capacities": capacities,
        }
    return {
        "name": name,
        "master": master,
        "overlays": overlays,
        "nets": nets,
        "expected_feasible": dict(zip(ARMS, expected)),
    }


def _star(name, sink_count, remove_last=False, spare_access=False):
    """One driver and all sinks need distinct contacts on the SAME wire tap.

    With three sinks the four required contacts exceed restricted capacity 3.
    The optional spare contact is at the other end of that same conductor and
    reaches an unused input; it cannot bypass a required contact at wire:0.
    """
    master = _master(name)
    _component(master, "d0", "output")
    _component(master, "wire", "wire")
    _connector(master, "drive", "d0:0", "wire:0")
    required = ["drive"]
    sinks = []
    for i in range(sink_count):
        sink = f"t{i}"
        _component(master, sink, "input")
        _connector(master, f"sink{i}", "wire:0", f"{sink}:0")
        required.append(f"sink{i}")
        sinks.append(sink)
    restricted = required.copy()
    if remove_last:
        restricted.remove(f"sink{sink_count-1}")
    if spare_access:
        _component(master, "unused", "input")
        _connector(master, "spare", "wire:1", "unused:0")
    return master, restricted, [{"driver": "d0", "sinks": sinks, "width": 16}]


def cases():
    """Return six independent controls; each master has at most five connectors.

    Exact optimum costs of feasible arms are 3 (access-only), 4
    (capacity-only/joint-required), and 2 (positive). The other controls have
    no feasible subset under their fixed demands and global budget.
    """
    result = []

    # Access is necessary and sufficient; capacity 3 already accommodates all
    # three required contacts. More capacity cannot invent the missing pin.
    master, restricted, nets = _star("access-only", 2, remove_last=True)
    result.append(_case("access-only", master, restricted, nets,
                        (False, True, False, True)))

    # Access relaxation adds a real but irrelevant connector. It cannot remove
    # the need for all four contacts at wire:0; only the capacity relaxation can.
    master, restricted, nets = _star("capacity-only", 3, spare_access=True)
    result.append(_case("capacity-only", master, restricted, nets,
                        (False, False, True, True)))

    # Capacity alone cannot supply sink2's absent contact; access alone leaves
    # four mandatory contacts competing for a capacity-three tap.
    master, restricted, nets = _star("joint-required", 3, remove_last=True)
    result.append(_case("joint-required", master, restricted, nets,
                        (False, False, False, True)))

    # Both nets must use the same permanently connected wire. Even when their
    # selected contacts are distinct, that would connect two physical drivers.
    master = _master("driver-short")
    for name, kind in (("d0", "output"), ("d1", "output"),
                       ("t0", "input"), ("t1", "input"),
                       ("unused", "input"), ("wire", "wire")):
        _component(master, name, kind)
    for key, a, b in (("drive0", "d0:0", "wire:0"),
                      ("drive1", "d1:0", "wire:1"),
                      ("sink0", "wire:0", "t0:0"),
                      ("sink1", "wire:1", "t1:0"),
                      ("spare", "wire:1", "unused:0")):
        _connector(master, key, a, b)
    nets = [{"driver": f"d{i}", "sinks": [f"t{i}"], "width": 16}
            for i in range(2)]
    result.append(_case("driver-short", master,
                        ["drive0", "drive1", "sink0", "sink1"], nets,
                        (False, False, False, False)))

    # Baseline already has a complete two-contact route. Access adds an equally
    # priced second route; it should not turn a feasible control into a failure.
    master = _master("positive")
    for name, kind in (("d0", "output"), ("t0", "input"),
                       ("A", "wire"), ("B", "wire")):
        _component(master, name, kind)
    for key, a, b in (("a_in", "d0:0", "A:0"),
                      ("a_out", "A:1", "t0:0"),
                      ("b_in", "d0:0", "B:0"),
                      ("b_out", "B:1", "t0:0")):
        _connector(master, key, a, b)
    nets = [{"driver": "d0", "sinks": ["t0"], "width": 16}]
    result.append(_case("positive", master, ["a_in", "a_out"], nets,
                        (True, True, True, True)))

    # A chain needs four connectors. Capacity is never binding and every arm
    # has the full path; the fixed global budget of three alone forbids it.
    master = _master("budget-fail")
    for name, kind in (("d0", "output"), ("t0", "input"),
                       ("A", "wire"), ("B", "wire"), ("C", "wire")):
        _component(master, name, kind)
    for key, a, b in (("j0", "d0:0", "A:0"),
                      ("j1", "A:1", "B:0"),
                      ("j2", "B:1", "C:0"),
                      ("j3", "C:1", "t0:0")):
        _connector(master, key, a, b)
    master["limits"]["custom_connector_budget"] = 3
    result.append(_case("budget-fail", master, list(master["connectors"]), nets,
                        (False, False, False, False)))

    # Callers may materialize or mutate their local copy without influencing a
    # later test invocation or another case.
    return copy.deepcopy(result)
