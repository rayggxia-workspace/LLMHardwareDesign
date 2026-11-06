// Read-only controller USER interface -> async FIFOs -> unchanged M loader.
// Not a DDR controller/PHY or AXI bridge. One accepted external read at a time.
// Each request reads 16 aligned bytes; response is >=1 mem_clk later.
// Caller coordinates reset with external outstanding transactions.
module dram_m_fifo_loader #(parameter FIFO_DEPTH=16)(
 input wire core_clk,mem_clk,reset,
 input wire load_valid,output wire load_ready,input wire load_bank,
 input wire [39:0] load_a_base,load_b_base,
 input wire [3:0] load_rows,input wire [2:0] load_tiles,
 input wire load_a_wide,load_b_wide,
 output reg done_valid,input wire done_ready,output reg done_error,
 output wire mem_req_valid,input wire mem_req_ready,output wire [39:0] mem_req_address,
 input wire mem_rsp_valid,output wire mem_rsp_ready,input wire [127:0] mem_rsp_data,
 input wire mem_rsp_error,
 output reg a_valid,input wire a_ready,output reg a_bank,
 output reg [2:0] a_row,output reg [1:0] a_tile,output reg a_wide,
 output reg [127:0] a_data,
 output reg b_valid,input wire b_ready,output reg b_bank,
 output reg [1:0] b_tile,output reg b_wide,b_half,output reg [511:0] b_data,
 output wire request_fifo_full,response_fifo_full,output wire loading
);
 wire crst,mrst;
 dm_reset_sync cs(core_clk,reset,crst),ms(mem_clk,reset,mrst);
 reg active,issued_done,phase_b,bank,wa,wb,fault;
 reg [39:0] abase,bbase;
 reg [3:0] rows;
 reg [2:0] tiles,grow;
 reg [1:0] gtile;
 reg [2:0] gword;
 reg [6:0] expected,received;
 reg [511:0] gather;
 wire [40:0] a_end={1'b0,load_a_base}+41'(load_rows)*41'(load_tiles)*41'd16;
 wire [40:0] b_end={1'b0,load_b_base}+41'(load_tiles)*(load_b_wide?41'd128:41'd64);
 wire bad=load_rows==0||load_rows>8||load_tiles==0||load_tiles>4||
  load_a_base[3:0]!=0||load_b_base[3:0]!=0||a_end[40]||b_end[40];
 assign load_ready=!crst&&!active&&!done_valid;
 assign loading=active;
 wire qwvalid=active&&!issued_done,qwready,qrvalid,qrready;
 wire [8:0] tag={phase_b,grow,gtile,(phase_b&&gword[2]),(phase_b?gword[1:0]:2'b0)};
 wire [39:0] next_address=phase_b?
  bbase+(40'(gtile)<<(wb?7:6))+(40'(gword)<<4):
  abase+((40'(grow)*40'(tiles)+40'(gtile))<<4);
 wire [48:0] qrdata;
 dm_async_fifo #(.WIDTH(49),.DEPTH(FIFO_DEPTH)) requests(
  .reset(reset),.wclk(core_clk),.rclk(mem_clk),
  .wvalid(qwvalid),.wready(qwready),.wdata({tag,next_address}),
  .rvalid(qrvalid),.rready(qrready),.rdata(qrdata));
 wire swready,srvalid,srready;
 wire [137:0] srdata;
 reg outstanding;
 reg [8:0] return_tag;
 assign mem_req_valid=!mrst&&!outstanding&&qrvalid&&swready;
 assign mem_req_address=qrdata[39:0];
 assign qrready=mem_req_valid&&mem_req_ready;
 assign mem_rsp_ready=!mrst&&outstanding&&swready;
 dm_async_fifo #(.WIDTH(138),.DEPTH(FIFO_DEPTH)) responses(
  .reset(reset),.wclk(mem_clk),.rclk(core_clk),
  .wvalid(mem_rsp_valid&&outstanding&&!mrst),.wready(swready),
  .wdata({return_tag,mem_rsp_error,mem_rsp_data}),
  .rvalid(srvalid),.rready(srready),.rdata(srdata));
 assign request_fifo_full=!qwready&&!crst;
 assign response_fifo_full=!swready&&!mrst;
 assign srready=active&&!a_valid&&!b_valid;
 always @(posedge mem_clk or posedge mrst)begin
  if(mrst)begin outstanding<=0;return_tag<=0;end
  else begin
   if(mem_req_valid&&mem_req_ready)begin outstanding<=1;return_tag<=qrdata[48:40];end
   if(mem_rsp_valid&&mem_rsp_ready)outstanding<=0;
  end
 end
 always @(posedge core_clk or posedge crst)begin
  if(crst)begin
   active<=0;issued_done<=0;phase_b<=1;bank<=0;wa<=0;wb<=0;fault<=0;
   abase<=0;bbase<=0;rows<=0;tiles<=0;grow<=0;gtile<=0;gword<=0;
   expected<=0;received<=0;gather<=0;done_valid<=0;done_error<=0;
   a_valid<=0;a_bank<=0;a_row<=0;a_tile<=0;a_wide<=0;a_data<=0;
   b_valid<=0;b_bank<=0;b_tile<=0;b_wide<=0;b_half<=0;b_data<=0;
  end else begin
   if(done_valid&&done_ready)done_valid<=0;
   if(a_valid&&a_ready)a_valid<=0;
   if(b_valid&&b_ready)b_valid<=0;
   if(load_valid&&load_ready)begin
    done_error<=bad;fault<=0;received<=0;issued_done<=0;phase_b<=1;
    bank<=load_bank;wa<=load_a_wide;wb<=load_b_wide;
    abase<=load_a_base;bbase<=load_b_base;rows<=load_rows;tiles<=load_tiles;
    grow<=0;gtile<=0;gword<=0;gather<=0;
    expected<=7'(load_tiles)*(load_b_wide?7'd8:7'd4)+7'(load_rows)*7'(load_tiles);
    if(bad)done_valid<=1;else active<=1;
   end
   if(qwvalid&&qwready)begin
    if(phase_b)begin
     if(gword==(wb?3'd7:3'd3))begin
      gword<=0;
      if(3'(gtile)+1==tiles)begin phase_b<=0;gtile<=0;end
      else gtile<=gtile+1'b1;
     end else gword<=gword+1'b1;
    end else begin
     if(3'(gtile)+1==tiles)begin
      gtile<=0;
      if(4'(grow)+1==rows)issued_done<=1;
      else grow<=grow+1'b1;
     end else gtile<=gtile+1'b1;
    end
   end
   if(srvalid&&srready)begin
    received<=received+1'b1;
    if(srdata[128])fault<=1;
    if(!fault&&!srdata[128])begin
     if(!srdata[137])begin
      a_valid<=1;a_bank<=bank;a_row<=srdata[136:134];a_tile<=srdata[133:132];
      a_wide<=wa;a_data<=srdata[127:0];
     end else begin
      gather[128*int'(srdata[130:129])+:128]<=srdata[127:0];
      if(srdata[130:129]==3)begin
       b_valid<=1;b_bank<=bank;b_tile<=srdata[133:132];b_half<=srdata[131];
       b_wide<=wb;b_data<={srdata[127:0],gather[383:0]};
      end
     end
    end
   end
   // Every issued external read is drained even after a read error.
   // An error invalidates this load; caller must invalidate M's target bank.
   if(active&&issued_done&&received==expected&&!a_valid&&!b_valid)begin
    active<=0;done_valid<=1;done_error<=fault;
   end
  end
 end
endmodule
