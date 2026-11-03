// Verification fixture: unchanged physical S macro, ordinary port only.
module control_d_s_pair(
 input wire clk,reset,
 input wire task_valid,output wire task_ready,input wire [255:0] task_data,
 output wire complete_valid,input wire complete_ready,output reg [63:0] complete_data,
 output wire protocol_error,
 output wire arvalid,input wire arready,output wire [39:0] araddr,output wire [1:0] arid,
 output wire [7:0] arlen,output wire [2:0] arsize,output wire [1:0] arburst,
 input wire rvalid,output wire rready,input wire [127:0] rdata,input wire [1:0] rid,input wire [1:0] rresp,input wire rlast,
 output wire awvalid,input wire awready,output wire [39:0] awaddr,output wire [1:0] awid,
 output wire [7:0] awlen,output wire [2:0] awsize,output wire [1:0] awburst,
 output wire wvalid,input wire wready,output wire [127:0] wdata,output wire [15:0] wstrb,output wire wlast,
 input wire bvalid,output wire bready,input wire [1:0] bid,input wire [1:0] bresp,
 output wire s_req,output reg s_wr,output reg [9:0] s_addr,output reg [3:0] s_instance,output reg [127:0] s_din,
 output wire s_ready,s_valid,s_take,output wire [127:0] s_dout,
 output wire [31:0] s_read_count,s_write_count,
 input wire init_mode,init_valid,input wire [9:0] init_address,input wire [127:0] init_data,
 output wire init_ready,init_response,input wire init_take
);
 control_d dma(.*);
 wire mem_ready,mem_valid;wire [127:0] mem_data;
 assign s_ready=!init_mode && mem_ready;assign s_valid=!init_mode && mem_valid;assign s_dout=mem_data;
 assign init_ready=init_mode && mem_ready;assign init_response=init_mode && mem_valid;
 wire unused_lr,unused_done,unused_error,unused_busy,unused_av,unused_ab,unused_aw,unused_bv,unused_bb,unused_bw,unused_bh;
 wire [2:0] unused_ar;wire [1:0] unused_at,unused_bt;wire [127:0] unused_ad;wire [511:0] unused_bd;
 block_feed_s_macro_sram storage(.clk(clk),.reset(reset),.req(init_mode?init_valid:s_req),.wr(init_mode?1'b1:s_wr),
  .addr(init_mode?init_address:s_addr),.din(init_mode?init_data:s_din),.ready(mem_ready),.valid(mem_valid),
  .take(init_mode?init_take:s_take),.dout(mem_data),.load_valid(1'b0),.load_ready(unused_lr),.load_bank(1'b0),
  .load_rows(4'd0),.load_tiles(3'd0),.load_a_wide(1'b0),.load_b_wide(1'b0),.load_reuse_b(1'b0),
  .load_a_base(10'd0),.load_b_base(10'd0),.done_valid(unused_done),.done_take(1'b1),.done_error(unused_error),.busy(unused_busy),
  .a_valid(unused_av),.a_ready(1'b1),.a_bank(unused_ab),.a_row(unused_ar),.a_tile(unused_at),.a_wide(unused_aw),.a_data(unused_ad),
  .b_valid(unused_bv),.b_ready(1'b1),.b_bank(unused_bb),.b_tile(unused_bt),.b_wide(unused_bw),.b_half(unused_bh),.b_data(unused_bd));
 endmodule
