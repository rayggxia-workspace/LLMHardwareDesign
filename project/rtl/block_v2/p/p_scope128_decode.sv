// A combinational view of the fetcher's existing 128B scope register.
// No duplicate descriptor storage. CRC success must come from the real fetch.
// Rejected descriptors have no job_valid, so they cannot issue M/S traffic.
module p_scope128_decode #(
 // Opt-in belongs to an actual STREAM provider. Existing contiguous/native
 // profiles must keep rejecting service2; this decoder alone registers none.
 parameter logic ALLOW_STREAM_A16=1'b0
)(
 input wire scope_valid, output wire scope_ready,
 input wire [1023:0] scope_data,
 input wire scope_crc_ok,
 input wire [31:0] expected_topology,
 output wire job_valid, input wire job_ready,
 output wire reject_valid, input wire reject_ready,
 output wire [7:0] reject_code,
 output wire [127:0] input_key,
 output wire [31:0] rf_object_base0, rf_object_base1, output_version,
 output wire [31:0] sequence_base,
 output wire [63:0] weight_base0, weight_base1, bias_address0, bias_address1,
 output wire [31:0] columns, first_column,
 output wire [15:0] column_stride, full_k, k_begin, k_end,
 output wire [4:0] groups,
 output wire [3:0] first_context,
 output wire [1:0] ways,
 output wire head16,
 output wire [9:0] input_s_base, output_s_base0, output_s_base1,
 output wire [9:0] scratch_s_base, snapshot_s_base
);
 assign input_key=scope_data[128+:128];
 assign rf_object_base0=scope_data[256+:32];
 assign rf_object_base1=scope_data[288+:32];
 assign output_version=scope_data[320+:32];
 assign sequence_base=scope_data[352+:32];
 assign weight_base0=scope_data[384+:64];
 assign weight_base1=scope_data[448+:64];
 assign columns=scope_data[512+:32]; assign first_column=scope_data[544+:32];
 assign column_stride=scope_data[576+:16];
 assign groups=scope_data[592+:5]; assign first_context=scope_data[600+:4];
 assign full_k=scope_data[608+:16]; assign k_begin=scope_data[624+:16];
 assign k_end=scope_data[640+:16]; assign ways=scope_data[656+:2];
 assign head16=scope_data[664];
 assign input_s_base=scope_data[672+:10]; assign output_s_base0=scope_data[688+:10];
 assign output_s_base1=scope_data[704+:10]; assign scratch_s_base=scope_data[720+:10];
 assign snapshot_s_base=scope_data[736+:10];
 assign bias_address0=scope_data[768+:64]; assign bias_address1=scope_data[832+:64];
 wire [63:0] last_col={32'd0,first_column}+({59'd0,groups}-64'd1)*{48'd0,column_stride};
 wire stream_scope=scope_data[48+:16]==16'd2;
 wire service_bad=scope_data[48+:16]!=16'd1 && !(ALLOW_STREAM_A16&&stream_scope);
 wire [6:0] contexts={2'd0,groups}*{5'd0,ways};
 wire [63:0] records={57'd0,contexts}*(({48'd0,k_end}-{48'd0,k_begin})>>7);
 wire [63:0] record_bytes=head16 ? 64'd1152 : 64'd1088;
 wire [63:0] weight_bytes=(((last_col>>3)*({48'd0,full_k}>>7)+({48'd0,k_end}>>7)-64'd1)*record_bytes)+record_bytes;
 wire [64:0] weight_end0={1'b0,weight_base0}+{1'b0,weight_bytes};
 wire [64:0] weight_end1={1'b0,weight_base1}+{1'b0,weight_bytes};
 wire [63:0] rf_first0={32'd0,rf_object_base0}+({32'd0,first_column}>>3);
 wire [63:0] rf_first1={32'd0,rf_object_base1}+({32'd0,first_column}>>3);
 wire [63:0] rf_last0={32'd0,rf_object_base0}+(last_col>>3);
 wire [63:0] rf_last1={32'd0,rf_object_base1}+(last_col>>3);
 wire range_bad=groups==0 || groups>16 || (ways!=1 && ways!=2) ||
    ({3'd0,first_context}+contexts)>16 ||
    first_column[2:0]!=0 || column_stride<8 || column_stride[2:0]!=0 ||
    last_col>={32'd0,columns} || full_k==0 || full_k[6:0]!=0 ||
    k_begin[6:0]!=0 || k_end[6:0]!=0 || k_begin>=k_end || k_end>full_k ||
    ({32'd0,sequence_base}+records)>64'h100000000 ||
    weight_base0[5:0]!=0 || weight_end0>=65'h1000000000000 ||
    (ways==2 && (weight_base1[5:0]!=0 || weight_end1>=65'h1000000000000));
 wire identity_bad=rf_last0[63:32]!=0 || (ways==2 &&
    (rf_last1[63:32]!=0 || !(rf_last0<rf_first1 || rf_last1<rf_first0)));
 wire [10:0] out_words={6'd0,groups}<<1;
 wire [10:0] out_end0={1'b0,output_s_base0}+out_words;
 wire [10:0] out_end1={1'b0,output_s_base1}+out_words;
 // Service1 owns a full contiguous A16 image. Service2 owns just one K128
 // staging tile, whose current key/K/generation/session/ticket and LOAD proof
 // must come from the real window/transport provider, never this decoder.
 wire [13:0] input_end={4'd0,input_s_base}+(stream_scope?14'd16:{1'b0,full_k[15:3]});
 wire [10:0] snapshot_end={1'b0,snapshot_s_base}+({4'd0,contexts}<<1);
 wire partial_scope=k_begin!=0 || k_end!=full_k;
 wire stream_bad=stream_scope&&(partial_scope||bias_address0!=0||(ways==2&&bias_address1!=0));
 wire [15:0] raw_input_s=scope_data[672+:16],raw_out0=scope_data[688+:16],
    raw_out1=scope_data[704+:16],raw_scratch=scope_data[720+:16],
    raw_snapshot=scope_data[736+:16];
 wire memory_bad=raw_input_s>1023 || raw_out0>1023 || raw_out1>1023 ||
    raw_scratch>1023 || raw_snapshot>1023 ||
    input_end>14'd1024 || out_end0>1024 || (ways==2 && out_end1>1024) ||
    !((out_end0<={1'b0,input_s_base}) || ({4'd0,output_s_base0}>=input_end)) ||
    (ways==2 && (!((out_end1<={1'b0,input_s_base}) || ({4'd0,output_s_base1}>=input_end)) ||
                 !((out_end0<={1'b0,output_s_base1}) || ({1'b0,output_s_base0}>=out_end1)))) ||
    (partial_scope && (snapshot_end>1024 ||
      !((snapshot_end<={1'b0,input_s_base}) || ({4'd0,snapshot_s_base}>=input_end)) ||
      !((snapshot_end<={1'b0,output_s_base0}) || ({1'b0,snapshot_s_base}>=out_end0)) ||
      (ways==2 && !((snapshot_end<={1'b0,output_s_base1}) || ({1'b0,snapshot_s_base}>=out_end1)))));
 wire reserved_bad=scope_data[597+:3]!=0 || scope_data[604+:4]!=0 ||
    scope_data[658+:6]!=0 || scope_data[665+:7]!=0 ||
    scope_data[752+:16]!=0 || scope_data[896+:96]!=0;
 // Address zero explicitly means a zero bias; nonzero bias is fetched by
 // the executor, never fabricated by this decoder.
 wire bias_bad=(bias_address0!=0 && (bias_address0[63:48]!=0 || bias_address0[1:0]!=0)) ||
    (ways==2 && bias_address1!=0 && (bias_address1[63:48]!=0 || bias_address1[1:0]!=0));
 assign reject_code=!scope_crc_ok ? 8'd1 :
    (scope_data[0+:32]!=32'h02505001 || scope_data[32+:16]!=16'd128 ||
     scope_data[64+:32]!=32'h02504d02 || reserved_bad) ? 8'd2 :
    scope_data[96+:32]!=expected_topology ? 8'd3 :
    service_bad ? 8'd4 :
    (range_bad || bias_bad || stream_bad) ? 8'd5 : identity_bad ? 8'd6 : memory_bad ? 8'd7 : 8'd0;
 assign job_valid=scope_valid && reject_code==0;
 assign reject_valid=scope_valid && reject_code!=0;
 assign scope_ready=reject_code==0 ? job_ready : reject_ready;
 // The actual CRC bytes have already been consumed by lc_scope_fetch128.
 wire unused_crc=^scope_data[992+:32];
endmodule
