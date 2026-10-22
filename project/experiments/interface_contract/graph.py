"""Build the fixed ACT/MXU *boundary port wiring* graph.

Only the eight recorded links and same-name parent connections are used. Bit
identity comes from explicit, zero-based LSB-first port names, never LEF row
order or Yosys internal signal IDs. Distinct physical boundary pins remain
distinct even when their internal RTL signal is an alias or a constant.

``build_graph`` raises ``GraphError`` on incomplete or ambiguous inputs. Its
single-driver check describes the declared boundary directions; it is not a
proof of independent RTL signals, internal logic, timing, or legal access.
"""
from collections import Counter
from collections.abc import Mapping
from copy import deepcopy


class GraphError(ValueError):
    """The fixed connection contract or its expanded views are inconsistent."""


# act port, mxu port, width, candidate driving the boundary connection.
_LINKS = (
    ("ren", "act_ren", 2, "MXU20"),
    ("r_use", "computing", 1, "MXU20"),
    ("r_blk", "act_blk", 16, "MXU20"),
    ("r_blk2", "act_blk2", 16, "MXU20"),
    ("r_hi", "act_hi", 2, "MXU20"),
    ("r_grp", "act_grp", 8, "MXU20"),
    ("r_data", "act_data", 512, "ACT20"),
    ("r_scale", "act_scale", 128, "ACT20"),
)
_CANDIDATES = ("ACT20", "MXU20")


def _require(condition, message):
    if not condition:
        raise GraphError(message)


def _expanded_names(port, width):
    return [port] if width == 1 else [f"{port}[{i}]" for i in range(width)]


def _port_shape(port, description):
    _require(isinstance(description, Mapping), f"Port {port!r} must be an object")
    direction = description.get("direction")
    width = description.get("width")
    _require(direction in ("input", "output"), f"Unsupported direction for {port!r}")
    _require(type(width) is int and width > 0, f"Invalid width for {port!r}")
    return direction, width


def _validated_views(views):
    _require(isinstance(views, Mapping) and set(views) == set(_CANDIDATES),
             "Views must contain exactly ACT20 and MXU20")
    expanded = {}
    for candidate in _CANDIDATES:
        view = views[candidate]
        _require(isinstance(view, Mapping), f"Invalid view {candidate}")
        ports, rows = view.get("ports"), view.get("bits")
        _require(isinstance(ports, Mapping) and isinstance(rows, Mapping),
                 f"{candidate} requires ports and bits objects")
        endpoints = {}
        for port, description in ports.items():
            _require(isinstance(port, str) and bool(port), f"Invalid port name in {candidate}")
            direction, width = _port_shape(port, description)
            names = _expanded_names(port, width)
            _require(description.get("bits") == names,
                     f"{candidate}.{port}: exact LSB-first bit names required")
            for offset, name in enumerate(names):
                _require(name not in endpoints, f"Duplicate boundary endpoint {candidate}.{name}")
                _require(name in rows and isinstance(rows[name], Mapping),
                         f"Missing bit row for {candidate}.{name}")
                row = rows[name]
                for key in ("name", "pin_raw_name"):
                    if key in row:
                        _require(row[key] == name, f"Bit row name mismatch for {candidate}.{name}")
                if "candidate" in row:
                    _require(row["candidate"] == candidate, f"Bit row candidate mismatch for {candidate}.{name}")
                if "direction" in row:
                    _require(isinstance(row["direction"], str) and row["direction"].lower() == direction,
                             f"Bit row direction mismatch for {candidate}.{name}")
                endpoints[name] = dict(candidate=candidate, name=name, port=port,
                                       offset=offset, direction=direction,
                                       role="driver" if direction == "output" else "sink")
        _require(set(rows) == set(endpoints),
                 f"{candidate}: unknown or omitted bit rows outside declared ports")
        expanded[candidate] = endpoints
    return expanded


