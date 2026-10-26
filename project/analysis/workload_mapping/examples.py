"""Small explicit workload graphs; these fixtures do not execute model arithmetic.

Qwen dimensions reuse the PR50 config-only example. All hardware, call contracts,
quantization, scheduling and traffic placement below are illustrative assumptions.
"""
from __future__ import annotations

import argparse
import copy
import json
import math
from pathlib import Path


def _evidence(kind="synthetic", status="assumed", source="Hand-built contract fixture; no measured trace"):
    return {"kind": kind, "source": source, "status": status}


class _Graph:
    """Build explicit copies without treating a tensor ID as globally resident."""

    def __init__(self, identifier, scope, evidence=None):
        self.graph = {
            "schema_version": "workload-mapping/1", "id": identifier,
            "evidence": evidence or _evidence(), "scope": scope,
            "nodes": [], "calls": [], "tensors": [], "storages": [],
            "states": [], "events": [], "transfers": [], "resource_input": None,
        }
        self.blocks = {
            "schema_version": "workload-blocks/1", "id": identifier + "-blocks",
            "evidence": _evidence(source="Synthetic declared hardware; no RTL, capacity or timing measurement"),
            "resources": [], "links": [],
        }
        self.tensors = {}
        self.resources = {}
        self.resident = {}
        self.links = {}

    def resource(self, name, kind="compute"):
        if name not in self.resources:
            resource = {
                "id": name, "kind": kind, "capacity_bytes": 1 << 30,
                "capabilities": [],
                "ports": [
                    {"id": name + "_in", "direction": "input", "protocol": "ready_valid",
                     "width_bits": 128, "fifo_bytes": 2048},
                    {"id": name + "_out", "direction": "output", "protocol": "ready_valid",
                     "width_bits": 128, "fifo_bytes": 2048},
                ],
            }
            self.resources[name] = resource
            self.blocks["resources"].append(resource)
        return name

    def tensor(self, name, shape, resource, bits=8, role="activation",
               producer=None, metadata_bytes=0, axes=None, initial=None):
        self.resource(resource, "host" if resource == "host" else "compute")
        tid, sid = "t_" + name, "s_" + name
        storage_bits = next(n for n in (8, 16, 32, 64) if n >= bits)
        elements = math.prod(shape)
        self.graph["storages"].append({
            "id": sid, "resource": resource,
            "size_bytes": elements * storage_bits // 8 + (metadata_bytes or 0),
            "begin": "", "end": "",
        })
        tensor = {
            "id": tid, "shape": list(shape),
            "axes": axes or ["d" + str(i) for i in range(len(shape))],
            "layout": "row_major", "logical_bits": bits, "storage_bits": storage_bits,
            "metadata_bytes": metadata_bytes, "storage": sid, "offset_bytes": 0,
            "producer": producer, "consumers": [], "role": role,
            "initial": producer is None if initial is None else initial, "alias_of": None,
        }
        self.graph["tensors"].append(tensor)
        self.tensors[tid] = tensor
        self.resident[tid] = {resource: sid}
        return tid

    def alias(self, name, tensor_id):
        """Declare a full view of existing bytes; do not allocate or copy them."""
        tensor = copy.deepcopy(self.tensors[tensor_id])
        tensor.update(id="t_" + name, producer=None, initial=False,
                      alias_of=tensor_id, consumers=[])
        self.graph["tensors"].append(tensor)
        self.tensors[tensor["id"]] = tensor
        self.resident[tensor["id"]] = dict(self.resident[tensor_id])
        return tensor["id"]

    def via(self, source, destination, intermediate):
        """Replace an existing direct route with two explicitly declared hops."""
        direct = self.links[(source, destination)]
        self.resource(intermediate, "adapter")
        self.resources[intermediate]["capabilities"].append({
            "semantic": "route", "status": "declared",
            "source": "Synthetic intermediate forwarder; no physical routing or hardware proof",
        })
        self.blocks["links"] = [link for link in self.blocks["links"] if link["id"] != direct]
        path = []
        for first, last in ((source, intermediate), (intermediate, destination)):
            lid = "l_" + first + "_to_" + last
            self.links[(first, last)] = lid
            self.blocks["links"].append({
                "id": lid, "source": first, "source_port": first + "_out",
                "destination": last, "destination_port": last + "_in",
                "protocol": "ready_valid",
            })
            path.append(lid)
        for transfer in self.graph["transfers"]:
            if transfer["path"] == [direct]:
                transfer["path"] = list(path)

    def _event(self, kind, ref, phase):
        eid = "e_" + ref
        self.graph["events"].append({
            "id": eid, "kind": kind, "ref": ref,
            "step": len(self.graph["events"]), "phase": phase,
        })
        return eid

    def _copy(self, tensor_id, destination, phase):
        if destination in self.resident[tensor_id]:
            return
        tensor = self.tensors[tensor_id]
        source, source_storage = next(iter(self.resident[tensor_id].items()))
        self.resource(destination)
        pair = (source, destination)
        if pair not in self.links:
            lid = "l_" + source + "_to_" + destination
            self.links[pair] = lid
            self.blocks["links"].append({
                "id": lid, "source": source, "source_port": source + "_out",
                "destination": destination, "destination_port": destination + "_in",
                "protocol": "ready_valid",
            })
        sid = "s_copy_" + tensor_id + "_to_" + destination
        self.graph["storages"].append({
            "id": sid, "resource": destination,
            "size_bytes": math.prod(tensor["shape"]) * tensor["storage_bits"] // 8
                          + (tensor["metadata_bytes"] or 0),
            "begin": "", "end": "",
        })
        xid = "tr_" + tensor_id + "_to_" + destination
        self.graph["transfers"].append({
            "id": xid, "tensor": tensor_id, "source_storage": source_storage,
            "destination_storage": sid, "path": [self.links[pair]], "messages": 1,
        })
        self._event("transfer", xid, phase)
        self.resident[tensor_id][destination] = sid

    def call(self, name, semantic, resource, reads, shape, bits=8,
             role="activation", phase="prefill", axes=None):
        self.resource(resource)
        for tid in reads:
            self._copy(tid, resource, phase)
        capability = {"semantic": semantic, "status": "declared",
                      "source": "Synthetic functional requirement; implementation unverified"}
        if not any(c["semantic"] == semantic for c in self.resources[resource]["capabilities"]):
            self.resources[resource]["capabilities"].append(capability)
        nid, cid = "n_" + name, "c_" + name
        self.graph["nodes"].append({
            "id": nid, "semantic": semantic,
            "contract": "Illustrative explicit shapes/formats; no numeric, rounding, saturation or timing verification",
        })
        output = self.tensor(name, shape, resource, bits, role, cid, axes=axes)
        self.graph["calls"].append({
            "id": cid, "node": nid, "resource": resource,
            "reads": list(reads), "writes": [output],
        })
        for tid in reads:
            self.tensors[tid]["consumers"].append(cid)
        self._event("call", cid, phase)
        return output

    def state(self, name, kind, initial, updates):
        self.graph["states"].append({
            "id": "state_" + name, "kind": kind, "initial": initial,
            "versions": [
                {"tensor": tensor, "writer": self.tensors[tensor]["producer"], "previous": previous}
                for tensor, previous in updates
            ],
        })
        self.tensors[initial]["role"] = "state"
        for tensor, _ in updates:
            self.tensors[tensor]["role"] = "state"

    def finish(self):
        if not self.graph["events"]:
            raise ValueError("example requires events")
        first, last = self.graph["events"][0]["id"], self.graph["events"][-1]["id"]
        for storage in self.graph["storages"]:
            storage["begin"], storage["end"] = first, last
        port_links = {}
        for link in self.blocks["links"]:
            for side in ("source", "destination"):
                key = (side, link[side], link[side + "_port"])
                port_links.setdefault(key, []).append(link)
        routed = {resource for (_, resource, _), links in port_links.items() if len(links) > 1}
        for resource in sorted(routed):
            if any(c["semantic"] == "route" for c in self.resources[resource]["capabilities"]):
                continue
            self.resources[resource]["capabilities"].append({
                "semantic": "route", "status": "declared",
                "source": "Synthetic shared-port mux/arbiter/forwarder for fanin or fanout; serialized reference TX, not implementation proof",
            })
        return self.graph, self.blocks


