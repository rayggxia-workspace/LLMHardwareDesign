// Two complete commands and two complete completions per endpoint. There is
// one additional packet assembly register, explicit in the storage budget.
module control_endpoint_queue(
 input wire clk,reset,
 input wire cmd_valid,output wire cmd_ready,input wire [31:0] cmd_data,input wire cmd_last,
 output wire task_valid,input wire task_ready,output wire [255:0] task_data,
 input wire complete_valid,output wire complete_ready,input wire [63:0] complete_data,
 output wire done_valid,input wire done_ready,output wire [31:0] done_data,output wire done_last,
 output reg protocol_error
);
 reg [255:0] assembly;reg [2:0] word;
 reg [255:0] tasks[0:1];reg tw,tr;reg [1:0] tc;
 reg [63:0] completions[0:1];reg dw,dr;reg [1:0] dc;reg half;
 assign cmd_ready=(tc<2);
 assign task_valid=(tc!=0);assign task_data=tasks[tr];
 assign complete_ready=(dc<2);
 assign done_valid=(dc!=0);assign done_data=half?completions[dr][63:32]:completions[dr][31:0];
 assign done_last=half;
 wire cmd_take=cmd_valid&&cmd_ready;
 wire task_take=task_valid&&task_ready;
 wire done_take=done_valid&&done_ready;
 wire completion_take=complete_valid&&complete_ready;
 wire push_task=cmd_take && word==7 && cmd_last;
 wire pop_completion=done_take && half;
 always @(posedge clk) begin
  if(reset) begin word<=0;assembly<=0;tw<=0;tr<=0;tc<=0;dw<=0;dr<=0;dc<=0;half<=0;protocol_error<=0;end
  else begin
   if(cmd_take) begin
    if(cmd_last!=(word==7)) begin protocol_error<=1;word<=0;end
    else if(word==7) begin tasks[tw]<={cmd_data,assembly[223:0]};tw<=~tw;word<=0;end
    else begin assembly[word*32+:32]<=cmd_data;word<=word+1;end
   end
   if(task_take) tr<=~tr;
   case({push_task,task_take}) 2'b10:tc<=tc+1;2'b01:tc<=tc-1;default:begin end endcase
   if(completion_take) begin completions[dw]<=complete_data;dw<=~dw;end
   if(done_take) begin half<=~half;if(half) dr<=~dr;end
   case({completion_take,pop_completion}) 2'b10:dc<=dc+1;2'b01:dc<=dc-1;default:begin end endcase
  end
 end
endmodule
