`timescale 1ns/1ps
module network_pm #(parameter integer BYTES=8320)(
  input wire clk_i,rst_ni,input wire [31:0] cycle_i,input wire [31:0] stall_i,
  input wire pm_req_valid_o,pm_req_write_o,input wire [13:0] pm_req_address_o,input wire [127:0] pm_req_data_o,
  output wire pm_req_ready_i,output reg pm_rsp_valid_i,output reg [127:0] pm_rsp_data_i,output wire pm_rsp_error_i,
  input wire pm_rsp_ready_o,input wire fault_active_i,input wire [31:0] fault_address_i,input wire [127:0] fault_xor_i
);
  reg [127:0] memory[0:519],pending_data; reg pending=0,pending_write;
  reg [13:0] pending_address; integer wait_cycles=0,n;
  initial for(n=0;n<520;n=n+1) memory[n]={16{8'hcd}};
  assign pm_req_ready_i=rst_ni && !pending && !pm_rsp_valid_i && (stall_i==0 || cycle_i%5==0);
  assign pm_rsp_error_i=0;
  always @(posedge clk_i) begin
    if(!rst_ni) begin pending<=0; pm_rsp_valid_i<=0; pm_rsp_data_i<=0; end
    else begin
      if(pm_req_valid_o && pm_req_ready_i) begin
        if(pending || pm_rsp_valid_i || pm_req_address_o[3:0]!=0 || {18'b0,pm_req_address_o}+16>BYTES) $fatal(1,"network PM bounds/ownership");
        pending<=1; pending_write<=pm_req_write_o; pending_address<=pm_req_address_o; pending_data<=pm_req_data_o; wait_cycles<=32'(stall_i)+1;
      end
      if(pending) begin
        if(wait_cycles==0) begin
          pending<=0; pm_rsp_valid_i<=1;
          if(pending_write) begin memory[pending_address[13:4]]<=pending_data; pm_rsp_data_i<=0; end
          else pm_rsp_data_i<=memory[pending_address[13:4]] ^ (fault_active_i && {18'b0,pending_address}==fault_address_i ? fault_xor_i : 128'b0);
        end else wait_cycles<=wait_cycles-1;
      end
      if(pm_rsp_valid_i && pm_rsp_ready_o) pm_rsp_valid_i<=0;
    end
  end
endmodule
