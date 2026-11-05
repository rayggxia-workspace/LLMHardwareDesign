module tb_pj;
 logic clk=0, reset=1;
 always #5 clk=~clk;
 logic [1:0] io_req_valid=0,io_req_write=0,io_rsp_ready=0;
 logic [19:0] io_req_addr=0;
 logic [255:0] io_req_data=0;
 wire [1:0] io_req_ready,io_rsp_valid;
 wire [255:0] io_rsp_data;
 task automatic access(input bit wr,input logic [9:0] addr,input logic [127:0] val,output logic [127:0] result);
  @(negedge clk);
  io_req_valid=1; io_req_write={1'b0,wr}; io_req_addr={10'b0,addr}; io_req_data={128'b0,val};
  do @(posedge clk); while(!io_req_ready[0]);
  @(negedge clk); io_req_valid=0;
  repeat(3) @(negedge clk);
  io_rsp_ready=1;
  do @(posedge clk); while(!io_rsp_valid[0]);
  result=io_rsp_data[127:0];
  @(negedge clk); io_rsp_ready=0;
 endtask
 logic [127:0] got;
 initial begin
  repeat(3) @(negedge clk);
  reset=0;
 end
 initial begin
  repeat(5000) @(posedge clk);
  $fatal(1,"handshake watchdog");
 end
`ifdef TEST_P
 logic load_valid=0,load_take=0,cmd_valid=0,cmd_store=0,gate_valid=0,cmd_route=0,cmd_pack16=0,gate_route=0,bridge=0;
 wire route_valid,route_take;
 wire [31:0] route_data;
 logic [3:0] cmd_op=0;
 logic [63:0] cmd_data=0;
 wire load_ready,load_done,load_error,cmd_ready,cmd_done,cmd_error,gate_ready,gate_done,gate_error;
 block_p16 dut(
  .clk(clk),.reset(reset),.io_req_valid(io_req_valid),.io_req_write(io_req_write),
  .io_req_addr(io_req_addr),.io_req_data(io_req_data),.io_req_ready(io_req_ready),
  .io_rsp_valid(io_rsp_valid),.io_rsp_ready(io_rsp_ready),.io_rsp_data(io_rsp_data),
  .load_valid(load_valid),.load_ready(load_ready),.load_bank(1'b0),.load_rows(4'd1),.load_tiles(3'd1),
  .load_a_wide(1'b0),.load_b_wide(1'b0),.load_reuse_b(1'b0),.load_a_base(10'd0),.load_b_base(10'd4),
  .load_done(load_done),.load_take(load_take),.load_error(load_error),
  .cmd_valid(cmd_valid),.cmd_ready(cmd_ready),.cmd_op(cmd_op),.cmd_index(6'b0),.cmd_data(cmd_data),
  .cmd_store(cmd_store),.cmd_route(cmd_route),.cmd_pack16(cmd_pack16),.cmd_dst(cmd_pack16 ? 10'd12 : 10'd8),.cmd_done(cmd_done),.cmd_take(1'b1),
  .cmd_error(cmd_error),.cmd_saturated(),.cmd_result(),
  .gate_valid(gate_valid),.gate_route(gate_route),.gate_ready(gate_ready),.gate_a(10'd12),.gate_b(10'd13),.gate_dst(10'd14),
  .gate_done(gate_done),.gate_take(1'b1),.gate_error(gate_error),.gate_saturated(),
  .m_to_g_valid(route_valid),.m_to_g_data(route_data),.m_to_g_take(bridge && route_take),
  .g_from_m_valid(bridge && route_valid),.g_from_m_data(route_data),.g_from_m_take(route_take));
 task automatic m_cmd(input logic [3:0] op,input logic [63:0] data,input bit writes,input bit expect_error);
  @(negedge clk); cmd_valid=1;cmd_op=op;cmd_data=data;cmd_store=writes;
  do @(posedge clk); while(!cmd_ready);
  @(negedge clk);cmd_valid=0;
  do @(posedge clk); while(!cmd_done);
  if(cmd_error!==expect_error) $fatal(1,"M command %0d error=%b",op,cmd_error);
 endtask
 task automatic gate_cmd;
  @(negedge clk);gate_valid=1;
  do @(posedge clk);while(!gate_ready);
  @(negedge clk);gate_valid=0;
  do @(posedge clk);while(!gate_done);
  if(gate_error) $fatal(1,"G command failed");
 endtask
 logic [127:0] replay;
 initial begin
  wait(!reset);
  access(1,0,128'd2,got);
  access(1,1,0,got);
  access(1,2,0,got);
  access(1,3,0,got);
  access(1,4,128'hfb0000000000000003,got);
  access(1,5,0,got);
  access(1,6,0,got);
  access(1,7,0,got);
  @(negedge clk);load_valid=1;
  do @(posedge clk);while(!load_ready);
  @(negedge clk);load_valid=0;
  do @(posedge clk);while(!load_done);
  if(load_error) $fatal(1,"M feed failed");
  repeat(3) begin
   @(negedge clk);
   if(!load_done || load_error || load_ready) $fatal(1,"feed completion did not hold");
  end
  load_take=1;
  @(negedge clk);load_take=0;
  if(load_done || !load_ready) $fatal(1,"feed completion did not release");
  m_cmd(10,64'h9214,0,0);
  m_cmd(10,64'h9210,0,0);
  m_cmd(5,64'h101,1,0);
  access(0,8,0,got);
  if(got!==128'hfffffff600000006) $fatal(1,"M rounded writeback got %h",got);
  m_cmd(15,0,1,1);
  access(0,8,0,got);
  if(got!==128'hfffffff600000006) $fatal(1,"failed M command wrote SRAM");
  access(1,12,128'hd8f0_2710,got);
  access(1,13,128'h0400_0200,got);
  gate_cmd();
  access(0,14,0,got);
  if(got!==128'd5000) $fatal(1,"G writeback got %h",got);
  @(negedge clk);cmd_pack16=1;
  m_cmd(5,64'h100,1,0);
  access(0,12,0,got);
  if(got!==128'hffec000c) $fatal(1,"M signed lane packing got %h",got);
  @(negedge clk);cmd_pack16=0;
  gate_cmd();
  access(0,14,0,replay);
  @(negedge clk);cmd_route=1;
  m_cmd(5,64'h100,0,0);
  repeat(4) begin
   @(negedge clk);
   if(!route_valid || route_data!==32'hffec000c || cmd_ready) $fatal(1,"direct launch did not hold");
  end
  access(1,12,128'h2710,got); // The bypass must ignore this stale replay slot.
  @(negedge clk);gate_route=1;bridge=1;
  gate_cmd();
  access(0,14,0,got);
  if(route_valid || got!==replay) $fatal(1,"direct route differs from SRAM replay");
  $display("PASS P16 feed, two K segments, writeback, invalid command, gated SiLU and direct equivalence");
  $finish;
 end
`else
 logic start=0,done_take=0,out_take=0,release_valid=0,join_three=0,rx_last=0;
 logic [31:0] rx_tag=32'h01000007,join_tag=32'h01000008;
 logic [1:0] rx_slot=0;
 wire start_ready,done_valid,done_error,out_valid,out_last,release_ready,rx_error;
 wire [127:0] out_data;
 wire [31:0] out_tag;
 wire [9:0] out_index;
 block_j16 dut(
  .clk(clk),.reset(reset),.io_req_valid(io_req_valid),.io_req_write(io_req_write),
  .io_req_addr(io_req_addr),.io_req_data(io_req_data),.io_req_ready(io_req_ready),
  .io_rsp_valid(io_rsp_valid),.io_rsp_ready(io_rsp_ready),.io_rsp_data(io_rsp_data),
  .active_epoch(8'd1),.rx_tag(rx_tag),.rx_slot(rx_slot),.rx_last(rx_last),.rx_error(rx_error),
  .start(start),.start_ready(start_ready),.join_tag(join_tag),.join_three(join_three),
  .result_addr(10'd12),.words(10'd2),.done_valid(done_valid),.done_take(done_take),.done_error(done_error),
  .out_valid(out_valid),.out_take(out_take),.out_data(out_data),.out_tag(out_tag),
  .out_index(out_index),.out_last(out_last),.release_valid(release_valid),.release_ready(release_ready));
 task automatic receive_word(input logic [1:0] slot,input logic [9:0] addr,
                             input bit last,input logic [127:0] data,input bit expect_error);
  @(negedge clk);
  rx_slot=slot;rx_last=last;
  io_req_valid=1;io_req_write=1;io_req_addr={10'b0,addr};io_req_data={128'b0,data};
  do @(posedge clk);while(!io_req_ready[0]);
  @(negedge clk);io_req_valid=0;
  repeat(3) @(negedge clk);
  io_rsp_ready=1;
  do @(posedge clk);while(!io_rsp_valid[0]);
  if(rx_error!==expect_error) $fatal(1,"J RX slot=%d addr=%d error=%b",slot,addr,rx_error);
  @(negedge clk);io_rsp_ready=0;
 endtask
 task automatic begin_join(input bit expect_error);
  @(negedge clk);start=1;
  do @(posedge clk);while(!start_ready);
  @(negedge clk);start=0;
  do @(posedge clk);while(!done_valid);
  if(done_error!==expect_error) $fatal(1,"J done_error=%b",done_error);
  @(negedge clk);done_take=1;
  @(negedge clk);done_take=0;
 endtask
 task automatic tx_check(input logic [127:0] expected);
  @(negedge clk);io_req_valid=2;io_req_write=0;io_req_addr={10'd12,10'b0};
  do @(posedge clk);while(!io_req_ready[1]);
  @(negedge clk);io_req_valid=0;io_rsp_ready=2;
  do @(posedge clk);while(!io_rsp_valid[1]);
  if(io_rsp_data[255:128]!==expected) $fatal(1,"J SRAM writeback incorrect");
  @(negedge clk);io_rsp_ready=0;
 endtask
 task automatic drain(input logic [15:0] first,input logic [15:0] second);
  do @(posedge clk);while(!out_valid);
  repeat(5) begin
   @(negedge clk);
   if(!out_valid || out_data!=={8{first}} || out_tag!=join_tag || out_index!=0 || out_last)
    $fatal(1,"J held result corrupt");
  end
  out_take=1;
  @(negedge clk);
  if(!out_valid || out_data!=={8{second}} || out_index!=1 || !out_last)
   $fatal(1,"J last result corrupt");
  @(negedge clk);out_take=0;
  tx_check({8{first}});
  @(negedge clk);release_valid=1;
  if(!release_ready) $fatal(1,"J never released lease");
  @(negedge clk);release_valid=0;
 endtask
 initial begin
  wait(!reset);
  rx_tag=32'h00000007;
  receive_word(0,4,0,{8{16'd5}},1); // Reject an old epoch.
  rx_tag=32'h01000007;
  receive_word(1,8,0,{8{16'd8}},0);
  receive_word(1,10,1,{8{16'd8}},1); // Reject a missing word.
  receive_word(1,9,1,{8{16'd8}},0);
  receive_word(0,8,0,{8{16'd5}},1); // Reject an overlapping branch.
  receive_word(0,4,0,{8{16'd5}},0);
  receive_word(0,5,1,{8{16'h7fff}},0);
  begin_join(1);
  if(out_valid) $fatal(1,"mismatched tag published output");
  join_tag=rx_tag;
  begin_join(0);
  drain(16'd13,16'h7fff);

  rx_tag=32'h01000008;join_tag=rx_tag;join_three=1;
  receive_word(2,0,0,{8{16'h8000}},0);
  receive_word(2,1,1,{8{16'd2}},0);
  receive_word(1,8,0,{8{16'd100}},0);
  receive_word(1,9,1,{8{16'd3}},0);
  receive_word(0,4,0,{8{16'h7fff}},0);
  begin_join(1);
  receive_word(0,5,1,{8{16'd4}},0);
  begin_join(0);
  drain(16'd99,16'd9);
  $display("PASS J16 stale/mismatched/incomplete/overlapping RX rejection, two and three branches, stalled T lease");
  $finish;
 end
`endif
endmodule
