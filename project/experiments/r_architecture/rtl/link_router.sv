// Four-source/four-destination 128-bit shared link, one flit in flight.
module link_router(input wire clk,reset,input wire [3:0] in_valid,output reg [3:0] in_ready,input wire [511:0] in_data,input wire [7:0] in_route,output reg [3:0] out_valid,input wire [3:0] out_ready,output wire [511:0] out_data);
 reg valid;reg [127:0] payload;reg [1:0] route,rr;reg chosen;reg [1:0] grant;integer k;
 wire space=!valid||out_ready[route];
 always @*begin
  in_ready=0;out_valid=0;chosen=0;grant=rr;
  if(!reset)begin
   if(valid)out_valid[route]=1;
   for(k=0;k<4;k=k+1)if(!chosen&&in_valid[(rr+k)%4])begin grant=(rr+k)%4;chosen=1;end
   if(chosen&&space)in_ready[grant]=1;
  end
 end
 for(genvar j=0;j<4;j=j+1)assign out_data[128*j+:128]=payload;
 always @(posedge clk)begin
  if(reset)begin valid<=0;payload<=0;route<=0;rr<=0;end
  else if(chosen&&space)begin valid<=1;payload<=in_data[128*grant+:128];route<=in_route[2*grant+:2];rr<=grant+1'b1;end
  else if(valid&&out_ready[route])valid<=0;
 end
endmodule