def minimal():
    """A four-byte input copy, matrix output and explicit cross-Block copy."""
    b = _Graph("minimal", "Synthetic two-call dependency and explicit transfer example.")
    x = b.tensor("input", [1, 4], "host")
    weight = b.tensor("weight", [4, 2], "matrix", role="weight")
    acc = b.call("matmul", "matrix", "matrix", [x, weight], [1, 2], bits=32)
    b.call("requant", "requantize", "vector", [acc], [1, 2])
    return b.finish()


def reuse():
    """Two node calls reuse one compute Block; separate live intermediates remain."""
    b = _Graph("reuse", "Synthetic reuse of the same matrix resource across two calls.")
    x = b.tensor("input", [1, 4], "matrix")
    weight = b.tensor("weight", [4, 4], "matrix", role="weight")
    first = b.call("matrix_first", "matrix", "matrix", [x, weight], [1, 4], bits=32)
    middle = b.call("rq_first", "requantize", "vector", [first], [1, 4])
    second = b.call("matrix_second", "matrix", "matrix", [middle, weight], [1, 4], bits=32)
    b.call("rq_second", "requantize", "vector", [second], [1, 4])
    return b.finish()


def state_feedback():
    """Three convolution and recurrent steps with explicit previous versions."""
    b = _Graph("state-feedback", "Synthetic three-step convolution and recurrent state lineage.")
    history0 = b.tensor("history0", [2, 4], "state", role="state")
    recurrent0 = b.tensor("recurrent0", [4, 4], "state", bits=32, role="state")
    previous_h, previous_r = history0, recurrent0
    histories, recurrent = [], []
    for i in range(3):
        x = b.tensor("input" + str(i), [1, 4], "host")
        convolved = b.call("convolution" + str(i + 1), "convolution", "state",
                           [previous_h, x], [1, 4], phase="iteration")
        h = b.call("history" + str(i + 1), "convolution_history_update", "state",
                   [previous_h, x], [2, 4], role="state", phase="iteration")
        r = b.call("recurrent" + str(i + 1), "recurrent_update", "state",
                   [previous_r, convolved], [4, 4], bits=32, role="state", phase="iteration")
        histories.append((h, previous_h))
        recurrent.append((r, previous_r))
        previous_h, previous_r = h, r
    b.state("history", "convolution_history", history0, histories)
    b.state("recurrent", "recurrent", recurrent0, recurrent)
    return b.finish()


