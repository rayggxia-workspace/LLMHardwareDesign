"""Independent source-bound byte/ROM calibration receiver (server real traces only)."""
import argparse
from collections import Counter
import json
from pathlib import Path

from audit_io76 import (descriptor, load_json, need, save_json, sha,
                        source_binding, verify_manifest)
from micro_audit76 import LiveReplay, oracle


OPCODES = dict(zip(("COPY", "ADD", "SUB", "MULS8", "SHL", "SHR", "OR", "AND", "XOR", "CMP", "MUX", "CTRL"), range(12)))
SPECS = {
    "mul_s32_s32": {"input": ["S32", "S32"], "output": "S64", "digit_products": 25},
    "mul_s64_s32": {"input": ["S64", "S32"], "output": "S128", "digit_products": 45},
    "mul_s32_u16": {"input": ["S32", "U16"], "output": "S64", "digit_products": 15},
    "signextend_s16_i64": {"input": ["S16"], "output": "S64"},
    "add_s64": {"input": ["S64", "S64"], "output": "S64", "overflow": "reject"},
    "sub_s64": {"input": ["S64", "S64"], "output": "S64", "overflow": "reject"},
    "add_u128": {"input": ["U128", "U128"], "output": "U128", "overflow": "reject"},
    "abs_s64": {"input": ["S64"], "output": "U64"},
    "max_s64": {"input": ["S64", "S64"], "output": "S64"},
    "cmp_s64": {"input": ["S64", "S64"], "output": "less/equal"},
    "align_s32_i64": {"input": ["S32", "shift0..63"], "output": "S64", "overflow": "reject"},
    "shl_s64_s128": {"input": ["S64", "shift0..127"], "output": "S128", "overflow": "reject"},
    "shl_u128": {"input": ["U128", "shift0..127"], "output": "U128", "overflow": "reject"},
    "rne_s64_i32": {"input": ["S64", "shift0..128"], "output": "S32", "overflow": "reject", "rounding": "symmetric RNE"},
    "rne_s128_i32": {"input": ["S128", "shift0..128"], "output": "S32", "overflow": "reject", "rounding": "symmetric RNE"},
    "udiv_u128": {"input": ["U128", "U128"], "output": "U128 quotient/remainder", "zero_divisor": "reject"},
    "isqrt_u128": {"input": ["U128"], "output": "U64 floor sqrt"},
    "div_rne_s128_u64_i32": {"input": ["S128", "U64"], "output": "S32", "overflow_or_zero": "reject", "rounding": "symmetric RNE"},
}
SOURCES = {"micro_sha256": "micro.py", "byte_core_sv_sha256": "byte_core.sv",
           "byte_tb_cpp_sha256": "byte_tb.cpp", "run_server_sha256": "run_server.py"}
COST_FIELDS = ("scalar_ALU_dependency_cycles", "software_controller_dispatches",
               "conservative_scalar_cycles_ALU_plus_dispatch", "byte_store_reads",
               "byte_store_writes", "input_load_bytes", "result_read_bytes", "scratch_peak_bytes")


def integer(value):
    need(isinstance(value, str) and str(int(value)) == value, "canonical decimal input/result integer")
    return int(value)


def decode_result(values):
    need(isinstance(values, dict), "typed micro endpoint")
    return {key: value if type(value) is bool else integer(value) for key, value in values.items()}


def shift_domain(op):
    return list(range(64 if op == "align_s32_i64" else 128 if op.startswith("shl_") else 129)) if op.startswith(("rne_", "shl_")) or op == "align_s32_i64" else [0]


def profile_from_replay(record):
    result = {key: record[key] for key in ("byte_store_reads", "byte_store_writes", "input_load_bytes", "result_read_bytes", "scratch_peak_bytes")}
    result.update(scalar_ALU_dependency_cycles=record["actions"], software_controller_dispatches=record["actions"],
                  conservative_scalar_cycles_ALU_plus_dispatch=2*record["actions"], frame_capacity_bytes=512, SIMD8_qualified=False,
                  primitive_counts={name: record["primitive_opcodes"].get(str(op), 0) for name, op in OPCODES.items()})
    return result


def verify_profile(claim, actual):
    for key in COST_FIELDS+("frame_capacity_bytes", "SIMD8_qualified"):
        need(type(claim[key]) is type(actual[key]) and claim[key] == actual[key], "actual byte microprofile "+key)
    need({key: value for key, value in claim["primitive_counts"].items() if value} ==
         {key: value for key, value in actual["primitive_counts"].items() if value}, "restricted opcode count profile")


