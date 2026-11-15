`timescale 1ns/1ps
// Parent control/format adapter. Arithmetic is performed only by the selected
// E32 MAC macro. Independent A/B DDR cache lines and one outstanding read; no hidden dot core.
module e32_dot_service_controller #(parameter logic [31:0] TOPOLOGY=0)(
 input wire clk,reset,
 input wire service_valid,output wire service_ready,
 input wire [127:0] service_owner,input wire [31:0] service_ticket,
 input wire [1023:0] service_descriptor,
 input wire service_cancel_valid,output wire service_cancel_ready,
 output wire service_done_valid,input wire service_done_ready,
 output reg [127:0] service_done_owner,output reg [31:0] service_done_ticket,
 output reg [15:0] service_done_status,
 output reg [31:0] service_done_read_bytes,service_done_write_bytes,
 output wire rd_valid,input wire rd_ready,output wire [63:0] rd_address,rd_tag,
 input wire rd_rsp_valid,output wire rd_rsp_ready,input wire [63:0] rd_rsp_tag,
 input wire [511:0] rd_rsp_data,input wire rd_rsp_error,
 output wire s_req_valid,s_req_write,input wire s_req_ready,
 output wire [9:0] s_req_address,output wire [127:0] s_req_data,
 input wire s_rsp_valid,output wire s_rsp_ready,input wire [127:0] s_rsp_data,input wire s_rsp_error,
 output wire resource_e_in_valid,input wire resource_e_in_ready,
 output wire [63:0] resource_e_in_data,output wire [3:0] resource_e_in_op,resource_e_in_mask,
 output wire [7:0] resource_e_in_shift,output wire [2:0] resource_e_in_minus,
 input wire resource_e_out_valid,output wire resource_e_out_ready,
 input wire [63:0] resource_e_out_data,input wire [3:0] resource_e_out_clipped,input wire resource_e_out_error
);
 localparam [4:0] IDLE=0,BEGIN_SEND=1,BEGIN_WAIT=2,A_READ=3,B_READ=4,READ_REQ=5,READ_WAIT=6,
  STEP_SEND=7,STEP_WAIT=8,END_SEND=9,END_WAIT=10,SCALE_SEND=11,SCALE_WAIT=12,
  WRITE_REQ=13,WRITE_WAIT=14,ABORT_SEND=15,ABORT_WAIT=16,REPORT=17;
 localparam [15:0] BAD_DESC=16'h0340,ABORTED=16'h0341,DDR_FAULT=16'h0342,E_FAULT=16'h0343,
  SRAM_FAULT=16'h0344,ADDRESS_FAULT=16'h0345;
 reg [4:0] state,return_state;
 reg cancelled,macro_live,cache_a_valid,cache_b_valid,out_high,e_error;
 reg [1:0] beat,lane;
 reg [15:0] full_k,k;
 reg [2:0] columns;
 reg [5:0] shift,scale_shift;
 reg [9:0] result_word;
 reg scale_enabled;
 reg [31:0] coefficient,a_stride,b_k_stride,b_column_stride,a_value;
 reg [63:0] a_address,b_address,b_lane_address,read_address,cache_a_address,cache_b_address;
 reg [511:0] cache_a_data,cache_b_data;
 reg [127:0] b_values,result;
 reg [31:0] session,read_sequence;
 wire [15:0] d_k=service_descriptor[128+:16],d_result=service_descriptor[160+:16];
 wire [7:0] d_columns=service_descriptor[144+:8],d_shift=service_descriptor[152+:8];
 wire [63:0] d_a=service_descriptor[192+:64],d_b=service_descriptor[256+:64];
 wire legal=TOPOLOGY!=0&&service_descriptor[31:0]==32'h31444d45&&
  service_descriptor[32+:16]==128&&service_descriptor[48+:16]==1&&
  service_descriptor[64+:32]==32'h02504503&&service_descriptor[96+:32]==TOPOLOGY&&
  d_k!=0&&d_columns>=1&&d_columns<=4&&d_shift<=63&&d_result<1024&&
  service_descriptor[176+:16]==0&&d_a[63:48]==0&&d_b[63:48]==0&&d_a[1:0]==0&&d_b[1:0]==0&&
  service_descriptor[320+:2]==0&&service_descriptor[352+:2]==0&&service_descriptor[384+:2]==0&&
  service_descriptor[416+:8]<=1&&service_descriptor[424+:8]<=63&&service_descriptor[432+:16]==0&&
  (service_descriptor[416]||service_descriptor[424+:8]==0&&service_descriptor[448+:32]==0)&&
  service_descriptor[480+:512]==0&&session!=32'hffffffff;
 wire cancel_now=cancelled||(service_cancel_valid&&service_cancel_ready);
 assign service_ready=!reset&&state==IDLE;
 assign service_cancel_ready=!reset&&state!=IDLE&&state!=REPORT;
 assign service_done_valid=!reset&&state==REPORT;
 assign rd_valid=!reset&&state==READ_REQ;
 assign rd_address=read_address;
 assign rd_tag={session,read_sequence};
 assign rd_rsp_ready=!reset&&state==READ_WAIT;
 assign s_req_valid=!reset&&state==WRITE_REQ;
 assign s_req_write=1;
 assign s_req_address=result_word;
 assign s_req_data=result;
 assign s_rsp_ready=!reset&&state==WRITE_WAIT;
 wire sending=state==BEGIN_SEND||state==STEP_SEND||state==END_SEND||state==SCALE_SEND||state==ABORT_SEND;
 wire waiting=state==BEGIN_WAIT||state==STEP_WAIT||state==END_WAIT||state==SCALE_WAIT||state==ABORT_WAIT;
 wire binary_command=state==STEP_SEND||state==SCALE_SEND;
 wire [127:0] operand=state==BEGIN_SEND?{112'd0,full_k}:
   state==STEP_SEND?(beat[1]?b_values:{4{a_value}}):
   state==SCALE_SEND?(beat[1]?{4{coefficient}}:result):128'd0;
 assign resource_e_in_valid=!reset&&sending;
 assign resource_e_in_data=beat[0]?operand[127:64]:operand[63:0];
 assign resource_e_in_op=state==BEGIN_SEND?4'd12:state==STEP_SEND?4'd13:
                         state==END_SEND?4'd14:state==SCALE_SEND?4'd2:4'd15;
 assign resource_e_in_mask=(4'b1<<columns)-4'b1;
 assign resource_e_in_shift=state==BEGIN_SEND||state==END_SEND?{2'd0,shift}:
                            state==SCALE_SEND?{2'd0,scale_shift}:8'd0;
 assign resource_e_in_minus=0;
 assign resource_e_out_ready=!reset&&waiting;
 wire [63:0] operand_address=state==A_READ?a_address:b_lane_address;
 wire cache_a_hit=cache_a_valid&&cache_a_address=={operand_address[63:6],6'd0};
 wire cache_b_hit=cache_b_valid&&cache_b_address=={operand_address[63:6],6'd0};
 wire cache_hit=cache_a_hit||cache_b_hit;
 wire [511:0] selected_cache=cache_a_hit?cache_a_data:cache_b_data;
 wire [31:0] cached_value=selected_cache[32*operand_address[5:2]+:32];
 wire [64:0] next_a={1'b0,a_address}+{33'd0,a_stride};
 wire [64:0] next_b={1'b0,b_address}+{33'd0,b_k_stride};
 wire [64:0] next_lane={1'b0,b_lane_address}+{33'd0,b_column_stride};
 always @(posedge clk)begin
  if(reset)begin
   state<=IDLE;return_state<=A_READ;cancelled<=0;macro_live<=0;cache_a_valid<=0;cache_b_valid<=0;out_high<=0;e_error<=0;
   beat<=0;lane<=0;full_k<=0;k<=0;columns<=0;shift<=0;scale_shift<=0;result_word<=0;scale_enabled<=0;
   coefficient<=0;a_stride<=0;b_k_stride<=0;b_column_stride<=0;a_value<=0;
   a_address<=0;b_address<=0;b_lane_address<=0;read_address<=0;cache_a_address<=0;cache_b_address<=0;cache_a_data<=0;cache_b_data<=0;
   b_values<=0;result<=0;session<=0;read_sequence<=0;
   service_done_owner<=0;service_done_ticket<=0;service_done_status<=0;
   service_done_read_bytes<=0;service_done_write_bytes<=0;
  end else begin
   if(service_cancel_valid&&service_cancel_ready)cancelled<=1;
   if(sending&&resource_e_in_valid&&resource_e_in_ready)begin
    if(beat==(binary_command?2'd3:2'd1))begin
     beat<=0;out_high<=0;e_error<=0;
     case(state)
      BEGIN_SEND:state<=BEGIN_WAIT;
      STEP_SEND:state<=STEP_WAIT;
      END_SEND:state<=END_WAIT;
      SCALE_SEND:state<=SCALE_WAIT;
      default:state<=ABORT_WAIT;
     endcase
    end else beat<=beat+1'b1;
   end
   if(waiting&&resource_e_out_valid&&resource_e_out_ready)begin
    out_high<=!out_high;e_error<=e_error||resource_e_out_error;
    if(!out_high)result[63:0]<=resource_e_out_data;
    else begin
     result[127:64]<=resource_e_out_data;
     if(e_error||resource_e_out_error)begin
      service_done_status<=E_FAULT;
      state<=macro_live&&state!=ABORT_WAIT?ABORT_SEND:REPORT;
     end else case(state)
      BEGIN_WAIT:begin
       macro_live<=1;
       if(cancel_now)begin service_done_status<=ABORTED;state<=ABORT_SEND;end
       else state<=A_READ;
      end
      STEP_WAIT:begin
       if(cancel_now)begin service_done_status<=ABORTED;state<=ABORT_SEND;end
       else if(k==full_k-1'b1)state<=END_SEND;
       else if(next_a>65'h1000000000000-4||next_b>65'h1000000000000-4)begin
        service_done_status<=ADDRESS_FAULT;state<=ABORT_SEND;
       end else begin
        k<=k+1'b1;a_address<=next_a[63:0];b_address<=next_b[63:0];state<=A_READ;
       end
      end
      END_WAIT:begin
       macro_live<=0;
       if(cancel_now)begin service_done_status<=ABORTED;state<=REPORT;end
       else state<=scale_enabled?SCALE_SEND:WRITE_REQ;
      end
      SCALE_WAIT:begin
       if(cancel_now)begin service_done_status<=ABORTED;state<=REPORT;end
       else state<=WRITE_REQ;
      end
      default:begin macro_live<=0;state<=REPORT;end
     endcase
    end
   end
   case(state)
    IDLE:if(service_valid&&service_ready)begin
     service_done_owner<=service_owner;service_done_ticket<=service_ticket;
     service_done_status<=legal?0:BAD_DESC;service_done_read_bytes<=0;service_done_write_bytes<=0;
     cancelled<=0;macro_live<=0;cache_a_valid<=0;cache_b_valid<=0;beat<=0;out_high<=0;e_error<=0;result<=0;
     full_k<=d_k;k<=0;columns<=d_columns[2:0];shift<=d_shift[5:0];result_word<=d_result[9:0];
     a_address<=d_a;b_address<=d_b;b_lane_address<=d_b;
     a_stride<=service_descriptor[320+:32];b_k_stride<=service_descriptor[352+:32];
     b_column_stride<=service_descriptor[384+:32];scale_enabled<=service_descriptor[416];
     scale_shift<=service_descriptor[424+:6];coefficient<=service_descriptor[448+:32];
     session<=session+1'b1;read_sequence<=0;
     state<=legal?BEGIN_SEND:REPORT;
    end
    A_READ,B_READ:begin
     if(cancel_now)begin service_done_status<=ABORTED;state<=ABORT_SEND;end
     else if(operand_address[63:48]!=0||operand_address[1:0]!=0)begin
      service_done_status<=ADDRESS_FAULT;state<=ABORT_SEND;
     end else if(!cache_hit)begin
      read_address<={operand_address[63:6],6'd0};return_state<=state;state<=READ_REQ;
     end else if(state==A_READ)begin
      a_value<=cached_value;b_values<=0;lane<=0;b_lane_address<=b_address;state<=B_READ;
     end else begin
      b_values[32*lane+:32]<=cached_value;
      if({1'b0,lane}+3'd1==columns)state<=STEP_SEND;
      else if(next_lane>65'h1000000000000-4)begin service_done_status<=ADDRESS_FAULT;state<=ABORT_SEND;end
      else begin lane<=lane+1'b1;b_lane_address<=next_lane[63:0];end
     end
    end
    READ_REQ:if(rd_valid&&rd_ready)state<=READ_WAIT;
    READ_WAIT:if(rd_rsp_valid&&rd_rsp_ready)begin
     service_done_read_bytes<=service_done_read_bytes+64;
     read_sequence<=read_sequence+1'b1;
     if(rd_rsp_error||rd_rsp_tag!=rd_tag)begin service_done_status<=DDR_FAULT;state<=ABORT_SEND;end
     else if(cancel_now)begin service_done_status<=ABORTED;state<=ABORT_SEND;end
     else begin
      if(return_state==A_READ)begin cache_a_valid<=1;cache_a_address<=read_address;cache_a_data<=rd_rsp_data;end
      else begin cache_b_valid<=1;cache_b_address<=read_address;cache_b_data<=rd_rsp_data;end
      state<=return_state;
     end
    end
    WRITE_REQ:if(s_req_valid&&s_req_ready)state<=WRITE_WAIT;
    WRITE_WAIT:if(s_rsp_valid&&s_rsp_ready)begin
     if(!s_rsp_error)service_done_write_bytes<=16;
     if(s_rsp_error)service_done_status<=SRAM_FAULT;
     else if(cancel_now)service_done_status<=ABORTED;
     state<=REPORT;
    end
    REPORT:if(service_done_ready)state<=IDLE;
    default:begin end
   endcase
  end
 end
 wire unused=^{s_rsp_data,resource_e_out_clipped};
endmodule
