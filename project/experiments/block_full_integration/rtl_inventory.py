#!/usr/bin/env python3
"""Read-only original-design inventory; writes three NEW task deliverables only.

No HDL elaboration, simulator, EDA tool, scheduler, git mutation, or broad audit
is run. Instance frontiers are source-backed plans, not completed partitioning.
"""
import argparse
import csv
import datetime
import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess

EXPECTED_COMMITS = {
    "opentpu_small": "f237dab2f196855a59a083b1454786df8f01291f",
    "llaccel_core": "f7db8a22791a1ce9dc13e7c90b0b9b9386169aa5",
}
SHA = re.compile(r"^[0-9a-f]{64}$")


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def small_ref(path, maximum=16*1024*1024):
    path = Path(path)
    if not path.is_file():
        raise ValueError("Missing input: " + str(path))
    size = path.stat().st_size
    if size > maximum:
        raise ValueError("Refusing unexpectedly large inventory input: " + str(path))
    return {"path": str(path), "bytes": size, "sha256": digest(path),
            "verification": "actual_file_read_SHA256_this_inventory"}


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def uncomment(text):
    return re.sub(r"/\*[\s\S]*?\*/|//[^\n]*",
                  lambda m: "\n" * m.group(0).count("\n"), text)


def line_refs(path, needles):
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    rows = []
    for i, line in enumerate(lines):
        if any(needle in line for needle in needles):
            rows.append({"line": i + 1, "text": line.strip()})
    return {"file": small_ref(path), "lines": rows}


def module_template(path, module):
    """Lexical source template only; no resolution of generate/ifdef/parameters."""
    text = Path(path).read_text(encoding="utf-8")
    clean = uncomment(text)
    match = re.search(r"\bmodule\s+" + re.escape(module) + r"\b", clean)
    if not match:
        raise ValueError("Missing source module " + module + " in " + str(path))
    end = re.search(r"\bendmodule\b", clean[match.end():])
    if end is None:
        raise ValueError("Missing endmodule for " + module)
    finish = match.end() + end.end()
    body = clean[match.start():finish]
    first_line = clean[:match.start()].count("\n") + 1
    regions, arrays = [], []
    for offset, line in enumerate(body.splitlines()):
        if re.search(r"\balways_ff\b|\balways\s*@\s*\([^)]*(posedge|negedge)", line):
            regions.append({"line": first_line + offset, "text": line.strip()})
        if re.search(r"\b(logic|reg|wire)\b", line) and line.count("[") >= 2:
            arrays.append({"line": first_line + offset, "declaration": line.strip()})
    return {"module": module, "source": small_ref(path),
            "line_start": first_line, "line_end": first_line + body.count("\n"),
            "sequential_process_source_locations": regions,
            "multi_dimension_declaration_candidates": arrays,
            "array_candidates_are_not_proven_memories_or_storage_counts": True,
            "generate_and_ifdef_resolved": False,
            "elaborated_state_bit_count": None}


def find_instance(path, parent_module, child_module, instance):
    """Balanced parameter scan verifies one literal instance in the source template."""
    source = Path(path).read_text(encoding="utf-8")
    clean = uncomment(source)
    top = re.search(r"\bmodule\s+" + re.escape(parent_module) + r"\b", clean)
    if top is None:
        raise ValueError("Parent module missing")
    end = clean.find("endmodule", top.end())
    sub = clean[top.end():end]
    matches = []
    for hit in re.finditer(r"\b" + re.escape(child_module) + r"\b", sub):
        cursor = hit.end()
        while cursor < len(sub) and sub[cursor].isspace():
            cursor += 1
        if cursor < len(sub) and sub[cursor] == "#":
            cursor += 1
            while cursor < len(sub) and sub[cursor].isspace():
                cursor += 1
            if cursor >= len(sub) or sub[cursor] != "(":
                continue
            level = 1
            cursor += 1
            while cursor < len(sub) and level:
                level += (sub[cursor] == "(") - (sub[cursor] == ")")
                cursor += 1
        found = re.match(r"\s*" + re.escape(instance) + r"\s*\(", sub[cursor:])
        if found:
            absolute = top.end() + hit.start()
            matches.append({"line": clean[:absolute].count("\n") + 1,
                            "module": child_module, "instance": instance})
    if len(matches) != 1:
        raise ValueError("Expected one source instance %s/%s, got %d" % (parent_module, instance, len(matches)))
    return matches[0]


