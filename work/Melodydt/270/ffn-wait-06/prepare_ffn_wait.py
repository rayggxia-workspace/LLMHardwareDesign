"""Add simulation-only FFN wait tracing to the sealed C639 fixture."""

import argparse
from pathlib import Path

from prepare_native_probe import replace_once


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    args = parser.parse_args()
    project = args.source / "project"
    exp = project / "experiments/block_local_native"
    replace_once(
        project / "experiments/shared_x_control/rtl/p_native_weight_overlap_candidate.sv",
        "\nendmodule\n",
        "\n`ifndef SYNTHESIS\n" + r""" // Simulation-only trace of the exact controller readiness gates.
 integer wait_probe_class, wait_probe_previous;
 time wait_probe_start;
 logic [127:0] wait_probe_owner;
 always_comb begin
  wait_probe_class=0;
  if(scope_live) begin
   case(state)
    FILL_WAIT: begin
     if(!pair_prep_second&&pair_candidate&&maximum_W_generation<W_GENERATION_LIMIT&&next_session<SESSION_LIMIT-32'd8)
      wait_probe_class=12;
     else if(!(pair_prep_second?saved_fill_seen:fill_seen))
      wait_probe_class=A_loaded[selected_A_slot]&&current_load_shift<=17 ? 1 : 3;
     else if(!A_loaded[selected_A_slot]||current_load_shift>17)
      wait_probe_class=2;
     else wait_probe_class=12;
    end
    W_JOIN:wait_probe_class=4;
    EXEC_PUSH:wait_probe_class=5;
    EXEC_ISSUE:wait_probe_class=6;
    EXEC_WAIT:wait_probe_class=7;
    BEGIN_SEND,BEGIN_WAIT,CTX_PUSH,CTX_ISSUE,CTX_WAIT,ALLOC_SEND,ALLOC_WAIT,
      FENCE_SEND,FENCE_WAIT,FENCE_REARM:wait_probe_class=8;
    A_CLOSE,A_RELEASE:wait_probe_class=9;
    IDLE:wait_probe_class=front_record_valid&&front_record_A_first&&!first_window_match ? 10 : 11;
    PAIR_ACCEPT_SECOND:wait_probe_class=12;
    default:wait_probe_class=11;
   endcase
  end
 end
 always @(posedge clk) begin : ffn_wait_probe
  if(reset) begin
   wait_probe_previous<=0;
   wait_probe_start<=0;
   wait_probe_owner<='0;
  end else if($test$plusargs("FFN_WAIT_PROBE")) begin
   if(wait_probe_class!=wait_probe_previous||owner!=wait_probe_owner) begin
    if(wait_probe_previous!=0)
     $display("FFN_LC %m %h %0d %0d %0d",wait_probe_owner,wait_probe_previous,wait_probe_start,$time);
    wait_probe_start<=$time;
    wait_probe_previous<=wait_probe_class;
    wait_probe_owner<=owner;
   end
   if(g_cmd_valid&&g_cmd_ready)
    $display("FFN_EXEC %m %h offer %0d %0d %0d",owner,seq_id,next_session,$time);
   if(complete_valid&&complete_ready&&!complete_error)
    $display("FFN_EXEC %m %h complete %0d 0 %0d",owner,complete_sequence,$time);
  end
 end""" + "\n`endif\nendmodule\n",
    )
    replace_once(
        exp / "test_ffn_three_p_native.sv",
        "  assign project_ready[p]=",
        r"""
  always @(posedge clk) begin : ffn_scope_probe
   if(!reset&&$test$plusargs("FFN_WAIT_PROBE")) begin
    if(local_offer&&lc_call[p]&&scope_available)
     $display("FFN_SCOPE call %h %0d %0d %0d",execution_owner,p,
              down_phase ? 58+int'(down_index) : stripe_index,$time);
    if(node_done&&raw_take)
     $display("FFN_SCOPE raw %h %0d %0d %0d",raw_owner,p,
              down_phase ? 58+int'(down_index) : stripe_index,$time);
    if(lc_done[p]&&lc_done_ready[p])
     $display("FFN_SCOPE lc %h %0d %0d %0d",returned_owner,p,
              down_phase ? 58+int'(down_index) : stripe_index,$time);
   end
  end""" + "\n  assign project_ready[p]=",
    )
    replace_once(
        exp / "test_native_decode638_product_replay.sv",
        "    wire unused_ffn_commit=",
        r"""
    always @(posedge clk) begin : ffn_mc_wait_probe
        if (!reset && parallel_ffn && $test$plusargs("FFN_WAIT_PROBE") &&
            controller.cohort.mother.trace_retire_o &&
            controller.cohort.mother.trace_opcode_o == 8'h11)
            $display("FFN_WAIT %0d %0d %0d",
                     generation,controller.cohort.mother.trace_pc_o,$time);
    end""" + "\n    wire unused_ffn_commit=",
    )
    replace_once(
        exp / "run_decode638_q_tile_replay.sh",
        '"+FFN_WEIGHT_PROBE"',
        '"+FFN_WEIGHT_PROBE" "+FFN_WAIT_PROBE"',
    )


if __name__ == "__main__":
    main()
