module w8_dot_candidate #(parameter integer ABITS=8,AW=(ABITS==8?32:40))(
 input wire clk,reset,
 input wire cmd_valid,output wire cmd_ready,
 input wire [2:0] cmd_ctx,input wire cmd_first,cmd_last,
 input wire [4:0] cmd_k,input wire [3:0] cmd_n,input wire [15:0] cmd_offset,
 input wire [16*ABITS-1:0] cmd_a,
 input wire dma_valid,output wire dma_ready,input wire [511:0] dma_data,
 output wire fill_ack,
 output wire out_valid,input wire out_ready,output wire [2:0] out_ctx,
 output wire [8*AW-1:0] out_data,output wire out_error
);
 wire mv,mr,mf,ml;wire [2:0] mc;wire [4:0] mk;wire [3:0] mn;wire [15:0] mo;
 wire [16*ABITS-1:0] ma;wire [1023:0] mb;
 w8_weight_buffer #(.ABITS(ABITS)) buffer_i(.clk,.reset,.cmd_valid,.cmd_ready,.cmd_ctx,.cmd_first,.cmd_last,.cmd_k,.cmd_n,.cmd_offset,.cmd_a,
  .dma_valid,.dma_ready,.dma_data,.fill_ack,.m_valid(mv),.m_ready(mr),.m_ctx(mc),.m_first(mf),.m_last(ml),.m_k(mk),.m_n(mn),.m_offset(mo),.m_a(ma),.m_b(mb));
 w8_stream_mac #(.ABITS(ABITS),.AW(AW)) mac_i(.clk,.reset,.in_valid(mv),.in_ready(mr),.in_ctx(mc),.in_first(mf),.in_last(ml),.in_k(mk),.in_n(mn),.in_offset(mo),.in_a(ma),.in_b(mb),.out_valid,.out_ready,.out_ctx,.out_data,.out_error);
endmodule
