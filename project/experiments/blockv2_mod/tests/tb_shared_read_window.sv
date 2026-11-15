module tb_shared_read_window;
reg clk;
reg reset;
reg [11:0] c_req_valid;
wire [11:0] c_req_ready;
reg [767:0] c_req_address;
reg [383:0] c_req_tag;
reg [11:0] c_req_channel;
reg [59:0] c_req_record_beats;
wire [11:0] c_rsp_valid;
reg [11:0] c_rsp_ready;
wire [383:0] c_rsp_tag;
wire [6143:0] c_rsp_data;
reg [11:0] c_close_valid;
wire [11:0] c_close_ready;
reg [383:0] c_close_tag_base;
reg [11:0] c_cancel_valid;
wire [11:0] c_cancel_ready;
reg [383:0] c_cancel_tag;
wire [11:0] c_cancel_ack_valid;
reg [11:0] c_cancel_ack_ready;
wire [383:0] c_cancel_ack_tag;
wire [11:0] c_cancel_ack_rejected;
reg [11:0] c_fence_valid;
wire [11:0] c_fence_ready;
reg [383:0] c_fence_cookie;
reg [107:0] c_fence_epoch;
wire [11:0] c_fence_done_valid;
reg [11:0] c_fence_done_ready;
wire [383:0] c_fence_done_cookie;
wire [107:0] c_fence_done_epoch;
wire [3:0] d_req_valid;
reg [3:0] d_req_ready;
wire [255:0] d_req_address;
wire [255:0] d_req_tag;
reg [3:0] d_rsp_valid;
wire [3:0] d_rsp_ready;
reg [255:0] d_rsp_tag;
reg [2047:0] d_rsp_data;
wire d_fence_valid;
reg d_fence_ready;
wire [31:0] d_fence_generation;
reg d_fence_done_valid;
wire d_fence_done_ready;
reg [31:0] d_fence_done_generation;
wire fault_valid;
reg fault_ready;
wire [7:0] fault_kind;
wire [4:0] fault_client;
wire [31:0] fault_local_tag;
wire [63:0] fault_global_tag;
wire [11:0] debug_beats;
wire [11:0] debug_descriptors;
wire [31:0] debug_generation;
reg [8:0] service_req_valid;
wire [8:0] service_req_ready;
reg [575:0] service_req_address;
reg [575:0] service_req_tag;
wire [8:0] service_rsp_valid;
reg [8:0] service_rsp_ready;
wire [575:0] service_rsp_tag;
wire [4607:0] service_rsp_data;
wire [8:0] service_rsp_error;
wire [8:0] service_idle;
wire [8:0] service_protocol_fault;
reg [8:0] write_req_valid;
wire [8:0] write_req_ready;
reg [575:0] write_req_address,write_req_tag;
reg [4607:0] write_req_data;
wire [8:0] write_done_valid;
reg [8:0] write_done_ready;
wire [575:0] write_done_tag;
wire [8:0] write_done_error,write_idle,write_protocol_fault;
wire transport_idle;
wire [3:0] d_req_write;
wire [2047:0] d_req_data;
 native_shared_memory_plane dut(.*);
 initial begin clk=0;reset=0;c_req_valid=0;c_req_address=0;c_req_tag=0;c_req_channel=0;c_req_record_beats=0;c_rsp_ready=0;c_close_valid=0;c_close_tag_base=0;c_cancel_valid=0;c_cancel_tag=0;c_cancel_ack_ready=0;c_fence_valid=0;c_fence_cookie=0;c_fence_epoch=0;c_fence_done_ready=0;d_req_ready=0;d_rsp_valid=0;d_rsp_tag=0;d_rsp_data=0;d_fence_ready=0;d_fence_done_valid=0;d_fence_done_generation=0;fault_ready=0;service_req_valid=0;service_req_address=0;service_req_tag=0;service_rsp_ready=0;write_req_valid=0;write_req_address=0;write_req_tag=0;write_req_data=0;write_done_ready=0; reset=1;repeat(4)@(negedge clk);reset=0;end
 always #5 clk=~clk;

 integer offered[0:8],returned[0:8],owner_peak[0:8];
 integer issued=0,responses=0,cycle=0,peak0=0,peak1=0,selected=-1;
 integer total=0,waccepted=0,wfinished=0;
 reg [63:0] tokens[0:63],addresses[0:63];reg pending[0:63];
 bit start_returns=0,response_taken=0,pending_fence=0;
 reg [31:0] fence_reply_generation=0;
 reg [3:0] seen[0:8];
 initial begin
  for(integer i=0;i<9;i++)begin offered[i]=0;returned[i]=0;owner_peak[i]=0;seen[i]=0;end
  for(integer i=0;i<64;i++)pending[i]=0;
 end
 always @(posedge clk)if(!reset)begin
  if(d_fence_valid&&d_fence_ready)begin pending_fence=1;fence_reply_generation=d_fence_generation;end
  if(d_fence_done_valid&&d_fence_done_ready)pending_fence=0;
  cycle=cycle+1;response_taken=d_rsp_valid[0]&&d_rsp_ready[0];
  if(fault_valid||service_protocol_fault||write_protocol_fault)$fatal(1,"protocol fault");
  if(debug_beats[5:0]>32||debug_beats[11:6]>32)$fatal(1,"DDR channel credits exceeded");
  if(debug_beats[5:0]>peak0)peak0=debug_beats[5:0];
  if(debug_beats[11:6]>peak1)peak1=debug_beats[11:6];
  for(integer k=0;k<9;k++)begin
   if(service_req_valid[k]&&service_req_ready[k])offered[k]=offered[k]+1;
   if(offered[k]-returned[k]>owner_peak[k])owner_peak[k]=offered[k]-returned[k];
   if(service_rsp_valid[k]&&service_rsp_ready[k])begin
    integer seq;
    seq=service_rsp_tag[k*64+:64]-256;
    if(seq<0||seq>3||service_rsp_error[k]||service_rsp_data[k*512+:512]!={8{64'(65536+k*4096+seq*64)}})
     $fatal(1,"owner/tag/data routing");
    if(seen[k][seq])$fatal(1,"duplicate response");seen[k][seq]=1;
    returned[k]=returned[k]+1;total=total+1;
   end
   if(offered[k]-returned[k]>4)$fatal(1,"read owner credits");
  end
  if(write_req_valid[0]&&write_req_ready[0])waccepted=waccepted+1;
  if(write_done_valid[0]&&write_done_ready[0])begin
   if(write_done_tag[0+:64]!=888||write_done_error[0])$fatal(1,"write commit");
   wfinished=wfinished+1;
  end
  for(integer lane=0;lane<4;lane++)if(d_req_valid[lane]&&d_req_ready[lane])begin
   if(d_req_write[lane]&&d_req_data[lane*512+:512]!=512'd99)$fatal(1,"write payload");
   tokens[issued]=d_req_tag[lane*64+:64];addresses[issued]=d_req_address[lane*64+:64];
   pending[issued]=1;issued=issued+1;
  end
  if(d_rsp_valid[0]&&d_rsp_ready[0])begin pending[selected]=0;responses=responses+1;end
  if(issued>=32)start_returns=1;
  if(total==36&&wfinished==1&&transport_idle)begin
   if(issued!=37||responses!=37||peak0!=32||!(&service_idle)||!(&write_idle))$fatal(1,"final drain/budget");
   if(owner_peak[0]!=4)$fatal(1,"source overlap not exercised");
   $display("CAPACITY read_slots_per_owner=4 write_slots_per_owner=1 peak_channel0=32");
   $display("PASS actual plane+DMA 9 owners, 36 concurrent reads, write commit, reordered returns and drain");$finish;
  end
  if(cycle>5000)$fatal(1,"timeout issued=%0d responses=%0d total=%0d",issued,responses,total);
 end
 always @(negedge clk)if(!reset)begin
  d_fence_ready=1;d_fence_done_valid=pending_fence;d_fence_done_generation=fence_reply_generation;
  d_req_ready=cycle%7==0?0:15;fault_ready=1;
  for(integer k=0;k<9;k++)begin
   service_req_valid[k]=offered[k]<4;
   service_req_address[k*64+:64]=65536+k*4096+offered[k]*64;
   service_req_tag[k*64+:64]=256+offered[k];
   service_rsp_ready[k]=cycle%9!=k;
  end
  write_req_valid[0]=waccepted==0;write_req_address[0+:64]=64'h40000;
  write_req_tag[0+:64]=888;write_req_data[0+:512]=99;write_done_ready=9'h1ff;
  if(!d_rsp_valid[0]||response_taken)begin
   selected=-1;
   if(start_returns)for(integer i=0;i<64;i++)if(pending[i])selected=i;
   d_rsp_valid=0;
   if(selected>=0)begin d_rsp_valid[0]=1;d_rsp_tag[0+:64]=tokens[selected];d_rsp_data[0+:512]={8{addresses[selected]}};end
  end
 end
endmodule
