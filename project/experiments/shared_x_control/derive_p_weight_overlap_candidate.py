"""Independent candidate: issue the older pair member on its own W FILL."""
from pathlib import Path

rtl = Path(__file__).parent / "rtl"
s = (rtl / "p_native_weight_prefill.sv").read_text(encoding="utf-8")


def edit(old, new):
    global s
    assert s.count(old) == 1, old
    s = s.replace(old, new)


edit("module p_native_weight_prefill #(", "module p_native_weight_overlap_candidate #(")
edit("(pair_prep_second||state==PAIR_ACCEPT_SECOND);", "(pair_prep_second||pair_first_pending||state==PAIR_ACCEPT_SECOND);")
edit(" wire current_fill_fire=control_valid&&control_body&&!control_sop&&control_eop&&fill_body_ok;",
     """ wire current_fill_fire=control_valid&&control_body&&!control_sop&&control_eop&&fill_body_ok;
 wire saved_fill_fire=control_valid&&control_body&&!control_sop&&control_eop&&saved_fill_body_ok;""")
edit("else if(fill_seen&&A_loaded[selected_A_slot]&&current_load_shift<=17&&(!pair_prep_second||saved_fill_seen))begin",
     """else if((pair_prep_second?saved_fill_seen:fill_seen)&&A_loaded[selected_A_slot]&&current_load_shift<=17)begin""")
edit("""             // Exchange the sole saved record with the current prepared one.
             pair_hold<='{seq_id,col,address,full_k,k,context_id,n,completion_context,way,head,create,final_record,A_first,A_last,A_uses,current_context_generation,current_A_generation,current_use,W_bank,W_generation};pair_prep_second<=0;pair_first_pending<=1;""",
     """             // Older W is ready. Keep the younger ALLOC owner and its
             // unconsumed FILL receipt while launching the older EXEC.
             pair_hold<='{seq_id,col,address,full_k,k,context_id,n,completion_context,way,head,create,final_record,A_first,A_last,A_uses,current_context_generation,current_A_generation,current_use,W_bank,W_generation};pair_prep_second<=0;pair_first_pending<=1;
             saved_allocation_session<=allocation_session;saved_fill_seen<=fill_seen||current_fill_fire;
             allocation_session<=saved_allocation_session;fill_seen<=1;""")
edit("""         allocation_seen<=1;fill_seen<=1;input_seen<=0;failed<=0;record_progressed<=0;state<=W_JOIN;""",
     """         allocation_session<=saved_allocation_session;
         allocation_seen<=1;fill_seen<=saved_fill_seen||saved_fill_fire;
         input_seen<=0;failed<=0;record_progressed<=0;
         state<=(saved_fill_seen||saved_fill_fire)?W_JOIN:FILL_WAIT;""")
(rtl / "p_native_weight_overlap_candidate.sv").write_text(s, encoding="utf-8")
