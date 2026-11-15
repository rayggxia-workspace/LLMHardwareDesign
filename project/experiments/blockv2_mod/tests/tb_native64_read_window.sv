module tb_native64_read_window;
 reg clk=0;always #5 clk=~clk;
 reg reset=1,req_valid=0,rsp_ready=0,dma_ready=1,dma_rsp_valid=0,fence_ready=0,fence_done_valid=0;
 reg [63:0] req_address=0,req_tag=0;
 wire req_ready,rsp_valid,rsp_error,dma_valid,dma_rsp_ready,fence_valid,fence_done_ready,idle,protocol_fault;
 wire [63:0] rsp_tag,dma_address;wire [511:0] rsp_data;wire [31:0] dma_tag,fence_cookie;wire [8:0] fence_epoch;
 reg [31:0] dma_rsp_tag=0,fence_done_cookie=0;reg[8:0] fence_done_epoch=0;reg[511:0] dma_rsp_data=0;
 native64_dma_read_window_client #(.OUTSTANDING(4),.SERIAL_LIMIT(3)) dut(.*);
 task offer(input integer n);
  @(negedge clk);req_valid=1;req_address=64'h1000+64*n;req_tag=100+n;
  do @(posedge clk);while(!req_ready);
  if(dma_tag!={(31'(n%4)),1'b0})$fatal(1,"physical serial");
  @(negedge clk);req_valid=0;
 endtask
 task respond(input integer n,input bit error);
  @(negedge clk);dma_rsp_valid=1;dma_rsp_tag=(n%4)*2+error;dma_rsp_data=512'(n+1000);rsp_ready=0;
  repeat(3)begin @(posedge clk);if(!rsp_valid||dma_rsp_ready||rsp_tag!=100+n||rsp_error!=error)$fatal(1,"return hold");end
  @(negedge clk);rsp_ready=1;
  @(posedge clk);if(!rsp_valid||!dma_rsp_ready||rsp_data!=512'(n+1000))$fatal(1,"return");
  @(negedge clk);dma_rsp_valid=0;rsp_ready=0;
 endtask
 integer peak=0;
 always @(negedge clk)if(!reset&&$countones(dut.live)>peak)peak=$countones(dut.live);
 initial begin
  repeat(3)@(negedge clk);reset=0;
  for(integer i=0;i<4;i++)offer(i);
  @(negedge clk);req_valid=1;req_tag=104;
  repeat(3)begin @(posedge clk);if(req_ready||idle||fence_valid)$fatal(1,"must drain before fence");end
  @(negedge clk);req_valid=0;
  respond(3,0);respond(1,1);respond(2,0);respond(0,0);
  @(negedge clk);req_valid=1;req_tag=104;req_address=64'h1100;
  wait(fence_valid);@(negedge clk);fence_ready=1;
  @(negedge clk);fence_ready=0;fence_done_valid=1;fence_done_cookie=fence_cookie+1;fence_done_epoch=fence_epoch;
  @(negedge clk);if(req_ready)$fatal(1,"wrong fence accepted");fence_done_valid=0;
  @(negedge clk);fence_done_valid=1;fence_done_cookie=fence_cookie;
  @(negedge clk);fence_done_valid=0;
  do @(posedge clk);while(!req_ready);
  if(dma_tag!=0)$fatal(1,"serial did not reset after real fence");
  @(negedge clk);req_valid=0;
  respond(4,0);
  @(posedge clk);if(!idle||!protocol_fault)$fatal(1,"final drain/fault");
  if(peak!=4)$fatal(1,"read window capacity");
  $display("CAPACITY peak_reads=%0d",peak);
  $display("PASS 4 outstanding, reordered/error returns, backpressure, drain and matched fence namespace reuse");$finish;
 end
 initial begin #20000;$fatal(1,"timeout");end
endmodule
