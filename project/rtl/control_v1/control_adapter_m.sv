// M task adapter: local scale+execute sequence, or real M-result -> S drain.
// A/B payload and local accumulation remain entirely in the accepted M macro.
module control_adapter_m(
 input wire clk,reset,input wire task_valid,output wire task_ready,input wire [255:0] task_data,
 output reg complete_valid,input wire complete_ready,output reg [63:0] complete_data,
 output reg cmd_valid,input wire cmd_ready,output reg [3:0] cmd_op,output reg [5:0] cmd_index,output reg [63:0] cmd_data,
 input wire rsp_valid,output wire rsp_ready,input wire [127:0] rsp_data,input wire rsp_error,rsp_saturated,
 output reg s_req,output wire s_wr,output reg [9:0] s_addr,output reg [127:0] s_din,
 input wire s_ready,s_valid,output wire s_take
);
 localparam IDLE=0,SCALE_SEND=1,SCALE_WAIT=2,COMMAND_SEND=3,COMMAND_WAIT=4,WRITE=5,WRITE_ACK=6,NEXT=7;
 reg [2:0] state;reg [7:0] operation;reg [15:0] tag;
 reg [63:0] gemm;reg [20:0] scale;reg bank;
 reg [3:0] rows_left;reg [2:0] row;reg [1:0] word_index;
 reg [9:0] destination;reg [9:0] read_format;
 reg saturated;reg [31:0] moved;
 wire drain=operation==1 || operation==2;
 wire raw=operation==1;
 wire [31:0] requested_rows=task_data[63:32],requested_start=task_data[95:64],requested_destination=task_data[191:160];
 wire [31:0] requested_bytes=requested_rows*(task_data[7:0]==1?32'd64:32'd32);
 wire invalid_header=task_data[15:8]!=8'h01 || task_data[7:0]>4;
 wire invalid_drain=requested_rows<1 || requested_rows>8 || requested_start>7 || requested_rows+requested_start>8 ||
  requested_destination[31:14]!=0 || requested_destination[3:0]!=0 || requested_destination+requested_bytes>16384 ||
  task_data[223:202]!=0 || task_data[255:224]!=0;
 assign task_ready=state==IDLE && !complete_valid;
 assign rsp_ready=state==SCALE_WAIT || state==COMMAND_WAIT;
 assign s_wr=1'b1;assign s_take=state==WRITE_ACK;
 task finish;
  input [3:0] status;input [31:0] result;
  begin complete_valid<=1;complete_data<={result,7'b0,(saturated || (rsp_valid && rsp_ready && rsp_saturated)),status,4'd1,tag};state<=IDLE;end
 endtask
 always @(posedge clk) begin
  if(reset) begin
   state<=IDLE;operation<=0;tag<=0;gemm<=0;scale<=0;bank<=0;rows_left<=0;row<=0;word_index<=0;destination<=0;read_format<=0;
   saturated<=0;moved<=0;complete_valid<=0;complete_data<=0;cmd_valid<=0;cmd_op<=0;cmd_index<=0;cmd_data<=0;s_req<=0;s_addr<=0;s_din<=0;
  end else begin
   if(complete_valid && complete_ready) complete_valid<=0;
   case(state)
    IDLE:if(task_valid && task_ready) begin
     operation<=task_data[7:0];tag<=task_data[31:16];gemm<=task_data[95:32];scale<=task_data[116:96];bank<=task_data[192];
     rows_left<=task_data[35:32];row<=task_data[66:64];word_index<=0;destination<=task_data[173:164];read_format<=task_data[201:192];
     saturated<=0;moved<=0;
     if(invalid_header || ((task_data[7:0]==1 || task_data[7:0]==2) && invalid_drain) ||
       (task_data[7:0]==0 && (task_data[191:117]!=0 || task_data[255:193]!=0))) begin
      complete_valid<=1;complete_data<={32'b0,8'b0,4'd2,4'd1,task_data[31:16]};
     end else state<=task_data[7:0]==0?SCALE_SEND:COMMAND_SEND;
    end
    SCALE_SEND:if(!cmd_valid) begin cmd_valid<=1;cmd_op<=4;cmd_index<=0;cmd_data<={43'b0,scale};end
     else if(cmd_ready) begin cmd_valid<=0;state<=SCALE_WAIT;end
    SCALE_WAIT:if(rsp_valid) begin if(rsp_error) finish(4,rsp_data[31:0]);else state<=COMMAND_SEND;end
    COMMAND_SEND:if(!cmd_valid) begin
     cmd_valid<=1;cmd_data<=0;cmd_index<=0;
     case(operation)
      0:begin cmd_op<=10;cmd_index<={bank,5'b0};cmd_data<=gemm;end
      1:begin cmd_op<=3;cmd_index<={row,1'b0,word_index};end
      2:begin cmd_op<=5;cmd_index<={row,2'b0,word_index[0]};cmd_data<={54'b0,read_format};end
      3:cmd_op<=6;
      4:begin cmd_op<=11;cmd_index<={5'b0,bank};end
      default:cmd_op<=15;
     endcase
    end else if(cmd_ready) begin cmd_valid<=0;state<=COMMAND_WAIT;end
    COMMAND_WAIT:if(rsp_valid) begin
     saturated<=saturated||rsp_saturated;
     if(rsp_error) finish(4,rsp_data[31:0]);
     else if(drain) begin s_din<=rsp_data;state<=WRITE;end
     else finish(0,rsp_data[31:0]);
    end
    WRITE:if(!s_req) begin s_req<=1;s_addr<=destination;end
     else if(s_ready) begin s_req<=0;state<=WRITE_ACK;end
    WRITE_ACK:if(s_valid) begin destination<=destination+1;moved<=moved+16;state<=NEXT;end
    NEXT:if(word_index==(raw?2'd3:2'd1)) begin
     if(rows_left==1) finish(0,moved);
     else begin rows_left<=rows_left-1;row<=row+1;word_index<=0;state<=COMMAND_SEND;end
    end else begin word_index<=word_index+1;state<=COMMAND_SEND;end
    default:finish(3,0);
   endcase
  end
 end
endmodule
