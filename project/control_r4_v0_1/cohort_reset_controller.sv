`timescale 1ns/1ps
// Management-side bounded cohort sequencer. ACKs certify real provider flush;
// this controller cannot infer absence of untagged replies from a timeout.
module cohort_reset_controller #(parameter integer MEMBERS=8,MIN_RESET=4,QUIET_CYCLES=3)(
 input wire clk,por_ni,
 input wire reset_valid,output wire reset_ready,input wire [31:0] reset_sequence,reset_generation,reset_epoch,
 input wire ack_valid,input wire [MEMBERS-1:0] ack_mask,input wire [31:0] ack_sequence,ack_epoch,
 input wire providers_quiet,fault,
 input wire reload_valid,input wire [2:0] prepared_mask,input wire [31:0] prepared_generation,
 output wire reset_o,admit_o,reload_o,output wire [2:0] phase_o,
 output reg [31:0] sequence_o,generation_o,epoch_o,output reg [MEMBERS-1:0] acknowledged_o,
 output wire poisoned_o
);
 localparam [2:0] RESET=0,QUIET=1,RELOAD=2,RUN=3,POISON=4;
 reg [2:0] state;reg reset_hold;integer reset_age,quiet_age;
 assign phase_o=state;assign reset_o=!por_ni||reset_hold;
 assign admit_o=por_ni&&state==RUN&&!reset_valid&&!fault;
 assign reload_o=por_ni&&state==RELOAD;
 assign poisoned_o=state==POISON;
 assign reset_ready=por_ni&&state!=RESET;
 always @(posedge clk)begin
  if(!por_ni)begin
   state<=RESET;reset_hold<=1;sequence_o<=1;generation_o<=1;epoch_o<=1;
   acknowledged_o<=0;reset_age<=0;quiet_age<=0;
  end else if(reset_valid&&reset_ready)begin
   if(reset_sequence<=sequence_o||reset_generation<=generation_o||reset_epoch<=epoch_o)state<=POISON;
   else begin
    sequence_o<=reset_sequence;generation_o<=reset_generation;epoch_o<=reset_epoch;
    state<=RESET;reset_hold<=1;acknowledged_o<=0;reset_age<=0;quiet_age<=0;
   end
  end else if(fault&&state!=RESET)state<=POISON;
  else case(state)
   RESET:begin
    if(reset_age<MIN_RESET)reset_age<=reset_age+1;
    if(ack_valid)begin
     if(ack_mask==0||ack_sequence!=sequence_o||ack_epoch!=epoch_o||(acknowledged_o&ack_mask)!=0)state<=POISON;
     else acknowledged_o<=acknowledged_o|ack_mask;
    end
    if(&acknowledged_o&&reset_age>=MIN_RESET&&!ack_valid)begin reset_hold<=0;state<=QUIET;quiet_age<=0;end
   end
   QUIET:begin
    if(!providers_quiet)quiet_age<=0;
    else if(quiet_age==QUIET_CYCLES-1)begin state<=RELOAD;quiet_age<=0;end
    else quiet_age<=quiet_age+1;
   end
   RELOAD:if(reload_valid)begin
    if(prepared_mask==3'b111&&prepared_generation==generation_o&&providers_quiet)state<=RUN;
    else state<=POISON;
   end
   RUN:begin end
   default:begin end
  endcase
 end
endmodule