def _validate_contract(contract):
    _require(isinstance(contract, Mapping), "Contract must be an object")
    _require(isinstance(contract.get("top"), str) and bool(contract["top"]), "Missing contract top")
    links = contract.get("connections")
    _require(isinstance(links, list) and len(links) == len(_LINKS), "Expected exactly eight connection groups")
    expected = {(a, m): width for a, m, width, _ in _LINKS}
    seen = set()
    for row in links:
        _require(isinstance(row, Mapping), "Invalid connection row")
        key = (row.get("act_port"), row.get("mxu_port"))
        _require(key in expected, f"Unknown connection group {key!r}")
        _require(key not in seen, f"Duplicate connection group {key!r}")
        seen.add(key)
        _require(type(row.get("width")) is int and row["width"] == expected[key],
                 f"Wrong connection width for {key!r}")
        _require(row.get("exact_bit_identity") is True, f"Unverified bit identity for {key!r}")
    _require(seen == set(expected), "Missing fixed connection group")
    external = contract.get("external_ports")
    _require(isinstance(external, Mapping) and len(external) == 40, "Expected 40 parent ports")
    total = 0
    for name, description in external.items():
        _require(isinstance(name, str) and bool(name), "Invalid parent port name")
        _, width = _port_shape(name, description)
        total += width
    _require(total == 1662 and contract.get("external_signal_bits") == total,
             "Expected exactly 1662 parent bits")
    _require(contract.get("address_and_data_bits") == 684 and contract.get("computing_feedback_bits") == 1,
             "Invalid address/data or computing count")
    _require(contract.get("shared_clock") == "clk", "Expected the recorded shared clk")
    _require(contract.get("added_registers") == 0, "Contract introduces unsupported state")
    _require(external.get("clk") == {"direction": "input", "width": 1}, "Invalid parent clk")
    _require(external.get("computing") == {"direction": "output", "width": 1}, "Invalid parent computing")
    return external


