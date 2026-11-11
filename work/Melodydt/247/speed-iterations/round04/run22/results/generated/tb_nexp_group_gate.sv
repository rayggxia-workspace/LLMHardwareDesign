// Four instances are testbench-only: all BATCH/DIRECT parameter combinations.
module tb_nexp_group_gate #(parameter integer LANES=2);
 reg clk=0,reset=1,cv=0,take=0;always #5 clk=~clk;
 wire [3:0] ready,done,error;wire [511:0] result;
 for(genvar i=0;i<4;i++)begin: combos
  pu_u_group #(.NEXP_BATCH(i%2),.NEXP_DIRECT(i/2),.NEXP_DIRECT_LANES(LANES)) dut(.clk,.reset,
   .n_cmd_valid(cv),.n_cmd_store(1'b0),.n_cmd_direct(1'b0),.n_done_ready(take),.n_cmd_ready(ready[i]),
   .n_done_valid(done[i]),.n_done_error(error[i]),.n_done_saturated(),.n_cmd_meta(40'h000000001c),.n_cmd_sources(2'd0),
   .n_cmd_src(20'd0),.n_cmd_dst(10'd0),.n_done_data(result[128*i+:128]),.n_to_e_valid(),.n_to_e_ready(1'b1),.n_to_e_data(),
   .e_cmd_valid(1'b0),.e_cmd_store(1'b0),.e_cmd_direct_a(1'b0),.e_done_ready(1'b1),.e_cmd_ready(),.e_done_valid(),.e_done_error(),.e_done_saturated(),
   .e_cmd_sources(2'd0),.e_cmd_op(4'd0),.e_cmd_shift(5'd0),.e_cmd_src(30'd0),.e_cmd_dst(10'd0),.e_done_data(),
   .e_direct_a_valid(1'b0),.e_direct_a_abort(1'b0),.e_direct_a_ready(),.e_direct_a_data(128'd0),
   .io_req_valid(2'd0),.io_req_write(2'd0),.io_rsp_ready(2'd0),.io_req_addr(20'd0),.io_req_data(256'd0),.io_req_ready(),.io_rsp_valid(),.io_rsp_data());
 end
 integer guard;
 initial begin
  repeat(4)@(negedge clk);reset=0;@(negedge clk);cv=1;
  @(posedge clk);if(ready!==4'b1111)$fatal(1,"group gate accept");@(negedge clk);cv=0;guard=0;
  while(done!=4'b1111)begin @(negedge clk);guard++;if(guard>128)$fatal(1,"group gate timeout");end
  if(error!==4'b0111||result[511:384]!==128'd32768||result[383:0]!==0)$fatal(1,"BATCH/DIRECT native gate");
  repeat(4)begin @(negedge clk);if(done!==4'b1111||ready!==0)$fatal(1,"gate completion backpressure");end
  take=1;@(posedge clk);@(negedge clk);take=0;
  $display("GROUP_GATE_PASS combinations=4");$finish;
 end
 initial begin #200000;$fatal(1,"group gate watchdog");end
endmodule
