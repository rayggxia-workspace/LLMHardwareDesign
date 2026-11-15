`timescale 1ns/1ps
// Internal 512bit control records, physical transport 128bit. No speculative
// task acceptance: core_ready only on the real fourth transmit handshake.
// Receive storage is exactly ONE 64B frame, never an unbounded return queue.
module mc_packet128_bridge(
  input logic clk,reset,
  input logic core_task_valid,output logic core_task_ready,
  input logic [511:0] core_task_packet,
  input logic [7:0] core_task_target,
  input logic core_task_credit,
  output logic tx_valid,input logic tx_ready,
  output logic [127:0] tx_data,
  output logic [7:0] tx_target,
  output logic tx_sop,tx_eop,tx_credit,
  input logic rx_valid,output logic rx_ready,
  input logic [127:0] rx_data,
  input logic [7:0] rx_source,
  input logic rx_sop,rx_eop,
  output logic core_return_valid,input logic core_return_ready,
  output logic [511:0] core_return_packet,
  output logic drained,
  output logic [31:0] frame_fault_count
);
  typedef enum logic [1:0] {IDLE,COLLECT,DROP} rx_state_t;
  rx_state_t rx_state;
  logic [1:0] tx_word,rx_word;
  logic [7:0] source;
  logic full;
  logic [511:0] packet;
  wire rx_fire=rx_valid&&rx_ready;
  assign tx_valid=!reset&&core_task_valid;
  assign tx_data=core_task_packet[128*tx_word+:128];
  assign tx_target=core_task_target;
  assign tx_sop=tx_word==0;
  assign tx_eop=tx_word==3;
  assign tx_credit=core_task_credit;
  assign core_task_ready=!reset&&tx_word==3&&tx_ready;
  assign rx_ready=!reset&&!full;
  assign core_return_valid=!reset&&full;
  assign core_return_packet=packet;
  assign drained=!reset&&tx_word==0&&!core_task_valid&&rx_state==IDLE&&!full;
  task automatic malformed_complete;
    begin
      // Version zero is guaranteed to fail MC packet admission. No source,
      // token or payload from a malformed frame is trusted to retire an owner.
      packet<=0;full<=1;rx_state<=IDLE;rx_word<=0;
      if(frame_fault_count!=32'hffffffff) frame_fault_count<=frame_fault_count+1;
    end
  endtask
  always_ff @(posedge clk) begin
    if(reset) begin
      rx_state<=IDLE;tx_word<=0;rx_word<=0;source<=0;full<=0;packet<=0;frame_fault_count<=0;
    end else begin
      if(tx_valid&&tx_ready) tx_word<=tx_word+1'b1;
      if(core_return_valid&&core_return_ready) full<=0;
      if(rx_fire) case(rx_state)
        IDLE: begin
          if(rx_sop&&!rx_eop&&rx_source<9&&rx_data[24+:8]==rx_source) begin
            packet[127:0]<=rx_data;source<=rx_source;rx_word<=1;rx_state<=COLLECT;
          end else if(rx_eop) malformed_complete();
          else rx_state<=DROP;
        end
        COLLECT: begin
          if(rx_sop || rx_source!=source || rx_eop!=(rx_word==3)) begin
            if(rx_eop) malformed_complete();else rx_state<=DROP;
          end else begin
            packet[128*rx_word+:128]<=rx_data;
            if(rx_word==3) begin full<=1;rx_state<=IDLE;rx_word<=0;end
            else rx_word<=rx_word+1'b1;
          end
        end
        DROP: if(rx_eop) malformed_complete();
        default: rx_state<=DROP;
      endcase
    end
  end
endmodule
