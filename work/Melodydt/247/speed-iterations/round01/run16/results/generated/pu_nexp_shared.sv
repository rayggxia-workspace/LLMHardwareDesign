// Issue247 round1. One unchanged native N is shared with ordinary commands.
// op15 is an explicit destructive/clobber ABI. It starts a fresh N context;
// normal multi-command statistics must not be resumed without a new op0.
// No second N, EXP table, reduction lane or private S is instantiated here.
module pu_nexp_shared (
 input wire clk,reset,
 input wire exec_valid,output wire exec_ready,input wire [63:0] exec_meta,
 input wire [127:0] exec_a,exec_b,
 output wire result_valid,input wire result_ready,output wire [127:0] result_data,
 output wire result_error,result_saturated,
 output wire n_valid,input wire n_ready,output wire [63:0] n_meta,
 output wire [127:0] n_a,n_b,
 input wire n_result_valid,output wire n_result_ready,input wire [127:0] n_result,
 input wire n_error,n_saturated
);
 localparam [31:0] PACKED16=32'h4e455850,CONTAINER32=32'h4e583332;
 localparam [1:0] IDLE=0,SEND=1,WAIT_RESULT=2,ERROR=3;
 reg [1:0] phase;
 reg container32;
 reg [3:0] count;
 reg [127:0] packed_data;
 wire selected=exec_meta[3:0]==4'd15;
 wire mode32=exec_meta[39:8]==CONTAINER32;
 wire legal_tag=mode32||exec_meta[39:8]==PACKED16;
 reg payload_ok;reg [127:0] packed_input;
 always @* begin
  packed_input=0;payload_ok=exec_meta[63:40]==0&&legal_tag&&exec_meta[7:4]>0&&
   exec_meta[7:4]<=(mode32?4:8)&&exec_b==0;
  if(mode32)begin
   for(integer i=0;i<4;i=i+1)begin
    // Used high16 bits are deliberately ignored by the declared legacy
    // S32-container -> signed-low16 mapping. This is not saturating convert.
    if(i<exec_meta[7:4])packed_input[16*i+:16]=exec_a[32*i+:16];
    else if(exec_a[32*i+:32]!=0)payload_ok=0;
   end
  end else begin
   for(integer i=0;i<8;i=i+1)begin
    if(i<exec_meta[7:4])packed_input[16*i+:16]=exec_a[16*i+:16];
    else if(exec_a[16*i+:16]!=0)payload_ok=0;
   end
  end
 end
 wire batch_ready,batch_valid,batch_error;
 wire [127:0] batch_data,b_cmd_data;
 wire b_cmd_valid,b_rsp_ready;wire [3:0] b_cmd_op,b_cmd_count;
 reg [127:0] mapped_result;
 always @* begin
  mapped_result=batch_data;
  if(container32)begin
   mapped_result=0;
   for(integer i=0;i<4;i=i+1)
    if(i<count)mapped_result[32*i+:32]={16'd0,batch_data[16*i+:16]};
  end
 end
 nexp_batch_adapter batch(
  .clk,.reset,.in_valid(phase==SEND),.in_ready(batch_ready),.in_count(count),.in_data(packed_data),
  .out_valid(batch_valid),.out_ready(phase==WAIT_RESULT&&result_ready),.out_data(batch_data),.out_error(batch_error),
  .n_cmd_valid(b_cmd_valid),.n_ready,.n_cmd_op(b_cmd_op),.n_cmd_count(b_cmd_count),.n_cmd_data(b_cmd_data),
  .n_valid(n_result_valid),.n_rsp_ready(b_rsp_ready),.n_data(n_result),.n_error
 );
 // Ordinary command paths remain combinationally identical when no batch owns
 // the route. Selection during a batch uses only captured state, never live
 // external metadata. Its final response must be consumed before release.
 assign exec_ready=!reset&&phase==IDLE&&(selected?(n_ready&&!n_result_valid):n_ready);
 assign n_valid=!reset&&(phase!=IDLE?b_cmd_valid:(exec_valid&&!selected));
 assign n_meta=phase!=IDLE?{24'd0,32'd0,b_cmd_count,b_cmd_op}:exec_meta;
 assign n_a=phase!=IDLE?b_cmd_data:exec_a;
 assign n_b=phase!=IDLE?128'd0:exec_b;
 assign n_result_ready=!reset&&(phase!=IDLE?b_rsp_ready:result_ready);
 assign result_valid=!reset&&(phase==ERROR||(phase==WAIT_RESULT?batch_valid:(phase==IDLE?n_result_valid:1'b0)));
 assign result_data=phase==ERROR?128'd0:(phase==WAIT_RESULT?mapped_result:n_result);
 assign result_error=phase==ERROR?1'b1:(phase==WAIT_RESULT?batch_error:n_error);
 assign result_saturated=phase==IDLE?n_saturated:1'b0;
 always @(posedge clk)begin
  if(reset)begin phase<=IDLE;container32<=0;count<=0;packed_data<=0;end
  else begin
   case(phase)
    IDLE:if(exec_valid&&exec_ready&&selected)begin
     container32<=mode32;count<=exec_meta[7:4];packed_data<=packed_input;
     phase<=payload_ok?SEND:ERROR;
    end
    SEND:if(batch_ready)phase<=WAIT_RESULT;
    WAIT_RESULT:if(batch_valid&&result_ready)phase<=IDLE;
    ERROR:if(result_ready)phase<=IDLE;
    default:phase<=IDLE;
   endcase
  end
 end
endmodule
