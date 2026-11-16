`timescale 1ns/1ps
// G's P0.S supplies all reads; the selected P.S commits the A16 Mid tile.
// The quantizer expects replies in issue order. Keep two owner IDs only and
// let each actual S hold its reply until oldest; no extra payload or S port.
module quant_mid_s128_router(
 input wire clk,reset,
 input wire [1:0] destination,
 input wire req_valid,req_write,output wire req_ready,
 input wire [9:0] req_address,input wire [127:0] req_data,input wire [31:0] req_tag,
 output wire rsp_valid,input wire rsp_ready,output wire [127:0] rsp_data,
 output wire [31:0] rsp_tag,
 output wire [2:0] s_valid,s_write,input wire [2:0] s_ready,
 output wire [29:0] s_address,output wire [383:0] s_data,output wire [95:0] s_tag,
 input wire [2:0] s_rsp_valid,output wire [2:0] s_rsp_ready,
 input wire [383:0] s_rsp_data,input wire [95:0] s_rsp_tag,
 output wire drained
);
 reg [1:0] owners[2],count;
 reg head,tail;
 wire [1:0] selected=req_write ? destination:2'd0;
 wire [1:0] oldest=owners[head];
 assign drained=count==0;
 assign rsp_valid=!reset&&count!=0&&s_rsp_valid[oldest];
 assign rsp_data=s_rsp_data[128*oldest+:128];
 assign rsp_tag=s_rsp_tag[32*oldest+:32];
 wire pop=rsp_valid&&rsp_ready;
 wire capacity=count<2||pop;
 assign req_ready=!reset&&capacity&&selected<3&&s_ready[selected];
 wire push=req_valid&&req_ready;
 for(genvar p=0;p<3;p=p+1)begin: port
  assign s_valid[p]=!reset&&capacity&&req_valid&&selected==2'(p);
  assign s_write[p]=req_write;
  assign s_address[p*10+:10]=req_address;
  assign s_data[p*128+:128]=req_data;
  assign s_tag[p*32+:32]=req_tag;
  assign s_rsp_ready[p]=!reset&&count!=0&&oldest==2'(p)&&rsp_ready;
 end
 always @(posedge clk)begin
  if(reset)begin count<=0;head<=0;tail<=0;owners[0]<=0;owners[1]<=0;end
  else begin
   if(push)begin owners[tail]<=selected;tail<=!tail;end
   if(pop)head<=!head;
   case({push,pop})
    2'b10:count<=count+2'd1;
    2'b01:count<=count-2'd1;
    default:begin end
   endcase
`ifndef SYNTHESIS
   assert(count<=2)else $fatal(1,"quantization S owner overflow");
`endif
  end
 end
endmodule
