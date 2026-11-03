module dram_m_fifo_tb #(parameter FIFO_DEPTH=16)(
 input wire core_clk,mem_clk,reset,
 input wire load_valid,output wire load_ready,input wire load_bank,
 input wire [39:0] load_a_base,load_b_base,
 input wire [3:0] load_rows,input wire [2:0] load_tiles,
 input wire load_a_wide,load_b_wide,
 output wire done_valid,input wire done_ready,output wire done_error,
 output wire mem_req_valid,input wire mem_req_ready,output wire [39:0] mem_req_address,
 input wire mem_rsp_valid,output wire mem_rsp_ready,input wire [127:0] mem_rsp_data,input wire mem_rsp_error,
 input wire allow_a,allow_b,
 input wire cmd_valid,output wire cmd_ready,input wire [3:0] cmd_op,
 input wire [5:0] cmd_index,input wire [63:0] cmd_data,
 output wire rsp_valid,input wire rsp_ready,output wire [127:0] rsp_data,
 output wire rsp_error,rsp_saturated,busy,
 output wire a_valid,a_ready,a_bank,a_wide,output wire [2:0] a_row,
 output wire [1:0] a_tile,output wire [127:0] a_data,
 output wire b_valid,b_ready,b_bank,b_wide,b_half,output wire [1:0] b_tile,
 output wire [511:0] b_data,
 output wire request_fifo_full,response_fifo_full,loading
);
 wire mar,mbr;
 assign a_ready=mar&&allow_a;
 assign b_ready=mbr&&allow_b;
 dram_m_fifo_loader #(.FIFO_DEPTH(FIFO_DEPTH)) loader(
 .core_clk(core_clk),.mem_clk(mem_clk),.reset(reset),
 .load_valid(load_valid),.load_ready(load_ready),.load_bank(load_bank),
 .load_a_base(load_a_base),.load_b_base(load_b_base),.load_rows(load_rows),.load_tiles(load_tiles),
 .load_a_wide(load_a_wide),.load_b_wide(load_b_wide),
 .done_valid(done_valid),.done_ready(done_ready),.done_error(done_error),
 .mem_req_valid(mem_req_valid),.mem_req_ready(mem_req_ready),.mem_req_address(mem_req_address),
 .mem_rsp_valid(mem_rsp_valid),.mem_rsp_ready(mem_rsp_ready),.mem_rsp_data(mem_rsp_data),.mem_rsp_error(mem_rsp_error),
 .a_valid(a_valid),.a_ready(a_ready),.a_bank(a_bank),.a_row(a_row),.a_tile(a_tile),.a_wide(a_wide),.a_data(a_data),
 .b_valid(b_valid),.b_ready(b_ready),.b_bank(b_bank),.b_tile(b_tile),.b_wide(b_wide),.b_half(b_half),.b_data(b_data),
 .request_fifo_full(request_fifo_full),.response_fifo_full(response_fifo_full),.loading(loading));
 block_v2_m m(.clk(core_clk),.reset(reset),
 .a_valid(a_valid&&allow_a),.a_ready(mar),.a_bank(a_bank),.a_row(a_row),.a_tile(a_tile),.a_wide(a_wide),.a_data(a_data),
 .b_valid(b_valid&&allow_b),.b_ready(mbr),.b_bank(b_bank),.b_tile(b_tile),.b_wide(b_wide),.b_half(b_half),.b_data(b_data),
 .cmd_valid(cmd_valid),.cmd_ready(cmd_ready),.cmd_op(cmd_op),.cmd_index(cmd_index),.cmd_data(cmd_data),
 .rsp_valid(rsp_valid),.rsp_ready(rsp_ready),.rsp_data(rsp_data),.rsp_error(rsp_error),.rsp_saturated(rsp_saturated),.busy(busy));
endmodule
