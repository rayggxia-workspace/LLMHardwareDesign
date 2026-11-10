"""Two-owner real EXEC issuer from the serial guard, without a response FIFO."""
from pathlib import Path
p=Path(__file__).parent/'rtl'
s=(p/'bounded_serial_m_guard2.sv').read_text(encoding='utf-8')
h=s[:s.index('  typedef struct packed')].replace('module bounded_serial_m_guard2 #(', 'module m_dual_exec_issue #(').replace(",\n  parameter logic EXEC_ISSUE_PROFILE=1'b0",'')
h=h.replace('''  output logic native_valid,input logic native_ready,
  output logic [511:0] native_ticket,
  output logic [7:0] native_resource,native_service,
  output logic [255:0] native_payload,
''','''  // Prepared-record provider must already own exact W READY and A LOAD
  // leases. This issuer replays the lease; it does not synthesize those ACKs.
  output logic a_use_valid,input logic a_use_ready,
  output logic [127:0] a_use_key,output logic a_use_slot,
  output logic [15:0] a_use_generation,a_use_kk,a_use_sequence,
  output logic [31:0] a_use_record,a_use_session,
  // BEGIN/ALLOC/CANCEL/DRAIN/FENCE or pre-CREATE from the preparation FSM.
  // Frame owner is retained from offer (even ready=0) through actual EOP.
  input logic side_valid,output logic side_ready,input logic side_sop,side_eop,
  input logic [127:0] side_data,
  output logic lc_valid,input logic lc_ready,output logic lc_sop,lc_eop,
  output logic [127:0] lc_data,output logic tx_fault_valid,
''')
b=r'''
  logic native_valid,native_ready;
  logic [511:0] native_ticket;
  logic [7:0] native_resource,native_service;
  logic [255:0] native_payload;
  logic gi_valid,use_pending;
  logic exec_valid,exec_ready,exec_sop,exec_eop;
  logic [127:0] exec_data,exec_payload;
  logic held,held_exec,prefer_exec;
  logic [2:0] tx_index;
  logic payload_ready;
  logic [7:0] tx_fault_status;
  logic guard_quiescent;
  wire choose_exec=held?held_exec:(exec_valid&&(!side_valid||prefer_exec));
  assign lc_valid=choose_exec?exec_valid:side_valid;
  assign lc_sop=choose_exec?exec_sop:side_sop;
  assign lc_eop=choose_exec?exec_eop:side_eop;
  assign lc_data=choose_exec?exec_data:side_data;
  assign exec_ready=choose_exec&&lc_ready;
  assign side_ready=!choose_exec&&lc_ready;
  assign quiescent=guard_quiescent&&!held&&!use_pending&&!side_valid&&!exec_valid;

  always_comb begin
    exec_payload=0;
    exec_payload[1:0]=native_payload[145:144];
    exec_payload[17:2]=native_payload[161:146];
    exec_payload[33:18]=native_payload[177:162];
    exec_payload[49:34]=native_payload[127:112]-16'd128;
    exec_payload[65:50]=native_payload[210:195];
    exec_payload[66]=native_payload[178];
    exec_payload[82:67]=native_payload[194:179];
    exec_payload[88:83]=native_payload[239:234];
    exec_payload[120:89]=native_payload[95:64];
  end
  m_short_command_tx tx(.clk,.reset,.cmd_valid(native_valid),.cmd_ready(native_ready),
    .cmd_opcode(4'd3),.cmd_scope(native_payload[99:96]),.cmd_scope_generation(native_payload[233:218]),
    .cmd_high16(16'd0),.cmd_session(native_payload[31:0]),.cmd_record(native_payload[63:32]),.cmd_bank(2'd0),
    .word_index(tx_index),.payload_valid(1'b1),.payload_ready,.payload_data(exec_payload),
    .lc_valid(exec_valid),.lc_ready(exec_ready),.lc_sop(exec_sop),.lc_eop(exec_eop),.lc_data(exec_data),
    .reject_valid(tx_fault_valid),.reject_ready(1'b0),.reject_status(tx_fault_status));

  // The guard keeps native_ticket/payload tied to lane_slot until matched
  // INPUT EOP. Only this single arm bit is new; no duplicate wide ticket.
  assign a_use_valid=use_pending;
  assign a_use_key=native_ticket[255:128];
  assign a_use_slot=native_payload[178];
  assign a_use_generation=native_payload[194:179];
  assign a_use_kk=native_payload[210:195];
  assign a_use_sequence=native_payload[177:162];
  assign a_use_record=native_payload[63:32];
  assign a_use_session=native_payload[31:0];
  assign input_consumed_valid=gi_valid&&!use_pending;
  always_ff @(posedge clk)begin
    if(reset)begin held<=0;held_exec<=0;prefer_exec<=0;use_pending<=0;end
    else begin
      if(lc_valid)begin
        if(lc_ready&&lc_eop)begin held<=0;prefer_exec<=!choose_exec;end
        else if(!held)begin held<=1;held_exec<=choose_exec;end
      end
      if(native_valid&&native_ready)use_pending<=1;
      if(a_use_valid&&a_use_ready)use_pending<=0;
    end
  end
  bounded_serial_m_guard2 #(.ABI_ID(ABI_ID),.TOPOLOGY(TOPOLOGY),.CAPACITY(CAPACITY),
    .NUMERIC_ID(NUMERIC_ID),.LAYOUT_ID(LAYOUT_ID),.EXEC_ISSUE_PROFILE(1'b1)) guard(
    .clk,.reset,.cmd_valid,.cmd_ready,.cmd_ticket,.cmd_job_key,.cmd_abi,.cmd_topology,.cmd_capacity,.cmd_numeric,.cmd_layout,
    .cmd_resource,.cmd_service,.cmd_provider,.cmd_function,.cmd_native_op,.cmd_payload,.cmd_stored,.cmd_store_words,.cmd_destination,
    .native_valid,.native_ready,.native_ticket,.native_resource,.native_service,.native_payload,
    .lr_valid,.lr_ready,.lr_sop,.lr_eop,.lr_data,
    .input_consumed_valid(gi_valid),.input_consumed_ready(input_consumed_ready&&!use_pending),.input_consumed_ticket,.input_consumed_error,
    .native_abort_valid,.native_abort_ready,.native_abort_ticket,.native_abort_next_k,.native_abort_error,
    .control_valid,.control_ready,.control_sop,.control_eop,.control_data,.cancel_drained_valid,.cancel_drained_ready,.cancel_drained_ticket,
    .s_valid,.s_ready,.s_ticket,.s_word,.s_address,.s_data,.ack_valid,.ack_ready,.ack_ticket,.ack_word,.ack_error,
    .terminal_valid,.terminal_ready,.terminal_ticket,.terminal_error,.terminal_stored,.terminal_partial,.terminal_data,
    .cancel_valid,.cancel_job_key,.cancel_one_valid,.cancel_one_ready,.cancel_one_ticket,.timeout_valid,.clear_quarantine,.resume_after_drain,
    .halted,.quarantine,.quiescent(guard_quiescent),.occupied_slots,.result_slots_occupied,.rejected_protocol_events,.committed_words);
  wire unused_native_diagnostics=^{native_resource,native_service,native_ticket[511:256],native_ticket[127:0],
      native_payload[255:240],native_payload[217:211],native_payload[143:128],native_payload[111:100],tx_index,payload_ready,tx_fault_status};
endmodule
'''
(p/'m_dual_exec_issue.sv').write_text(h+b,encoding='utf-8')
