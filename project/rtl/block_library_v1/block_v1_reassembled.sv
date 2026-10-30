// One physical S/byte/S32/SFU/link bank, four mutually exclusive controller leases.
module block_v1_reassembled(input wire clk,reset,cmd,input wire [1:0] command_kind,
 input wire soft_abort,output wire abort_ready,abort_accept,
 output wire cmd_ready,cmd_accept,busy,done,input wire ack,output reg [7:0] status,output wire [7:0] debug_state,output reg [1:0] owner,
 input wire [31:0] gateup_address,records_address,gamma_address,m_owner,m_version,epsilon,coefficient,
 input wire [10:0] length,position,input wire [15:0] window,input wire [63:0] query_units,input wire signed [7:0] key_unit,value_unit,
 input wire [31:0] key_address,value_address,a_owner,a_version,score_multiplier,
 input wire [1:0] r_command,input wire [4:0] r_head,input wire signed [15:0] r_initial_unit,input wire [31:0] r_expected_position,
 input wire g_command,input wire [31:0] g_owner,input wire [63:0] g_context_id,g_expected_position,g_expected_version,input wire [4:0] g_slot,
 output wire [63:0] g_position,g_version,g_context_saved,output wire [31:0] g_numeric_epoch,g_owner_saved,output wire [15:0] g_units,g_value_units,g_candidate_units,output wire [31:0] g_candidate_epoch,output wire g_bank,g_state_validated,
 output wire [7:0] gdebug,output wire [63:0] g_cycles,output wire [31:0] g_reads,g_writes,g_sreads,g_swrites,g_wide_calls,output wire [3:0] g_retries,
 output wire g_obs_valid,output wire [2:0] g_obs_kind,output wire g_obs_head,output wire [6:0] g_obs_pair,g_obs_i,output wire signed [63:0] g_obs_lo,g_obs_hi,
 input wire accept_candidate,reject_candidate,output wire candidate_ready,
 output wire [31:0] r_position,r_numeric_epoch,output wire signed [15:0] r_unit,output wire r_bank,output wire [31:0] candidate_epoch,output wire signed [15:0] candidate_unit,
 input wire cfg,cfg_wr,input wire [9:0] cfg_addr,input wire [127:0] cfg_din,output wire cfg_ready,cfg_valid,input wire cfg_take,output wire [127:0] cfg_dout,
 output wire result_valid,result_candidate,output wire [9:0] result_index,output wire [127:0] result_data,input wire result_take,
 input wire mem_hold,mul_hold,input wire ext_ready,ext_valid,output wire ext_req,ext_wr,output wire [31:0] ext_addr,output wire [127:0] ext_wdata,output wire ext_take,input wire [127:0] ext_data,
 output reg [31:0] epoch,output wire [31:0] ext_epoch,input wire [31:0] response_epoch,output reg [31:0] stale_responses,aborts,leases,
 output reg [63:0] cycles,export_cycles,drain_cycles,output wire [31:0] wire_beats,transactions,mul_grants0,mul_grants1,mul_wait0,mul_wait1,mul_contested,
 output reg [31:0] sreads,swrites,fgrants,result_lines,output wire [4:0] service_accept,output wire services_drained,
 output wire swrite_event,output wire [9:0] swrite_addr,output wire [127:0] swrite_data,
 output wire [7:0] mdebug,adebug,rdebug,vdebug,ndebug,output wire [4:0] mfront_debug,
 output wire obs_mid_valid,obs_a_valid,output wire [11:0] obs_index,output wire signed [31:0] obs_mid,output wire signed [7:0] obs_a,
 output wire m_obs_valid,output wire [10:0] m_obs_row,output wire [2:0] m_obs_rank,output wire signed [31:0] m_obs_acc,m_obs_down,
 output wire a_obs_valid,output wire [1:0] a_obs_kind,output wire [2:0] a_obs_head,output wire [10:0] a_obs_key,output wire signed [31:0] a_obs_x,a_obs_y,output wire [63:0] a_obs_sum,
 output wire [31:0] cache_owner,cache_version,output wire [10:0] cache_length,output wire signed [7:0] cache_key_unit,cache_value_unit,
 output wire [127:0] deltas,observed_sum,observed_den,output wire [7:0] expert_valid,
 output wire [63:0] m_cycles,a_cycles,r_cycles,output wire [31:0] r_reads,r_writes,r_sreads,r_swrites,output wire [3:0] r_retries);
 wire lib_s_req,lib_s_wr,lib_s_ready,lib_s_valid,lib_s_take;
 wire [9:0] lib_s_addr;wire [127:0] lib_s_din,lib_s_dout,lib_byte_p;
 wire [63:0] lib_byte_a,lib_byte_b;
 block_v1_vs compute(.*);
 block_v1_m8 multipliers(lib_byte_a,lib_byte_b,lib_byte_p);
 block_v1_s16k storage(clk,reset,lib_s_req,lib_s_wr,lib_s_addr,lib_s_din,
                      lib_s_ready,lib_s_valid,lib_s_take,lib_s_dout);
endmodule
