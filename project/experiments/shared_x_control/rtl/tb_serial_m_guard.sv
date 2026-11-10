`timescale 1ns/1ps
// Product-M frames + actual local_s_base/four original SRAM banks.
// The M peer supplies frames; numeric M execution is a separate joint gate.
module tb_serial_m_guard;
  logic clk,reset;
  initial clk=0;
  always #5 clk=~clk;
  logic cmd_valid,cmd_ready;
  logic [511:0] cmd_ticket;
  logic [127:0] cmd_job_key;
  logic [31:0] cmd_abi,cmd_topology,cmd_capacity,cmd_numeric,cmd_layout;
  logic [7:0] cmd_resource,cmd_service,cmd_provider,cmd_function;
  logic [15:0] cmd_native_op;
  logic [255:0] cmd_payload;
  logic cmd_stored;
  logic [1:0] cmd_store_words;
  logic [9:0] cmd_destination;
  logic native_valid,native_ready;
  logic [511:0] native_ticket;
  logic [7:0] native_resource,native_service;
  logic [255:0] native_payload;
  logic lr_valid,lr_ready,lr_sop,lr_eop;
  logic [127:0] lr_data;
  logic input_consumed_valid,input_consumed_ready,input_consumed_error;
  logic [511:0] input_consumed_ticket;
  logic native_abort_valid,native_abort_ready;
  logic [511:0] native_abort_ticket;
  logic [15:0] native_abort_next_k;
  logic control_valid,control_ready,control_sop,control_eop;
  logic [127:0] control_data;
  logic cancel_drained_valid,cancel_drained_ready;
  logic [511:0] cancel_drained_ticket;
  logic s_valid,s_ready,s_word;
  logic [511:0] s_ticket;
  logic [9:0] s_address;
  logic [127:0] s_data;
  logic ack_valid,ack_ready,ack_word,ack_error;
  logic [511:0] ack_ticket;
  logic terminal_valid,terminal_ready,terminal_stored,terminal_partial;
  logic [511:0] terminal_ticket;
  logic [7:0] terminal_error;
  logic [255:0] terminal_data;
  logic cancel_valid,timeout_valid,clear_quarantine,resume_after_drain;
  logic [127:0] cancel_job_key;
  logic halted,quarantine,quiescent;
  logic [1:0] occupied_slots,result_slots_occupied;
  logic [31:0] rejected_protocol_events,committed_words;
  bounded_serial_m_guard dut(.*);
  logic allow_request,allow_ACK,inject_wrong;
  logic host_valid,host_ready,host_rsp_valid,host_rsp_ready;
  logic [9:0] host_address;
  logic [1:0] c_ready,c_rsp_valid,owners;
  logic [63:0] c_rsp_tag;
  logic [127:0] c_rsp_data;
  logic req_valid,req_write,req_ready,rsp_valid,rsp_ready;
  logic [9:0] req_address;
  logic [127:0] req_data,rsp_data;
  assign s_ready=c_ready[0]&&allow_request;
  assign host_ready=c_ready[1];assign host_rsp_valid=c_rsp_valid[1];
  assign ack_valid=inject_wrong||(c_rsp_valid[0]&&allow_ACK);
  assign ack_ticket=inject_wrong?(s_ticket^512'd1):s_ticket;
  assign ack_word=s_word;assign ack_error=0;
  native_s128_mux2 mux(.clk,.reset,.c_valid({host_valid,s_valid&&allow_request}),.c_write(2'b01),
    .c_address({host_address,s_address}),.c_data({128'b0,s_data}),.c_tag({32'b0,31'b0,s_word}),
    .c_ready,.c_response_valid(c_rsp_valid),.c_response_ready({host_rsp_ready,ack_ready&&allow_ACK&&!inject_wrong}),
    .c_response_data(c_rsp_data),.c_response_tag(c_rsp_tag),.req_valid,.req_write,.req_address,.req_data,
    .req_ready,.rsp_valid,.rsp_ready,.rsp_data,.owners_occupied(owners));
  local_s_base storage(.clk,.reset,.req_valid,.req_write,.req_addr(req_address),.req_data,.req_ready,.rsp_valid,.rsp_ready,.rsp_data);
  integer seed,cycle,trace_file,input_ACKs,control_beats;
  string trace_path;
  task automatic pause(input int n=1);repeat(n) @(negedge clk);endtask
  function automatic logic [511:0] ticket(input int id);
    return {cmd_job_key,128'h12345678,{32'd250,cmd_job_key[63:32],32'd402,32'd1},96'b0,32'(id)};
  endfunction
  function automatic logic [255:0] payload(input int id,input bit snapshot);
    logic [255:0] p;
    p=0;p[31:0]=32'(500+id);p[63:32]=32'(1000+id);p[95:64]=32'(2000+id);
    p[99:96]=4'(id%16);p[103:100]=8;p[111:104]=id==6?16:128;p[127:112]=128;p[143:128]=128;
    p[145:144]=2'(id%4);p[161:146]=9;p[177:162]=16'(id);p[178]=1;p[194:179]=3;
    p[210:195]=0;p[213:211]=id==5?3:2;p[215]=snapshot&&id!=5;p[216]=snapshot;p[217]=id!=5;return p;
  endfunction
  function automatic logic [255:0] values(input int id);
    return {32'(id+7),32'(id+6),32'(id+5),32'(id+4),32'(id+3),32'(id+2),32'(id+1),32'(id)};
  endfunction
  function automatic logic [127:0] header(input int id,input logic [7:0] event_id,input logic [15:0] flags);
    return {flags,32'(1000+id),32'(500+id),8'b0,event_id,32'h02504d02};
  endfunction
  function automatic logic [127:0] meta(input int id,input bit input_event,input bit snapshot);
    logic [210:64] p;
    p=147'(payload(id,snapshot)>>64);
    if(input_event) return {29'b0,p[95:64],p[210:195],p[194:179],p[178],p[177:162],p[161:146],p[145:144]};
    return {14'b0,p[177:162],p[161:146],p[145:144],p[95:64],p[143:128],p[127:112],p[111:104],p[103:100],p[99:96]};
  endfunction
  function automatic logic [15:0] flags(input int id,input bit snapshot);
    return {(snapshot?4'd4:4'd2),1'b0,(id==5?3'd3:3'd2),4'(id%16),2'b0,(snapshot&&id!=5),snapshot};
  endfunction
  task automatic enqueue(input int id,input bit snapshot);
    cmd_ticket=ticket(id);cmd_payload=payload(id,snapshot);cmd_stored=snapshot;
    cmd_store_words=snapshot?2:0;cmd_destination=10'(100+2*id);cmd_valid=1;
    do @(posedge clk);while(!cmd_ready);@(negedge clk);cmd_valid=0;
  endtask
  task automatic take_native(input int id,input bit snapshot);
    while(!native_valid) @(negedge clk);
    assert(native_ticket==ticket(id)&&native_payload==payload(id,snapshot)&&native_resource==0&&native_service==32);
    native_ready=1;pause();native_ready=0;
  endtask
  task automatic flit(input bit sop,input bit eop,input logic [127:0] word);
    lr_valid=1;lr_sop=sop;lr_eop=eop;lr_data=word;
    do @(posedge clk);while(!lr_ready);@(negedge clk);lr_valid=0;pause(seed%2);
  endtask
  task automatic input_event(input int id,input bit snapshot);
    flit(1,0,header(id,3,16'h2000));flit(0,1,meta(id,1,snapshot));
  endtask
  task automatic rf_event(input int id,input bit snapshot);
    logic [255:0] v;
    v=values(id);flit(1,0,header(id,4,flags(id,snapshot)));flit(0,!snapshot,meta(id,0,snapshot));
    if(snapshot) begin flit(0,0,v[127:0]);flit(0,1,v[255:128]);end
  endtask
  task automatic take_terminal(input int id,input bit stored,input logic [7:0] error_code);
    while(!terminal_valid) @(negedge clk);
    assert(terminal_ticket==ticket(id)&&terminal_stored==stored&&terminal_error==error_code&&!terminal_partial);
    if(stored) begin assert(terminal_data==values(id));end
    else begin assert(terminal_data==0||error_code==5);end
    pause(seed%3);terminal_ready=1;pause();terminal_ready=0;
  endtask
  task automatic readback(input int id);
    logic [255:0] expected;
    expected=values(id);
    for(integer word_index=0;word_index<2;word_index=word_index+1) begin
      host_address=10'(100+2*id+word_index);host_valid=1;
      do @(posedge clk);while(!host_ready);@(negedge clk);host_valid=0;
      while(!host_rsp_valid) @(negedge clk);
      assert(c_rsp_data==expected[128*word_index+:128]);host_rsp_ready=1;pause();host_rsp_ready=0;
    end
  endtask
  always @(posedge clk) begin
    if(reset) begin cycle<=0;input_ACKs<=0;control_beats<=0;end
    else begin
      cycle<=cycle+1;
      assert(occupied_slots<=2&&result_slots_occupied<=2&&owners<=2);
      if(lr_valid&&lr_ready) $fwrite(trace_file,"%0d,MFLIT,%0d,%0d,%032x\n",cycle,lr_sop,lr_eop,lr_data);
      if(s_valid&&s_ready) $fwrite(trace_file,"%0d,SREQ,%0d,%0d,%032x\n",cycle,s_word,s_address,s_data);
      if(ack_valid&&ack_ready) $fwrite(trace_file,"%0d,SACK,%0d,%0d,%0d\n",cycle,ack_word,inject_wrong,committed_words);
      if(terminal_valid&&terminal_ready) $fwrite(trace_file,"%0d,TERM,%0d,%0d,%0d\n",cycle,terminal_ticket[31:0],terminal_stored,terminal_error);
      if(input_consumed_valid&&input_consumed_ready) begin
        input_ACKs<=input_ACKs+1;
        assert(input_consumed_ticket==native_ticket&&!input_consumed_error);
      end
      if(control_valid&&control_ready) begin
        control_beats<=control_beats+1;
        assert(control_data==lr_data&&control_sop==lr_sop&&control_eop==lr_eop);
      end
      if(c_rsp_valid[0]&&ack_ready&&allow_ACK&&!inject_wrong) assert(c_rsp_tag[31:0]=={31'b0,s_word});
      if(host_rsp_valid) assert(c_rsp_tag[63:32]==0);
    end
  end
  initial begin
    reset=1;cmd_valid=0;cmd_ticket=0;cmd_job_key=128'h00000001000000fa0000000100000001;
    cmd_abi=32'h02500001;cmd_topology=25001;cmd_capacity=1;cmd_numeric=32'h53333251;cmd_layout=32'h4b313633;
    cmd_resource=0;cmd_service=32;cmd_provider=1;cmd_function=0;cmd_native_op=0;cmd_payload=0;
    cmd_stored=0;cmd_store_words=0;cmd_destination=0;native_ready=0;
    lr_valid=0;lr_sop=0;lr_eop=0;lr_data=0;input_consumed_ready=1;control_ready=0;native_abort_ready=0;
    cancel_drained_valid=0;cancel_drained_ticket=0;terminal_ready=0;cancel_valid=0;cancel_job_key=cmd_job_key;
    timeout_valid=0;clear_quarantine=0;resume_after_drain=0;
    allow_request=0;allow_ACK=0;inject_wrong=0;host_valid=0;host_address=0;host_rsp_ready=0;
    seed=1;if($value$plusargs("SEED=%d",seed)) begin end
    trace_path="serial-m.csv";if($value$plusargs("TRACE=%s",trace_path)) begin end
    trace_file=$fopen(trace_path,"w");assert(trace_file!=0);
    pause(3);reset=0;pause();enqueue(1,1);enqueue(2,1);take_native(1,1);
    // RF before INPUT, wrong session, wrong metadata, and early snapshot EOP.
    flit(1,0,header(1,4,flags(1,1)));flit(0,1,meta(1,0,1));
    assert(occupied_slots==2&&result_slots_occupied==0&&!terminal_valid);
    input_consumed_ready=0;
    fork
      begin input_event(1,1);end
      begin pause(5);assert(input_consumed_valid&&!lr_ready&&input_ACKs==0);input_consumed_ready=1;end
    join
    flit(1,0,header(99,4,flags(1,1)));flit(0,1,0);
    flit(1,0,header(1,4,flags(1,1)));flit(0,0,meta(1,0,1)^128'd1);flit(0,1,0);
    flit(1,0,header(1,4,flags(1,1)));flit(0,0,meta(1,0,1));flit(0,1,128'hbad);
    flit(1,0,header(1,4,flags(1,1)));flit(0,0,meta(1,0,1));flit(0,0,128'hbad);
    flit(0,0,128'hbad);flit(0,1,0); // Missing high-word EOP: drain, no publication.
    assert(result_slots_occupied==0&&!s_valid&&!terminal_valid);
    rf_event(1,1);take_native(2,1);input_event(2,1);rf_event(2,1);pause(2);
    assert(result_slots_occupied==2&&occupied_slots==2&&!terminal_valid);
    allow_request=1;while(!c_rsp_valid[0]) @(negedge clk);
    inject_wrong=1;pause();inject_wrong=0;assert(!terminal_valid&&committed_words==0);
    allow_ACK=1;while(!terminal_valid) @(negedge clk);assert(committed_words==2);readback(1);take_terminal(1,1,0);
    while(!terminal_valid) @(negedge clk);assert(committed_words==4);readback(2);take_terminal(2,1,0);
    enqueue(3,0);take_native(3,0);input_event(3,0);rf_event(3,0);take_terminal(3,0,0);assert(committed_words==4);
    // Control frames have no result assembly or owner-release side effect.
    fork
      begin flit(1,0,header(0,10,16'h2000));flit(0,1,0);end
      begin pause(4);assert(control_valid&&control_sop&&!lr_ready);control_ready=1;end
    join
    assert(control_beats==2&&quiescent);
    enqueue(4,1);take_native(4,1);cancel_valid=1;pause();cancel_valid=0;
    assert(cancel_drained_ready);cancel_drained_valid=1;cancel_drained_ticket=ticket(99);pause();cancel_drained_valid=0;
    assert(occupied_slots==1&&!terminal_valid&&halted);
    input_event(4,1);rf_event(4,1);take_terminal(4,0,5);
    assert(committed_words==4&&quiescent&&!quarantine&&input_ACKs==4&&rejected_protocol_events>=7);
    resume_after_drain=1;pause();resume_after_drain=0;assert(!halted);
    // SPILL is a control-kind snapshot: no fake INPUT and final remains false.
    cmd_job_key[63:32]=2;cancel_job_key=cmd_job_key;
    enqueue(5,1);take_native(5,1);rf_event(5,1);
    while(!terminal_valid) @(negedge clk);readback(5);take_terminal(5,1,0);
    assert(quiescent&&committed_words==6&&input_ACKs==4);
    // Partial head cancellation reports prefix48, but never becomes a store
    // or permission to resume this K128 record at48.
    enqueue(6,1);take_native(6,1);cancel_valid=1;pause();cancel_valid=0;
    flit(1,0,header(6,5,16'h4000));flit(0,0,128'h00300006);flit(0,0,128'hbad);flit(0,1,128'h12345678);
    assert(!native_abort_valid&&occupied_slots==1&&!terminal_valid);
    flit(1,0,header(6,5,16'h4000));flit(0,0,128'h00300006);
    flit(0,0,{32'd250,cmd_job_key[63:32],32'd402,32'd1});flit(0,1,128'h12345678);
    assert(native_abort_valid&&native_abort_ticket==ticket(6)&&native_abort_next_k==48);
    pause(3);assert(native_abort_valid&&occupied_slots==1&&!terminal_valid);
    native_abort_ready=1;pause();native_abort_ready=0;
    pause(4);assert(occupied_slots==1&&!terminal_valid); // A/W/DMA proof still withheld.
    cancel_drained_ticket=ticket(6);cancel_drained_valid=1;
    do @(posedge clk);while(!cancel_drained_ready);@(negedge clk);cancel_drained_valid=0;
    take_terminal(6,0,5);assert(quiescent&&committed_words==6);
    $display("PASS serial_m_guard actualS seed=%0d cycles=%0d inputACK=%0d committed=%0d rejects=%0d",seed,cycle,input_ACKs,committed_words,rejected_protocol_events);
    $fclose(trace_file);$finish;
  end
  initial begin #300000;$fatal(1,"serial M guard timeout");end
endmodule
