"""Apply an older-record EXEC priority experiment to the pinned FFN RTL."""

import argparse
from pathlib import Path
from hashlib import sha256

from prepare_native_probe import replace_once


CONTROL = "project/experiments/shared_x_control/rtl/p_native_weight_overlap_candidate.sv"
CONTROL_SHA256 = "cfcb3f38ce261417213cbdedf79697fe7d5d502159ea914bda8d34d45c836c3d"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    args = parser.parse_args()
    path = args.source / CONTROL
    if sha256(path.read_bytes()).hexdigest() != CONTROL_SHA256:
        raise ValueError("expected the instrumented #270 WAIT baseline")
    replace_once(
        path,
        " wire selected_A_slot=k[7];",
        """ wire selected_A_slot=k[7];
 // A prepared replay can be paired immediately with no additional allocation.
 // Otherwise the current record can issue without accepting a younger owner.
 wire first_exec_eligible=fill_seen&&A_loaded[selected_A_slot]&&current_load_shift<=17;
 wire first_exec_preempts_pair=first_exec_eligible&&!replay_prepared;""",
    )
    replace_once(
        path,
        "state==PAIR_ACCEPT_SECOND&&!cancelled&&!scope_cancel&&pair_second_shape",
        "state==PAIR_ACCEPT_SECOND&&!first_exec_preempts_pair&&!cancelled&&!scope_cancel&&pair_second_shape",
    )
    replace_once(
        path,
        "else if(!pair_prep_second&&pair_candidate&&maximum_W_generation",
        "else if(!pair_prep_second&&!first_exec_preempts_pair&&pair_candidate&&maximum_W_generation",
    )
    replace_once(
        path,
        """         pair_hold_valid<=0;early_cancel_live<=1;early_cancel_seen<=0;early_drain_seen<=0;state<=EARLY_HALT;
       end else if(front_record_valid&&front_record_ready)begin
         pair_prep_second<=1;""",
        """         pair_hold_valid<=0;early_cancel_live<=1;early_cancel_seen<=0;early_drain_seen<=0;state<=EARLY_HALT;
       end else if(first_exec_preempts_pair)begin
         // The younger record has not transferred and retains its original owner.
         pair_hold_valid<=0;state<=W_JOIN;
       end else if(front_record_valid&&front_record_ready)begin
         pair_prep_second<=1;""",
    )
    # Preserve the monitor's classification of the actual first RTL branch.
    replace_once(
        path,
        "if(!pair_prep_second&&pair_candidate&&maximum_W_generation",
        "if(!pair_prep_second&&!first_exec_preempts_pair&&pair_candidate&&maximum_W_generation",
    )
    replace_once(
        path,
        "PAIR_ACCEPT_SECOND:wait_probe_class=12;",
        "PAIR_ACCEPT_SECOND:wait_probe_class=first_exec_preempts_pair ? 4 : 12;",
    )


if __name__ == "__main__":
    main()
