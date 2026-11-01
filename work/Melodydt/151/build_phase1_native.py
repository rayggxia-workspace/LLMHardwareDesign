#!/usr/bin/env python3
"""Build source-traced seven-leaf contracts. Python3.7 standard library only.

This checks source/interface consistency, not RTL temporal correctness. The only
write targets are files below the explicitly supplied isolated --output-dir.
"""
import argparse
import copy
import hashlib
import json
import re
from pathlib import Path

FREEZE = "643c6012a11cbf461146ac40fbf61485223fe946"
TOPS = {
    "M": ("project/rtl/block_v2/block_v2_m.sv", "block_v2_m"),
    "N": ("project/rtl/block_v2/block_v2_n.sv", "block_v2_n"),
    "E": ("project/rtl/block_v2/block_v2_e.sv", "block_v2_e"),
    "G": ("project/rtl/block_v2/block_v2_g.sv", "block_v2_g"),
    "R": ("project/rtl/block_library_v1/block_v1_r.sv", "block_v1_r"),
    "S": ("project/rtl/block_feed_v1/block_feed_s_macro.sv", "block_feed_s_macro"),
    "T": ("project/rtl/block_v1/transaction6k.sv", "transaction6k")
}
S_STORE = "project/rtl/block_feed_v1/block_feed_s16k.sv"
S_LOADER = "project/rtl/block_feed_v1/block_feed_loader.sv"


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def write_json(path, value):
    Path(path).write_bytes((json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def stripped_comments(text):
    return re.sub(r"/\*.*?\*/|//[^\n]*", lambda m: re.sub(r"[^\n]", " ", m.group()), text, flags=re.S)


def parse_ports(text, module):
    """ANSI ports with inherited comma declarations; fail closed on unknown syntax."""
    clean = stripped_comments(text)
    match = re.search(r"\bmodule\s+" + re.escape(module) + r"\s*\((.*?)\)\s*;", clean, re.S)
    if not match:
        raise ValueError("Missing ANSI module header: " + module)
    ports = []
    inherited = None
    cursor = match.start(1)
    for fragment in match.group(1).split(","):
        token = fragment.strip()
        declaration = re.match(r"^(input|output|inout)\s+(?:(wire|reg|logic)\s+)?(?:(signed)\s+)?(?:\[(\d+)\s*:\s*(\d+)\]\s+)?(\w+)$", token)
        if declaration:
            direction, data_kind, signed, msb, lsb, name = declaration.groups()
            inherited = {"direction": direction, "data_kind": data_kind or "implicit_wire",
                         "signed": bool(signed), "msb": int(msb) if msb else None,
                         "lsb": int(lsb) if lsb else None,
                         "width": abs(int(msb) - int(lsb)) + 1 if msb else 1}
        else:
            if inherited is None or not re.match(r"^\w+$", token):
                raise ValueError("Unsupported port syntax: " + token)
            name = token
        port = dict(inherited)
        port["name"] = name
        port["declaration_line"] = clean.count("\n", 0, cursor + fragment.rfind(name)) + 1
        ports.append(port)
        cursor += len(fragment) + 1
    if len(set(p["name"] for p in ports)) != len(ports):
        raise ValueError("Duplicate port name")
    return ports


def port_signature(ports):
    return [(p["name"], p["direction"], p["width"], p["data_kind"], p["signed"]) for p in ports]


def trace(root, path, first, last):
    lines = (root / path).read_text(encoding="utf-8").splitlines()
    if not 1 <= first <= last <= len(lines):
        raise ValueError("Source range outside file")
    return {"path": path, "first_line": first, "last_line": last,
            "source_commit": FREEZE,
            "github": "https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/" + FREEZE + "/" + path + "#L" + str(first)}


def op(name, native_guard, input_schema, response, effect, trace_id, ignored=None):
    return {"name": name, "native_guard": native_guard, "input_schema": input_schema,
            "response": response, "effect": effect, "trace_ids": [trace_id],
            "native_ignored_fields": ignored or [],
            "owner_policy": "External unique owner must also prove family/units/lineage/lifetime; native guard alone is not full admission."}


def channel(name, valid, ready, transfer, payload, owner, note=""):
    return {"name": name, "valid_or_request": valid, "ready_or_take": ready,
            "transfer": transfer, "payload": payload, "outside_driver": owner,
            "note": note}


def m_semantics():
    return {
        "owner": "M_CTRL", "count_port": False,
        "request_acceptance": "cmd_valid&&cmd_ready; cmd_ready=!reset&&state==IDLE&&(!rsp_valid||rsp_ready)",
        "response_acceptance": "rsp_valid&&rsp_ready; all response data/error/saturated held until consumed",
        "busy_meaning": "!cmd_ready, includes reset and unconsumed response; not a compute-only flag",
        "channels": [
            channel("A", "a_valid", "a_ready", "a_valid&&a_ready", "bank1,row3,tile2,wide1,A128", "S_LOADER", "Native A ready is output by M; selected input bank locked during EXEC; other bank may preload."),
            channel("B", "b_valid", "b_ready", "b_valid&&b_ready", "bank1,tile2,wide1,half1,B512", "S_LOADER", "S8 half must0; S16 half1 only after matching bank/tile wide half0."),
            channel("command", "cmd_valid", "cmd_ready", "cmd_valid&&cmd_ready", "op4,index6,data64", "M_CTRL"),
            channel("response", "rsp_valid", "rsp_ready", "rsp_valid&&rsp_ready", "data128,error1,saturated1", "M_CTRL")],
        "operand_layout": {"A": "8 S8 in low64 or8 S16 in128; row/tile selected explicitly",
                           "B": "n-major offset8*n+k; S8=64 elements per512; S16=32 elements per512 with half0/1",
                           "input_banks": 2, "max_rows": 8, "max_tiles": 4,
                           "result_context": "One shared8x8 S64 merged context across both input banks; not two result contexts"},
        "operations": {
            "3": op("READ_S64_PAIR", "merged_valid[row] && pair<4 && data==0", "index=(row<<3)|pair, row0..7,pair0..3", "payload:2xS64/128", "Read does not release merged row", "M_READ_OPS"),
            "4": op("SET_SCALE", "index==0 && data[63:21]==0", "signed factor=data[15:0]; left_shift=data[20:16]0..31", "ACK:data0,error0,saturated0", "Global scale, applied on EXEC; not matrix EXEC or per-lane scale", "M_READ_OPS"),
            "5": op("READ_FORMATTED", "merged_valid[row] && index[2:0]<2 && data[63:10]==0 && data[9:8]<3 && data[7:6]==0", "index=(row<<3)|half0..1; right_shift=data[5:0]0..63; width=data[9:8]:0=S8,1=S16,2=S32", "payload:4xS32 carrier/128 even when logical S8/S16; RNE then clamp; saturated=OR", "Read does not release result; logical16 can be extracted only after this numeric conversion", "M_FORMAT"),
            "6": op("CLEAR_ALL_VALID", "index==0 && data==0", "none", "ACK:data0", "Clear A/B validity,merged_valid,partial_valid; does not clear payload RAM or scale", "M_READ_OPS"),
            "10": op("EXEC", "descriptor_ok; A/B validity and formats match; if append, old rows valid with same active_n", "index[5]=bank,index[4:0]=0; bits0 fmtA,1 fmtB,2 clear_result,3 reserved0,7:4 lastK1..8,11:8 N1..8,14:12 tiles1..4,18:15 rows1..8,63:19=0", "ACK/status only:data[7:0]=fault_rows,upper120=0,error=OR fault mask,saturated0; NOT matrix payload", "One K segment<=32; successful rows atomically commit8 S64; failed row preserves prior merged row; no command-wide rollback", "M_EXEC"),
            "11": op("CLEAR_INPUT_BANK", "index[5:1]==0 && data==0", "index[0]=bank", "ACK:data0", "Clear only selected input-bank A/B validity; preserve merged and scale", "M_READ_OPS"),
            "12": op("READ_PARTIAL_DIAG", "data==0 && index[2:0]<4 && partial_valid[index[3]] && bank_owner[index[3]]==index[5:3]", "row=index[5:3],pair=index[1:0],index[2]=0,partial_bank=index[3] overlaps row low bit", "payload:2xS40 sign-extended to2xS64", "Diagnostic partial before global scale/merge, not complete result history", "M_READ_OPS")},
        "invalid_operation": "Unknown op or failed per-op native guard produces error1,data0,saturated0. EXEC fault_rows status applies after a valid EXEC runs; descriptor rejection is a separate immediate error response.",
        "visibility_commit_release": ["A/B writes become valid on accepted channel handshake.", "EXEC row-level commit precedes final status response; error may accompany other rows already updated.", "M3/M5 read only; release/reuse is external lifetime policy; CLEAR or later EXEC may invalidate/overwrite.", "CLEAR_ALL does not reset scale; reset initializes factor1,left_shift0."],
        "cancel_reset": "No in-flight abort. Clear commands require IDLE/cmd_ready. Reset drops in-flight/results-valid and initializes scale, without clearing all operand/result payload bytes.",
        "trace_ids": ["M_PORTS", "M_READY", "M_DESC", "M_FORMAT", "M_EXEC", "M_READ_OPS", "M_RESET"]}


def n_semantics():
    common = "Commands accepted only IDLE and prior response empty/consumed; count fields not listed as consumed are natively ignored."
    return {
        "owner": "N_CTRL", "count_port": True,
        "request_acceptance": "cmd_valid&&cmd_ready; cmd_ready=!reset&&phase==IDLE&&(!rsp_valid||rsp_ready)",
        "response_acceptance": "rsp_valid&&rsp_ready; response data/error/saturated held",
        "busy_meaning": "!cmd_ready; includes pending response/reset",
        "channels": [channel("command", "cmd_valid", "cmd_ready", "cmd_valid&&cmd_ready", "op4,count4,param32,data128,aux128", "N_CTRL"),
                     channel("response", "rsp_valid", "rsp_ready", "rsp_valid&&rsp_ready", "data128,error1,saturated1", "N_CTRL")],
        "modes": {"0": "Softmax", "1": "RMS", "2": "L2"},
        "count_contract": "STATS/EXP/Norm/Soft replay count1..8; TopK_LOAD count1..4; no per-lane mask; group count1..65535; TopK records<=40,K1..8",
        "numeric_formulas": {"EXP": "scoreS16Q10 minus same-group max inS17; d<-16384 gives0,d>=0 gives32768; otherwise fixed LUT with RNE interpolation -> U16Q15",
                             "Softmax_factor": "floor(2^44/exp_sum), must fitU32; N6 usesRNE30(U16code*factor) then clamp0..16384",
                             "RMS": "a=floor((sumsq<<16)/count)+(epsilon_raw<<16)",
                             "L2": "a=(sumsq<<16)+(epsilon_raw<<16)",
                             "Norm_factor": "root=floor(sqrt(a)); factor=floor(2^38/root), rootnonzero andfactorfitsU32",
                             "Norm_result": "satS16(RNE30(x_raw*factor*gamma_raw)); gamma nominalS16Q10,outputF explicitly bound",
                             "epsilon": "positiveU32 in original input-raw-square units forRMS/L2; model epsilon conversion/rounding requires separate proof"},
        "operations": {
            "0": op("BEGIN_GROUP", "param<=2 && (param==0 || data[31:0]!=0)", "param=mode0/1/2; epsilon=data[31:0] positive for Norm", "ACK:data0", "Reset Norm/Softmax statistics,EXP/replayed counts and factor_valid; create context; DOES NOT clear top_loading", "N_DISPATCH", ["cmd_count", "cmd_aux", "cmd_data[127:32]"]),
            "1": op("STATS", "context_valid&&!statistics_final && count1..8 && accumulated_count+count<=65535", "count S16 values in low16*count data; aux ignored", "ACK:data0", "Update count,sum,sumsq,max,min; preserve original scores/x for replay externally", "N_GUARDS", ["cmd_param", "cmd_aux", "inactive data lanes"]),
            "2": op("FINALIZE_STATS", "context_valid&&!statistics_final&&accumulated_count!=0", "none", "ACK:data0,error for arithmetic factor failure", "Softmax only finalizes stats; RMS/L2 compute normalization factor, set factor_valid on success", "N_FACTOR", ["cmd_count", "cmd_param", "cmd_data", "cmd_aux"]),
            "3": op("SCORE_TO_EXP", "context_valid&&mode==0&&statistics_final&&!factor_valid && count1..8 && exp_count+count<=accumulated_count", "original same-group S16 score Q10 in data; NOT EXP codes", "payload:count U16 EXP codes0..32768, upper inactive lanes0", "Compute EXP(score-max), accumulate exp_sum/exp_count; exact codes/lineage retained externally for N6", "N_EXP", ["cmd_param", "cmd_aux", "inactive data lanes"]),
            "4": op("FINALIZE_EXP", "context_valid&&mode==0&&statistics_final&&!factor_valid&&exp_count==accumulated_count&&exp_sum!=0", "none", "ACK:data0,error if divide/quotient failure", "factor=floor(2^44/exp_sum), must fitU32; set factor_valid", "N_FACTOR", ["cmd_count", "cmd_param", "cmd_data", "cmd_aux"]),
            "5": op("NORM_REPLAY", "context_valid&&factor_valid&&mode!=0 && count1..8 && replayed+count<=accumulated_count", "data=S16 x same-group; aux=S16 gamma per valid lane, nominal Q10", "payload:count S16 RNE30(x*factor*gamma), saturateS16; inactive lanes0", "Increment replayed; gamma/epsilon determine output units; no beta,mean subtraction or LayerNorm mode", "N_REPLAY", ["cmd_param", "inactive data/aux lanes"]),
            "6": op("SOFT_REPLAY", "context_valid&&factor_valid&&mode==0 && count1..8 && replayed+count<=accumulated_count && each valid code<=32768", "data=exact U16 EXP codes from same max/aggregate context, NOT original scores", "payload:count nonnegative S16 probabilityQ14=clamp0..16384(RNE30(U16_code*factor)); inactive lanes0", "Zero-extend U16 before factor multiply; no gamma; increment replayed", "N_REPLAY", ["cmd_param", "cmd_aux", "inactive data lanes"]),
            "7": op("READ_STATS", "context_valid", "none", "record128:count[15:0]U16,max[31:16]S16,min[47:32]S16,sum[79:48]S32,sumsq[127:80]U48", "Read does not release context", "N_DISPATCH", ["cmd_count", "cmd_param", "cmd_data", "cmd_aux"]),
            "8": op("BEGIN_TOPK", "param>=1&&param<=8", "param=K1..8", "ACK:data0", "Clear top_count,set top_loading; independent of Norm context, may replace unfinished TopK loading natively", "N_TOPK", ["cmd_count", "cmd_data", "cmd_aux"]),
            "9": op("LOAD_TOPK_RECORDS", "top_loading && count1..4 && top_count+count<=40", "each32bit record:scoreS16 low16,ID U16 high16", "ACK:data0", "Store input records; IDs need not equal record position", "N_TOPK", ["cmd_param", "cmd_aux", "inactive data records"]),
            "10": op("FINISH_TOPK", "top_loading&&top_count>0&&K<=top_count", "none", "payload:K U16 IDs, inactive lanes0; NOT scores or routing weights", "Descending signed score; ties lowerID; chosen record removed; clear top_loading", "N_TOPK", ["cmd_count", "cmd_param", "cmd_data", "cmd_aux"]),
            "11": op("READ_FACTOR", "factor_valid", "none", "factorU32 in low32; upper96zero", "Factor meaning depends on Norm/Softmax context, not one universal Q format", "N_DISPATCH", ["cmd_count", "cmd_param", "cmd_data", "cmd_aux"])},
        "invalid_operation": "Other op or failed command_ok returns error1,data0,saturated0 without executing accepted mathematical operation",
        "visibility_commit_release": [common, "No commit/release port. Context persists across calls and may be overwritten by a new BEGIN; external owner must preserve needed results/lineage.", "Native counters/guards do not prove same-group score/gamma/EXP provenance; this is a required external contract.", "Norm epsilon is raw input-square units; factor and gamma formulas must be explicitly bound; epsilon0 is not legal for Norm."],
        "cancel_reset": "No abort/cancel. New BEGIN only when ready, may overwrite previous Norm/Softmax group; BEGIN does not cancel TopK context. Reset invalidates contexts, pending response and active operation; not all internal payload arrays reset.",
        "trace_ids": ["N_PORTS", "N_READY", "N_GUARDS", "N_DISPATCH", "N_EXP", "N_FACTOR", "N_REPLAY", "N_TOPK", "N_RESET"]}


def e_semantics():
    definitions = [
        ("ADD", "satS16(A+B)", "A,B", "ignored"),
        ("SUB", "satS16(A-B)", "A,B", "ignored"),
        ("MUL", "satS16(RNEshift(A*B))", "A,B", "RNE right0..31"),
        ("FMA", "satS16(RNEshift(A*B+C))", "A,B,C; C in product raw units", "RNE right0..31"),
        ("MAX", "max(A,B)", "A,B", "ignored"),
        ("MIN", "min(A,B)", "A,B", "ignored"),
        ("SELECT", "C!=0?A:B", "A,B,C as predicate", "ignored"),
        ("SHIFT_LEFT", "satS16(A<<shift)", "A", "left0..31"),
        ("SHIFT_RIGHT_ARITH", "satS16(A>>>shift), not RNE", "A", "arithmetic right0..31"),
        ("ROPE_PAIR", "even=Aeven*Beven-Aodd*Bodd; odd=Aodd*Beven+Aeven*Bodd; RNEshift once then satS16", "A,B adjacent complete pairs", "RNE right0..31"),
        ("RNE_COPY", "satS16(RNEshift(A))", "A", "RNE right0..31"),
        ("ABS", "satS16(abs(A)); -32768 becomes32767", "A", "ignored"),
        ("PACK_S8", "8 S16 A clamp to8 S8 in low64; upper64zero", "A", "ignored"),
        ("CAST_S32_S16", "A interpreted4xS32, RNEshift then clamp4xS16 in low64; upper64zero", "A as four S32", "RNE right0..31")]
    operations = {}
    for code, (name, formula, operands, shift) in enumerate(definitions):
        operations[str(code)] = {"name": name, "formula": formula, "operands": operands,
                                 "shift_semantics": shift, "native_guard": "in_op<=13; all5bit shifts accepted",
                                 "response": "out_valid/data128,error,saturated; any lane clamp OR",
                                 "trace_ids": ["E_ROUND_PACK", "E_EXEC"]}
    return {"owner": "E_CTRL", "count_port": False,
            "request_acceptance": "in_valid&&in_ready; in_ready=!reset&&phase==IDLE&&(!out_valid||out_ready)",
            "response_acceptance": "out_valid&&out_ready; held until consumed",
            "channels": [channel("input", "in_valid", "in_ready", "in_valid&&in_ready", "op4,shift5,A/B/C128", "E_CTRL"), channel("output", "out_valid", "out_ready", "out_valid&&out_ready", "data128,error,saturated", "E_CTRL")],
            "operations": operations,
            "lane_contract": "Normally8 S16 lanes; E12=8 S8 low64; E13=4 S16 low64. No count/mask port. Outside owner maintains valid tail/padding; RoPE requires actual logical pairs.",
            "invalid_operation": "in_op14/15 accepted as error response data0,saturated0; no legal arithmetic execution",
            "visibility_commit_release": "No persistent result bank or commit. Inputs captured on handshake; output consumed only on out_valid&&out_ready; independent operations serialize through one engine.",
            "cancel_reset": "No abort/cancel; drain legal/illegal output. Synchronous reset drops operation/response; internal arithmetic registers need not reset when invalid.",
            "trace_ids": ["E_PORTS", "E_READY", "E_ROUND_PACK", "E_EXEC", "E_RESET"]}


def g_semantics():
    return {"owner": "G_CTRL", "count_port": False,
            "request_acceptance": "in_valid&&in_ready; advance=!out_valid||out_ready; in_ready=!reset&&advance",
            "response_acceptance": "out_valid&&out_ready; when stalled all pipeline stages freeze together",
            "channels": [channel("input", "in_valid", "in_ready", "in_valid&&in_ready", "fn3,gated1,x32,gate32", "G_CTRL"), channel("output", "out_valid", "out_ready", "out_valid&&out_ready", "data32,error,saturated", "G_CTRL")],
            "functions": {"0": {"name": "SiLU", "input_F": 10, "ungated_output_F": 10, "gated_output_F": 10},
                          "1": {"name": "Sigmoid", "input_F": 10, "ungated_output_F": 14, "gated_output_F": 10},
                          "2": {"name": "GELU_tanh", "input_F": 10, "ungated_output_F": 10, "gated_output_F": 10},
                          "3": {"name": "Softplus", "input_F": 10, "ungated_output_F": 10, "gated_output_F": 10}},
            "gated_contract": "Apply activation to x, then if gated multiply by gate S16Q10; RNE14 for Sigmoid, RNE10 otherwise; final S16 saturation. gate is ignored mathematically when gated0.",
            "lane_contract": "Two S16 lanes/32bit; no count/mask, no per-lane ready; unused tail must be padded and ignored externally",
            "pipeline": "Four stages, II1 only when output advances; valid/error/fn-kind/gated bookkeeping travels with pipeline",
            "invalid_operation": "fn4..7 still travel through pipeline; out_error1,data0,saturated0",
            "visibility_commit_release": "No command-index/result-bank/commit. Each accepted input produces one ordered output; consume only with out_valid.",
            "cancel_reset": "No selective cancel. Stop new inputs and drain, or coordinated reset drops all in-flight valids and output; payload stages are not generally reset.",
            "trace_ids": ["G_PORTS", "G_READY", "G_FUNCTION", "G_PIPE_RESET"]}


def r_semantics():
    return {
        "owner": "R_CTRL", "count_port": False,
        "request_acceptance": "cmd_valid&&cmd_ready; cmd_ready=!reset&&phase==IDLE&&(!rsp_valid||rsp_ready)",
        "response_acceptance": "rsp_valid&&rsp_ready; held; no rsp_saturated port",
        "busy_meaning": "!cmd_ready; pending candidates can exist while busy0",
        "channels": [channel("command", "cmd_valid", "cmd_ready", "cmd_valid&&cmd_ready", "op4,index10,data128", "R_CTRL"), channel("response", "rsp_valid", "rsp_ready", "rsp_valid&&rsp_ready", "data128,error", "R_CTRL")],
        "identity": {"native_width_bits": 32, "open": "owner[40:9],epoch[72:41],position[104:73]", "exec": "mode[1:0],owner[33:2],epoch[65:34],position[97:66]", "commit": "owner[31:0],epoch[63:32],position[95:64],next_position[127:96]", "enforced_on": ["EXEC", "COMMIT"], "not_enforced_on": "other load/read/revoke commands; outside unique owner must enforce their permissions"},
        "formats": {"state_x_inject_output_history": "S32 common product-declared F", "key_query_taps": "S16 Q1.14; names key/query also serve B/C coefficients", "decay_beta_element_decay": "U32Q1.31 restricted0..0x80000000", "skip": "S32Q16.16", "capacity": "two2048xS32 banks; one active8KiB and one shadow8KiB; length1..256 rows x8 lanes; shadow also holds SSM factors"},
        "operations": {
            "0": op("OPEN", "length1..256 && data[127:105]==0 && !pending_state&&!pending_history", "length=data[8:0]; owner/epoch/position as identity.open", "ACK:data0", "Create context, clear operand-valid/output flags; does not clear payload banks or failed flag explicitly", "R_OPEN_LOAD", ["cmd_index"]),
            "1": op("LOAD_ACTIVE_STATE", "context_valid && index<2*length && !pending_state&&!pending_history", "4xS32 per128; index=state half-row", "ACK:data0", "Write active bank; active_valid[index]=1", "R_OPEN_LOAD"),
            "2": op("LOAD_KEY", "context_valid && index<=31 && !pending_state", "8xS16 key Q14 per128", "ACK:data0", "key_valid block set; pending_history alone does not prohibit this load", "R_OPEN_LOAD"),
            "3": op("LOAD_QUERY", "context_valid && index<=31 && !pending_state", "8xS16 query Q14 per128", "ACK:data0", "query_valid block set", "R_OPEN_LOAD"),
            "4": op("LOAD_X_OR_INJECT", "context_valid && index<=3 && !pending_state", "index0/1=4S32 x; index2/3=4S32 inject", "ACK:data0", "x_valid[index] set; inject is supplied algorithm quantity, not computed by packing", "R_OPEN_LOAD"),
            "5": op("LOAD_PARAMETERS", "context_valid&&!pending_state&&index<=2; index0 upper64zero and bothUQ31<=0x80000000", "index0:decay[31:0],beta[63:32]; index1/2:4xS32 skipQ16.16", "ACK:data0", "index0 param_valid; index1/2 skip_valid", "R_OPEN_LOAD"),
            "6": op("EXEC", "context_valid&&!pending_state; upper127:98zero; exactowner/epoch/position; mode<=2; per-mode loaded guards", "data identity.exec; mode0=GDN,1=SSM,2=conv", "ACK:data0,error=arithmetic failed; actual output fetched byop12", "On success output_valid1; mode2 pending_history1,mode0/1 pending_state1. Output is readable BEFORE commit; active state/history remain uncommitted candidates", "R_EXEC_COMMIT", ["cmd_index"]),
            "7": op("COMMIT", "context_valid && (pending_state||pending_history) && exactowner/epoch/position && epoch!=0xffffffff", "data identity.commit", "ACK:data0 after COPY has published state/history/epoch", "Accepted COMMIT entersCOPY withrsp_valid0,cmd_ready0; cannot be interrupted byop8. COPY swaps active/shadow if pending_state,copies candidatehistory if pending_history,increments epoch,sets caller next_position,clears pending/x_valid/output_valid; laterop8 cannot rollback thatcommit", "R_EXEC_COMMIT", ["cmd_index"]),
            "8": op("REVOKE_CANDIDATES", "No extra native guard beyond cmd_ready", "none", "ACK:data0", "Clear pending_state,pending_history,output_valid,decay_valid; preserve active state/history and owner/epoch/context; no native identity comparison", "R_REVOKE", ["cmd_index", "cmd_data"]),
            "9": op("LOAD_HISTORY", "context_valid&&index<=5&&!pending_history&&!pending_state", "4xS32 per128,6 chunks=3 history rows x8", "ACK:data0", "history_valid[index] set", "R_READ_LOAD"),
            "10": op("LOAD_TAPS", "context_valid&&index<=3&&!pending_history&&!pending_state", "8xS16 Q14 per128;4 blocks=4taps x8", "ACK:data0", "tap_valid[index] set", "R_READ_LOAD"),
            "11": op("READ_ACTIVE_STATE", "context_valid&&index<2*length&&active_valid[index]", "index selects4xS32", "payload:4xS32 active state", "Not shadow/candidate; no release", "R_READ_LOAD", ["cmd_data"]),
            "12": op("READ_CANDIDATE_OUTPUT", "output_valid&&index<=1", "index selects4 of8 S32 outputs", "payload:4xS32 output; valid beforecommit", "Read does not commit; commit/revoke/nextEXEC/OPEN/reset can clear output_valid", "R_READ_LOAD", ["cmd_data"]),
            "13": op("READ_META", "No extra native guard beyond cmd_ready", "none", "record128:length[8:0],pending_state9,pending_history10,output_valid11,zero[31:12],owner[63:32],epoch[95:64],position[127:96]", "Read metadata even when no context; no release", "R_READ_LOAD", ["cmd_index", "cmd_data"]),
            "14": op("READ_ACTIVE_HISTORY", "context_valid&&index<=5&&history_valid[index]", "index selects4S32", "payload:4xS32 committed/history input", "Not history_next candidate; no release", "R_READ_LOAD", ["cmd_data"]),
            "15": op("LOAD_SSM_DECAY", "context_valid&&index<2*length&&!pending_state&&!pending_history && eachU32<=0x80000000", "4xUQ1.31 factors in128", "ACK:data0", "Write shadow bank reused for factors; decay_valid[index] set; reload after eachSSM state step", "R_OPEN_LOAD")},
        "exec_mode_guards": {"0": "loaded all active halves,all key/query blocks,param_valid,x_valid[1:0]==3; pending_history allowed",
                             "1": "mode0 loaded guards plus all decay factors,x_valid==15,skip_valid==3; param_valid still required natively even though scalar coefficients not used in same manner",
                             "2": "!pending_history,x_valid[1:0]==3,tap_valid==15,history_valid==63; no active/key/param load requirement"},
        "commit_barrier": {"acceptance": "op7 cmd_valid&&cmd_ready after nativeguard passes",
                           "during_COPY": "phase!=IDLE meanscmd_ready0 andrsp_valid0; op8 cannot be accepted tointerruptCOPY",
                           "publication": "COPY edge updatesactive/history/epoch thenraises successfulACK; published state exists beforeACK consumption",
                           "post_commit_revoke_rolls_back": False,
                           "trace_ids": ["R_READY", "R_EXEC_COMMIT", "R_FINISH_COPY"]},
        "invalid_operation": "All4bit ops0..15 have meanings; failedguards return error1,data0 without that command action. Arithmetic overflow returns EXEC error,output invalid; no saturation flag.",
        "visibility_commit_release": ["EXEC writes shadow/history_next and output candidate; successful result can leave macro before local commit.", "R7 is local atomic bank-role/history publication, not full multi-tile/model version commit.", "A pending history candidate can survive a subsequent failed state calculation; outside policy must decide commit/revoke.", "New OPEN blocked while either candidate pending. RESUME pending_history for mode0/1 is distinct from opening a newcontext.", "Active/shadow are finite fixed storage; external version management does not increase native capacity."],
        "cancel_reset": "R8 only accepted when cmd_ready/IDLE, cannot interrupt arithmetic orCOPY after acceptedR7. COPY publishes active/history/epoch beforeCOMMIT ACK; laterR8 doesnotrollback committedstate. R8 revokes candidates without nativeidentity authentication; uniqueR_CTRL protectsaccess. Reset invalidatescontexts/flags anddropsinflightresponse; payloadarraysnotreset; reset isnot a commitrollbackAPI.",
        "trace_ids": ["R_PORTS", "R_READY", "R_FORMATS", "R_OPEN_LOAD", "R_EXEC_COMMIT", "R_REVOKE", "R_READ_LOAD", "R_FINISH_COPY", "R_RESET"]}


def s_semantics():
    return {"owner": "S_CTRL", "count_port": False,
            "request_acceptance": "ordinary req&&ready; loader load_valid&&load_ready are separate channels",
            "response_acceptance": "ordinary valid&&take; loader done_valid&&done_take separate; A/B independently valid&&ready",
            "busy_meaning": "feeder.busy only; does NOT cover ordinary pending valid or loader done_valid",
            "channels": [channel("ordinary_request", "req", "ready", "req&&ready", "wr1,addr10,din128", "S_CTRL"),
                         channel("ordinary_response", "valid", "take", "valid&&take", "dout128; write also responds", "S_CTRL"),
                         channel("loader_request", "load_valid", "load_ready", "load_valid&&load_ready", "bank1,rows4,tiles3,a/b_wide1,reuse_b1,a/b_base10", "S_CTRL"),
                         channel("loader_done", "done_valid", "done_take", "done_valid&&done_take", "done_error", "S_CTRL"),
                         channel("loader_A", "a_valid", "a_ready", "a_valid&&a_ready", "bank,row,tile,wide,A128", "M_NATIVE_READY", "Nominal M import; alternate export sink requires prebuilt route selection, never multiple direct drivers."),
                         channel("loader_B", "b_valid", "b_ready", "b_valid&&b_ready", "bank,tile,wide,half,B512", "M_NATIVE_READY", "Same selection rule as A; both branches must drain perdescriptor.")],
            "ordinary": {"capacity_bytes": 16384, "address": "1024 whole128bit words;bank=addr[1:0],row=addr[9:2]",
                         "acceptance": "ready=!reset&&(!valid||take)&&!wide_fire;wide_fire=wide_req&&wide_ready",
                         "read": "dout is selected pre-existing128bit word; no initialization-valid metadata",
                         "write": "memory changes on accepted write; response dout=din echo ACK, not old bytes; ACK must be consumed",
                         "response_holding": "one128bit ordinary and one512bit privatewide finite response; stable under respective stall",
                         "errors": "No rsp_error or bounds/initialization/error response; address bitwidth only; no byte write mask"},
            "loader": {"native_opcode": None, "descriptor": "parallel native fields, not packed64bit command",
                       "guard": "rows1..8,tiles1..4;bothbases4-wordaligned;a_base+tiles*(rows>4?8:4)<=1024; if!reuse_b,b_base+tiles*(b_wide?8:4)<=1024",
                       "A_layout": "per tile4words forrows<=4 else8words; one128bit container perA row evenS8",
                       "B_layout": "per tile4wordsS8 or8wordsS16; n-major8*n+k; S16 half0 thenhalf1",
                       "queues_bytes": 192, "outstanding_private_reads": 1,
                       "ready": "load_ready=!reset&&!busy&&!done_valid; cannot accept newload on same edge olddone taken",
                       "completion": "invalid descriptor:done_error1 withoutbusy; valid:done only after requests_done&&!pending&&Aqueueempty&&!Bvalid; allA/B delivered",
                       "completion_is_compute_done": False,
                       "reuse_b": "Skips B reads; no native validation of weight identity/version already inM. Outside owner proves bank/tile/format/version."},
            "internal_arbitration": "wide private read consumes all4 real1RW banks and suppresses ordinary ready for thatacceptedwide cycle; not extra external512bit RAM/DMA ports; no general arbitrary-master arbiter",
            "visibility_commit_release": ["Ordinary write visible in storage on acceptance; response ACK still owns finite response slot until take.", "Loader internalqueues not complete descriptor storage. Same-S serial generic export may need additional1024B capture before done and ordinary writeback; this is not implemented.", "S top instantiates storage+feeder only, not M; nativeA/B port compatibility is not v2 combined system acceptance."],
            "cancel_reset": "No ordinary rollback or loader abort. Loader must drain allA/B and done or coordinatedreset. Reset clears finite response/feeder valids, not payload storage; coordinate consumers/bank-valid tracking for partial deliveries.",
            "trace_ids": ["S_PORTS_INTERNAL", "S_ORDINARY", "S_LOADER_PORTS", "S_LOADER_GUARD", "S_LOADER_DONE"]}


def t_semantics():
    return {"owner": "T_CTRL", "count_port": False,
            "request_acceptance": "Separate phase-specific valid/ready channels; no cmd_op or generic command/rsp interface",
            "response_acceptance": "Only read_valid&&read_take is payload consumption; lifecycle events are port handshakes/stateobservations",
            "channels": [channel("BEGIN", "begin_valid", "begin_ready", "begin_valid&&begin_ready", "owner2,generation32,words10", "T_CTRL"),
                         channel("WRITE", "write_valid", "write_ready", "write_valid&&write_ready", "index10,data128", "T_CTRL"),
                         channel("COMMIT", "commit_valid", "commit_ready", "commit_valid&&commit_ready", "none", "T_CTRL"),
                         channel("REVOKE", "revoke_valid", "revoke_ready", "revoke_valid&&revoke_ready", "none", "T_CTRL"),
                         channel("READ", "read_valid", "read_take", "read_valid&&read_take", "index10,data128,last1", "T_CTRL"),
                         channel("RELEASE", "release_valid", "release_ready", "release_valid&&release_ready", "none", "T_CTRL")],
            "identity": {"owner_bits": 2, "generation_bits": 32, "native_authentication": False,
                         "meaning": "BEGIN records metadata; subsequent ports have noidentity and do not authenticate owner/generation; one outside owner enforceslease"},
            "payload": "384x128=6144B opaque wholewords; no numeric operation/format conversion",
            "states": {"0": "EMPTY", "1": "FILL", "2": "SEALED", "3": "READ_REQ", "4": "READ_HOLD", "5": "RELEASE"},
            "phase_guards": {"BEGIN": "EMPTY && words1..384", "WRITE": "FILL&&!revoke_valid&&write_index==received; muststart0 and advancecontiguously",
                             "COMMIT": "SEALED&&!revoke_valid", "REVOKE": "FILL||SEALED", "READ": "READ_HOLD", "RELEASE": "state==RELEASE"},
            "responses": {"commit_error": False, "generic_rsp": False, "sealed": "state==SEALED&&!reset", "committed": "READ_REQ||READ_HOLD||RELEASE,resetmasked", "busy": "state!=EMPTY; not resetmasked"},
            "errors": "Sticky protocol_error only untilreset: invalid BEGIN size whenEMPTY or wrongWRITE index whenFILL&&!revoke_valid; other premature lifecycle valids may simply nothandshake, not universally diagnosed",
            "visibility_commit_release": ["WRITE changes provisional storage onaccept; final expected write automatically SEALED.", "COMMIT handshake moves to READ_REQ; first payload needs startup cycle; READ_HOLD consumption edge refillsnextword so steadyII1.", "Read data/index/last stable under stall; no randomread/rewind. Finaltake enters RELEASE; does not free T automatically.", "RELEASE handshake enters EMPTY; owner/generation/count metadata retained, not authorization.", "Single native consumerlease; fork needs externalcopies/refcounts/holding, never OR multiple take signals.", "Same physicalT new BEGIN waits fulloldbatch preservation and release; candidate max6144B S spool/control is additional system plan. DistinctT do not become jointly atomic."],
            "cancel_reset": "REVOKE onlyFILL/SEALED, prior tocommit; commit/read/release states cannot revoke. Reset clears lease/control/error, not RAM; coordinated hardreset required whenconsumer/fabric resets. No independent perwordcancel.",
            "trace_ids": ["T_PORTS", "T_GUARDS", "T_LIFECYCLE", "T_RESET"]}


TRACE_RANGES = {
    "M_PORTS": (TOPS["M"][0], 5, 15), "M_READY": (TOPS["M"][0], 38, 46),
    "M_DESC": (TOPS["M"][0], 48, 62), "M_FORMAT": (TOPS["M"][0], 105, 122),
    "M_EXEC": (TOPS["M"][0], 184, 193), "M_READ_OPS": (TOPS["M"][0], 197, 248), "M_RESET": (TOPS["M"][0], 129, 137),
    "N_PORTS": (TOPS["N"][0], 3, 9), "N_READY": (TOPS["N"][0], 54, 55),
    "N_GUARDS": (TOPS["N"][0], 84, 100), "N_DISPATCH": (TOPS["N"][0], 134, 164),
    "N_EXP": (TOPS["N"][0], 168, 189), "N_FACTOR": (TOPS["N"][0], 145, 201),
    "N_REPLAY": (TOPS["N"][0], 203, 220), "N_TOPK": (TOPS["N"][0], 222, 232), "N_RESET": (TOPS["N"][0], 126, 132),
    "E_PORTS": (TOPS["E"][0], 5, 11), "E_READY": (TOPS["E"][0], 25, 25),
    "E_ROUND_PACK": (TOPS["E"][0], 26, 43), "E_EXEC": (TOPS["E"][0], 49, 88), "E_RESET": (TOPS["E"][0], 45, 48),
    "G_PORTS": (TOPS["G"][0], 3, 9), "G_READY": (TOPS["G"][0], 11, 12),
    "G_FUNCTION": (TOPS["G"][0], 39, 67), "G_PIPE_RESET": (TOPS["G"][0], 69, 84),
    "R_PORTS": (TOPS["R"][0], 4, 9), "R_READY": (TOPS["R"][0], 46, 47), "R_FORMATS": (TOPS["R"][0], 1, 3),
    "R_OPEN_LOAD": (TOPS["R"][0], 112, 139), "R_EXEC_COMMIT": (TOPS["R"][0], 141, 160),
    "R_REVOKE": (TOPS["R"][0], 162, 162), "R_READ_LOAD": (TOPS["R"][0], 163, 183),
    "R_FINISH_COPY": (TOPS["R"][0], 249, 262), "R_RESET": (TOPS["R"][0], 98, 108),
    "S_PORTS_INTERNAL": (TOPS["S"][0], 4, 30), "S_ORDINARY": (S_STORE, 11, 37),
    "S_LOADER_PORTS": (S_LOADER, 6, 21), "S_LOADER_GUARD": (S_LOADER, 31, 59), "S_LOADER_DONE": (S_LOADER, 67, 108),
    "S_STORE_RESET": (S_STORE, 19, 23), "S_LOADER_RESET": (S_LOADER, 60, 66),
    "T_PORTS": (TOPS["T"][0], 4, 21), "T_GUARDS": (TOPS["T"][0], 27, 40), "T_LIFECYCLE": (TOPS["T"][0], 46, 69),
    "T_RESET": (TOPS["T"][0], 41, 44), "T_COORDINATED_RESET": (TOPS["T"][0], 1, 3)
}


# Exact source fragments whose interpretation is easy to get wrong. These are
# checked as source anchors as well as the frozen whole-file hashes.
SOURCE_ANCHORS = {
    "M3_S64": (TOPS["M"][0], "3:if(merged_valid[cmd_index[5:3]]&&cmd_index[2:0]<4&&cmd_data==0)"),
    "M5_carrier32": (TOPS["M"][0], "formatted[32*l+:32]=value[31:0];"),
    "M_exec_status": (TOPS["M"][0], "DRAIN:if(committed==rows)respond({120'd0,fault_rows},|fault_rows,0);"),
    "M_clear_keeps_scale": (TOPS["M"][0], "av<=0;for(i=0;i<8;i=i+1)bv[i]<=0;merged_valid<=0;partial_valid<=0;respond(0,0,0);"),
    "N3_score_not_exp": (TOPS["N"][0], "ex[l]<=exponential($signed({fetch[l][15],fetch[l]})-$signed({maximum[15],maximum}));"),
    "N6_unsigned_EXP": (TOPS["N"][0], "assign norm_operand[l]=operation==6?$signed({1'b0,raw[l]}):$signed({raw[l][15],raw[l]});"),
    "N6_no_gamma": (TOPS["N"][0], "for(integer l=0;l<2;l=l+1)gate_product[l]<=operation==6?$signed({{16{norm_product[l][47]}},norm_product[l]}):normalized_gate[l];"),
    "N_begin_no_TopK_clear": (TOPS["N"][0], "count<=0;sum<=0;sumsq<=0;maximum<=-32768;minimum<=32767;exp_sum<=0;exp_count<=0;replayed<=0;rsp_valid<=1;"),
    "E12_bytes": (TOPS["E"][0], "packed_result[8*j+:8]=rounded[7:0];"),
    "E13_four_values": (TOPS["E"][0], "13:total[i]<=i<4?{{16{a[2*(i&3)+1][15]}},a[2*(i&3)+1],a[2*(i&3)]}:48'sd0;"),
    "G_fn_error": (TOPS["G"][0], "e1<=in_fn>3;e2<=e1;e3<=e2;out_error<=e3;"),
    "G_gated_frac": (TOPS["G"][0], "rounded=g3?rne(product3[l],sig3?5'd14:5'd10):$signed({{16{f3[l][15]}},f3[l]});"),
    "R32_identity": (TOPS["R"][0], "reg [31:0] owner,epoch,position,decay,beta,next_position;"),
    "R_candidate_before_commit": (TOPS["R"][0], "if(!failed)begin if(mode==2)pending_history<=1;else pending_state<=1;end"),
    "R_revoke_no_identity": (TOPS["R"][0], "8:begin pending_state<=0;pending_history<=0;output_valid<=0;decay_valid<=0;end"),
    "S_write_echo": (S_STORE, "if(wr)dout<=din;"),
    "S_busy_from_feeder": (TOPS["S"][0], ".done_valid(done_valid),.done_take(done_take),.done_error(done_error),.busy(busy),"),
    "S_done_drains_both": (S_LOADER, "if(busy&&requests_done&&!pending&&count==0&&!weight_valid)begin"),
    "T_II1_refill": (TOPS["T"][0], "else begin cursor <= cursor + 1; held <= payload[cursor+1]; end"),
    "T_no_auto_release": (TOPS["T"][0], "if (cursor + 1 == word_count) state <= RELEASE;")
}


def port_owner(macro, port):
    if port["direction"] != "input":
        return "NATIVE_" + macro
    name = port["name"]
    if name in ("clk", "reset"):
        return "FABRIC_CLOCK_RESET"
    if macro == "M" and name.startswith(("a_", "b_")):
        return "S_LOADER"
    if macro == "S" and name in ("a_ready", "b_ready"):
        return "M_NATIVE_READY_OR_PREBUILT_EXPORT_SELECTION"
    return macro + "_CTRL"


def build_contract(root):
    root = Path(root)
    old = read_json(root / "work/Melodydt/151/rtl-derived-contract.json")
    baseline = read_json(root / "work/Melodydt/151/rtl-baseline.json")
    if baseline["source_commit"] != FREEZE or len(baseline["core_files"]) != 14:
        raise ValueError("This contract requires the existing643c fourteen-file freeze")
    provenance = []
    for item in baseline["core_files"]:
        path = root / item["path"]
        if sha(path) != item["sha256"]:
            raise ValueError("Frozen source drift: " + item["path"])
        provenance.append({"path": item["path"], "sha256": sha(path),
                           "bytes": len(path.read_bytes()), "git_blob_sha": item["git_blob_sha"]})
    semantics = {"M": m_semantics(), "N": n_semantics(), "E": e_semantics(),
                 "G": g_semantics(), "R": r_semantics(), "S": s_semantics(), "T": t_semantics()}
    # An operation's trace should show its gate/dispatch as well as its datapath.
    for definition in semantics["N"]["operations"].values():
        definition["trace_ids"] = sorted(set(definition["trace_ids"] + ["N_GUARDS", "N_DISPATCH"]))
    semantics["N"]["operations"]["1"]["trace_ids"].append("N_EXP")
    semantics["M"]["operations"]["10"]["trace_ids"] += ["M_DESC", "M_READ_OPS"]
    semantics["M"]["operations"]["5"]["trace_ids"].append("M_READ_OPS")
    for code in ("6", "7"):
        semantics["R"]["operations"][code]["trace_ids"].append("R_FINISH_COPY")
    semantics["S"]["trace_ids"] += ["S_STORE_RESET", "S_LOADER_RESET"]
    semantics["T"]["trace_ids"].append("T_COORDINATED_RESET")
    ports_total = 0
    for macro, (path, module) in TOPS.items():
        text = (root / path).read_text(encoding="utf-8")
        ports = parse_ports(text, module)
        old_ports = parse_ports("module " + module + "(" + old["interfaces"][macro]["ansi_header_normalized"] + ");", module)
        if port_signature(ports) != port_signature(old_ports):
            raise ValueError("Prior derived interface mismatch: " + macro)
        sequential_sources = [S_STORE, S_LOADER] if macro == "S" else [path]
        for sequential_path in sequential_sources:
            sequential_text = (root / sequential_path).read_text(encoding="utf-8")
            if "always @(posedge clk)" not in sequential_text or "negedge" in sequential_text:
                raise ValueError("Review changed clock/reset structure: " + macro)
        for port in ports:
            port["unique_driving_owner_contract"] = port_owner(macro, port)
        semantics[macro].update({"module": module, "path": path, "sha256": sha(root / path),
                                 "ports": ports,
                                 "clock_reset": {"clock": "posedge clk", "reset": "active-high synchronous; affects logic only onclockedge",
                                                 "native_CDC": False, "frequency_qualified_by_this_contract": False,
                                                 "integration_rule": "Common synchronous domain or separately designed verified CDC; reset cancellation coordinated with owners/consumers"}})
        ports_total += len(ports)
    anchors = {}
    for name, (path, literal) in SOURCE_ANCHORS.items():
        text = (root / path).read_text(encoding="utf-8")
        if literal not in text:
            raise ValueError("Missing semantic source anchor: " + name)
        anchors[name] = {"path": path, "line": text[:text.index(literal)].count("\n") + 1,
                         "literal": literal, "source_commit": FREEZE}
    contract = {
        "schema_version": 1, "issue": 151, "PR": 152,
        "research_revision": "343f4d4", "leaf_source_commit": FREEZE,
        "status": "PHASE1_NATIVE_CONTRACT_CANDIDATE_NOT_COMMON_BASE_FREEZE",
        "scope": {"role_metadata": "compile-time semantic proof, no universal runtime role tags required",
                  "M1_M10": "finite capability union must include all active control/mux/storage/arithmetic/clock/reset needed by products",
                  "M11_M12": "permanent binding of existing routes/program entry/parameters; cannot fabricate active logic",
                  "system_has_external_memory": True, "external_memory_this_phase": "not implemented or assessed; flexibility preserved",
                  "new_system_RTL_implemented": False, "RTL_combination_verified": False,
                  "physical_qualified": False, "common_base_frozen": False,
                  "latest_upstream_auto_imported": False},
        "external_owners_status": "proposed integration contract, not instantiated controllers; nativeR identity checks are distinct from port ownership",
        "general_rules": ["Only sample inputs on their legal handshake; keep unaccepted input valid/payload stable as required by composed protocol.",
                          "During reset suppress/count no transaction events; synchronous reset wins on its clock edge, and owners/consumers must reset or invalidate context consistently.",
                          "Only consume output when nativevalid. S/T payload bytes without validity/context may be stale; no implicit zero-initialized RAM.",
                          "Unique outside driver for each input; multiple push-pull outputs never metal-short even when valids are disjoint; prebuild MUX/selection if shared.",
                          "No common numeric128 schema: element types, counts, record fields, units and lineage are statically bound peroperation.",
                          "Canonical unused fields may be set0 by externalowner; ignored nativefields are not claimed to be RTL illegal.",
                          "Response-accepted, data-visible, localcommit, resource-release and full-model commit are separate events."],
        "source_provenance": provenance,
        "source_input_contracts": [{"path": "work/Melodydt/151/rtl-derived-contract.json", "sha256": sha(root / "work/Melodydt/151/rtl-derived-contract.json")},
                                   {"path": "work/Melodydt/151/rtl-baseline.json", "sha256": sha(root / "work/Melodydt/151/rtl-baseline.json")}],
        "source_traces": {key: trace(root, *value) for key, value in TRACE_RANGES.items()},
        "source_anchors": anchors, "macros": semantics,
        "summary": {"macro_count": 7, "top_port_count": ports_total,
                    "per_macro_port_count": {m: len(v["ports"]) for m, v in semantics.items()},
                    "frozen_core_files_checked": 14,
                    "semantic_source_anchors_checked": len(anchors),
                    "new_system_RTL_modules": 0, "RTL_simulations_performed": 0,
                    "physical_experiments_performed": 0},
        "limitations": ["Static byte/interface/source-trace checks do not prove temporal protocol implementation or numerical quality.",
                        "This phase contracts seven native endpoints; it does not instantiate a seven-macro top, unified transport, controller ROM or all legal routes.",
                        "The retained R implementation's final qualification is independent; no old4032 physical qualification is transferred.",
                        "No remote state, simulator, server, physical data or ref-project is changed by this tool."]}
    return contract


def port_inventory(contract):
    """Human-readable mechanically derived appendix; each port still has JSON trace."""
    lines = ["# 七顶层端口机械清单", "", "由固定643c RTL的ANSI header解析；方向相对于宏。owner为集成契约，尚未实例化。", ""]
    for macro, item in contract["macros"].items():
        lines += ["## " + macro + " — " + item["module"], "", "| 端口 | 方向 | 位宽 | 外侧/原生唯一驱动约束 | 源码行 |", "|---|---|---:|---|---:|"]
        for port in item["ports"]:
            lines.append("| `%s` | %s | %s | %s | %s |" % (port["name"], port["direction"], port["width"], port["unique_driving_owner_contract"], port["declaration_line"]))
        lines.append("")
    return "\n".join(lines) + "\n"


def contract_errors(root, contract):
    """Validate whole generated contract against fixed sources and canonical rules."""
    expected = build_contract(root)
    errors = []
    if contract != expected:
        for key in expected:
            if contract.get(key) != expected[key]:
                errors.append("CONTRACT_MISMATCH:" + key)
        for key in set(contract) - set(expected):
            errors.append("UNEXPECTED_FIELD:" + key)
    return errors


def negative_probes(root, contract):
    """Each mutation represents a consequential documentation/interface failure."""
    cases = [
        ("M_response_width", lambda x: next(p for p in x["macros"]["M"]["ports"] if p["name"] == "rsp_data").update({"width": 64})),
        ("M_EXEC_as_payload", lambda x: x["macros"]["M"]["operations"]["10"].update({"response": "matrix payload"})),
        ("N3_as_N6", lambda x: x["macros"]["N"]["operations"]["3"].update({"input_schema": "EXP codes"})),
        ("E_has_count", lambda x: x["macros"]["E"].update({"count_port": True})),
        ("G_sigmoid_gated_Q14", lambda x: x["macros"]["G"]["functions"]["1"].update({"gated_output_F": 14})),
        ("R_owner2_not32", lambda x: x["macros"]["R"]["identity"].update({"native_width_bits": 2})),
        ("R_revoke_after_commit_rollback", lambda x: x["macros"]["R"]["commit_barrier"].update({"post_commit_revoke_rolls_back": True})),
        ("S_busy_as_whole_macro", lambda x: x["macros"]["S"].update({"busy_meaning": "allrequestscomplete"})),
        ("T_invented_commit_error", lambda x: x["macros"]["T"]["responses"].update({"commit_error": True})),
        ("freeze_claim", lambda x: x["scope"].update({"common_base_frozen": True})),
        ("missing_source_trace", lambda x: x["source_traces"].pop("R_REVOKE"))]
    result = []
    for name, mutate in cases:
        altered = copy.deepcopy(contract)
        mutate(altered)
        errors = contract_errors(root, altered)
        result.append({"id": name, "rejected": bool(errors), "errors": errors})
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", required=True, help="read-only integrated source package")
    ap.add_argument("--output-dir", required=True, help="isolated draft/output directory")
    ap.add_argument("--check", help="check an existing generated contract instead of replacing it")
    args = ap.parse_args()
    root, out = Path(args.root), Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    if args.check:
        contract = read_json(args.check)
        errors = contract_errors(root, contract)
        if errors:
            print(json.dumps({"result": "FAIL", "errors": errors}))
            return 1
    else:
        contract = build_contract(root)
        write_json(out / "phase1-native-contract.json", contract)
        (out / "phase1-port-inventory.md").write_bytes(port_inventory(contract).encode("utf-8"))
    probes = negative_probes(root, contract)
    receipt = {"result": "PASS" if all(x["rejected"] for x in probes) else "FAIL",
               "scope": "static native source/interface/contract consistency only; not RTL simulation",
               "summary": contract["summary"], "positive_contract_check": "PASS",
               "negative_contract_mutations": probes,
               "tool_sha256": sha(Path(__file__)), "contract_sha256": hashlib.sha256((json.dumps(contract, ensure_ascii=False, indent=2) + "\n").encode("utf-8")).hexdigest(),
               "inputs": contract["source_provenance"],
               "not_executed": ["RTL simulation", "numeric/model acceptance", "P&R", "remote synchronization"]}
    write_json(out / "phase1-native-checks.json", receipt)
    print(json.dumps({"result": receipt["result"], "summary": contract["summary"],
                      "negative_cases_rejected": sum(int(x["rejected"]) for x in probes)}))
    return 0 if receipt["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
