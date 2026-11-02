// Single-clock AXI4-Lite slave. AW and W are independent one-entry queues;
// AR is a separate one-entry queue. Never requires simultaneous AW/W arrival.
module control_axil_bridge(
 input wire clk,reset,
 input wire [15:0] axil_awaddr,input wire axil_awvalid,output wire axil_awready,
 input wire [31:0] axil_wdata,input wire [3:0] axil_wstrb,input wire axil_wvalid,output wire axil_wready,
 output reg [1:0] axil_bresp,output reg axil_bvalid,input wire axil_bready,
 input wire [15:0] axil_araddr,input wire axil_arvalid,output wire axil_arready,
 output reg [31:0] axil_rdata,output reg [1:0] axil_rresp,output reg axil_rvalid,input wire axil_rready,
 output reg cfg_valid,input wire cfg_ready,output reg cfg_write,output reg [15:0] cfg_addr,
 output reg [31:0] cfg_wdata,output reg [3:0] cfg_wstrb,
 input wire cfg_rsp_valid,output wire cfg_rsp_ready,input wire [31:0] cfg_rdata,input wire cfg_error
);
 localparam IDLE=0,SEND=1,REPLY=2;
 reg [1:0] state;reg aw_full,w_full,ar_full,last_write;
 reg [15:0] aw_addr,ar_addr;reg [31:0] w_data;reg [3:0] w_strb;
 // Minimal AXI-Lite profile: optional PROT attributes are absent (default 000).
 // The platform interconnect enforces access before this physical endpoint.
 assign axil_awready=!reset && !aw_full;assign axil_wready=!reset && !w_full;assign axil_arready=!reset && !ar_full;
 assign cfg_rsp_ready=!reset && state==REPLY && (cfg_write?!axil_bvalid:!axil_rvalid);
 wire write_eligible=aw_full && w_full && !axil_bvalid;
 wire read_eligible=ar_full && !axil_rvalid;
 always @(posedge clk) begin
  if(reset) begin
   state<=IDLE;aw_full<=0;w_full<=0;ar_full<=0;last_write<=0;aw_addr<=0;ar_addr<=0;w_data<=0;w_strb<=0;
   axil_bvalid<=0;axil_bresp<=0;axil_rvalid<=0;axil_rdata<=0;axil_rresp<=0;
   cfg_valid<=0;cfg_write<=0;cfg_addr<=0;cfg_wdata<=0;cfg_wstrb<=0;
  end else begin
   if(axil_awvalid && axil_awready) begin aw_addr<=axil_awaddr;aw_full<=1;end
   if(axil_wvalid && axil_wready) begin w_data<=axil_wdata;w_strb<=axil_wstrb;w_full<=1;end
   if(axil_arvalid && axil_arready) begin ar_addr<=axil_araddr;ar_full<=1;end
   if(axil_bvalid && axil_bready) axil_bvalid<=0;
   if(axil_rvalid && axil_rready) axil_rvalid<=0;
   case(state)
    IDLE:if(write_eligible && (!read_eligible || !last_write)) begin
     cfg_write<=1;cfg_addr<=aw_addr;cfg_wdata<=w_data;cfg_wstrb<=w_strb;cfg_valid<=1;
     aw_full<=0;w_full<=0;last_write<=1;state<=SEND;
    end else if(read_eligible) begin
     cfg_write<=0;cfg_addr<=ar_addr;cfg_wdata<=0;cfg_wstrb<=0;cfg_valid<=1;
     ar_full<=0;last_write<=0;state<=SEND;
    end
    SEND:if(cfg_valid && cfg_ready) begin cfg_valid<=0;state<=REPLY;end
    REPLY:if(cfg_rsp_valid && cfg_rsp_ready) begin
     if(cfg_write) begin axil_bvalid<=1;axil_bresp<=cfg_error?2'b10:2'b00;end
     else begin axil_rvalid<=1;axil_rresp<=cfg_error?2'b10:2'b00;axil_rdata<=cfg_rdata;end
     state<=IDLE;
    end
    default:state<=IDLE;
   endcase
  end
 end
endmodule