def receipt_with_log(path):
    path = Path(path)
    obj = read_json(path)
    return {"receipt": small_ref(path), "record": obj}


def log_ref(path, expected=None):
    path = Path(path)
    ref = small_ref(path)
    if expected is not None and ref["sha256"] != expected:
        raise ValueError("Historical log hash mismatch: " + str(path))
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    selected = [{"line": i + 1, "text": line[:280]} for i, line in enumerate(lines)
                if re.search(r"PASS|FAIL|mismatch|MATCH|checks|cases|cycles|error|Error|Verilator", line)]
    return {"file": ref, "evidence_excerpt": selected[-8:],
            "excerpt_is_not_an_independent_reexecution": True}


def source_filelist(op_root, ll_root):
    mk = op_root / "build/asic/small/config.mk"
    text = mk.read_text()
    line = next(x for x in text.splitlines() if x.startswith("export VERILOG_FILES ="))
    files = line.split("=", 1)[1].split()
    params_line = next(x for x in text.splitlines() if x.startswith("export VERILOG_TOP_PARAMS ="))
    words = params_line.split("=", 1)[1].split()
    if len(words) % 2:
        raise ValueError("Malformed openTPU parameter list")
    params = {words[i]: int(words[i+1]) for i in range(0, len(words), 2)}
    ll_f = ll_root / "rtl/filelist.f"
    ll_entries, incdirs = [], []
    for raw in ll_f.read_text().splitlines():
        value = raw.split("//", 1)[0].strip()
        if not value:
            continue
        if value.startswith("+incdir+"):
            incdirs.append(str(ll_root / value[8:]))
        elif value.startswith("+"):
            raise ValueError("Unsupported filelist option: " + value)
        else:
            ll_entries.append(small_ref(ll_root / value))
    return {
        "opentpu_small": {"configuration_source": small_ref(mk),
            "target_declaration": small_ref(op_root / "targets/nangate45-small.toml"),
            "ordered_source_files": [small_ref(Path(p)) for p in files],
            "parameters_explicit": params,
            "additional_actual_defaults": {"S_top_fixed": 1, "MXU_E": 0, "COLL_GATHER": 1,
                "SEQ_WC": 0, "QUANT_XD_slice_default": 1024, "DMA_DEPTH_default": 128},
            "sdc": line_refs(op_root / "build/asic/small/constraint.sdc",
                ["create_clock", "clk_period", "set_input_delay", "set_output_delay", "set_false_path"]),
            "clock_period_ns": 2.5, "external_hold_checks_excluded_in_original_SDC": True},
        "llaccel_core": {"configuration_source": small_ref(ll_root / "synth/orfs/config_v1.mk"),
            "elaboration_template": small_ref(ll_root / "synth/yosys/elab_core.ys"),
            "configuration_driver": line_refs(ll_root / "synth/run_yosys.sh", ["v1)", "dma_depth=", "sed "]),
            "filelist": small_ref(ll_f), "ordered_source_files": ll_entries, "include_dirs": incdirs,
            "parameters_explicit": {"EPILOGUE_FUSION": 0, "DMA_MAX_OUTSTANDING": 16},
            "real_VECTOR_and_ATTN_selected_not_filelist_core_stubs": True,
            "sdc": line_refs(ll_root / "synth/orfs/constraint.sdc",
                ["create_clock", "clk_period", "set_input_delay", "set_output_delay"]),
            "clock_period_ns": 3.0,
            "filelist_contains_llaccel_top_and_sram_bank_but_selected_synthesis_top_is_llaccel_core": True},
    }


