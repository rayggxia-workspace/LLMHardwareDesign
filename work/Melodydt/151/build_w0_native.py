#!/usr/bin/env python3
"""W0 evidence/contract lock, Python3.7 stdlib; no RTL or online mutations.

Latest source snapshots are read-only audit inputs below localonly/ and must not
be uploaded. This tool does not import them into the selected integrated RTL.
"""
import argparse
import copy
import hashlib
import json
import re
from pathlib import Path

PARENT = "bd7cb2f3060c61e5d28a2ece0653dd9336a024af"
NATIVE = "707878621b2add4ed218b8c43df2e95c9a56e2ba"


def read(p):
    return json.loads(p.read_text(encoding="utf-8-sig"))


def write(p, x):
    p.write_bytes((json.dumps(x, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def blob(b):
    return hashlib.sha1(("blob " + str(len(b)) + "\0").encode("ascii") + b).hexdigest()


def ports(text, name):
    text = re.sub(r"/\*.*?\*/|//[^\n]*", lambda m: re.sub(r"[^\n]", " ", m.group()), text, flags=re.S)
    m = re.search(r"\bmodule\s+" + re.escape(name) + r"\s*\((.*?)\)\s*;", text, re.S)
    assert m, name
    result, previous, offset = [], None, m.start(1)
    for fragment in m.group(1).split(","):
        s = fragment.strip()
        d = re.match(r"^(input|output|inout)\s+(?:(wire|reg|logic)\s+)?(?:(signed)\s+)?(?:\[(\d+)\s*:\s*(\d+)\]\s+)?(\w+)$", s)
        if d:
            direction, kind, signed, high, low, port = d.groups()
            previous = {"direction": direction, "data_kind": kind or "implicit_wire", "signed": bool(signed),
                        "msb": int(high) if high else None, "lsb": int(low) if low else None,
                        "width": abs(int(high) - int(low)) + 1 if high else 1}
        else:
            assert previous is not None and re.match(r"^\w+$", s), s
            port = s
        row = dict(previous)
        row.update({"name": port, "declaration_line": text.count("\n", 0, offset + fragment.rfind(port)) + 1})
        result.append(row)
        offset += len(fragment) + 1
    assert len(result) == len(set(p["name"] for p in result))
    return result


def signature(p):
    return [(x["name"], x["direction"], x["width"], x["signed"], x["data_kind"]) for x in p]


def classifiers():
    return {
        "M": {"selector": "accepted cmd_op, plus success/error and op5width; response has no op echo",
              "by_op": {"3": "RESULT_2xS64", "4": "CONFIG_ACK_ZERO", "5": "RESULT_4xS32_CARRIER_LOGICAL_S8_S16_OR_S32",
                        "6": "CLEAR_ACK_ZERO", "10": "EXEC_STATUS_FAULT_ROWS_NOT_TENSOR", "11": "BANK_CLEAR_ACK_ZERO", "12": "PARTIAL_DIAGNOSTIC_2xS40_EXTENDED_S64"},
              "error": "rsp_error makes current response a failure, not usable tensor; descriptor rejection is distinct from completed EXEC row-fault mask",
              "extra_rule": "A/B handshakes produce input-valid state, not cmd/rsp ACKs; track separately"},
        "N": {"selector": "accepted cmd_op,mode,count and source-context; no op/role echo",
              "by_op": {"0": "BEGIN_ACK_ZERO", "1": "STATS_ACK_ZERO", "2": "FINALIZE_STATS_ACK_OR_FACTOR_ERROR", "3": "EXP_U16_CODES_NOT_PROBABILITY",
                        "4": "FINALIZE_EXP_ACK_OR_FACTOR_ERROR", "5": "NORM_S16_VECTOR", "6": "SOFTMAX_PROB_S16_Q14", "7": "MIXED_STATS_RECORD",
                        "8": "TOPK_BEGIN_ACK_ZERO", "9": "TOPK_LOAD_ACK_ZERO", "10": "TOPK_U16_IDS_NOT_SCORES", "11": "RAW_U32_FACTOR_CONTEXT_DEPENDENT"},
              "error": "rsp_error invalidates mathematical payload; factor not valid after arithmetic failure",
              "extra_rule": "N3 consumes original score; N6 consumes exact same-group EXP. Equal width/F is not provenance proof"},
        "E": {"selector": "accepted in_op; no count/mask or format echo",
              "by_op": {str(k): ("PACKED_8xS8_LOW64" if k == 12 else "CAST_4xS16_LOW64_HIGH64_ZERO" if k == 13 else "VECTOR_8xS16") for k in range(14)},
              "error": "op14/15 produces error/data0/saturated0; invalid payload must not be forwarded",
              "extra_rule": "external valid_count and pair/tail schema survive operation; padding is not logical data"},
        "G": {"selector": "accepted fn/gated in ordered pipeline; output has no fn/gated echo",
              "legal_fn": [0, 1, 2, 3], "by_fn_gated": {"fn1_gated0": "SIGMOID_ACTIVATION_2xS16_Q14_NOT_SOFTMAX_PROB", "fn1_gated1": "GATED_2xS16_Q10", "fn0_2_3_gated0_or1": "ACTIVATION_OR_GATED_2xS16_Q10"},
              "error": "fn4..7 returns ordered error/data0/saturated0",
              "extra_rule": "keep finite ordered format bookkeeping/static phase proof across all pipeline stalls; two physical lanes, no nativecount"},
        "R": {"selector": "accepted cmd_op and current owner/epoch/position/validity, no op echo",
              "by_op": {str(k): ("ACTIVE_STATE_4xS32" if k == 11 else "CANDIDATE_OUTPUT_4xS32_BEFORE_COMMIT" if k == 12 else "MIXED_META_NOT_CONTEXT_VALID_PROOF" if k == 13 else "ACTIVE_HISTORY_4xS32" if k == 14 else "CONTROL_OR_EXEC_OR_COMMIT_ACK_ZERO") for k in range(16)},
              "error": "rsp_error invalidates current output; no saturated pin; local state/history may be separately pending",
              "extra_rule": "EXEC6 completion is not outputpayload; op12 reads it. COMMIT7 ACK follows publication and is not reversible byop8"},
        "S": {"selector": "track accepted ordinary wr separately from loader/done/A/B streams",
              "ordinary_read": "RAW_WORD128_NO_TYPE_OR_INITIALIZATION_PROOF", "ordinary_write": "WRITE_ACK_ECHO_DIN_MUST_TAKE",
              "loader_done": "DELIVERY_DRAINED_OR_DESCRIPTOR_ERROR_NOT_M_EXEC_DONE", "loader_A_B": "READY_VALID_OPERAND_STREAMS_NOT_ORDINARY_RSP",
              "error": "ordinary has no error pin; done_error belongs only to loader",
              "extra_rule": "busy is feederbusy only; neither ordinaryvalid nor donevalid is implied empty"},
        "T": {"selector": "native phase-specific handshake/state, not a generic response opcode",
              "events": {"BEGIN": "LEASE_METADATA_ACCEPTED", "WRITE": "PROVISIONAL_WORD_ACCEPTED_NO_INDIVIDUAL_ACK", "SEALED": "ALL_WORDS_WRITTEN_NOT_COMMITTED",
                         "COMMIT": "PUBLISH_READ_SEQUENCE_NO_COMMIT_ERROR_PIN", "READ": "OPAQUE_WORD128_WITH_INDEX_LAST", "FINAL_TAKE": "ENTER_RELEASE_NOT_FREE", "RELEASE": "RESOURCE_EMPTY"},
              "error": "protocol_error sticky is not a per-command rsp; only selected native protocol violations are checked",
              "extra_rule": "owner2/gen32 metadata is not authentication; single consumer; committed read cannot be revoked"}}


def build(root, out, observation=None, latest_source_dir=None):
    out.mkdir(parents=True, exist_ok=True)
    old = read(root / "work/Melodydt/151/phase1-native-contract.json")
    selected = read(root / "work/Melodydt/151/phase2-source-lock.json")
    observation = observation or (out / "w0-latest-get.json")
    latest_source_dir = latest_source_dir or (out / "localonly/latest")
    latest = read(observation)
    assert selected["selected_PR144_ref"] == NATIVE and len(selected["core_files"]) == 14
    upstream = {x["path"]: x for x in latest["files"]}
    core = []
    for row in selected["core_files"]:
        path = row["path"]
        a = (root / path).read_bytes()
        b = (latest_source_dir / path).read_bytes()
        u = upstream[path]
        assert sha(root / path) == row["sha256"] and blob(a) == row["sha"]
        assert blob(b) == u["git_blob_sha"]
        core.append({"path": path, "selected_ref": NATIVE, "selected_git_blob_sha": blob(a),
                     "selected_sha256": hashlib.sha256(a).hexdigest(), "selected_bytes": len(a),
                     "latest_observed_ref": latest["head_sha"], "latest_git_blob_sha": blob(b),
                     "latest_sha256": hashlib.sha256(b).hexdigest(), "latest_bytes": len(b),
                     "git_blob_equal": blob(a) == blob(b), "raw_bytes_equal": a == b,
                     "selected_url": "https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/" + NATIVE + "/" + path,
                     "latest_url": u["url"]})
    receipt_path = "work/Melodydt/151/phase2-rtl-evidence/run-receipt.json"
    receipt = read(root / receipt_path)
    p2paths = ["project/rtl/block_connection_p2/block_p2_mst_top.sv", "project/rtl/block_connection_p2/block_p2_mother_rom.sv",
               "project/rtl/block_connection_p2/block_p2_s_ctrl.sv", "project/tb/block_connection_p2/phase2_mst_tb.sv",
               "project/tb/block_connection_p2/phase2_s_ctrl_tb.sv"]
    p2 = []
    for path in p2paths:
        b = (root / path).read_bytes()
        recorded = [v for v in receipt["inputs"] if v.get("name") == Path(path).name]
        assert len(recorded) == 1 and recorded[0]["sha256"] == hashlib.sha256(b).hexdigest()
        p2.append({"path": path, "bytes": len(b), "git_blob_sha": blob(b), "sha256": hashlib.sha256(b).hexdigest(),
                   "matches_actual_run_input": True, "source_url": "https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/" + PARENT + "/" + path})
    lock = {"schema_version": 1, "issue": 151, "research_parent": PARENT, "selected_native_ref": NATIVE,
            "latest_PR144_observation": latest,
            "core_files": core, "comparison": {"scope": "fourteen core RTL/include only", "files": 14,
            "git_blob_equal": sum(int(x["git_blob_equal"]) for x in core), "raw_bytes_equal": sum(int(x["raw_bytes_equal"]) for x in core),
            "changed_paths": [x["path"] for x in core if not x["raw_bytes_equal"]],
            "full_latest_branch_imported_or_merged": False, "selected_native_upgraded": False},
            "P2_implementation": {"native_source_ref": NATIVE, "execution_worktree": "three newRTL andtwoTB uncommitted during actual run; receipt SHA is authoritative",
            "actual_run_receipt": {"path": receipt_path, "sha256": sha(root / receipt_path)},
            "implementation_delivery_ref": "1cc43a93", "current_research_ref": PARENT, "P2_actual_source_hashes": p2,
            "retained_case_count": len(receipt["case_ids"]), "new_execution_in_W0": False},
            "boundaries": {"physical_qualification_reaudited": False, "common_base_frozen": False,
            "historical_P1_receipts_rewritten": False, "other_upstream_files_compared": False,
            "latest_head_tracking": "one observed frozen head; later upstream updates require a new comparison"},
            "upload_exclusions": ["localonly/**"]}
    macros = copy.deepcopy(old["macros"])
    header_checks = []
    for m, item in macros.items():
        p = root / item["path"]
        parsed = ports(p.read_text(encoding="utf-8"), item["module"])
        assert signature(parsed) == signature(item["ports"]), m
        owners = {x["name"]: x["unique_driving_owner_contract"] for x in item["ports"]}
        for port in parsed:
            port["unique_driving_owner_contract"] = owners[port["name"]]
        item["ports"] = parsed
        item["sha256"] = sha(p)
        item["response_classifier"] = classifiers()[m]
        header_checks.append({"macro": m, "path": item["path"], "ports": len(parsed), "signature_equal_retained_P1": True})
    macros["R"]["arithmetic_temporaries"] = {"rne_input_and_result_bits": 128, "fits32_input_bits": 128, "value_bits": 128,
        "selected_source_fact": True, "numerical_equivalence_to_old643_or_physical_qualification_proven_here": False}
    rpath = macros["R"]["path"]
    rlines = (root / rpath).read_text(encoding="utf-8").splitlines()
    def rline(needle):
        hit = [i for i, s in enumerate(rlines, 1) if needle in s]
        assert len(hit) == 1, needle
        return hit[0]
    r_ranges = {"R_READY": (rline("assign cmd_ready="), rline("assign busy=")),
                "R_OPEN_LOAD": (rline("0:begin // OPEN"), rline("6:begin // EXEC") - 2),
                "R_EXEC_COMMIT": (rline("6:begin // EXEC"), rline("8:begin pending_state") - 2),
                "R_REVOKE": (rline("8:begin pending_state"), rline("8:begin pending_state")),
                "R_READ_LOAD": (rline("9:begin"), rline("default:rsp_error<=1;") - 1),
                "R_FINISH_COPY": (rline("FINISH:begin"), rline("x_valid<=0;output_valid<=0;phase<=IDLE;rsp_valid<=1;rsp_error<=0;rsp_data<=0;") + 1),
                "R_RESET": (rline("always @(posedge clk)begin"), rline("if(rsp_valid&&rsp_ready)rsp_valid<=0;"))}
    traces = copy.deepcopy(old["source_traces"])
    for name, trace in traces.items():
        if trace["path"] == rpath and name in r_ranges:
            trace["first_line"], trace["last_line"] = r_ranges[name]
        trace["source_commit"] = NATIVE
        trace["github"] = "https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/" + NATIVE + "/" + trace["path"] + "#L" + str(trace["first_line"])
        lines = (root / trace["path"]).read_text(encoding="utf-8").splitlines()
        assert 1 <= trace["first_line"] <= trace["last_line"] <= len(lines)
    anchors = copy.deepcopy(old["source_anchors"])
    for name, a in anchors.items():
        text = (root / a["path"]).read_text(encoding="utf-8")
        assert a["literal"] in text, name
        a["line"] = text[:text.index(a["literal"])].count("\n") + 1
        a["source_commit"] = NATIVE
    contract = {"schema_version": 1, "issue": 151, "research_parent": PARENT, "selected_native_ref": NATIVE,
        "status": "W0_NATIVE_CONTRACT_CANDIDATE_NOT_RTL_INTEGRATION_OR_BASE_FREEZE",
        "normative_source": "selected707 actual RTL; P1 semantic tables retained only where source guards/ports agree, traces reanchored",
        "source_lock_ref": "w0-source-lock.json", "source_lock_sha256": None,
        "scope": {"seven_native_endpoint_contracts": True, "all_product_programs_or_parameters_bound": False,
                  "latest_branch_merged": False, "new_RTL_implemented": False, "new_RTL_simulation": False,
                  "new_physical_qualification": False, "common_base_frozen": False,
                  "roles_compile_time_only": True, "universal_runtime_role_tags_required": False},
        "general_rules": old["general_rules"], "external_owners_status": old["external_owners_status"],
        "macros": macros, "source_traces": traces, "source_anchors": anchors, "header_checks": header_checks,
        "source_provenance": [{"path": v["path"], "sha256": v["selected_sha256"], "git_blob_sha": v["selected_git_blob_sha"], "bytes": v["selected_bytes"]} for v in core],
        "response_classification_rules": ["Use accepted operation/phase andnativevalid/error, never infer kind from zero/nonzerodata orbuswidth.",
            "Only payload-class successful responses may become tensors; configuration/statistics/factor/metadata/ID/diagnostic classes require declared interpretation.",
            "Same16bit Q14 range does not make G Sigmoid activation equal to N normalized probability, or EXP/IDs into numeric operands.",
            "Preserve the accepted operation/format/count/lifetime in externalowner bookkeeping; no generic per-packet role header is mandated.",
            "Nativeignoredfields remain ignored; stricter canonicalzero andownership policies are integration rules, not fabricated RTLguards."],
        "unresolved_or_external_obligations": ["Fixed family dimensions/parameter/Fin/Fout/error tolerance are not fully instantiated.",
            "Only declared integer rounding/formulas are native facts; entire-model quantization and numerical acceptance remain unproven.",
            "Single-context M/N/R lifetimes, S/T capacity, loader1024capture/T6144spool where needed, and realMEM/NUM are not supplied by this contract.",
            "LocalRcommit cannot be interrupted or rolled back; multitile/fulljob state version publication is external and unimplemented.",
            "No nativeCDC/independent-reset cancellation guarantee; clock/reset/owners/consumers must be coordinated or new adapters designed.",
            "No physical timing, noise, routing, power, PG or latest noncore evidence is requalified in W0."],
        "inherited_contract_input": {"path": "work/Melodydt/151/phase1-native-contract.json", "sha256": sha(root / "work/Melodydt/151/phase1-native-contract.json"), "historical_native_ref": old["leaf_source_commit"], "historical_receipt_not_rewritten": True},
        "summary": {"macros": 7, "ports": sum(len(v["ports"]) for v in macros.values()), "channels": sum(len(v["channels"]) for v in macros.values()),
                    "source_anchors": len(anchors), "source_trace_ranges": len(traces), "new_simulations": 0}}
    assert lock["comparison"]["raw_bytes_equal"] == 14 and lock["comparison"]["git_blob_equal"] == 14
    assert contract["summary"]["ports"] == 149 and contract["summary"]["channels"] == 24
    for m in ("M", "N", "R"):
        assert set(macros[m]["operations"]) == set(macros[m]["response_classifier"]["by_op"])
    assert set(macros["E"]["operations"]) == set(macros["E"]["response_classifier"]["by_op"])
    assert "commit_error" not in [v["name"] for v in macros["T"]["ports"]]
    write(out / "w0-source-lock.json", lock)
    contract["source_lock_sha256"] = sha(out / "w0-source-lock.json")
    write(out / "w0-native-contract.json", contract)
    checks = {"result": "PASS_STATIC_CONTRACT_AND_SOURCE_LOCK_ONLY", "core_files_equal": 14, "core_files_changed": 0,
              "P2_actual_run_input_files_match": 5, "header_checks": header_checks,
              "ports": 149, "channels": 24, "source_anchors": len(anchors), "source_trace_ranges": len(traces),
              "response_opcode_entries": {m: len(macros[m]["response_classifier"].get("by_op", {})) for m in ("M", "N", "E", "R")},
              "tool_sha256": sha(Path(__file__)), "outputs": {f: sha(out / f) for f in ("w0-source-lock.json", "w0-native-contract.json")},
              "no_RTL_simulation_or_physical_qualification": True, "upload_exclusions": ["localonly/**"]}
    write(out / "w0-native-checks.json", checks)
    print(json.dumps({"result": checks["result"], "core_equal": 14, "ports": 149, "channels": 24, "P2_hash_matches": 5}))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", required=True)
    p.add_argument("--output-dir", required=True)
    p.add_argument("--observation", help="Fixed-head GET metadata JSON; defaults to output-dir/w0-latest-get.json")
    p.add_argument("--latest-source-dir", help="Read-only tree containing exact bytes at the observation ref")
    a = p.parse_args()
    build(Path(a.root), Path(a.output_dir),
          Path(a.observation) if a.observation else None,
          Path(a.latest_source_dir) if a.latest_source_dir else None)


if __name__ == "__main__":
    main()
