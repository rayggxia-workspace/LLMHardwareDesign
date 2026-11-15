module tb_activation_scope #(parameter BYTES=8192);
 localparam ERROR_READ=0,ERROR_ACK=0,CANCEL=0,BURSTS=BYTES/64;
 reg clk=0;always #5 clk=~clk;
 reg cancel=0;
 reg reset=1,launch_valid=0,done_ready=0,rd_ready=1,s_ready=1,rd_rsp_valid=0,s_rsp_valid=0;
 wire launch_ready,done_valid,done_error,rd_valid,rd_rsp_ready,s_valid,s_rsp_ready;
 wire [63:0] rd_address,rd_tag;reg [63:0] rd_rsp_tag;
 reg [511:0] rd_rsp_data;
 wire [9:0] s_address;wire [127:0] s_data;wire [31:0] s_tag;reg [31:0] s_rsp_tag;
 reg [1023:0] descriptor=0;
 wire [15:0] status;wire [31:0] read_bytes,write_bytes;
 assign done_error=status!=0;
 ddr_s128_load_scope #(.TOPOLOGY(1),.PAYLOAD_BYTES(BYTES),.LOCAL_DMA_SEQUENCE(1)) dut(
 .clk,.reset,.service_valid(launch_valid),.service_ready(launch_ready),
 .service_owner(128'd0),.service_ticket(32'd7),.service_descriptor(descriptor),
 .service_cancel_valid(cancel),.service_cancel_ready(),
 .service_done_valid(done_valid),.service_done_ready(done_ready),.service_done_owner(),.service_done_ticket(),
 .service_done_status(status),.service_done_read_bytes(read_bytes),.service_done_write_bytes(write_bytes),
 .rd_valid,.rd_ready,.rd_address,.rd_tag,.rd_rsp_valid,.rd_rsp_ready,.rd_rsp_tag,.rd_rsp_data,.rd_rsp_error(1'b0),
 .s_valid,.s_ready,.s_address,.s_data,.s_tag,.s_rsp_valid,.s_rsp_ready,.s_rsp_tag,.s_rsp_error(1'b0));
 bit [127:0] pending=0;integer issued=0,writes=0,acked=0,cycle=0,peak=0,peak_reads=0;
 reg [31:0] ack_tags[0:511];integer ack_due[0:511];integer chosen;integer cancelled_issued=0;
 always @(posedge clk)if(!reset)begin
  cycle<=cycle+1;
  if(cancel&&rd_valid)$fatal(1,"new read after cancel");
  if(rd_valid&&rd_ready)begin
   if(rd_tag[6:0]>=BURSTS||rd_tag[63:7]!=1||rd_address!=64'h1000+rd_tag[6:0]*64)$fatal(1,"read binding");
   pending[rd_tag[6:0]]=1;issued=issued+1;if($countones(pending)>peak_reads)peak_reads=$countones(pending);
  end
  if(rd_rsp_valid&&rd_rsp_ready)pending[rd_rsp_tag[6:0]]=0;
  if(s_valid&&s_ready)begin
   if(s_address!=32+writes||s_data!={4{32'(writes/4*4+writes%4)}})$fatal(1,"write data/address");
   ack_tags[writes]=s_tag;ack_due[writes]=cycle+5;writes=writes+1;
  end
  if(s_rsp_valid&&s_rsp_ready)acked=acked+1;
  if(writes-acked>peak)peak=writes-acked;
  if(writes-acked>2)$fatal(1,"write credits");
  if(done_valid)begin
   if(CANCEL)begin
    if(done_error||issued!=cancelled_issued||pending!=0||acked!=writes)$fatal(1,"cancel drain");
   end else if(ERROR_READ||ERROR_ACK)begin
    if(!done_error||pending!=0||acked!=writes)$fatal(1,"error drain");
   end else if(done_error||issued!=BURSTS||writes!=BYTES/16||acked!=BYTES/16||read_bytes!=BYTES||write_bytes!=BYTES||peak!=2)$fatal(1,"completion/drain");
   $display("CAPACITY peak_reads=%0d peak_writes=%0d",peak_reads,peak);
   if(!CANCEL&&!ERROR_READ&&!ERROR_ACK&&peak_reads!=2)$fatal(1,"read overlap regressed");
   $display("PASS reordered DDR returns, bounded writes, stalled acknowledgements");$finish;
  end
  if(cycle>10000)$fatal(1,"timeout");
 end
 always @(negedge clk)if(!reset)begin
  if(!cancel&&((CANCEL==1&&issued==2)||(CANCEL==2&&writes==2)))begin cancel=1;cancelled_issued=issued;end
  rd_ready=(cycle%5!=0);s_ready=(cycle%7!=0);
  s_rsp_valid=acked<writes&&cycle>=ack_due[acked];
  if(s_rsp_valid)s_rsp_tag=ack_tags[acked]^((ERROR_ACK&&acked==0)?1:0);
  rd_rsp_valid=0;chosen=-1;
  // Release higher tag first after allowing both read requests into flight.
  if(cycle%6==0)for(integer i=0;i<BURSTS;i++)if(pending[i])chosen=i;
  if(chosen>=0)begin
   rd_rsp_valid=1;rd_rsp_tag=128+chosen;
   for(integer lane=0;lane<4;lane++)rd_rsp_data[lane*128+:128]={4{32'(chosen*4+lane)}};
  end
 end
 initial begin
  descriptor[31:0]=BYTES==512?32'h314c5244:32'h384c5244;
  descriptor[47:32]=128;descriptor[63:48]=1;descriptor[95:64]=32'h02500002;
  descriptor[127:96]=1;descriptor[143:128]=32;descriptor[255:192]=64'h1000;
  repeat(3)@(negedge clk);reset=0;launch_valid=1;
  @(negedge clk);launch_valid=0;
 end
endmodule
