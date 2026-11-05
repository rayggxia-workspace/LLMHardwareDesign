  // Fixed route 12: P0 -> P1 and P1 -> P0. The test carries the full
  // outstanding TX identity even though the legacy RAW16 endpoint takes done.
  localparam integer ACK_ID_BITS=272;
  reg [ACK_ID_BITS-1:0] active_ack_id, previous_ack_id;
  reg previous_ack_valid=0;
  reg ack_reset_seen=0;
  integer ack_attempt=0;
  wire ack_guard_busy, ack_guard_ready, ack_guard_done, ack_guard_reject, ack_wire_ready;
  wire [ACK_ID_BITS-1:0] tx_ack_id={link_job[0],link_epoch[0],link_task[0],link_sequence[0],link_edge[0],
                                       16'h0001,32'd1,32'd1,32'd0};
  wire arm_ack=link_valid[0] && link_ready[0] && link_kind[0]==2;
  wire dest_written=store_valid[1] && store_ready[1];
  wire early_ack=ack_inject==8 && route_dst && route_state==1 && route_delay==1;
  wire stale_ack=ack_inject==7 && previous_ack_valid && ack_attempt==0;
  wire wrong_identity=ack_inject==5 || ack_inject==9 || ack_inject==10;
  wire wrong_ack=wrong_identity && ack_attempt==0;
  wire duplicate_ack=ack_inject==6;
  wire extra_attempt=wrong_identity || duplicate_ack || (ack_inject==7 && previous_ack_valid);
  wire ack_delivery_slot=stall==0 || cycle%17==0;
  wire ack_send=route_state==3 && mode!=2 && ack_delivery_slot &&
                    ack_attempt < (extra_attempt ? 2 : 1);
  wire ack_in=early_ack || ack_send;
  wire [ACK_ID_BITS-1:0] ack_wire_id=early_ack ? active_ack_id :
                                     stale_ack ? previous_ack_id :
                                     wrong_ack ? active_ack_id ^ (272'd1 << (ack_inject==5 ? 208 : ack_inject==9 ? 144 : 112)) : active_ack_id;
  wire ack_done_gate=!duplicate_ack || ack_attempt>=2;
  p_stored_ack_guard #(.ID_BITS(ACK_ID_BITS)) ack_guard(
    .clk(clk_i),.reset(!rst_ni),.arm_valid(arm_ack),.arm_ready(ack_guard_ready),.arm_identity(tx_ack_id),
    .store_commit(dest_written),.ack_valid(ack_in),.ack_ready(ack_wire_ready),.ack_identity(ack_wire_id),
    .done_valid(ack_guard_done),.done_ready(done_ready[0] && ack_done_gate),
    .rejected(ack_guard_reject),.busy(ack_guard_busy));
  always @(posedge clk_i) begin
    ack_reset_seen<=!rst_ni;
    if(!rst_ni) begin
      ack_attempt<=0;
      if(!ack_reset_seen) $display("ACKG %0d RESET",cycle);
    end else begin
      if(arm_ack) begin
        if(!ack_guard_ready) $fatal(1,"source reused an outstanding ACK slot");
        active_ack_id<=tx_ack_id;
        $display("ACKG %0d ARM %068h",cycle,tx_ack_id);
      end
      if(dest_written)
        $display("ACKG %0d COMMIT %068h",cycle,active_ack_id);
      if(route_state==2 && route_dst && done_valid[1] && done_ready[1])
        ack_attempt<=0;
      if(ack_in && ack_wire_ready) begin
        if(!early_ack) ack_attempt<=ack_attempt+1;
        $display("ACKG %0d WIRE %068h",cycle,ack_wire_id);
      end
      if(ack_guard_reject)
        $display("ACKG %0d DROP",cycle);
      if(ack_guard_done && !ack_done_gate)
        $display("ACKG %0d HOLD %068h",cycle,active_ack_id);
      if(ack_guard_done && ack_done_gate && done_ready[0]) begin
        previous_ack_id<=active_ack_id;
        previous_ack_valid<=1;
        $display("ACKG %0d DONE %068h",cycle,active_ack_id);
      end
      // In the reset campaign, save the lost old acknowledgement in the
      // external fault injector, beyond the control cohort's reset boundary.
      if(mode==2 && route_state==3) begin
        previous_ack_id<=active_ack_id;
        previous_ack_valid<=1;
      end
    end
  end