def verify_program(folder, cases):
    """Replay finite live memory and couple every action to the real RTL output."""
    root = Path(folder)
    machine, global_action, next_case, case_start = LiveReplay(), 0, 0, None
    profiles, topologies, endpoints = [], {}, []
    with (root/"program.tsv").open("rb") as stream, (root/"rtl_actual.tsv").open("r", encoding="ascii") as rtl:
        while True:
            position = stream.tell()
            encoded = stream.readline()
            if not encoded:
                break
            line = encoded.decode("ascii")
            words = line.strip().split()
            need(words, "no blank trace injection")
            if words[0] == "B":
                need(next_case < len(cases), "trace does not add unlisted cases")
                case_start = position
            record = machine.line(line)
            if words[0] == "A":
                actual = list(map(int, rtl.readline().split()))
                need(actual == [global_action, global_action % 8, int(words[-2]), int(words[-1])],
                     "actual sequential RTL action/lane/result binding")
                global_action += 1
            if record is not None:
                case = cases[next_case]
                need(record["case"] == case["case"] == "case"+str(next_case)
                     and case["trace_byte_start"] == case_start and case["trace_byte_end"] == stream.tell(), "complete exact trace byte segment")
                need(case["status"] == "PASS_MICROPROGRAM_ORACLE" and case["op"] in SPECS, "actual typed executed micro case")
                a, b, shift = (integer(case[key]) for key in ("a", "b", "shift"))
                expected = oracle(case["op"], a, b, shift)
                result = decode_result(case["result"])
                need(result == record["outputs"] and decode_result(case["oracle"]) == expected
                     and all(result[key] == value for key, value in expected.items()), "independent published mathematical endpoint/validity")
                if "source_expected" in case:
                    need(result.get("value") == integer(case["source_expected"]), "actual source integer expected code")
                actual = profile_from_replay(record)
                verify_profile(case["profile"], actual)
                need(case["topology_sha256"] == record["topology_sha256"], "actual normalized topology SHA")
                control = (case["op"], shift if len(shift_domain(case["op"])) > 1 else 0)
                prior = topologies.setdefault(control, record["topology_sha256"])
                need(prior == record["topology_sha256"], "data-independent control/address topology for fixed typed shift")
                profiles.append(actual)
                endpoints.append({"case": record["case"], "outputs": record["outputs"], "actions": record["actions"],
                                  "topology_sha256": record["topology_sha256"]})
                next_case += 1
        need(machine.case is None and next_case == len(cases) and next_case > 0, "all listed cases fully replayed")
        remainder = [row.strip().split() for row in rtl if row.strip()]
    return profiles, endpoints, global_action, remainder


