// Fixed reference topology for real-interface validation. Macro RTL is unchanged.
module control_system(
 input wire  clk,
 input wire  reset,
 input wire [15:0] axil_awaddr,
 input wire  axil_awvalid,
 output wire  axil_awready,
 input wire [31:0] axil_wdata,
 input wire [3:0] axil_wstrb,
 input wire  axil_wvalid,
 output wire  axil_wready,
 output wire [1:0] axil_bresp,
 output wire  axil_bvalid,
 input wire  axil_bready,
 input wire [15:0] axil_araddr,
 input wire  axil_arvalid,
 output wire  axil_arready,
 output wire [31:0] axil_rdata,
 output wire [1:0] axil_rresp,
 output wire  axil_rvalid,
 input wire  axil_rready,
 output wire  arvalid,
 input wire  arready,
 output wire [39:0] araddr,
 output wire [1:0] arid,
 output wire [7:0] arlen,
 output wire [2:0] arsize,
 output wire [1:0] arburst,
 input wire  rvalid,
 output wire  rready,
 input wire [127:0] rdata,
 input wire [1:0] rid,
 input wire [1:0] rresp,
 input wire  rlast,
 output wire  awvalid,
 input wire  awready,
 output wire [39:0] awaddr,
 output wire [1:0] awid,
 output wire [7:0] awlen,
 output wire [2:0] awsize,
 output wire [1:0] awburst,
 output wire  wvalid,
 input wire  wready,
 output wire [127:0] wdata,
 output wire [15:0] wstrb,
 output wire  wlast,
 input wire  bvalid,
 output wire  bready,
 input wire [1:0] bid,
 input wire [1:0] bresp,
 output wire  busy,
 output wire  ended,
 output wire [3:0] fault,
 output wire [7:0] error_pc,
 output wire  protocol_error,
 output wire [31:0] s_read_count,
 output wire [31:0] s_write_count
);
 wire  cfg_valid;
 wire  cfg_ready;
 wire  cfg_write;
 wire [15:0] cfg_addr;
 wire [31:0] cfg_wdata;
 wire [3:0] cfg_wstrb;
 wire  cfg_rsp_valid;
 wire  cfg_rsp_ready;
 wire [31:0] cfg_rdata;
 wire  cfg_error;
 control_axil_bridge host(.clk(clk),.reset(reset),.axil_awaddr(axil_awaddr),.axil_awvalid(axil_awvalid),.axil_awready(axil_awready),.axil_wdata(axil_wdata),.axil_wstrb(axil_wstrb),.axil_wvalid(axil_wvalid),.axil_wready(axil_wready),.axil_bresp(axil_bresp),.axil_bvalid(axil_bvalid),.axil_bready(axil_bready),.axil_araddr(axil_araddr),.axil_arvalid(axil_arvalid),.axil_arready(axil_arready),.axil_rdata(axil_rdata),.axil_rresp(axil_rresp),.axil_rvalid(axil_rvalid),.axil_rready(axil_rready),.cfg_valid(cfg_valid),.cfg_ready(cfg_ready),.cfg_write(cfg_write),.cfg_addr(cfg_addr),.cfg_wdata(cfg_wdata),.cfg_wstrb(cfg_wstrb),.cfg_rsp_valid(cfg_rsp_valid),.cfg_rsp_ready(cfg_rsp_ready),.cfg_rdata(cfg_rdata),.cfg_error(cfg_error));
 wire  task_valid;
 wire  task_ready;
 wire [31:0] task_data;
 wire [3:0] task_endpoint;
 wire  task_last;
 wire  done_valid;
 wire  done_ready;
 wire [31:0] done_data;
 wire  done_last;
 control_c controller(.clk(clk),.reset(reset),.cfg_valid(cfg_valid),.cfg_ready(cfg_ready),.cfg_write(cfg_write),.cfg_addr(cfg_addr),.cfg_wdata(cfg_wdata),.cfg_wstrb(cfg_wstrb),.cfg_rsp_valid(cfg_rsp_valid),.cfg_rsp_ready(cfg_rsp_ready),.cfg_rdata(cfg_rdata),.cfg_error(cfg_error),.task_valid(task_valid),.task_ready(task_ready),.task_data(task_data),.task_endpoint(task_endpoint),.task_last(task_last),.done_valid(done_valid),.done_ready(done_ready),.done_data(done_data),.done_last(done_last),.busy(busy),.ended(ended),.fault(fault),.error_pc(error_pc));
 wire [6:0] q_cmd_ready;
 wire [6:0] q_task_valid;
 wire [6:0] q_task_ready;
 wire [1791:0] q_tasks;
 wire [6:0] q_complete_valid;
 wire [6:0] q_complete_ready;
 wire [447:0] q_completions;
 wire [6:0] q_done_valid;
 wire [6:0] q_done_ready;
 wire [223:0] q_done_data;
 wire [6:0] q_done_last;
 wire [6:0] q_error;
 wire [6:0] routed_cmd_valid;
 control_endpoint_queue queue_0(.clk(clk),.reset(reset),.cmd_valid(routed_cmd_valid[0]),.cmd_ready(q_cmd_ready[0]),.cmd_data(task_data),.cmd_last(task_last),.task_valid(q_task_valid[0]),.task_ready(q_task_ready[0]),.task_data(q_tasks[0+:256]),.complete_valid(q_complete_valid[0]),.complete_ready(q_complete_ready[0]),.complete_data(q_completions[0+:64]),.done_valid(q_done_valid[0]),.done_ready(q_done_ready[0]),.done_data(q_done_data[0+:32]),.done_last(q_done_last[0]),.protocol_error(q_error[0]));
 control_endpoint_queue queue_1(.clk(clk),.reset(reset),.cmd_valid(routed_cmd_valid[1]),.cmd_ready(q_cmd_ready[1]),.cmd_data(task_data),.cmd_last(task_last),.task_valid(q_task_valid[1]),.task_ready(q_task_ready[1]),.task_data(q_tasks[256+:256]),.complete_valid(q_complete_valid[1]),.complete_ready(q_complete_ready[1]),.complete_data(q_completions[64+:64]),.done_valid(q_done_valid[1]),.done_ready(q_done_ready[1]),.done_data(q_done_data[32+:32]),.done_last(q_done_last[1]),.protocol_error(q_error[1]));
 control_endpoint_queue queue_2(.clk(clk),.reset(reset),.cmd_valid(routed_cmd_valid[2]),.cmd_ready(q_cmd_ready[2]),.cmd_data(task_data),.cmd_last(task_last),.task_valid(q_task_valid[2]),.task_ready(q_task_ready[2]),.task_data(q_tasks[512+:256]),.complete_valid(q_complete_valid[2]),.complete_ready(q_complete_ready[2]),.complete_data(q_completions[128+:64]),.done_valid(q_done_valid[2]),.done_ready(q_done_ready[2]),.done_data(q_done_data[64+:32]),.done_last(q_done_last[2]),.protocol_error(q_error[2]));
 control_endpoint_queue queue_3(.clk(clk),.reset(reset),.cmd_valid(routed_cmd_valid[3]),.cmd_ready(q_cmd_ready[3]),.cmd_data(task_data),.cmd_last(task_last),.task_valid(q_task_valid[3]),.task_ready(q_task_ready[3]),.task_data(q_tasks[768+:256]),.complete_valid(q_complete_valid[3]),.complete_ready(q_complete_ready[3]),.complete_data(q_completions[192+:64]),.done_valid(q_done_valid[3]),.done_ready(q_done_ready[3]),.done_data(q_done_data[96+:32]),.done_last(q_done_last[3]),.protocol_error(q_error[3]));
 control_endpoint_queue queue_4(.clk(clk),.reset(reset),.cmd_valid(routed_cmd_valid[4]),.cmd_ready(q_cmd_ready[4]),.cmd_data(task_data),.cmd_last(task_last),.task_valid(q_task_valid[4]),.task_ready(q_task_ready[4]),.task_data(q_tasks[1024+:256]),.complete_valid(q_complete_valid[4]),.complete_ready(q_complete_ready[4]),.complete_data(q_completions[256+:64]),.done_valid(q_done_valid[4]),.done_ready(q_done_ready[4]),.done_data(q_done_data[128+:32]),.done_last(q_done_last[4]),.protocol_error(q_error[4]));
 control_endpoint_queue queue_5(.clk(clk),.reset(reset),.cmd_valid(routed_cmd_valid[5]),.cmd_ready(q_cmd_ready[5]),.cmd_data(task_data),.cmd_last(task_last),.task_valid(q_task_valid[5]),.task_ready(q_task_ready[5]),.task_data(q_tasks[1280+:256]),.complete_valid(q_complete_valid[5]),.complete_ready(q_complete_ready[5]),.complete_data(q_completions[320+:64]),.done_valid(q_done_valid[5]),.done_ready(q_done_ready[5]),.done_data(q_done_data[160+:32]),.done_last(q_done_last[5]),.protocol_error(q_error[5]));
 control_endpoint_queue queue_6(.clk(clk),.reset(reset),.cmd_valid(routed_cmd_valid[6]),.cmd_ready(q_cmd_ready[6]),.cmd_data(task_data),.cmd_last(task_last),.task_valid(q_task_valid[6]),.task_ready(q_task_ready[6]),.task_data(q_tasks[1536+:256]),.complete_valid(q_complete_valid[6]),.complete_ready(q_complete_ready[6]),.complete_data(q_completions[384+:64]),.done_valid(q_done_valid[6]),.done_ready(q_done_ready[6]),.done_data(q_done_data[192+:32]),.done_last(q_done_last[6]),.protocol_error(q_error[6]));
 control_route routes(.clk(clk),.reset(reset),.task_valid(task_valid),.task_ready(task_ready),.task_endpoint(task_endpoint),
  .cmd_valid(routed_cmd_valid),.cmd_ready(q_cmd_ready),.endpoint_valid(q_done_valid),.endpoint_ready(q_done_ready),
  .endpoint_data(q_done_data),.endpoint_last(q_done_last),.done_valid(done_valid),.done_ready(done_ready),.done_data(done_data),.done_last(done_last));
 wire [5:0] mem_req;
 wire [5:0] mem_wr;
 wire [5:0] mem_ready;
 wire [5:0] mem_valid;
 wire [5:0] mem_take;
 wire [59:0] mem_addr;
 wire [767:0] mem_din;
 wire [127:0] mem_dout;
 wire  ep0_protocol_error;
 wire [3:0] ep0_s_instance;
 control_d endpoint_0(.clk(clk),.reset(reset),.task_valid(q_task_valid[0]),.task_ready(q_task_ready[0]),.task_data(q_tasks[0+:256]),.complete_valid(q_complete_valid[0]),.complete_ready(q_complete_ready[0]),.complete_data(q_completions[0+:64]),.protocol_error(ep0_protocol_error),.arvalid(arvalid),.arready(arready),.araddr(araddr),.arid(arid),.arlen(arlen),.arsize(arsize),.arburst(arburst),.rvalid(rvalid),.rready(rready),.rdata(rdata),.rid(rid),.rresp(rresp),.rlast(rlast),.awvalid(awvalid),.awready(awready),.awaddr(awaddr),.awid(awid),.awlen(awlen),.awsize(awsize),.awburst(awburst),.wvalid(wvalid),.wready(wready),.wdata(wdata),.wstrb(wstrb),.wlast(wlast),.bvalid(bvalid),.bready(bready),.bid(bid),.bresp(bresp),.s_req(mem_req[0]),.s_wr(mem_wr[0]),.s_addr(mem_addr[0+:10]),.s_instance(ep0_s_instance),.s_din(mem_din[0+:128]),.s_ready(mem_ready[0]),.s_valid(mem_valid[0]),.s_take(mem_take[0]),.s_dout(mem_dout),.s_read_count(s_read_count),.s_write_count(s_write_count));
 wire  ep1_cmd_valid;
 wire  ep1_cmd_ready;
 wire [3:0] ep1_cmd_op;
 wire [5:0] ep1_cmd_index;
 wire [63:0] ep1_cmd_data;
 wire  ep1_rsp_valid;
 wire  ep1_rsp_ready;
 wire [127:0] ep1_rsp_data;
 wire  ep1_rsp_error;
 wire  ep1_rsp_saturated;
 control_adapter_m endpoint_1(.clk(clk),.reset(reset),.task_valid(q_task_valid[1]),.task_ready(q_task_ready[1]),.task_data(q_tasks[256+:256]),.complete_valid(q_complete_valid[1]),.complete_ready(q_complete_ready[1]),.complete_data(q_completions[64+:64]),.cmd_valid(ep1_cmd_valid),.cmd_ready(ep1_cmd_ready),.cmd_op(ep1_cmd_op),.cmd_index(ep1_cmd_index),.cmd_data(ep1_cmd_data),.rsp_valid(ep1_rsp_valid),.rsp_ready(ep1_rsp_ready),.rsp_data(ep1_rsp_data),.rsp_error(ep1_rsp_error),.rsp_saturated(ep1_rsp_saturated),.s_req(mem_req[1]),.s_wr(mem_wr[1]),.s_addr(mem_addr[10+:10]),.s_din(mem_din[128+:128]),.s_ready(mem_ready[1]),.s_valid(mem_valid[1]),.s_take(mem_take[1]));
 wire  ep2_cmd_valid;
 wire  ep2_cmd_ready;
 wire [3:0] ep2_cmd_op;
 wire [3:0] ep2_cmd_count;
 wire [31:0] ep2_cmd_param;
 wire [127:0] ep2_cmd_data;
 wire [127:0] ep2_cmd_aux;
 wire  ep2_rsp_valid;
 wire  ep2_rsp_ready;
 wire [127:0] ep2_rsp_data;
 wire  ep2_rsp_error;
 wire  ep2_rsp_saturated;
 control_adapter_n endpoint_2(.clk(clk),.reset(reset),.task_valid(q_task_valid[2]),.task_ready(q_task_ready[2]),.task_data(q_tasks[512+:256]),.complete_valid(q_complete_valid[2]),.complete_ready(q_complete_ready[2]),.complete_data(q_completions[128+:64]),.s_req(mem_req[2]),.s_wr(mem_wr[2]),.s_addr(mem_addr[20+:10]),.s_din(mem_din[256+:128]),.s_ready(mem_ready[2]),.s_valid(mem_valid[2]),.s_take(mem_take[2]),.s_dout(mem_dout),.cmd_valid(ep2_cmd_valid),.cmd_ready(ep2_cmd_ready),.cmd_op(ep2_cmd_op),.cmd_count(ep2_cmd_count),.cmd_param(ep2_cmd_param),.cmd_data(ep2_cmd_data),.cmd_aux(ep2_cmd_aux),.rsp_valid(ep2_rsp_valid),.rsp_ready(ep2_rsp_ready),.rsp_data(ep2_rsp_data),.rsp_error(ep2_rsp_error),.rsp_saturated(ep2_rsp_saturated));
 wire  ep3_in_valid;
 wire  ep3_in_ready;
 wire [3:0] ep3_in_op;
 wire [4:0] ep3_in_shift;
 wire [127:0] ep3_in_a;
 wire [127:0] ep3_in_b;
 wire [127:0] ep3_in_c;
 wire  ep3_out_valid;
 wire  ep3_out_ready;
 wire [127:0] ep3_out_data;
 wire  ep3_out_error;
 wire  ep3_out_saturated;
 control_adapter_e endpoint_3(.clk(clk),.reset(reset),.task_valid(q_task_valid[3]),.task_ready(q_task_ready[3]),.task_data(q_tasks[768+:256]),.complete_valid(q_complete_valid[3]),.complete_ready(q_complete_ready[3]),.complete_data(q_completions[192+:64]),.s_req(mem_req[3]),.s_wr(mem_wr[3]),.s_addr(mem_addr[30+:10]),.s_din(mem_din[384+:128]),.s_ready(mem_ready[3]),.s_valid(mem_valid[3]),.s_take(mem_take[3]),.s_dout(mem_dout),.in_valid(ep3_in_valid),.in_ready(ep3_in_ready),.in_op(ep3_in_op),.in_shift(ep3_in_shift),.in_a(ep3_in_a),.in_b(ep3_in_b),.in_c(ep3_in_c),.out_valid(ep3_out_valid),.out_ready(ep3_out_ready),.out_data(ep3_out_data),.out_error(ep3_out_error),.out_saturated(ep3_out_saturated));
 wire  ep4_in_valid;
 wire  ep4_in_ready;
 wire [2:0] ep4_in_fn;
 wire  ep4_in_gated;
 wire [31:0] ep4_in_x;
 wire [31:0] ep4_in_gate;
 wire  ep4_out_valid;
 wire  ep4_out_ready;
 wire [31:0] ep4_out_data;
 wire  ep4_out_error;
 wire  ep4_out_saturated;
 control_adapter_g endpoint_4(.clk(clk),.reset(reset),.task_valid(q_task_valid[4]),.task_ready(q_task_ready[4]),.task_data(q_tasks[1024+:256]),.complete_valid(q_complete_valid[4]),.complete_ready(q_complete_ready[4]),.complete_data(q_completions[256+:64]),.s_req(mem_req[4]),.s_wr(mem_wr[4]),.s_addr(mem_addr[40+:10]),.s_din(mem_din[512+:128]),.s_ready(mem_ready[4]),.s_valid(mem_valid[4]),.s_take(mem_take[4]),.s_dout(mem_dout),.in_valid(ep4_in_valid),.in_ready(ep4_in_ready),.in_fn(ep4_in_fn),.in_gated(ep4_in_gated),.in_x(ep4_in_x),.in_gate(ep4_in_gate),.out_valid(ep4_out_valid),.out_ready(ep4_out_ready),.out_data(ep4_out_data),.out_error(ep4_out_error),.out_saturated(ep4_out_saturated));
 wire  ep5_load_valid;
 wire  ep5_load_ready;
 wire  ep5_load_bank;
 wire [3:0] ep5_load_rows;
 wire [2:0] ep5_load_tiles;
 wire  ep5_load_a_wide;
 wire  ep5_load_b_wide;
 wire  ep5_load_reuse_b;
 wire [9:0] ep5_load_a_base;
 wire [9:0] ep5_load_b_base;
 wire  ep5_done_valid;
 wire  ep5_done_take;
 wire  ep5_done_error;
 control_adapter_s endpoint_5(.clk(clk),.reset(reset),.task_valid(q_task_valid[5]),.task_ready(q_task_ready[5]),.task_data(q_tasks[1280+:256]),.complete_valid(q_complete_valid[5]),.complete_ready(q_complete_ready[5]),.complete_data(q_completions[320+:64]),.load_valid(ep5_load_valid),.load_ready(ep5_load_ready),.load_bank(ep5_load_bank),.load_rows(ep5_load_rows),.load_tiles(ep5_load_tiles),.load_a_wide(ep5_load_a_wide),.load_b_wide(ep5_load_b_wide),.load_reuse_b(ep5_load_reuse_b),.load_a_base(ep5_load_a_base),.load_b_base(ep5_load_b_base),.done_valid(ep5_done_valid),.done_take(ep5_done_take),.done_error(ep5_done_error));
 wire  ep6_begin_valid;
 wire  ep6_begin_ready;
 wire [1:0] ep6_begin_owner;
 wire [31:0] ep6_begin_generation;
 wire [9:0] ep6_begin_words;
 wire  ep6_write_valid;
 wire  ep6_write_ready;
 wire [9:0] ep6_write_index;
 wire [127:0] ep6_write_data;
 wire  ep6_commit_valid;
 wire  ep6_commit_ready;
 wire  ep6_revoke_valid;
 wire  ep6_revoke_ready;
 wire  ep6_read_valid;
 wire  ep6_read_take;
 wire [9:0] ep6_read_index;
 wire [127:0] ep6_read_data;
 wire  ep6_read_last;
 wire  ep6_release_valid;
 wire  ep6_release_ready;
 wire  ep6_t_busy;
 wire  ep6_t_sealed;
 wire  ep6_t_committed;
 wire  ep6_t_error;
 control_adapter_t endpoint_6(.clk(clk),.reset(reset),.task_valid(q_task_valid[6]),.task_ready(q_task_ready[6]),.task_data(q_tasks[1536+:256]),.complete_valid(q_complete_valid[6]),.complete_ready(q_complete_ready[6]),.complete_data(q_completions[384+:64]),.begin_valid(ep6_begin_valid),.begin_ready(ep6_begin_ready),.begin_owner(ep6_begin_owner),.begin_generation(ep6_begin_generation),.begin_words(ep6_begin_words),.write_valid(ep6_write_valid),.write_ready(ep6_write_ready),.write_index(ep6_write_index),.write_data(ep6_write_data),.commit_valid(ep6_commit_valid),.commit_ready(ep6_commit_ready),.revoke_valid(ep6_revoke_valid),.revoke_ready(ep6_revoke_ready),.read_valid(ep6_read_valid),.read_take(ep6_read_take),.read_index(ep6_read_index),.read_data(ep6_read_data),.read_last(ep6_read_last),.release_valid(ep6_release_valid),.release_ready(ep6_release_ready),.t_busy(ep6_t_busy),.t_sealed(ep6_t_sealed),.t_committed(ep6_t_committed),.t_error(ep6_t_error),.s_req(mem_req[5]),.s_wr(mem_wr[5]),.s_addr(mem_addr[50+:10]),.s_din(mem_din[640+:128]),.s_ready(mem_ready[5]),.s_valid(mem_valid[5]),.s_take(mem_take[5]),.s_dout(mem_dout));
 assign protocol_error=(|q_error)||ep0_protocol_error||ep6_t_error;
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
 wire  unused_1_busy;
 block_v2_m macro_1(.clk(clk),.reset(reset),.a_valid(feed_a_valid),.a_ready(feed_a_ready),.a_bank(feed_a_bank),.a_row(feed_a_row),.a_tile(feed_a_tile),.a_wide(feed_a_wide),.a_data(feed_a_data),.b_valid(feed_b_valid),.b_ready(feed_b_ready),.b_bank(feed_b_bank),.b_tile(feed_b_tile),.b_wide(feed_b_wide),.b_half(feed_b_half),.b_data(feed_b_data),.cmd_valid(ep1_cmd_valid),.cmd_ready(ep1_cmd_ready),.cmd_op(ep1_cmd_op),.cmd_index(ep1_cmd_index),.cmd_data(ep1_cmd_data),.rsp_valid(ep1_rsp_valid),.rsp_ready(ep1_rsp_ready),.rsp_data(ep1_rsp_data),.rsp_error(ep1_rsp_error),.rsp_saturated(ep1_rsp_saturated),.busy(unused_1_busy));
 wire  unused_2_busy;
 block_v2_n macro_2(.clk(clk),.reset(reset),.cmd_valid(ep2_cmd_valid),.cmd_ready(ep2_cmd_ready),.cmd_op(ep2_cmd_op),.cmd_count(ep2_cmd_count),.cmd_param(ep2_cmd_param),.cmd_data(ep2_cmd_data),.cmd_aux(ep2_cmd_aux),.rsp_valid(ep2_rsp_valid),.rsp_ready(ep2_rsp_ready),.rsp_data(ep2_rsp_data),.rsp_error(ep2_rsp_error),.rsp_saturated(ep2_rsp_saturated),.busy(unused_2_busy));
 block_v2_e macro_3(.clk(clk),.reset(reset),.in_valid(ep3_in_valid),.in_ready(ep3_in_ready),.in_op(ep3_in_op),.in_shift(ep3_in_shift),.in_a(ep3_in_a),.in_b(ep3_in_b),.in_c(ep3_in_c),.out_valid(ep3_out_valid),.out_ready(ep3_out_ready),.out_data(ep3_out_data),.out_error(ep3_out_error),.out_saturated(ep3_out_saturated));
 block_v2_g macro_4(.clk(clk),.reset(reset),.in_valid(ep4_in_valid),.in_ready(ep4_in_ready),.in_fn(ep4_in_fn),.in_gated(ep4_in_gated),.in_x(ep4_in_x),.in_gate(ep4_in_gate),.out_valid(ep4_out_valid),.out_ready(ep4_out_ready),.out_data(ep4_out_data),.out_error(ep4_out_error),.out_saturated(ep4_out_saturated));
 wire  storage_req;
 wire  storage_wr;
 wire [9:0] storage_addr;
 wire [127:0] storage_din;
 wire  storage_ready;
 wire  storage_valid;
 wire  storage_take;
 wire [127:0] storage_dout;
 wire  unused_s_busy;
 block_feed_s_macro macro_s(.clk(clk),.reset(reset),.req(storage_req),.wr(storage_wr),.addr(storage_addr),.din(storage_din),.ready(storage_ready),.valid(storage_valid),.take(storage_take),.dout(storage_dout),.load_valid(ep5_load_valid),.load_ready(ep5_load_ready),.load_bank(ep5_load_bank),.load_rows(ep5_load_rows),.load_tiles(ep5_load_tiles),.load_a_wide(ep5_load_a_wide),.load_b_wide(ep5_load_b_wide),.load_reuse_b(ep5_load_reuse_b),.load_a_base(ep5_load_a_base),.load_b_base(ep5_load_b_base),.done_valid(ep5_done_valid),.done_take(ep5_done_take),.done_error(ep5_done_error),.busy(unused_s_busy),.a_valid(feed_a_valid),.a_ready(feed_a_ready),.a_bank(feed_a_bank),.a_row(feed_a_row),.a_tile(feed_a_tile),.a_wide(feed_a_wide),.a_data(feed_a_data),.b_valid(feed_b_valid),.b_ready(feed_b_ready),.b_bank(feed_b_bank),.b_tile(feed_b_tile),.b_wide(feed_b_wide),.b_half(feed_b_half),.b_data(feed_b_data));
 control_s_arbiter s_port(.clk(clk),.reset(reset),.req(mem_req),.wr(mem_wr),.addr(mem_addr),.din(mem_din),.ready(mem_ready),.valid(mem_valid),.take(mem_take),.dout(mem_dout),.s_req(storage_req),.s_wr(storage_wr),.s_addr(storage_addr),.s_din(storage_din),.s_ready(storage_ready),.s_valid(storage_valid),.s_take(storage_take),.s_dout(storage_dout));
 wire [1:0] unused_t_owner;
 wire [31:0] unused_t_generation;
 wire [9:0] unused_t_word_count;
 wire [2:0] unused_t_debug_state;
 transaction6k macro_t(.clk(clk),.reset(reset),.begin_valid(ep6_begin_valid),.begin_ready(ep6_begin_ready),.begin_owner(ep6_begin_owner),.begin_generation(ep6_begin_generation),.begin_words(ep6_begin_words),.write_valid(ep6_write_valid),.write_ready(ep6_write_ready),.write_index(ep6_write_index),.write_data(ep6_write_data),.commit_valid(ep6_commit_valid),.commit_ready(ep6_commit_ready),.revoke_valid(ep6_revoke_valid),.revoke_ready(ep6_revoke_ready),.read_valid(ep6_read_valid),.read_take(ep6_read_take),.read_index(ep6_read_index),.read_data(ep6_read_data),.read_last(ep6_read_last),.owner(unused_t_owner),.generation(unused_t_generation),.word_count(unused_t_word_count),.release_valid(ep6_release_valid),.release_ready(ep6_release_ready),.busy(ep6_t_busy),.sealed(ep6_t_sealed),.committed(ep6_t_committed),.protocol_error(ep6_t_error),.debug_state(unused_t_debug_state));
 wire unused_dma_instance=&{1'b0,ep0_s_instance};
endmodule
