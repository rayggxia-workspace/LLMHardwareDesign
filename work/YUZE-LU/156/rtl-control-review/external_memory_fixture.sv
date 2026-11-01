module external_memory_fixture(
input wire clk,reset,
input wire  dma_cmd_valid,
output wire  dma_cmd_ready,
input wire [1:0] dma_cmd_mode,
input wire [31:0] dma_cmd_ext_base,
input wire [31:0] dma_cmd_ext_stride,
input wire [10:0] dma_cmd_rows,
input wire [10:0] dma_cmd_cols,
input wire [10:0] dma_cmd_s_base,
input wire [10:0] dma_cmd_s_stride,
output wire  dma_done_valid,
input wire  dma_done_ready,
output wire  dma_done_error,
output wire  dma_busy,
output wire  dma_ext_valid,
input wire  dma_ext_ready,
output wire  dma_ext_write,
output wire [31:0] dma_ext_addr,
output wire [127:0] dma_ext_data,
input wire  dma_ext_rsp_valid,
output wire  dma_ext_rsp_ready,
input wire [127:0] dma_ext_rsp_data,
input wire  dma_ext_rsp_error,
output wire [2:0] dma_reserved_words,
input wire  s_load_valid,
output wire  s_load_ready,
input wire  s_load_bank,
input wire [3:0] s_load_rows,
input wire [2:0] s_load_tiles,
input wire  s_load_a_wide,
input wire  s_load_b_wide,
input wire  s_load_reuse_b,
input wire [9:0] s_load_a_base,
input wire [9:0] s_load_b_base,
output wire  s_done_valid,
input wire  s_done_take,
output wire  s_done_error,
output wire  s_busy,
input wire  m_cmd_valid,
output wire  m_cmd_ready,
input wire [3:0] m_cmd_op,
input wire [5:0] m_cmd_index,
input wire [63:0] m_cmd_data,
output wire  m_rsp_valid,
input wire  m_rsp_ready,
output wire [127:0] m_rsp_data,
output wire  m_rsp_error,
output wire  m_rsp_saturated,
output wire  m_busy,
input wire  n_cmd_valid,
output wire  n_cmd_ready,
input wire [3:0] n_cmd_op,
input wire [3:0] n_cmd_count,
input wire [31:0] n_cmd_param,
input wire [127:0] n_cmd_data,
input wire [127:0] n_cmd_aux,
output wire  n_rsp_valid,
input wire  n_rsp_ready,
output wire [127:0] n_rsp_data,
output wire  n_rsp_error,
output wire  n_rsp_saturated,
output wire  n_busy,
input wire  r_cmd_valid,
output wire  r_cmd_ready,
input wire [3:0] r_cmd_op,
input wire [9:0] r_cmd_index,
input wire [127:0] r_cmd_data,
output wire  r_rsp_valid,
input wire  r_rsp_ready,
output wire [127:0] r_rsp_data,
output wire  r_rsp_error,
output wire  r_busy,
input wire  t_begin_valid,
output wire  t_begin_ready,
input wire [1:0] t_begin_owner,
input wire [31:0] t_begin_generation,
input wire [9:0] t_begin_words,
input wire  t_write_valid,
output wire  t_write_ready,
input wire [9:0] t_write_index,
input wire [127:0] t_write_data,
input wire  t_commit_valid,
output wire  t_commit_ready,
input wire  t_revoke_valid,
output wire  t_revoke_ready,
output wire [9:0] t_read_index,
output wire [1:0] t_owner,
output wire [31:0] t_generation,
output wire [9:0] t_word_count,
input wire  t_release_valid,
output wire  t_release_ready,
output wire  t_busy,
output wire  t_sealed,
output wire  t_committed,
output wire  t_protocol_error,
output wire [2:0] t_debug_state,
input wire cpu_req,
input wire cpu_wr,
input wire cpu_take,
input wire [9:0] cpu_addr,
input wire [127:0] cpu_din,
output wire cpu_ready,cpu_valid,
output wire [127:0] cpu_dout,
output wire monitor_a_fire,monitor_b_fire,monitor_s_wait
);
wire  dma_s_req;
wire  dma_s_wr;
wire [9:0] dma_s_addr;
wire [127:0] dma_s_din;
wire  dma_s_ready;
wire  dma_s_valid;
wire  dma_s_take;
wire [127:0] dma_s_dout;
wire  dma_stream_valid;
wire  dma_stream_ready;
wire [127:0] dma_stream_data;
wire  dma_stream_last;
wire  mem_req;
wire  mem_wr;
wire [9:0] mem_addr;
wire [127:0] mem_din;
wire  mem_ready;
wire  mem_valid;
wire  mem_take;
wire [127:0] mem_dout;
wire  feed_a_valid;
wire  feed_a_ready;
wire  feed_a_bank;
wire [2:0] feed_a_row;
wire [1:0] feed_a_tile;
wire  feed_a_wide;
wire [127:0] feed_a_data;
wire  feed_b_valid;
wire  feed_b_ready;
wire  feed_b_bank;
wire [1:0] feed_b_tile;
wire  feed_b_wide;
wire  feed_b_half;
wire [511:0] feed_b_data;
finite_dma dma(.clk(clk),.reset(reset),.cmd_valid(dma_cmd_valid),.cmd_ready(dma_cmd_ready),.cmd_mode(dma_cmd_mode),.cmd_ext_base(dma_cmd_ext_base),.cmd_ext_stride(dma_cmd_ext_stride),.cmd_rows(dma_cmd_rows),.cmd_cols(dma_cmd_cols),.cmd_s_base(dma_cmd_s_base),.cmd_s_stride(dma_cmd_s_stride),.done_valid(dma_done_valid),.done_ready(dma_done_ready),.done_error(dma_done_error),.busy(dma_busy),.ext_valid(dma_ext_valid),.ext_ready(dma_ext_ready),.ext_write(dma_ext_write),.ext_addr(dma_ext_addr),.ext_data(dma_ext_data),.ext_rsp_valid(dma_ext_rsp_valid),.ext_rsp_ready(dma_ext_rsp_ready),.ext_rsp_data(dma_ext_rsp_data),.ext_rsp_error(dma_ext_rsp_error),.s_req(dma_s_req),.s_wr(dma_s_wr),.s_addr(dma_s_addr),.s_din(dma_s_din),.s_ready(dma_s_ready),.s_valid(dma_s_valid),.s_take(dma_s_take),.s_dout(dma_s_dout),.stream_valid(dma_stream_valid),.stream_ready(dma_stream_ready),.stream_data(dma_stream_data),.stream_last(dma_stream_last),.reserved_words(dma_reserved_words));
`ifdef TEST_SRAM
block_feed_s_macro_sram s(.clk(clk),.reset(reset),.req(mem_req),.wr(mem_wr),.addr(mem_addr),.din(mem_din),.ready(mem_ready),.valid(mem_valid),.take(mem_take),.dout(mem_dout),.load_valid(s_load_valid),.load_ready(s_load_ready),.load_bank(s_load_bank),.load_rows(s_load_rows),.load_tiles(s_load_tiles),.load_a_wide(s_load_a_wide),.load_b_wide(s_load_b_wide),.load_reuse_b(s_load_reuse_b),.load_a_base(s_load_a_base),.load_b_base(s_load_b_base),.done_valid(s_done_valid),.done_take(s_done_take),.done_error(s_done_error),.busy(s_busy),.a_valid(feed_a_valid),.a_ready(feed_a_ready),.a_bank(feed_a_bank),.a_row(feed_a_row),.a_tile(feed_a_tile),.a_wide(feed_a_wide),.a_data(feed_a_data),.b_valid(feed_b_valid),.b_ready(feed_b_ready),.b_bank(feed_b_bank),.b_tile(feed_b_tile),.b_wide(feed_b_wide),.b_half(feed_b_half),.b_data(feed_b_data));
`else
block_feed_s_macro s(.clk(clk),.reset(reset),.req(mem_req),.wr(mem_wr),.addr(mem_addr),.din(mem_din),.ready(mem_ready),.valid(mem_valid),.take(mem_take),.dout(mem_dout),.load_valid(s_load_valid),.load_ready(s_load_ready),.load_bank(s_load_bank),.load_rows(s_load_rows),.load_tiles(s_load_tiles),.load_a_wide(s_load_a_wide),.load_b_wide(s_load_b_wide),.load_reuse_b(s_load_reuse_b),.load_a_base(s_load_a_base),.load_b_base(s_load_b_base),.done_valid(s_done_valid),.done_take(s_done_take),.done_error(s_done_error),.busy(s_busy),.a_valid(feed_a_valid),.a_ready(feed_a_ready),.a_bank(feed_a_bank),.a_row(feed_a_row),.a_tile(feed_a_tile),.a_wide(feed_a_wide),.a_data(feed_a_data),.b_valid(feed_b_valid),.b_ready(feed_b_ready),.b_bank(feed_b_bank),.b_tile(feed_b_tile),.b_wide(feed_b_wide),.b_half(feed_b_half),.b_data(feed_b_data));
`endif
block_v2_m m(.clk(clk),.reset(reset),.a_valid(feed_a_valid),.a_ready(feed_a_ready),.a_bank(feed_a_bank),.a_row(feed_a_row),.a_tile(feed_a_tile),.a_wide(feed_a_wide),.a_data(feed_a_data),.b_valid(feed_b_valid),.b_ready(feed_b_ready),.b_bank(feed_b_bank),.b_tile(feed_b_tile),.b_wide(feed_b_wide),.b_half(feed_b_half),.b_data(feed_b_data),.cmd_valid(m_cmd_valid),.cmd_ready(m_cmd_ready),.cmd_op(m_cmd_op),.cmd_index(m_cmd_index),.cmd_data(m_cmd_data),.rsp_valid(m_rsp_valid),.rsp_ready(m_rsp_ready),.rsp_data(m_rsp_data),.rsp_error(m_rsp_error),.rsp_saturated(m_rsp_saturated),.busy(m_busy));
block_v2_n n(.clk(clk),.reset(reset),.cmd_valid(n_cmd_valid),.cmd_ready(n_cmd_ready),.cmd_op(n_cmd_op),.cmd_count(n_cmd_count),.cmd_param(n_cmd_param),.cmd_data(n_cmd_data),.cmd_aux(n_cmd_aux),.rsp_valid(n_rsp_valid),.rsp_ready(n_rsp_ready),.rsp_data(n_rsp_data),.rsp_error(n_rsp_error),.rsp_saturated(n_rsp_saturated),.busy(n_busy));
block_v1_r r(.clk(clk),.reset(reset),.cmd_valid(r_cmd_valid),.cmd_ready(r_cmd_ready),.cmd_op(r_cmd_op),.cmd_index(r_cmd_index),.cmd_data(r_cmd_data),.rsp_valid(r_rsp_valid),.rsp_ready(r_rsp_ready),.rsp_data(r_rsp_data),.rsp_error(r_rsp_error),.busy(r_busy));
transaction6k t(.clk(clk),.reset(reset),.begin_valid(t_begin_valid),.begin_ready(t_begin_ready),.begin_owner(t_begin_owner),.begin_generation(t_begin_generation),.begin_words(t_begin_words),.write_valid(t_write_valid),.write_ready(t_write_ready),.write_index(t_write_index),.write_data(t_write_data),.commit_valid(t_commit_valid),.commit_ready(t_commit_ready),.revoke_valid(t_revoke_valid),.revoke_ready(t_revoke_ready),.read_valid(dma_stream_valid),.read_take(dma_stream_ready),.read_index(t_read_index),.read_data(dma_stream_data),.read_last(dma_stream_last),.owner(t_owner),.generation(t_generation),.word_count(t_word_count),.release_valid(t_release_valid),.release_ready(t_release_ready),.busy(t_busy),.sealed(t_sealed),.committed(t_committed),.protocol_error(t_protocol_error),.debug_state(t_debug_state));
assign mem_req=dma_busy?dma_s_req:cpu_req;
assign mem_wr=dma_busy?dma_s_wr:cpu_wr;
assign mem_addr=dma_busy?dma_s_addr:cpu_addr;
assign mem_din=dma_busy?dma_s_din:cpu_din;
assign mem_take=dma_busy?dma_s_take:cpu_take;
assign dma_s_ready=dma_busy&&mem_ready;
assign dma_s_valid=dma_busy&&mem_valid;
assign dma_s_dout=mem_dout;
assign cpu_ready=!dma_busy&&mem_ready;
assign cpu_valid=!dma_busy&&mem_valid;
assign cpu_dout=mem_dout;
assign monitor_a_fire=feed_a_valid&&feed_a_ready;
assign monitor_b_fire=feed_b_valid&&feed_b_ready;
assign monitor_s_wait=mem_req&&!mem_ready;
endmodule
