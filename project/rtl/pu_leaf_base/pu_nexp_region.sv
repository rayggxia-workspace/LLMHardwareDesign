// Staged, contiguous NExp region -> actual U descriptors. Caller supplies
// signed Q5.10 values; S32 mode uses the existing low16-in-S32 ABI. No DMA.
// Input/output ranges must not overlap. Completion follows every U write ACK.
// NX32 caller must zero unused containers in its final input word.
module pu_nexp_region(
 input wire clk,reset,start_valid,output wire start_ready,
 input wire input_s16,input_q5_10,input wire [11:0] elements,
 input wire [9:0] input_base,output_base,
 output wire done_valid,input wire done_ready,output reg done_error,
 output reg [11:0] completed_values,completed_commands,
 output wire n_cmd_valid,input wire n_cmd_ready,output wire [39:0] n_cmd_meta,
 output wire [19:0] n_cmd_src,output wire [9:0] n_cmd_dst,
 input wire n_done_valid,output wire n_done_ready,input wire n_done_error
);
 localparam [1:0] IDLE=0,ISSUE=1,WAIT=2,DONE=3;
 reg [1:0] state;reg format16;reg [11:0] remaining;
 reg [9:0] src,dst;
 wire [3:0] lanes=format16?4'd8:4'd4;
 wire [3:0] count=remaining>{8'd0,lanes}?lanes:remaining[3:0];
 wire [12:0] input_words=input_s16?({1'b0,elements}+13'd7)>>3:({1'b0,elements}+13'd3)>>2;
 wire [12:0] output_words=({1'b0,elements}+13'd3)>>2;
 wire [13:0] input_end={4'd0,input_base}+{1'b0,input_words};
 wire [13:0] output_end={4'd0,output_base}+{1'b0,output_words};
 wire bad=!input_q5_10 || elements==0 || elements>2048 || input_end>1024 || output_end>1024 ||
          ({4'd0,input_base}<output_end && {4'd0,output_base}<input_end);
 assign start_ready=!reset && state==IDLE;
 assign done_valid=!reset && state==DONE;
 assign n_cmd_valid=!reset && state==ISSUE;
 assign n_cmd_meta={format16?32'h4e583136:32'h4e583332,count,4'd15};
 assign n_cmd_src={10'd0,src};assign n_cmd_dst=dst;
 assign n_done_ready=!reset && state==WAIT;
 always @(posedge clk)begin
  if(reset)begin state<=IDLE;done_error<=0;completed_values<=0;completed_commands<=0;remaining<=0;format16<=0;src<=0;dst<=0;end
  else case(state)
   IDLE:if(start_valid)begin
    format16<=input_s16;remaining<=elements;src<=input_base;dst<=output_base;
    completed_values<=0;completed_commands<=0;done_error<=bad;state<=bad?DONE:ISSUE;
   end
   ISSUE:if(n_cmd_ready)state<=WAIT;
   WAIT:if(n_done_valid)begin
    if(n_done_error)begin done_error<=1;state<=DONE;end
    else begin
     completed_commands<=completed_commands+1'b1;completed_values<=completed_values+{8'd0,count};
     if(remaining<={8'd0,lanes})begin remaining<=0;state<=DONE;end
     else begin remaining<=remaining-{8'd0,lanes};src<=src+1'b1;dst<=dst+(format16?10'd2:10'd1);state<=ISSUE;end
    end
   end
   DONE:if(done_ready)state<=IDLE;
   default:state<=IDLE;
  endcase
 end
endmodule
