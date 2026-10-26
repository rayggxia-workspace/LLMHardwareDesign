"""Convert the two pinned PR78 fixtures to explicit workload/typed contracts.

Arithmetic and state transitions call the original offline replay implementation.
Conversion never consumes independent expected numbers. This is a finite fixture
adapter, not an arbitrary LLM compiler, scheduler, hardware or physical proof.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys
import types

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
UPSTREAM = HERE.parent / "block_v2_offline"
COMMIT = "a5ff0c5af973ffeafa441712cd3f6e491da5a2fd"
SOURCE_SHA = "fb7caf8b8a040bfffe8e40a7c4a3488d650b45694f3828023f35ae98d9923db0"
MANIFEST_SHA = "21171877996027b6a450e427e0dc1d297e0345944b1b5392d25b9037120c7401"
FIXTURE_SHA = {
    "graph1_reduce_rq.input.json": "80caeff4a6ea9f07e6dfb96a5387957e84c6601354d1a6084d1b9e1d8fe42ece",
    "graph1_reduce_rq.expected.json": "4dfeb663288a99b09d2b3eb20beeff7d1b8a531e162b5d9d748aa744e50ef143",
    "graph2_state_commit.input.json": "e1146ffc6c09daa86a1c63f1c0a046d29e50dfb1abb36d24cde97070845bba24",
    "graph2_state_commit.expected.json": "e1ca5b640e661e7c11ce467727009daea4bbd6ef9f0c973f558b563411f5c10f",
}


class BridgeError(ValueError):
    pass


def _load_upstream():
    for path, digest in ((UPSTREAM / "replay.py", SOURCE_SHA),
                         (UPSTREAM / "fixtures/sha256.json", MANIFEST_SHA)):
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise BridgeError("pinned PR78 source SHA-256 mismatch: " + path.name)
    module = types.ModuleType("workload_mapping_pinned_v2_replay")
    module.__file__ = str(UPSTREAM / "replay.py")
    exec(compile((UPSTREAM / "replay.py").read_bytes(), module.__file__, "exec"), module.__dict__)
    return module


def _evidence(description):
    return {"kind": "synthetic", "source": description, "status": "derived"}


class _Builder:
    def __init__(self, config, scenario, upstream):
        self.config = config
        self.graph = {
            "schema_version": "workload-mapping/1", "id": "v2-" + config["graph_id"] + "-" + scenario,
            "evidence": _evidence("PR78@" + COMMIT + "; original replay arithmetic; synthetic fixture"),
            "scope": "Finite declared scenario; initial residency excludes setup traffic; no runtime cycles or hardware proof",
            "nodes": [], "calls": [], "tensors": [], "storages": [], "states": [],
            "events": [], "transfers": [], "resource_input": None,
        }
        self.blocks = {
            "schema_version": "workload-blocks/1", "id": self.graph["id"] + "-blocks",
            "evidence": _evidence("PR78 synthetic resource declarations; candidate functionality unverified"),
            "resources": [], "links": [],
        }
        self.s = {
            "schema_version": "workload-semantics/1",
            "source": {"commit": COMMIT, "kind": "synthetic", "files": [
                {"path": "project/analysis/block_v2_offline/replay.py", "sha256": SOURCE_SHA},
            ]},
            "tensor_formats": [], "reductions": [], "transactions": [],
            "memory_domains": [], "storage_domains": [], "dependencies": [],
        }
        self.tensors, self.resources, self.regions = {}, {}, {}
        self.node_ids, self.link_ids = set(), set()
        self.storage = upstream.storage(config["graph_id"])
        for rid, regions in self.storage["regions_bytes"].items():
            kind = "shared_bank" if rid == "S" else "private_ram"
            resource = {
                "id": rid, "kind": "storage" if rid == "S" else "compute",
                "capacity_bytes": config["resources"]["private_bytes"][rid],
                "capabilities": [], "ports": [],
            }
            self.resources[rid] = resource
            self.blocks["resources"].append(resource)
            self.s["memory_domains"].append({"resource": rid, "kind": kind,
                                            "capacity_bytes": resource["capacity_bytes"]})
            for region, size in regions.items():
                # Split the 12B input region into three known 4B slots. Transfer
                # offsets then remain zero at the corresponding 4B R input slot.
                slots = [("inputs_step" + str(i), 4) for i in (1, 2, 3)] if region == "inputs" else [(region, size)]
                for name, capacity in slots:
                    sid = "s_" + rid + "_" + name
                    self.regions[(rid, name)] = sid
                    self.graph["storages"].append({"id": sid, "resource": rid,
                        "size_bytes": capacity, "begin": "", "end": ""})
                    self.s["storage_domains"].append({"storage": sid, "kind": kind})

    def tensor(self, name, rid, region, shape, bits, *, unit=1, stage="VALUE", group=None,
               owner=None, epoch=None, version=None, offset=0, role="activation", initial=False,
               axes=None):
        tid = "t_" + name
        tensor = {
            "id": tid, "shape": list(shape), "axes": axes or ["lane"], "layout": "row_major",
            "logical_bits": bits, "storage_bits": bits, "metadata_bytes": 0,
            "storage": self.regions[(rid, region)], "offset_bytes": offset,
            "producer": None, "consumers": [], "role": role, "initial": initial, "alias_of": None,
        }
        self.graph["tensors"].append(tensor)
        self.tensors[tid] = tensor
        self.s["tensor_formats"].append({
            "tensor": tid, "unit": unit, "signedness": "signed", "stage": stage,
            "group": group, "owner": owner, "epoch": epoch, "version": version,
        })
        return tid

    def call(self, name, semantic, rid, reads, writes):
        nid, cid = "n_" + name, "c_" + name
        self.graph["nodes"].append({"id": nid, "semantic": semantic,
                                    "contract": "block-v2-offline/1@" + self.config["source_commit"]})
        if not any(c["semantic"] == semantic for c in self.resources[rid]["capabilities"]):
            self.resources[rid]["capabilities"].append({"semantic": semantic, "status": "declared",
                "source": "Synthetic contract; original Python oracle, no implemented Block qualification"})
        self.graph["calls"].append({"id": cid, "node": nid, "resource": rid,
                                    "reads": list(reads), "writes": list(writes)})
        for tid in reads:
            self.tensors[tid]["consumers"].append(cid)
        for tid in writes:
            self.tensors[tid]["producer"] = cid
        return cid, self.event("call", cid)

    def event(self, kind, ref):
        eid = "e_" + ref
        self.graph["events"].append({"id": eid, "kind": kind, "ref": ref,
                                     "step": len(self.graph["events"]), "phase": "iteration"})
        return eid

    def depend(self, before, after, reason):
        self.s["dependencies"].append({"before": before, "after": after, "reason": reason})

    def transfer(self, name, tid, source, destination, destination_region):
        lid = "l_" + source + "_" + destination
        if lid not in self.link_ids:
            self.link_ids.add(lid)
            for rid, direction in ((source, "output"), (destination, "input")):
                pid = rid + ("_out" if direction == "output" else "_in")
                if not any(port["id"] == pid for port in self.resources[rid]["ports"]):
                    self.resources[rid]["ports"].append({"id": pid, "direction": direction,
                        "protocol": "ready_valid", "width_bits": self.config["link"]["bits"],
                        "fifo_bytes": self.config["resources"]["endpoint_fifo_bytes"]})
            self.blocks["links"].append({"id": lid, "source": source, "source_port": source + "_out",
                "destination": destination, "destination_port": destination + "_in", "protocol": "ready_valid"})
        trid = "tr_" + name
        self.graph["transfers"].append({"id": trid, "tensor": tid,
            "source_storage": self.tensors[tid]["storage"],
            "destination_storage": self.regions[(destination, destination_region)],
            "path": [lid], "messages": 1})
        return self.event("transfer", trid)

    def finish(self):
        first, last = self.graph["events"][0]["id"], self.graph["events"][-1]["id"]
        for storage in self.graph["storages"]:
            storage["begin"], storage["end"] = first, last
        for rid, resource in self.resources.items():
            self.s["memory_domains"].append({"resource": rid, "kind": "fifo",
                "capacity_bytes": sum(port["fifo_bytes"] for port in resource["ports"])})
        return self.graph, self.blocks, self.s


def _graph1(config, scenario, upstream):
    if scenario != "normal":
        raise BridgeError("graph1 supports only normal")
    upstream.graph1(config)  # Original complete-reduction/RNE arithmetic, no expected file.
    b = _Builder(config, scenario, upstream)
    x = b.tensor("x", "M", "x", [4], 8, initial=True, axes=["K"])
    weight = b.tensor("W", "M", "W", [2, 4], 8, role="weight", initial=True,
                      axes=["output_channel", "K"])
    residual = b.tensor("residual", "V", "residual", [2], 8, unit=2, initial=True)
    partials, sends, previous_send = [], [], None
    for group in sorted(config["data"]["groups"], key=lambda value: value["id"]):
        gid = group["id"]
        partial = b.tensor("partial_" + str(gid), "M", "partials", group["shape"], 32,
                           unit=group["unit"], stage="PARTIAL", group=gid, offset=gid * 8)
        _, produced = b.call("m_k" + str(gid), "PARTIAL32", "M", [x, weight], [partial])
        if previous_send is not None:
            b.depend(previous_send, produced, "send_complete")
        sent = b.transfer("partial_" + str(gid), partial, "M", "V", "partials")
        b.depend(produced, sent, "consume")
        partials.append(partial)
        sends.append(sent)
        previous_send = sent
    complete = b.tensor("complete", "V", "complete", [2], 32, stage="COMPLETE")
    reduce_call, reduced = b.call("v_reduce", "COMPLETE32", "V", partials, [complete])
    for sent in sends:
        b.depend(sent, reduced, "send_complete")
    rq = b.tensor("rq", "V", "rq", [2], 8, unit=2)
    rq_call, rqd = b.call("v_rq", "RNE_SAT8", "V", [complete], [rq])
    b.depend(reduced, rqd, "consume")
    output = b.tensor("output", "V", "output", [2], 16, unit=2)
    _, added = b.call("v_add", "RESIDUAL16", "V", [rq, residual], [output])
    b.depend(rqd, added, "consume")
    b.s["reductions"].append({"call": reduce_call, "partials": partials,
        "expected_groups": list(config["protocol"]["reduce_order"]), "complete": complete,
        "rq_call": rq_call, "rq_output": rq, "target_unit": 2})
    b.graph["resource_input"] = _graph1_resource_envelope()
    b.graph["scope"] += "; #48 export covers one synthetic 4x2 matrix and named transfer subset, not v2 typed protocol or private capacity identity"
    return b.finish()


def _graph1_resource_envelope():
    """Explicit eight-weight fixture envelope, not a model or packet-API dummy."""
    return {
        "schema_version": "llm-resource-input/1",
        "model": {
            "name": "synthetic-v2-graph1-one-4x2-matrix", "kind": "dense",
            "total_parameters": 8, "int8_parameters": 8, "auxiliary_parameters": [],
            "linear_ops": [{"name": "one-matrix-two-K-groups", "instances": 1,
                            "active_instances": 1, "input_features": 4, "output_features": 2,
                            "prefill_rows": "all"}],
            "linear_macs_per_token": None, "linear_outputs_per_token": None,
            "attention": [], "recurrent_states": [], "max_context_tokens": None,
            "source": {"kind": "hypothetical",
                       "uri": "https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/" + COMMIT
                              + "/project/analysis/block_v2_offline/fixtures/graph1_reduce_rq.input.json",
                       "revision": COMMIT,
                       "note": "Synthetic eight-weight matrix used once across two K groups. #48 carries only the named transfer subset; v2 typed units/reduction and tiny private capacities are not fully compatible with the fixed #41 profile."},
        },
        "precision": {"weight_bits": 8, "activation_bits": 8, "accumulator_bits": 32,
                      "kv_bits": 8, "quantization_contract": None},
        "scenario": {"phase": "prefill", "batch": 1, "input_tokens": 1, "output_tokens": 0,
                     "cached_tokens": 0, "target_tokens_per_second": None},
        "hardware": {"candidate_file": "profiles/block_candidate_v1.json", "matrix_counts": [1],
                     "clock_hz": None, "matrix_utilization": None,
                     "rq_initiation_interval_cycles": None, "external_capacity_bytes": None,
                     "external_effective_bytes_per_second": None,
                     "link_effective_fraction": None, "shared_reserve_bytes": 0},
        "placement": {"weights": "unknown", "kv": "unknown", "recurrent": "unknown"},
        "accounting": {"weight_scale": None, "kv_scale": None, "weight_padding_bytes": None,
                       "shared_workspace_bytes": None, "external_workspace_bytes": None,
                       "weight_read_passes": None, "kv_read_multiplier": None,
                       "recurrent_read_write_passes": None},
        "mapping": {"matrix_tile": {"rows": 1, "columns": 2, "reduction": 4,
                                   "operand_copies": 1, "accumulator_copies": 1, "reserved_bytes": 0}},
        "transfers": [],
    }


def _graph2(config, scenario, upstream):
    if scenario not in ("normal", "failure_retry"):
        raise BridgeError("graph2 supports normal or failure_retry")
    b = _Builder(config, scenario, upstream)
    b.graph["scope"] += "; ACT16 state units, private trials and atomic commit need the typed sidecar; no compatible #48 full-workload model envelope supplied"
    protocol = config["protocol"]
    owner, unit, epoch = protocol["owner"], protocol["unit"], protocol["epoch"]
    previous = b.tensor("state_v0", "R", "old", [2], 16, unit=unit, stage="COMMITTED",
                        owner=owner, epoch=epoch, version=0, role="state", initial=True)
    b.tensor("snapshot_v0", "S", "committed_snapshot", [2], 16, unit=unit,
             stage="SNAPSHOT", owner="S", epoch=epoch, version=0, initial=True)
    initial = previous
    inputs = {req["step"]: b.tensor("u" + str(req["step"]), "S", "inputs_step" + str(req["step"]),
                                   [2], 16, unit=req["unit"], owner="S", initial=True)
              for req in config["data"]["steps"]}
    machine = upstream.StateMachine(config)
    versions, prior_end = [], None
    bank_events = []
    for request in config["data"]["steps"]:
        attempts = [True, False] if scenario == "failure_retry" and request["step"] == 2 else [False]
        for attempt, fail in enumerate(attempts, 1):
            before_version = machine.version
            before_state, before_snapshot = list(machine.state), list(machine.snapshot)
            try:
                machine.step(request, fail_before_commit=fail)
            except upstream.TrialAborted:
                if not fail:
                    raise
                upstream.exact(machine.state, before_state, "abort keeps public state")
                upstream.exact(machine.snapshot, before_snapshot, "abort keeps snapshot")
                upstream.exact(machine.version, before_version, "abort keeps public version")
                outcome = "abort"
            else:
                if fail:
                    raise BridgeError("expected injected precommit abort did not occur")
                outcome = "commit"
            label = "step" + str(request["step"]) + "_attempt" + str(attempt)
            input_tensor = inputs[request["step"]]
            _, read_event = b.call(label + "_read", "READ_INPUT", "S", [input_tensor], [])
            if prior_end is not None:
                b.depend(prior_end, read_event, "release")
            sent = b.transfer(label + "_input", input_tensor, "S", "R", "input")
            bank_events.append({"event": sent, "storage": b.tensors[input_tensor]["storage"],
                                "op": "read", "step": request["step"]})
            b.depend(read_event, sent, "consume")
            proposal = b.tensor(label + "_proposal", "R", "proposal", [2], 32, unit=unit,
                stage="PROPOSAL", owner=owner, epoch=epoch, version=before_version + 1)
            pc, pe = b.call(label + "_proposal", "ADD32", "R", [previous, input_tensor], [proposal])
            b.depend(sent, pe, "send_complete")
            if prior_end is not None:
                b.depend(prior_end, pe, "state")
            gc, ge = b.call(label + "_guard", "EXACT_INT16_GUARD", "R", [proposal], [])
            b.depend(pe, ge, "guard")
            shadow = b.tensor(label + "_shadow", "R", "shadow", [2], 16, unit=unit,
                stage="SHADOW", owner=owner, epoch=epoch, version=before_version + 1)
            sc, se = b.call(label + "_shadow", "PRIVATE_SHADOW16", "R", [proposal], [shadow])
            b.depend(ge, se, "guard")
            published = None
            if outcome == "commit":
                published = b.tensor("state_v" + str(machine.version), "R", "old", [2], 16,
                    unit=unit, stage="COMMITTED", owner=owner, epoch=epoch, version=machine.version,
                    role="state")
                tc, te = b.call(label + "_commit", "ATOMIC_COMMIT", "R", [previous, shadow], [published])
                b.depend(se, te, "commit")
                versions.append({"tensor": published, "writer": tc, "previous": previous})
            else:
                tc, te = b.call(label + "_abort", "ABORT_PRIVATE_TRIAL", "R", [previous, shadow], [])
                b.depend(se, te, "release")
            b.s["transactions"].append({
                "id": "trial_" + label, "state": "state_recurrent", "owner": owner, "unit": unit,
                "epoch": epoch, "expected_version": before_version, "version": machine.version,
                "previous": previous, "proposal": proposal, "shadow": shadow, "published": published,
                "proposal_call": pc, "guard_call": gc, "shadow_call": sc, "terminal_call": tc,
                "outcome": outcome, "attempt": attempt, "step": request["step"],
                "guard": "all_lanes_exact", "guard_pass": True, "private": True,
            })
            prior_end = te
            if outcome == "commit":
                sent_state = b.transfer(label + "_published", published, "R", "S", "rx_staging")
                b.depend(te, sent_state, "commit")
                snapshot = b.tensor("snapshot_v" + str(machine.version), "S", "committed_snapshot",
                    [2], 16, unit=unit, stage="SNAPSHOT", owner="S", epoch=epoch, version=machine.version)
                _, snapshot_event = b.call(label + "_snapshot", "READ_ONLY_SNAPSHOT", "S", [published], [snapshot])
                bank_events.append({"event": snapshot_event,
                                    "storage": b.regions[("S", "committed_snapshot")],
                                    "op": "write", "step": request["step"]})
                b.depend(sent_state, snapshot_event, "send_complete")
                prior_end, previous = snapshot_event, published
    b.graph["states"].append({"id": "state_recurrent", "kind": "recurrent",
                              "initial": initial, "versions": versions})
    # Bind the actual StateMachine access trace to graph events. The upstream
    # slot is a serial access index, never a cycle or a generated timing budget.
    upstream.exact(len(bank_events), len(machine.bank), "bank event coverage")
    bank_resource = protocol["snapshot_owner"]
    b.s["bank_ports"] = [{"resource": bank_resource, "protocol": protocol["s_port"],
                           "width_bits": config["link"]["bits"]}]
    b.s["bank_accesses"] = []
    for actual_access, event in zip(machine.bank, bank_events):
        expected_operation = "read_input" if event["op"] == "read" else "write_snapshot"
        upstream.exact(actual_access["op"], expected_operation, "bank operation/event binding")
        upstream.exact(actual_access["step"], event["step"], "bank step/event binding")
        b.s["bank_accesses"].append({"resource": bank_resource, "event": event["event"],
            "storage": event["storage"], "op": event["op"], "slot": actual_access["slot"]})
    return b.finish()


def convert(config, scenario="normal"):
    """Convert an accepted finite v2 contract; never read expected result numbers."""
    upstream = _load_upstream()
    graph_id = upstream.validate(config)
    return (_graph1 if graph_id == "graph1_reduce_rq" else _graph2)(copy.deepcopy(config), scenario, upstream)


def accept_fixed(input_path, expected_path, scenario="normal"):
    """Check pinned fixture SHA first, replay original arithmetic, compare oracle, convert."""
    upstream = _load_upstream()
    config = upstream.read_json(input_path)
    graph_id = upstream.validate(config)
    for path, kind in ((Path(input_path), "input"), (Path(expected_path), "expected")):
        name = graph_id + "." + kind + ".json"
        if hashlib.sha256(path.read_bytes()).hexdigest() != FIXTURE_SHA[name]:
            raise BridgeError("fixed fixture SHA-256 mismatch: " + kind)
        upstream.check_fixture_digest(path, graph_id, kind)
    actual = upstream.replay(config)
    upstream.compare(actual, upstream.read_json(expected_path))
    graph, blocks, semantics = convert(config, scenario)
    semantics["source"]["files"].extend([
        {"path": "project/analysis/block_v2_offline/fixtures/" + graph_id + "." + kind + ".json",
         "sha256": FIXTURE_SHA[graph_id + "." + kind + ".json"]}
        for kind in ("input", "expected")
    ])
    return graph, blocks, semantics, actual


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--expected", type=Path, required=True)
    parser.add_argument("--scenario", choices=("normal", "failure_retry"), default="normal")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        graph, blocks, semantics, actual = accept_fixed(args.input, args.expected, args.scenario)
        from .core import build
        from .semantics import apply_semantics
        result = build(graph, blocks)
        apply_semantics(result, graph, blocks, semantics)
        from .cli import new_output
        from .consumer import verify_mapping
        verify_mapping(result["mapping_request"])
        output = new_output(REPO, args.output_dir)
        values = {"graph.json": graph, "blocks.json": blocks, "semantics.json": semantics,
                  "original_actual.json": actual, "mapping_request.json": result["mapping_request"],
                  "summary.json": result["summary"]}
        if result["resource_input"] is not None:
            values["resource_input.json"] = result["resource_input"]
            values["resource_report.json"] = result["resource_report"]
        for name, value in values.items():
            with (output / name).open("x", encoding="utf-8", newline="\n") as handle:
                json.dump(value, handle, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False)
                handle.write("\n")
        print(json.dumps({"status": "pass", "scope": "fixed fixture arithmetic, generic conversion and typed protocol",
                          "scenario": args.scenario, "graph": graph["id"], "output_dir": str(output)}))
        return 0
    except (ValueError, OSError, KeyError, TypeError, ArithmeticError) as exc:
        print("ERROR: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
