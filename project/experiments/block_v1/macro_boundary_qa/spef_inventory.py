"""Strict source RC inventory for the explicit distributed SPEF subset.

This reads actual resistor/capacitor records, not a caller-written ownership
ledger. Unsupported reduced/complex SPEF constructs fail closed. No equivalent
resistance, Elmore timing or coupling reduction is inferred from sums.
"""
from collections import defaultdict
import math
from pathlib import Path
import re

from audit import Invalid, file_sha, require


def positive_value(text):
    value = float(text)
    require(math.isfinite(value) and value >= 0, "nonfinite/negative SPEF quantity")
    return value


def scaled_value(text, multiplier):
    value = positive_value(text)*multiplier
    require(math.isfinite(value), "SPEF scaled quantity overflows")
    return value


def inventory(path, retain_all=True):
    path = Path(path)
    digest = file_sha(path)
    names, units, nets, ports = {}, {}, {}, {}
    mapped_values, net_names = set(), set()
    net_count = resistor_count = capacitor_count = 0
    section, current = "header", None
    design = None
    delimiter = None
    seen_sections = set()
    allowed_headers = {"*SPEF", "*DATE", "*VENDOR", "*PROGRAM", "*VERSION",
                       "*DESIGN_FLOW", "*DIVIDER", "*BUS_DELIMITER"}

    def resolve(name):
        # A mapped net/instance prefix can be followed by a pin/node suffix.
        match = re.fullmatch(r"\*(\d+)(.*)", name)
        if match:
            require(match[1] in names, f"unresolved SPEF name map: {name}")
            suffix = match[2]
            require(not suffix or (delimiter is not None and suffix.startswith(delimiter)), "name-map suffix")
            return names[match[1]] + suffix
        require(not name.startswith("*"), f"invalid SPEF node: {name}")
        return name

    with path.open(encoding="utf-8") as stream:
        for line_no, line in enumerate(stream, 1):
            line = line.strip()
            if not line or line.startswith("//"):
                continue
            fields = line.split()
            head = fields[0]
            try:
                if head == "*D_NET":
                    require(current is None and len(fields) == 3, "nested/malformed D_NET")
                    require(set(units) == {"time_s", "cap_pf", "res_ohm", "ind_h"}, "missing SPEF units")
                    name = resolve(fields[1])
                    require(name not in net_names, "duplicate D_NET")
                    net_names.add(name)
                    current = {"name": name, "reported_cap_pf": scaled_value(fields[2], units["cap_pf"]),
                               "connections": {}, "resistors": {}, "capacitors": {}}
                    section, seen_sections = "net", set()
                elif head == "*END":
                    require(current is not None and len(fields) == 1, "unmatched END")
                    require(seen_sections == {"*CONN", "*CAP", "*RES"}, "missing net sections")
                    net_count += 1
                    resistor_count += len(current["resistors"])
                    capacitor_count += len(current["capacitors"])
                    if retain_all or any(c["kind"] == "P" and c["direction"] == "I" for c in current["connections"].values()):
                        nets[current["name"]] = current
                    current, section = None, "between"
                elif current is not None:
                    if head in ("*CONN", "*CAP", "*RES"):
                        require(len(fields) == 1 and head not in seen_sections, "duplicate net section")
                        seen_sections.add(head)
                        section = head
                    elif section == "*CONN":
                        require(head in ("*P", "*I") and len(fields) >= 3, "unsupported CONN record")
                        name = resolve(fields[1])
                        require(name not in current["connections"] and fields[2] in ("I", "O", "B"), "duplicate/direction CONN")
                        # Preserve attributes (coordinates/load/driving cell) as evidence.
                        current["connections"][name] = {"kind": head[1:], "direction": fields[2], "attributes": fields[3:]}
                    elif section in ("*CAP", "*RES"):
                        require(head.isdigit(), "noninteger RC identifier")
                        kind = "resistors" if section == "*RES" else "capacitors"
                        require(head not in current[kind], "duplicate RC identifier")
                        require(len(fields) in ((4,) if kind == "resistors" else (3, 4)), "RC record arity")
                        nodes = [resolve(node) for node in fields[1:-1]]
                        require(len(set(nodes)) == len(nodes), "self-loop RC record")
                        multiplier = units["res_ohm"] if kind == "resistors" else units["cap_pf"]
                        current[kind][head] = {"nodes": nodes, "value": scaled_value(fields[-1], multiplier),
                                               "source_line": line_no}
                    else:
                        raise Invalid("unsupported net record")
                elif head == "*NAME_MAP":
                    require(section == "header" and not names, "duplicate/unordered NAME_MAP")
                    section = "names"
                elif section == "names" and re.fullmatch(r"\*\d+", head):
                    require(len(fields) == 2 and head[1:] not in names, "duplicate/malformed mapped name")
                    require(fields[1] not in mapped_values, "aliased mapped name")
                    names[head[1:]] = fields[1]
                    mapped_values.add(fields[1])
                elif head == "*PORTS":
                    require(section in ("header", "names") and len(fields) == 1, "duplicate/unordered PORTS")
                    section = "ports"
                elif section == "ports" and (not head.startswith("*") or re.fullmatch(r"\*\d+", head)):
                    require(len(fields) >= 2 and fields[1] in ("I", "O", "B"), "PORTS direction")
                    name = resolve(head)
                    require(name not in ports, "duplicate PORTS entry")
                    ports[name] = fields[1]
                elif head in ("*T_UNIT", "*C_UNIT", "*R_UNIT", "*L_UNIT"):
                    require(section == "header" and len(fields) == 3, "unit header order/arity")
                    dimension, factors = {
                        "*T_UNIT": ("time_s", {"NS": 1e-9, "PS": 1e-12}),
                        "*C_UNIT": ("cap_pf", {"PF": 1.0, "FF": .001}),
                        "*R_UNIT": ("res_ohm", {"OHM": 1.0, "KOHM": 1000.0}),
                        "*L_UNIT": ("ind_h", {"HENRY": 1.0, "MH": 1e-3, "UH": 1e-6}),
                    }[head]
                    require(dimension not in units and fields[2].upper() in factors, "duplicate/unsupported unit")
                    scale = positive_value(fields[1])
                    require(scale > 0, "zero unit scale")
                    units[dimension] = scale*factors[fields[2].upper()]
                elif head == "*DESIGN":
                    require(section == "header" and design is None and len(fields) == 2, "DESIGN header")
                    design = fields[1].strip('"')
                elif head == "*DELIMITER":
                    require(section == "header" and delimiter is None and len(fields) == 2, "DELIMITER header")
                    delimiter = fields[1]
                elif head in allowed_headers:
                    require(section == "header", "header after data")
                else:
                    raise Invalid(f"unsupported SPEF construct: {head}")
            except (Invalid, ValueError) as error:
                raise Invalid(f"SPEF line {line_no}: {error}") from error
    require(current is None and design and delimiter and nets, "incomplete SPEF")
    require(file_sha(path) == digest, "SPEF changed during inventory")
    input_nets = {}
    for net_name, net in nets.items():
        connections = net["connections"]
        for name, conn in connections.items():
            if conn["kind"] == "P":
                require(ports.get(name) == conn["direction"], "CONN/PORTS mismatch")
        drivers = [name for name, conn in connections.items() if conn["kind"] == "P" and conn["direction"] == "I"]
        if not drivers:
            continue
        require(len(drivers) == 1, "multiple input ports on one net unsupported")
        root = drivers[0]
        require(root not in input_nets, "input port occurs in multiple D_NETs")
        adjacency = defaultdict(set)
        for item in net["resistors"].values():
            a, b = item["nodes"]
            adjacency[a].add(b)
            adjacency[b].add(a)
        reached, frontier = set(), [root]
        while frontier:
            node = frontier.pop()
            if node in reached:
                continue
            reached.add(node)
            frontier.extend(adjacency[node] - reached)
        sinks = {name for name, conn in connections.items() if conn["kind"] == "I" and conn["direction"] == "I"}
        require(sinks <= reached, f"input resistor graph disconnects sinks: {root}")
        require(set(adjacency) <= reached, f"floating input resistor component: {root}")
        ground_nodes = {item["nodes"][0] for item in net["capacitors"].values() if len(item["nodes"]) == 1}
        require(ground_nodes <= reached, f"floating input ground capacitance: {root}")
        input_nets[root] = {
            "net": net_name, "driver": root, "sinks": sorted(sinks),
            "resistor_count": len(net["resistors"]),
            "resistance_sum_ohm": math.fsum(x["value"] for x in net["resistors"].values()),
            "ground_cap_pf": math.fsum(x["value"] for x in net["capacitors"].values() if len(x["nodes"]) == 1),
            "coupling_cap_pf_per_net_record": math.fsum(x["value"] for x in net["capacitors"].values() if len(x["nodes"]) == 2),
            "resistor_ids": sorted(net["resistors"]),
        }
    require(input_nets and set(input_nets) == {n for n, d in ports.items() if d == "I"},
            "missing input-port D_NET coverage")
    return {"schema": "block-v1-source-spef-inventory/1", "passed": True,
            "source_spef_sha256": digest, "design": design, "units": units,
            "ports": ports, "nets": nets, "input_nets": input_nets,
            "retained_nets": "all" if retain_all else "input-boundary-only",
            "total_counts": {"nets": net_count, "resistors": resistor_count, "capacitors": capacitor_count},
            "boundary_qualified": False,
            "scope": "Explicit SPEF record/graph inventory only; sums are not equivalent R or timing, coupling records are not globally deduplicated"}