def bind_original_baseline_sources(filelists, op_root, ll_root, pending):
    """Compare selected source SHA to the actual original baseline input manifests."""
    b = pending / "hardware-baseline-20261021-173305/baseline"
    manifests = {
        "opentpu_small": b / "opentpu/source_manifest.json",
        "llaccel_core": b / "llaccel/source-manifest.json",
    }
    roots = {"opentpu_small": op_root, "llaccel_core": ll_root}
    result = {}
    for case, manifest in manifests.items():
        record = read_json(manifest)
        old_rows = record["files"] if isinstance(record, dict) else record
        old = {x["path"]: x["sha256"] for x in old_rows}
        checked, excluded = [], []
        for now in filelists[case]["ordered_source_files"]:
            rel = str(Path(now["path"]).relative_to(roots[case]))
            if not rel.startswith("rtl/"):
                excluded.append({"path": now["path"], "reason":
                    "Generated ASIC mapping or abstract macro model; not a tracked original RTL baseline source."})
                continue
            if rel not in old or now["sha256"] != old[rel]:
                raise ValueError("Selected RTL differs from original baseline manifest: " + case + "/" + rel)
            checked.append({"relative_path": rel, "sha256": now["sha256"],
                            "matches_historical_original_input": True})
        if not checked:
            raise ValueError("No selected RTL bound to baseline")
        result[case] = {"manifest": small_ref(manifest), "checked": checked,
                        "generated_physical_inputs_separate": excluded,
                        "status": "PASS_SELECTED_ORIGINAL_RTL_SOURCE_IDENTITY",
                        "simulation_compatibility_patches_recorded_separately": True}
    return result