def build_graph(contract, views):
    """Return connections, complete nets/incidence, and the original parent ports.

    ``views[candidate]['ports'][port]['bits']`` must be explicit exact bit names
    in LSB order. ``views[candidate]['bits']`` contains those signal rows only.
    Geometry and additional alias/constant metadata are not interpreted here.
    Parent endpoints use candidate ``TOP`` and their declared boundary direction;
    their wiring roles are reversed (an input drives, an output receives).
    """
    external = _validate_contract(contract)
    expanded = _validated_views(views)
    nets, membership, connections = {}, {}, []

    def add(net_name, kind, endpoint):
        key = (endpoint["candidate"], endpoint["name"])
        _require(key not in membership,
                 f"Endpoint {key!r} already belongs to net {membership.get(key)!r}")
        membership[key] = net_name
        net = nets.setdefault(net_name, dict(name=net_name, kind=kind, endpoints=[]))
        _require(net["kind"] == kind, f"Inconsistent net kind for {net_name}")
        net["endpoints"].append(deepcopy(endpoint))

    def ref(endpoint):
        return {"candidate": endpoint["candidate"], "name": endpoint["name"]}

    for act_port, mxu_port, width, driver_candidate in _LINKS:
        group = act_port + "->" + mxu_port
        for candidate, port in (("ACT20", act_port), ("MXU20", mxu_port)):
            description = views[candidate]["ports"].get(port)
            _require(description is not None, f"Missing contracted port {candidate}.{port}")
            direction, actual_width = _port_shape(port, description)
            _require(actual_width == width, f"Width mismatch for {candidate}.{port}")
            expected_direction = "output" if candidate == driver_candidate else "input"
            _require(direction == expected_direction, f"Wrong direction for {candidate}.{port}")
        for offset in range(width):
            act_name = _expanded_names(act_port, width)[offset]
            mxu_name = _expanded_names(mxu_port, width)[offset]
            act, mxu = expanded["ACT20"][act_name], expanded["MXU20"][mxu_name]
            feedback = mxu_port == "computing"
            net_name = ("external:" if feedback else "interface:") + mxu_name
            kind = "external" if feedback else "interface"
            add(net_name, kind, act)
            add(net_name, kind, mxu)
            driver, sink = (act, mxu) if driver_candidate == "ACT20" else (mxu, act)
            connections.append(dict(group=group, offset=offset, act=ref(act), mxu=ref(mxu),
                                    driver=ref(driver), sink=ref(sink), net=net_name))

    for port, description in external.items():
        direction, width = _port_shape(port, description)
        owners = [candidate for candidate in _CANDIDATES if port in views[candidate]["ports"]]
        expected_owner_count = 2 if port == "clk" else 1
        _require(len(owners) == expected_owner_count,
                 f"Unknown or ambiguous parent port {port!r}: owners={owners!r}")
        if port == "computing":
            _require(owners == ["MXU20"], "computing must be the MXU output")
        for candidate in owners:
            child_direction, child_width = _port_shape(port, views[candidate]["ports"][port])
            _require((child_direction, child_width) == (direction, width),
                     f"Parent/macro shape mismatch for {candidate}.{port}")
        for offset, name in enumerate(_expanded_names(port, width)):
            net_name = "external:" + name
            if port == "computing":
                _require(membership.get(("MXU20", name)) == net_name,
                         "computing feedback must share its parent output net")
            else:
                for candidate in owners:
                    add(net_name, "external", expanded[candidate][name])
            add(net_name, "external", dict(candidate="TOP", name=name, port=port, offset=offset,
                                             direction=direction,
                                             role="driver" if direction == "input" else "sink"))

    expected_macro = {(candidate, name) for candidate in _CANDIDATES for name in expanded[candidate]}
    actual_macro = {key for key in membership if key[0] != "TOP"}
    _require(actual_macro == expected_macro,
             f"Unassigned or unknown macro endpoints: missing={sorted(expected_macro-actual_macro)!r}, "
             f"extra={sorted(actual_macro-expected_macro)!r}")
    incidence = []
    ordered_nets = []
    for name in sorted(nets):
        net = nets[name]
        net["endpoints"].sort(key=lambda e: (e["candidate"], e["name"]))
        drivers = [e for e in net["endpoints"] if e["role"] == "driver"]
        sinks = [e for e in net["endpoints"] if e["role"] == "sink"]
        _require(len(drivers) == 1, f"Net {name} must have exactly one boundary driver")
        _require(bool(sinks), f"Net {name} has no boundary sink")
        net["driver"] = deepcopy(drivers[0])
        net["sinks"] = deepcopy(sinks)
        incidence.extend(dict(net=name, **e) for e in net["endpoints"])
        ordered_nets.append(net)
    roles = Counter(e["role"] for e in incidence)
    input_bits = sum(p["width"] for p in external.values() if p["direction"] == "input")
    return dict(
        schema=1, top=contract["top"], external_ports=deepcopy(dict(external)),
        connections=connections, nets=ordered_nets, incidence=incidence,
        summary=dict(connection_groups=8, connection_bits=len(connections), address_and_data_bits=684,
                     computing_feedback_bits=1, external_ports=len(external), external_signal_bits=1662,
                     external_input_bits=input_bits, external_output_bits=1662-input_bits,
                     nets=len(ordered_nets), private_interface_nets=684, interface_nets=685,
                     macro_endpoints=len(expected_macro), top_endpoints=1662,
                     endpoint_incidence=len(incidence), drivers=roles["driver"], sinks=roles["sink"],
                     shared_clock="external:clk", computing_feedback_net="external:computing",
                     boundary_wiring_only=True, logical_aliases_merged=False, constant_ports_merged=False,
                     scope="Fixed boundary-port wiring and declared-direction roles only; physical pins remain distinct despite RTL aliases/constants. No internal independence, RTL equivalence, timing or legal-access proof."),
    )
