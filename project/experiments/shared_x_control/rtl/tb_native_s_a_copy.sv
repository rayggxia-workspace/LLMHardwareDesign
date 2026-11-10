`timescale 1ns/1ps
// Functional bank model DELAY=3ns is arbitrary. A 10ns functional clock is
// intentional; this is a protocol/numeric SRAM integration, NOT 300MHz STA.
module tb_native_s_a_copy;
  logic clk,reset,halt,flush;
  initial clk=0;
  always #5 clk=~clk;
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
  logic [127:0] a_key;
  logic [15:0] a_generation,a_kk,a_use_sequence;
  logic close_valid,close_ready,close_slot,release_valid,release_ready,release_slot;
  logic [15:0] close_generation,release_generation;
  logic quiescent,source_reads_drained;
  logic [1:0] live_slots;
  logic [31:0] fault_cycles;
  private_a_tile_frontend front(.copy_committed_prefix(copy_committed_prefix[10:0]),.*);

  logic host_valid,host_ready,host_response_valid,host_response_ready;
  logic [9:0] host_address;
  logic [127:0] host_data;
  logic allow_responses;
  logic [1:0] cv[4],cw[4],cr[4],rv[4],rr[4],occupied[4];
  logic [19:0] ca[4];
  logic [255:0] cd[4];
  logic [63:0] ct[4],rt[4];
  logic [127:0] rd[4];
  logic [3:0] nv,nw,nready,nrv,nrr;
  logic [9:0] na[4];
  logic [127:0] nd[4],nrd[4];
  assign cv[0]={u_valid,host_valid};
  assign cw[0]=2'b01;
  assign ca[0]={u_address,host_address};
  assign cd[0]={128'b0,host_data};
  assign ct[0]={u_tag,32'b0};
  assign rr[0]={u_response_ready,host_response_ready};
  assign host_ready=cr[0][0];
  assign host_response_valid=rv[0][0];
  assign u_ready=cr[0][1];
  assign u_response_valid=rv[0][1];
  assign u_response_data=rd[0];
  assign u_response_tag=rt[0][63:32];
  assign u_response_error=0;
  assign p_ack_error=0;
  assign response_valid=rv[1][1]&&allow_responses;
  assign response_data=rd[1];
  assign response_tag=rt[1][63:32];
  assign s_ready=cr[1][1];
  for(genvar p=0;p<3;p=p+1) begin: clients
    assign cv[p+1]={(p==0?s_valid:1'b0),p_valid[p]};
    assign cw[p+1]=2'b01;
    assign ca[p+1]={(p==0?s_address:10'b0),p_address[10*p+:10]};
    assign cd[p+1]={128'b0,p_data[128*p+:128]};
    assign ct[p+1]={(p==0?s_tag:32'b0),p_tag[32*p+:32]};
    assign rr[p+1]={(p==0?(response_ready&&allow_responses):1'b1),p_ack_ready[p]&&allow_responses};
    assign p_ready[p]=cr[p+1][0];
    assign p_ack_valid[p]=rv[p+1][0]&&allow_responses;
    assign p_ack_tag[32*p+:32]=rt[p+1][31:0];
  end
  for(genvar m=0;m<4;m=m+1) begin: memories
    native_s128_mux2 mux(.clk,.reset,.c_valid(cv[m]),.c_write(cw[m]),.c_address(ca[m]),
      .c_data(cd[m]),.c_tag(ct[m]),.c_ready(cr[m]),.c_response_valid(rv[m]),
      .c_response_ready(rr[m]),.c_response_data(rd[m]),.c_response_tag(rt[m]),
      .req_valid(nv[m]),.req_write(nw[m]),.req_address(na[m]),.req_data(nd[m]),
      .req_ready(nready[m]),.rsp_valid(nrv[m]),.rsp_ready(nrr[m]),.rsp_data(nrd[m]),
      .owners_occupied(occupied[m]));
    local_s_base storage(.clk,.reset,.req_valid(nv[m]),.req_write(nw[m]),.req_addr(na[m]),
      .req_data(nd[m]),.req_ready(nready[m]),.rsp_valid(nrv[m]),.rsp_ready(nrr[m]),.rsp_data(nrd[m]));
  end
  integer cycle,seed,trace_file,no_overlap,single_first;
  integer source_reads,Pwrites[3],Areads,Muses,max_P0_owners;
  logic trace_active;
  logic [1:0] observed_max;
  string trace_path;
  function automatic logic [127:0] source_word(input int index);
    logic [127:0] value;
    for(integer lane=0;lane<8;lane=lane+1) value[16*lane+:16]=16'(index*8+lane-256);
    return value;
  endfunction
  always @(posedge clk) begin
    if(reset) begin
      cycle<=0;source_reads<=0;Areads<=0;Muses<=0;max_P0_owners<=0;observed_max<=0;
      for(integer p=0;p<3;p=p+1) Pwrites[p]<=0;
    end else begin
      cycle<=cycle+1;
      if(occupied[1]>observed_max) begin observed_max<=occupied[1];max_P0_owners<=int'(occupied[1]);end
      if(trace_active) begin
        for(integer m=0;m<4;m=m+1) begin
          if(nv[m]&&nready[m]) $fwrite(trace_file,"%0d,NREQ,%0d,%0d,%0d,%0d\n",cycle,m,nw[m],na[m],occupied[m]);
          if(nrv[m]&&nrr[m]) $fwrite(trace_file,"%0d,NRSP,%0d,0,0,%0d\n",cycle,m,occupied[m]);
        end
        if(cmd_valid&&cmd_ready) $fwrite(trace_file,"%0d,CMD,%0d,%0d,%0d,%0d\n",cycle,cmd_slot,cmd_generation,cmd_kk,cmd_planned_uses);
        if(u_valid&&u_ready) begin
          source_reads<=source_reads+1;
          $fwrite(trace_file,"%0d,UREQ,0,%0d,%0d,0\n",cycle,u_tag,u_address);
        end
        for(integer p=0;p<3;p=p+1) if(p_ack_valid[p]&&p_ack_ready[p]) begin
          Pwrites[p]<=Pwrites[p]+1;
          $fwrite(trace_file,"%0d,PACK,%0d,%0d,%0d,0\n",cycle,p,p_ack_tag[32*p+:32],copy_committed_prefix[11*p+:11]);
        end
        if(s_valid&&s_ready) begin
          Areads<=Areads+1;
          assert({1'b0,s_address}-11'd100<copy_committed_prefix[10:0]) else $fatal(1,"real S A read before matching copy ACK");
          $fwrite(trace_file,"%0d,SREQ,%0d,%0d,%0d,0\n",cycle,s_tag[15],s_tag,s_address);
        end
        if(response_valid&&response_ready) $fwrite(trace_file,"%0d,SRSP,%0d,%0d,0,0\n",cycle,response_tag[15],response_tag);
        if(load_done_valid&&load_done_ready) $fwrite(trace_file,"%0d,LOAD,%0d,%0d,%0d,0\n",cycle,load_done_slot,load_done_generation,load_done_error);
        if(use_valid&&use_ready) begin Muses<=Muses+1;$fwrite(trace_file,"%0d,MUSE,%0d,%0d,%0d,%0d\n",cycle,use_slot,use_generation,use_kk,use_sequence);end
        if(a_valid&&a_ready) $fwrite(trace_file,"%0d,ASTEP,%0d,%0d,%0d,%0d\n",cycle,a_slot,a_generation,a_kk,a_step);
      end
    end
  end
  task automatic pause(input int n=1);repeat(n) @(negedge clk);endtask
  task automatic initialize_source;
    for(integer word_index=0;word_index<32;word_index=word_index+1) begin
      @(negedge clk);host_address=10'(word_index);host_data=source_word(word_index);host_valid=1;
      do @(posedge clk);while(!host_ready);@(negedge clk);host_valid=0;
      while(!host_response_valid) @(negedge clk);
      host_response_ready=1;pause();host_response_ready=0;
    end
  endtask
  task automatic command(input bit slot,input int k,input logic [15:0] uses);
    @(negedge clk);cmd_slot=slot;cmd_generation=1;cmd_kk=16'(k);cmd_planned_uses=16'(uses);
    cmd_key=start_key;cmd_S_base=10'(100+k*16);cmd_copy_offset=10'(k*16);cmd_valid=1;
    do @(posedge clk);while(!cmd_ready);@(negedge clk);cmd_valid=0;
  endtask
  task automatic take_load(input bit slot);
    while(!load_done_valid) @(negedge clk);
    assert(load_done_slot==slot&&!load_done_error&&load_done_generation==1&&load_done_key==start_key) else $fatal(1,"realS LOAD identity");
    load_done_ready=1;pause();load_done_ready=0;
  endtask
  task automatic weight_use(input bit slot,input int k,input int seq);
    @(negedge clk);w_slot=slot;w_generation=1;w_kk=16'(k);w_use_sequence=16'(seq);
    w_key=start_key;w_record=32'(1000+k*100+seq);w_valid=1;
    do @(posedge clk);while(!w_ready);@(negedge clk);w_valid=0;
    use_slot=slot;use_generation=1;use_kk=16'(k);use_sequence=16'(seq);use_key=start_key;use_valid=1;
    do @(posedge clk);while(!use_ready);@(negedge clk);use_valid=0;
    for(integer step=0;step<8;step=step+1) begin
      while(!a_valid) @(negedge clk);
      assert(a_key==start_key&&a_slot==slot&&a_generation==1&&a_kk==16'(k)&&a_use_sequence==16'(seq)&&a_step==3'(step)&&a_weight_record==32'(1000+k*100+seq)) else $fatal(1,"realS M JOIN identity");
      assert(a_data=={source_word(k*16+2*step+1),source_word(k*16+2*step)}) else $fatal(1,"actual SRAM signed A replay");
      pause(seed%3);a_ready=1;pause();a_ready=0;
    end
  endtask
  task automatic close_release(input bit slot);
    @(negedge clk);close_slot=slot;close_generation=1;close_valid=1;
    do @(posedge clk);while(!close_ready);@(negedge clk);close_valid=0;
    release_slot=slot;release_generation=1;release_valid=1;
    do @(posedge clk);while(!release_ready);@(negedge clk);release_valid=0;
  endtask
  initial begin
    reset=1;halt=0;flush=0;seed=1;trace_active=0;allow_responses=1;no_overlap=0;single_first=0;
    start_valid=0;start_key=128'h00000001000000fa0000000100000001;start_generation=1;
    start_U_base=0;start_P_bases={10'd300,10'd200,10'd100};start_words=32;start_P_mask=7;
    destination_window_released=1;done_ready=0;cmd_valid=0;cmd_slot=0;
    cmd_generation=0;cmd_kk=0;cmd_planned_uses=0;cmd_key=0;cmd_S_base=0;cmd_copy_offset=0;
    load_done_ready=0;w_valid=0;w_slot=0;w_generation=0;w_kk=0;w_use_sequence=0;w_key=0;w_record=0;
    use_valid=0;use_slot=0;use_generation=0;use_kk=0;use_sequence=0;use_key=0;a_ready=0;
    close_valid=0;close_slot=0;close_generation=0;release_valid=0;release_slot=0;release_generation=0;
    host_valid=0;host_address=0;host_data=0;host_response_ready=0;
    if($value$plusargs("SEED=%d",seed)) begin end
    if($value$plusargs("NO_OVERLAP=%d",no_overlap)) begin end
    if($value$plusargs("SINGLE_FIRST=%d",single_first)) begin end
    trace_path=$sformatf("native-s-%0d.csv",seed);
    if($value$plusargs("TRACE=%s",trace_path)) begin end
    trace_file=$fopen(trace_path,"w");assert(trace_file!=0) else $fatal(1,"trace open");
    $fwrite(trace_file,"cycle,event,resource,identity,detail,value\n");
    pause(3);reset=0;pause();initialize_source();trace_active=1;
    start_valid=1;do @(posedge clk);while(!start_ready);@(negedge clk);start_valid=0;
    if(no_overlap!=0) while(!done_valid) @(negedge clk);
    command(0,0,2);if(single_first==0) command(1,1,1);
    // Deliberately backpressure the actual native responses, not a fake ACK.
    fork
      begin
        if(no_overlap==0) begin
          while(copy_committed_prefix[10:0]<3) @(negedge clk);
          allow_responses=0;pause(5+seed);allow_responses=1;
        end
      end
      begin
        take_load(0);if(single_first!=0) command(1,1,1);weight_use(0,0,1);
        release_slot=0;release_generation=1;release_valid=1;pause();
        assert(!release_ready&&live_slots[0]) else $fatal(1,"realS A freed before planned reuse");release_valid=0;
        take_load(1);
        assert(Areads==32) else $fatal(1,"actual S load did not use exactly 16 words per tile");
        weight_use(0,0,2);close_release(0);
        weight_use(1,1,1);close_release(1);
      end
    join
    while(!done_valid) @(negedge clk);
    assert(!done_error&&copy_committed_prefix=={11'd32,11'd32,11'd32}&&committed_words==96) else $fatal(1,"actualS copy terminal before commits");
    done_ready=1;pause();done_ready=0;pause(3);
    assert(source_reads==32&&Areads==32&&Muses==3) else $fatal(1,"actualS transfer accounting / unwanted repeated A load");
    assert(Pwrites[0]==32&&Pwrites[1]==32&&Pwrites[2]==32) else $fatal(1,"actualS 3P ACK count");
    assert(live_slots==0&&quiescent&&source_reads_drained&&copy_quiescent) else $fatal(1,"actualS lease drain");
    assert(fault_cycles==1&&copy_faults==0) else $fatal(1,"unexpected native protocol fault");
    if(no_overlap==0) assert(max_P0_owners==2) else $fatal(1,"actualS did not exercise two bounded owner credits");
    $display("PASS native_s_a_copy seed=%0d cycles=%0d Ureads=%0d Pwrites=%0d/%0d/%0d Areads=%0d Muse=%0d max_owners=%0d",seed,cycle,source_reads,Pwrites[0],Pwrites[1],Pwrites[2],Areads,Muses,max_P0_owners);
    $fclose(trace_file);$finish;
  end
  initial begin #500000; $fatal(1,"actualS timeout"); end
endmodule