def alias_copy_transport():
    """Multiple consumers, an alias, physical copies, i33, scales and shared TX."""
    b = _Graph(
        "alias-copy-transport",
        "Synthetic wide values and explicit scale tensor; one local alias consumer, "
        "two remote consumers, one two-hop route and shared source output. "
        "Metadata describes a separate eight-byte envelope, not duplicate scale data.",
    )
    data = b.tensor("wide_input", [1, 4], "matrix", bits=33, metadata_bytes=8)
    view = b.alias("wide_view", data)
    scale = b.tensor("scale", [1], "matrix", bits=32, role="scale")
    b.call("local_reduce", "wide_reduce", "matrix", [view, scale], [1, 1], bits=33)
    b.call("remote_left", "wide_reduce", "vector_left", [view, scale], [1, 1], bits=33)
    b.call("remote_right", "wide_reduce", "vector_right", [data, scale], [1, 1], bits=33)
    b.via("matrix", "vector_left", "forwarder")
    return b.finish()


def attention(tiny=False):
    """Selected layer, prefill two tokens then decode one; no actual model trace."""
    H, I, Q, KV, D = (4, 8, 2, 1, 2) if tiny else (1024, 3072, 16, 8, 128)
    ev = _evidence() if tiny else _evidence(
        "config_derived", "derived",
        "PR50@b06d85a801a87c07f9745ccae6950dc7e4cbd0d2 config-only Qwen dimensions "
        "H1024/I3072/Q16/KV8/head128; schedule, formats, placement and Blocks synthetic",
    )
    b = _Graph(
        "attention-tiny" if tiny else "qwen-config",
        "One selected layer, prefill2/decode1, explicit Q/K/V/O, KV versions, "
        "gate/up/down and two residuals; no checkpoint, inference or captured numerical trace.",
        ev,
    )
    dims = {"q": (H, Q * D), "k": (H, KV * D), "v": (H, KV * D),
            "o": (Q * D, H), "gate": (H, I), "up": (H, I), "down": (I, H)}
    weights = {
        name: b.tensor("w_" + name, list(shape), "matrix", role="weight",
                       axes=["input", "output"])
        for name, shape in dims.items()
    }

    def linear(prefix, name, value, rows, output, phase):
        acc = b.call(prefix + "_" + name + "_acc", "matrix", "matrix",
                     [value, weights[name]], [rows, output], bits=32, phase=phase)
        return b.call(prefix + "_" + name, "requantize", "vector", [acc],
                      [rows, output], phase=phase)

    def part(prefix, rows, phase, previous=None):
        x = b.tensor(prefix + "_input", [rows, H], "host", axes=["token", "hidden"])
        norm = b.call(prefix + "_norm1", "normalization", "vector", [x],
                      [rows, H], phase=phase)
        q = linear(prefix, "q", norm, rows, Q * D, phase)
        k = linear(prefix, "k", norm, rows, KV * D, phase)
        v = linear(prefix, "v", norm, rows, KV * D, phase)
        q = b.call(prefix + "_q_rope", "rotary_position", "vector", [q],
                   [rows, Q, D], phase=phase, axes=["token", "q_head", "head_dim"])
        k = b.call(prefix + "_k_rope", "rotary_position", "vector", [k],
                   [rows, KV, D], phase=phase, axes=["token", "kv_head", "head_dim"])
        v = b.call(prefix + "_v_layout", "reshape", "vector", [v],
                   [rows, KV, D], phase=phase, axes=["token", "kv_head", "head_dim"])
        if previous is None:
            full_k, full_v = k, v
        else:
            full_k = b.call(prefix + "_k_append", "kv_append", "state",
                            [previous[0], k], [3, KV, D], role="state", phase=phase)
            full_v = b.call(prefix + "_v_append", "kv_append", "state",
                            [previous[1], v], [3, KV, D], role="state", phase=phase)
            b.state("kv_key", "kv", previous[0], [(full_k, previous[0])])
            b.state("kv_value", "kv", previous[1], [(full_v, previous[1])])
        context = b.call(prefix + "_attention", "grouped_query_attention", "attention",
                         [q, full_k, full_v], [rows, Q * D], phase=phase)
        output = linear(prefix, "o", context, rows, H, phase)
        residual = b.call(prefix + "_residual1", "residual_add", "vector",
                          [x, output], [rows, H], phase=phase)
        norm2 = b.call(prefix + "_norm2", "normalization", "vector", [residual],
                       [rows, H], phase=phase)
        gate = linear(prefix, "gate", norm2, rows, I, phase)
        up = linear(prefix, "up", norm2, rows, I, phase)
        gated = b.call(prefix + "_gate_up", "gated_activation", "vector", [gate, up],
                       [rows, I], phase=phase)
        down = linear(prefix, "down", gated, rows, H, phase)
        b.call(prefix + "_residual2", "residual_add", "vector",
               [residual, down], [rows, H], phase=phase)
        return full_k, full_v

    prefix_kv = part("prefill", 2, "prefill")
    part("decode", 1, "decode", prefix_kv)
    return b.finish()


