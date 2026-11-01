#!/usr/bin/env python3
"""Issue151: bounded static connection action planner, not an RTL/model compiler.

Python 3.7+, standard library only. Roles stay in this host-side contract. Outputs
describe capabilities to freeze before M1-M10 and bindings for M11/M12; they do
not add cells, operators or runtime role tags using upper metal.
"""
import argparse
import collections
import hashlib
import json
from pathlib import Path


VERSION = "0.1-static-action-plan"
COUNTS = {"source_roles": 23, "data_destinations": 27,
          "controlled_destinations": 20, "data_slots": 621,
          "controlled_parameter_slots": 460, "recipes": 153,
          "sample_obligations": 96}
ACTION_FAMILIES = {
    "PROVE_SCHEMA": {"stage": "software", "meaning": "Bind family, semantic role, record field, operation and provenance; no runtime role header."},
    "PROVE_NUMERIC": {"stage": "software", "meaning": "Bind Fin/Fout, signedness, range, rounding, saturation and algorithm error acceptance."},
    "BIND_PRODUCT": {"stage": "permanent_binding", "meaning": "Select an already fabricated port/route, operation ROM constants, count and owner using M11/M12."},
    "SELECT_ROUTE": {"stage": "new_fixed_glue", "meaning": "Real prebuilt MUX/demux and phase select or one dedicated point-to-point net. Exclusive valid never permits shorting push-pull outputs."},
    "HOLD_HANDSHAKE": {"stage": "new_fixed_glue", "meaning": "Capture a response before advancing source; hold payload/sideband until accepted; filter ACK/error/saturation."},
    "PACK_LANES": {"stage": "fixed_wires_and_optional_registers", "meaning": "Field selection, sign/zero extension, split/concatenate, lane order and valid-tail handling; does not alter numeric units."},
    "NATIVE_OP": {"stage": "existing_leaf_operation", "meaning": "Reuse a proved existing op (e.g. M5, E10/E13, N3/N6) only when its exact formula/layout matches; transport/owner glue remains separate."},
    "ONCHIP_STORE": {"stage": "new_fixed_glue_with_existing_S", "meaning": "Bounded S allocation, typed snapshot, write ACK consumption and credits; this round has no EXT/DMA/spill path."},
    "LIFECYCLE": {"stage": "new_fixed_control", "meaning": "Unique owner, fork reference counts, JOIN companions, RESUME same context, REENTER new context and storage lifetime."},
    "FIELD_JOIN": {"stage": "fixed_wires_and_optional_registers", "meaning": "Select record fields and collect explicitly supplied companions/ROM constants; no invented scores, gamma or inject."},
    "EXP_REPLAY": {"stage": "native_N_plus_new_control", "meaning": "Keep exact EXP lineage and factor context, wait FINALIZE, issue N6; never bitcast EXP into probability."},
    "CONTROLLED_FIELD": {"stage": "new_fixed_control", "meaning": "Unique command owner validates integral fields, bounds, reserved bits and authorized updates. Runtime ID address formation needs prebuilt checked address logic."},
    "GATHER_DATA": {"stage": "unresolved_data_and_new_fixed_control", "meaning": "Resolve ID into original score/record/data using an explicit table and layout; ID alone does not contain those data."},
    "LOADER_CAPTURE": {"stage": "new_storage_and_control", "meaning": "For serial same-S reentry, candidate 1024B snapshot, both A/B sinks, then done then ordinary writes; not existing loader storage."},
    "T_BATCH_SPOOL": {"stage": "new_control_with_reserved_S", "meaning": "Same physical T reentry needs complete old batch, max6144B S spool, ACKs, last take/release, then new BEGIN; distinct T need not force this."},
    "MISSING_NUMERIC": {"stage": "capability_gap", "meaning": "Only if no exact native-op/wiring proof exists: missing wide arithmetic/normalization/inject/etc. Freeze before M1-M10 or reject this product mapping."}
}
COMMON = ["PROVE_SCHEMA", "PROVE_NUMERIC", "BIND_PRODUCT", "SELECT_ROUTE",
          "HOLD_HANDSHAKE", "PACK_LANES", "LIFECYCLE"]
