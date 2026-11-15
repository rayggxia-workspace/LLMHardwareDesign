// Two gathered bursts; ordered SRAM responses, two reads, one DDR write in flight.
module s128_store_pipeline(
 input wire clk,reset,cmd_valid, output wire cmd_ready,
 input wire [8:0] cmd_bursts,input wire [9:0] cmd_word,
 input wire [63:0] cmd_address,cmd_tag,
 output wire done_valid,input wire done_ready,output reg done_error,
 output wire s_req_valid,input wire s_req_ready,output wire [9:0] s_req_address,
 input wire s_rsp_valid,output wire s_rsp_ready,input wire [127:0] s_rsp_data,input wire s_rsp_error,
 output wire wr_valid,input wire wr_ready,output wire [63:0] wr_address,wr_tag,
 output wire [511:0] wr_data,input wire wr_done_valid,output wire wr_done_ready,
 input wire [63:0] wr_done_tag,input wire wr_done_error);
 reg active,report,writing,read_offer,write_offer;
 reg [8:0] count,retired;
 reg [10:0] issued,received;
 reg [9:0] first_word;
 reg [63:0] address,tag;
 reg [511:0] payload[0:1];
 wire read_fire=s_req_valid&&s_req_ready;
 wire response_fire=s_rsp_valid&&s_rsp_ready;
 wire write_fire=wr_valid&&wr_ready;
 wire ack=wr_done_valid&&wr_done_ready;
 wire bad_response=response_fire&&s_rsp_error;
 wire bad_ack=ack&&(wr_done_error||wr_done_tag!=wr_tag);
 assign cmd_ready=!reset&&!active&&!report;
 assign done_valid=!reset&&report;
 assign s_req_valid=!reset&&active&&(!done_error||read_offer)&&issued<({2'd0,count}<<2)&&
   issued<(({2'd0,retired}+11'd2)<<2)&&issued-received<2;
 assign s_req_address=first_word+issued[9:0];
 assign s_rsp_ready=!reset&&active&&received<issued;
 assign wr_valid=!reset&&active&&(!done_error||write_offer)&&!writing&&
   retired<count&&received>=(({2'd0,retired}+11'd1)<<2);
 assign wr_address=address+({55'd0,retired}<<6);
 assign wr_tag=tag+{55'd0,retired};
 assign wr_data=payload[retired[0]];
 assign wr_done_ready=!reset&&active&&writing;
 always @(posedge clk) begin
  if(reset)begin active<=0;report<=0;writing<=0;read_offer<=0;write_offer<=0;done_error<=0;count<=0;retired<=0;issued<=0;received<=0;first_word<=0;address<=0;tag<=0;payload[0]<=0;payload[1]<=0;end
  else begin
   if(cmd_valid&&cmd_ready)begin
    count<=cmd_bursts;retired<=0;issued<=0;received<=0;first_word<=cmd_word;address<=cmd_address;tag<=cmd_tag;writing<=0;
    done_error<=cmd_bursts==0||cmd_bursts>256||({1'b0,cmd_word}+({2'd0,cmd_bursts}<<2)>1024)||cmd_address[5:0]!=0||cmd_address>64'd0-({55'd0,cmd_bursts}<<6)||cmd_tag>64'd0-{55'd0,cmd_bursts};
    active<=1;
   end
   read_offer<=s_req_valid&&!s_req_ready;
   write_offer<=wr_valid&&!wr_ready;
   if(read_fire)issued<=issued+1'b1;
   if(response_fire)begin received<=received+1'b1;payload[received[2]][received[1:0]*128+:128]<=s_rsp_data;end
   if(write_fire)writing<=1;
   if(ack&&wr_done_tag==wr_tag)begin writing<=0;retired<=retired+1'b1;end
   if(bad_response||bad_ack)done_error<=1;
   // Error drains accepted traffic; success waits for the last physical ACK.
   if(active&&((done_error&&issued==received&&!writing&&!read_offer&&!write_offer)||(retired==count&&count!=0&&!writing)))begin active<=0;report<=1;end
   if(report&&done_ready)report<=0;
  end
 end
endmodule