def verify_costs(table, cases, profiles, *, allow17=False):
    keys = set(SPECS)-({"signextend_s16_i64"} if allow17 and "signextend_s16_i64" not in table["ops"] else set())
    need(table["schema"] == "micro-cost-table76-v1" and set(table["ops"]) == keys, "complete typed calibration op set")
    inventory = table["inventory"]
    need(inventory["VR8_lanes"] == 8 and inventory["SFU_count"] == 1 and inventory["SFU_uses_VR8_lane0"] is True
         and inventory["scalar_frame_bytes"] == 512 and inventory["operand_register_bytes_per_active_lane"] == 5
         and inventory["VR8_operand_register_total_bytes"] == 40, "finite shared VR8/SFU/frame/operand inventory")
    need(inventory["ROM"] == {"word_bits": 32, "latency_cycles": 2, "II_cycles": 1, "ports": 1,
                               "depth_words": 32768, "capacity_bytes": 131072}, "qualified ROM port/word/latency inventory")
    need(inventory["SFU_ops"] == ["udiv_u128", "isqrt_u128", "div_rne_s128_u64_i32"], "single SFU shared microprogram keys")
    for op in sorted(keys):
        value = table["ops"][op]
        need(value["spec"] == SPECS[op], "typed width/round/guard specification "+op)
        selected = [i for i, case in enumerate(cases) if case["op"] == op]
        controls = [i for i in selected if cases[i]["source"] == "complete_shift_domain_zero_input"]
        domain = shift_domain(op)
        if len(domain) > 1:
            need(sorted(integer(cases[i]["shift"]) for i in controls) == domain
                 and all(integer(cases[i]["a"]) == 0 and integer(cases[i]["b"]) == 1 for i in controls),
                 "entire finite shift domain actually RTL replayed")
            basis = controls
        else:
            need(bool(selected), "each no-shift typed operation actually replayed")
            basis = selected
        expected = {key: max(profiles[i][key] for i in basis) for key in COST_FIELDS}
        expected.update(primitive_counts={key: max(profiles[i]["primitive_counts"][key] for i in basis) for key in OPCODES},
                        frame_capacity_bytes=512, SIMD8_qualified=False)
        need(value["costs"] == expected, "exhaustive finite-domain width fee/profile "+op)
        need(all(profiles[i]["scalar_ALU_dependency_cycles"] == expected["scalar_ALU_dependency_cycles"] for i in selected)
             and all(profiles[i][key] <= expected[key] for i in selected for key in COST_FIELDS), "fixed dependency topology/bound covers actual operands")
        proof = value["proof"]
        need(proof["kind"] == "fixed_loops_exhaustive_shift_domain" and proof["domain"] == domain
             and proof["source_sha256"] == table["source"]["micro_sha256"]
             and value["domain_bound_status"] == "FIXED_DATA_INDEPENDENT_TOPOLOGY_EXHAUSTIVE_SHIFT", "source-bound finite-domain proof")
        coverage = {"cases": len(selected), "boundary": sum(cases[i]["source"] == "boundary" for i in selected),
                    "random": sum(cases[i]["source"] == "random_seed7601" for i in selected),
                    "real_Granite": sum(isinstance(cases[i]["source"], dict) for i in selected),
                    "complete_shift_domain_vectors": len(controls), "RTL_status": "PASS_BYTE_CORE_RTL_REPLAY"}
        need(value["coverage"] == coverage, "executed vectors coverage by typed op")
        need(value["observed_max"] == {key: max(profiles[i][key] for i in selected) for key in
                                      ("scalar_ALU_dependency_cycles", "byte_store_reads", "byte_store_writes", "scratch_peak_bytes")},
             "actual observed profile stays distinct from finite-domain fee")
    return len(keys)