def build_frontier(op_root, ll_root, ledger, block_root):
    specs = [
        ("opentpu_small","op.ACT","u_slice.u_act","otpu_actram","rtl/mem/otpu_actram.sv","existing_reusable_block","ACT","rtl/top/otpu_slice.sv","otpu_slice"),
        ("opentpu_small","op.MXU","u_slice.u_mxu","otpu_mxu","rtl/mxu/otpu_mxu.sv","existing_reusable_block","MXU","rtl/top/otpu_slice.sv","otpu_slice"),
        ("opentpu_small","op.VPU","u_slice.u_vpu","otpu_vpu","rtl/vpu/otpu_vpu.sv","auxiliary_block_pending","open_VPU","rtl/top/otpu_slice.sv","otpu_slice"),
        ("opentpu_small","op.QUANT","u_slice.u_quant","otpu_quant","rtl/vpu/otpu_quant.sv","auxiliary_block_pending","open_QUANT","rtl/top/otpu_slice.sv","otpu_slice"),
        ("opentpu_small","op.TMEM","u_slice.u_tmem","otpu_tmem","rtl/mem/otpu_tmem.sv","auxiliary_block_pending","open_TMEM","rtl/top/otpu_slice.sv","otpu_slice"),
        ("opentpu_small","op.SEQ_IMEM","u_slice.u_seq","otpu_seq","rtl/seq/otpu_seq.sv","auxiliary_block_pending","open_SEQ_IMEM","rtl/top/otpu_slice.sv","otpu_slice"),
        ("opentpu_small","op.DMA","u_slice.u_dma","otpu_dma","rtl/dma/otpu_dma.sv","auxiliary_block_pending","open_DMA","rtl/top/otpu_slice.sv","otpu_slice"),
        ("opentpu_small","op.COLLECTIVE","g_coll.u_coll","otpu_coll","rtl/top/otpu_coll.sv","auxiliary_block_pending","open_COLLECTIVE","rtl/asic/otpu_asic_top.sv","otpu_asic_top"),
        ("llaccel_core","ll.GEMM","u_gemm","gemm_engine","rtl/gemm_engine.sv","existing_reusable_block","GEMM","rtl/llaccel_core.sv","llaccel_core"),
        ("llaccel_core","ll.VECTOR","u_vec","vec_engine","rtl/vec_engine.sv","existing_reusable_block","VECTOR","rtl/llaccel_core.sv","llaccel_core"),
        ("llaccel_core","ll.ATTN","u_attn","attn_engine","rtl/attn_engine.sv","auxiliary_block_pending","ll_ATTN","rtl/llaccel_core.sv","llaccel_core"),
        ("llaccel_core","ll.DMA","u_dma","dma_engine","rtl/dma_engine.sv","auxiliary_block_pending","ll_DMA","rtl/llaccel_core.sv","llaccel_core"),
        ("llaccel_core","ll.CMD","u_cp","cmd_proc","rtl/cmd_proc.sv","auxiliary_block_pending","ll_CMD","rtl/llaccel_core.sv","llaccel_core"),
        ("llaccel_core","ll.SRAM_XBAR","u_xbar","sram_xbar","rtl/sram_xbar.sv","auxiliary_block_pending","ll_SRAM_XBAR","rtl/llaccel_core.sv","llaccel_core"),
        ("llaccel_core","ll.DRAM_ARB","u_arb","dram_arb","rtl/dram_arb.sv","auxiliary_block_pending","ll_DRAM_ARB","rtl/llaccel_core.sv","llaccel_core"),
        ("llaccel_core","ll.PERF","u_perf","perf_counters","rtl/perf_counters.sv","auxiliary_block_pending","ll_PERF","rtl/llaccel_core.sv","llaccel_core"),
    ]
    prior = {row["id"]: row for row in ledger["rows"]}
    rows = []
    for design, item_id, instance, module, rel, ownership, owner, parent_rel, parent_module in specs:
        root = op_root if design == "opentpu_small" else ll_root
        literal_instance = instance.split(".")[-1]
        hit = find_instance(root / parent_rel, parent_module, module, literal_instance)
        row = {"id": item_id, "design": design, "entry_kind": "actual_instance_subtree",
            "selector": {"include_subtree": instance}, "owner": owner,
            "ownership_class": ownership, "module": module,
            "instance_evidence": {"file": small_ref(root / parent_rel), **hit},
            "template": module_template(root / rel, module),
            "state_and_memory_description": prior[item_id].get("state", []),
            "cycle_contract": prior[item_id].get("cycle", []),
            "historical_ledger_row": item_id, "clock_reset_contract": prior[item_id].get("clock_reset_contract"),
            "physical_boundary": "inside_target_core",
            "integration_proven": False, "ownership_is_proposed_frontier_not_completed_hard_macro": True}
        rows.append(row)
    op_children = [x["selector"]["include_subtree"] for x in rows if x["design"] == "opentpu_small" and x["selector"]["include_subtree"].startswith("u_slice.")]
    rows += [
        {"id":"op.SLICE_LOCAL","design":"opentpu_small","entry_kind":"module_local_logic",
         "selector":{"scope":"u_slice","exclude_subtrees":op_children},"owner":"open_SLICE_CONTROL_ARBITRATION",
         "ownership_class":"auxiliary_block_pending","module":"otpu_slice",
         "template":module_template(op_root/"rtl/top/otpu_slice.sv","otpu_slice"),
         "state_and_memory_description":[s for key in ["op.LOADER_CHAIN","op.ARBITER_BOUNDARY_STATUS"] for s in prior[key]["state"]],
         "additional_behavior":"RLD local pipeline, collective pending state, loader/CHAIN/error reset control, TMEM grants and registered external A/SW/B requests and B responses.",
         "integration_proven":False},
        {"id":"op.TOP_FIXED","design":"opentpu_small","entry_kind":"module_local_logic",
         "selector":{"scope":"otpu_asic_top","exclude_subtrees":["u_slice","g_coll.u_coll"]},
         "owner":"open_TOP_FIXED","ownership_class":"top_fixed_connection","module":"otpu_asic_top",
         "template":module_template(op_root/"rtl/asic/otpu_asic_top.sv","otpu_asic_top"),
         "state_and_memory_description":[],"additional_behavior":"rinit packed-to-unpacked wiring and error OR; selected COLL_GATHER=1. No free case-specific new active logic.",
         "integration_proven":False},
        {"id":"ll.TOP_FIXED","design":"llaccel_core","entry_kind":"module_local_logic",
         "selector":{"scope":"llaccel_core","exclude_subtrees":[x["selector"]["include_subtree"] for x in rows if x["design"]=="llaccel_core"]},
         "owner":"ll_TOP_FIXED","ownership_class":"top_fixed_connection","module":"llaccel_core",
         "template":module_template(ll_root/"rtl/llaccel_core.sv","llaccel_core"),
         "state_and_memory_description":[],"additional_behavior":"Engine interconnect and perf increment decode; all active helper logic must be represented in frozen union before custom routing.",
         "integration_proven":False},
        {"id":"op.EXTERNAL","design":"opentpu_small","entry_kind":"external_environment",
         "selector":{"external_ports":["rinit","ld_start","ld_addr","ld_n","a_rdy","b_rdy","sw_rdy","wr_idle","rd_idle","a_rvalid","a_rdata","b_rvalid","b_rtag","b_rdata"]},
         "owner":"open_HOST_DRAM_MODEL","ownership_class":"external_test_environment","module":None,
         "state_and_memory_description":["Behavioral DRAM and host/loader driver are outside otpu_asic_top physical area."],
         "integration_proven":False},
        {"id":"ll.EXTERNAL_SRAM_MODEL","design":"llaccel_core","entry_kind":"external_environment",
         "selector":{"external_testbench_subtree":"llaccel_top.g_bank[0:15].u_bank"},
         "owner":"ll_SRAM_DRAM_HOST_MODEL","ownership_class":"external_test_environment","module":"sram_bank",
         "template":module_template(ll_root/"rtl/sram_bank.sv","sram_bank"),
         "instance_evidence":line_refs(ll_root/"rtl/llaccel_top.sv",["u_core","g_bank","sram_bank u_bank"]),
         "state_and_memory_description":prior["ll.EXTERNAL_SRAM_MODEL"]["state"],
         "additional_behavior":"DRAM including K/V and host external; SRAM bank ports remain full 16-bank interface.",
         "integration_proven":False},
    ]
    for design in ["opentpu_small","llaccel_core"]:
        roots = [r["selector"]["include_subtree"] for r in rows if r["design"]==design and "include_subtree" in r["selector"]]
        if len(roots)!=len(set(roots)) or any(a.startswith(b+".") for a in roots for b in roots if a!=b):
            raise ValueError("Overlapping ownership frontiers")
    return rows


