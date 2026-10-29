// Representative public-port composition; no changes to native macro RTL.
module linkclose_mts_bench(
 input wire clk,reset,cmd_valid,command_capture,
 output wire cmd_ready,input wire [3:0]cmd_op,input wire [5:0]cmd_index,
 input wire [127:0]cmd_data,
 input wire begin_valid,output wire begin_ready,input wire [9:0]begin_words,
 input wire commit_valid,output wire commit_ready,
 input wire release_valid,output wire release_ready,
 input wire write_enable,read_enable,s_take,
 input wire verify_req,input wire [9:0]verify_addr,
 output wire verify_ready,s_valid,output wire [127:0]s_dout,
 output wire t_error,bridge_error,bridge_saturated,
 output wire [1:0]occupancy,output wire m_valid,m_ready,
 output wire [127:0]m_data,output wire t_write_valid,t_write_ready,
 output wire [9:0]t_write_index,output wire [127:0]t_write_data,
 output wire t_read_valid,t_read_take,output wire [9:0]t_read_index,
 output wire [127:0]t_read_data,output wire t_busy,t_sealed
);
 wire m_error,m_saturated;
 block_v1_m m(.clk(clk),.reset(reset),.cmd_valid(cmd_valid),.cmd_ready(cmd_ready),
  .cmd_op(cmd_op),.cmd_index(cmd_index),.cmd_data(cmd_data),.rsp_valid(m_valid),
  .rsp_ready(m_ready),.rsp_data(m_data),.rsp_error(m_error),.rsp_saturated(m_saturated),.busy());
 linkclose_bridge b(.clk(clk),.reset(reset),.command_valid(cmd_valid),.command_ready(cmd_ready),
  .command_capture(command_capture),.response_valid(m_valid),.response_ready(m_ready),
  .response_data(m_data),.response_error(m_error),.response_saturated(m_saturated),
  .begin_valid(begin_valid),.begin_ready(begin_ready),.write_enable(write_enable),
  .write_valid(t_write_valid),.write_ready(t_write_ready),.write_index(t_write_index),
  .write_data(t_write_data),.occupancy(occupancy),.observed_error(bridge_error),
  .observed_saturation(bridge_saturated));
 transaction6k t(.clk(clk),.reset(reset),.begin_valid(begin_valid),.begin_ready(begin_ready),
  .begin_owner(2'b01),.begin_generation(32'd1),.begin_words(begin_words),
  .write_valid(t_write_valid),.write_ready(t_write_ready),.write_index(t_write_index),.write_data(t_write_data),
  .commit_valid(commit_valid),.commit_ready(commit_ready),.revoke_valid(1'b0),.revoke_ready(),
  .read_valid(t_read_valid),.read_take(t_read_take),.read_index(t_read_index),.read_data(t_read_data),
  .read_last(),.owner(),.generation(),.word_count(),.release_valid(release_valid),
  .release_ready(release_ready),.busy(t_busy),.sealed(t_sealed),.committed(),.protocol_error(t_error),.debug_state());
 wire s_ready;
 wire stream=t_read_valid&&read_enable;
 assign t_read_take=!verify_req&&read_enable&&s_ready;
 assign verify_ready=s_ready&&!t_read_valid;
 block_v1_s16k s(.clk(clk),.reset(reset),.req(verify_req?verify_req:stream),
  .wr(!verify_req),.addr(verify_req?verify_addr:t_read_index),.din(t_read_data),
  .ready(s_ready),.valid(s_valid),.take(s_take),.dout(s_dout));
endmodule