def verify_actual_sources(cases, compiled, granite):
    """Reconstruct every actual operand from unchanged prior integer artifacts."""
    import numpy as np
    compiled = Path(compiled)
    cm, _ = verify_manifest(compiled, kind="granite-moe-compiled74-v1", statuses=("COMPILED_NOT_EXECUTED",))
    need(cm["model_revision"] == "a02780686e08a03fe0d2679a293b5c74a90efa89", "unchanged Granite revision")
    indexed = {}
    for folder in granite:
        folder = Path(folder)
        manifest, _ = verify_manifest(folder, kind="granite-moe-run74-v1", statuses=("EXECUTED_COMPLETE",))
        report = load_json(folder/"report.json")
        need(report["router_bits"] == 16 and report["split"] == "evaluation" and report["layer"] in (0, 13), "actual frozen R16/evaluation source")
        indexed[sha(folder/"manifest.json")] = (folder, report["layer"])
    arrays = {}
    with np.load(compiled/"constants.npz", allow_pickle=False) as constants:
        for fingerprint, (folder, layer) in indexed.items():
            with np.load(folder/"runtime.npz", allow_pickle=False) as archive:
                arrays[fingerprint] = (layer, {key: archive[key] for key in archive.files})
        count = 0
        for case in cases:
            source = case["source"]
            if not isinstance(source, dict):
                continue
            need(source["manifest_sha256"] in arrays, "actual sample source manifest")
            layer, z = arrays[source["manifest_sha256"]]
            need(integer(source["layer"]) == layer, "actual source layer")
            p = source["provenance"]
            p = {key: [integer(v) for v in value] if isinstance(value, list) else integer(value) if isinstance(value, str) and value.lstrip("-").isdigit() else value for key, value in p.items()}
            op = case["op"]; expected_value = None
            if "down_acc32" in p:
                t, rank, c = p["down_acc32"]; expert = int(z["router.ids"][t, rank])
                need(p["expert"] == expert and p["mantissa_output"] == c, "real expert ID/output selection")
                a, b, shift = int(z["down_acc32"][t, rank, c]), int(constants[f"L{layer}.down_mant_q31"][expert, c]), 0
                expected_value = int(z["down_RQ_product64"][t, rank, c])
            elif "down_RQ_product64" in p:
                t, rank, c = p["down_RQ_product64"]; expert = int(z["router.ids"][t, rank])
                a, b = int(z["down_RQ_product64"][t, rank, c]), 0
                shift = 31-int(constants[f"L{layer}.down_exp"][expert, c])-int(z["mid_delta"][t, rank])
                expected_value = int(z["down_q12"][t, rank, c])
            elif "down_q12" in p:
                t, rank, c = p["down_q12"]
                need(p["gate_q15"] == [t, rank], "same actual gate operand")
                a, b, shift = int(z["down_q12"][t, rank, c]), int(z["router.gate_q15"][t, rank]), 0
                expected_value = int(z["merge_product64"][t, rank, c])
            elif "layer_output_q12" in p:
                t, c = p["layer_output_q12"]
                a, b, shift = int(z["layer_output_q12"][t, c]), int(constants[f"L{layer}.next_gamma_q20"][c]), 0
            elif "norm_numerator_for" in p or "next_norm" in p:
                t, c = p.get("norm_numerator_for", p.get("next_norm"))
                product = int(z["layer_output_q12"][t, c])*int(constants[f"L{layer}.next_gamma_q20"][c])
                a, b, shift = (product, 0, 12) if op == "shl_s64_s128" else (product << 12, int(z["next_norm.denominator_u64"][t]), 0)
                if op == "div_rne_s128_u64_i32": expected_value = int(z["next_norm_q12"][t, c])
            elif "next_norm_sumsq" in p:
                t = p["next_norm_sumsq"]
                a = (int(z["next_norm.sumsq_hi_u64"][t]) << 64)+int(z["next_norm.sumsq_lo_u64"][t]); b, shift = 1536, 0
            elif "next_norm_variance" in p:
                t = p["next_norm_variance"]
                value = (int(z["next_norm.variance_hi_u64"][t]) << 64)+int(z["next_norm.variance_lo_u64"][t])
                a, b, shift = (value, 0, 40) if op == "shl_u128" else (value << 40, 0, 0)
                if op == "isqrt_u128": expected_value = int(z["next_norm.denominator_u64"][t])
            elif "down_exp" in p:
                # Typed exponent conversion was added without changing old numeric results.
                expert, c = p["down_exp"]
                a, b, shift = int(constants[f"L{layer}.down_exp"][expert, c]), 0, 0
            else:
                raise ValueError("unknown actual sample provenance")
            need((integer(case["a"]), integer(case["b"]), integer(case["shift"])) == (a, b, shift), "reconstructed actual integer operands")
            if expected_value is not None:
                need(integer(case["source_expected"]) == expected_value, "reconstructed actual integer result code")
            count += 1
    need(count > 0 and {value[1] for value in indexed.values()} == {0, 13}, "both actual layers represented")
    return count


def verify_rom(folder, compiled, report, rtl_lines):
    import numpy as np
    root = Path(folder)
    with np.load(Path(compiled)/"constants.npz", allow_pickle=False) as constants:
        actual = []
        for key in ("silu_lut_q12", "route_exp2_q24"):
            value = constants[key]
            need(value.dtype.kind in "iu" and value.dtype.itemsize == 4, "real 32bit ROM constants")
            actual += [int(v) % (1 << 32) for v in value.reshape(-1)]
    words = [int(line, 16) for line in (root/"rom.hex").read_text(encoding="ascii").splitlines()]
    need(len(actual) == 18434 and len(words) == 32768 and words == actual+[0]*(32768-len(actual)), "actual LUT words, finite ROM and padding")
    queries = [list(map(int, row.split())) for row in (root/"rom.requests").read_text(encoding="ascii").splitlines()]
    need(queries and len(queries) == len(rtl_lines) and all(len(v) == 2 and 0 <= v[0] < 32768 and v[1] == words[v[0]] for v in queries), "ROM request data/address binding")
    for i, ((address, word), line) in enumerate(zip(queries, rtl_lines)):
        need(line == ["R", str(i+2), str(address), str(word)], "ROM actual sequential latency2/II1 response")
    need(report["ROM"]["ROM_file_sha256"] == sha(root/"rom.hex")
         and report["ROM"]["requests_sha256"] == sha(root/"rom.requests")
         and report["ROM"]["word_bits"] == 32 and report["ROM"]["latency_cycles"] == 2
         and report["ROM"]["II_cycles"] == 1 and report["ROM"]["requests"] == len(queries), "actual ROM report/source qualification")
    return len(queries)


