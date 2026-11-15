module tb_activation_pair #(parameter ERROR_READ=0,ERROR_ACK=0,CANCEL=0);
 reg clk=0;always #5 clk=~clk;
 reg cancel=0,ack_error=0;
 reg reset=1,launch_valid=0,done_ready=0,rd_ready=1,s_ready=1,rd_rsp_valid=0,s_rsp_valid=0;
 wire launch_ready,done_valid,done_error,rd_valid,rd_rsp_ready,s_valid,s_rsp_ready;
 wire [63:0] rd_address,rd_tag;reg [63:0] rd_rsp_tag;
 reg [511:0] rd_rsp_data;
 wire [9:0] s_address;wire [127:0] s_data;wire [31:0] s_tag;reg [31:0] s_rsp_tag;
 s128_ddr_range_load dut(.clk,.reset,.cancel,.launch_valid,.launch_ready,.launch_base(64'h1000),.launch_s_base(10'd32),
 .launch_bursts(8'd2),.launch_pair(1'b1),.launch_pair_beat(1'b1),.launch_pair_high(1'b1),
 .done_valid,.done_error,.done_ready,.rd_valid,.rd_ready,.rd_address,.rd_tag,
 .rd_rsp_error(ERROR_READ&&rd_rsp_tag==1),.rd_rsp_valid,.rd_rsp_ready,.rd_rsp_tag,.rd_rsp_data,.s_valid,.s_ready,.s_address,.s_data,.s_tag,
 .s_rsp_valid,.s_rsp_error(ack_error),.s_rsp_ready,.s_rsp_tag);
 bit [7:0] pending=0;integer issued=0,writes=0,acked=0,cycle=0,peak=0,peak_reads=0;
 reg [31:0] ack_tags[0:31];integer ack_due[0:31];integer chosen;
 always @(posedge clk)if(!reset)begin
  cycle<=cycle+1;
  if(rd_valid&&rd_ready)begin
   if(rd_tag>=8||rd_address!=64'h1000+rd_tag*64)$fatal(1,"read binding");
   pending[rd_tag]=1;issued=issued+1;if($countones(pending)>peak_reads)peak_reads=$countones(pending);
  end
  if(rd_rsp_valid&&rd_rsp_ready)pending[rd_rsp_tag]=0;
  if(s_valid&&s_ready)begin
   if(s_address!=32+writes||s_data!={4{32'(6+writes)}})$fatal(1,"write data/address");
   ack_tags[writes]=s_tag;ack_due[writes]=cycle+5;writes=writes+1;
  end
  if(s_rsp_valid&&s_rsp_ready)acked=acked+1;
  if(writes-acked>peak)peak=writes-acked;
  if(writes-acked>2)$fatal(1,"write credits");
  if(done_valid)begin
   if(ERROR_READ||ERROR_ACK)begin
    if(!done_error||pending!=0||acked!=writes)$fatal(1,"error drain");
   end else if(done_error||issued!=2||writes!=2||acked!=2||peak!=2)$fatal(1,"completion/drain");
   $display("CAPACITY peak_reads=%0d peak_writes=%0d",peak_reads,peak);
   if(!ERROR_READ&&!ERROR_ACK&&peak_reads!=2)$fatal(1,"read overlap regressed");
   $display("PASS reordered DDR returns, bounded writes, stalled acknowledgements");$finish;
  end
  if(cycle>2000)$fatal(1,"timeout");
 end
 always @(negedge clk)if(!reset)begin
  rd_ready=(cycle%5!=0);s_ready=(cycle%7!=0);
  s_rsp_valid=acked<writes&&cycle>=ack_due[acked];
  if(s_rsp_valid)s_rsp_tag=ack_tags[acked];
  ack_error=ERROR_ACK&&acked==0;
  rd_rsp_valid=0;chosen=-1;
  // Release higher tag first after allowing both read requests into flight.
  if(cycle%6==0)for(integer i=0;i<8;i++)if(pending[i])chosen=i;
  if(chosen>=0)begin
   rd_rsp_valid=1;rd_rsp_tag=chosen;
   for(integer lane=0;lane<4;lane++)rd_rsp_data[lane*128+:128]={4{32'(chosen*4+lane)}};
  end
 end
 initial begin
  repeat(3)@(negedge clk);reset=0;launch_valid=1;
  @(negedge clk);launch_valid=0;
 end
endmodule
