// Control the existing finite S->M feeder. Real A/B valid/ready stays directly
// between S and M; completion means the feeder's native done, not an S pre-read.
module control_adapter_s(
 input wire clk,reset,input wire task_valid,output wire task_ready,input wire [255:0] task_data,
 output reg complete_valid,input wire complete_ready,output reg [63:0] complete_data,
 output reg load_valid,input wire load_ready,output reg load_bank,
 output reg [3:0] load_rows,output reg [2:0] load_tiles,
 output reg load_a_wide,load_b_wide,load_reuse_b,output reg [9:0] load_a_base,load_b_base,
 input wire done_valid,output wire done_take,input wire done_error
);
 reg active,waiting;reg [15:0] tag;
 wire invalid=task_data[15:0]!=16'h0500 || task_data[255:193]!=0 || task_data[191:128]!=0 ||
  task_data[63:42]!=0 || task_data[95:78]!=0 || task_data[67:64]!=0 ||
  task_data[127:110]!=0 || task_data[99:96]!=0 || task_data[35:32]==0 || task_data[35:32]>8 ||
  task_data[38:36]==0 || task_data[38:36]>4;
 assign task_ready=!active && !complete_valid;
 assign done_take=active && waiting;
 always @(posedge clk) begin
  if(reset) begin
   active<=0;waiting<=0;tag<=0;complete_valid<=0;complete_data<=0;load_valid<=0;load_bank<=0;
   load_rows<=0;load_tiles<=0;load_a_wide<=0;load_b_wide<=0;load_reuse_b<=0;load_a_base<=0;load_b_base<=0;
  end else begin
   if(complete_valid && complete_ready) complete_valid<=0;
   if(task_valid && task_ready) begin
    tag<=task_data[31:16];load_bank<=task_data[192];load_rows<=task_data[35:32];load_tiles<=task_data[38:36];
    load_a_wide<=task_data[39];load_b_wide<=task_data[40];load_reuse_b<=task_data[41];
    load_a_base<=task_data[77:68];load_b_base<=task_data[109:100];
    if(invalid) begin complete_valid<=1;complete_data<={32'b0,8'b0,4'd2,4'd5,task_data[31:16]};end
    else begin active<=1;waiting<=0;load_valid<=1;end
   end
   if(load_valid && load_ready) begin load_valid<=0;waiting<=1;end
   if(done_valid && done_take) begin
    active<=0;waiting<=0;complete_valid<=1;complete_data<={32'b0,8'b0,done_error?4'd4:4'd0,4'd5,tag};
   end
  end
 end
endmodule
