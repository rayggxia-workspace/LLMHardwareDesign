`timescale 1ns/1ps
// Descriptor-driven existing G32 leaf, retaining SRAM until final write ACK.
module gated_s32_scope #(parameter logic [31:0] TOPOLOGY=25001)(
 input wire clk,reset,service_valid,output wire service_ready,
 input wire [127:0] service_owner,input wire [31:0] service_ticket,
 input wire [1023:0] service_descriptor,
 input wire service_cancel_valid,output wire service_cancel_ready,
 output wire service_done_valid,input wire service_done_ready,
 output reg [127:0] service_done_owner,output reg [15:0] service_done_status,
 output reg [31:0] service_done_read_bytes,service_done_write_bytes,
 output wire s_req_valid,s_req_write,input wire s_req_ready,
 output wire [9:0] s_req_address,output wire [127:0] s_req_data,
 input wire s_rsp_valid,output wire s_rsp_ready,input wire [127:0] s_rsp_data
);
 localparam [1:0] IDLE=0,LAUNCH=1,RUN=2,REPORT=3;
 reg [1:0] state;reg cancelled;
 reg [9:0] gate_base,up_base,output_base;reg [5:0] words;
 wire [15:0] a=service_descriptor[128+:16],b=service_descriptor[144+:16],
              c=service_descriptor[160+:16],n=service_descriptor[176+:16];
 wire [16:0] ae={1'b0,a}+{1'b0,n},be={1'b0,b}+{1'b0,n},ce={1'b0,c}+{1'b0,n};
 wire legal=service_descriptor[31:0]==32'h314d5347 && service_descriptor[32+:16]==128 &&
  service_descriptor[48+:16]==1 && service_descriptor[64+:32]==32'h02500002 &&
  service_descriptor[96+:32]==TOPOLOGY && service_descriptor[991:192]==0 &&
  n>0&&n<=32&&ae<=1024&&be<=1024&&ce<=1024&&
  (ae<={1'b0,b}||be<={1'b0,a})&&(ae<={1'b0,c}||ce<={1'b0,a})&&(be<={1'b0,c}||ce<={1'b0,b});
 wire ready,done,error;wire [5:0] done_words;
 wire gin,gready,gout,gtake,gated,gerror;wire [63:0] gate,up,value;wire [1:0] mask,outmask;
 reg tags[0:1];reg head,tail;
 assign service_ready=!reset&&state==IDLE;
 assign service_done_valid=!reset&&state==REPORT;
 assign service_cancel_ready=!reset&&(state==LAUNCH||state==RUN)&&!cancelled;
 g_s128_frontend frontend(.clk,.reset,.cmd_valid(state==LAUNCH),.cmd_ready(ready),
  .cmd_gate_base(gate_base),.cmd_up_base(up_base),.cmd_mid_base(output_base),.cmd_words(words),.cmd_gated(1'b1),
  .done_valid(done),.done_take(state==RUN),.done_error(error),.done_words,
  .s_req_valid,.s_req_write,.s_req_addr(s_req_address),.s_req_data,.s_req_ready,.s_rsp_valid,.s_rsp_ready,.s_rsp_data,
  .g_in_valid(gin),.g_in_ready(gready),.g_in_gate(gate),.g_in_up(up),.g_in_gated(gated),.g_in_mask(mask),
  .g_out_valid(gout),.g_out_ready(gtake),.g_out_data(value),.g_out_mask(outmask),.g_out_error(gerror));
 g_s32 G(.clk,.reset,.in_valid(gin),.in_ready(gready),.in_gate(gate),.in_up(up),.in_gated(gated),
  .in_mask(mask),.out_valid(gout),.out_ready(gtake),.out_data(value),.out_mask(outmask),.out_error(gerror));
 always @(posedge clk)begin
  if(reset)begin state<=IDLE;cancelled<=0;gate_base<=0;up_base<=0;output_base<=0;words<=0;
   service_done_owner<=0;service_done_status<=0;service_done_read_bytes<=0;service_done_write_bytes<=0;head<=0;tail<=0;end
  else begin
   if(service_cancel_valid&&service_cancel_ready)cancelled<=1;
   if(s_req_valid&&s_req_ready)begin tags[tail]<=s_req_write;tail<=!tail;end
   if(s_rsp_valid&&s_rsp_ready)begin
    head<=!head;
    if(tags[head])service_done_write_bytes<=service_done_write_bytes+16;
    else service_done_read_bytes<=service_done_read_bytes+16;
   end
   case(state)
    IDLE:if(service_valid)begin
     service_done_owner<=service_owner;service_done_status<=legal?0:16'h02f0;
     service_done_read_bytes<=0;service_done_write_bytes<=0;cancelled<=0;head<=0;tail<=0;
     gate_base<=a[9:0];up_base<=b[9:0];output_base<=c[9:0];words<=n[5:0];
     state<=legal?LAUNCH:REPORT;
    end
    LAUNCH:if(ready)state<=RUN;
    RUN:if(done)begin
     service_done_status<=error||done_words!=words ? 16'h02f1 :
      (cancelled||(service_cancel_valid&&service_cancel_ready)) ? 16'h02f2 : 16'd0;
     state<=REPORT;
    end
    REPORT:if(service_done_ready)state<=IDLE;
   endcase
  end
 end
 wire unused=^{service_ticket,service_descriptor[1023:992]};
endmodule