def verify_micro(folder, producer_dir, compiled, granite, *, allow17=False):
    root = Path(folder); producer_dir = Path(producer_dir)
    manifest, artifacts = verify_manifest(root, kind="micro-calibration-run76-v1", statuses=("PASS_BYTE_CORE_AND_WIDE_MICROPROGRAM",))
    source_binding(manifest, {key: producer_dir/name for key, name in SOURCES.items()})
    report = load_json(root/"report.json"); table = load_json(root/"cost_table.json"); cases = load_json(root/"cases.json")
    need(report["source"] == table["source"] == manifest["source"] and report["schema"] == "micro-calibration76-v1"
         and report["status"] == manifest["status"] and report["full_wide_RTL_FSM"] is False, "bound conditional calibration report")
    profiles, endpoints, actions, rtl_lines = verify_program(root, cases)
    keys = verify_costs(table, cases, profiles, allow17=allow17)
    actual_cases = verify_actual_sources(cases, compiled, granite)
    queries = verify_rom(root, compiled, report, rtl_lines)
    rtl = load_json(root/"rtl_report.json")
    need(report["RTL"] == rtl and rtl["status"] == "PASS_BYTE_CORE_RTL_REPLAY" and rtl["actions"] == actions
         and rtl["ALU_action_cycles"] == actions and rtl["ALU_latency_edges"] == 1 and rtl["cases"] == len(cases)
         and rtl["ROM_requests"] == queries and rtl["ROM_latency_cycles"] == 2 and rtl["ROM_II_cycles"] == 1
         and rtl["ROM_word_bits"] == 32 and rtl["ROM_ports"] == 1
         and rtl["lanes_covered"] == [actions//8+int(i < actions % 8) for i in range(8)]
         and report["cases"] == len(cases) and report["actions"] == actions, "full actual causal RTL statistics")
    need(all(command["returncode"] == 0 for command in report["commands"]), "actual tool commands completed")
    return {"schema": "micro-independent-receipt76-v1", "status": "PASS_MICRO_CAUSAL_BYTE_AND_ROM",
            "producer_manifest": descriptor(root/"manifest.json"), "artifacts": artifacts,
            "cost_table": descriptor(root/"cost_table.json"), "cases": len(cases), "actions": actions,
            "typed_keys": keys, "service_all_keys_qualified": keys == len(SPECS), "actual_Granite_cases": actual_cases,
            "ROM_actual_requests": queries, "endpoints": endpoints,
            "limits": ["Actual restricted byte RTL results drive causal live-store dependencies; all published outputs independently checked",
                       "Wide-loop controller/addressing and 512B backing are software, not full wide RTL FSM/RF/STA/PPA",
                       "One candidate dispatch surcharge/action and finite frame/BUS cost remain payable; scalar costs cannot divide by8",
                       "Actual LUT payload fits tested128KiB ROM; whole4,260,100B physical macro timing/capacity is not RTL/PPA-qualified"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("run", "producer-dir", "compiled", "binding", "out"):
        parser.add_argument("--"+name, type=Path, required=True)
    parser.add_argument("--granite", type=Path, action="append", required=True)
    parser.add_argument("--allow-17-key-pilot", action="store_true")
    parser.add_argument("--expect-reject", action="store_true")
    args = parser.parse_args(); args.out.mkdir(parents=True, exist_ok=False)
    binding = load_json(args.binding)
    for key, name in (("receive_micro76_sha256", "receive_micro76.py"), ("micro_audit76_sha256", "micro_audit76.py"), ("audit_io76_sha256", "audit_io76.py")):
        need(binding.get(key) == sha(Path(__file__).with_name(name)), "independent micro source binding "+key)
    try:
        receipt = verify_micro(args.run, args.producer_dir, args.compiled, args.granite, allow17=args.allow_17_key_pilot)
    except ValueError as error:
        receipt = {"schema": "micro-independent-rejection76-v1", "status": "REJECTED", "reason": str(error),
                   "producer_manifest": descriptor(args.run/"manifest.json"), "source": binding}
        save_json(args.out/"receipt.json", receipt)
        if args.expect_reject:
            need(str(error) == "only initialized input bytes before arithmetic, no injected intermediate", "expected original post-ALU host input injection must be actual rejection")
            print("EXPECTED_REJECTION", str(error), flush=True)
            return
        raise
    need(not args.expect_reject, "expected rejection unexpectedly accepted")
    receipt["source"] = binding
    save_json(args.out/"receipt.json", receipt)
    print(receipt["status"], receipt["cases"], receipt["actions"], flush=True)


if __name__ == "__main__":
    main()
