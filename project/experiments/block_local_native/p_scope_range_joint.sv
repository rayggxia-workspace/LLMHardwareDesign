module p_scope_range_joint (
 input wire clk, reset,
 input wire scope_valid, output wire scope_ready,
 input wire [1023:0] scope_data,
 input wire scope_crc_ok, input wire [31:0] expected_topology,
 input wire [127:0] job_owner,
 output wire reject_valid, input wire reject_ready, output wire [7:0] reject_code,
 input wire cancel_valid, input wire [127:0] cancel_owner,
 output reg record_valid, input wire record_ready,
 output reg [127:0] record_owner,
 output reg [31:0] record_sequence,
 output reg [63:0] record_address,
 output reg [15:0] record_bytes, record_full_k, record_k,
 output reg [31:0] record_col,
 output reg [3:0] record_context, record_n,
 output reg record_way,
 output reg record_head16, record_create, record_restore, record_final, record_spill,
 output reg record_A_first, record_A_last,
 output reg [4:0] record_A_uses,
 input wire complete_valid, output wire complete_ready,
 input wire [127:0] complete_owner,
 input wire [31:0] complete_sequence,
 input wire [3:0] complete_context,
 input wire [15:0] complete_next_k,
 input wire complete_error,
 output reg rejected_complete,
 output reg done_valid, input wire done_ready,
 output reg [127:0] done_owner,
 output reg done_error, done_cancelled,
 output reg [31:0] done_issued, done_completed,
 output reg [31:0] done_failed_sequence,
 output reg [15:0] done_failed_next_k
);
 wire job_valid,job_ready,job_head16;
 wire [31:0] job_sequence_base,job_columns,job_first_col;
 wire [63:0] job_weight_base,job_weight_base1;
 wire [1:0] job_ways;
 wire [15:0] job_col_stride,job_full_k,job_k_begin,job_k_end;
 wire [4:0] job_groups;
 wire [3:0] job_first_context;
 wire [127:0] input_key;
 wire [31:0] rf_object_base0,rf_object_base1,output_version;
 wire [63:0] bias_address0,bias_address1;
 wire [9:0] input_s_base,output_s_base0,output_s_base1,scratch_s_base,snapshot_s_base;
 p_scope128_decode decode(
  .sequence_base(job_sequence_base),.weight_base0(job_weight_base),.weight_base1(job_weight_base1),
  .ways(job_ways),.columns(job_columns),.first_column(job_first_col),.column_stride(job_col_stride),
  .groups(job_groups),.first_context(job_first_context),.full_k(job_full_k),
  .k_begin(job_k_begin),.k_end(job_k_end),.head16(job_head16),.*);
 record_range_iterator range_unit(.*);
 wire unused_fields=^{input_key,rf_object_base0,rf_object_base1,output_version,
   bias_address0,bias_address1,input_s_base,output_s_base0,output_s_base1,scratch_s_base,snapshot_s_base};
endmodule