def blocks_replacement(variant="wider"):
    """Same workload with a different declared hardware inventory, never measured."""
    graph, blocks = minimal()
    blocks = copy.deepcopy(blocks)
    blocks["id"] = "minimal-replacement-" + variant
    if variant == "wider":
        for resource in blocks["resources"]:
            for port in resource["ports"]:
                port["width_bits"] = 256
    elif variant == "unknown":
        for resource in blocks["resources"]:
            for capability in resource["capabilities"]:
                capability["status"] = "unknown"
    elif variant == "capacity_limited":
        for resource in blocks["resources"]:
            resource["capacity_bytes"] = 1
    else:
        raise ValueError("unsupported replacement variant: " + variant)
    return graph, blocks


def write_examples(destination):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    builders = {
        "minimal": minimal, "reuse": reuse, "state-feedback": state_feedback,
        "attention-tiny": lambda: attention(True), "qwen-config": attention,
        "blocks-replacement": blocks_replacement,
        "alias-copy-transport": alias_copy_transport,
    }
    for name, builder in builders.items():
        graph, blocks = builder()
        for suffix, value in (("mapping", graph), ("blocks", blocks)):
            path = destination / (name + "." + suffix + ".json")
            path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n",
                            encoding="utf-8", newline="\n")
    return len(builders)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).with_name("examples"))
    args = parser.parse_args()
    print(json.dumps({"examples_written": write_examples(args.output_dir),
                      "output_dir": str(args.output_dir)}))
