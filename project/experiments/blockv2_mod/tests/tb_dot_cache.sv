module tb_dot_cache #(parameter BAD_TAG=0);
 reg clk=0;always #5 clk=~clk;
 reg reset=1,service_valid=0;wire service_ready,service_done_valid;wire [127:0] service_done_owner;
 wire [31:0] service_done_ticket,service_done_read_bytes,service_done_write_bytes;wire [15:0] service_done_status;
 reg [1023:0] service_descriptor=0;
 wire rd_valid,rd_rsp_ready;reg rd_ready=1,rd_rsp_valid=0;wire [63:0] rd_address,rd_tag;reg [63:0] rd_rsp_tag;
 reg [511:0] rd_rsp_data;wire s_req_valid,s_req_write,s_rsp_ready;reg s_req_ready=1,s_rsp_valid=0;
 wire [9:0] s_req_address;wire [127:0] s_req_data;
 wire resource_e_in_valid,resource_e_in_ready,resource_e_out_valid,resource_e_out_ready,resource_e_out_error;
 wire [63:0] resource_e_in_data,resource_e_out_data;wire [3:0] resource_e_in_op,resource_e_in_mask,resource_e_out_clipped;
 wire [7:0] resource_e_in_shift;wire [2:0] resource_e_in_minus;
 e32_dot_service_controller #(.TOPOLOGY(1)) dut(.clk,.reset,.service_valid,.service_ready,
 .service_owner(128'd1),.service_ticket(32'd2),.service_descriptor,.service_cancel_valid(1'b0),.service_cancel_ready(),
 .service_done_valid,.service_done_ready(1'b1),.service_done_owner,.service_done_ticket,.service_done_status,
 .service_done_read_bytes,.service_done_write_bytes,.rd_valid,.rd_ready,.rd_address,.rd_tag,.rd_rsp_valid,
 .rd_rsp_ready,.rd_rsp_tag,.rd_rsp_data,.rd_rsp_error(1'b0),.s_req_valid,.s_req_write,.s_req_ready,.s_req_address,.s_req_data,
 .s_rsp_valid,.s_rsp_ready,.s_rsp_data(128'd0),.s_rsp_error(1'b0),
 .resource_e_in_valid,.resource_e_in_ready,.resource_e_in_data,.resource_e_in_op,.resource_e_in_mask,
 .resource_e_in_shift,.resource_e_in_minus,.resource_e_out_valid,.resource_e_out_ready,.resource_e_out_data,
 .resource_e_out_clipped,.resource_e_out_error);
 e_s32_mac_ap64 core(.clk,.reset,.in_valid(resource_e_in_valid),.in_ready(resource_e_in_ready),.in_data(resource_e_in_data),
 .in_op(resource_e_in_op),.in_mask(resource_e_in_mask),.in_shift(resource_e_in_shift),.in_minus(resource_e_in_minus),
 .out_valid(resource_e_out_valid),.out_ready(resource_e_out_ready),.out_data(resource_e_out_data),
 .out_clipped(resource_e_out_clipped),.out_error(resource_e_out_error));
 integer cycle=0,due=0,ack_due=0,reads=0,writes=0,round=0;bit pending=0,ack_pending=0,restart=0;
 reg [63:0] address,tag;
 always @(posedge clk)if(!reset)begin
  cycle=cycle+1;
  if(service_valid&&service_ready)service_valid<=0;
  if(rd_valid&&rd_ready)begin
   if(pending)$fatal(1,"multiple outstanding");
   pending=1;address=rd_address;tag=rd_tag;due=cycle+5;reads=reads+1;
  end
  if(rd_rsp_valid&&rd_rsp_ready)pending=0;
  if(s_req_valid&&s_req_ready)begin
   if(s_req_data!={96'd0,32'(round==0?64:384)})$fatal(1,"wrong E output %h",s_req_data);
   writes=writes+1;ack_pending=1;ack_due=cycle+4;
  end
  if(s_rsp_valid&&s_rsp_ready)ack_pending=0;
  if(service_done_valid)begin
   if(BAD_TAG)begin
    if(service_done_status==0||writes!=0||pending)$fatal(1,"bad tag accepted");
    $display("PASS dot bad tag abort");$finish;
   end
   if(!BAD_TAG && (service_done_status!=0||service_done_read_bytes!=256||reads!=4*(round+1)||writes!=round+1))$fatal(1,"cache traffic/result status=%h reads=%0d bytes=%0d writes=%0d",service_done_status,reads,service_done_read_bytes,writes);
   if(round==1)begin $display("PASS real E dot dual cache: 4 reads per K32, reset between commands");$finish;end
   round=1;restart=1;
  end
  if(cycle>5000)$fatal(1,"timeout");
 end
 always @(negedge clk)if(!reset)begin
  rd_ready=cycle%7!=0;s_req_ready=cycle%5!=0;
  rd_rsp_valid=pending&&cycle>=due;rd_rsp_tag=tag^(BAD_TAG?64'd1:64'd0);
  if(address<64'h2000) rd_rsp_data={16{32'(round==0?1:3)}};
  else rd_rsp_data={16{32'(round==0?2:4)}};
  s_rsp_valid=ack_pending&&cycle>=ack_due;
  if(restart)begin service_valid=1;restart=0;end
 end
 initial begin
  service_descriptor[31:0]=32'h31444d45;service_descriptor[32+:16]=128;service_descriptor[48+:16]=1;
  service_descriptor[64+:32]=32'h02504503;service_descriptor[96+:32]=1;
  service_descriptor[128+:16]=32;service_descriptor[144+:8]=1;
  service_descriptor[192+:64]=64'h1000;service_descriptor[256+:64]=64'h2000;
  service_descriptor[320+:32]=4;service_descriptor[352+:32]=4;
  repeat(3)@(negedge clk);reset=0;service_valid=1;
 end
endmodule
