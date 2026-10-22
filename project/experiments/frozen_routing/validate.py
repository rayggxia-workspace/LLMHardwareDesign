"""Independent global electrical validation. Does not trust router paths/owners."""
from collections import Counter, defaultdict
from model import digest


def validate_mapping(base, workload, mapping):
    """Check declared functional inventory independently of mapping generation."""
    errors = []
    if set(mapping) != {"x", "y", *workload["ops"]}:
        errors.append("mapping_coverage")
    if mapping.get("x") != "S0" or mapping.get("y") != "S1":
        errors.append("io_mapping")
    if len(set(mapping.values())) != len(mapping):
        errors.append("mapping_not_injective")
    for node, op in workload["ops"].items():
        block = base.get("blocks", {}).get(mapping.get(node))
        if block is None:
            errors.append("unknown_block")
        elif op not in block["operations"]:
            errors.append("unsupported_operation")
    return {"valid": not errors, "errors": sorted(set(errors))}


def validate(base, nets, solution, expected_hash=None):
    errors = []
    if not isinstance(solution, dict) or not isinstance(solution.get("connectors"), list) or any(
            not isinstance(k, str) for k in solution.get("connectors", [])):
        return {"valid": False, "errors": ["invalid_configuration_type"]}
    if not isinstance(nets, list) or any(
            not isinstance(n, dict) or type(n.get("width")) is not int or n["width"] <= 0
            or not isinstance(n.get("driver"), str) or not isinstance(n.get("sinks"), list)
            or any(not isinstance(s, str) for s in n.get("sinks", [])) for n in nets):
        return {"valid": False, "errors": ["invalid_demand_type_or_width"]}
    actual_hash = digest(base)
    if expected_hash is not None and actual_hash != expected_hash:
        errors.append("fixed_inventory_changed")
    if set(solution) != {"base_sha256", "connectors"}:
        errors.append("undeclared_configuration_field")
    if solution.get("base_sha256") != actual_hash:
        errors.append("base_hash_mismatch")
    selected = solution.get("connectors", [])
    if len(selected) != len(set(selected)):
        errors.append("duplicate_connector")
    if len(selected) > base["limits"]["custom_connector_budget"]:
        errors.append("connector_budget")
    parent = {c: c for c in base["components"]}

    def find(c):
        while parent[c] != c:
            parent[c] = parent[parent[c]]
            c = parent[c]
        return c

    counts = Counter()
    for key in selected:
        con = base["connectors"].get(key)
        if con is None:
            errors.append("illegal_connector")
            continue
        for tap in (con["a"], con["b"]):
            if tap not in base["taps"]:
                errors.append("illegal_tap")
        if con["a"] not in base["taps"] or con["b"] not in base["taps"]:
            continue
        counts.update([con["a"], con["b"]])
        a, b = (find(base["taps"][con[x]]["component"]) for x in ("a", "b"))
        parent[a] = b
    for tap, count in counts.items():
        if count > base["taps"][tap]["capacity"]:
            errors.append("endpoint_capacity")
    drivers = defaultdict(set)
    for c, info in base["components"].items():
        if info["driver"]:
            drivers[find(c)].add(info["driver"])
    if any(len(ds) > 1 for ds in drivers.values()):
        errors.append("multiple_drivers")
    sink_owner = {}
    for net in nets:
        d = net["driver"]
        if d not in parent or base["components"][d]["driver"] != d:
            errors.append("invalid_driver")
            continue
        for sink in net["sinks"]:
            if sink not in parent or base["components"][sink]["kind"] != "input":
                errors.append("invalid_sink")
                continue
            if sink in sink_owner and sink_owner[sink] != d:
                errors.append("different_nets_same_sink")
            sink_owner[sink] = d
            if find(sink) != find(d):
                errors.append("disconnected_sink")
            if drivers[find(sink)] != {d}:
                errors.append("wrong_driver")
        for c, info in base["components"].items():
            if find(c) == find(d) and info["width"] < net["width"]:
                errors.append("width_mismatch")
    used = {base["taps"][base["connectors"][key][ab]]["component"]
            for key in selected if key in base["connectors"] for ab in ("a", "b")}
    return {"valid": not errors, "errors": sorted(set(errors)),
            "custom_connections": len(selected),
            "custom_cost_units": sum(base["connectors"][k]["cost_units"]
                                     for k in set(selected) if k in base["connectors"]),
            "occupied_prefab_length_units": sum(base["components"][c]["length_units"] for c in used)}
