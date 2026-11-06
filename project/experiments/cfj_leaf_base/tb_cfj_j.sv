module tb_cfj_j;
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
 logic start=0,done_take=0,out_take=0,release_valid=0,join_three=0,rx_last=0;
 logic [31:0] rx_tag=32'h01000007,join_tag=32'h01000008;
 logic [1:0] rx_slot=0;
 wire start_ready,done_valid,done_error,out_valid,out_last,release_ready,rx_error;
 wire [127:0] out_data;
 wire [31:0] out_tag;
 wire [9:0] out_index;
 wire late_e_valid,late_s_take;
 wire [127:0] late_e_data;
 block_cfj_j #(.LATE_E_WRITEBACK(1)) dut(
  .clk(clk),.reset(reset),.io_req_valid(io_req_valid),.io_req_write(io_req_write),
  .io_req_addr(io_req_addr),.io_req_data(io_req_data),.io_req_ready(io_req_ready),
  .io_rsp_valid(io_rsp_valid),.io_rsp_ready(io_rsp_ready),.io_rsp_data(io_rsp_data),
  .active_epoch(8'd1),.rx_tag(rx_tag),.rx_slot(rx_slot),.rx_last(rx_last),.rx_error(rx_error),
  .start(start),.start_ready(start_ready),.join_tag(join_tag),.join_three(join_three),
  .result_addr(10'd12),.words(10'd2),.done_valid(done_valid),.done_take(done_take),.done_error(done_error),
  .out_valid(out_valid),.out_take(out_take),.out_data(out_data),.out_tag(out_tag),
  .out_index(out_index),.out_last(out_last),.release_valid(release_valid),.release_ready(release_ready),
  .late_e_valid,.late_e_data,.late_e_take(late_s_take),
  .late_s_valid(late_e_valid),.late_s_data(late_e_data),.late_s_take);
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
  rx_tag=32'h01000009;
  receive_word(0,4,0,{8{16'd5}},1);
  rx_tag=32'h01000007;
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
 initial begin
  #50000;
  $fatal(1,"J timeout");
 end
endmodule
