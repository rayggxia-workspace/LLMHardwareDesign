"""Check expected pairing and deliberate bypasses in the focused fixture."""

import argparse
from pathlib import Path

from prepare_native_probe import replace_once


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fixture", type=Path)
    args = parser.parse_args()
    path = args.fixture
    replace_once(
        path,
        " integer native_execs,drain_commands,cancel_error_count;",
        """ integer native_execs,drain_commands,cancel_error_count;
 integer priority_bypasses;
 always @(posedge clk) begin
  if(reset) priority_bypasses<=0;
  else if(case_id<2&&weight_overlap_provider.exec.first_exec_preempts_pair&&
          !scope_cancel&&!weight_overlap_provider.exec.cancelled&&
          (exec_state==5'd29||(exec_state==5'd8&&!weight_overlap_provider.exec.pair_prep_second&&
           weight_overlap_provider.exec.pair_candidate&&
           weight_overlap_provider.exec.maximum_W_generation<16'hffff&&
           weight_overlap_provider.exec.next_session<SESSION_LIMIT-32'd8))) begin
   assert(weight_overlap_provider.exec.fill_seen&&
          weight_overlap_provider.exec.A_loaded[weight_overlap_provider.exec.selected_A_slot]&&
          !weight_overlap_provider.exec.front_record_ready)
     else $fatal(1,"EXEC priority without matching A/W proof or after younger handshake");
   priority_bypasses<=priority_bypasses+1;
  end
 end""",
    )
    replace_once(
        path,
        "pair_detaches==32*GROUPS",
        "(pair_detaches>0&&priority_bypasses>0&&pair_detaches+priority_bypasses==32*GROUPS)",
    )
    replace_once(
        path,
        "  if(WEIGHT_PREFILL)assert",
        '  $display("EXEC_PRIORITY_ACCOUNTING pairs=%0d bypasses=%0d",pair_detaches,priority_bypasses);\n'
        "  if(WEIGHT_PREFILL)assert",
    )


if __name__ == "__main__":
    main()
