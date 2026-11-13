`timescale 1ns/1ps
// Zero-copy typed view of the LC's already CRC-checked128B scope registers.
// The external record provider must complete FINAL/SPILL only after real S
// writes/ACKs. This module does not turn INPUT-consumed into record-complete.
module p_scope_range_service #(
 // The old iterator/control fixture remains generic. A real native provider
 // must opt into its actually registered numeric/restore coverage.
 parameter logic NATIVE_LOCAL_CONTIG=1'b0,
 parameter logic NATIVE_STREAM_A16=1'b0,
 parameter logic NATIVE_RESIDENT_X_K2048=1'b0,
 parameter logic NATIVE_DUAL_A16=1'b0
)(
 input logic clk,reset,
 input logic service_valid,output logic service_ready,
 input logic [127:0] service_owner,input logic [31:0] service_ticket,
 input logic [1023:0] service_descriptor,input logic [31:0] expected_topology,
 input logic service_cancel_valid,output logic service_cancel_ready,
 output logic service_done_valid,input logic service_done_ready,
 output logic [127:0] service_done_owner,output logic [31:0] service_done_ticket,
 output logic [15:0] service_done_status,
 input logic [31:0] native_confirmed_read_bytes,native_confirmed_write_bytes,
 output logic [31:0] service_done_read_bytes,service_done_write_bytes,
 output logic [127:0] input_key,
 output logic [31:0] rf_object_base0,rf_object_base1,output_version,
 output logic [63:0] bias_address0,bias_address1,
 output logic [9:0] input_s_base,output_s_base0,output_s_base1,scratch_s_base,snapshot_s_base,
 output logic record_valid,input logic record_ready,
 output logic [127:0] record_owner,output logic [31:0] record_sequence,
 output logic [63:0] record_address,
 output logic [15:0] record_bytes,record_full_k,record_k,
 output logic [31:0] record_col,output logic [3:0] record_context,record_n,
 output logic record_way,record_head16,record_create,record_restore,record_final,record_spill,
 output logic record_A_first,record_A_last,output logic [4:0] record_A_uses,
 input logic complete_valid,output logic complete_ready,input logic [127:0] complete_owner,
 input logic [31:0] complete_sequence,input logic [3:0] complete_context,
 input logic [15:0] complete_next_k,input logic complete_error,output logic rejected_complete
);
 logic job_valid,job_ready,reject_valid,reject_ready,decode_ready,typed_job_ready;
 logic [7:0] reject_code;
 logic [31:0] sequence_base,columns,first_column;
 logic [63:0] weight_base0,weight_base1;
 logic [15:0] column_stride,full_k,k_begin,k_end;
 logic [4:0] groups;
 logic [3:0] first_context;
 logic [1:0] ways;
 logic head16,range_done_valid,range_done_ready,range_done_error,range_done_cancelled;
 logic [127:0] range_done_owner;
 logic [31:0] done_issued,done_completed,done_failed_sequence;
 logic [15:0] done_failed_next_k;
 logic reject_live;
 logic [127:0] rejected_owner;
 logic [31:0] rejected_ticket;
 logic [7:0] held_reject_code;
 assign reject_ready=!reset&&!reject_live&&job_ready;
 wire foreign_input=input_key[127:96]!=service_owner[95:64]||input_key[95:64]!=service_owner[63:32];
 wire nonzero_bias=bias_address0!=0||(ways==2&&bias_address1!=0);
 wire ticket_bad=service_ticket!=service_owner[31:0];
 wire unsupported_native=(NATIVE_LOCAL_CONTIG&&
     ((full_k!=128&&full_k!=256)||k_begin!=0||k_end!=full_k))||
     (NATIVE_STREAM_A16&&(NATIVE_LOCAL_CONTIG||NATIVE_RESIDENT_X_K2048||NATIVE_DUAL_A16||service_descriptor[48+:16]!=16'd2||k_begin!=0||k_end!=full_k))||
     (NATIVE_RESIDENT_X_K2048&&(NATIVE_LOCAL_CONTIG||NATIVE_DUAL_A16||service_descriptor[48+:16]!=16'd1||full_k!=2048||k_begin!=0||k_end!=full_k))||
     (NATIVE_DUAL_A16&&(NATIVE_LOCAL_CONTIG||NATIVE_STREAM_A16||NATIVE_RESIDENT_X_K2048||
       (service_descriptor[48+:16]==16'd1&&full_k!=2048)||k_begin!=0||k_end!=full_k));
 wire provider_bad=foreign_input||nonzero_bias||ticket_bad||unsupported_native;
 assign typed_job_ready=job_ready&&!provider_bad&&!reject_live;
 assign service_ready=!reset&&!reject_live&&((job_valid&&provider_bad)?reject_ready:decode_ready);
 p_scope128_decode #(.ALLOW_STREAM_A16((NATIVE_STREAM_A16||NATIVE_DUAL_A16)&&!NATIVE_LOCAL_CONTIG)) decode(
   .scope_valid(service_valid&&!reject_live),.scope_ready(decode_ready),.scope_data(service_descriptor),.scope_crc_ok(1'b1),
   .expected_topology,.job_valid,.job_ready(typed_job_ready),.reject_valid,.reject_ready,.reject_code,
   .input_key,.rf_object_base0,.rf_object_base1,.output_version,.sequence_base,.weight_base0,.weight_base1,
   .bias_address0,.bias_address1,.columns,.first_column,.column_stride,.full_k,.k_begin,.k_end,
   .groups,.first_context,.ways,.head16,.input_s_base,.output_s_base0,.output_s_base1,.scratch_s_base,.snapshot_s_base
 );
 record_range_iterator range_service(
   .clk,.reset,.job_valid(job_valid&&!provider_bad&&!reject_live),.job_ready,.job_owner(service_owner),.job_sequence_base(sequence_base),
   .job_weight_base(weight_base0),.job_weight_base1(weight_base1),.job_ways(ways),.job_columns(columns),
   .job_first_col(first_column),.job_col_stride(column_stride),.job_groups(groups),.job_first_context(first_context),
   .job_full_k(full_k),.job_k_begin(k_begin),.job_k_end(k_end),.job_head16(head16),
   .cancel_valid(service_cancel_valid),.cancel_owner(service_owner),
   .record_valid,.record_ready,.record_owner,.record_sequence,.record_address,.record_bytes,.record_full_k,
   .record_k,.record_col,.record_context,.record_n,.record_way,.record_head16,.record_create,.record_restore,
   .record_final,.record_spill,.record_A_first,.record_A_last,.record_A_uses,
   .complete_valid,.complete_ready,.complete_owner,.complete_sequence,.complete_context,.complete_next_k,.complete_error,
   .rejected_complete,.done_valid(range_done_valid),.done_ready(range_done_ready),.done_owner(range_done_owner),
   .done_error(range_done_error),.done_cancelled(range_done_cancelled),.done_issued,.done_completed,
   .done_failed_sequence,.done_failed_next_k
 );
 assign service_cancel_ready=!reset;
 assign service_done_valid=reject_live||range_done_valid;
 assign range_done_ready=service_done_ready&&!reject_live;
 assign service_done_owner=reject_live?rejected_owner:range_done_owner;
 assign service_done_ticket=reject_live?rejected_ticket:range_done_owner[31:0];
 assign service_done_status=reject_live ? (16'd32+{8'd0,held_reject_code}) :
     (range_done_error?16'd1:(range_done_cancelled?16'd3:16'd0));
 assign service_done_read_bytes=reject_live?32'd0:native_confirmed_read_bytes;
 assign service_done_write_bytes=reject_live?32'd0:native_confirmed_write_bytes;
 always_ff @(posedge clk)begin
   if(reset)begin reject_live<=0;rejected_owner<=0;rejected_ticket<=0;held_reject_code<=0;end
   else begin
     if((reject_valid||(job_valid&&provider_bad))&&reject_ready)begin
       reject_live<=1;rejected_owner<=service_owner;rejected_ticket<=service_ticket;
       held_reject_code<=reject_valid?reject_code:(foreign_input?8'd8:(nonzero_bias?8'd9:(ticket_bad?8'd10:8'd11)));
     end
     if(reject_live&&service_done_ready)reject_live<=0;
   end
 end
 wire unused_range_diagnostics=^{done_issued,done_completed,done_failed_sequence,done_failed_next_k};
endmodule
