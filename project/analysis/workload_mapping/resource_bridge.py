"""Pinned #48 packet/multi-hop/shared-TX arithmetic without invented hardware.

Recovered from chat preparation, including its pending hardening; not compared
with server files. Reuses the existing sibling llm_resources sources unchanged.
account() checks transport records, not graph dependencies or physical routes.
Temporary S-prefixed names only reach upstream arithmetic; they allocate nothing.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
from pathlib import Path
import types

HERE = Path(__file__).resolve().parent
SOURCE_DIR = HERE.parent / "llm_resources"
SOURCE_LOCK = HERE / "resource_source_lock.json"
UPSTREAM_COMMIT = "b06d85a801a87c07f9745ccae6950dc7e4cbd0d2"
INTEGRATION_COMMIT = "a5ff0c5af973ffeafa441712cd3f6e491da5a2fd"
SOURCE_HASHES = {
    "estimate.py": "55e42ed6528a4f8805971ba2719b22d7ff4392a069b4ab7ab983d281990b84f3",
    "schema.json": "8ad314e84626b600eb1b4bcb55505ecddcbff39ea9745de72537fd0627d291b4",
    "profiles/block_candidate_v1.json": "671b848f3225fe5ec06cd19465bcc929d1a66c49cf8008e991ae61b0633ea430",
    "examples/qwen3_06b.json": "b795f90e0a0d92095767da6c5fea38f1b35d5cc494f8bbd4377828359f2d87a7",
}
PACKET_KEYS = frozenset({
    "data_link_bits", "beat_bytes", "packet_header_bytes", "endpoint_fifo_bytes",
})
TRANSFER_KEYS = frozenset({
    "id", "path", "shape", "logical_bits", "storage_bits", "metadata_bytes", "messages",
})


class ResourceError(ValueError):
    """Invalid transport input, source lock, or #48 envelope."""


