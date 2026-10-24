"""Finite explicit workload conversion, recovered from the Issue 63 chat.

Local continuation; not compared byte-for-byte with the protected server copy.
No inference, mapping search, network access, or hardware synthesis.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
from pathlib import Path


class InputError(ValueError):
    pass


def require(ok, message):
    if not ok:
        raise InputError(message)


def obj(value, keys, where):
    require(type(value) is dict, f"{where}: expected object")
    expected = set(keys.split())
    require(set(value) == expected,
            f"{where}: missing={sorted(expected-set(value))}, unknown={sorted(set(value)-expected)}")


def string(value, where):
    require(type(value) is str and bool(value.strip()), f"{where}: nonempty string required")


def integer(value, where, minimum=0):
    require(type(value) is int and value >= minimum, f"{where}: integer >= {minimum} required")


def sequence(value, where):
    require(type(value) is list, f"{where}: array required")
    return value


def unique(values, where):
    require(len(values) == len(set(values)), f"{where}: duplicate value")


def refs(items, target, where):
    for item in sequence(items, where):
        string(item, where)
        require(item in target, f"{where}: missing reference {item}")
    unique(items, where)


def read_json(path):
    def pairs(items):
        out = {}
        for key, value in items:
            require(key not in out, f"duplicate JSON key: {key}")
            out[key] = value
        return out
    def constant(value):
        raise InputError(f"nonfinite JSON number: {value}")
    try:
        return json.loads(Path(path).read_text(encoding="utf8"),
                          object_pairs_hook=pairs, parse_constant=constant)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise InputError(str(exc)) from exc


def canonical(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2,
                       allow_nan=False) + "\n").encode("utf8")


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def evidence(value, where):
    obj(value, "kind source status", where)
    require(value["kind"] in ("synthetic", "config_derived", "reference"), where+": unsupported kind")
    require(value["status"] in ("assumed", "derived", "observed", "unknown"), where+": unsupported status")
    string(value["source"], where+".source")


def index(items, fields, where):
    result = {}
    for n, item in enumerate(sequence(items, where)):
        obj(item, fields, f"{where}[{n}]")
        string(item["id"], where+".id")
        require(item["id"] not in result, f"{where}: duplicate ID {item['id']}")
        result[item["id"]] = item
    return result


def tensor_bytes(t):
    return math.prod(t["shape"]) * t["storage_bits"] // 8 + (t["metadata_bytes"] or 0)


def parse(graph, blocks):
    obj(graph, "schema_version id evidence scope nodes calls tensors storages states events transfers resource_input", "graph")
    obj(blocks, "schema_version id evidence resources links", "blocks")
    require(graph["schema_version"] == "workload-mapping/1", "unknown graph version")
    require(blocks["schema_version"] == "workload-blocks/1", "unknown block version")
    for name, data in (("graph", graph), ("blocks", blocks)):
        string(data["id"], name+".id")
        evidence(data["evidence"], name+".evidence")
    string(graph["scope"], "scope")
    resources = index(blocks["resources"], "id kind capacity_bytes capabilities ports", "resources")
    ports = {}
    for r in resources.values():
        require(r["kind"] in ("compute", "storage", "external", "host", "adapter"), "invalid resource kind")
        if r["capacity_bytes"] is not None:
            integer(r["capacity_bytes"], "capacity_bytes")
        semantics = []
        for cap in sequence(r["capabilities"], "capabilities"):
            obj(cap, "semantic status source", "capability")
            string(cap["semantic"], "semantic")
            semantics.append(cap["semantic"])
            require(cap["status"] in ("declared", "implemented", "verified", "unknown"), "invalid capability status")
            string(cap["source"], "capability.source")
        unique(semantics, "capabilities")
        ports[r["id"]] = index(r["ports"], "id direction protocol width_bits fifo_bytes", r["id"]+".ports")
        for p in r["ports"]:
            require(p["direction"] in ("input", "output"), "invalid port direction")
            if p["protocol"] is not None:
                string(p["protocol"], "protocol")
            for field in ("width_bits", "fifo_bytes"):
                if p[field] is not None:
                    integer(p[field], field, 1)
            require(p["width_bits"] is None or p["width_bits"] % 8 == 0, "interface width_bits must be byte aligned")
    links = index(blocks["links"], "id source source_port destination destination_port protocol", "links")
    fanout, fanin = {}, {}
    for link in links.values():
        for side in ("source", "destination"):
            require(link[side] in resources, f"{link['id']}: missing resource")
            require(link[side+"_port"] in ports[link[side]], f"{link['id']}: missing {side} port")
        src = ports[link["source"]][link["source_port"]]
        dst = ports[link["destination"]][link["destination_port"]]
        require(src["direction"] == "output" and dst["direction"] == "input", f"{link['id']}: direction mismatch")
        string(link["protocol"], "link.protocol")
        for p in (src, dst):
            require(p["protocol"] is None or p["protocol"] == link["protocol"], "protocol mismatch; explicit adapter required")
        require(src["width_bits"] is None or dst["width_bits"] is None or src["width_bits"] == dst["width_bits"], "width mismatch; explicit adapter required")
        fanout.setdefault((link["source"], link["source_port"]), set()).add((link["destination"], link["destination_port"]))
        fanin.setdefault((link["destination"], link["destination_port"]), set()).add((link["source"], link["source_port"]))
    for (rid, pid), peers in list(fanout.items()) + list(fanin.items()):
        if len(peers) > 1:
            require(any(c["semantic"] == "route" and c["status"] != "unknown" for c in resources[rid]["capabilities"]),
                    f"{rid}.{pid}: multiple connections require explicit route/mux capability; no implicit broadcast")
    nodes = index(graph["nodes"], "id semantic contract", "nodes")
    calls = index(graph["calls"], "id node resource reads writes", "calls")
    tensors = index(graph["tensors"], "id shape axes layout logical_bits storage_bits metadata_bytes storage offset_bytes producer consumers role initial alias_of", "tensors")
    stores = index(graph["storages"], "id resource size_bytes begin end", "storages")
    states = index(graph["states"], "id kind initial versions", "states")
    events = index(graph["events"], "id kind ref step phase", "events")
    transfers = index(graph["transfers"], "id tensor source_storage destination_storage path messages", "transfers")
    unique([graph["id"]] + list(nodes)+list(calls)+list(tensors)+list(stores)+list(states)+list(events)+list(transfers), "graph IDs")
    require(bool(events), "finite explicit execution events required")
    positions = {eid: i for i, eid in enumerate(events)}
    for node in nodes.values():
        string(node["semantic"], "node.semantic")
        string(node["contract"], "node.contract")
    seen_calls, seen_transfers, previous_step = [], [], -1
    for e in events.values():
        require(e["kind"] in ("call", "transfer"), "unsupported dynamic event")
        require(e["phase"] in ("prefill", "decode", "iteration"), "unsupported phase")
        integer(e["step"], "event.step")
        require(e["step"] >= previous_step, "event steps must be nondecreasing")
        previous_step = e["step"]
        target = calls if e["kind"] == "call" else transfers
        require(e["ref"] in target, "missing event reference")
        (seen_calls if e["kind"] == "call" else seen_transfers).append(e["ref"])
    require(sorted(seen_calls) == sorted(calls), "each call must have exactly one event")
    require(sorted(seen_transfers) == sorted(transfers), "each transfer must have exactly one event")
    for s in stores.values():
        require(s["resource"] in resources, "storage missing resource")
        integer(s["size_bytes"], "storage.size_bytes")
        require(s["begin"] in events and s["end"] in events, "missing lifetime event")
        require(positions[s["begin"]] <= positions[s["end"]], "reversed storage lifetime")
    consumers = {tid: [] for tid in tensors}
    producers, unresolved = {}, []
    for call in calls.values():
        require(call["node"] in nodes and call["resource"] in resources, "missing node/resource")
        refs(call["reads"], tensors, call["id"]+".reads")
        refs(call["writes"], tensors, call["id"]+".writes")
        require(not set(call["reads"]) & set(call["writes"]), "writes require new tensor version")
        for tid in call["reads"]:
            consumers[tid].append(call["id"])
        for tid in call["writes"]:
            require(tid not in producers, "multiple producers")
            producers[tid] = call["id"]
        semantic = nodes[call["node"]]["semantic"]
        caps = [c for c in resources[call["resource"]]["capabilities"] if c["semantic"] == semantic]
        require(bool(caps), f"{call['id']}: capability {semantic} missing")
        if caps[0]["status"] != "verified":
            unresolved.append(f"{call['id']}: capability only {caps[0]['status']}; hardware function unproven")
    for t in tensors.values():
        require(t["storage"] in stores, "missing tensor storage")
        require(bool(sequence(t["shape"], "shape")), "static nonempty shape required")
        for n in t["shape"]:
            integer(n, "shape dimension", 1)
        require(len(sequence(t["axes"], "axes")) == len(t["shape"]), "shape/axes rank mismatch")
        for a in t["axes"]:
            string(a, "axis meaning")
        unique(t["axes"], "axes")
        string(t["layout"], "layout")
        integer(t["logical_bits"], "logical_bits", 1)
        require(type(t["storage_bits"]) is int and t["storage_bits"] in (8, 16, 32, 64), "unsupported storage_bits")
        require(t["logical_bits"] <= t["storage_bits"], "logical bits exceed container")
        require(t["logical_bits"] != 33 or t["storage_bits"] == 64, "i33 requires i64 container")
        integer(t["offset_bytes"], "offset_bytes")
        if t["metadata_bytes"] is None:
            unresolved.append(t["id"]+": metadata unknown; occupancy is known lower bound")
        else:
            integer(t["metadata_bytes"], "metadata_bytes")
        require(t["role"] in ("activation", "weight", "state", "scale", "bias", "mask"), "invalid tensor role")
        require(type(t["initial"]) is bool, "initial must be boolean")
        refs(t["consumers"], calls, t["id"]+".consumers")
        require(sorted(t["consumers"]) == sorted(consumers[t["id"]]), "incomplete consumer list")
        require(t["producer"] == producers.get(t["id"]), "producer declaration mismatch")
        require(not t["initial"] or t["producer"] is None, "initial cannot have producer")
        require(t["offset_bytes"]+tensor_bytes(t) <= stores[t["storage"]]["size_bytes"], "tensor storage range exceeds allocation")
        if t["alias_of"] is not None:
            require(t["alias_of"] in tensors and t["alias_of"] != t["id"], "missing/cyclic alias")
            require(t["producer"] is None and not t["initial"], "alias cannot produce copy/initial contents")
        else:
            require(t["initial"] or t["producer"] is not None, "tensor has no initial value/producer")
    def root(tid, visited=None):
        visited = set() if visited is None else visited
        require(tid not in visited, "alias cycle")
        visited.add(tid)
        t = tensors[tid]
        if t["alias_of"] is None:
            return tid
        parent = tensors[t["alias_of"]]
        require(t["storage"] == parent["storage"] and t["storage_bits"] == parent["storage_bits"] and t["logical_bits"] == parent["logical_bits"], "alias must share storage and format")
        require(t["offset_bytes"] >= parent["offset_bytes"] and t["offset_bytes"]+tensor_bytes(t) <= parent["offset_bytes"]+tensor_bytes(parent), "view range outside parent")
        return root(t["alias_of"], visited)
    roots = {tid: root(tid) for tid in tensors}
    state_tensors = []
    for state in states.values():
        require(state["kind"] in ("convolution_history", "recurrent", "kv"), "unsupported state kind")
        require(state["initial"] in tensors and (tensors[state["initial"]]["initial"] or tensors[state["initial"]]["producer"] is not None), "state initial value missing")
        previous = state["initial"]
        state_tensors.append(previous)
        for v in sequence(state["versions"], "state.versions"):
            obj(v, "tensor writer previous", "state.version")
            require(v["previous"] == previous, "lost previous state version")
            require(v["tensor"] in tensors and v["writer"] in calls, "missing state version/writer")
            require(tensors[v["tensor"]]["producer"] == v["writer"], "state writer mismatch")
            require(previous in calls[v["writer"]]["reads"], "state writer must read previous version")
            state_tensors.append(v["tensor"])
            previous = v["tensor"]
    unique(state_tensors, "state version ownership")
    require(set(state_tensors) == {t["id"] for t in tensors.values() if t["role"] == "state"}, "every state tensor needs explicit state lineage")
    for tr in transfers.values():
        require(tr["tensor"] in tensors, "missing transfer tensor")
        for key in ("source_storage", "destination_storage"):
            require(tr[key] in stores, "missing transfer storage")
        require(tr["source_storage"] != tr["destination_storage"], "copy requires distinct storage")
        integer(tr["messages"], "messages", 1)
        sequence(tr["path"], "path")
        src, dst = (stores[tr[k]]["resource"] for k in ("source_storage", "destination_storage"))
        cursor = src
        for lid in tr["path"]:
            require(lid in links, "missing link")
            require(links[lid]["source"] == cursor, "invalid directed path")
            cursor = links[lid]["destination"]
        require(cursor == dst and (src == dst or bool(tr["path"])), "path destination mismatch")
        for lid in tr["path"][:-1]:
            mid = links[lid]["destination"]
            require(any(c["semantic"] == "route" and c["status"] != "unknown" for c in resources[mid]["capabilities"]), "explicit forwarding capability missing")
        t = tensors[tr["tensor"]]
        require(t["offset_bytes"]+tensor_bytes(t) <= stores[tr["destination_storage"]]["size_bytes"], "copy destination too small")
    if graph["resource_input"] is not None:
        from .resource_bridge import account
        account([], graph["resource_input"])
    return dict(resources=resources, ports=ports, links=links, nodes=nodes, calls=calls,
                tensors=tensors, stores=stores, states=states, events=events,
                transfers=transfers, positions=positions, roots=roots, unresolved=unresolved)


def validate(graph, blocks):
    x = parse(graph, blocks)
    tensors, stores, events, roots = (x[k] for k in ("tensors", "stores", "events", "roots"))
    pos = x["positions"]
    event_for = {e["ref"]: pos[e["id"]] for e in events.values()}
    uses = {tid: [] for tid in tensors}
    for call in x["calls"].values():
        for tid in call["reads"]:
            uses[roots[tid]].append(event_for[call["id"]])
    for tr in x["transfers"].values():
        uses[roots[tr["tensor"]]].append(event_for[tr["id"]])
    last_use = {tid: max(indices, default=-1) for tid, indices in uses.items()}
    resident, produced = {sid: set() for sid in stores}, set()
    def active(sid, at):
        require(pos[stores[sid]["begin"]] <= at <= pos[stores[sid]["end"]], "use outside storage lifetime")
    def covers(held, wanted):
        a, b = tensors[held], tensors[wanted]
        return roots[held] == roots[wanted] and a["offset_bytes"] <= b["offset_bytes"] and a["offset_bytes"]+tensor_bytes(a) >= b["offset_bytes"]+tensor_bytes(b)
    def write(tid, sid, at):
        active(sid, at)
        t = tensors[tid]
        for old in list(resident[sid]):
            a = tensors[old]
            overlap = max(t["offset_bytes"], a["offset_bytes"]) < min(t["offset_bytes"]+tensor_bytes(t), a["offset_bytes"]+tensor_bytes(a))
            if roots[old] != roots[tid] and overlap:
                require(last_use[roots[old]] <= at, f"{sid}: premature overwrite of live tensor/state {old}")
                resident[sid].remove(old)
        resident[sid].add(tid)
        produced.add(roots[tid])
    for t in tensors.values():
        if t["initial"]:
            require(pos[stores[t["storage"]]["begin"]] == 0, "initial storage must start at first event")
            write(t["id"], t["storage"], 0)
    communications, snapshots = [], []
    for at, e in enumerate(events.values()):
        for sid, s in stores.items():
            if pos[s["end"]] < at:
                resident[sid].clear()
        if e["kind"] == "call":
            call = x["calls"][e["ref"]]
            for tid in call["reads"]:
                require(roots[tid] in produced, f"{call['id']}: consume before production of {tid}")
                locations = [sid for sid, values in resident.items() if stores[sid]["resource"] == call["resource"] and any(covers(held, tid) for held in values)]
                require(bool(locations), f"{call['id']}: {tid} not resident; explicit transfer required")
                for sid in locations:
                    active(sid, at)
            for tid in call["writes"]:
                sid = tensors[tid]["storage"]
                require(stores[sid]["resource"] == call["resource"], "producer differs from allocation resource")
                write(tid, sid, at)
        else:
            tr = x["transfers"][e["ref"]]
            tid, t = tr["tensor"], tensors[tr["tensor"]]
            active(tr["source_storage"], at)
            require(any(covers(held, tid) for held in resident[tr["source_storage"]]), "source tensor not resident")
            write(tid, tr["destination_storage"], at)
            path = [stores[tr["source_storage"]]["resource"]] + [x["links"][lid]["destination"] for lid in tr["path"]]
            communications.append(dict(id=tr["id"], event=e["id"], tensor=tid,
                source_storage=tr["source_storage"], destination_storage=tr["destination_storage"],
                path=path, links=tr["path"], shape=t["shape"], logical_bits=t["logical_bits"],
                storage_bits=t["storage_bits"], metadata_bytes=t["metadata_bytes"], messages=tr["messages"],
                payload_bits=math.prod(t["shape"])*t["logical_bits"],
                container_bytes=math.prod(t["shape"])*t["storage_bits"]//8,
                evidence=copy.deepcopy(graph["evidence"])))
        used = {rid: 0 for rid in x["resources"]}
        for s in stores.values():
            if pos[s["begin"]] <= at <= pos[s["end"]]:
                used[s["resource"]] += s["size_bytes"]
        for rid, size in used.items():
            capacity = x["resources"][rid]["capacity_bytes"]
            require(capacity is None or size <= capacity, f"{rid}: declared storage occupancy exceeds capacity")
        snapshots.append(dict(event=e["id"], occupancy_bytes=used))
    weights = {roots[t["id"]] for t in tensors.values() if t["role"] == "weight"}
    return dict(status="pass", scope="logical conversion and declared finite storage only",
        communication=communications, storage=dict(
            peak_bytes={rid: max(s["occupancy_bytes"][rid] for s in snapshots) for rid in x["resources"]},
            events=snapshots, allocations=list(stores.values()),
            unique_weight_elements=sum(math.prod(tensors[tid]["shape"]) for tid in weights),
            alias_capacity_bytes=0, qualification="declared allocation; not measured GPU/HBM traffic"),
        unresolved=sorted(set(x["unresolved"] + [r["id"]+": capacity unknown" for r in x["resources"].values() if r["capacity_bytes"] is None])))


def build(graph, blocks):
    from .resource_bridge import account
    checked = validate(graph, blocks)
    transfers = [{k: t[k] for k in ("id", "path", "shape", "logical_bits", "storage_bits", "metadata_bytes", "messages")}
                 for t in checked["communication"] if len(t["path"]) >= 2 and t["metadata_bytes"] is not None]
    ledger = account(transfers, graph["resource_input"])
    accounting = {t["id"]: t for t in ledger["transfers"]}
    port_lookup = {r["id"]: {p["id"]: p for p in r["ports"]} for r in blocks["resources"]}
    link_lookup = {link["id"]: link for link in blocks["links"]}
    for t in checked["communication"]:
        t["transport"] = accounting.get(t["id"])
        t["interface_width_bits"] = []
        for lid in t["links"]:
            link = link_lookup[lid]
            for side in ("source", "destination"):
                p = port_lookup[link[side]][link[side+"_port"]]
                t["interface_width_bits"].append(p["width_bits"])
                for field in ("protocol", "fifo_bytes", "width_bits"):
                    if p[field] is None:
                        checked["unresolved"].append(lid+": "+field+" unknown")
                if p["fifo_bytes"] is not None and t["transport"] is not None:
                    require(p["fifo_bytes"] >= min(2048, t["transport"]["wire_bytes"]), "endpoint FIFO cannot hold declared packet")
        if t["transport"] is not None:
            t["transport"]["ideal_link_cycles_scope"] = "#41 reference 128bit link; not execution cycles or physical wires"
        elif t["metadata_bytes"] is None:
            checked["unresolved"].append(t["id"]+": packet cost blocked by unknown metadata")
        elif len(t["path"]) < 2:
            t["transport"] = {"wire_bytes": 0, "packets": 0, "scope": "explicit local copy"}
    mapping = dict(schema_version="mapping-request/1", contract_status="proposed downstream input; no #55 reader",
        id=graph["id"], evidence=graph["evidence"], graph_sha256=digest(graph), blocks_sha256=digest(blocks),
        logical_graph=copy.deepcopy(graph),
        resources=copy.deepcopy(blocks["resources"]), links=copy.deepcopy(blocks["links"]),
        events=copy.deepcopy(graph["events"]), communication=checked["communication"], storage=checked["storage"],
        transport=dict(edges=ledger["edges"], shared_TX=ledger["shared_TX"]), assumptions=checked["unresolved"],
        physical_policy=dict(fixed_layers=["M"+str(i) for i in range(1,9)], custom_layers=["M9","M10"],
            custom_vias=["M8-M9","M9-M10"], fallback_layers=["M11","M12"],
            technical_via_permission="unknown", physical_wires="unknown"))
    summary = dict(schema_version="workload-summary/1", logical={"status":"pass", "scope":checked["scope"]},
        reference_assets={"status":"not_executed"}, physical={"status":"not_executed", "missing":[
            "same-version instances and ports", "real fixed M8 access routes", "frozen base and technology via evidence"]},
        hardware_functional_qualification="unknown", resource_projection={
            "status":"pass" if ledger["resource_input"] is not None else "not_executed",
            "full_graph_compatible":False, "incompatibilities":ledger["incompatibilities"],
            "omitted_semantics":["event order", "state versions", "alias/lifetime", "instance/port identity", "physical bindings"]})
    return dict(mapping_request=mapping, resource_input=ledger["resource_input"],
                resource_report=ledger["resource_report"], summary=summary)
