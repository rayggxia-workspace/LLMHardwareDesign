// Issue247 optional bank-concurrent local S. Capacity stays 16KiB.
// Default mode preserves the existing memory/feeder phase contract.
module local_s_p #(
 parameter bit ENABLE_BANK_RW=1'b0,
 parameter bit ENABLE_REUSE_A=1'b0,
 parameter bit ENABLE_SHARED_A=1'b0,
 parameter bit ENABLE_TRUE_RW=1'b0
) (
 input wire clk,reset,cold_reset,
 input wire wide_write_req,input wire [7:0] wide_write_addr,
 input wire [511:0] wide_write_data,input wire [3:0] wide_write_mask,
 output wire wide_write_ready,wide_write_valid,input wire wide_write_take,
 input wire req_valid,req_write,input wire [9:0] req_addr,input wire [127:0] req_data,
 output wire req_ready,rsp_valid,input wire rsp_ready,output wire [127:0] rsp_data,
 input wire load_valid,load_bank,load_a_wide,load_b_wide,load_reuse_b,
 input wire load_skip_a,
 input wire [3:0] load_rows,input wire [2:0] load_tiles,
 input wire [9:0] load_a_base,load_b_base,
 output wire load_ready,done_valid,done_error,
 input wire done_take,a_ready,b_ready,
 output wire a_valid,a_bank,a_wide,b_valid,b_bank,b_wide,b_half,
 output wire [2:0] a_row,output wire [1:0] a_tile,b_tile,
 output wire [127:0] a_data,output wire [511:0] b_data
`ifdef USE_POWER_PINS
 ,inout wire vdd,gnd
`endif
);
 wire effective_reset=reset||(ENABLE_TRUE_RW&&cold_reset);
 wire memory_ready,loader_ready,loader_busy,loader_done,loader_error;
 wire skip_a_enabled=ENABLE_SHARED_A&&load_skip_a;
 wire concurrent_enabled=ENABLE_BANK_RW||ENABLE_TRUE_RW;
 wire raw_write_ready;
 reg [1:0] write_outstanding;
 wire wide_req,wide_ready,wide_valid,wide_take;
 wire [7:0] wide_addr;wire [511:0] wide_data;
 reg [1:0] outstanding;
 reg lease;
 reg [10:0] a_first,a_end,b_first,b_end;
 wire [10:0] address={1'b0,req_addr};
 wire protected_a=address>=a_first&&address<a_end;
 wire protected_b=address>=b_first&&address<b_end;
 wire protected_write=concurrent_enabled&&lease&&req_write&&(protected_a||protected_b);
 wire [10:0] wide_word_base={1'b0,wide_write_addr,2'b00};
 wire [3:0] protected_lanes;
 for(genvar lane=0;lane<4;lane=lane+1)begin: protect_wide
  wire [10:0] wa=wide_word_base+11'(lane);
  assign protected_lanes[lane]=wide_write_mask[lane]&&lease&&
       ((wa>=a_first&&wa<a_end)||(wa>=b_first&&wa<b_end));
 end
 // New load still wins an idle boundary. Once accepted, bank mode permits
 // ordinary traffic except writes into any still-owned input range.
 wire start_boundary=load_valid&&!loader_busy&&!loader_done&&outstanding==0&&write_outstanding==0;
 wire ordinary_enabled=(concurrent_enabled||(!loader_busy&&!loader_done))&&!start_boundary&&!protected_write;
 wire write_enabled=ENABLE_TRUE_RW&&!effective_reset&&!load_valid&&!start_boundary&&!(|protected_lanes);
 assign wide_write_ready=write_enabled&&raw_write_ready;
 wire load_enabled=outstanding==0&&write_outstanding==0;
 assign req_ready=ordinary_enabled&&memory_ready;
 assign load_ready=load_enabled&&loader_ready;
 assign done_valid=!effective_reset&&loader_done;assign done_error=!effective_reset&&loader_error;
 always @(posedge clk)begin
  if(effective_reset)begin outstanding<=0;write_outstanding<=0;lease<=0;a_first<=0;a_end<=0;b_first<=0;b_end<=0;end
  else begin
   case({wide_write_req&&wide_write_ready,wide_write_valid&&wide_write_take})
    2'b10:write_outstanding<=write_outstanding+1'b1;
    2'b01:write_outstanding<=write_outstanding-1'b1;
    default:begin end
   endcase
   case({req_valid&&req_ready,rsp_valid&&rsp_ready})
    2'b10:outstanding<=outstanding+1'b1;
    2'b01:outstanding<=outstanding-1'b1;
    default:begin end
   endcase
   if(load_valid&&load_ready)begin
    lease<=1;a_first<={1'b0,load_a_base};b_first<={1'b0,load_b_base};
    a_end<={1'b0,load_a_base}+((load_rows==0||skip_a_enabled)?11'd0:({8'b0,load_tiles}<<(load_rows>4?3:2)));
    b_end<={1'b0,load_b_base}+(load_reuse_b?11'd0:({8'b0,load_tiles}<<(load_b_wide?3:2)));
   end
   if(done_valid&&done_take)lease<=0;
  end
 end
 generate if(ENABLE_TRUE_RW)begin: true_rw
  block_feed_s16k_1r1w #(.ECHO_WRITE_DATA(1'b0)) storage(
   .clk,.reset,.cold_reset,
   .req(req_valid&&ordinary_enabled),.wr(req_write),.addr(req_addr),.din(req_data),.ready(memory_ready),
   .valid(rsp_valid),.take(rsp_ready),.dout(rsp_data),
   .wide_req,.wide_addr,.wide_ready,.wide_valid,.wide_take,.wide_dout(wide_data),
   .wide_write_req(wide_write_req&&write_enabled),.wide_write_addr,.wide_write_data,.wide_write_mask,
   .wide_write_ready(raw_write_ready),.wide_write_valid,.wide_write_take
`ifdef USE_POWER_PINS
   ,.vdd,.gnd
`endif
  );
 end else if(ENABLE_BANK_RW)begin: concurrent_banks
  assign raw_write_ready=1'b0;assign wide_write_valid=1'b0;
  block_feed_s16k_bank_rw #(.ECHO_WRITE_DATA(1'b0)) storage(
   .clk,.reset,.req(req_valid&&ordinary_enabled),.wr(req_write),.addr(req_addr),.din(req_data),.ready(memory_ready),
   .valid(rsp_valid),.take(rsp_ready),.dout(rsp_data),
   .wide_req,.wide_addr,.wide_ready,.wide_valid,.wide_take,.wide_dout(wide_data)
`ifdef USE_POWER_PINS
   ,.vdd,.gnd
`endif
  );
 end else begin: compatible
  assign raw_write_ready=1'b0;assign wide_write_valid=1'b0;
  block_feed_s16k_sram #(.ECHO_WRITE_DATA(1'b0)) storage(
   .clk,.reset,.req(req_valid&&ordinary_enabled),.wr(req_write),.addr(req_addr),.din(req_data),.ready(memory_ready),
   .valid(rsp_valid),.take(rsp_ready),.dout(rsp_data),
   .wide_req,.wide_addr,.wide_ready,.wide_valid,.wide_take,.wide_dout(wide_data)
`ifdef USE_POWER_PINS
   ,.vdd,.gnd
`endif
  );
 end endgenerate
 // ENABLE_REUSE_A is passed only when requested, keeping an unchanged legacy
 // loader compilable for the default standalone memory validation.
 generate if(ENABLE_REUSE_A||ENABLE_SHARED_A)begin: reuse_a
  block_feed_loader #(.ENABLE_REUSE_A(ENABLE_REUSE_A),.ENABLE_SKIP_A(ENABLE_SHARED_A)) feeder(
   .clk,.reset(effective_reset),.load_valid(load_valid&&load_enabled),.load_ready(loader_ready),
   .load_bank,.load_rows,.load_tiles,.load_a_wide,.load_b_wide,.load_reuse_b,.load_a_base,.load_b_base,.load_skip_a(skip_a_enabled),
   .done_valid(loader_done),.done_take,.done_error(loader_error),.busy(loader_busy),
   .mem_req(wide_req),.mem_addr(wide_addr),.mem_ready(wide_ready),.mem_valid(wide_valid),.mem_take(wide_take),.mem_data(wide_data),
   .a_valid,.a_ready,.a_bank,.a_row,.a_tile,.a_wide,.a_data,.b_valid,.b_ready,.b_bank,.b_tile,.b_wide,.b_half,.b_data
  );
 end else begin: legacy_a
  block_feed_loader feeder(
   .load_skip_a(1'b0),.clk,.reset(effective_reset),.load_valid(load_valid&&load_enabled),.load_ready(loader_ready),
   .load_bank,.load_rows,.load_tiles,.load_a_wide,.load_b_wide,.load_reuse_b,.load_a_base,.load_b_base,
   .done_valid(loader_done),.done_take,.done_error(loader_error),.busy(loader_busy),
   .mem_req(wide_req),.mem_addr(wide_addr),.mem_ready(wide_ready),.mem_valid(wide_valid),.mem_take(wide_take),.mem_data(wide_data),
   .a_valid,.a_ready,.a_bank,.a_row,.a_tile,.a_wide,.a_data,.b_valid,.b_ready,.b_bank,.b_tile,.b_wide,.b_half,.b_data
  );
 end endgenerate
endmodule
