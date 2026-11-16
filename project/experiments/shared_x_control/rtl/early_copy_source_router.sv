`timescale 1ns/1ps
// A copy has ONE bound ordinary-S source, selected before START and retained
// through all issued reads and destination ACK drain. No source data buffer.
// Provider 0=U, 1=P0, 2=P1, 3=P2. Each provider is a logical arbiter client,
// not an extra physical SRAM port. Tags are restored by that local arbiter.
module early_copy_source_router(
  input logic clk,reset,
  input logic bind_valid,
  output logic bind_ready,
  input logic [1:0] bind_source,
  input logic [127:0] bind_key,
  input logic release_valid,
  output logic release_ready,
  input logic [127:0] release_key,
  output logic bound,
  output logic [1:0] bound_source,
  output logic [127:0] bound_key,
  output logic drained,
  input logic u_valid,
  output logic u_ready,
  input logic [9:0] u_address,
  input logic [31:0] u_tag,
  output logic u_response_valid,
  input logic u_response_ready,
  output logic [127:0] u_response_data,
  output logic [31:0] u_response_tag,
  output logic u_response_error,
  output logic [3:0] source_valid,
  input logic [3:0] source_ready,
  output logic [39:0] source_address,
  output logic [127:0] source_tag,
  input logic [3:0] source_response_valid,
  output logic [3:0] source_response_ready,
  input logic [511:0] source_response_data,
  input logic [127:0] source_response_tag,
  input logic [3:0] source_response_error,
  output logic [31:0] fault_cycles
);
  logic inflight,good_response,bad_response,request_fire,response_fire;
  logic [31:0] expected_tag;
  assign drained=!inflight&&!u_valid&&source_response_valid==0;
  assign bind_ready=!reset&&!bound&&drained;
  assign release_ready=!reset&&bound&&drained&&release_key==bound_key;
  assign good_response=bound&&inflight&&source_response_valid[bound_source]&&
      source_response_tag[32*bound_source+:32]==expected_tag;
  assign u_ready=!reset&&bound&&!inflight&&source_ready[bound_source];
  assign u_response_valid=!reset&&good_response;
  assign u_response_data=source_response_data[128*bound_source+:128];
  assign u_response_tag=source_response_tag[32*bound_source+:32];
  assign u_response_error=source_response_error[bound_source];
  assign request_fire=u_valid&&u_ready;
  assign response_fire=u_response_valid&&u_response_ready;
  always_comb begin
    source_valid=0;source_address=0;source_tag=0;
    // Unexpected responses must drain without satisfying the current lease.
    source_response_ready={4{!reset}};
    if(bound) begin
      source_valid[bound_source]=!reset&&!inflight&&u_valid;
      source_address[10*bound_source+:10]=u_address;
      source_tag[32*bound_source+:32]=u_tag;
      if(good_response) source_response_ready[bound_source]=u_response_ready&&!reset;
    end
    bad_response=|(source_response_valid&source_response_ready)&&!response_fire;
    for(integer s=0;s<4;s=s+1)
      if(source_response_valid[s]&&source_response_ready[s]&&
         (!bound||s!=int'(bound_source)||!good_response)) bad_response=1;
  end
  always_ff @(posedge clk) begin
    if(reset) begin
      bound<=0;bound_source<=0;bound_key<=0;inflight<=0;expected_tag<=0;fault_cycles<=0;
    end else begin
      if(bind_valid&&bind_ready) begin bound<=1;bound_source<=bind_source;bound_key<=bind_key;end
      if(release_valid&&release_ready) bound<=0;
      if(request_fire) begin inflight<=1;expected_tag<=u_tag;end
      if(response_fire) inflight<=0;
      if(bad_response||(release_valid&&bound&&release_key!=bound_key)) fault_cycles<=fault_cycles+1'b1;
    end
  end
endmodule
