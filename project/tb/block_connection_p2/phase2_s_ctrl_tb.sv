`timescale 1ns/1ps
module phase2_s_ctrl_tb;
  reg clk=0;
  always #5 clk=~clk;
  reg resetn=0;
  reg req_valid=0,req_write=0,rsp_ready=0;
  reg [9:0] req_addr=0;
  reg [127:0] req_data=0;
  wire req_ready,rsp_valid,rsp_error;
  wire [127:0] rsp_data;
  wire h_req,h_we,h_take;
  wire [9:0] h_addr;
  wire [127:0] h_din;
  reg allow_req=1,allow_ack=1;
  wire native_req=h_req&&allow_req;
  wire native_take=h_take&&allow_ack;
  wire native_ready,native_valid;
  wire [127:0] native_data;
  integer cycles=0,generic_requests=0,native_requests=0,native_acks=0,generic_responses=0;
  integer completed_transactions=0;
  block_p2_s_ctrl dut(.clk(clk),.resetn(resetn),.req_valid(req_valid),.req_ready(req_ready),
    .req_write(req_write),.req_addr(req_addr),.req_data(req_data),.rsp_valid(rsp_valid),
    .rsp_ready(rsp_ready),.rsp_data(rsp_data),.rsp_error(rsp_error),
    .s_req(h_req),.s_we(h_we),.s_addr(h_addr),.s_din(h_din),.s_rsp_ready(h_take),
    .s_ready(native_ready&&allow_req),.s_rsp_valid(native_valid&&allow_ack),.s_dout(native_data));
  block_feed_s16k storage(.clk(clk),.reset(!resetn),.req(native_req),.wr(h_we),.addr(h_addr),.din(h_din),
    .ready(native_ready),.valid(native_valid),.take(native_take),.dout(native_data),
    .wide_req(1'b0),.wide_addr(8'd0),.wide_ready(),.wide_valid(),.wide_take(1'b0),.wide_dout());

  always @(posedge clk) begin
    cycles=cycles+1;
    if(cycles>20000) $fatal(1,"FAIL_P2 helper timeout");
    if(resetn) begin
      if(req_valid&&req_ready) generic_requests=generic_requests+1;
      if(native_req&&native_ready) native_requests=native_requests+1;
      if(native_valid&&native_take) native_acks=native_acks+1;
      if(rsp_valid&&rsp_ready) generic_responses=generic_responses+1;
      if(rsp_valid&&rsp_error!==1'b0) $fatal(1,"FAIL_P2 native S has no error pin");
    end
  end

  task automatic reset_pair;
    begin
      @(negedge clk); resetn=0;req_valid=0;rsp_ready=0;allow_req=1;allow_ack=1;
      repeat(3) @(negedge clk);
      if(req_ready||rsp_valid||h_req||h_take) $fatal(1,"FAIL_P2 reset masks handshakes");
      resetn=1;
      @(negedge clk);
      if(!req_ready) $fatal(1,"FAIL_P2 helper not idle after coordinated reset");
    end
  endtask

  task automatic transaction;
    input wr;
    input [9:0] addr;
    input [127:0] data,expected;
    input integer request_stalls,ack_stalls,response_stalls;
    integer gr,nr,na,gs,j;
    begin
      gr=generic_requests;nr=native_requests;na=native_acks;gs=generic_responses;
      @(negedge clk);req_valid=1;req_write=wr;req_addr=addr;req_data=data;
      rsp_ready=0;allow_req=0;allow_ack=0;
      while(!req_ready) @(negedge clk);
      @(posedge clk);#1;
      @(negedge clk);req_valid=0;req_write=!wr;req_addr=10'd999;req_data=128'hbad;
      for(j=0;j<request_stalls;j=j+1) begin
        if(!h_req||h_we!==wr||h_addr!==addr||h_din!==data||req_ready)
          $fatal(1,"FAIL_P2 captured request did not hold under S request stall");
        @(negedge clk);
      end
      allow_req=1;
      @(posedge clk);#1;
      @(negedge clk);
      for(j=0;j<ack_stalls;j=j+1) begin
        if(!native_valid||native_data!==expected||rsp_valid||req_ready)
          $fatal(1,"FAIL_P2 native S response/ACK lost under stall");
        @(negedge clk);
      end
      allow_ack=1;
      while(!rsp_valid) @(negedge clk);
      for(j=0;j<response_stalls;j=j+1) begin
        if(!rsp_valid||rsp_data!==expected||rsp_error||req_ready||h_req||h_take)
          $fatal(1,"FAIL_P2 helper response did not hold exactly once");
        @(negedge clk);
      end
      if(rsp_data!==expected) $fatal(1,"FAIL_P2 helper response data mismatch");
      rsp_ready=1;
      @(posedge clk);#1;
      @(negedge clk);rsp_ready=0;
      if(!req_ready||rsp_valid) $fatal(1,"FAIL_P2 generic response was not consumed");
      if(generic_requests!=gr+1||native_requests!=nr+1||native_acks!=na+1||generic_responses!=gs+1)
        $fatal(1,"FAIL_P2 request/ACK accounting mismatch gr=%0d nr=%0d na=%0d gs=%0d",
          generic_requests-gr,native_requests-nr,native_acks-na,generic_responses-gs);
      completed_transactions=completed_transactions+1;
    end
  endtask

  task automatic submit_for_reset;
    input [127:0] data;
    input accept_native;
    begin
      @(negedge clk);allow_req=accept_native;allow_ack=0;req_valid=1;req_write=1;
      req_addr=10'd11;req_data=data;rsp_ready=0;
      while(!req_ready) @(negedge clk);
      @(posedge clk);#1;
      @(negedge clk);req_valid=0;
      if(accept_native) begin
        while(!native_valid) @(negedge clk);
        if(native_data!==data) $fatal(1,"FAIL_P2 accepted write ACK should equal new din");
      end else begin
        repeat(4) @(negedge clk);
        if(!h_req||native_valid) $fatal(1,"FAIL_P2 queued write unexpectedly issued");
      end
    end
  endtask

  initial begin
    reset_pair();
    transaction(1,10'd11,128'h0123456789abcdeffedcba9876543210,128'h0123456789abcdeffedcba9876543210,5,7,6);
    transaction(0,10'd11,0,128'h0123456789abcdeffedcba9876543210,3,4,5);
    transaction(1,10'd11,128'h88776655443322110011223344556677,128'h88776655443322110011223344556677,4,5,7);
    transaction(0,10'd11,0,128'h88776655443322110011223344556677,2,3,4);
    $display("CASE_PASS H01_CAPTURE_REQUEST_BACKPRESSURE");
    $display("CASE_PASS H02_NATIVE_WRITE_ACK_AND_READBACK");
    $display("CASE_PASS H03_RESPONSE_HOLD_EXACTLY_ONCE");
    // A queued-but-unaccepted write is cancelled by coordinated reset.
    submit_for_reset(128'hdeaddeaddeaddead,0);reset_pair();
    transaction(0,10'd11,0,128'h88776655443322110011223344556677,2,2,3);
    $display("CASE_PASS H04_RESET_BEFORE_NATIVE_ACCEPT");
    // Accepted S writes survive reset: reset clears response lifecycle, not RAM.
    submit_for_reset(128'h112233445566778899aabbccddeeff00,1);reset_pair();
    transaction(0,10'd11,0,128'h112233445566778899aabbccddeeff00,2,3,4);
    $display("CASE_PASS H05_RESET_AFTER_WRITE_PRESERVES_PAYLOAD");
    transaction(1,10'd12,128'h55,128'h55,1,1,1);
    transaction(0,10'd12,0,128'h55,1,1,1);
    if(completed_transactions!=8) $fatal(1,"FAIL_P2 transaction count");
    $display("CASE_PASS H06_REPEAT_TRANSACTION");
    $display("PASS_P2_S_CTRL completed=%0d gr=%0d native_req=%0d native_ack=%0d generic_rsp=%0d cycles=%0d",
      completed_transactions,generic_requests,native_requests,native_acks,generic_responses,cycles);
    $finish;
  end
endmodule
