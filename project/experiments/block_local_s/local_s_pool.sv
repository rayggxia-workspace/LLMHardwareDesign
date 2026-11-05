// Structural integration fixture: P0/P1/P2, U0/U1, C0, F0, J0/J1.
// Each instance contains its own real 16KiB storage and arbiter. Fifth client
// exists only on C. These are protocol peers, not full compute macro models.
module local_s_pool(
 input wire clk,input wire [8:0] reset,
 input wire [44:0] req_valid,req_write,rsp_ready,
 input wire [449:0] req_addr,input wire [5759:0] req_data,
 output wire [44:0] req_ready,rsp_valid,output wire [5759:0] rsp_data,
 input wire [8:0] load_valid,load_bank,load_a_wide,load_b_wide,load_reuse_b,
 input wire [35:0] load_rows,input wire [26:0] load_tiles,
 input wire [89:0] load_a_base,load_b_base,
 output wire [8:0] load_ready,done_valid,done_error,busy,
 input wire [8:0] done_take,a_ready,b_ready,
 output wire [8:0] a_valid,a_bank,a_wide,b_valid,b_bank,b_wide,b_half,
 output wire [26:0] a_row,output wire [17:0] a_tile,b_tile,
 output wire [1151:0] a_data,output wire [4607:0] b_data
);
 generate for(genvar b=0;b<9;b=b+1) begin: blocks
  localparam integer N=b==5 ? 5 : 4;
  block_local_s_macro #(.CLIENTS(N),.WITH_FEEDER(b<3)) private_s(
   .clk(clk),.reset(reset[b]),
   .req_valid(req_valid[b*5+:N]),.req_write(req_write[b*5+:N]),
   .req_addr(req_addr[b*50+:N*10]),.req_data(req_data[b*640+:N*128]),
   .req_ready(req_ready[b*5+:N]),.rsp_valid(rsp_valid[b*5+:N]),
   .rsp_ready(rsp_ready[b*5+:N]),.rsp_data(rsp_data[b*640+:N*128]),
   .load_valid(load_valid[b]),.load_ready(load_ready[b]),
   .load_bank(load_bank[b]),.load_rows(load_rows[b*4+:4]),.load_tiles(load_tiles[b*3+:3]),
   .load_a_wide(load_a_wide[b]),.load_b_wide(load_b_wide[b]),.load_reuse_b(load_reuse_b[b]),
   .load_a_base(load_a_base[b*10+:10]),.load_b_base(load_b_base[b*10+:10]),
   .done_valid(done_valid[b]),.done_take(done_take[b]),.done_error(done_error[b]),.busy(busy[b]),
   .a_valid(a_valid[b]),.a_ready(a_ready[b]),.a_bank(a_bank[b]),.a_row(a_row[b*3+:3]),
   .a_tile(a_tile[b*2+:2]),.a_wide(a_wide[b]),.a_data(a_data[b*128+:128]),
   .b_valid(b_valid[b]),.b_ready(b_ready[b]),.b_bank(b_bank[b]),.b_tile(b_tile[b*2+:2]),
   .b_wide(b_wide[b]),.b_half(b_half[b]),.b_data(b_data[b*512+:512]));
  if(N==4) begin: unused_client
   assign req_ready[b*5+4]=0;
   assign rsp_valid[b*5+4]=0;
   assign rsp_data[b*640+512+:128]=0;
  end
 end endgenerate
endmodule
