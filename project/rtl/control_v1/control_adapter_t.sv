// T lifecycle and bounded S<->T transport. No second 6KiB buffer is added.
module control_adapter_t(
 input wire clk,reset,input wire task_valid,output wire task_ready,input wire [255:0] task_data,
 output reg complete_valid,input wire complete_ready,output reg [63:0] complete_data,
 output reg begin_valid,input wire begin_ready,output reg [1:0] begin_owner,output reg [31:0] begin_generation,output reg [9:0] begin_words,
 output reg write_valid,input wire write_ready,output reg [9:0] write_index,output reg [127:0] write_data,
 output reg commit_valid,input wire commit_ready,output reg revoke_valid,input wire revoke_ready,
 input wire read_valid,output wire read_take,input wire [9:0] read_index,input wire [127:0] read_data,input wire read_last,
 output reg release_valid,input wire release_ready,input wire t_busy,t_sealed,t_committed,t_error,
 output reg s_req,output reg s_wr,output reg [9:0] s_addr,output reg [127:0] s_din,
 input wire s_ready,s_valid,output wire s_take,input wire [127:0] s_dout
);
 localparam IDLE=0,CONTROL=1,FILL_READ=2,FILL_REPLY=3,FILL_WRITE=4,DRAIN=5,DRAIN_WRITE=6,DRAIN_REPLY=7,NEXT=8;
 reg [3:0] state;reg [7:0] operation;reg [15:0] tag;
 reg [9:0] cursor,size,remaining,base;reg session;
 wire [31:0] words=task_data[63:32],reference=task_data[95:64];
 wire transfer=task_data[7:0]==1 || task_data[7:0]==3;
 wire invalid=task_data[15:8]!=8'h06 || task_data[7:0]>5 || task_data[191:96]!=0 ||
  task_data[223:194]!=0 || (transfer && (words==0 || words>384 || reference[31:14]!=0 || reference[3:0]!=0 || reference+(words<<4)>16384)) ||
  (task_data[7:0]==0 && (words==0 || words>384 || t_busy)) ||
  (task_data[7:0]==1 && (!session || t_sealed || t_committed || {22'b0,cursor}+words>{22'b0,size})) ||
  (task_data[7:0]==2 && !t_sealed) || (task_data[7:0]==3 && !t_committed) ||
  (task_data[7:0]==4 && (!session || !release_ready)) || (task_data[7:0]==5 && (!session || t_committed));
 assign task_ready=state==IDLE && !complete_valid;
 assign s_take=state==FILL_REPLY || state==DRAIN_REPLY;
 assign read_take=state==DRAIN_REPLY && s_valid;
 task finish;
  input [3:0] status;
  begin complete_valid<=1;complete_data<={22'b0,size,8'b0,status,4'd6,tag};state<=IDLE;end
 endtask
 always @(posedge clk) begin
  if(reset) begin
   state<=IDLE;operation<=0;tag<=0;cursor<=0;size<=0;remaining<=0;base<=0;session<=0;
   complete_valid<=0;complete_data<=0;begin_valid<=0;begin_owner<=0;begin_generation<=0;begin_words<=0;
   write_valid<=0;write_index<=0;write_data<=0;commit_valid<=0;revoke_valid<=0;release_valid<=0;
   s_req<=0;s_wr<=0;s_addr<=0;s_din<=0;
  end else begin
   if(complete_valid && complete_ready) complete_valid<=0;
   case(state)
    IDLE:if(task_valid && task_ready) begin
     operation<=task_data[7:0];tag<=task_data[31:16];remaining<=task_data[41:32];base<=task_data[77:68];
     if(invalid || t_error) begin complete_valid<=1;complete_data<={32'b0,8'b0,4'd2,4'd6,task_data[31:16]};end
     else case(task_data[7:0])
      0:begin begin_valid<=1;begin_owner<=task_data[193:192];begin_generation<=task_data[255:224];begin_words<=task_data[41:32];size<=task_data[41:32];state<=CONTROL;end
      1:state<=FILL_READ;
      2:begin commit_valid<=1;state<=CONTROL;end
      3:state<=DRAIN;
      4:begin release_valid<=1;state<=CONTROL;end
      5:begin revoke_valid<=1;state<=CONTROL;end
      default:finish(2);
     endcase
    end
    CONTROL:if(begin_valid && begin_ready) begin begin_valid<=0;session<=1;cursor<=0;finish(0);end
     else if(commit_valid && commit_ready) begin commit_valid<=0;finish(0);end
     else if(release_valid && release_ready) begin release_valid<=0;session<=0;finish(0);end
     else if(revoke_valid && revoke_ready) begin revoke_valid<=0;session<=0;finish(0);end
    FILL_READ:if(!s_req) begin s_req<=1;s_wr<=0;s_addr<=base;end
     else if(s_ready) begin s_req<=0;state<=FILL_REPLY;end
    FILL_REPLY:if(s_valid) begin write_data<=s_dout;write_index<=cursor;write_valid<=1;state<=FILL_WRITE;end
    FILL_WRITE:if(write_valid && write_ready) begin write_valid<=0;cursor<=cursor+1;state<=NEXT;end
    DRAIN:if(read_valid) begin s_din<=read_data;s_addr<=base;s_wr<=1;s_req<=1;state<=DRAIN_WRITE;end
    DRAIN_WRITE:if(s_req && s_ready) begin s_req<=0;state<=DRAIN_REPLY;end
    DRAIN_REPLY:if(s_valid) begin
     if(read_last && remaining!=1) finish(4);
     else state<=NEXT;
    end
    NEXT:if(remaining==1) finish(0);
     else begin remaining<=remaining-1;base<=base+1;state<=operation==1?FILL_READ:DRAIN;end
    default:finish(3);
   endcase
  end
 end
 wire unused_read_index=&{1'b0,read_index};
endmodule
