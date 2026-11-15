module tb_store_pipeline;
 parameter integer BURSTS=8, ERROR=0, HELD=0;
 reg clk=0;always #5 clk=~clk;
 reg reset=1,cmd_valid=0,done_ready=0;
 wire cmd_ready,done_valid,done_error,s_req_valid,s_rsp_ready,wr_valid,wr_done_ready;
 wire [9:0] s_req_address;wire [63:0] wr_address,wr_tag;wire [511:0] wr_data;
 reg s_req_ready=1,s_rsp_valid=0,s_rsp_error=0,wr_ready=1,wr_done_valid=0,wr_done_error=0;
 reg [127:0] s_rsp_data=0;reg [63:0] wr_done_tag=0;
 s128_store_pipeline dut(.clk,.reset,.cmd_valid,.cmd_ready,.cmd_bursts(9'(BURSTS)),.cmd_word(10'd4),.cmd_address(64'd4096),.cmd_tag(64'd77),
 .done_valid,.done_ready,.done_error,.s_req_valid,.s_req_ready,.s_req_address,.s_rsp_valid,.s_rsp_ready,.s_rsp_data,.s_rsp_error,
 .wr_valid,.wr_ready,.wr_address,.wr_tag,.wr_data,.wr_done_valid,.wr_done_ready,.wr_done_tag,.wr_done_error);
 reg held_read=0,held_write=0;reg [9:0] held_address;reg [63:0] held_ddr;reg [511:0] held_data;
 always @(posedge clk)if(!reset)begin
  if(held_read&&(!s_req_valid||s_req_address!=held_address))$fatal(1,"withdrawn SRAM offer");
  if(held_write&&(!wr_valid||wr_address!=held_ddr||wr_data!=held_data))$fatal(1,"withdrawn DDR offer");
  held_read<=s_req_valid&&!s_req_ready;held_address<=s_req_address;
  held_write<=wr_valid&&!wr_ready;held_ddr<=wr_address;held_data<=wr_data;
 end
 integer bad_seen=0;
 integer cycle=0,requests=0,responses=0,writes=0,acks=0,peak=0,due[0:2047],addr[0:2047],write_due=0,first_ack_reads=0;
 always @(posedge clk) if(!reset)begin
  cycle<=cycle+1;
  if(s_req_valid&&s_req_ready)begin due[requests]<=cycle+8;addr[requests]<=s_req_address;requests<=requests+1;end
  if(s_rsp_valid&&s_rsp_ready)responses<=responses+1;
  if(requests-responses>peak)peak<=requests-responses;
  if(requests-responses>2)$fatal(1,"read credit overflow");
  if(wr_valid&&wr_ready)begin
   if(writes!=acks)$fatal(1,"write credit overflow");
   if(wr_address!=4096+writes*64||wr_tag!=77+writes)$fatal(1,"address/tag");
   for(integer j=0;j<4;j=j+1)if(wr_data[j*128+:128]!={4{32'(4+writes*4+j)}})$fatal(1,"payload");
   writes<=writes+1;write_due<=cycle+60;
  end
  if(wr_done_valid&&wr_done_ready&&wr_done_tag!=wr_tag)bad_seen<=1;
  if(wr_done_valid&&wr_done_ready&&wr_done_tag==wr_tag)begin
   acks<=acks+1;if(acks==0)first_ack_reads<=requests;
  end
  if(cycle>3000)$fatal(1,"timeout");
 end
 always @(negedge clk)begin
  s_rsp_valid=!reset&&responses<requests&&cycle>=due[responses];
  s_rsp_data={4{32'(addr[responses])}};
  s_rsp_error=ERROR==1&&responses==(HELD==2?6:2);
  wr_done_valid=!reset&&writes>acks&&cycle>=write_due;
  wr_done_tag=77+acks+(ERROR==3&&!bad_seen?1:0);wr_done_error=ERROR==2;
  s_req_ready=HELD==1&&requests==3&&cycle<100?0:cycle%5!=3;
  wr_ready=HELD==2&&writes==0&&cycle<150?0:cycle%7!=4;
 end
 initial begin
  repeat(3)@(negedge clk);reset=0;cmd_valid=1;
  @(negedge clk);cmd_valid=0;
  wait(done_valid);@(negedge clk);
  if(requests!=responses||writes!=acks)$fatal(1,"early completion");
  if(ERROR==0)begin
   if(done_error||acks!=BURSTS||responses!=BURSTS*4||peak!=2)$fatal(1,"successful extent/peak");
   if(BURSTS>1&&first_ack_reads<8)$fatal(1,"serialized next burst");
  end else if(!done_error)$fatal(1,"fault lost");
  repeat(4)begin @(negedge clk);if(!done_valid)$fatal(1,"terminal not held");end
  done_ready=1;@(negedge clk);done_ready=0;
  if(!cmd_ready)$fatal(1,"not reusable");
  $display("PASS store BURSTS=%0d ERROR=%0d reads=%0d writes=%0d peak=%0d prefetch=%0d",BURSTS,ERROR,responses,acks,peak,first_ack_reads);$finish;
 end
endmodule
