`timescale 1ns/1ps
module tb_bounded_service_guard;
  logic clk, reset=1;
  initial clk=0;
  always #1 clk=~clk;
  logic cmd_valid=0,cmd_ready;
  logic [511:0] cmd_ticket=0;
  logic [127:0] cmd_job_key=128'h00000001000000fa0000000100000001;
  logic [31:0] cmd_abi=32'h02500001,cmd_topology=25001,cmd_capacity=1;
  logic [31:0] cmd_numeric=32'h53333251,cmd_layout=32'h4b313633;
  logic [7:0] cmd_resource=0,cmd_service=32;
  logic [7:0] cmd_provider=1,cmd_function=0;
  logic [15:0] cmd_native_op=0;
  logic [255:0] cmd_payload=0;
  logic cmd_stored=0;
  logic [1:0] cmd_store_words=0;
  logic [9:0] cmd_destination=0;
  logic native_valid,native_ready=0;
  logic [511:0] native_ticket;
  logic [7:0] native_resource,native_service;
  logic [255:0] native_payload;
  logic result_valid=0,result_ready;
  logic [511:0] result_ticket=0;
  logic [255:0] result_data=0;
  logic result_error=0;
  logic s_valid,s_ready=0;
  logic [511:0] s_ticket;
  logic s_word;
  logic [9:0] s_address;
  logic [127:0] s_data;
  logic ack_valid=0,ack_ready;
  logic [511:0] ack_ticket=0;
  logic ack_word=0,ack_error=0;
  logic terminal_valid,terminal_ready=0;
  logic [511:0] terminal_ticket;
  logic [7:0] terminal_error;
  logic terminal_stored,terminal_partial;
  logic [255:0] terminal_data;
  logic cancel_valid=0;
  logic [127:0] cancel_job_key=128'h00000001000000fa0000000100000001;
  logic timeout_valid=0,clear_quarantine=0,resume_after_drain=0;
  logic halted,quarantine,quiescent;
  logic [1:0] occupied_slots,result_slots_occupied;
  logic [31:0] rejected_protocol_events,committed_words;
  bounded_service_guard dut(.*);
  int seed=1, native_accepts;
  int trace_file,cycle;
  string trace_path;
  logic prev_native, prev_native_ready, prev_s,prev_s_ready;
  logic prev_terminal,prev_terminal_ready;
  logic [783:0] old_native;
  logic [650:0] old_s;
  logic [777:0] old_terminal;
  always @(posedge clk) begin
    if (reset) begin
      native_accepts<=0;
      cycle<=0;
      prev_native<=0;prev_native_ready<=0;prev_s<=0;prev_s_ready<=0;
      prev_terminal<=0;prev_terminal_ready<=0;
      old_native<=0;old_s<=0;old_terminal<=0;
    end else begin
      cycle<=cycle+1;
      $fwrite(trace_file,"%0d,RESULT_OCC,0,0,0,0,%0d,0,1,0\n",cycle,result_slots_occupied);
      if(cmd_valid&&cmd_ready) $fwrite(trace_file,"%0d,CMD,0,0,0,0,%0d,%0d,1,%032x\n",cycle,cmd_store_words,cmd_ticket[31:0],cmd_job_key);
      if(native_valid&&native_ready) $fwrite(trace_file,"%0d,NREQ,0,0,0,0,0,%0d,1,%032x\n",cycle,native_ticket[31:0],native_ticket[511:384]);
      if(result_valid&&result_ready) $fwrite(trace_file,"%0d,NRSP,0,0,0,0,0,%0d,%0d,%032x\n",cycle,result_ticket[31:0],dut.matching_result,result_ticket[511:384]);
      if(s_valid&&s_ready) $fwrite(trace_file,"%0d,SWRITE,0,0,0,0,%0d,%0d,1,%032x\n",cycle,s_word,s_ticket[31:0],s_ticket[511:384]);
      if(ack_valid&&ack_ready) $fwrite(trace_file,"%0d,SACK,0,0,0,0,%0d,%0d,%0d,%032x\n",cycle,ack_word,ack_ticket[31:0],dut.matching_ACK,ack_ticket[511:384]);
      if(terminal_valid&&terminal_ready) $fwrite(trace_file,"%0d,TERMINAL,0,0,0,0,%0d,%0d,1,%032x\n",cycle,terminal_error,terminal_ticket[31:0],terminal_ticket[511:384]);
      if (prev_native && !prev_native_ready)
        assert(native_valid && {native_ticket,native_resource,native_service,native_payload}==old_native) else $fatal(1,"native valid/payload withdrawn");
      if (prev_s && !prev_s_ready)
        assert(s_valid && {s_ticket,s_word,s_address,s_data}==old_s) else $fatal(1,"S valid/payload withdrawn");
      if (prev_terminal && !prev_terminal_ready)
        assert(terminal_valid && {terminal_ticket,terminal_error,terminal_stored,terminal_partial,terminal_data}==old_terminal) else $fatal(1,"terminal changed under backpressure");
      if (native_valid && native_ready) native_accepts<=native_accepts+1;
      assert(occupied_slots<=2) else $fatal(1,"slot overflow");
      assert(result_slots_occupied<=2) else $fatal(1,"result FIFO overflow");
      prev_native<=native_valid; prev_native_ready<=native_ready;
      prev_s<=s_valid; prev_s_ready<=s_ready;
      prev_terminal<=terminal_valid; prev_terminal_ready<=terminal_ready;
      old_native<={native_ticket,native_resource,native_service,native_payload};
      old_s<={s_ticket,s_word,s_address,s_data};
      old_terminal<={terminal_ticket,terminal_error,terminal_stored,terminal_partial,terminal_data};
    end
  end
  function automatic logic [511:0] ticket(input int id);
    logic [511:0] value;
    value='0; value[511:384]=cmd_job_key; value[31:0]=32'(id);
    return value;
  endfunction
  function automatic logic [255:0] data(input int id);
    return {32'(id+7),32'(id+6),32'(id+5),32'(id+4),32'(id+3),32'(id+2),32'(id+1),32'(id)};
  endfunction
  task automatic pause(input int n=1);
    repeat(n) @(negedge clk);
  endtask
  task automatic enqueue(input int id,input bit stored,input bit legacy=0);
    @(negedge clk);
    cmd_ticket=ticket(id);cmd_payload=data(id);cmd_stored=stored;
    cmd_store_words=stored?2:0;cmd_destination=100;
    cmd_abi=legacy?32'h00010001:32'h02500001;cmd_valid=1;
    do @(posedge clk); while (!cmd_ready);
    @(negedge clk);
    cmd_valid=0;
  endtask
  task automatic take_native(input int id);
    while(!native_valid) @(negedge clk);
    assert(native_ticket==ticket(id) && native_payload==data(id)) else $fatal(1,"native identity/data");
    pause(seed%3+1);native_ready=1;pause();native_ready=0;
  endtask
  task automatic respond(input int id,input bit foreign=0);
    @(negedge clk);result_ticket=ticket(id);
    if(foreign) result_ticket[383]=1;
    result_data=data(id);result_valid=1;
    pause();assert(result_ready) else $fatal(1,"result stalled unexpectedly");result_valid=0;
  endtask
  task automatic take_write(input int id,input bit word_index);
    logic [255:0] expected_data;
    expected_data=data(id);
    while(!s_valid) @(negedge clk);
    assert(s_ticket==ticket(id) && s_word==word_index && s_address==10'(100+int'(word_index))) else $fatal(1,"write identity/address");
    assert(s_data==(word_index?expected_data[255:128]:expected_data[127:0])) else $fatal(1,"write data");
    pause(seed%4+1);s_ready=1;pause();s_ready=0;
  endtask
  task automatic acknowledge(input int id,input bit word_index,input bit foreign=0,input bit failure=0);
    @(negedge clk);ack_ticket=ticket(id);if(foreign)ack_ticket[382]=1;
    ack_word=word_index;ack_error=failure;ack_valid=1;
    pause();assert(ack_ready) else $fatal(1,"ACK stalled");ack_valid=0;ack_error=0;
  endtask
  task automatic take_terminal(input int id,input logic [7:0] error_code,input bit stored,input bit partial_write=0);
    while(!terminal_valid) @(negedge clk);
    assert(terminal_ticket==ticket(id) && terminal_error==8'(error_code) && terminal_stored==stored && terminal_partial==partial_write) else $fatal(1,"terminal status id%0d err%0d",id,terminal_error);
    pause(seed%3+1);terminal_ready=1;pause();terminal_ready=0;
  endtask
  initial begin
    if($value$plusargs("SEED=%d",seed)) begin end
    trace_path=$sformatf("service-guard-%0d.csv",seed);
    if($value$plusargs("TRACE=%s",trace_path)) begin end
    trace_file=$fopen(trace_path,"w");assert(trace_file!=0) else $fatal(1,"cannot open trace");
    $fwrite(trace_file,"cycle,event,slot,generation,kk,use,detail,tag,match,object_key\n");
    pause(3);reset=0;pause();
    enqueue(1,1);enqueue(2,0);
    assert(!cmd_ready && occupied_slots==2) else $fatal(1,"third slot admitted");
    take_native(1);respond(1,1);respond(1);
    take_native(2);respond(2);
    assert(result_slots_occupied==2 && committed_words==0) else $fatal(1,"second result did not overlap pending first ACK");
    take_write(1,0);acknowledge(1,0,1);
    assert(committed_words==0 && !terminal_valid) else $fatal(1,"foreign ACK released owner");
    acknowledge(1,0);
    assert(committed_words==1 && !terminal_valid) else $fatal(1,"first ACK completed two words");
    take_write(1,1);pause(3);
    assert(!terminal_valid) else $fatal(1,"missing second ACK");
    acknowledge(1,1);take_terminal(1,0,1);
    take_terminal(2,0,0);
    enqueue(3,0,1);take_terminal(3,1,0);
    assert(native_accepts==2) else $fatal(1,"legacy ABI reached provider");
    enqueue(4,1);take_native(4);respond(4);
    while(!s_valid) @(negedge clk);
    cancel_valid=1;pause();cancel_valid=0;
    assert(halted && s_valid) else $fatal(1,"cancel withdrew proposed write");
    take_write(4,0);timeout_valid=1;pause();timeout_valid=0;
    clear_quarantine=1;pause();clear_quarantine=0;
    assert(quarantine && !quiescent) else $fatal(1,"timeout freed owner");
    acknowledge(4,0);take_terminal(4,5,0,1);
    while(!quiescent) @(negedge clk);
    clear_quarantine=1;pause();clear_quarantine=0;
    resume_after_drain=1;pause();resume_after_drain=0;
    assert(!halted && !quarantine) else $fatal(1,"drained retry not released");
    enqueue(10,0);take_terminal(10,1,0);
    cmd_job_key=128'h00000002000000fa0000000200000002;cancel_job_key=cmd_job_key;
    enqueue(5,0);enqueue(6,0);
    while(!native_valid) @(negedge clk);
    cancel_valid=1;pause();cancel_valid=0;
    take_native(5);respond(5);take_terminal(5,5,0);take_terminal(6,5,0);
    while(!quiescent) @(negedge clk);
    resume_after_drain=1;pause();resume_after_drain=0;
    cmd_job_key=128'h00000003000000fa0000000300000003;cancel_job_key=cmd_job_key;
    enqueue(7,1);take_native(7);respond(7);take_write(7,0);acknowledge(7,0,0,1);take_terminal(7,3,0);
    cmd_resource=2;cmd_provider=2;
    enqueue(8,0);take_terminal(8,1,0);
    cmd_provider=1;cmd_function=1;
    enqueue(9,0);take_terminal(9,1,0);
    assert(committed_words==3 && native_accepts==5 && rejected_protocol_events>=3) else $fatal(1,"accounting mismatch");
    $display("PASS bounded-service-guard seed=%0d commits=%0d rejected=%0d native=%0d",seed,committed_words,rejected_protocol_events,native_accepts);
    $fclose(trace_file);
    $finish;
  end
  initial begin #20000; $fatal(1,"test timeout"); end
endmodule
