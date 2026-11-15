module tb_activation_pipeline #(parameter ERROR_READ=0,ERROR_ACK=0,CANCEL=0,HOLD_READ=0,HOLD_WRITE=0,BAD_ACK=0);
 reg clk=0;always #5 clk=~clk;
 reg cancel=0,ack_error=0;bit bad_seen=0,held_at_error=0;
 reg prev_r=0,prev_s=0;reg [63:0] prev_addr,prev_tag;reg [9:0] prev_sa;reg [127:0] prev_sd;
 reg reset=1,launch_valid=0,done_ready=0,rd_ready=1,s_ready=1,rd_rsp_valid=0,s_rsp_valid=0;
 wire launch_ready,done_valid,done_error,rd_valid,rd_rsp_ready,s_valid,s_rsp_ready;
 wire [63:0] rd_address,rd_tag;reg [63:0] rd_rsp_tag;
 reg [511:0] rd_rsp_data;
 wire [9:0] s_address;wire [127:0] s_data;wire [31:0] s_tag;reg [31:0] s_rsp_tag;
 s128_ddr_range_load dut(.clk,.reset,.cancel,.launch_valid,.launch_ready,.launch_base(64'h1000),.launch_s_base(10'd32),
 .launch_bursts(8'd8),.launch_pair(1'b0),.launch_pair_beat(1'b0),.launch_pair_high(1'b0),
 .done_valid,.done_error,.done_ready,.rd_valid,.rd_ready,.rd_address,.rd_tag,
 .rd_rsp_error(ERROR_READ&&rd_rsp_tag==(HOLD_READ?0:1)),.rd_rsp_valid,.rd_rsp_ready,.rd_rsp_tag,.rd_rsp_data,.s_valid,.s_ready,.s_address,.s_data,.s_tag,
 .s_rsp_valid,.s_rsp_error(ack_error),.s_rsp_ready,.s_rsp_tag);
 bit [7:0] pending=0;integer issued=0,writes=0,acked=0,cycle=0,peak=0,peak_reads=0;
 reg [31:0] ack_tags[0:31];integer ack_due[0:31];integer chosen;integer cancelled_issued=0;
 always @(posedge clk)if(!reset)begin
  cycle<=cycle+1;
  if(prev_r&&(!rd_valid||rd_address!=prev_addr||rd_tag!=prev_tag))$fatal(1,"held DDR offer changed");
  if(prev_s&&(!s_valid||s_address!=prev_sa||s_data!=prev_sd))$fatal(1,"held SRAM offer changed");
  prev_r=rd_valid&&!rd_ready;prev_addr=rd_address;prev_tag=rd_tag;
  prev_s=s_valid&&!s_ready;prev_sa=s_address;prev_sd=s_data;
  if(ERROR_READ&&rd_rsp_valid&&rd_rsp_ready&&rd_rsp_tag==(HOLD_READ?0:1))
   held_at_error=(HOLD_READ&&dut.read_held)||(HOLD_WRITE&&dut.write_held);

  if(cancel&&rd_valid&&!dut.read_held)$fatal(1,"new read after cancel");
  if(rd_valid&&rd_ready)begin
   if(rd_tag>=8||rd_address!=64'h1000+rd_tag*64)$fatal(1,"read binding");
   pending[rd_tag]=1;issued=issued+1;if($countones(pending)>peak_reads)peak_reads=$countones(pending);
  end
  if(rd_rsp_valid&&rd_rsp_ready)pending[rd_rsp_tag]=0;
  if(s_valid&&s_ready)begin
   if(s_address!=32+writes||s_data!={4{32'(writes/4*4+writes%4)}})$fatal(1,"write data/address");
   ack_tags[writes]=s_tag;ack_due[writes]=cycle+5;writes=writes+1;
  end
  if(s_rsp_valid&&s_rsp_ready)begin
   if(s_rsp_tag==ack_tags[acked])acked=acked+1;
   else begin bad_seen=1;if(done_valid)$fatal(1,"bad ACK retired request");end
  end
  if(writes-acked>peak)peak=writes-acked;
  if(writes-acked>2)$fatal(1,"write credits");
  if(done_valid)begin
   if(CANCEL)begin
    if(done_error||issued!=cancelled_issued||pending!=0||acked!=writes)$fatal(1,"cancel drain");
   end else if(ERROR_READ||ERROR_ACK||BAD_ACK)begin
    if(!done_error||pending!=0||acked!=writes)$fatal(1,"error drain");
   end else if(done_error||issued!=8||writes!=32||acked!=32||peak!=2)$fatal(1,"completion/drain");
   if(ERROR_READ&&(HOLD_READ||HOLD_WRITE)&&!held_at_error)$fatal(1,"missing held error coverage");
   if(BAD_ACK&&!bad_seen)$fatal(1,"missing invalid ACK coverage");
   $display("CAPACITY peak_reads=%0d peak_writes=%0d",peak_reads,peak);
   if(!CANCEL&&!ERROR_READ&&!ERROR_ACK&&!BAD_ACK&&peak_reads!=2)$fatal(1,"read overlap regressed");
   $display("PASS reordered DDR returns, bounded writes, stalled acknowledgements");$finish;
  end
  if(cycle>2000)$fatal(1,"timeout");
 end
 always @(negedge clk)if(!reset)begin
  if(!cancel&&((CANCEL==1&&issued==2)||(CANCEL==2&&writes==2)||(CANCEL==3&&dut.read_held)||(CANCEL==4&&dut.write_held)))begin cancel=1;cancelled_issued=issued+(dut.read_held?1:0);end
  rd_ready=(HOLD_READ&&issued==1&&cycle<16)?0:(cycle%5!=0);s_ready=(HOLD_WRITE&&writes==0&&cycle<20)?0:(cycle%7!=0);
  s_rsp_valid=acked<writes&&cycle>=ack_due[acked];
  if(s_rsp_valid)s_rsp_tag=ack_tags[acked]^((BAD_ACK&&!bad_seen)?1:0);
  ack_error=ERROR_ACK&&acked==0;
  rd_rsp_valid=0;chosen=-1;
  // Release higher tag first after allowing both read requests into flight.
  if(cycle%6==0)for(integer i=0;i<8;i++)if(pending[i]&&(!HOLD_WRITE||chosen<0))chosen=i;
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
