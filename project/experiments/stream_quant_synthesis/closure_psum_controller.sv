// One finite transaction slot. The timed candidate declares a finite
// number of slots per P. SRAM interface is a 128-byte transaction, not a physical port.
module closure_psum_controller(
 input wire clk,reset,
 input wire cmd_valid,output wire cmd_ready,input wire [13:0] cmd_address,
 input wire [15:0] cmd_generation,input wire cmd_first,
 input wire [3:0] cmd_count,input wire [87:0] cmd_mantissa,input wire [55:0] cmd_shift,
 input wire part_valid,output wire part_ready,input wire [15:0] part_generation,input wire [319:0] part_data,
 output wire rd_valid,input wire rd_ready,output wire [13:0] rd_address,output wire [15:0] rd_generation,
 input wire rd_rsp_valid,output wire rd_rsp_ready,input wire [15:0] rd_rsp_generation,input wire [1023:0] rd_rsp_data,
 output wire wr_valid,input wire wr_ready,output wire [13:0] wr_address,output wire [15:0] wr_generation,output wire [1023:0] wr_data,
 input wire wr_ack_valid,output wire wr_ack_ready,input wire [15:0] wr_ack_generation,
 output reg done_valid,input wire done_ready,output reg done_error,output reg [15:0] done_generation,output reg fault
);
 localparam IDLE=0,READ=1,WAIT_INPUT=2,ISSUE=3,RESULT=4,WRITE=5,ACK=6,RESPOND=7;
 reg [3:0] phase;
 reg [13:0] address;reg [15:0] generation;
 reg [3:0] count;reg [87:0] mantissa;reg [55:0] shift;
 reg [319:0] partial;
 reg [1023:0] previous,result;
 reg have_previous,have_partial;
 wire alu_ready,alu_valid,alu_error;wire [1023:0] alu_data;
 closure_partial128 alu(clk,reset,phase==ISSUE,alu_ready,count,partial,mantissa,shift,previous,
                         alu_valid,phase==RESULT,alu_data,alu_error);
 assign cmd_ready=!reset&&!fault&&phase==IDLE&&(!done_valid||done_ready);
 assign part_ready=!reset&&!fault&&!have_partial&&phase!=IDLE&&phase!=RESPOND;
 assign rd_valid=!reset&&!fault&&phase==READ;
 assign rd_address=address;assign rd_generation=generation;
 assign rd_rsp_ready=!reset&&!fault&&phase==WAIT_INPUT&&!have_previous;
 assign wr_valid=!reset&&!fault&&phase==WRITE;
 assign wr_address=address;assign wr_generation=generation;assign wr_data=result;
 assign wr_ack_ready=!reset&&!fault&&phase==ACK;
 always @(posedge clk)begin
  if(reset)begin
   phase<=IDLE;done_valid<=0;done_error<=0;done_generation<=0;fault<=0;
   address<=0;generation<=0;count<=0;mantissa<=0;shift<=0;partial<=0;previous<=0;result<=0;
   have_previous<=0;have_partial<=0;
  end else begin
   if(done_valid&&done_ready)begin done_valid<=0;if(phase==RESPOND&&!fault)phase<=IDLE;end
   if(part_valid&&part_ready)begin
    if(part_generation!=generation)begin fault<=1;done_valid<=1;done_error<=1;phase<=RESPOND;end
    else begin partial<=part_data;have_partial<=1;end
   end
   if(cmd_valid&&cmd_ready)begin
    address<=cmd_address;generation<=cmd_generation;done_generation<=cmd_generation;
    count<=cmd_count;mantissa<=cmd_mantissa;shift<=cmd_shift;have_partial<=0;have_previous<=cmd_first;
    previous<=0;done_error<=0;
    if(cmd_address[6:0]!=0||cmd_count==0||cmd_count>8)begin fault<=1;done_valid<=1;done_error<=1;phase<=RESPOND;end
    else phase<=cmd_first?WAIT_INPUT:READ;
   end
   if(rd_valid&&rd_ready)phase<=WAIT_INPUT;
   if(rd_rsp_valid&&rd_rsp_ready)begin
    if(rd_rsp_generation!=generation)begin fault<=1;done_valid<=1;done_error<=1;phase<=RESPOND;end
    else begin previous<=rd_rsp_data;have_previous<=1;end
   end
   if(phase==WAIT_INPUT&&have_previous&&have_partial&&!fault)phase<=ISSUE;
   if(phase==ISSUE&&alu_ready)phase<=RESULT;
   if(phase==RESULT&&alu_valid)begin
    if(alu_error)begin fault<=1;done_valid<=1;done_error<=1;phase<=RESPOND;end
    else begin result<=alu_data;phase<=WRITE;end
   end
   if(wr_valid&&wr_ready)phase<=ACK;
   if(wr_ack_valid&&wr_ack_ready)begin
    done_valid<=1;phase<=RESPOND;done_error<=wr_ack_generation!=generation;
    if(wr_ack_generation!=generation)fault<=1;
   end
  end
 end
endmodule
