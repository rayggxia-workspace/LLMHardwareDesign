// Independent-clock transport FIFO. Payload is stored; only Gray pointers
// cross through two-stage synchronizers. Physical CDC constraints are required
// before hardware use; RTL simulation does not establish metastability MTBF.
module hbm_async_fifo #(parameter integer WIDTH=155, LGDEPTH=4)(
 input wire wclk,rclk,reset,
 input wire wvalid,output wire wready,input wire [WIDTH-1:0] wdata,
 output wire rvalid,input wire rready,output wire [WIDTH-1:0] rdata
);
 localparam integer PTR=LGDEPTH+1;
 reg [WIDTH-1:0] mem[0:(1<<LGDEPTH)-1];
 reg [PTR-1:0] wp,rp,wgray,rgray;
 (* async_reg="true" *) reg [PTR-1:0] r_sync1,r_sync2,w_sync1,w_sync2;
 reg full,empty;
 wire [PTR-1:0] wn=wp+{{(PTR-1){1'b0}},(wvalid&&wready)};
 wire [PTR-1:0] rn=rp+{{(PTR-1){1'b0}},(rvalid&&rready)};
 wire [PTR-1:0] wg=(wn>>1)^wn,rg=(rn>>1)^rn;
 assign wready=!reset&&!full;
 assign rvalid=!reset&&!empty;
 assign rdata=mem[rp[LGDEPTH-1:0]];
 always @(posedge wclk)begin
  if(reset)begin wp<=0;wgray<=0;r_sync1<=0;r_sync2<=0;full<=0;end
  else begin
   r_sync1<=rgray;r_sync2<=r_sync1;wp<=wn;wgray<=wg;
   full<=wg=={~r_sync2[PTR-1:PTR-2],r_sync2[PTR-3:0]};
   if(wvalid&&wready)mem[wp[LGDEPTH-1:0]]<=wdata;
  end
 end
 always @(posedge rclk)begin
  if(reset)begin rp<=0;rgray<=0;w_sync1<=0;w_sync2<=0;empty<=1;end
  else begin
   w_sync1<=wgray;w_sync2<=w_sync1;rp<=rn;rgray<=rg;empty<=rg==w_sync2;
  end
 end
endmodule
