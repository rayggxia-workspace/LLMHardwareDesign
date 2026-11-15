`timescale 1ns/1ps
// Parent standard-cell adapter for one existing E32 macro.
// A grant spans every operand beat and BOTH accepted 64-bit result beats of one E command.
// CLIENTS is a hardware build parameter, never added by product metal.
module e32_service_selector #(
 parameter integer CLIENTS=3,
 parameter bit MAC_CONTEXT=0,
 parameter integer OWNER_BITS=(CLIENTS>1 ? $clog2(CLIENTS) : 1)
)(
 input wire clk,reset,
 input wire [CLIENTS-1:0] client_in_valid,
 output logic [CLIENTS-1:0] client_in_ready,
 input wire [CLIENTS-1:0][63:0] client_in_data,
 input wire [CLIENTS-1:0][3:0] client_in_op,client_in_mask,
 input wire [CLIENTS-1:0][7:0] client_in_shift,
 input wire [CLIENTS-1:0][2:0] client_in_minus,
 output logic [CLIENTS-1:0] client_out_valid,
 input wire [CLIENTS-1:0] client_out_ready,
 output logic [CLIENTS-1:0][63:0] client_out_data,
 output logic [CLIENTS-1:0][3:0] client_out_clipped,
 output logic [CLIENTS-1:0] client_out_error,
 output wire macro_in_valid,
 input wire macro_in_ready,
 output wire [63:0] macro_in_data,
 output wire [3:0] macro_in_op,macro_in_mask,
 output wire [7:0] macro_in_shift,
 output wire [2:0] macro_in_minus,
 input wire macro_out_valid,
 output wire macro_out_ready,
 input wire [63:0] macro_out_data,
 input wire [3:0] macro_out_clipped,
 input wire macro_out_error,
 output wire busy
);
 reg owned,context_owned,command_seen;
 reg [3:0] command_op;
 reg result_high;
 reg [OWNER_BITS-1:0] owner;
 integer chosen;
 assign busy=owned;
 assign macro_in_valid=!reset && owned && client_in_valid[owner];
 assign macro_in_data=owned ? client_in_data[owner] : 64'd0;
 assign macro_in_op=owned ? client_in_op[owner] : 4'd0;
 assign macro_in_mask=owned ? client_in_mask[owner] : 4'd0;
 assign macro_in_shift=owned ? client_in_shift[owner] : 8'd0;
 assign macro_in_minus=owned ? client_in_minus[owner] : 3'd0;
 assign macro_out_ready=!reset && owned && client_out_ready[owner];
 always_comb begin
   chosen=-1;
   for(integer i=CLIENTS-1;i>=0;i=i-1)
     if(client_in_valid[i]) chosen=i;
   client_in_ready='0;
   client_out_valid='0;
   client_out_data='0;
   client_out_clipped='0;
   client_out_error='0;
   if(!reset && owned) begin
     client_in_ready[owner]=macro_in_ready;
     client_out_valid[owner]=macro_out_valid;
     client_out_data[owner]=macro_out_data;
     client_out_clipped[owner]=macro_out_clipped;
     client_out_error[owner]=macro_out_error;
   end
 end
 always @(posedge clk) begin
   if(reset)begin owned<=0;owner<=0;result_high<=0;context_owned<=0;command_seen<=0;command_op<=0;end
   else if(!owned && chosen>=0)begin owned<=1;owner<=OWNER_BITS'(chosen);end
   else if(owned && macro_out_valid && macro_out_ready)begin
     result_high<=!result_high;
     if(result_high)begin
       command_seen<=0;
       if(MAC_CONTEXT&&command_op==12&&!macro_out_error)begin context_owned<=1;owned<=1;end
       else if(MAC_CONTEXT&&(command_op==14||command_op==15)&&!macro_out_error)begin context_owned<=0;owned<=0;end
       else owned<=MAC_CONTEXT&&context_owned;
     end
   end
   if(!reset&&owned&&macro_in_valid&&macro_in_ready&&!command_seen)begin
     command_seen<=1;command_op<=macro_in_op;
   end
 end
 initial begin
   if(CLIENTS<1) $error("E32 selector needs at least one registered client");
 end
endmodule
