// D: independent finite read/write planners and 32-word payload buffers.
// S narrow accesses share one physical port; this registered arbiter records
// real accepted accesses. External DRAM controller/PHY are outside this macro.
module control_d(
 input wire clk,reset,
 input wire task_valid,output wire task_ready,input wire [255:0] task_data,
 output reg complete_valid,input wire complete_ready,output reg [63:0] complete_data,
 output wire protocol_error,
 output wire arvalid,input wire arready,output wire [39:0] araddr,output wire [1:0] arid,
 output wire [7:0] arlen,output wire [2:0] arsize,output wire [1:0] arburst,
 input wire rvalid,output wire rready,input wire [127:0] rdata,input wire [1:0] rid,input wire [1:0] rresp,input wire rlast,
 output wire awvalid,input wire awready,output wire [39:0] awaddr,output wire [1:0] awid,
 output wire [7:0] awlen,output wire [2:0] awsize,output wire [1:0] awburst,
 output wire wvalid,input wire wready,output wire [127:0] wdata,output wire [15:0] wstrb,output wire wlast,
 input wire bvalid,output wire bready,input wire [1:0] bid,input wire [1:0] bresp,
 output reg s_req,output reg s_wr,output reg [9:0] s_addr,output reg [3:0] s_instance,output reg [127:0] s_din,
 input wire s_ready,input wire s_valid,output wire s_take,input wire [127:0] s_dout,
 output reg [31:0] s_read_count,s_write_count
);
 wire [1:0] planner_error,transport_error;
 assign protocol_error=|planner_error || |transport_error;
 wire rtask_ready,wtask_ready;
 assign task_ready=!protocol_error && (task_data[0]?wtask_ready:rtask_ready);
 wire rv,rr,wv,wr,ri,wi,rack,wack,rackid,wackid,rackerr,wackerr;
 wire [39:0] raddress,waddress;wire [9:0] rlocal,wlocal;wire [3:0] rinstance,winstance;
 wire [4:0] rbeats,wbeats;wire [15:0] rmask,wmask;
 wire rdir,wdir;wire [5:0] rreserved,wreserved;
 wire rcv,wcv,rcr,wcr;wire [63:0] rcd,wcd;
 control_dma_planner read_plan(
  .clk(clk),.reset(reset),.task_valid(task_valid && !task_data[0] && !protocol_error),.task_ready(rtask_ready),.task_data(task_data),
  .burst_valid(rv),.burst_ready(rr),.burst_address(raddress),.burst_local_word(rlocal),.burst_s_instance(rinstance),
  .burst_beats(rbeats),.burst_id(ri),.burst_write(rdir),.burst_last_strobe(rmask),
  .ack_valid(rack),.ack_id(rackid),.ack_error(rackerr),.complete_valid(rcv),.complete_ready(rcr),.complete_data(rcd),
  .reserved_words(rreserved),.protocol_error(planner_error[0]));
 control_dma_planner write_plan(
  .clk(clk),.reset(reset),.task_valid(task_valid && task_data[0] && !protocol_error),.task_ready(wtask_ready),.task_data(task_data),
  .burst_valid(wv),.burst_ready(wr),.burst_address(waddress),.burst_local_word(wlocal),.burst_s_instance(winstance),
  .burst_beats(wbeats),.burst_id(wi),.burst_write(wdir),.burst_last_strobe(wmask),
  .ack_valid(wack),.ack_id(wackid),.ack_error(wackerr),.complete_valid(wcv),.complete_ready(wcr),.complete_data(wcd),
  .reserved_words(wreserved),.protocol_error(planner_error[1]));
 wire rsvalid,rsready,wsrequest,wsready;wire [9:0] rsaddress,wsaddress;
 wire [3:0] rsinstance,wsinstance;wire [127:0] rsdata;
 control_dma_read read_transport(
  .clk(clk),.reset(reset),.burst_valid(rv),.burst_ready(rr),.burst_address(raddress),.burst_local_word(rlocal),.burst_s_instance(rinstance),
  .burst_beats(rbeats),.burst_id(ri),.burst_last_strobe(rmask),.ack_valid(rack),.ack_id(rackid),.ack_error(rackerr),.protocol_error(transport_error[0]),
  .arvalid(arvalid),.arready(arready),.araddr(araddr),.arid(arid),.arlen(arlen),.arsize(arsize),.arburst(arburst),
  .rvalid(rvalid),.rready(rready),.rdata(rdata),.rid(rid),.rresp(rresp),.rlast(rlast),
  .s_valid(rsvalid),.s_ready(rsready),.s_address(rsaddress),.s_instance(rsinstance),.s_data(rsdata));
 control_dma_write write_transport(
  .clk(clk),.reset(reset),.burst_valid(wv),.burst_ready(wr),.burst_address(waddress),.burst_local_word(wlocal),.burst_s_instance(winstance),
  .burst_beats(wbeats),.burst_id(wi),.burst_last_strobe(wmask),.ack_valid(wack),.ack_id(wackid),.ack_error(wackerr),.protocol_error(transport_error[1]),
  .awvalid(awvalid),.awready(awready),.awaddr(awaddr),.awid(awid),.awlen(awlen),.awsize(awsize),.awburst(awburst),
  .wvalid(wvalid),.wready(wready),.wdata(wdata),.wstrb(wstrb),.wlast(wlast),.bvalid(bvalid),.bready(bready),.bid(bid),.bresp(bresp),
  .s_request(wsrequest),.s_ready(wsready),.s_address(wsaddress),.s_instance(wsinstance),.s_valid(s_valid),.s_take(s_take),.s_data(s_dout));
 reg last_load,last_complete_write;
 assign rsready=s_req && s_wr && s_ready;
 assign wsready=s_req && !s_wr && s_ready;
 wire choose_load=rsvalid && (!wsrequest || !last_load);
 wire choose_read_complete=rcv && (!wcv || last_complete_write);
 wire complete_room=!complete_valid || complete_ready;
 assign rcr=complete_room && choose_read_complete;
 assign wcr=complete_room && !choose_read_complete && wcv;
 always @(posedge clk) begin
  if(reset) begin
   s_req<=0;s_wr<=0;s_addr<=0;s_instance<=0;s_din<=0;last_load<=0;
   s_read_count<=0;s_write_count<=0;complete_valid<=0;complete_data<=0;last_complete_write<=0;
  end else begin
   if(!s_req) begin
    if(choose_load) begin s_req<=1;s_wr<=1;s_addr<=rsaddress;s_instance<=rsinstance;s_din<=rsdata;end
    else if(wsrequest) begin s_req<=1;s_wr<=0;s_addr<=wsaddress;s_instance<=wsinstance;s_din<=0;end
   end else if(s_ready) begin
    s_req<=0;last_load<=s_wr;
    if(s_wr) s_write_count<=s_write_count+1;else s_read_count<=s_read_count+1;
   end
   if(complete_valid && complete_ready) complete_valid<=0;
   if(rcr) begin complete_valid<=1;complete_data<=rcd;last_complete_write<=0;end
   else if(wcr) begin complete_valid<=1;complete_data<=wcd;last_complete_write<=1;end
  end
 end
 wire unused_direction_credit=&{1'b0,rdir,wdir,rreserved,wreserved};
endmodule
