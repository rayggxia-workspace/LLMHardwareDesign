`timescale 1ns/1ps
// N32 hard-macro revision. Only cmd_mode[1:0] extends the original pins.
// Mode 0: original Softmax. Mode 1: RMS factor. Mode 2: Argmax.
// Mode 3/count 0: epsilon=cmd_tag, clear configuration.
// Mode 3/count 1: shifts={cmd_tag[13:6],cmd_tag[5:0]}, result word=cmd_base.
// Each configuration is a real acknowledged command. Scalar results commit to S.
// The internal engine shares the original two scale lanes and divider/root unit.
module n_s32_mod(
 input wire clk,reset,
 input wire cmd_valid,output wire cmd_ready,input wire [31:0] cmd_tag,
 input wire [1:0] cmd_mode,
 input wire [9:0] cmd_base,input wire [12:0] cmd_count,input wire cmd_committed,
 input wire abort_valid,output wire abort_ready,input wire [31:0] abort_tag,
 output wire rsp_valid,input wire rsp_ready,output wire [31:0] rsp_tag,
 output wire rsp_error,rsp_aborted,output wire [11:0] rsp_writes,
 output wire s_req_valid,input wire s_req_ready,output wire s_req_write,
 output wire [9:0] s_req_address,output wire [127:0] s_req_data,
 input wire s_rsp_valid,output wire s_rsp_ready,input wire [127:0] s_rsp_data,input wire s_rsp_error
);
 localparam [2:0] IDLE=0,RUN=1,STORE=2,ACK=3,REPORT=4;
 reg [2:0] state;
 reg epsilon_valid,format_valid,cancelled;
 reg [31:0] epsilon,tag;
 reg signed [5:0] baseline_shift;
 reg signed [7:0] epsilon_shift;
 reg [9:0] result_word;
 reg [1:0] mode;
 reg [127:0] result;
 reg failed,aborted;reg [11:0] writes;
 wire engine_ready,engine_rsp_valid,engine_error,engine_aborted,engine_abort_ready;
 wire [31:0] engine_tag,engine_scalar,engine_index;
 wire signed [5:0] engine_shift;wire [5:0] engine_extra;
 wire [11:0] engine_writes;
 wire engine_s_valid,engine_s_write,engine_s_take;
 wire [9:0] engine_s_address;wire [127:0] engine_s_data;
 wire mode_configured=cmd_mode==0||(cmd_mode==1&&epsilon_valid&&format_valid)||(cmd_mode==2&&format_valid);
 wire launch=state==IDLE&&cmd_valid&&cmd_mode!=3&&mode_configured;
 wire passthrough=state==RUN&&mode==0;
 wire stop=cancelled||(abort_valid&&abort_ready);
 assign cmd_ready=!reset&&state==IDLE&&(cmd_mode==3||!mode_configured||engine_ready);
 assign rsp_valid=!reset&&(state==REPORT||(passthrough&&engine_rsp_valid));
 assign rsp_tag=passthrough ? engine_tag : tag;
 assign rsp_error=passthrough ? engine_error : failed;
 assign rsp_aborted=passthrough ? engine_aborted : aborted;
 assign rsp_writes=passthrough ? engine_writes : writes;
 assign abort_ready=!reset&&(state==RUN ? engine_abort_ready :
    (state==STORE||state==ACK)&&!cancelled&&abort_tag==tag);
 assign s_req_valid=!reset&&(state==STORE||(state==RUN&&engine_s_valid));
 assign s_req_write=state==STORE||(state==RUN&&engine_s_write);
 assign s_req_address=state==STORE ? result_word : engine_s_address;
 assign s_req_data=state==STORE ? result : engine_s_data;
 assign s_rsp_ready=!reset&&(state==ACK||(state==RUN&&engine_s_take));
 n_s32_reduction_engine engine(
  .clk,.reset,.cmd_valid(launch),.cmd_ready(engine_ready),.cmd_tag,.cmd_mode,
  .cmd_base,.cmd_count,.cmd_committed,.cmd_epsilon_mantissa(epsilon),
  .cmd_epsilon_shift(epsilon_shift),.cmd_baseline_shift(baseline_shift),
  .abort_valid(abort_valid&&state==RUN),.abort_ready(engine_abort_ready),.abort_tag,
  .rsp_valid(engine_rsp_valid),.rsp_ready(state==RUN&&(mode!=0||rsp_ready)),
  .rsp_tag(engine_tag),.rsp_error(engine_error),.rsp_aborted(engine_aborted),
  .rsp_writes(engine_writes),.rsp_scalar(engine_scalar),.rsp_index(engine_index),
  .rsp_shift(engine_shift),.rsp_extra_shift(engine_extra),
  .s_req_valid(engine_s_valid),.s_req_ready(state==RUN&&s_req_ready),
  .s_req_write(engine_s_write),.s_req_address(engine_s_address),.s_req_data(engine_s_data),
  .s_rsp_valid(state==RUN&&s_rsp_valid),.s_rsp_ready(engine_s_take),.s_rsp_data,.s_rsp_error);
 always @(posedge clk)begin
  if(reset)begin
   state<=IDLE;epsilon_valid<=0;format_valid<=0;cancelled<=0;
   epsilon<=0;tag<=0;baseline_shift<=0;epsilon_shift<=0;result_word<=0;
   mode<=0;result<=0;failed<=0;aborted<=0;writes<=0;
  end else begin
   if(abort_valid&&abort_ready)cancelled<=1;
   case(state)
    IDLE:if(cmd_valid&&cmd_ready)begin
     tag<=cmd_tag;mode<=cmd_mode;failed<=0;aborted<=0;writes<=0;cancelled<=0;
     if(cmd_mode==3)begin
      state<=REPORT;
      if(!cmd_committed)begin failed<=1;epsilon_valid<=0;format_valid<=0;end
      else if(cmd_count==0&&cmd_base==0&&cmd_tag!=0)begin
       epsilon<=cmd_tag;epsilon_valid<=1;format_valid<=0;
      end else if(cmd_count==1&&cmd_tag[31:14]==0)begin
       baseline_shift<=cmd_tag[5:0];epsilon_shift<=cmd_tag[13:6];
       result_word<=cmd_base;format_valid<=1;
      end else begin failed<=1;epsilon_valid<=0;format_valid<=0;end
     end else begin
      epsilon_valid<=0;format_valid<=0;
      if(!mode_configured)begin failed<=1;state<=REPORT;end
      else state<=RUN;
     end
    end
    RUN:if(engine_rsp_valid)begin
     if(mode==0)begin if(rsp_ready)state<=IDLE;end
     else if(engine_error||engine_aborted||engine_tag!=tag||stop)begin
      failed<=engine_error||engine_tag!=tag;aborted<=engine_aborted||stop;state<=REPORT;
     end else begin
      result<={40'd0,6'd0,mode,2'd0,engine_extra,{2{engine_shift[5]}},engine_shift,engine_index,engine_scalar};
      state<=STORE;
     end
    end
    STORE:if(s_req_ready)state<=ACK;
    ACK:if(s_rsp_valid)begin failed<=s_rsp_error;aborted<=stop;writes<=s_rsp_error ? 0 : 1;state<=REPORT;end
    REPORT:if(rsp_ready)state<=IDLE;
    default:begin failed<=1;state<=REPORT;end
   endcase
  end
 end
endmodule
