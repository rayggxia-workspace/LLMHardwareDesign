// Actual P/non-P SRAM leaves, at their ordinary request/response ports.
module native_s_io;
 reg clk=0,reset=1;
 always #5 clk=~clk;
 reg [1:0] req_valid=0,req_write=0,rsp_ready=0;
 reg [9:0] address[0:1];
 reg [127:0] data[0:1];
 wire [1:0] req_ready,rsp_valid;
 wire [127:0] result[0:1];
 local_s_base normal(.clk(clk),.reset(reset),.req_valid(req_valid[0]),.req_write(req_write[0]),
  .req_addr(address[0]),.req_data(data[0]),.req_ready(req_ready[0]),.rsp_valid(rsp_valid[0]),
  .rsp_ready(rsp_ready[0]),.rsp_data(result[0]));
 local_s_p feeder(.clk(clk),.reset(reset),.req_valid(req_valid[1]),.req_write(req_write[1]),
  .req_addr(address[1]),.req_data(data[1]),.req_ready(req_ready[1]),.rsp_valid(rsp_valid[1]),
  .rsp_ready(rsp_ready[1]),.rsp_data(result[1]),
  .load_valid(1'b0),.load_bank(1'b0),.load_a_wide(1'b0),.load_b_wide(1'b0),.load_reuse_b(1'b0),
  .load_rows(4'd0),.load_tiles(3'd0),.load_a_base(10'd0),.load_b_base(10'd0),
  .load_ready(),.done_valid(),.done_error(),.done_take(1'b1),.a_ready(1'b1),.b_ready(1'b1),
  .a_valid(),.a_bank(),.a_wide(),.a_row(),.a_tile(),.a_data(),
  .b_valid(),.b_bank(),.b_wide(),.b_half(),.b_tile(),.b_data());
 task automatic access(input integer p,input bit wr,input integer addr,input logic [127:0] value);
  time began;
  @(negedge clk);began=$time;
  address[p]=10'(addr);data[p]=value;req_write[p]=wr;req_valid[p]=1;
  do @(posedge clk);while(!req_ready[p]);
  @(negedge clk);req_valid[p]=0;
  while(!rsp_valid[p])@(negedge clk);
  if(!wr&&result[p]!==value)$fatal(1,"S value differs p=%0d addr=%0d",p,addr);
  rsp_ready[p]=1;
  @(negedge clk);rsp_ready[p]=0;
  $display("LEAF kind=S_IO p=%0d write=%0d ticks=%0d",p,wr,($time-began)/10);
 endtask
 initial begin
  logic [127:0] value;
  repeat(3)@(negedge clk);reset=0;
  for(integer p=0;p<2;p=p+1)for(integer bank=0;bank<4;bank=bank+1)begin
   value={32'h01234567,32'h89abcdef,32'h76543210,32'hfedcba98};
   // Storage interleaves banks in address[1:0], not the high address bits.
   access(p,1,bank,value);access(p,0,bank,value);
   access(p,1,1020+bank,~value);access(p,0,1020+bank,~value);
  end
  $display("NATIVE_S_IO_PASS");$finish;
 end
 initial begin repeat(10000)@(posedge clk);$fatal(1,"SRAM watchdog");end
endmodule
