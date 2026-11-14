"""Observe the first Q COPY/LOAD and EXEC pair in the frozen 105530 replay."""

import argparse
from pathlib import Path

from instrument_qwen_105530 import instrument, replace_once


FRONT = "qkv_attention_datapath"
NODE = "p0.physical_node"
RANGE = NODE + ".exec"
EXEC = RANGE + ".early_exec.exec"
M = NODE + ".M"
CORE = M + ".native"
FIRST_WEIGHT = 5017600
SECOND_WEIGHT = 5035008
THIRD_WEIGHT = 5052416


def tap(kind, condition, **fields):
    template = " ".join(["QWEN_K0 " + kind, "ps=%0d", "cycle=%0d"]
                        + [field + "=%0d" for field in fields])
    values = ", ".join(["edge_ps", "core_cycle"] + list(fields.values()))
    return '                if ({})\n                    $display("{}", {});\n'.format(
        condition, template, values)


def observer():
    copy = [
        tap("copy_start", f"{FRONT}.copy_valid && {FRONT}.copy_ready"),
        tap("copy_read", f"{FRONT}.u_valid && {FRONT}.u_ready",
            address=f"{FRONT}.u_address", tag=f"{FRONT}.u_tag"),
        tap("copy_read_ack", f"{FRONT}.u_rsp && {FRONT}.u_rsp_ready", tag=f"{FRONT}.u_rsp_tag"),
        tap("copy_write", f"{NODE}.cp_valid && {NODE}.cp_ready",
            address=f"{NODE}.cp_address", tag=f"{NODE}.cp_tag"),
        tap("copy_ack", f"{NODE}.cp_ack_valid && {NODE}.cp_ack_ready", tag=f"{NODE}.cp_ack_tag"),
        tap("copy_done", f"{FRONT}.copy_done && {FRONT}.copy_take"),
        tap("a_load_read", f"{NODE}.ar_valid && {NODE}.ar_ready",
            address=f"{NODE}.ar_address", tag=f"{NODE}.ar_tag"),
        tap("a_load_ack", f"{NODE}.ar_rsp_valid && {NODE}.ar_rsp_ready", tag=f"{NODE}.ar_rsp_tag"),
        tap("a_load_proof", f"{FRONT}.proof_valid && {FRONT}.proof_take"),
        tap("lease_release", f"{FRONT}.lease_release"),
    ]
    execution = [
        tap("weight_fill_ack", f"{M}.tx_end && {M}.tx_source == 4'd2",
            sequence=f"{M}.tx_frame[95:64]", session=f"{M}.tx_frame[63:32]"),
        tap("guard_accept", f"{EXEC}.g_cmd_valid && {EXEC}.g_cmd_ready", sequence=f"{EXEC}.seq_id"),
        tap("exec_first_flit",
            f"{NODE}.lc_valid && {NODE}.lc_ready && {NODE}.lc_sop && {NODE}.lc_data[19:16] == 4'd3",
            sequence=f"{NODE}.lc_data[95:64]", session=f"{NODE}.lc_data[63:32]"),
        tap("exec_last_flit",
            f"{NODE}.lc_valid && {NODE}.lc_ready && {NODE}.lc_eop && qwen_pair_exec_packet",
            sequence="qwen_pair_sequence", session="qwen_pair_session"),
        tap("a_use", f"{EXEC}.issue_use_valid && {EXEC}.af_use_ready",
            sequence=f"{EXEC}.issue_use_record", session=f"{EXEC}.issue_use_session"),
        tap("m_exec_start", f"{M}.n_exec_valid && {M}.n_exec_ready",
            sequence=f"{M}.n_exec_record", session=f"{M}.session"),
        tap("first_operand", f"{NODE}.a_valid && {NODE}.a_ready && {NODE}.a_beat == 3'd0",
            session=f"{NODE}.a_session"),
        tap("last_operand", f"{NODE}.a_valid && {NODE}.a_ready && {NODE}.a_beat == 3'd7",
            session=f"{NODE}.a_session"),
        tap("raw_accept", f"{CORE}.raw_valid && {CORE}.raw_ready", sequence=f"{M}.A_record"),
        tap("input_eop", f"{M}.tx_end && {M}.tx_source == 4'd3",
            sequence=f"{M}.tx_frame[95:64]", session=f"{M}.tx_frame[63:32]"),
        tap("rf_offer", f"{M}.n_rsp_valid && !qwen_pair_rf_pending", sequence=f"{M}.n_rsp_record"),
        tap("rf_eop", f"{M}.tx_end && {M}.tx_source == 4'd4",
            sequence=f"{M}.tx_frame[95:64]", session=f"{M}.tx_frame[63:32]"),
        tap("guard_terminal", f"{EXEC}.g_terminal_valid && {EXEC}.g_terminal_ready",
            sequence=f"{EXEC}.g_terminal_ticket[63:32]", session=f"{EXEC}.g_terminal_ticket[31:0]"),
        tap("range_complete", f"{RANGE}.complete_valid && {RANGE}.complete_ready",
            sequence=f"{RANGE}.complete_sequence", context=f"{RANGE}.complete_context"),
    ]
    return f"""
    // Observe the same pre-NBA edge as the base QWEN_EDGE markers.
    bit qwen_pair_active, qwen_pair_seen, qwen_pair_exec_packet, qwen_pair_rf_pending;
    logic [31:0] qwen_pair_sequence, qwen_pair_session;
    always @(posedge clk) begin : qwen_observe_pair
        longint unsigned edge_ps, core_cycle;
        if (reset) begin
            qwen_pair_active <= 0;
            qwen_pair_seen <= 0;
            qwen_pair_exec_packet <= 0;
            qwen_pair_rf_pending <= 0;
            qwen_pair_sequence <= 0;
            qwen_pair_session <= 0;
        end else begin
            edge_ps = longint'($realtime/1ps);
            core_cycle = (edge_ps - 64'd55000)/64'd10000 + 1;
            if (!qwen_pair_seen && generation == 1 && provider_valid[0] && provider_ready[0] &&
                ticket[0] == 3 && provider_descriptor[0][31:0] == 32'h02505001) begin
                qwen_pair_seen <= 1;
                qwen_pair_active <= 1;
            end
            if (qwen_pair_active) begin
                if ({NODE}.lc_valid && {NODE}.lc_ready && {NODE}.lc_sop) begin
                    qwen_pair_exec_packet <= {NODE}.lc_data[19:16] == 4'd3;
                    qwen_pair_sequence <= {NODE}.lc_data[95:64];
                    qwen_pair_session <= {NODE}.lc_data[63:32];
                end
                qwen_pair_rf_pending <= {M}.n_rsp_valid && !{M}.n_rsp_ready;
{''.join(copy)}{''.join(execution)}
                if ({FRONT}.mr_valid && {FRONT}.mr_ready) begin
                    case ({FRONT}.mr_address)
                      64'd{FIRST_WEIGHT},64'd{SECOND_WEIGHT},64'd{THIRD_WEIGHT}:
                        $display("QWEN_K0 weight_offer ps=%0d cycle=%0d address=%0d tag=%0d beats=%0d channel=%0d",
                                 edge_ps,core_cycle,{FRONT}.mr_address,{FRONT}.mr_tag,
                                 {FRONT}.mr_length,{FRONT}.mr_channel);
                      default: begin end
                    endcase
                    if ({FRONT}.mr_address == 64'd{THIRD_WEIGHT}) begin
                        $display("QWEN_K0 third_weight_accept ps=%0d cycle=%0d address=%0d",
                                 edge_ps,core_cycle,{FRONT}.mr_address);
                        qwen_pair_active <= 0;
                        if ($test$plusargs("QWEN_K0_STOP")) begin
                            $display("QWEN_K0_STOP ps=%0d cycle=%0d address=%0d",
                                     edge_ps,core_cycle,{FRONT}.mr_address);
                            $finish;
                        end
                    end
                end
            end
        end
    end
"""


def instrument_pair(source):
    """Patch a fresh source extraction with the base and pair observations."""
    instrument(source)
    top = source / "project/experiments/block_local_native/test_native_decode638_product_replay.sv"
    original = top.read_bytes().decode("utf-8")
    ending = "\r\n" if "\r\n" in original else "\n"
    patched = replace_once(original, "endmodule", observer().replace("\n", ending) + "endmodule")
    top.write_bytes(patched.encode("utf-8"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    instrument_pair(parser.parse_args().source)


if __name__ == "__main__":
    main()
