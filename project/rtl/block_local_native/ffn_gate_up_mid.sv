`timescale 1ns/1ps
// Logical FFN service group, never a physical Block boundary. The S ports
// remain the three independent P.S native adapters. G is a separate leaf.
// Stripe commit comes from actual scatter completions; Mid descriptor is
// published only after all 16 writes to the selected P.S are acknowledged.
module ffn_gate_up_mid #(
 parameter integer TOTAL_COLUMNS=11008
)(
 input wire clk,reset,
 input wire start_valid,output wire start_ready,input wire [63:0] start_owner,
 output wire stripe_valid,input wire stripe_ready,output wire [63:0] stripe_owner,
 output wire [15:0] stripe_first,output wire [7:0] stripe_width,
 input wire stripe_commit_valid,output wire stripe_commit_ready,
 input wire [63:0] stripe_commit_owner,input wire [15:0] stripe_commit_first,
 input wire stripe_commit_error,
 output wire [2:0] s_valid,s_write,input wire [2:0] s_ready,
 output wire [29:0] s_address,output wire [383:0] s_data,output wire [95:0] s_tag,
 input wire [2:0] s_rsp_valid,output wire [2:0] s_rsp_ready,
 input wire [383:0] s_rsp_data,input wire [95:0] s_rsp_tag,
 output wire mid_valid,input wire mid_ready,
 output wire [63:0] mid_owner,output wire [15:0] mid_first,
 output wire [1:0] mid_destination,output wire [9:0] mid_destination_base,
 output wire [5:0] mid_shift,
 output wire done_valid,input wire done_ready,output wire done_error,
 output wire [31:0] rejected_commits
);
 wire g_valid,g_ready,g_done,g_take,g_error;
 wire [9:0] g_gate_base,g_up_base,g_mid_base;
 wire [5:0] g_words,g_shift,q_shift;
 wire [127:0] g_key;
 wire [15:0] g_first;
 wire mid_cmd,mid_cmd_ready,q_done,q_take,q_error,q_cancelled;
 wire [15:0] q_first;
 wire [127:0] q_key;
 wire [4:0] q_words;
 wire [15:0] q_mask;
 wire [31:0] q_rejected;
 reg [15:0] quant_epoch;
 reg [5:0] max_shift;
 reg g_active,quant_fail;
 wire [63:0] mid_job_owner;
 wire [127:0] expected_key={mid_job_owner,64'h4d49445f41313600};
 wire q_bad=q_error||q_cancelled||q_words!=5'd16||q_mask!=16'hffff||
    q_key!=expected_key||q_first!=mid_first;
 // No new work is offered while an old result remains visible. A quiescent
 // namespace rearm is a separate integration requirement before 16-bit wrap.
 wire quant_exhausted=quant_epoch==16'hffff;
 assign mid_valid=q_done&&!q_bad;
 assign mid_owner=mid_job_owner;
 assign mid_shift=q_shift;
 wire mid_result_ready;
 assign q_take=mid_result_ready&&(q_bad||mid_ready);
 ffn_gate_up_ring_control #(.TOTAL_COLUMNS(TOTAL_COLUMNS)) schedule(.clk,.reset,
  .start_valid,.start_ready,.start_owner,.stripe_valid,.stripe_ready,.stripe_owner,.stripe_first,.stripe_width,
  .stripe_commit_valid,.stripe_commit_ready,.stripe_commit_owner,.stripe_commit_first,.stripe_commit_error,
  .g_valid,.g_ready,.g_gate_base,.g_up_base,.g_mid_base,.g_commit_valid(g_done),.g_commit_ready(g_take),
  .g_commit_error(g_error||g_key!=expected_key||g_first!=mid_first),.g_commit_words(g_words),
  .mid_valid(mid_cmd),.mid_ready(quant_exhausted||mid_cmd_ready),.mid_job_owner,.mid_first,.mid_destination,.mid_destination_base,
  .mid_commit_valid(q_done&&(q_bad||mid_ready)||quant_fail),
  .mid_commit_ready(mid_result_ready),.mid_commit_owner(mid_job_owner),.mid_commit_first(mid_first),
  .mid_commit_error(q_bad||quant_fail),.done_valid,.done_ready,.done_error,.rejected_commits);

 wire gs_valid,gs_write,gs_rsp_ready;
 wire [9:0] gs_address;
 wire [127:0] gs_data;
 wire gin,gin_ready,gout,gout_ready,gated,gout_error;
 wire [63:0] gate,up,value;
 wire [1:0] gin_mask,gout_mask;
 g_s128_observed_scale g_adapter(.clk,.reset,.cmd_key(expected_key),.cmd_kk(mid_first),
  .cmd_valid(g_valid),.cmd_ready(g_ready),.cmd_gate_base(g_gate_base),.cmd_up_base(g_up_base),.cmd_mid_base(g_mid_base),
  .cmd_words(6'd16),.cmd_gated(1'b1),.done_valid(g_done),.done_take(g_take),.done_key(g_key),.done_kk(g_first),
  .done_error(g_error),.done_words(g_words),.done_a_shift(g_shift),
  .s_req_valid(gs_valid),.s_req_write(gs_write),.s_req_addr(gs_address),.s_req_data(gs_data),
  .s_req_ready(s_ready[0]&&g_active),.s_rsp_valid(s_rsp_valid[0]&&g_active),.s_rsp_ready(gs_rsp_ready),
  .s_rsp_data(s_rsp_data[127:0]),.g_in_valid(gin),.g_in_ready(gin_ready),.g_in_gate(gate),.g_in_up(up),
  .g_in_gated(gated),.g_in_mask(gin_mask),.g_out_valid(gout),.g_out_ready(gout_ready),.g_out_data(value),
  .g_out_mask(gout_mask),.g_out_error(gout_error));
 g_s32 G(.clk,.reset,.in_valid(gin),.in_ready(gin_ready),.in_gate(gate),.in_up(up),
  .in_gated(gated),.in_mask(gin_mask),.out_valid(gout),.out_ready(gout_ready),.out_data(value),
  .out_mask(gout_mask),.out_error(gout_error));

 wire qr_valid,qr_write,qr_ready,qs_valid,qs_ready,qr_drained;
 wire [9:0] qr_address;
 wire [127:0] qr_data,qs_data;
 wire [31:0] qr_tag,qs_tag;
 s32_a16_tile_quantizer quant(.clk,.reset,.cmd_valid(mid_cmd&&!quant_exhausted),.cmd_ready(mid_cmd_ready),
  .cmd_key(expected_key),.cmd_generation(quant_epoch+16'd1),.cmd_kk(mid_first),.cmd_source(10'd848),
  .cmd_destination(mid_destination_base),.cmd_shift_known(1'b1),.cmd_shift(max_shift),
  .cancel_valid(1'b0),.cancel_key(128'd0),.s_valid(qr_valid),.s_ready(qr_ready),.s_write(qr_write),
  .s_address(qr_address),.s_data(qr_data),.s_tag(qr_tag),.rsp_valid(qs_valid),.rsp_ready(qs_ready),
  .rsp_tag(qs_tag),.rsp_data(qs_data),.rsp_error(1'b0),.done_valid(q_done),.done_ready(q_take),
  .done_key(q_key),.done_kk(q_first),.done_error(q_error),.done_cancelled(q_cancelled),
  .done_words(q_words),.done_written_mask(q_mask),.done_shift(q_shift),.rejected_responses(q_rejected));
 wire [2:0] q_valid,q_write,q_rsp_ready;
 wire [29:0] q_address;
 wire [383:0] q_data;
 wire [95:0] q_tag;
 quant_mid_s128_router router(.clk,.reset,.destination(mid_destination),
  .req_valid(qr_valid),.req_ready(qr_ready),.req_write(qr_write),.req_address(qr_address),.req_data(qr_data),.req_tag(qr_tag),
  .rsp_valid(qs_valid),.rsp_ready(qs_ready),.rsp_data(qs_data),.rsp_tag(qs_tag),.drained(qr_drained),
  .s_valid(q_valid),.s_write(q_write),.s_ready(s_ready&{2'b11,!g_active}),.s_address(q_address),.s_data(q_data),.s_tag(q_tag),
  .s_rsp_valid(s_rsp_valid&{2'b11,!g_active}),.s_rsp_ready(q_rsp_ready),.s_rsp_data,.s_rsp_tag);
 assign s_valid={q_valid[2:1],g_active ? gs_valid:q_valid[0]};
 assign s_write={q_write[2:1],g_active ? gs_write:q_write[0]};
 assign s_address={q_address[29:10],g_active ? gs_address:q_address[9:0]};
 assign s_data={q_data[383:128],g_active ? gs_data:q_data[127:0]};
 assign s_tag={q_tag[95:32],g_active ? 32'h473332:q_tag[31:0]};
 assign s_rsp_ready={q_rsp_ready[2:1],g_active ? gs_rsp_ready:q_rsp_ready[0]};
 always @(posedge clk)begin
  if(reset)begin quant_epoch<=0;max_shift<=0;g_active<=0;quant_fail<=0;end
  else begin
   if(g_valid&&g_ready)g_active<=1;
   if(g_done&&g_take)begin
    g_active<=0;
    if(g_mid_base==10'd848||g_shift>max_shift)max_shift<=g_shift;
   end
   if(mid_cmd&&quant_exhausted)quant_fail<=1;
   else if(mid_result_ready)quant_fail<=0;
   if(mid_cmd&&mid_cmd_ready&&!quant_exhausted)quant_epoch<=quant_epoch+16'd1;
`ifndef SYNTHESIS
   assert(!g_active||qr_drained)else $fatal(1,"G and Mid reused the same S owner");
   assert(!q_done||qr_drained)else $fatal(1,"Mid released before actual S drain");
   assert(q_rejected==0)else $fatal(1,"Mid result response identity");
`endif
  end
 end
 wire [32:0] _unused_router_debug={qr_drained,q_rejected};
endmodule
