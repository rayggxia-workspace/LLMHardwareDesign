// Native P16 operand, command, and SRAM response exercise. The test driver
// is an integration fixture. It does not stand in for the programmable MC/LC.
module native_p(input logic clk, reset);
  logic req=0, wr=0, rsp_take=0;
  logic [9:0] address=0;
  logic [127:0] data=0;
  wire [1:0] ready, rsp;
  wire [255:0] result;
  logic load=0, cmd=0, store=0, gated=0;
  logic [9:0] cmd_dst=0;
  logic [3:0] op=0;
  logic [63:0] arg=0;
  wire load_ready, load_done, load_error, cmd_ready, cmd_done, cmd_error;
  wire gate_ready, gate_done, gate_error;

  block_p16 dut (
    .clk(clk), .reset(reset),
    .io_req_valid({1'b0,req}), .io_req_write({1'b0,wr}),
    .io_req_addr({10'b0,address}), .io_req_data({128'b0,data}),
    .io_req_ready(ready), .io_rsp_valid(rsp), .io_rsp_ready({1'b0,rsp_take}),
    .io_rsp_data(result),
    .load_valid(load), .load_ready(load_ready), .load_bank(1'b0),
    .load_rows(4'd1), .load_tiles(3'd4), .load_a_wide(1'b0), .load_b_wide(1'b0),
    .load_reuse_b(1'b0), .load_a_base(10'd0), .load_b_base(10'd16),
    .load_done(load_done), .load_take(1'b1), .load_error(load_error),
    .cmd_valid(cmd), .cmd_ready(cmd_ready), .cmd_op(op), .cmd_index(6'b0),
    .cmd_data(arg), .cmd_store(store), .cmd_route(1'b0), .cmd_pack16(store),
    .cmd_dst(cmd_dst), .cmd_done(cmd_done), .cmd_take(1'b1), .cmd_error(cmd_error),
    .cmd_saturated(), .cmd_result(),
    .gate_valid(gated), .gate_route(1'b0), .gate_ready(gate_ready),
    .gate_a(10'd32), .gate_b(10'd33), .gate_dst(10'd34),
    .gate_done(gate_done), .gate_take(1'b1), .gate_error(gate_error),
    .gate_saturated(), .m_to_g_valid(), .m_to_g_data(), .m_to_g_take(1'b0),
    .g_from_m_valid(1'b0), .g_from_m_data(32'b0), .g_from_m_take());

  task automatic access(input bit write, input int addr,
    input logic [127:0] value, input int stall, output logic [127:0] got);
    @(negedge clk);
    req=1; wr=write; address=10'(addr); data=value;
    do @(posedge clk); while(!ready[0]);
    @(negedge clk); req=0;
    if(stall != 0) begin
      wait(rsp[0]);
      repeat(stall) begin
        @(negedge clk);
        if(!rsp[0]) $fatal(1, "SRAM response dropped under backpressure");
      end
    end
    rsp_take=1;
    do @(posedge clk); while(!rsp[0]);
    got=result[127:0];
    @(negedge clk); rsp_take=0;
  endtask

  task automatic command(input int code, input logic [63:0] argument,
    input bit write, input int dest, input bit expected_error);
    @(negedge clk);
    cmd=1; op=4'(code); arg=argument; store=write; cmd_dst=10'(dest);
    do @(posedge clk); while(!cmd_ready);
    @(negedge clk); cmd=0;
    do @(posedge clk); while(!cmd_done);
    if(cmd_error!==expected_error) $fatal(1,"native M command %0d unexpected status", code);
  endtask

  task automatic project(input logic [127:0] words[0:2559], input int dest);
    logic [127:0] ignored;
    command(4,64'd1,0,0,0);
    for(int seg=0;seg<80;seg++) begin
      for(int i=0;i<32;i++) access(1,i,words[32*seg+i],0,ignored);
      @(negedge clk); load=1;
      do @(posedge clk); while(!load_ready);
      @(negedge clk); load=0;
      do @(posedge clk); while(!load_done);
      if(load_error) $fatal(1,"native feeder failed");
      command(10,seg==0?64'hc284:64'hc280,0,0,0);
    end
    command(5,64'h102,1,dest,0);
  endtask

  task automatic gate;
    @(negedge clk); gated=1;
    do @(posedge clk); while(!gate_ready);
    @(negedge clk); gated=0;
    do @(posedge clk); while(!gate_done);
    if(gate_error) $fatal(1,"native G failed");
  endtask
endmodule

module tb_ffn;
  logic clk=0, reset=1;
  always #5 clk=~clk;
  native_p p0(clk,reset), p1(clk,reset);
  logic [127:0] g[0:2559], u[0:2559], expected[0:2];
  logic [127:0] got, tx, ignored;
  string vectors;
  int split, stall;
  initial begin
    if(!$value$plusargs("vectors=%s",vectors) ||
       !$value$plusargs("split=%d",split) ||
       !$value$plusargs("stall=%d",stall)) $fatal(1,"missing test input");
    $readmemh({vectors,"/gate.hex"},g);
    $readmemh({vectors,"/up.hex"},u);
    $readmemh({vectors,"/expected.hex"},expected);
    repeat(4) @(negedge clk);
    reset=0;
    if(split) begin
      fork
        p0.project(g,32);
        p1.project(u,33);
      join
      p1.access(0,33,0,0,tx);
      if(tx!==expected[1]) $fatal(1,"native up source mismatch got %h expected %h",tx,expected[1]);
      $display("TRACE up_in_flight");
      p0.access(1,33,tx,stall,ignored);
      $display("TRACE up_rx_stored");
      $display("TRACE up_source_release");
    end else begin
      p0.project(g,32);
      p0.project(u,33);
    end
    p0.access(0,32,0,0,got);
    if(got!==expected[0]) $fatal(1,"native gate mismatch got %h expected %h",got,expected[0]);
    p0.access(0,33,0,0,got);
    if(got!==expected[1]) $fatal(1,"native up mismatch got %h expected %h",got,expected[1]);
    p0.gate();
    p0.access(0,34,0,0,got);
    if(got!==expected[2]) $fatal(1,"native mid mismatch got %h expected %h",got,expected[2]);
    $display("TRACE mid_stored %h",got);
    p0.command(15,0,1,34,1);
    p0.access(0,34,0,0,got);
    if(got!==expected[2]) $fatal(1,"failed command modified SRAM");
    $display("PASS native P16 FFN split=%0d stall=%0d",split,stall);
    $finish;
  end
  initial begin
    repeat(200000) @(posedge clk);
    $fatal(1,"watchdog");
  end
endmodule

