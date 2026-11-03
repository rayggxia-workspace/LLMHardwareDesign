// Finite S <-> R-local transport. The R state arrays stay in R; this adapter
// owns one128bit transfer, one512bit command result and protocol cursors.
// Fixed1024-S32-per-bank ABI; the R producer's final qualification is separate.
module control_adapter_r(
 input wire clk,reset,input wire task_valid,output wire task_ready,input wire [255:0] task_data,
 output reg complete_valid,input wire complete_ready,output reg [63:0] complete_data,
 output reg load_valid,input wire load_ready,output reg [2:0] load_target,
 output reg [9:0] load_index,output reg [127:0] load_data,
 output reg rd_bank,output reg [9:0] rd_index,output reg rd_valid,input wire rd_ready,
 input wire rd_rsp_valid,output wire rd_rsp_ready,input wire [127:0] rd_data,
 output reg cmd_valid,input wire cmd_ready,output reg [2:0] cmd_op,
 output reg [8:0] cmd_rows,output reg cmd_role,cmd_clear,output reg [1:0] cmd_mode,
 input wire rsp_valid,output wire rsp_ready,input wire rsp_error,input wire [511:0] rsp_data,
 output reg s_req,output reg s_wr,output reg [9:0] s_addr,output reg [127:0] s_din,
 input wire s_ready,s_valid,output wire s_take,input wire [127:0] s_dout
);
 localparam IDLE=0,S_READ=1,S_REPLY=2,R_LOAD=3,R_DRAIN=4,R_READ=5,R_REPLY=6,
  S_WRITE=7,S_ACK=8,COMMAND=9,RESULT=10,NEXT=11;
 reg [3:0] state;reg [1:0] operation;reg [15:0] tag;
 reg [8:0] remaining;reg [31:0] moved;reg [511:0] result;reg [1:0] result_word;
 wire [31:0] w1=task_data[63:32],w2=task_data[95:64],w3=task_data[127:96],w4=task_data[159:128];
 wire [31:0] packets=w3;
 reg [10:0] target_packets;
 always @*case(w1[2:0])
  0,1:target_packets=256;
  2,3:target_packets=16;
  4,6:target_packets=6;
  5:target_packets=1;
  7:target_packets=4;
 endcase
 wire header_bad=task_data[15:8]!=8'h07 || task_data[7:0]>2 || task_data[255:160]!=0;
 wire address_bad=w4[31:14]!=0 || w4[3:0]!=0;
 // Validate full32bit operands before truncating hardware cursors. Bounds
 // make the additions/shifts below finite and prevent wrapped acceptance.
 wire transfer_bad=packets==0 || packets>256 || w2>255 || address_bad ||
  (w4+32'd16*packets)>16384 ||
  (task_data[7:0]==0 && (w1>7 || w2+packets>{21'b0,target_packets})) ||
  (task_data[7:0]==1 && (w1>1 || w2+packets>256));
 wire command_bad=w1>7 || w2>128 || w3>15 || address_bad || w4>16320;
 assign task_ready=state==IDLE && !complete_valid;
 assign s_take=state==S_REPLY || state==S_ACK;
 assign rd_rsp_ready=state==R_REPLY;
 assign rsp_ready=state==RESULT;
 task finish;
  input [3:0] status;input [31:0] count;
  begin complete_valid<=1;complete_data<={count,8'b0,status,4'd7,tag};state<=IDLE;end
 endtask
 always @(posedge clk)begin
  if(reset)begin
   state<=IDLE;operation<=0;tag<=0;remaining<=0;moved<=0;result<=0;result_word<=0;
   complete_valid<=0;complete_data<=0;load_valid<=0;load_target<=0;load_index<=0;load_data<=0;
   rd_bank<=0;rd_index<=0;rd_valid<=0;cmd_valid<=0;cmd_op<=0;cmd_rows<=0;cmd_role<=0;cmd_clear<=0;cmd_mode<=0;
   s_req<=0;s_wr<=0;s_addr<=0;s_din<=0;
  end else begin
   if(complete_valid && complete_ready)complete_valid<=0;
   case(state)
    IDLE:if(task_valid && task_ready)begin
     tag<=task_data[31:16];operation<=task_data[1:0];remaining<=w3[8:0];moved<=0;result_word<=0;s_addr<=w4[13:4];
     if(header_bad || (task_data[7:0]==2?command_bad:transfer_bad))begin
      complete_valid<=1;complete_data<={32'b0,8'b0,4'd2,4'd7,task_data[31:16]};
     end else case(task_data[7:0])
      0:begin load_target<=w1[2:0];load_index<=w2[9:0];state<=S_READ;end
      1:begin rd_bank<=w1[0];rd_index<=w2[9:0];rd_valid<=1;state<=R_READ;end
      2:begin cmd_op<=w1[2:0];cmd_rows<=w2[8:0];cmd_role<=w3[0];cmd_clear<=w3[1];cmd_mode<=w3[3:2];cmd_valid<=1;state<=COMMAND;end
      default:finish(2,0);
     endcase
    end
    S_READ:if(!s_req)begin s_req<=1;s_wr<=0;end
     else if(s_ready)begin s_req<=0;state<=S_REPLY;end
    S_REPLY:if(s_valid)begin load_data<=s_dout;load_valid<=1;state<=R_LOAD;end
    R_LOAD:if(load_valid && load_ready)begin
     load_valid<=0;moved<=moved+1;
     if(remaining==1)state<=R_DRAIN;
     else begin remaining<=remaining-1;load_index<=load_index+1;s_addr<=s_addr+1;state<=S_READ;end
    end
    // R load_ready is low while its final state write remains in flight.
    R_DRAIN:if(load_ready)finish(0,moved);
    R_READ:if(rd_valid && rd_ready)begin rd_valid<=0;state<=R_REPLY;end
    R_REPLY:if(rd_rsp_valid)begin s_din<=rd_data;s_wr<=1;s_req<=1;state<=S_WRITE;end
    COMMAND:if(cmd_valid && cmd_ready)begin cmd_valid<=0;state<=RESULT;end
    RESULT:if(rsp_valid)begin
     if(rsp_error)finish(4,0);
     else begin result<=rsp_data;s_din<=rsp_data[127:0];s_wr<=1;s_req<=1;state<=S_WRITE;end
    end
    S_WRITE:if(s_req && s_ready)begin s_req<=0;state<=S_ACK;end
    S_ACK:if(s_valid)begin
     moved<=moved+1;
     if(operation==2)begin
      if(result_word==3)finish(0,moved+1);
      else begin result_word<=result_word+1;s_addr<=s_addr+1;state<=NEXT;end
     end else if(remaining==1)finish(0,moved+1);
     else begin remaining<=remaining-1;rd_index<=rd_index+1;s_addr<=s_addr+1;rd_valid<=1;state<=R_READ;end
    end
    NEXT:begin s_din<=result[128*result_word+:128];s_req<=1;state<=S_WRITE;end
    default:finish(3,0);
   endcase
  end
 end
endmodule
