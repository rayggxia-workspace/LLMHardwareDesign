// Candidate coefficient accumulator, separate from the existing M leaf.
// Sixteen tagged contexts x eight S128 values = 2048 active register bytes.
// One ALU transaction at a time; response acceptance retires ownership.
module closure_context16(
 input wire clk,reset,in_valid,output wire in_ready,
 input wire [3:0] in_context,input wire in_first,in_last,
 input wire [15:0] in_generation,input wire [319:0] in_partial,
 input wire [87:0] in_mantissa,input wire [55:0] in_shift,
 output reg out_valid,input wire out_ready,output reg out_error,
 output reg [3:0] out_context,output reg [15:0] out_generation,
 output reg [1023:0] out_data,output reg fault
);
 reg [1023:0] values[0:15];reg [15:0] generations[0:15];reg [15:0] live;
 reg busy,last;reg [3:0] context_id;reg [15:0] generation;
 wire alu_ready,alu_valid,alu_error;wire [1023:0] alu_data;
 wire identity_ok=in_first?!live[in_context]:(live[in_context]&&generations[in_context]==in_generation);
 assign in_ready=!reset&&!fault&&!busy&&!out_valid&&alu_ready;
 closure_partial128 alu(clk,reset,in_valid&&in_ready&&identity_ok,alu_ready,4'd8,
                       in_partial,in_mantissa,in_shift,in_first?1024'd0:values[in_context],
                       alu_valid,busy&&!out_valid,alu_data,alu_error);
 always @(posedge clk)begin
  if(reset)begin
   live<=0;busy<=0;last<=0;context_id<=0;generation<=0;
   out_valid<=0;out_error<=0;out_context<=0;out_generation<=0;out_data<=0;fault<=0;
   for(integer i=0;i<16;i=i+1)begin values[i]<=0;generations[i]<=0;end
  end else begin
   if(in_valid&&in_ready)begin
    context_id<=in_context;generation<=in_generation;last<=in_last;
    if(!identity_ok)begin
     out_valid<=1;out_error<=1;out_context<=in_context;out_generation<=in_generation;fault<=1;
    end else begin busy<=1;end
   end
   if(busy&&alu_valid&&!out_valid)begin
    out_valid<=1;out_error<=alu_error;out_context<=context_id;out_generation<=generation;out_data<=alu_data;
    if(alu_error)fault<=1;
   end
   if(out_valid&&out_ready)begin
    out_valid<=0;busy<=0;
    if(!out_error)begin values[context_id]<=out_data;generations[context_id]<=generation;live[context_id]<=!last;end
   end
  end
 end
endmodule
