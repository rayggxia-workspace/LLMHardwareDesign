`timescale 1ns/1ps
// Parent control service for one selected N32-mod macro and its owned SRAM.
// There is no arithmetic instance and no inter-group connection in this module.
// Opcode 1: in-place Softmax; 2: RMS factor; 3: Argmax.
// Scalar modes commit one 16-byte result record before reporting completion.
module n32_service_controller #(parameter logic [31:0] TOPOLOGY=0)(
 input wire clk,reset,service_valid,
 output wire service_ready,
 input wire [127:0] service_owner,
 input wire [31:0] service_ticket,
 input wire [1023:0] service_descriptor,
 input wire service_cancel_valid,
 output wire service_cancel_ready,
 output wire service_done_valid,
 input wire service_done_ready,
 output reg [127:0] service_done_owner,
 output reg [31:0] service_done_ticket,
 output reg [15:0] service_done_status,
 output reg [31:0] service_done_read_bytes,service_done_write_bytes,
 output wire s_req_valid,s_req_write,
 input wire s_req_ready,
 output wire [9:0] s_req_address,
 output wire [127:0] s_req_data,
 input wire s_rsp_valid,
 output wire s_rsp_ready,
 input wire [127:0] s_rsp_data,
 input wire s_rsp_error,
 output wire resource_n_cmd_valid,
 input wire resource_n_cmd_ready,
 output wire [31:0] resource_n_cmd_tag,
 output wire [1:0] resource_n_cmd_mode,
 output wire [9:0] resource_n_cmd_base,
 output wire [12:0] resource_n_cmd_count,
 output wire resource_n_cmd_committed,
 output wire resource_n_abort_valid,
 input wire resource_n_abort_ready,
 output wire [31:0] resource_n_abort_tag,
 input wire resource_n_rsp_valid,
 output wire resource_n_rsp_ready,
 input wire [31:0] resource_n_rsp_tag,
 input wire resource_n_rsp_error,resource_n_rsp_aborted,
 input wire [11:0] resource_n_rsp_writes,
 input wire resource_n_s_req_valid,resource_n_s_req_write,
 output wire resource_n_s_req_ready,
 input wire [9:0] resource_n_s_req_address,
 input wire [127:0] resource_n_s_req_data,
 output wire resource_n_s_rsp_valid,
 input wire resource_n_s_rsp_ready,
 output wire [127:0] resource_n_s_rsp_data,
 output wire resource_n_s_rsp_error
);
 localparam [2:0] IDLE=0,CFG_OFFER=1,CFG_WAIT=2,EXEC_OFFER=3,RUN=4,REPORT=5;
 reg [2:0] state;
 reg cancelled,pending_write,cfg_step;
 reg [1:0] mode;
 reg [9:0] base,result_word;
 reg [12:0] count;
 reg [31:0] epsilon;
 reg signed [7:0] epsilon_shift;
 reg signed [5:0] baseline_shift;
 wire [15:0] operation=service_descriptor[48+:16];
 wire [15:0] offered_base=service_descriptor[128+:16];
 wire [15:0] offered_count=service_descriptor[144+:16];
 wire [15:0] offered_result=service_descriptor[208+:16];
 wire [7:0] offered_shift=service_descriptor[192+:8];
 wire [16:0] offered_words=({1'b0,offered_count}+17'd3)>>2;
 wire legal=service_descriptor[31:0]==32'h3156534e&&
   service_descriptor[32+:16]==128&&operation>=1&&operation<=3&&
   service_descriptor[64+:32]==32'h02504e03&&service_descriptor[96+:32]==TOPOLOGY&&
   service_descriptor[991:224]==0&&offered_count!=0&&offered_count<=4096&&
   ({1'b0,offered_base}+offered_words<=1024)&&
   offered_shift[7:6]=={2{offered_shift[5]}}&&
   (operation==2 ? service_descriptor[160+:32]!=0 :
    service_descriptor[160+:48]==0)&&
   (operation==1 ? offered_result==16'hffff : offered_result<1024);
 wire cancel_now=service_cancel_valid&&service_cancel_ready;
 assign service_ready=!reset&&state==IDLE;
 assign service_done_valid=!reset&&state==REPORT;
 assign service_cancel_ready=!reset&&!cancelled&&state!=IDLE&&state!=REPORT;
 wire [31:0] cfg_tag=cfg_step ? {18'd0,epsilon_shift,baseline_shift} : epsilon;
 wire configuring=state==CFG_OFFER||state==CFG_WAIT;
 assign resource_n_cmd_valid=!reset&&(state==CFG_OFFER||state==EXEC_OFFER);
 assign resource_n_cmd_tag=configuring ? cfg_tag : service_done_ticket;
 assign resource_n_cmd_mode=configuring ? 2'd3 : mode;
 assign resource_n_cmd_base=configuring ? (cfg_step ? result_word : 10'd0) : base;
 assign resource_n_cmd_count=configuring ? {12'd0,cfg_step} : count;
 assign resource_n_cmd_committed=1'b1;
 assign resource_n_abort_valid=!reset&&state==RUN&&(cancelled||cancel_now);
 assign resource_n_abort_tag=service_done_ticket;
 assign resource_n_rsp_ready=!reset&&(state==RUN||state==CFG_WAIT);
 assign resource_n_s_req_ready=state==RUN&&s_req_ready;
 assign resource_n_s_rsp_valid=state==RUN&&s_rsp_valid;
 assign resource_n_s_rsp_data=s_rsp_data;
 assign resource_n_s_rsp_error=s_rsp_error;
 assign s_req_valid=!reset&&state==RUN&&resource_n_s_req_valid;
 assign s_req_write=resource_n_s_req_write;
 assign s_req_address=resource_n_s_req_address;
 assign s_req_data=resource_n_s_req_data;
 assign s_rsp_ready=!reset&&state==RUN&&resource_n_s_rsp_ready;
 always @(posedge clk)begin
  if(reset)begin
   state<=IDLE;cancelled<=0;pending_write<=0;cfg_step<=0;mode<=0;base<=0;result_word<=0;count<=0;
   epsilon<=0;epsilon_shift<=0;baseline_shift<=0;
   service_done_owner<=0;service_done_ticket<=0;service_done_status<=0;
   service_done_read_bytes<=0;service_done_write_bytes<=0;
  end else begin
   if(cancel_now)cancelled<=1;
   if(s_req_valid&&s_req_ready)pending_write<=s_req_write;
   if(s_rsp_valid&&s_rsp_ready&&!s_rsp_error)begin
    if(pending_write)service_done_write_bytes<=service_done_write_bytes+16;
    else service_done_read_bytes<=service_done_read_bytes+16;
   end
   case(state)
    IDLE:if(service_valid)begin
     service_done_owner<=service_owner;service_done_ticket<=service_ticket;
     service_done_status<=legal ? 0 : 16'h0310;
     service_done_read_bytes<=0;service_done_write_bytes<=0;cancelled<=0;
     mode<=2'(operation-1);base<=offered_base[9:0];count<=offered_count[12:0];
     result_word<=offered_result[9:0];epsilon<=service_descriptor[160+:32];
     baseline_shift<=offered_shift[5:0];epsilon_shift<=service_descriptor[200+:8];
     cfg_step<=operation==3;
     state<=!legal ? REPORT : operation==1 ? EXEC_OFFER : CFG_OFFER;
    end
    CFG_OFFER:if(resource_n_cmd_ready)state<=CFG_WAIT;
    CFG_WAIT:if(resource_n_rsp_valid)begin
     if(resource_n_rsp_error||resource_n_rsp_aborted||resource_n_rsp_tag!=cfg_tag)begin
      service_done_status<=16'h0312;state<=REPORT;
     end else if(cancelled||cancel_now)begin service_done_status<=16'h0311;state<=REPORT;end
     else if(!cfg_step)begin cfg_step<=1;state<=CFG_OFFER;end
     else state<=EXEC_OFFER;
    end
    EXEC_OFFER:if(resource_n_cmd_ready)state<=RUN;
    RUN:if(resource_n_rsp_valid)begin
     service_done_status<=resource_n_rsp_error||resource_n_rsp_tag!=service_done_ticket ?
       16'h0312 : resource_n_rsp_aborted||cancelled||cancel_now ? 16'h0311 : 16'd0;
     state<=REPORT;
    end
    REPORT:if(service_done_ready)state<=IDLE;
    default:begin service_done_status<=16'h0312;state<=REPORT;end
   endcase
  end
 end
endmodule
