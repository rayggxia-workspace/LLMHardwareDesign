// Explicit NEW E-side arithmetic extension, not a capability of frozen E.
// No state memory; eight exact S32 x S16/S32/U32 products, registered latency 2.
module c_wide_native(input wire clk,reset,in_valid,output wire in_ready,
 input wire [255:0] in_a,in_b,input wire [1:0] in_kind,
 output reg out_valid,input wire out_ready,output reg [511:0] out_data,
 output wire out_error,output wire [31:0] command_count);
 reg [1:0] phase;
 reg [255:0] aa,bb;
 reg [1:0] kind;
 reg signed [64:0] products[0:7];
 assign in_ready=!reset&&phase==0&&(!out_valid||out_ready);
 assign out_error=0;
 assign command_count=1;
 integer j;
 reg signed [32:0] operand_b;
 always @(posedge clk)begin
  if(reset)begin phase<=0;out_valid<=0;out_data<=0;aa<=0;bb<=0;kind<=0;for(j=0;j<8;j=j+1)products[j]<=0;end
  else begin
   if(out_valid&&out_ready)out_valid<=0;
   if(in_valid&&in_ready)begin aa<=in_a;bb<=in_b;kind<=in_kind;phase<=1;end
   if(phase==1)begin
    for(j=0;j<8;j=j+1)begin
     if(kind==0)operand_b={{17{bb[32*j+15]}},bb[32*j+:16]};
     else if(kind==1)operand_b={bb[32*j+31],bb[32*j+:32]};
     else operand_b={1'b0,bb[32*j+:32]};
     products[j]<=$signed(aa[32*j+:32])*operand_b;
    end
    phase<=2;
   end
   if(phase==2)begin for(j=0;j<8;j=j+1)out_data[64*j+:64]<=products[j][63:0];out_valid<=1;phase<=0;end
  end
 end
endmodule
