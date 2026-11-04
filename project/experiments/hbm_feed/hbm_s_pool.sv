// Verification composition: sixteen real private S macros and one shared M
// numeric verifier. This does not claim sixteen parallel compute blocks.
module hbm_s_pool #(parameter integer NS=16,LGDEPTH=4)(
 input wire core_clk,mem_clk,reset,
 input wire [NS-1:0] in_valid,out_ready,hold_core,
 output wire [NS-1:0] in_ready,out_valid,
 input wire [154:0] in_data[NS],output wire [154:0] out_data[NS],
 input wire [3:0] select_s,input wire load_valid,output wire load_ready,
 input wire done_take,output wire done_valid,done_error,
 input wire a_allow,b_allow,
 input wire cmd_valid,output wire cmd_ready,input wire [3:0] cmd_op,
 input wire [5:0] cmd_index,input wire [63:0] cmd_data,
 output wire rsp_valid,input wire rsp_ready,output wire [127:0] rsp_data,
 output wire rsp_error,rsp_saturated,output wire [NS-1:0] a_fire,b_fire
);
 wire [NS-1:0] lr,dv,de,av,ar,ab,aw,bv,br,bb,bw,bh;
 wire [2:0] row[NS];wire [1:0] atile[NS],btile[NS];
 wire [127:0] adata[NS];wire [511:0] bdata[NS];
 wire ma_ready,mb_ready,unused_busy;
 assign load_ready=lr[select_s];assign done_valid=dv[select_s];assign done_error=de[select_s];
 for(genvar i=0;i<NS;i=i+1)begin: ports
  assign ar[i]=(select_s==4'(i))&&ma_ready&&a_allow;
  assign br[i]=(select_s==4'(i))&&mb_ready&&b_allow;
  assign a_fire[i]=av[i]&&ar[i];assign b_fire[i]=bv[i]&&br[i];
  hbm_s_endpoint #(.LGDEPTH(LGDEPTH)) endpoint(
   .core_clk(core_clk),.mem_clk(mem_clk),.reset(reset),.hold_core(hold_core[i]),
   .in_valid(in_valid[i]),.in_ready(in_ready[i]),.in_data(in_data[i]),
   .out_valid(out_valid[i]),.out_ready(out_ready[i]),.out_data(out_data[i]),
   .load_valid(load_valid&&(select_s==4'(i))),.load_ready(lr[i]),
   .done_take(done_take&&(select_s==4'(i))),.done_valid(dv[i]),.done_error(de[i]),
   .a_valid(av[i]),.a_ready(ar[i]),.a_bank(ab[i]),.a_row(row[i]),.a_tile(atile[i]),.a_wide(aw[i]),.a_data(adata[i]),
   .b_valid(bv[i]),.b_ready(br[i]),.b_bank(bb[i]),.b_tile(btile[i]),.b_wide(bw[i]),.b_half(bh[i]),.b_data(bdata[i]));
 end
 block_v2_m matrix(
  .clk(core_clk),.reset(reset),
  .a_valid(av[select_s]&&a_allow),.a_ready(ma_ready),.a_bank(ab[select_s]),
  .a_row(row[select_s]),.a_tile(atile[select_s]),.a_wide(aw[select_s]),.a_data(adata[select_s]),
  .b_valid(bv[select_s]&&b_allow),.b_ready(mb_ready),.b_bank(bb[select_s]),
  .b_tile(btile[select_s]),.b_wide(bw[select_s]),.b_half(bh[select_s]),.b_data(bdata[select_s]),
  .cmd_valid(cmd_valid),.cmd_ready(cmd_ready),.cmd_op(cmd_op),.cmd_index(cmd_index),.cmd_data(cmd_data),
  .rsp_valid(rsp_valid),.rsp_ready(rsp_ready),.rsp_data(rsp_data),.rsp_error(rsp_error),
  .rsp_saturated(rsp_saturated),.busy(unused_busy));
endmodule
