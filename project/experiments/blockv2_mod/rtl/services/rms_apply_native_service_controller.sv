// Parent controls: read committed N result, then command the selected E macro.
module rms_apply_native_service_controller #(parameter logic [31:0] TOPOLOGY=0)(
 input wire clk,
 input wire reset,
 input wire service_valid,
 output wire service_ready,
 input wire [127:0] service_owner,
 input wire [31:0] service_ticket,
 input wire [1023:0] service_descriptor,
 input wire service_cancel_valid,
 output wire service_cancel_ready,
 output wire service_done_valid,
 input wire service_done_ready,
 output wire [127:0] service_done_owner,
 output wire [31:0] service_done_ticket,
 output wire [15:0] service_done_status,
 output wire [31:0] service_done_read_bytes,
 output wire [31:0] service_done_write_bytes,
 output wire s_req_valid,
 input wire s_req_ready,
 output wire s_req_write,
 output wire [9:0] s_req_address,
 output wire [127:0] s_req_data,
 input wire s_rsp_valid,
 output wire s_rsp_ready,
 input wire [127:0] s_rsp_data,
 input wire s_rsp_error,
 output wire resource_e_in_valid,
 input wire resource_e_in_ready,
 output wire [63:0] resource_e_in_data,
 output wire [3:0] resource_e_in_op,
 output wire [3:0] resource_e_in_mask,
 output wire [7:0] resource_e_in_shift,
 output wire [2:0] resource_e_in_minus,
 input wire resource_e_out_valid,
 output wire resource_e_out_ready,
 input wire [63:0] resource_e_out_data,
 input wire [3:0] resource_e_out_clipped,
 input wire resource_e_out_error
);
 localparam [15:0] BAD_DESC=16'h0350,BAD_FACTOR=16'h0351,FAULT=16'h0352,ABORTED=16'h0353;
 localparam [2:0] IDLE=0,FREAD=1,FWAIT=2,ISSUE=3,ACTIVE=4,REPORT=5;
 reg [2:0] state;reg cancelled,pending_write;
 reg [127:0] owner;reg [31:0] ticket,reads,writes;reg [15:0] status;
 reg [9:0] x,gamma,words,factor_word;reg [31:0] factor;
 reg signed [7:0] factor_shift,gamma_shift;
 wire [15:0] dx=service_descriptor[128+:16],dg=service_descriptor[144+:16];
 wire [15:0] dw=service_descriptor[160+:16],df=service_descriptor[176+:16];
 wire signed [7:0] gs=service_descriptor[192+:8];
 wire [16:0] xe={1'b0,dx}+{1'b0,dw},ge={1'b0,dg}+{1'b0,dw};
 wire legal=TOPOLOGY!=0&&service_descriptor[0+:32]==32'h31414d52&&
 service_descriptor[32+:16]==128&&service_descriptor[48+:16]==1&&
 service_descriptor[64+:32]==32'h02504504&&service_descriptor[96+:32]==TOPOLOGY&&
 service_descriptor[991:200]==0&&dw!=0&&dw<1024&&xe<=1024&&ge<=1024&&df<1024&&
 (xe<=dg||ge<=dx)&&!(df>=dx&&df<xe)&&!(df>=dg&&df<ge)&&gs>=-63&&gs<=63;
 wire signed [7:0] packet_shift=s_rsp_data[64+:8];
 wire [7:0] packet_extra=s_rsp_data[72+:8];
 wire signed [9:0] baseline=10'($signed(packet_shift))-10'({1'b0,packet_extra});
 wire signed [9:0] apply_shift=10'sd14+baseline;
 wire packet_legal=s_rsp_data[127:88]==0&&s_rsp_data[80+:8]==1&&s_rsp_data[32+:32]==0&&
 !s_rsp_data[31]&&packet_shift>=-32&&packet_shift<=31&&packet_extra<=63&&
 baseline>=-32&&baseline<=31&&apply_shift>=-63&&apply_shift<=63;
 wire child_ready,child_done,child_error;
 wire c_valid,c_write,c_take;wire [9:0] c_address;wire [127:0] c_data;
 assign service_ready=!reset&&state==IDLE;
 assign service_cancel_ready=!reset&&state!=IDLE&&state!=REPORT&&!cancelled;
 assign service_done_valid=!reset&&state==REPORT;
 assign service_done_owner=owner;assign service_done_ticket=ticket;
 assign service_done_status=status;assign service_done_read_bytes=reads;assign service_done_write_bytes=writes;
 assign s_req_valid=!reset&&(state==FREAD||(state==ACTIVE&&c_valid));
 assign s_req_write=state==ACTIVE&&c_write;
 assign s_req_address=state==FREAD?factor_word:c_address;
 assign s_req_data=c_data;
 assign s_rsp_ready=!reset&&(state==FWAIT||(state==ACTIVE&&c_take));
 always @(posedge clk)begin
  if(reset)begin state<=IDLE;cancelled<=0;pending_write<=0;owner<=0;ticket<=0;reads<=0;writes<=0;
   status<=0;x<=0;gamma<=0;words<=0;factor_word<=0;factor<=0;factor_shift<=0;gamma_shift<=0;end
  else begin
   if(service_cancel_valid&&service_cancel_ready)cancelled<=1;
   if(s_req_valid&&s_req_ready)pending_write<=s_req_write;
   if(s_rsp_valid&&s_rsp_ready&&!s_rsp_error)begin
    if(pending_write)writes<=writes+16;else reads<=reads+16;
   end
   case(state)
    IDLE:if(service_valid&&service_ready)begin
     owner<=service_owner;ticket<=service_ticket;reads<=0;writes<=0;cancelled<=0;
     x<=dx[9:0];gamma<=dg[9:0];words<=dw[9:0];factor_word<=df[9:0];gamma_shift<=gs;
     status<=legal?0:BAD_DESC;state<=legal?FREAD:REPORT;
    end
    FREAD:if(s_req_ready)state<=FWAIT;
    FWAIT:if(s_rsp_valid)begin
     if(s_rsp_error||!packet_legal)begin status<=s_rsp_error?FAULT:BAD_FACTOR;state<=REPORT;end
     else begin factor<=s_rsp_data[31:0];factor_shift<=apply_shift[7:0];state<=ISSUE;end
    end
    ISSUE:if(child_ready)state<=ACTIVE;
    ACTIVE:if(child_done)begin
     status<=child_error?FAULT:((cancelled||(service_cancel_valid&&service_cancel_ready))?ABORTED:16'd0);
     state<=REPORT;
    end
    REPORT:if(service_done_ready)state<=IDLE;
    default:state<=IDLE;
   endcase
  end
 end
 rms_apply_s32_service_controller apply_control(.clk(clk),.reset(reset),.cmd_valid(state==ISSUE),.cmd_ready(child_ready),.cmd_x(x),.cmd_gamma(gamma),.cmd_words(words),.cmd_factor(factor),.cmd_factor_shift(factor_shift),.cmd_gamma_shift(gamma_shift),.done_valid(child_done),.done_error(child_error),.done_ready(state==ACTIVE),.s_req_valid(c_valid),.s_req_write(c_write),.s_req_ready(s_req_ready&&state==ACTIVE),.s_req_address(c_address),.s_req_data(c_data),.s_rsp_valid(s_rsp_valid&&state==ACTIVE),.s_rsp_error(s_rsp_error),.s_rsp_ready(c_take),.s_rsp_data(s_rsp_data),.resource_e_in_valid(resource_e_in_valid),.resource_e_in_ready(resource_e_in_ready),.resource_e_in_data(resource_e_in_data),.resource_e_in_op(resource_e_in_op),.resource_e_in_mask(resource_e_in_mask),.resource_e_in_shift(resource_e_in_shift),.resource_e_in_minus(resource_e_in_minus),.resource_e_out_valid(resource_e_out_valid),.resource_e_out_error(resource_e_out_error),.resource_e_out_ready(resource_e_out_ready),.resource_e_out_data(resource_e_out_data),.resource_e_out_clipped(resource_e_out_clipped));
endmodule