def compatibility(op_root,ll_root,block_root):
    wave = block_root/"issue-7/parallel-blocks-wave2-06"
    checks=[]
    for name, rels, source in [
        ("ACT",["rtl/mem/otpu_actram.sv","rtl/top/otpu_pkg.sv"],wave/"act-cap20/source"),
        ("MXU",["rtl/mxu/otpu_mxu.sv","rtl/top/otpu_pkg.sv","rtl/tech/generic/otpu_tech_dsp.sv"],wave/"mxu-cap20/source"),
        ("GEMM",["rtl/gemm_engine.sv","rtl/llaccel_pkg.sv"],wave/"gemm-cap20/source"),
        ("VECTOR",["rtl/llaccel_pkg.sv","rtl/llaccel_luts_pkg.sv","rtl/sync_fifo.sv","rtl/isqrt.sv","rtl/udiv.sv","rtl/vec_engine.sv","rtl/llaccel_luts_undef.sv"],block_root/"issue-7/vec-harden-01/source"),
    ]:
        orig=op_root if name in ("ACT","MXU") else ll_root
        pairs=[]
        for rel in rels:
            a,b=small_ref(orig/rel),small_ref(source/rel)
            pairs.append({"relative":rel,"original":a,"block_source":b,"byte_identical":a["sha256"]==b["sha256"]})
        if not all(x["byte_identical"] for x in pairs):
            raise ValueError("Block source version mismatch: "+name)
        checks.append({"block":name,"selected_source_pairs":pairs,
                       "scope":"Selected actual source dependencies; not whole RTL-to-routed-block equivalence",
                       "complete_core_replacement_verified":False})
    return {"checks":checks,
        "open_boundary_sources":[small_ref(wave/"act-cap20/boundary.sv"),small_ref(wave/"mxu-cap20/boundary.sv")],
        "open_compatible_parameters":{"D":32,"MCOLS":2,"ROWS":2,"BLOCKS":32,"LANES":4,"DEPTH":64,"IMPL":2,"CL":16,"E":0,"SID":0},
        "current_ACT_MXU_chain":[{"directory":str(block_root/("issue-15/"+name)),
            "experiment":small_ref(block_root/("issue-15/"+name+"/experiment.json")),
            "inputs":small_ref(block_root/("issue-15/"+name+"/input-sha256.json"))}
            for name in ["m9-act-03","m9-mxu-03"]],
        "alternative_merged_not_in_primary_ownership":str(block_root/"issue-15/m9-merged-03"),
        "old_report_wave2_is_not_latest_ACT_MXU_physical_qualification":True,
        "physical_migration_and_new_top_loads_not_checked_here":True}


