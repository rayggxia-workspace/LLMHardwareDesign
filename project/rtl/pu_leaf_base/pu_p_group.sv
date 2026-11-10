// P16 accepts native M commands and a two-lane gated SiLU service.
module pu_p_group #(
 parameter integer S_CONSUMER_PRIORITY = 0,
 parameter integer S_BANK_RW = 0,
 parameter integer M_CONTEXTS = 0,
 parameter integer SHARED_A = 0,
 parameter integer S_TRUE_RW = 0
) (
 input wire clk, reset,
 // Cold reset invalidates migrated local-S contents; assert with group reset
 // at power-up. Warm reset preserves locations and all accepted writes.
 input wire s_cold_reset,
 input wire wide_write_req,input wire [7:0] wide_write_addr,
 input wire [511:0] wide_write_data,input wire [3:0] wide_write_mask,
 output wire wide_write_ready,wide_write_valid,input wire wide_write_take,
 input wire load_a_shared,input wire [10:0] load_pool_base,input wire [7:0] load_pool_epoch,
 output wire pool_load_valid,input wire pool_load_ready,
 output wire [10:0] pool_load_base,output wire [7:0] pool_load_epoch,
 output wire pool_load_bank,pool_load_wide,output wire [3:0] pool_load_rows,
 output wire [2:0] pool_load_tiles,
 input wire pool_done_valid,pool_done_error,output wire pool_done_take,
 input wire pool_a_valid,output wire pool_a_ready,input wire pool_a_bank,pool_a_wide,
 input wire [2:0] pool_a_row,input wire [1:0] pool_a_tile,input wire [127:0] pool_a_data,
 input wire [1:0] io_req_valid, io_req_write,
 input wire [19:0] io_req_addr, input wire [255:0] io_req_data,
 output wire [1:0] io_req_ready, io_rsp_valid,
 input wire [1:0] io_rsp_ready, output wire [255:0] io_rsp_data,
 input wire load_valid, output wire load_ready,
 input wire load_bank, input wire [3:0] load_rows, input wire [2:0] load_tiles,
 input wire load_a_wide, load_b_wide, load_reuse_b,
 input wire [9:0] load_a_base, load_b_base,
 output reg load_done, input wire load_take, output reg load_error,
 input wire cmd_valid, output wire cmd_ready,
 input wire [3:0] cmd_op, input wire [5:0] cmd_index, input wire [63:0] cmd_data,
 input wire cmd_store, cmd_route, cmd_pack16, input wire [9:0] cmd_dst,
 output reg cmd_done, input wire cmd_take, output reg cmd_error, cmd_saturated,
 output reg [127:0] cmd_result,
 input wire gate_valid, gate_route, output wire gate_ready,
 input wire [9:0] gate_a, gate_b, gate_dst,
 output reg gate_done, input wire gate_take, output reg gate_error, gate_saturated,
 output reg m_to_g_valid, output reg [31:0] m_to_g_data, input wire m_to_g_take,
 input wire g_from_m_valid, input wire [31:0] g_from_m_data, output wire g_from_m_take
);
 reg reset_q;
 always @(posedge clk) reset_q<=reset||(S_TRUE_RW!=0&&s_cold_reset);
 wire a_valid,a_ready,a_bank,a_wide,b_valid,b_ready,b_bank,b_wide,b_half;
 wire [2:0] a_row;
 wire [1:0] a_tile,b_tile;
 wire [127:0] a_data,m_s_unused;
 wire [511:0] b_data;
 wire sa_valid,sa_ready,sa_bank,sa_wide,sb_valid,sb_ready,sb_bank,sb_wide,sb_half;
 wire [2:0] sa_row;
 wire [1:0] sa_tile,sb_tile;
 wire [127:0] sa_data;
 wire [511:0] sb_data;
 wire s_load_ready,s_load_done,s_load_error;
 reg load_inflight,load_send,shared_load,pool_send;
 reg [10:0] pool_base_q;reg [7:0] pool_epoch_q;
 reg [30:0] load_config;
 wire feed_empty=(shared_load ? !pool_a_valid : sa_ready) && sb_ready;
 wire s_load_take=s_load_done && feed_empty && (!shared_load||pool_done_valid);
 assign pool_load_valid=SHARED_A!=0&&!reset_q&&pool_send;
 assign pool_load_base=pool_base_q;assign pool_load_epoch=pool_epoch_q;
 assign pool_load_bank=load_config[30];assign pool_load_rows=load_config[29:26];
 assign pool_load_tiles=load_config[25:23];assign pool_load_wide=load_config[22];
 assign pool_done_take=SHARED_A!=0&&shared_load&&s_load_take;
 assign load_ready=!reset_q && !load_inflight && !load_done;
 always @(posedge clk) begin
  if(reset_q) begin
   load_inflight<=0; load_send<=0; load_done<=0; load_error<=0;
   shared_load<=0;pool_send<=0;pool_base_q<=0;pool_epoch_q<=0;
  end else begin
   if(load_done && load_take) load_done<=0;
   if(load_ready && load_valid) begin
    load_inflight<=1; load_send<=1;
    shared_load<=SHARED_A!=0&&load_a_shared;pool_send<=SHARED_A!=0&&load_a_shared;
    pool_base_q<=load_pool_base;pool_epoch_q<=load_pool_epoch;
    load_config<={load_bank,load_rows,load_tiles,load_a_wide,load_b_wide,load_reuse_b,load_a_base,load_b_base};
   end
   if(load_send && s_load_ready) load_send<=0;
   if(pool_load_valid&&pool_load_ready)pool_send<=0;
   if(s_load_take) begin
    load_inflight<=0; load_done<=1; load_error<=s_load_error||(shared_load&&pool_done_error);
   end
  end
 end
 wire local_a_valid,local_a_ready,local_a_bank,local_a_wide;
 wire [2:0] local_a_row;wire [1:0] local_a_tile;wire [127:0] local_a_data;
 assign local_a_ready=a_ready&&!shared_load;
 assign pool_a_ready=SHARED_A!=0&&!reset_q&&shared_load&&load_inflight&&a_ready;
 assign a_valid=shared_load ? (pool_a_valid&&load_inflight) : local_a_valid;
 assign {a_bank,a_row,a_tile,a_wide,a_data}=shared_load ?
       {pool_a_bank,pool_a_row,pool_a_tile,pool_a_wide,pool_a_data} :
       {local_a_bank,local_a_row,local_a_tile,local_a_wide,local_a_data};
 pj_feed_hold #(.WIDTH(135)) hold_a(
  .clk(clk),.reset(reset_q),.src_valid(sa_valid),.src_ready(sa_ready),
  .src_data({sa_bank,sa_row,sa_tile,sa_wide,sa_data}),
  .dst_valid(local_a_valid),.dst_ready(local_a_ready),.dst_data({local_a_bank,local_a_row,local_a_tile,local_a_wide,local_a_data}));
 pj_feed_hold #(.WIDTH(517)) hold_b(
  .clk(clk),.reset(reset_q),.src_valid(sb_valid),.src_ready(sb_ready),
  .src_data({sb_bank,sb_tile,sb_wide,sb_half,sb_data}),
  .dst_valid(b_valid),.dst_ready(b_ready),.dst_data({b_bank,b_tile,b_wide,b_half,b_data}));
 wire m_ready,m_valid,m_error,m_sat;
 wire [127:0] m_result,g_s_data;
 wire [1:0] local_req,local_write,local_ready,local_rsp,local_take;
 wire [19:0] local_addr;
 wire [255:0] local_data;
 wire m_store_done,g_s_done,g_ready,g_valid,g_error,g_sat;
 wire [31:0] g_result;
 reg m_pending,m_writes,m_commit,m_routes,m_pack,m_dispatch;
 reg [3:0] m_op; reg [5:0] m_index; reg [63:0] m_data;
 wire signed16_read=cmd_op==4'd5 && cmd_data[9:8]==2'd1;
 wire bad_route=(cmd_route && (cmd_store || !signed16_read)) ||
                (cmd_pack16 && (!cmd_store || !signed16_read));
 wire [63:0] packed_s16={cmd_result[111:96],cmd_result[79:64],cmd_result[47:32],cmd_result[15:0]};
 reg [9:0] m_dst,g_base_a,g_base_b,g_dst;
 reg [31:0] g_x,g_other;
 localparam G_IDLE=0, G_A=1, G_B=2, G_RUN=3, G_WAIT=4, G_STORE=5, G_ROUTE=6;
 reg [2:0] g_state;
 assign cmd_ready=!reset_q && !m_pending && !cmd_done && !m_to_g_valid;
 assign g_from_m_take=!reset_q && g_state==G_ROUTE;
 assign gate_ready=!reset_q && g_state==G_IDLE && !gate_done;
 pj_sram_client m_writeback(
  .clk(clk),.reset(reset_q),.start(m_commit),.idle(),.write_word(1'b1),
  .address(m_dst),.data(m_pack ? {64'b0,packed_s16} : cmd_result),.req_valid(local_req[1]),
  .req_write(local_write[1]),.req_addr(local_addr[19:10]),.req_data(local_data[255:128]),
  .req_ready(local_ready[1]),.rsp_valid(local_rsp[1]),.rsp_ready(local_take[1]),.done(m_store_done));
 pj_sram_client g_client(
  .clk(clk),.reset(reset_q),.start(g_state==G_A || g_state==G_B || g_state==G_STORE),
  .idle(),.write_word(g_state==G_STORE),
  .address(g_state==G_A ? g_base_a : g_state==G_B ? g_base_b : g_dst),
  .data({96'b0,g_x}),.req_valid(local_req[0]),.req_write(local_write[0]),
  .req_addr(local_addr[9:0]),.req_data(local_data[127:0]),.req_ready(local_ready[0]),
  .rsp_valid(local_rsp[0]),.rsp_ready(local_take[0]),.done(g_s_done));
 wire [1:0] mem_req,mem_write,mem_ready,mem_rsp,mem_take;
 wire [19:0] mem_addr;
 wire [255:0] mem_data,mem_result;
 for(genvar i=0;i<2;i=i+1) begin: boundary
  pj_mem_port #(.RESETLESS_PAYLOAD(1)) mem(
   .clk(clk),.reset(reset_q),.req_valid(io_req_valid[i]),.req_write(io_req_write[i]),
   .req_addr(io_req_addr[i*10+:10]),.req_data(io_req_data[i*128+:128]),.req_ready(io_req_ready[i]),
   .rsp_valid(io_rsp_valid[i]),.rsp_data(io_rsp_data[i*128+:128]),.rsp_ready(io_rsp_ready[i]),
   .s_req_valid(mem_req[i]),.s_req_write(mem_write[i]),.s_req_addr(mem_addr[i*10+:10]),
   .s_req_data(mem_data[i*128+:128]),.s_req_ready(mem_ready[i]),.s_rsp_valid(mem_rsp[i]),
   .s_rsp_data(mem_result[i*128+:128]),.s_rsp_ready(mem_take[i]));
 end
 wire store_req,store_write,store_ready,store_rsp,store_take;
 wire [9:0] store_addr;
 wire [127:0] store_data,store_result;
 wire store_load_valid,store_load_ready,store_done_valid,store_done_error,store_done_take;
 pu_p_store_control #(.CLIENTS(4), .ENABLE_BANK_RW(S_BANK_RW||S_TRUE_RW),
  .CONSUMER_PRIORITY(S_CONSUMER_PRIORITY), .CONSUMER_MASK(4'b1100)) store_control(
  .clk(clk),.reset(reset_q),.req_valid({local_req,mem_req}),
  .req_write({local_write,mem_write}),.req_addr({local_addr,mem_addr}),
  .req_data({local_data,mem_data}),.req_ready({local_ready,mem_ready}),
  .rsp_valid({local_rsp,mem_rsp}),.rsp_ready({local_take,mem_take}),
  .rsp_data({m_s_unused,g_s_data,mem_result}),
  .mem_req(store_req),.mem_write(store_write),.mem_addr(store_addr),.mem_data(store_data),
  .mem_ready(store_ready),.mem_valid(store_rsp),.mem_result(store_result),.mem_take(store_take),
  .load_valid(load_send),.load_ready(s_load_ready),
  .store_load_valid(store_load_valid),.store_load_ready(store_load_ready),
  .store_done_valid(store_done_valid),.store_done_error(store_done_error),.store_done_take(store_done_take),
  .load_done_valid(s_load_done),.load_done_error(s_load_error),.load_done_take(s_load_take));
 local_s_p #(.ENABLE_BANK_RW(S_BANK_RW),.ENABLE_TRUE_RW(S_TRUE_RW!=0),
  .ENABLE_SHARED_A(SHARED_A!=0),.ENABLE_REUSE_A(M_CONTEXTS != 0)) store(
  .cold_reset(s_cold_reset),.wide_write_req,.wide_write_addr,.wide_write_data,.wide_write_mask,
  .wide_write_ready,.wide_write_valid,.wide_write_take,.load_skip_a(shared_load),
  .clk(clk),.reset(reset_q),.req_valid(store_req),.req_write(store_write),
  .req_addr(store_addr),.req_data(store_data),.req_ready(store_ready),
  .rsp_valid(store_rsp),.rsp_ready(store_take),.rsp_data(store_result),
  .load_valid(store_load_valid),.load_ready(store_load_ready),.load_bank(load_config[30]),
  .load_rows(load_config[29:26]),.load_tiles(load_config[25:23]),.load_a_wide(load_config[22]),
  .load_b_wide(load_config[21]),.load_reuse_b(load_config[20]),.load_a_base(load_config[19:10]),
  .load_b_base(load_config[9:0]),
  .done_valid(store_done_valid),.done_take(store_done_take),.done_error(store_done_error),
  .a_valid(sa_valid),.a_ready(sa_ready),.a_bank(sa_bank),.a_row(sa_row),.a_tile(sa_tile),.a_wide(sa_wide),.a_data(sa_data),
  .b_valid(sb_valid),.b_ready(sb_ready),.b_bank(sb_bank),.b_tile(sb_tile),.b_wide(sb_wide),.b_half(sb_half),.b_data(sb_data));
 generate if(M_CONTEXTS != 0) begin: context_mode
 block_v2_m_context #(.CONTEXTS(M_CONTEXTS)) multiply(
  .clk(clk),.reset(reset_q),.a_valid(a_valid),.a_ready(a_ready),.a_bank(a_bank),.a_row(a_row),
  .a_tile(a_tile),.a_wide(a_wide),.a_data(a_data),.b_valid(b_valid),.b_ready(b_ready),
  .b_bank(b_bank),.b_tile(b_tile),.b_wide(b_wide),.b_half(b_half),.b_data(b_data),
  .cmd_valid(m_dispatch),.cmd_ready(m_ready),.cmd_op(m_op),
  .cmd_index(m_index),.cmd_data(m_data),.rsp_valid(m_valid),.rsp_ready(m_pending && !m_dispatch && !m_commit),
  .rsp_data(m_result),.rsp_error(m_error),.rsp_saturated(m_sat),.busy());
 end else begin: legacy_mode
 block_v2_m multiply(
  .clk(clk),.reset(reset_q),.a_valid(a_valid),.a_ready(a_ready),.a_bank(a_bank),.a_row(a_row),
  .a_tile(a_tile),.a_wide(a_wide),.a_data(a_data),.b_valid(b_valid),.b_ready(b_ready),
  .b_bank(b_bank),.b_tile(b_tile),.b_wide(b_wide),.b_half(b_half),.b_data(b_data),
  .cmd_valid(m_dispatch),.cmd_ready(m_ready),.cmd_op(m_op),
  .cmd_index(m_index),.cmd_data(m_data),.rsp_valid(m_valid),.rsp_ready(m_pending && !m_dispatch && !m_commit),
  .rsp_data(m_result),.rsp_error(m_error),.rsp_saturated(m_sat),.busy());
 end endgenerate
 block_v2_g gate(
  .clk(clk),.reset(reset_q),.in_valid(g_state==G_RUN),.in_ready(g_ready),
  .in_fn(3'd0),.in_gated(1'b1),.in_x(g_x),.in_gate(g_other),
  .out_valid(g_valid),.out_ready(g_state==G_WAIT),.out_data(g_result),
  .out_error(g_error),.out_saturated(g_sat));
 always @(posedge clk) begin
  if(reset_q) begin
   m_pending<=0; m_commit<=0; m_dispatch<=0; m_to_g_valid<=0; cmd_done<=0; cmd_error<=0; cmd_saturated<=0;
   g_state<=G_IDLE; gate_done<=0; gate_error<=0; gate_saturated<=0;
  end else begin
   if(cmd_done && cmd_take) cmd_done<=0;
   if(m_to_g_valid && m_to_g_take) m_to_g_valid<=0;
   if(cmd_valid && cmd_ready) begin
    if(bad_route) begin cmd_done<=1; cmd_error<=1; cmd_saturated<=0; cmd_result<=0; end
    else begin
     m_pending<=1; m_dispatch<=1; m_writes<=cmd_store; m_routes<=cmd_route;
     m_pack<=cmd_pack16; m_dst<=cmd_dst;
     m_op<=cmd_op; m_index<=cmd_index; m_data<=cmd_data;
    end
   end
   if(m_dispatch && m_ready) m_dispatch<=0;
   if(m_pending && !m_dispatch && !m_commit && m_valid) begin
    cmd_result<=m_result; cmd_error<=m_error; cmd_saturated<=m_sat;
    if(m_routes && !m_error) begin m_to_g_data<={m_result[47:32],m_result[15:0]}; m_to_g_valid<=1; end
    if(m_writes && !m_error) m_commit<=1;
    else begin cmd_done<=1; m_pending<=0; end
   end
   if(m_store_done) begin m_commit<=0; cmd_done<=1; m_pending<=0; end
   if(gate_done && gate_take) gate_done<=0;
   case(g_state)
    G_IDLE: if(gate_valid && gate_ready) begin
     g_base_a<=gate_a; g_base_b<=gate_b; g_dst<=gate_dst; g_state<=gate_route ? G_ROUTE : G_A;
    end
    G_ROUTE: if(g_from_m_valid) begin g_x<=g_from_m_data; g_state<=G_B; end
    G_A: if(g_s_done) begin g_x<=g_s_data[31:0]; g_state<=G_B; end
    G_B: if(g_s_done) begin g_other<=g_s_data[31:0]; g_state<=G_RUN; end
    G_RUN: if(g_ready) g_state<=G_WAIT;
    G_WAIT: if(g_valid) begin
     g_x<=g_result; gate_error<=g_error; gate_saturated<=g_sat;
     if(g_error) begin gate_done<=1; g_state<=G_IDLE; end
     else g_state<=G_STORE;
    end
    G_STORE: if(g_s_done) begin gate_done<=1; g_state<=G_IDLE; end
    default: g_state<=G_IDLE;
   endcase
  end
 end
endmodule
