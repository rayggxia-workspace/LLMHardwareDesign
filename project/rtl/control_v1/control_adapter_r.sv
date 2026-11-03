// Endpoint7: bounded S<->qualified R256 transport and native pass commands.
// All payload/control state is owned here; no state is hidden in upper metals.
module control_adapter_r(
 input wire clk,reset,input wire task_valid,output wire task_ready,input wire [255:0] task_data,
 output reg complete_valid,input wire complete_ready,output reg [63:0] complete_data,
 output reg s_req,output reg s_wr,output reg [9:0] s_addr,output reg [127:0] s_din,
 input wire s_ready,s_valid,output wire s_take,input wire [127:0] s_dout,
 output reg load_valid,input wire load_ready,output reg [2:0] load_target,
 output reg [9:0] load_index,output reg [127:0] load_data,
 output reg rd_valid,input wire rd_ready,output reg rd_bank,output reg [9:0] rd_index,
 input wire rd_rsp_valid,output wire rd_rsp_ready,input wire [127:0] rd_data,
 output reg cmd_valid,input wire cmd_ready,output reg [2:0] cmd_op,
 output reg [8:0] cmd_rows,output reg cmd_role,cmd_clear,output reg [1:0] cmd_mode,
 input wire rsp_valid,output wire rsp_ready,input wire rsp_error,input wire [511:0] rsp_data
);
 localparam IDLE=0,SREAD=1,SREPLY=2,LOAD=3,RREAD=4,RREPLY=5,
  SWRITE=6,SACK=7,NEXT=8,COMMAND=9,CREPLY=10;
 reg [3:0] state;reg [1:0] operation;
 reg [15:0] tag;reg [6:0] remaining;reg [9:0] base;
 reg save_result,packed_result;reg [1:0] result_index;
 reg [511:0] response_hold;
 wire [7:0] requested_op=task_data[7:0];
 wire [3:0] flags=task_data[15:12];
 wire [31:0] count=task_data[63:32],reference=task_data[95:64],index=task_data[127:96],target=task_data[159:128];
 reg [31:0] load_limit;
 always @*begin
  case(target[2:0])
   0,1:load_limit=64;
   2,3:load_limit=4;
   4,6:load_limit=6;
   5:load_limit=1;
   default:load_limit=4;
  endcase
 end
 wire transfer=requested_op<2;
 wire [31:0] result_bytes=flags[1]?32'd32:32'd64;
 wire [31:0] bytes=transfer?(count<<4):(flags[0]?result_bytes:32'd0);
 wire invalid=task_data[11:8]!=4'd7 || requested_op>2 || task_data[255:160]!=0 ||
  reference[31:14]!=0 || reference[3:0]!=0 || reference+bytes>16384 ||
  (transfer && (flags!=0 || count==0 || count>64 || index>63)) ||
  (requested_op==0 && (target>7 || index+count>load_limit)) ||
  (requested_op==1 && (target>1 || index+count>64)) ||
  (requested_op==2 && (flags[3:2]!=0 || (flags[1]&&!flags[0]) ||
   index!=0 || target!=0 || count[31:16]!=0 || count[15:14]>2 ||
   (count[2:0]<4 && (count[11:3]==0 || count[11:3]>32)) ||
   (count[2:0]>=4 && count[11:3]!=0) ||
   (flags[1] && count[2:0]!=5)));
 assign task_ready=!reset && state==IDLE && !complete_valid;
 assign s_take=state==SREPLY || state==SACK;
 assign rd_rsp_ready=state==RREPLY;
 assign rsp_ready=state==CREPLY;
 task finish;
  input [3:0] status;
  begin complete_valid<=1;complete_data<={32'b0,8'b0,status,4'd7,tag};state<=IDLE;end
 endtask
 always @(posedge clk)begin
  if(reset)begin
   state<=IDLE;operation<=0;tag<=0;remaining<=0;base<=0;save_result<=0;packed_result<=0;result_index<=0;response_hold<=0;
   complete_valid<=0;complete_data<=0;s_req<=0;s_wr<=0;s_addr<=0;s_din<=0;
   load_valid<=0;load_target<=0;load_index<=0;load_data<=0;rd_valid<=0;rd_bank<=0;rd_index<=0;
   cmd_valid<=0;cmd_op<=0;cmd_rows<=0;cmd_role<=0;cmd_clear<=0;cmd_mode<=0;
  end else begin
   if(complete_valid&&complete_ready)complete_valid<=0;
   case(state)
    IDLE:if(task_valid&&task_ready)begin
     tag<=task_data[31:16];operation<=requested_op[1:0];remaining<=count[6:0];base<=reference[13:4];
     load_target<=target[2:0];load_index<=index[9:0];rd_bank<=target[0];rd_index<=index[9:0];
     save_result<=flags[0];packed_result<=flags[1];result_index<=0;
     if(invalid)begin complete_valid<=1;complete_data<={32'b0,8'b0,4'd2,4'd7,task_data[31:16]};end
     else if(requested_op==0)state<=SREAD;
     else if(requested_op==1)state<=RREAD;
     else begin
      cmd_op<=count[2:0];cmd_rows<=count[11:3];cmd_role<=count[12];cmd_clear<=count[13];cmd_mode<=count[15:14];
      cmd_valid<=1;state<=COMMAND;
     end
    end
    SREAD:if(!s_req)begin s_req<=1;s_wr<=0;s_addr<=base;end
     else if(s_ready)begin s_req<=0;state<=SREPLY;end
    SREPLY:if(s_valid)begin load_data<=s_dout;load_valid<=1;state<=LOAD;end
    LOAD:if(load_valid&&load_ready)begin load_valid<=0;state<=NEXT;end
    RREAD:begin rd_valid<=1;state<=RREPLY;end
    RREPLY:begin
     if(rd_valid&&rd_ready)rd_valid<=0;
     if(rd_rsp_valid)begin s_din<=rd_data;state<=SWRITE;end
    end
    SWRITE:if(!s_req)begin s_req<=1;s_wr<=1;s_addr<=base;end
     else if(s_ready)begin s_req<=0;state<=SACK;end
    SACK:if(s_valid)state<=NEXT;
    NEXT:if(remaining==1)finish(0);
     else begin
      remaining<=remaining-1;base<=base+1;
      if(operation==0)begin load_index<=load_index+1;state<=SREAD;end
      else if(operation==1)begin rd_index<=rd_index+1;state<=RREAD;end
      else begin
       result_index<=result_index+1;
       if(packed_result) s_din<={response_hold[479:448],response_hold[415:384],response_hold[351:320],response_hold[287:256]};
       else s_din<=response_hold[(32'(result_index)+1)*128+:128];
       state<=SWRITE;
      end
     end
    COMMAND:if(cmd_valid&&cmd_ready)begin cmd_valid<=0;state<=CREPLY;end
    CREPLY:if(rsp_valid)begin
     if(rsp_error)finish(4);
     else if(!save_result)finish(0);
     else begin
      response_hold<=rsp_data;result_index<=0;remaining<=packed_result?7'd2:7'd4;
      s_din<=packed_result?{rsp_data[223:192],rsp_data[159:128],rsp_data[95:64],rsp_data[31:0]}:rsp_data[127:0];
      state<=SWRITE;
     end
    end
    default:finish(3);
   endcase
  end
 end
endmodule