def _unique(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise ResourceError("duplicate source-lock JSON key: " + key)
        out[key] = value
    return out


def expected_source_lock():
    """The Python constants, not a mutable lock file, anchor accepted source bytes."""
    return {
        "schema_version": "workload-resource-source-lock/1",
        "repository": "rayggxia-workspace/LLMHardwareDesign",
        "integration_commit": INTEGRATION_COMMIT,
        "recovery": "chat preparation recovered locally; not compared with server files",
        "source_directory": "project/analysis/llm_resources",
        "files": [
            {"path": path, "sha256": digest, "commit": UPSTREAM_COMMIT,
             "upstream_path": "project/analysis/llm_resources/" + path,
             "url": ("https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/"
                     + UPSTREAM_COMMIT + "/project/analysis/llm_resources/" + path)}
            for path, digest in sorted(SOURCE_HASHES.items())
        ],
        "candidate_original": {
            "commit": "3fa0b45070c7ce4587240589d48703d02a1b5246",
            "path": "project/experiments/block_candidate/candidate.json",
            "sha256": SOURCE_HASHES["profiles/block_candidate_v1.json"],
            "status": "declared candidate; not implemented hardware",
        },
    }


def verify_sources(source_root=None, lock_path=None):
    """Verify all four existing sources and the lock on every load."""
    root = Path(source_root) if source_root is not None else SOURCE_DIR
    lock_file = Path(lock_path) if lock_path is not None else SOURCE_LOCK
    try:
        root = root.resolve(strict=True)
        lock_location = lock_file.resolve(strict=True)
        if not lock_location.is_relative_to(lock_file.parent.resolve(strict=True)):
            raise ResourceError("source lock escapes its declared directory")
        lock = json.loads(lock_location.read_text(encoding="utf-8"), object_pairs_hook=_unique)
        if lock != expected_source_lock():
            raise ResourceError("fixed resource source lock differs from audited records")
        for path, expected in SOURCE_HASHES.items():
            location = (root / path).resolve(strict=True)
            if not location.is_relative_to(root):
                raise ResourceError("fixed resource dependency escapes source directory: " + path)
            actual = hashlib.sha256(location.read_bytes()).hexdigest()
            if actual != expected:
                raise ResourceError("fixed resource dependency SHA-256 mismatch: " + path)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ResourceError("fixed resource dependency unavailable: " + str(exc)) from exc
    return {"source_sha256_verified": True, **copy.deepcopy(lock)}


def load_upstream():
    """Load the existing estimator only after its exact pinned bytes pass."""
    provenance = verify_sources()
    module = types.ModuleType("workload_mapping_pinned_llm_resources")
    module.__file__ = str(SOURCE_DIR / "estimate.py")
    exec(compile((SOURCE_DIR / "estimate.py").read_bytes(), module.__file__, "exec"),
         module.__dict__)
    candidate = module.read_json(SOURCE_DIR / "profiles" / "block_candidate_v1.json")
    module.validate_candidate(candidate)
    return module, candidate, provenance


def _integer(value, where, minimum=0):
    if type(value) is not int or value < minimum:
        raise ResourceError(f"{where}: expected integer >= {minimum}")
    return value


def _transfers(records):
    if not isinstance(records, list):
        raise ResourceError("transfers: expected array")
    seen, result = set(), []
    for index, raw in enumerate(records):
        where = f"transfers[{index}]"
        if not isinstance(raw, dict) or set(raw) != TRANSFER_KEYS:
            raise ResourceError(where + ": expected exactly " + ", ".join(sorted(TRANSFER_KEYS)))
        item = copy.deepcopy(raw)
        name = item["id"]
        if not isinstance(name, str) or not name or name in seen:
            raise ResourceError(where + ".id: expected unique nonempty string")
        seen.add(name)
        path = item["path"]
        if (not isinstance(path, list) or len(path) < 2
                or any(not isinstance(p, str) or not p for p in path)):
            raise ResourceError(where + ".path: expected at least two nonempty resource IDs")
        shape = item["shape"]
        if not isinstance(shape, list) or not shape:
            raise ResourceError(where + ".shape: expected static nonempty positive integer shape")
        for dimension in shape:
            _integer(dimension, where + ".shape", 1)
        logical = _integer(item["logical_bits"], where + ".logical_bits", 1)
        if logical > 64:
            raise ResourceError(where + ".logical_bits: maximum 64")
        storage = _integer(item["storage_bits"], where + ".storage_bits", 1)
        if storage not in (8, 16, 32, 64) or logical > storage:
            raise ResourceError(where + ": unsupported storage container or logical bits exceed container")
        if logical == 33 and storage != 64:
            raise ResourceError(where + ": i33 transport requires an i64 container")
        _integer(item["metadata_bytes"], where + ".metadata_bytes (unknown must stay outside known ledger)")
        if item["messages"] is not None:
            _integer(item["messages"], where + ".messages", 1)
        result.append(item)
    return result


def _upstream_transfer(item, path=None):
    return {
        "name": item["id"], "path": list(path if path is not None else item["path"]),
        "shape": list(item["shape"]), "logical_bits": item["logical_bits"],
        "storage_bits": item["storage_bits"], "metadata_bytes": item["metadata_bytes"],
        "messages_per_step": item["messages"],
    }


def _arithmetic_envelope():
    # Synthetic one-parameter shell solely for the unmodified API. Its model,
    # inventory and storage conclusions never become user workload results.
    return {
        "schema_version": "llm-resource-input/1",
        "model": {
            "name": "synthetic-api-shell-not-a-workload", "kind": "dense",
            "total_parameters": 1, "int8_parameters": 1, "auxiliary_parameters": [],
            "linear_ops": None, "linear_macs_per_token": 1, "linear_outputs_per_token": None,
            "attention": [], "recurrent_states": [], "max_context_tokens": None,
            "source": {"kind": "hypothetical", "uri": "urn:workload-mapping:packet-arithmetic",
                       "revision": None,
                       "note": "Synthetic API shell only; model and inventory results discarded."},
        },
        "precision": {"weight_bits": 8, "activation_bits": 8, "accumulator_bits": 32,
                      "kv_bits": 8, "quantization_contract": None},
        "scenario": {"phase": "prefill", "batch": 1, "input_tokens": 1, "output_tokens": 0,
                     "cached_tokens": 0, "target_tokens_per_second": None},
        "hardware": {
            "candidate_file": "profiles/block_candidate_v1.json", "matrix_counts": [1],
            "clock_hz": None, "matrix_utilization": None, "rq_initiation_interval_cycles": None,
            "external_capacity_bytes": None, "external_effective_bytes_per_second": None,
            "link_effective_fraction": None, "shared_reserve_bytes": 0,
        },
        "placement": {"weights": "unknown", "kv": "unknown", "recurrent": "unknown"},
        "accounting": {
            "weight_scale": None, "kv_scale": None, "weight_padding_bytes": None,
            "shared_workspace_bytes": None, "external_workspace_bytes": None,
            "weight_read_passes": None, "kv_read_multiplier": None,
            "recurrent_read_write_passes": None,
        },
        "mapping": {"matrix_tile": {
            "rows": 1, "columns": 1, "reduction": 1, "operand_copies": 1,
            "accumulator_copies": 1, "reserved_bytes": 0,
        }},
        "transfers": [],
    }


def account(transfers, resource_input=None, *, packet_profile=None):
    """Packet/edge/TX arithmetic plus an optional explicitly bounded #48 export.

    Unknown message counts remain null; unknown metadata cannot enter this ledger.
    Every endpoint is injectively renamed S0.. inside the cost API only. This does
    not allocate banks, links, ports, rates or physical wires. resource_input must
    be an explicit valid #48 model envelope; its transfers are replaced by the
    representable path subset. Packet overrides cannot claim the original profile.
    """
    records = _transfers(transfers)
    upstream, original, provenance = load_upstream()
    candidate = copy.deepcopy(original)
    if packet_profile is not None:
        if not isinstance(packet_profile, dict) or not set(packet_profile) <= PACKET_KEYS:
            raise ResourceError("packet_profile: unknown packet-format field")
        for key, value in packet_profile.items():
            _integer(value, "packet_profile." + key)
            candidate[key] = value
    try:
        upstream.validate_candidate(candidate)
        if resource_input is not None:
            upstream.validate_input(resource_input)
    except (upstream.InputError, ArithmeticError) as exc:
        raise ResourceError(str(exc)) from exc

    names = sorted({node for item in records for node in item["path"]})
    rename = {name: "S" + str(index) for index, name in enumerate(names)}
    inverse = {value: key for key, value in rename.items()}
    graph = {value: [] for value in rename.values()} or {"S0": []}
    for item in records:
        for source, destination in zip(item["path"], item["path"][1:]):
            if rename[destination] not in graph[rename[source]]:
                graph[rename[source]].append(rename[destination])
    for destinations in graph.values():
        destinations.sort()
    candidate["logical_bindings_hybrid"] = graph
    internal = _arithmetic_envelope()
    internal["transfers"] = [_upstream_transfer(item, [rename[n] for n in item["path"]])
                             for item in records]
    try:
        arithmetic = upstream.compute(internal, candidate)
    except (upstream.InputError, ArithmeticError) as exc:
        raise ResourceError("packet accounting: " + str(exc)) from exc
    per_transfer = []
    for item, result in zip(records, arithmetic["transfers"]):
        per_transfer.append({
            "id": item["id"], "path": item["path"], "messages": item["messages"],
            "payload_bytes": result["payload_bytes"],
            "logical_payload_bits": math.prod(item["shape"]) * item["logical_bits"],
            "storage_container_bytes": math.prod(item["shape"]) * item["storage_bits"] // 8,
            "metadata_bytes": item["metadata_bytes"],
            "packet_header_and_alignment_bytes": result["wire_bytes"] - result["payload_bytes"],
            "packets": result["packets"], "wire_bytes": result["wire_bytes"],
            "ideal_link_cycles": result["ideal_link_cycles"],
            "hop_summed_wire_bytes_per_step": result["hop_summed_wire_bytes_per_step"],
        })
    transport = arithmetic["reference_transport"]
    known_edges = {(inverse[e["source"]], inverse[e["destination"]]): e
                   for e in transport["edges"]}
    known_tx = {inverse[node]: entry for node, entry in transport["shared_TX"].items()}
    # Upstream sums known counts only. Preserve its arithmetic, keep every
    # declared edge/TX visible, and put null on incomplete totals.
    complete_edges, complete_tx = {}, {}
    for item in records:
        for source, destination in zip(item["path"], item["path"][1:]):
            pair = (source, destination)
            complete_edges[pair] = complete_edges.get(pair, True) and item["messages"] is not None
            complete_tx[source] = complete_tx.get(source, True) and item["messages"] is not None

    def finish_entry(entry, complete):
        known = entry["accounted_wire_bytes_per_step"] if entry is not None else 0
        return {
            "accounted_wire_bytes_per_step": known if complete else None,
            "known_wire_bytes_per_step_lower_bound": known, "all_message_counts_known": complete,
            "required_bytes_per_second": None, "capacity_bytes_per_second": None,
            "lower_bound_exceeds_capacity": None,
        }

    edges = [{"source": src, "destination": dst,
              **finish_entry(known_edges.get((src, dst)), complete)}
             for (src, dst), complete in sorted(complete_edges.items())]
    shared = {src: finish_entry(known_tx.get(src), complete)
              for src, complete in sorted(complete_tx.items())}
    incompatible, compatible = [], []
    reference_graph = original["logical_bindings_hybrid"]
    format_changed = any(candidate[key] != original[key] for key in PACKET_KEYS)
    for item in records:
        if format_changed:
            incompatible.append({"transfer_id": item["id"],
                                 "reason": "packet_profile differs from pinned candidate; not exported"})
        elif any(src not in reference_graph or dst not in reference_graph[src]
                 for src, dst in zip(item["path"], item["path"][1:])):
            incompatible.append({"transfer_id": item["id"],
                                 "reason": "path not expressible by original named candidate graph"})
        else:
            compatible.append(_upstream_transfer(item))
    exported = report = None
    if resource_input is None:
        incompatible.append({"transfer_id": None,
                             "reason": "no explicit llm-resource-input/1 model envelope supplied"})
    elif format_changed:
        incompatible.append({"transfer_id": None,
                             "reason": "changed packet format needs its own explicit #48 candidate contract"})
    else:
        exported = copy.deepcopy(resource_input)
        exported["transfers"] = compatible
        exported["hardware"]["candidate_file"] = "profiles/block_candidate_v1.json"
        try:
            report = upstream.compute(exported, original)
        except (upstream.InputError, ArithmeticError) as exc:
            raise ResourceError("resource subset export: " + str(exc)) from exc
    unresolved = [
        "edge and TX sums cover listed messages only; no concurrency or arbitration proof",
        "temporary S-prefixed cost nodes do not allocate hardware banks, ports or links",
        "logical event order is not a clock schedule; rates and capacity are unknown",
        "#48 transfer projection does not encode graph dependencies, state versions, aliases or lifetimes",
    ]
    if any(item["messages"] is None for item in records):
        unresolved.append("unknown message counts make affected edge/TX totals null; known lower bounds and per-message costs retained")
    return {
        "schema_version": "workload-resource-accounting/1",
        "scope": "packet and listed-message arithmetic; no hardware or full-model feasibility certificate",
        "transfers": per_transfer, "edges": edges, "shared_TX": shared,
        "all_listed_message_counts_known": all(item["messages"] is not None for item in records),
        "resource_input": exported, "resource_report": report,
        "incompatibilities": incompatible, "unresolved": unresolved,
        "provenance": {
            **provenance, "packet_profile": {key: candidate[key] for key in sorted(PACKET_KEYS)},
            "packet_profile_evidence": "assumed override" if format_changed else "declared upstream candidate",
            "export_candidate": "profiles/block_candidate_v1.json",
            "export_candidate_sha256": SOURCE_HASHES["profiles/block_candidate_v1.json"],
            "export_candidate_file_scope": "resolve using existing project/analysis/llm_resources root or explicit --candidate",
            "generic_projection": "injective endpoint renaming for arithmetic only; graph results discarded",
        },
    }
