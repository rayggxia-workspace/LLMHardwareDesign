// Expose the existing decoder and provider guard without issuing data traffic.
// Supply the matching input owner. Runtime CALL and window ownership are
// separate obligations for the compiler and runtime integration.
module p_scope_admission_probe (
  input logic [1023:0] descriptor,
  input logic [31:0] topology,
  output logic [7:0] status
);
  wire reject_valid, job_valid, service_ready, record_valid;
  wire [7:0] reject_code;
  p_scope_range_service #(.NATIVE_STREAM_A16(1'b1)) main_provider (
    .clk(1'b0), .reset(1'b0), .service_valid(1'b1), .service_ready,
    .service_owner({32'd1, descriptor[224+:32], descriptor[192+:32], 32'd1}),
    .service_ticket(32'd1), .service_descriptor(descriptor), .expected_topology(topology),
    .service_cancel_valid(1'b0), .service_done_ready(1'b1),
    .native_confirmed_read_bytes(32'd0), .native_confirmed_write_bytes(32'd0),
    .record_valid,.record_ready(1'b0), .complete_valid(1'b0), .complete_owner('0),
    .complete_sequence('0), .complete_context('0), .complete_next_k('0), .complete_error(1'b0)
  );
  assign status = main_provider.reject_code != 0 ? main_provider.reject_code :
    main_provider.foreign_input ? 8'd8 : main_provider.nonzero_bias ? 8'd9 :
    main_provider.ticket_bad ? 8'd10 : main_provider.unsupported_native ? 8'd11 : 8'd0;
endmodule