CONDITIONAL_ACTION_RULES = {
    "NATIVE_OP": "Only if a concrete op formula, unit, shape and capacity match is proved; no forced extra E/NUM hop.",
    "MISSING_NUMERIC": "Only if required arithmetic cannot be implemented by exact existing ops/wires; legal requirement remains a capability gap.",
    "ONCHIP_STORE": "Only if staging/replay/fork/reentry needs it; finite S slots and no spill fallback this round.",
    "FIELD_JOIN": "Only if record fields or independently supplied companions are consumed by chosen op.",
    "GATHER_DATA": "ID_RESOLVE only; ID_AS_INT or transport need no score gather.",
    "LOADER_CAPTURE": "Only serial same-S reentry with all A/B drained; direct legal loader sinks may avoid extra1024B.",
    "T_BATCH_SPOOL": "Only same physical T reentry/full-batch lifetime; distinct T/direct sink evaluated separately."
}
STAGES = {
    "enumeration": "SOURCE_COUNTS_AND_REFERENCES_CHECKED",
    "recipe_action_family": "CLASSIFIED_NOT_INSTANTIATED",
    "semantic_instance": "CONDITIONAL_OR_UNRESOLVED_FROM_SOURCE",
    "numeric_instance": "UNBOUND_NOT_QUALITY_ACCEPTED",
    "product_lowering": "NOT_FULLY_INSTANTIATED",
    "route_and_capacity": "UNBOUND_NO_AUTOMATIC_SPILL",
    "system_RTL": "NOT_IMPLEMENTED_BY_THIS_DELIVERY",
    "RTL_verification": "NOT_EXECUTED",
    "physical_qualification": "NOT_EXECUTED"
}


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def write_json(path, value):
    Path(path).write_bytes((json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require(condition, code, detail):
    if not condition:
        raise PlanError(code, detail)


class PlanError(Exception):
    def __init__(self, code, detail):
        self.code, self.detail = code, detail


def rne(value, shift):
    """Signed round-to-nearest ties-to-even, matches M/E/G integer formula."""
    require(isinstance(value, int) and isinstance(shift, int) and 0 <= shift <= 63,
            "BAD_INTEGER", "RNE requires an integer and shift0..63")
    if not shift:
        return value
    q, rem = divmod(value, 1 << shift)
    half = 1 << (shift - 1)
    return q + int(rem > half or (rem == half and (q & 1)))


def sat(value, bits):
    return max(-(1 << (bits - 1)), min((1 << (bits - 1)) - 1, value))


def pack(values, bits):
    return sum((v & ((1 << bits) - 1)) << (i * bits)
               for i, v in enumerate(values))


def packets_s16(values):
    return ["0x%08x" % pack(values[i:i + 2], 16)
            for i in range(0, len(values), 2)]


def bounded_values(values, low, high, count=None):
    require(isinstance(values, list) and values and
            all(isinstance(v, int) and not isinstance(v, bool) and low <= v <= high for v in values),
            "VALUE_RANGE", "Values violate the native field's range")
    if count is not None:
        require(len(values) == count, "LANE_COUNT", "Native layout lane count mismatch")


def plan_base():
    return {"planner": VERSION, "result": "ACTION_PLAN_CANDIDATE",
            "runtime_role_tag_required": False,
            "model_compiled": False, "system_RTL_implemented": False,
            "RTL_verified": False, "physical_qualified": False,
            "numeric_quality_accepted": False,
            "semantic_instance": "BOUNDED_PROBE_CONTRACT_CHECKED",
            "remaining": ["product family authorization and full numerical acceptance",
                          "physical endpoint/route/clock/reset and owner binding",
                          "implement and verify listed new glue; run RTL/system/P&R checks"],
            "runtime_guards": ["hold valid payload while ready is low",
                               "accept only correct owner's successful response",
                               "consume ACKs and obey destination lifetime"],
            "actions": [], "arithmetic": [], "gaps": []}


def same_F(actual, requested):
    require(isinstance(actual, int) and actual == requested,
            "UNIT_MISMATCH", "A wire/bitcast cannot change fixed-point F")


def m_read5_to_g(case):
    s, d = case["source"], case["destination"]
    require(s.get("op") == 5, "SOURCE_OP", "This probe requires actual M READ5")
    cmd = s["cmd_data"]
    require(isinstance(cmd, int) and cmd >= 0 and (cmd >> 10) == 0 and
            ((cmd >> 6) & 3) == 0 and ((cmd >> 8) & 3) < 3,
            "M_DESCRIPTOR", "M5 descriptor reserved bits or width invalid")
    width = (cmd >> 8) & 3
    require(width == 1, "M_NOT_S16", "Raw S32/S64 is not S16: select authorized native M5 width1 or explicit conversion")
    require(s.get("layout") == "4xS32_sign_extended_S16", "LAYOUT_MISMATCH",
            "M5 still returns four S32 carriers; S16 is its logical payload")
    require(s.get("quantization_authorized") is True, "QUANTIZATION_UNBOUND",
            "Native M5 shift/clamp must be authorized by the product numeric contract")
    same_F(s["merged_F"] - (cmd & 63), d["F"])
    require(d.get("role") == "G.x" and d["F"] == 10, "DESTINATION",
            "G activation x requires S16 Q5.10")
    require(not d.get("gated", False) or d.get("gate_handle"), "MISSING_COMPANION", "G gated mode needs gate data")
    values = s["native_output_values"]
    bounded_values(values, -32768, 32767, 4)
    p = plan_base()
    p["actions"] = ["PROVE_SCHEMA", "PROVE_NUMERIC", "BIND_PRODUCT", "SELECT_ROUTE", "NATIVE_OP", "HOLD_HANDSHAKE", "PACK_LANES"]
    p["native_commands"] = [{"macro": "M", "op": 5, "cmd_data": cmd}]
    p["wire_map"] = ["G packet0={M[47:32],M[15:0]}", "G packet1={M[111:96],M[79:64]}"]
    p["new_glue"] = ["keep existing M response held through two G accepts, or prebuilt capture if releasing M earlier",
                     "2-phase32bit MUX/splitter and valid/ready state; source ready only after final phase without capture"]
    p["reference_packets_hex"] = packets_s16(values)
    p["output_valid_elements"] = 4
    p["arithmetic"] = ["existing M5 RNE+S16 clamp already performed; no extra arithmetic for this connection"]
    p["gaps"] = ["NEW_M_TO_G_HOLD_SPLIT_ROUTE_NOT_IMPLEMENTED"]
    return p


def e_to_g(case):
    s, d = case["source"], case["destination"]
    op, shift = s["op"], s["shift"]
    require(op in (12, 13), "SOURCE_OP", "Probe supports E12 and E13")
    require(isinstance(shift, int) and 0 <= shift <= 31, "E_SHIFT", "E shift is five bits")
    n = 8 if op == 12 else 4
    expected = "8xS8_low64" if op == 12 else "4xS16_low64"
    require(s.get("layout") == expected, "LAYOUT_MISMATCH", "E12 low64 is eight S8; E13 low64 is four S16")
    vals = s["native_input_values"]
    bounded_values(vals, -(1 << (15 if op == 12 else 31)),
                   (1 << (15 if op == 12 else 31)) - 1, n)
    # E12 clamps A S16 to S8 and ignores shift. E13 reassembles four S32,
    # RNE-shifts and clamps to S16. These are software reference calculations.
    result = [sat(v, 8) for v in vals] if op == 12 else [sat(rne(v, shift), 16) for v in vals]
    actual_F = s["input_F"] if op == 12 else s["input_F"] - shift
    same_F(actual_F, d["F"])
    require(d.get("role") == "G.x" and d["F"] == 10, "DESTINATION", "G x requires Q5.10")
    p = plan_base()
    p["actions"] = ["PROVE_SCHEMA", "PROVE_NUMERIC", "BIND_PRODUCT", "SELECT_ROUTE", "NATIVE_OP", "HOLD_HANDSHAKE", "PACK_LANES"]
    p["native_commands"] = [{"macro": "E", "op": op, "shift": shift}]
    p["arithmetic"] = ["existing E12 S8 clamp; shift ignored" if op == 12 else "existing E13 S32 RNE right-shift and S16 clamp"]
    p["wire_map"] = ["sign-extend each S8 to S16 then pack two per G packet" if op == 12 else "split four low64 S16 into two G packets"]
    p["new_glue"] = ["hold existing E output or use prebuilt capture; phase select32",
                     "four phases" if op == 12 else "two phases"]
    p["reference_native_output_hex"] = "0x%032x" % pack(result, 8 if op == 12 else 16)
    p["reference_packets_hex"] = packets_s16(result)
    p["output_valid_elements"] = n
    p["gaps"] = ["NEW_E_TO_G_SPLIT_ROUTE_NOT_IMPLEMENTED"]
    return p


def g_sigmoid_to_e(case):
    s, d = case["source"], case["destination"]
    require(s.get("fn") == 1, "SOURCE_OP", "This bounded probe uses G Sigmoid fn1")
    require(d.get("role") == "E.A_vec" and d.get("F") == 10, "DESTINATION", "Probe target is E S16 Q10 operand")
    gated = s.get("gated", False)
    actual_F = 10 if gated else 14
    vals = s["native_output_values"]
    bounded_values(vals, -32768 if gated else 0, 32767 if gated else 16384, 2)
    require(actual_F == 10 or case.get("allow_native_rescale") is True,
            "NEEDS_NUMERIC_CONVERSION", "Ungated Sigmoid Q14 cannot be bitcast as Q10; E10 shift4 can perform RNE")
    p = plan_base()
    p["actions"] = ["PROVE_SCHEMA", "PROVE_NUMERIC", "BIND_PRODUCT", "SELECT_ROUTE", "HOLD_HANDSHAKE", "PACK_LANES"]
    p["native_commands"] = []
    if actual_F != 10:
        p["actions"].append("NATIVE_OP")
        p["native_commands"] = [{"macro": "E", "op": 10, "shift": 4, "active_lanes": 2,
                                  "inactive_lanes": "zero and externally ignored"}]
        p["arithmetic"] = ["existing E10 RNE right4 then S16 clamp; ties to even, including negative integers"]
        vals = [sat(rne(v, 4), 16) for v in vals]
    else:
        p["arithmetic"] = ["G gated Sigmoid output already Q10; no extra rescale"]
    p["new_glue"] = ["G32 capture and zero-pad to E128; valid count remains2, not8", "E command owner and result capture/route"]
    p["reference_valid_output_values"] = vals
    p["reference_packets_hex"] = packets_s16(vals)
    p["gaps"] = ["NEW_G_E_ROUTE_AND_OWNER_NOT_IMPLEMENTED"]
    return p


def n_exp_replay(case):
    s, d = case["source"], case["destination"]
    require(d.get("role") == "N.soft_replay" and d.get("op") == 6,
            "EXP_NOT_PROBABILITY", "EXP is an unnormalized unsigned code; probability requires N6 with correct factor context")
    lineage, context = s.get("lineage", {}), d.get("context", {})
    require(lineage.get("kind") == "N_EXP", "EXP_LINEAGE", "Exact EXP code provenance must be retained")
    direct = s.get("role") == "N.exp" and s.get("op") == 3
    if not direct:
        proof = s.get("copy_proof", {})
        expected_copy = {"S.stored_word": "S.word128", "T.committed_word": "T.word128",
                         "E.vector": "E.op10_shift0"}.get(s.get("role"))
        require(expected_copy is not None and proof.get("primitive") == expected_copy and
                proof.get("bit_exact") is True and proof.get("no_arithmetic_change") is True,
                "LOSSLESS_COPY_PROOF", "S/T/other identity replay must retain schema and a proved lossless copy path")
        if s.get("role") == "E.vector":
            require(s.get("op") == 10 and s.get("shift") == 0,
                    "LOSSLESS_COPY_PROOF", "This executable identity proof only covers actual E10 shift0; arithmetic changes lose original EXP lineage")
    for key in ("group", "max_version", "exp_set_version", "full_group_count"):
        require(key in lineage and lineage[key] == context.get(key), "EXP_CONTEXT_MISMATCH",
                "Replay group/max/EXP aggregate version and full count must match factor owner")
    vals = s["native_output_values"]
    bounded_values(vals, 0, 32768)
    require(len(vals) <= 8, "LANE_COUNT", "N command accepts1..8 elements")
    total = context["full_group_count"]
    require(context.get("context_valid") is True and context.get("mode") == 0,
            "N_CONTEXT_STATE", "N6 needs a valid Softmax context, not a new or Norm context")
    require(isinstance(total, int) and 1 <= total <= 65535 and
            0 <= context.get("replayed", 0) and context.get("replayed", 0) + len(vals) <= total,
            "N_COUNT", "Group count/replayed limit violated")
    p = plan_base()
    p["actions"] = ["PROVE_SCHEMA", "BIND_PRODUCT", "SELECT_ROUTE", "HOLD_HANDSHAKE", "PACK_LANES", "LIFECYCLE", "EXP_REPLAY", "NATIVE_OP"]
    p["native_commands"] = [{"macro": "N", "op": 6, "count": len(vals), "param": 0,
                              "data_hex": "0x%032x" % pack(vals, 16), "aux": 0}]
    p["arithmetic"] = ["existing N6: RNE30(U16_code * context_factor), clamp0..16384; no gamma multiplication"]
    p["new_glue"] = ["retain/replay exact EXP codes with same context", "wait factor_valid and own N command port"]
    p["gaps"] = ["NEW_N_REPLAY_ROUTE_AND_LIFETIME_NOT_IMPLEMENTED"]
    if context.get("factor_valid") is not True:
        p["result"] = "STATE_PENDING"
        p["gaps"].append("WAIT_SAME_CONTEXT_FACTOR_VALID_RESUME_NOT_REENTER")
    if "factor_raw" in context:
        factor = context["factor_raw"]
        require(isinstance(factor, int) and 0 <= factor <= 0xffffffff, "N_FACTOR", "Factor must fit U32")
        require(context.get("exp_count") == total and isinstance(context.get("exp_sum"), int) and context["exp_sum"] > 0,
                "N_FACTOR_CONTEXT", "Factor needs all EXP codes accumulated")
        require(factor == (1 << 44) // context["exp_sum"], "N_FACTOR_CONTEXT", "Factor does not match native op4 quotient")
        if context.get("factor_valid"):
            p["reference_probability_Q14"] = [max(0, min(16384, rne(v * factor, 30))) for v in vals]
    mapping = case.get("mapping", {})
    if mapping.get("required_bytes", 0) > mapping.get("available_onchip_bytes", 0):
        p["result"] = "MAPPING_PENDING"
        p["gaps"].append("ONCHIP_CAPACITY_NOT_SEMANTIC_ILLEGAL_NO_SPILL_THIS_ROUND")
    return p


def topk_to_controlled_gather(case):
    s, d = case["source"], case["destination"]
    require(s.get("role") == "N.topk_ids" and s.get("op") == 10,
            "SOURCE_OP", "This probe uses N10 ID output")
    require(d.get("role") == "S.address", "ID_NOT_SCORE", "ID cannot be relabeled as score; use explicit ID lookup/gather")
    ids = s["ids"]
    bounded_values(ids, 0, 65535)
    require(len(ids) <= 8, "LANE_COUNT", "N TopK returns at most8 IDs")
    domain = case["id_domain"]
    require(all(domain[0] <= x <= domain[1] for x in ids), "ID_DOMAIN", "ID outside declared algorithm domain")
    require(d.get("owner") == "S_CTRL" and d.get("policy") == "checked_dynamic",
            "PARAMETER_OWNER", "S address is a validated command-owner field, not unchecked payload forwarding")
    require(d.get("address_unit") == "S128_word" and all(isinstance(d.get(k), int) for k in ("base", "stride")) and d["base"] >= 0 and d["stride"] > 0,
            "ADDRESS_FORMULA", "Bind nonnegative base and positive stride in S128-word units")
    addresses = [d["base"] + i * d["stride"] for i in ids]
    p = plan_base()
    p["actions"] = ["PROVE_SCHEMA", "BIND_PRODUCT", "SELECT_ROUTE", "HOLD_HANDSHAKE", "PACK_LANES", "CONTROLLED_FIELD", "GATHER_DATA", "LIFECYCLE"]
    p["checked_addresses"] = addresses
    p["arithmetic"] = ["checked ID*product_constant_stride+base address formation; requires prebuilt address capability, never a new M11 adder"]
    p["new_glue"] = ["TopK ID capture/rank selector", "owner-controlled bounds check/address generator", "ordinary S read response capture and data lookup"]
    p["gaps"] = ["NEW_CONTROLLED_ID_GATHER_NOT_IMPLEMENTED"]
    if any(x > 1023 for x in addresses):
        p["result"] = "MAPPING_PENDING"
        p["gaps"].append("S_CAPACITY_OR_ADDRESS_RANGE_GAP_KEEP_SEMANTIC_REQUIREMENT")
    if case.get("resolve") == "score":
        table = case.get("score_table")
        if table is None or any(str(i) not in table for i in ids):
            if p["result"] != "MAPPING_PENDING":
                p["result"] = "DATA_PENDING"
            p["gaps"].append("ORIGINAL_SCORE_DATA_OR_ID_TO_RECORD_MAP_MISSING")
        else:
            values = [table[str(i)] for i in ids]
            bounded_values(values, -32768, 32767)
            require(isinstance(case.get("score_F"), int), "SCORE_UNITS", "Gathered score needs explicit F")
            p["reference_gathered_score_values"] = values
            p["reference_gathered_score_F"] = case["score_F"]
    return p


PLANNERS = {"M5_S16_to_G": m_read5_to_g, "E12_E13_to_G": e_to_g,
            "G_sigmoid_to_E_Q10": g_sigmoid_to_e,
            "N_EXP_to_SOFT_REPLAY": n_exp_replay,
            "TopK_ID_to_controlled_gather": topk_to_controlled_gather}


def plan(case):
    try:
        require(case.get("kind") in PLANNERS, "UNSUPPORTED_PLANNER_INSTANCE",
                "Only listed bounded probes have executable lowering rules; other recipes remain unresolved")
        return PLANNERS[case["kind"]](case)
    except PlanError as exc:
        return {"planner": VERSION, "result": "INSTANCE_REJECTED", "error_code": exc.code,
                "detail": exc.detail, "pair_permanently_illegal": False,
                "model_compiled": False, "system_RTL_implemented": False}
    except (KeyError, TypeError, ValueError) as exc:
        return {"planner": VERSION, "result": "INSTANCE_REJECTED", "error_code": "MISSING_OR_MALFORMED_BINDING",
                "detail": str(exc), "pair_permanently_illegal": False,
                "model_compiled": False, "system_RTL_implemented": False}


def recipe_family(recipe_id):
    # Source prefix typed_carrier contains an underscore; split by exact prefix.
    classes = ["typed_carrier", "diagnostic", "probability", "numeric", "record", "factor", "loader", "exp", "id"]
    prefix = next(x for x in classes if recipe_id.startswith(x + "_"))
    mode = recipe_id[len(prefix) + 1:]
    actions = list(COMMON)
    if prefix in ("record", "factor", "diagnostic") or mode == "RECORD_JOIN_N":
        actions.append("FIELD_JOIN")
    if mode.startswith("PARAM_"):
        actions.append("CONTROLLED_FIELD")
    if mode == "EXP_REPLAY_N":
        actions += ["EXP_REPLAY", "NATIVE_OP"]
    if mode == "SCORE_REPLAY_N":
        actions.append("NATIVE_OP")
    if mode.startswith("TRANSPORT_"):
        actions.append("ONCHIP_STORE")
    if prefix == "id":
        actions.append("CONTROLLED_FIELD")
    native_constraints = []
    if mode == "SCORE_REPLAY_N":
        native_constraints = [{"macro": "N", "op": 3, "destination_role": "N.exp_score",
                               "input": "same-group original S16 scores used by STATS; not EXP codes",
                               "output": "U16 EXP codes plus exp_sum accumulation",
                               "context": "valid Softmax context, statistics_final, factor not yet valid; preserve original score/max lineage"}]
    elif mode == "EXP_REPLAY_N":
        native_constraints = [{"macro": "N", "op": 6, "destination_role": "N.soft_replay",
                               "input": "same-group exact U16 EXP codes; not original scores",
                               "output": "Q14 probability",
                               "context": "valid Softmax context with matching finalized factor; preserve EXP aggregate lineage"}]
    return {"source_class": prefix, "destination_mode": mode,
            "required_action_families": sorted(set(actions)),
            "conditional_action_families": list(CONDITIONAL_ACTION_RULES),
            "native_op_constraints": native_constraints,
            "stage_ref": "uninstantiated_stage_axes",
            "instance_numeric_and_route_binding": "UNRESOLVED",
            "does_not_instantiate_one_hardware_block_per_recipe": True}


def obligation_classification(row, slot, recipes):
    src, dst = row["source"], row["destination"]
    if src == "M.read32" and dst == "E.A_cast13":
        numeric = "Native M5-S32 then E13 is an available arithmetic choice; F/shift/saturation/quality still unbound. Native M5-S16 may remove E hop only with an explicit changed instance proof."
    elif src == "E.cast32_to16" and dst in ("G.x", "G.gate"):
        numeric = "E13 output already S16 low64; if explicit F=10, connection is holding/split, not a mandatory extra converter. F remains unbound here."
    elif src == "N.exp" and dst == "N.soft_replay":
        numeric = "Reuse N6 with exact EXP/max/factor lineage; not EXP-as-probability bitcast. Context, storage and complete replay sequence uninstantiated."
    elif src == "N.topk_ids":
        numeric = "Checked ID-domain/address binding and actual gather data required; IDs do not contain score/weight values."
    elif src == "R.output":
        numeric = "R S32 common F must be declared; E13 narrowing or wider bias/inject arithmetic is not replaced by low-bit selection."
    else:
        numeric = "Fin/Fout, range, op/mode, rounding/saturation and algorithm error acceptance remain explicit requirements; reuse exact existing ops first."
    return {"id": row["id"], "model_id": row["model_id"], "kind": row["kind"],
            "slot_id": slot["id"], "source": src, "destination": dst,
            "recipe_id": row["recipe_id"], "valid_elements": row["valid_elements"],
            "shape_status": "CONFIGURED_SAMPLE_REQUIREMENT_NOT_A_SCHEDULED_OR_RESIDENT_TENSOR",
            "action_family_ref": row["recipe_id"], "stage_ref": "uninstantiated_stage_axes",
            "numeric_lowering_note": numeric,
            "retained_source_conditions": row["required_conditions"],
            "retained_source_extra_requirements": row["extra_requirements"],
            "retained_slot_gaps": slot["gap_ids"],
            "unresolved": ["concrete command/count/stride/tail and companion/context handles",
                           "numeric quality and chosen implementation proof",
                           "finite onchip allocation and legal routes/owner/lifetimes",
                           "new interconnect/control RTL and verification"],
            "model_compiled": False}


def make_contract(root):
    root = Path(root)
    work = root / "work/Melodydt/151"
    ledger = read_json(work / "edge-ledger.json")
    obligations = read_json(work / "sample-connection-obligations.json")
    actual = {"source_roles": len(ledger["source_schema"]),
              "data_destinations": len(ledger["destination_schema"]),
              "controlled_destinations": len(ledger["controlled_schema"]),
              "data_slots": len(ledger["data_slots"]),
              "controlled_parameter_slots": len(ledger["controlled_parameter_slots"]),
              "recipes": len(ledger["recipes"]),
              "sample_obligations": len(obligations["obligations"])}
    require(actual == COUNTS, "SOURCE_DENOMINATOR_CHANGED", "Review changed input rather than silently changing coverage denominator")
    slots = ledger["data_slots"] + ledger["controlled_parameter_slots"]
    by_id = {s["id"]: s for s in slots}
    require(len(by_id) == 1081, "SLOT_DUPLICATE", "Slot IDs must be unique")
    require(set((s["src"], s["dst"]) for s in ledger["data_slots"]) ==
            set((s, d) for s in ledger["source_schema"] for d in ledger["destination_schema"]),
            "DATA_CARTESIAN", "Keep all23x27 source data slots")
    require(set((s["src"], s["dst"]) for s in ledger["controlled_parameter_slots"]) ==
            set((s, d) for s in ledger["source_schema"] for d in ledger["controlled_schema"]),
            "PARAM_CARTESIAN", "Keep all23x20 controlled slots")
    mappings = {rid: recipe_family(rid) for rid in ledger["recipes"]}
    for rid, mapping in mappings.items():
        source = ledger["recipes"][rid]
        mapping["retained_source_guards"] = {
            k: source[k] for k in ("semantic_guards", "state_guards", "mapping_guards")}
    require(all(s["recipe_id"] in mappings for s in slots), "RECIPE_REFERENCE", "Every original slot must resolve")
    rows = []
    for row in obligations["obligations"]:
        require(row["slot_id"] in by_id, "OBLIGATION_SLOT", "Sample obligation must refer to existing D/P slot")
        slot = by_id[row["slot_id"]]
        require((slot["src"], slot["dst"], slot["recipe_id"]) ==
                (row["source"], row["destination"], row["recipe_id"]),
                "OBLIGATION_REFERENCE", "Sample source/destination/recipe must exactly match original slot")
        require(set(row["required_conditions"]) >= set(slot["condition_ids"]),
                "OBLIGATION_GUARD", "Do not drop original semantic conditions")
        require(row["numeric_quality_accepted"] is False and row["RTL_path_implemented"] is False and
                row["onchip_full_model_admitted"] is False,
                "OBLIGATION_BASELINE_CHANGED", "Review any new qualification rather than silently inheriting an old incomplete status")
        rows.append(obligation_classification(row, slot, mappings))
    input_paths = ["work/Melodydt/151/edge-ledger.json",
                   "work/Melodydt/151/sample-connection-obligations.json",
                   "work/Melodydt/151/onchip-contract.json",
                   "work/Melodydt/151/family-spec.json",
                   "project/rtl/block_v2/block_v2_m.sv",
                   "project/rtl/block_v2/block_v2_e.sv",
                   "project/rtl/block_v2/block_v2_g.sv",
                   "project/rtl/block_v2/block_v2_n.sv",
                   "project/rtl/block_v2/block_v2_n_group.sv",
                   "project/rtl/block_feed_v1/block_feed_s_macro.sv",
                   "project/rtl/block_feed_v1/block_feed_s16k.sv",
                   "project/rtl/block_feed_v1/block_feed_loader.sv",
                   "project/rtl/block_v1/transaction6k.sv"]
    return {"schema_version": 1, "planner_version": VERSION,
            "artifact_kind": "COMPILE_TIME_ACTION_FAMILY_CONTRACT_NOT_MODEL_COMPILER_OR_RTL",
            "baseline_revision": "e44c4f5", "source_RTL_freeze": "643c6012a11cbf461146ac40fbf61485223fe946",
            "inputs": [{"path": p, "sha256": digest(root / p)} for p in input_paths],
            "scope": {"roles": "compile_time_only_not_generic_runtime_tags",
                      "M1_M10": "freeze finite capability union: arithmetic, muxes, registers, buffers, clock/reset, controllers and storage",
                      "M11_M12": "permanently bind products to already fabricated routes/commands/constants; cannot add active circuits",
                      "system_has_external_memory": True,
                      "external_memory_this_round": "not implemented or assessed; no EXT/DMA/spill generated; future integration preserved",
                      "no_claim_of_model_compilation": True},
            "coverage_denominators": actual,
            "original_catalog_preserved": True,
            "original_slot_status_counts": dict(collections.Counter(s["status"] for s in slots)),
            "enumeration_checks": {"data_cartesian": "23x27=621",
                                   "controlled_cartesian": "23x20=460",
                                   "all153_recipe_refs_mapped_to_action_families": True,
                                   "all96_obligations_exact_slot_recipe_checked": True},
            "uninstantiated_stage_axes": STAGES,
            "action_family_count_is_not_hardware_instance_count": True,
            "action_families": ACTION_FAMILIES,
            "conditional_action_rules": CONDITIONAL_ACTION_RULES,
            "recipe_action_mapping": mappings,
            "source_role_overrides": {
                "M.result64": "Keep fullS64 or prove exact M5-subset/native conversion; low32/16 selection alone is not a numeric conversion.",
                "S.write_echo": "Capture typed echo, consume ACK, free response slot before forwarding/reentry; not an independent read port.",
                "S.loader_A_and_B": "Drain both streams and done. Serial same-S reentry needs candidate1024B snapshot; native loader stores only192B queues and has no done-abort shortcut.",
                "T.committed_word": "Same physical T reentry uses complete batch snapshot with max6144B S reservation; distinct T or source-preserving routes must be evaluated separately."},
            "slot_source_references": [{"id": s["id"], "src": s["src"], "dst": s["dst"],
                                        "recipe_id": s["recipe_id"], "source_status": s["status"],
                                        "source_condition_ids": s["condition_ids"],
                                        "source_extra_guard_ids": s["extra_guard_ids"],
                                        "source_gap_ids": s["gap_ids"]} for s in slots],
            "sample_obligation_classification": rows,
            "native_evidence": [
                {"path": input_paths[4], "lines": "117-121,202-204,240-248", "fact": "M5 logical S16 remains4xS32 carriers; four low16 fields may wire to two G32 packets"},
                {"path": input_paths[5], "lines": "30-41,75-83", "fact": "E10 RNE copy; E12 packs8xS8 ignores shift; E13 RNE narrows4xS32 to4xS16 low64"},
                {"path": input_paths[6], "lines": "43-49,63-66,75-80", "fact": "ungated Sigmoid output Q14; gated Sigmoid multiply shifts14 and keeps gate Q10"},
                {"path": input_paths[7], "lines": "25-28,86-99,114-117,151-160,203-219,228-231", "fact": "N6 zero-extends EXP U16 and RNE30 factor multiplication; N10 returns IDs, not scores"},
                {"path": input_paths[8], "lines": "1-29", "fact": "Exact unsigned division quotient; op4 factor is floor(2^44/exp_sum)"},
                {"path": input_paths[11], "lines": "27,31-47,107-108", "fact": "192B A/B queues; both streams and pending reads drain before done; snapshot1024B is additional proposed capability"},
                {"path": input_paths[12], "lines": "22-39,58-68", "fact": "Sequential T committed read and explicit release; same-T full-batch spool is a new interconnect/control plan, not native rewind"}],
            "implementation_counts": {"new_system_RTL_modules": 0, "models_compiled": 0,
                                      "obligations_fully_instantiated": 0, "RTL_system_tests": 0,
                                      "physical_qualifications": 0},
            "limits": ["Mapped recipes classify capabilities, not universally legal instances or instantiated blocks.",
                       "Executable planner supports five bounded probe kinds, not all1081 slots or full graph scheduling.",
                       "M/S/T wide, same-resource, companion and lifetime gaps remain conditional; external-memory deferral is not permanent semantic prohibition.",
                       "Probe integer references are software contract checks, not RTL simulations or algorithm numerical acceptance."]}


def run_probes(cases):
    results = []
    for case in cases:
        expected = case["expected"]
        output = plan(case["input"])
        failures = []
        for key, value in expected.items():
            if output.get(key) != value:
                failures.append({"key": key, "expected": value, "actual": output.get(key)})
        results.append({"id": case["id"], "passed": not failures,
                        "failures": failures, "plan": output})
    return {"scope": "software integer/provenance/action planning probes, not RTL/system tests",
            "count": len(results), "passed": sum(int(x["passed"]) for x in results),
            "results": results}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", required=True, help="input integrated reference package; never modified")
    ap.add_argument("--output-dir", required=True, help="explicit isolated artifact directory")
    ap.add_argument("--case", help="single supported instance JSON; otherwise classify catalog and run bounded probes")
    args = ap.parse_args()
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    if args.case:
        result = plan(read_json(args.case))
        write_json(out / "single-plan.json", result)
        print(json.dumps({"result": result["result"], "output": str(out / "single-plan.json")}))
        return 0 if result["result"] != "INSTANCE_REJECTED" else 2
    contract = make_contract(args.root)
    write_json(out / "compile-lowering-contract.json", contract)
    probes = run_probes(read_json(Path(__file__).with_name("verification-cases.json"))["cases"])
    write_json(out / "probe-results.json", probes)
    receipt = {"tool": VERSION, "python_standard_library_only": True,
               "tool_sha256": digest(Path(__file__)),
               "probe_cases_sha256": digest(Path(__file__).with_name("verification-cases.json")),
               "coverage_denominators": contract["coverage_denominators"],
               "probe_count": probes["count"], "probes_passed": probes["passed"],
               "catalog_checks_passed": True, "model_compilation": "NOT_PERFORMED",
               "RTL_verification": "NOT_PERFORMED", "physical_verification": "NOT_PERFORMED",
               "inputs": contract["inputs"],
               "artifacts": [{"path": x, "sha256": digest(out / x)}
                             for x in ("compile-lowering-contract.json", "probe-results.json")]}
    write_json(out / "verification-receipt.json", receipt)
    print(json.dumps({"catalog_counts": contract["coverage_denominators"],
                      "probes": "%d/%d" % (probes["passed"], probes["count"]),
                      "output_dir": str(out)}))
    return int(probes["passed"] != probes["count"])


if __name__ == "__main__":
    raise SystemExit(main())
