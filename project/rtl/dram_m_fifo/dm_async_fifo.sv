// Dual-clock, power-of-two FIFO. Payload memory is not reset.
// Async assertion, synchronous deassertion in each domain; reset is coordinated.
module dm_reset_sync(input wire clk,reset,output wire rst);
 (* ASYNC_REG="TRUE" *) reg [1:0] pipe;
 always @(posedge clk or posedge reset)
  if(reset) pipe<=2'b11; else pipe<={pipe[0],1'b0};
 assign rst=pipe[1];
endmodule

module dm_async_fifo #(parameter WIDTH=128,parameter DEPTH=16)(
 input wire reset,wclk,rclk,
 input wire wvalid,output wire wready,input wire [WIDTH-1:0] wdata,
 output wire rvalid,input wire rready,output wire [WIDTH-1:0] rdata
);
 localparam A=$clog2(DEPTH),P=A+1;
 initial begin
  if(DEPTH<2 || (DEPTH&(DEPTH-1))!=0) $fatal(1,"FIFO depth must be power of two >=2");
 end
 wire wrst,rrst;
 dm_reset_sync ws(wclk,reset,wrst),rs(rclk,reset,rrst);
 reg [WIDTH-1:0] payload[0:DEPTH-1];
 reg [P-1:0] wb,wg,rb,rg;
 (* ASYNC_REG="TRUE" *) reg [P-1:0] rg1,rg2,wg1,wg2;
 reg full,empty;
 wire [P-1:0] wn=wb+{{(P-1){1'b0}},(wvalid&&wready)};
 wire [P-1:0] rn=rb+{{(P-1){1'b0}},(rvalid&&rready)};
 wire [P-1:0] wgn=(wn>>1)^wn,rgn=(rn>>1)^rn;
 localparam [P-1:0] MASK=(P'(1)<<(P-1))|(P'(1)<<(P-2));
 assign wready=!wrst&&!full;
 assign rvalid=!rrst&&!empty;
 assign rdata=payload[rb[A-1:0]];
 always @(posedge wclk or posedge wrst) begin
  if(wrst) begin wb<=0;wg<=0;rg1<=0;rg2<=0;full<=0;end
  else begin
   rg1<=rg;rg2<=rg1;wb<=wn;wg<=wgn;full<=wgn==(rg2^MASK);
   if(wvalid&&wready)payload[wb[A-1:0]]<=wdata;
  end
 end
 always @(posedge rclk or posedge rrst) begin
  if(rrst)begin rb<=0;rg<=0;wg1<=0;wg2<=0;empty<=1;end
  else begin wg1<=wg;wg2<=wg1;rb<=rn;rg<=rgn;empty<=rgn==wg2;end
 end
endmodule
