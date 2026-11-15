module tb_projection_read_queue;
 reg clk=0;always #5 clk=~clk;
 reg reset=1,p_rd_valid=0,l_rd_valid=0,rd_ready=0,rd_rsp_valid=0;
 reg p_rd_rsp_ready=0,l_rd_rsp_ready=0,rd_rsp_error=0;
 wire p_rd_ready,l_rd_ready,rd_valid,rd_rsp_ready,p_rd_rsp_valid,l_rd_rsp_valid,p_rd_rsp_error,l_rd_rsp_error;
 reg [63:0] p_rd_address=64'h100,l_rd_address=64'h200,p_rd_tag=7,l_rd_tag=7,rd_rsp_tag=0;
 wire [63:0] rd_address,rd_tag,p_rd_rsp_tag,l_rd_rsp_tag;
 reg [511:0] rd_rsp_data=0;wire [511:0] p_rd_rsp_data,l_rd_rsp_data;
 projection_read_queue dut(.*);
 integer pc=0,lc=0,issued=0,received=0,cycle=0;reg [63:0] tokens[0:3];
 reg held=0;reg[63:0] held_tag,held_address;
 always @(posedge clk)if(!reset)begin
  cycle<=cycle+1;
  if(p_rd_valid&&p_rd_ready)pc=pc+1;
  if(l_rd_valid&&l_rd_ready)lc=lc+1;
  if(held&&(rd_tag!=held_tag||rd_address!=held_address||!rd_valid))$fatal(1,"unstable stalled request");
  held=rd_valid&&!rd_ready;held_tag=rd_tag;held_address=rd_address;
  if(rd_valid&&rd_ready)begin tokens[issued]=rd_tag;issued=issued+1;end
  if(rd_rsp_valid&&rd_rsp_ready)begin
   if(received<2)begin
    if(!l_rd_rsp_valid||p_rd_rsp_valid||l_rd_rsp_tag!=7||l_rd_rsp_data!=rd_rsp_data||l_rd_rsp_error!=rd_rsp_error)$fatal(1,"load return route");
   end else if(!p_rd_rsp_valid||l_rd_rsp_valid||p_rd_rsp_tag!=7||p_rd_rsp_data!=rd_rsp_data||p_rd_rsp_error!=rd_rsp_error)$fatal(1,"projection return route");
   received=received+1;
  end
  if(received==4)begin
   if(pc!=2||lc!=2||issued!=4)$fatal(1,"lost request");
   $display("PASS four-slot read routing, colliding original tags, reverse returns, error forwarding and backpressure");$finish;
  end
  if(cycle>200)$fatal(1,"timeout");
 end
 always @(negedge clk)if(!reset)begin
  p_rd_valid=pc<2;l_rd_valid=lc<2;
  rd_ready=cycle%3!=0;p_rd_rsp_ready=cycle%4!=0;l_rd_rsp_ready=cycle%5!=0;
  rd_rsp_valid=issued==4;
  if(rd_rsp_valid)begin rd_rsp_tag=tokens[3-received];rd_rsp_data=512'(received+42);rd_rsp_error=received==1;end
 end
 initial begin repeat(3)@(negedge clk);reset=0;end
endmodule
