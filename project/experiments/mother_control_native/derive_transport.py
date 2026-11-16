"""Text-only compact transport top generation; RTL itself is checked in."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];RTL=ROOT/'project/rtl/mother_control_native'
core=(RTL/'mother_control_native64.sv').read_text()
ports=core[core.index('  input wire clk_i,'):core.index('\n);')]
start=ports.index('  output wire task_valid_o,');end=ports.index('  output wire result_valid_o,',start)
ports=ports[:start]+'''  output wire tx_valid,
  input wire tx_ready,
  output wire [127:0] tx_data,
  output wire [7:0] tx_target,
  output wire tx_sop,tx_eop,tx_credit,
  input wire rx_valid,
  output wire rx_ready,
  input wire [127:0] rx_data,
  input wire [7:0] rx_source,
  input wire rx_sop,rx_eop,
  input wire transport_drained_i,
  output wire [31:0] frame_fault_count,
'''+ports[end:]
ports=ports.replace('  input wire [255:0] start_args_i,\n','')
text='''// 64bit instructions; four-flit 128bit physical MC/LC task transport.
`timescale 1ns/1ps
module mother_control_native64_transport128 #(parameter [31:0] NATIVE_ABI_ID=32'h02500002)(
'''+ports+'''
);
  wire task_valid_o,task_ready_i,task_credit_o,return_valid_i,return_ready_o;
  wire [511:0] task_packet_o,return_packet_i;
  wire [7:0] task_target_o;
  wire [255:0] start_args_i=0;
  wire core_recover_ready,core_recover_valid,bridge_drained;
  assign recover_ready_o=core_recover_ready&&bridge_drained&&transport_drained_i;
  assign core_recover_valid=recover_valid_i&&bridge_drained&&transport_drained_i;
  mother_control_native64 #(.NATIVE_ABI_ID(NATIVE_ABI_ID)) mother(
    .recover_valid_i(core_recover_valid),.recover_ready_o(core_recover_ready),.*);
  mc_packet128_bridge transport(
    .clk(clk_i),.reset(!rst_ni),.core_task_valid(task_valid_o),.core_task_ready(task_ready_i),
    .core_task_packet(task_packet_o),.core_task_target(task_target_o),.core_task_credit(task_credit_o),
    .tx_valid,.tx_ready,.tx_data,.tx_target,.tx_sop,.tx_eop,.tx_credit,
    .rx_valid,.rx_ready,.rx_data,.rx_source,.rx_sop,.rx_eop,
    .core_return_valid(return_valid_i),.core_return_ready(return_ready_o),.core_return_packet(return_packet_i),
    .drained(bridge_drained),.frame_fault_count);
endmodule
'''
(RTL/'mother_control_native64_transport128.sv').write_text(text)