def baseline_evidence(pending,evidence):
    base=pending/"hardware-baseline-20261021-173305"
    r02=pending/"common-fabric-r02-20261022-132950"
    coverage_path=r02/"functional/coverage_summary_v6.json"
    coverage=read_json(coverage_path)
    original_open_path=r02/"functional/open-public-controls-original-v2-20261022T104130Z/original_rtl_probe/status.json"
    original_open=read_json(original_open_path)
    if original_open["status"]!="PASS_ORIGINAL_RTL_PUBLIC_CONTROLS_8_CASES":
        raise ValueError("Original public-control regression receipt is not PASS")
    open_commands=[]
    for row in original_open["commands"]:
        open_commands.append({"label":row.get("label"),"command":row.get("command"),
            "returncode":row.get("returncode"),"seconds":row.get("seconds"),
            "log":log_ref(row["log"],row.get("log_sha256"))})
    open_cases=[]
    for row in original_open["tests"]:
        if not row["pass"]:
            raise ValueError("Original open case did not pass")
        open_cases.append({"case":row["case"],"command":row["command"],
            "metrics":row["metrics"],"expected_timeout":row["expected_timeout"],
            "accepted_write_requests":row["accepted_write_requests"],
            "actual_dram_path":row["actual_dram"],"recorded_actual_sha256":row["actual_sha256"],
            "recorded_expected_sha256":row["expected_sha256"],"bytes":row["bytes"],
            "large_output_not_rehashed_here":True,
            "log":log_ref(row["log"],row.get("log_sha256"))})
    ll_status_path=base/"baseline/llaccel/results/status.json"
    ll_records=read_json(ll_status_path)
    ll_rows=[]
    for row in ll_records:
        if row.get("kind")=="tool" or any(word in row.get("label","") for word in ["elab","run-","build-system"]):
            new={k:row.get(k) for k in ["label","kind","command","cwd","exit_code","elapsed_seconds","compilation_pass","simulation_completed","comparison_pass"]}
            new["log"]=log_ref(row["log"])
            ll_rows.append(new)
    attn_path=pending/"llaccel-attn-full-20261021-191056/results/summary.json"
    attn=read_json(attn_path)
    if attn["status"]!="PASS_FULL_SUITE" or attn["completed_cases_reported"]!=724 or attn["failures_reported"]!=0:
        raise ValueError("ATTN supplementary terminal is not the expected full suite")
    return {
        "schema":"full-block-baseline-evidence-v1","status":"HISTORICAL_BASELINE_REUSE_VERIFIED_NO_NEW_DUT_RUN",
        "original_open":{"initial":receipt_with_log(base/"baseline/opentpu/final_summary.json"),
            "assertion_receipt":small_ref(base/"baseline/opentpu/status_assertions.json"),
            "latest_public_controls_receipt":small_ref(original_open_path),
            "tool_versions":original_open["tool_versions"],"commands":open_commands,"cases":open_cases,
            "compatibility_patch":small_ref(base/"baseline/opentpu/simulation_hooks.patch"),
            "source_synthesis_identity":small_ref(base/"physical/audit_opentpu/preprocess_identity.json"),
            "seed_policy":"Directed programs + two periodic ready-stall patterns; not seeds 0/1/2 random complete-core tests."},
        "original_ll":{"receipt":small_ref(ll_status_path),"records":ll_rows,
            "compatibility":receipt_with_log(base/"baseline/llaccel/compatibility.json"),
            "seed":1,"selected_config":{"EPILOGUE_FUSION":0,"DMA_MAX_OUTSTANDING":16},
            "fusion1_and_arb_depth_sweeps_are_extra_not_selected_config":True},
        "attention_unit_completion":{"summary":small_ref(attn_path),"actual_result":attn,
            "log":log_ref(pending/"llaccel-attn-full-20261021-191056/logs/attn-full.log",attn["log_sha256"]),
            "supersedes_prior_300s_timeout_as_the_later_full_unit_result":True,
            "complete_core_or_shared_724_cases":False},
        "later_complete_core_finite_regression":{"coverage_receipt":small_ref(coverage_path),
            "registered_input_index":small_ref(r02/"functional/unified_regression19_observable_metadata.json"),
            "counts":coverage["counts"],"families":coverage["test_families"],
            "remaining_limits":coverage["ordinary_domain_and_environment_limits"],
            "reference_and_previous_shared_results_not_transferred_to_new_blocks":True},
        "new_task_gaps":[
            "New ACT/MXU/GEMM/VECTOR + auxiliary Block integration has not been built or compared.",
            "Record and run random seeds 0,1,2 on the new full configured cores; old seed1 and directed stall cases are not this evidence.",
            "Compare public valid/address/data/byte-enable/status transaction traces and specified cycle timing, not final memory alone.",
            "Midflight reset/error recovery and deadline-response races remain limited; add applicable bounded cases.",
            "Requalify every actually used new gate master and SRAM behavior model; no unknown-model stub or zero-output fallback.",
            "No end-to-end original RTL to routed Block/full-core formal equivalence has been completed.",
        ],
        "minimal_replay_policy":{
            "do_not_replay_original_commands_in_old_output_directories":True,
            "new_runs_required_for_new_integrated_DUT":True,
            "ll_original_seed_template":["<source-bound-existing-Vllaccel_top>","+seed=<0|1|2>"],
            "open_template":"Reuse frozen program/expected DRAM inputs and public-controls TB; new TB trace checker must observe actual ports. New random scheduling stimulus needs a recorded seed interface.",
            "existing_passed_original_seed1_and_directed_cases_need_not_be_rebuilt_only_for_inventory":True},
        "operations_this_inventory":{"DUT_build":False,"DUT_run":False,"EDA":False,"Slurm_submit":False}
    }


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-root",type=Path,required=True)
    parser.add_argument("--opentpu-root",type=Path,required=True)
    parser.add_argument("--llaccel-root",type=Path,required=True)
    parser.add_argument("--history-pending",type=Path,required=True)
    parser.add_argument("--block-root",type=Path,required=True)
    args=parser.parse_args()
    allowed=Path("/public/home/yuzelu/PingyangHuang").resolve()
    root=args.task_root.resolve(strict=True)
    if root==allowed or allowed not in root.parents:
        raise ValueError("Task root must be a new task below PingyangHuang")
    destinations=[root/"inputs/rtl_inventory.json",root/"deliverables/coverage_map.csv",root/"inputs/baseline_evidence.json"]
    for p in destinations:
        if p.exists() or p.is_symlink():
            raise FileExistsError("Never overwrite inventory output: "+str(p))
        parent=p.parent.resolve(strict=True)
        if root not in parent.parents:
            raise ValueError("Output escapes new task root")
    pending=args.history_pending.resolve(strict=True)
    case_path=pending/"block-flow-generalization-20261022T143123188048Z/inputs/case_evidence.json"
    ledger_path=pending/"common-fabric-r02-20261022-132950/functional/full_core_function_mapping_ledger.json"
    evidence,ledger=read_json(case_path),read_json(ledger_path)
    versions={}
    for case,path in [("opentpu_small",args.opentpu_root),("llaccel_core",args.llaccel_root)]:
        env=dict(os.environ,GIT_OPTIONAL_LOCKS="0")
        sha=subprocess.check_output(["git","-C",str(path),"rev-parse","HEAD"],env=env,universal_newlines=True).strip()
        if sha!=EXPECTED_COMMITS[case]:
            raise ValueError("Original source commit changed: "+case+" "+sha)
        versions[case]={"root":str(path.resolve()),"commit":sha,"HEAD_read_only":True,
                       "whole_repository_clean_state_not_claimed":True}
    filelists=source_filelist(args.opentpu_root,args.llaccel_root)
    baseline_source_binding=bind_original_baseline_sources(filelists,args.opentpu_root,args.llaccel_root,pending)
    rows=build_frontier(args.opentpu_root,args.llaccel_root,ledger,args.block_root)
    compat=compatibility(args.opentpu_root,args.llaccel_root,args.block_root)
    baseline=baseline_evidence(pending,evidence)
    inventory={
        "schema":"full-block-rtl-inventory-v1","status":"SOURCE_BACKED_OWNERSHIP_FRONTIER_PENDING_NEW_ELABORATION",
        "created_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),"task_root":str(root),
        "generator":small_ref(Path(__file__).resolve()),"source_versions":versions,"build_inputs":filelists,
        "selected_original_RTL_baseline_binding":baseline_source_binding,
        "historical_case_evidence":small_ref(case_path),"historical_resource_ledger":small_ref(ledger_path),
        "targets":{k:{"top":v["original_top"],"configuration":v["configuration"],
                         "historical_public_ports":v["top_ports"],"memory_boundary":v["memory_boundary"],
                         "ports_are_historical_frontend_evidence_not_new_elaboration":True}
                   for k,v in evidence["cases"].items()},
        "ownership_frontier":rows,"core_block_compatibility":compat,
        "non_additive_categories":{
            "op.FP_HELPERS":"Owned recursively by VPU/QUANT/MXU and any actual callers; not a new duplicate standalone Block.",
            "op.ASIC_RAM_LEAVES":"Owned by concrete enclosing memory/FIFO/SEQ/engine instance; original archived 33 macros are not 33 extra Blocks.",
            "ll.SEQUENTIAL_HELPERS":"isqrt/udiv/FIFO/LUT instances belong to their actual parent engine/control subtree.",
            "ACT_plus_MXU_merged":"Alternative to ACT+MXU split, never added alongside them in the same primary coverage frontier."},
        "frontier_checks":{"duplicate_owner_rows":False,"subtree_frontier_overlaps":False,
            "source_instance_locations_checked":True,"module_local_residual_explicit":True,
            "selected_generate_branch_COLLECTIVE":"COLL_GATHER=1 -> g_coll.u_coll",
            "source_template_conditionals_are_not_elaborated_active_inventory":True,
            "complete_elaborated_leaf_cell_state_memory_bijection":"NOT_EXECUTED"},
        "stage2_required_inputs":[
            "Official elaborated selected top hierarchy with parameter/ifdef resolution and per-state/memory instance ownership.",
            "Complete interface split: preserve original registered A/SW/B timing, TMEM grants, reset/CHAIN/timeout paths and every engine instruction/done protocol.",
            "Auxiliary Block implementation views matching the selected original subtrees and timing; no omission of residual slice/core logic.",
            "Original-to-integrated port/state mapping and complete-core tests with public transaction/cycle observers.",
            "Qualified inactive union-resource input/reset/clock policy and fixed host-interface superset; no free clock gate or mux.",
            "Actual M1-M8 migration and M8 access qualification belongs to later physical stages and is not established by this inventory."],
        "operations":{"read_only_sources":True,"new_HDL_elaboration":False,"simulation":False,"routing":False,"remote_service_state_change":False}
    }
    stream=io.StringIO()
    columns=["id","design","entry_kind","source_module","selector","ownership_class","owner","state_memory","source_evidence","status"]
    writer=csv.DictWriter(stream,fieldnames=columns);writer.writeheader()
    for r in rows:
        src=r.get("instance_evidence",r.get("template",{}))
        writer.writerow({"id":r["id"],"design":r["design"],"entry_kind":r["entry_kind"],
            "source_module":r.get("module"),"selector":json.dumps(r["selector"],ensure_ascii=False,sort_keys=True),
            "ownership_class":r["ownership_class"],"owner":r["owner"],
            "state_memory":json.dumps(r.get("state_and_memory_description",[]),ensure_ascii=False),
            "source_evidence":json.dumps(src,ensure_ascii=False,sort_keys=True),
            "status":"SOURCE_CHECKED_FRONTIER_PENDING_INTEGRATION"})
    payloads=[json.dumps(inventory,ensure_ascii=False,indent=2)+"\n",stream.getvalue(),
              json.dumps(baseline,ensure_ascii=False,indent=2)+"\n"]
    # All reads and validations completed before any artifact is created.
    for path,text in zip(destinations,payloads):
        with path.open("x",encoding="utf-8",newline="") as fh:
            fh.write(text)
    print(json.dumps({"status":"PASS_INVENTORY_GENERATION_NOT_STAGE_ACCEPTANCE",
        "outputs":[small_ref(p) for p in destinations],"coverage_rows":len(rows),
        "complete_design_integration":"NOT_EXECUTED"},ensure_ascii=False))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
