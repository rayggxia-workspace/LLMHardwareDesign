`timescale 1ns/1ps
module tb_private_a_copy;
  logic clk,reset,halt,flush;
  initial clk=0;
  always #1 clk=~clk;
  logic start_valid,start_ready,destination_window_released;
  logic [127:0] start_key,copy_key;
  logic [15:0] start_generation;
  logic [9:0] start_U_base;
  logic [29:0] start_P_bases;
  logic [10:0] start_words;
  logic [2:0] start_P_mask;
  logic u_valid,u_ready,u_response_valid,u_response_ready,u_response_error;
  logic [9:0] u_address;
  logic [31:0] u_tag,u_response_tag;
  logic [127:0] u_response_data;
  logic [2:0] p_valid,p_ready,p_ack_valid,p_ack_ready,p_ack_error;
  logic [29:0] p_address;
  logic [95:0] p_tag,p_ack_tag;
  logic [383:0] p_data;
  logic [32:0] copy_committed_prefix;
  logic done_valid,done_ready,done_error,copy_quiescent;
  logic [31:0] copy_faults,committed_words;
  early_copy_3p copy(.quiescent(copy_quiescent),.fault_cycles(copy_faults),.*);
  logic cmd_valid,cmd_ready,cmd_slot;
  logic [15:0] cmd_generation,cmd_kk,cmd_planned_uses;
  logic [127:0] cmd_key;
  logic [9:0] cmd_S_base,cmd_copy_offset;
  logic load_done_valid,load_done_ready,load_done_slot,load_done_error;
  logic [15:0] load_done_generation;
  logic [127:0] load_done_key;
  logic s_valid,s_ready,response_valid,response_ready;
  logic [9:0] s_address;
  logic [31:0] s_tag,response_tag;
  logic [127:0] response_data;
  logic w_valid,w_ready,w_slot;
  logic [15:0] w_generation,w_kk,w_use_sequence;
  logic [127:0] w_key;
  logic [31:0] w_record;
  logic use_valid,use_ready,use_slot;
  logic [15:0] use_generation,use_kk,use_sequence;
  logic [127:0] use_key;
  logic a_valid,a_ready,a_slot;
  logic [255:0] a_data;
  logic [2:0] a_step;
  logic [31:0] a_weight_record;
  logic [15:0] a_generation,a_kk,a_use_sequence;
  logic close_valid,close_ready,close_slot,release_valid,release_ready,release_slot;
  logic [15:0] close_generation,release_generation;
  logic quiescent,source_reads_drained;
  logic [1:0] live_slots;
  logic [31:0] fault_cycles;
  private_a_tile_frontend front(.copy_committed_prefix(copy_committed_prefix[10:0]),.*);

  // Conservative native S model: one transaction per P port, writes and A
  // reads share the same P0 port. Acknowledgment follows the actual memory op.
  logic [127:0] Pmemory[3][1024];
  logic [2:0] Ppending,Piswrite;
  logic [9:0] Paddress[3];
  logic [127:0] Pdata[3];
  logic [31:0] Ptag[3];
  integer Pdelay[3];
  logic arb_read;
  logic [2:0] ack_actual,inject_ack;
  logic [95:0] ack_actual_tag,inject_ack_tag;
  logic response_actual,inject_response;
  logic [31:0] response_actual_tag,inject_response_tag;
  logic [127:0] response_actual_data;
  logic Upending;
  integer Udelay;
  logic [31:0] Utag;
  logic [127:0] Udata;
  integer seed,source_epoch;
  logic [10:0] prefix_before_late_ACK;
  logic old_s,old_sr,old_a,old_ar;
  logic [41:0] old_s_payload;
  logic [339:0] old_a_payload;
  function automatic logic [127:0] source_word(input int index,input int epoch);
    logic [127:0] value;
    for(integer lane=0;lane<8;lane=lane+1) value[16*lane+:16]=16'(epoch*4096+index*8+lane-256);
    return value;
  endfunction
  assign u_ready=!reset&&!Upending&&!u_response_valid;
  assign p_ack_valid=ack_actual|inject_ack;
  assign p_ack_tag={inject_ack[2]?inject_ack_tag[95:64]:ack_actual_tag[95:64],
                    inject_ack[1]?inject_ack_tag[63:32]:ack_actual_tag[63:32],
                    inject_ack[0]?inject_ack_tag[31:0]:ack_actual_tag[31:0]};
  assign p_ack_error=0;
  assign response_valid=response_actual|inject_response;
  assign response_tag=inject_response?inject_response_tag:response_actual_tag;
  assign response_data=response_actual_data;
  always_comb begin
    p_ready=0;s_ready=0;
    for(integer i=0;i<3;i=i+1) if(!reset&&!Ppending[i]) begin
      if(i==0 && s_valid && (!p_valid[0]||arb_read)) s_ready=1;
      else p_ready[i]=1;
    end
  end
  always @(posedge clk) begin
    if(reset) begin
      Ppending<=0;Piswrite<=0;arb_read<=0;ack_actual<=0;ack_actual_tag<=0;
      response_actual<=0;response_actual_tag<=0;response_actual_data<=0;
      Upending<=0;Udelay<=0;Utag<=0;Udata<=0;
      u_response_valid<=0;u_response_tag<=0;u_response_data<=0;u_response_error<=0;
      old_s<=0;old_sr<=0;old_a<=0;old_ar<=0;old_s_payload<=0;old_a_payload<=0;
      for(integer i=0;i<3;i=i+1) begin Paddress[i]<=0;Pdata[i]<=0;Ptag[i]<=0;Pdelay[i]<=0;end
    end else begin
      ack_actual<=0;response_actual<=0;
      if(old_s&&!old_sr) assert(s_valid&&{s_address,s_tag}==old_s_payload) else $fatal(1,"A read withdrew valid");
      if(old_a&&!old_ar) assert(a_valid&&{a_data,a_step,a_weight_record,a_slot,a_generation,a_kk,a_use_sequence}==old_a_payload) else $fatal(1,"A changed under M backpressure");
      old_s<=s_valid;old_sr<=s_ready;old_s_payload<={s_address,s_tag};
      old_a<=a_valid;old_ar<=a_ready;old_a_payload<={a_data,a_step,a_weight_record,a_slot,a_generation,a_kk,a_use_sequence};
      if(u_response_valid&&u_response_ready) u_response_valid<=0;
      if(u_valid&&u_ready) begin Upending<=1;Udelay<=1+seed%3;Utag<=u_tag;Udata<=source_word(int'(u_address),source_epoch);end
      if(Upending) begin
        if(Udelay!=0) Udelay<=Udelay-1;
        else if(!u_response_valid) begin Upending<=0;u_response_valid<=1;u_response_tag<=Utag;u_response_data<=Udata;end
      end
      for(integer i=0;i<3;i=i+1) begin
        if(p_valid[i]&&p_ready[i]) begin
          assert(!(i==0&&s_valid&&s_ready)) else $fatal(1,"private S acted dual port");
          Ppending[i]<=1;Piswrite[i]<=1;Paddress[i]<=p_address[10*i+:10];
          Pdata[i]<=p_data[128*i+:128];Ptag[i]<=p_tag[32*i+:32];Pdelay[i]<=1+(seed+i)%3;
          if(i==0) arb_read<=1;
        end
        if(i==0&&s_valid&&s_ready) begin
          assert({1'b0,s_address}-11'd100<copy_committed_prefix[10:0]) else $fatal(1,"A read before true copy ACK");
          Ppending[0]<=1;Piswrite[0]<=0;Paddress[0]<=s_address;Ptag[0]<=s_tag;Pdelay[0]<=1+seed%3;arb_read<=0;
        end
        if(Ppending[i]) begin
          if(Pdelay[i]!=0) Pdelay[i]<=Pdelay[i]-1;
          else if(Piswrite[i]&&!inject_ack[i]) begin
            Pmemory[i][Paddress[i]]<=Pdata[i];ack_actual[i]<=1;ack_actual_tag[32*i+:32]<=Ptag[i];Ppending[i]<=0;
          end else if(!Piswrite[i]&&!inject_response) begin
            response_actual<=1;response_actual_tag<=Ptag[i];response_actual_data<=Pmemory[i][Paddress[i]];Ppending[i]<=0;
          end
        end
      end
    end
  end
  task automatic pause(input int n=1);repeat(n) @(negedge clk);endtask
  task automatic command(input bit slot,input logic [15:0] gen,input int k,input logic [15:0] uses);
    @(negedge clk);cmd_slot=slot;cmd_generation=16'(gen);cmd_kk=16'(k);cmd_planned_uses=16'(uses);
    cmd_key=start_key;cmd_S_base=10'(100+k*16);cmd_copy_offset=10'(k*16);cmd_valid=1;
    do @(posedge clk);while(!cmd_ready);@(negedge clk);cmd_valid=0;
  endtask
  task automatic take_load(input bit slot,input bit error_expected=0,input logic [15:0] gen_expected=1);
    while(!load_done_valid) @(negedge clk);
    assert(load_done_slot==slot&&load_done_error==error_expected&&load_done_key==start_key&&load_done_generation==gen_expected) else $fatal(1,"load terminal identity/error");
    pause(3);load_done_ready=1;pause();load_done_ready=0;
  endtask
  task automatic weight(input bit slot,input logic [15:0] gen,input int k,input int seq);
    @(negedge clk);w_slot=slot;w_generation=16'(gen);w_kk=16'(k);w_use_sequence=16'(seq);
    w_key=start_key;w_record=32'(1000+k*100+seq);w_valid=1;
    do @(posedge clk);while(!w_ready);@(negedge clk);w_valid=0;
  endtask
  task automatic begin_use(input bit slot,input logic [15:0] gen,input logic [15:0] k,input logic [15:0] seq);
    @(negedge clk);use_slot=slot;use_generation=16'(gen);use_kk=16'(k);use_sequence=16'(seq);use_key=start_key;use_valid=1;
    do @(posedge clk);while(!use_ready);@(negedge clk);use_valid=0;
  endtask
  task automatic consume(input bit slot,input logic [15:0] gen,input int k,input int seq);
    for(integer step=0;step<8;step=step+1) begin
      while(!a_valid) @(negedge clk);
      assert(a_slot==slot&&a_generation==16'(gen)&&a_kk==16'(k)&&a_use_sequence==16'(seq)&&a_step==3'(step)&&a_weight_record==32'(1000+k*100+seq)) else $fatal(1,"M JOIN tag");
      assert(a_data=={source_word(k*16+step*2+1,source_epoch),source_word(k*16+step*2,source_epoch)}) else $fatal(1,"A K128 signed container replay mismatch");
      pause(seed%3+1);a_ready=1;pause();a_ready=0;
    end
  endtask
  task automatic close_release(input bit slot,input logic [15:0] gen);
    @(negedge clk);close_slot=slot;close_generation=16'(gen);close_valid=1;
    do @(posedge clk);while(!close_ready);@(negedge clk);close_valid=0;
    release_slot=slot;release_generation=16'(gen);release_valid=1;
    do @(posedge clk);while(!release_ready);@(negedge clk);release_valid=0;
  endtask
  task automatic start_copy;
    @(negedge clk);start_valid=1;
    do @(posedge clk);while(!start_ready);@(negedge clk);start_valid=0;destination_window_released=0;
  endtask
  initial begin
    reset=1;halt=0;flush=0;seed=1;source_epoch=0;
    start_valid=0;start_key=128'h00000001000000fa0000000100000001;start_generation=1;
    start_U_base=0;start_P_bases={10'd300,10'd200,10'd100};start_words=32;start_P_mask=7;
    destination_window_released=1;done_ready=0;cmd_valid=0;cmd_slot=0;
    cmd_generation=0;cmd_kk=0;cmd_planned_uses=0;cmd_key=0;cmd_S_base=0;cmd_copy_offset=0;
    load_done_ready=0;w_valid=0;w_slot=0;w_generation=0;w_kk=0;w_use_sequence=0;w_key=0;w_record=0;
    use_valid=0;use_slot=0;use_generation=0;use_kk=0;use_sequence=0;use_key=0;a_ready=0;
    close_valid=0;close_slot=0;close_generation=0;release_valid=0;release_slot=0;release_generation=0;
    inject_ack=0;inject_ack_tag=0;inject_response=0;inject_response_tag=0;
    if($value$plusargs("SEED=%d",seed)) begin end
    pause(3);reset=0;pause();
    inject_ack=1;inject_ack_tag=96'hdead;pause();inject_ack=0;
    assert(copy_committed_prefix==0) else $fatal(1,"foreign ACK advanced prefix");
    start_copy();command(0,1,0,2);command(1,1,1,1);
    assert(live_slots==3&&!cmd_ready) else $fatal(1,"more than two A tiles");
    weight(0,1,0,1); // Legal W completion before full A prefix arrives.
    pause(2);assert(!a_valid) else $fatal(1,"partial copy became M ready");
    take_load(0);begin_use(0,1,0,1);consume(0,1,0,1);
    release_slot=0;release_generation=1;release_valid=1;pause();
    assert(!release_ready&&live_slots[0]) else $fatal(1,"first consumer freed shared A tile");release_valid=0;
    w_slot=0;w_generation=1;w_kk=0;w_use_sequence=1;w_key=start_key;w_valid=1;pause();
    assert(!w_ready) else $fatal(1,"old W use sequence reused");w_valid=0;
    w_generation=0;w_use_sequence=2;w_valid=1;pause();
    assert(!w_ready) else $fatal(1,"wrong A slot generation joined W");w_valid=0;
    take_load(1);weight(0,1,0,2);begin_use(0,1,0,2);
    close_slot=0;close_generation=1;close_valid=1;
    do @(posedge clk);while(!close_ready);@(negedge clk);close_valid=0;
    release_slot=0;release_generation=1;release_valid=1;pause();
    assert(!release_ready) else $fatal(1,"CLOSE freed before last M acceptance");release_valid=0;
    consume(0,1,0,2);release_valid=1;do @(posedge clk);while(!release_ready);@(negedge clk);release_valid=0;
    weight(1,1,1,1);begin_use(1,1,1,1);consume(1,1,1,1);close_release(1,1);
    while(!done_valid) @(negedge clk);
    assert(!done_error&&copy_committed_prefix=={11'd32,11'd32,11'd32}&&committed_words==96) else $fatal(1,"3P copy did not wait actual commits");
    done_ready=1;pause();done_ready=0;
    command(0,2,0,1);
    while(!s_valid) @(negedge clk);
    halt=1;flush=1;pause();assert(!quiescent) else $fatal(1,"early flush discarded a proposed read");flush=0;
    take_load(0,1,2);while(!quiescent) @(negedge clk);flush=1;pause();flush=0;
    assert(live_slots==0) else $fatal(1,"cancel flush retained partial tile");
    while(response_actual) @(negedge clk);
    inject_response=1;inject_response_tag={16'd2,1'b0,4'd0,11'd0};pause();inject_response=0;
    assert(!load_done_valid&&live_slots==0) else $fatal(1,"late response restored invalid tile");
    halt=0;source_epoch=1;start_key=128'h00000002000000fa0000000200000002;start_generation=2;
    destination_window_released=1;start_copy();command(0,3,0,1);weight(0,3,0,1);
    while(!(Ppending[0]&&Piswrite[0]&&Ptag[0][31:16]==2)) @(negedge clk);
    prefix_before_late_ACK=copy_committed_prefix[10:0];
    inject_ack=1;inject_ack_tag[31:0]={16'd1,Ptag[0][15:0]};pause();inject_ack=0;
    assert(copy_committed_prefix[10:0]==prefix_before_late_ACK) else $fatal(1,"late old copy ACK advanced new epoch");
    do @(posedge clk);while(!(s_valid&&s_ready));@(negedge clk);
    inject_response=1;inject_response_tag={16'd2,1'b0,4'd0,11'd0};pause();inject_response=0;
    assert(!load_done_valid) else $fatal(1,"late old A response completed new slot");
    take_load(0,0,3);begin_use(0,3,0,1);consume(0,3,0,1);close_release(0,3);
    while(!done_valid) @(negedge clk);assert(!done_error) else $fatal(1,"fresh epoch failed");
    assert(fault_cycles>=5&&copy_faults>=2&&source_reads_drained&&response_ready&&p_ack_ready==7&&copy_quiescent==0) else $fatal(1,"negative-case accounting");
    $display("PASS private-A-copy seed=%0d nativeS128 multiuse earlycopy retry faults=%0d copyfaults=%0d",seed,fault_cycles,copy_faults);
    $finish;
  end
  initial begin #100000; $fatal(1,"private A/copy timeout");end
endmodule
