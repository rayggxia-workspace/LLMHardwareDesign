`timescale 1ns/1ps
// Internal LC/native boundary, not a new 512bit leaf-macro interface.
// Command metadata: two slots. Result data: independent 2x32B FIFO.
// Native engine can compute #2 while commit engine waits for #1's S ACK.
module bounded_service_guard #(
  parameter logic [31:0] ABI_ID=32'h02500001, TOPOLOGY=32'd25001,
  parameter logic [31:0] CAPACITY=32'd1, NUMERIC_ID=32'h53333251,
  parameter logic [31:0] LAYOUT_ID=32'h4b313633
)(
  input logic clk,reset,
  input logic cmd_valid,output logic cmd_ready,
  input logic [511:0] cmd_ticket,input logic [127:0] cmd_job_key,
  input logic [31:0] cmd_abi,cmd_topology,cmd_capacity,cmd_numeric,cmd_layout,
  input logic [7:0] cmd_resource,cmd_service,cmd_provider,cmd_function,
  input logic [15:0] cmd_native_op,input logic [255:0] cmd_payload,
  input logic cmd_stored,input logic [1:0] cmd_store_words,
  input logic [9:0] cmd_destination,
  output logic native_valid,input logic native_ready,
  output logic [511:0] native_ticket,
  output logic [7:0] native_resource,native_service,
  output logic [255:0] native_payload,
  input logic result_valid,output logic result_ready,
  input logic [511:0] result_ticket,input logic [255:0] result_data,
  input logic result_error,
  output logic s_valid,input logic s_ready,output logic [511:0] s_ticket,
  output logic s_word,output logic [9:0] s_address,output logic [127:0] s_data,
  input logic ack_valid,output logic ack_ready,input logic [511:0] ack_ticket,
  input logic ack_word,ack_error,
  output logic terminal_valid,input logic terminal_ready,
  output logic [511:0] terminal_ticket,output logic [7:0] terminal_error,
  output logic terminal_stored,terminal_partial,output logic [255:0] terminal_data,
  input logic cancel_valid,input logic [127:0] cancel_job_key,
  input logic timeout_valid,clear_quarantine,resume_after_drain,
  output logic halted,quarantine,quiescent,
  output logic [1:0] occupied_slots,result_slots_occupied,
  output logic [31:0] rejected_protocol_events,committed_words
);
  typedef struct packed {
    logic [511:0] ticket;logic [127:0] job_key;
    logic [31:0] abi_id,topology,capacity,numeric_id,layout_id;
    logic [7:0] resource_id,service_id,provider_id,function_id;
    logic [15:0] native_op;logic [255:0] payload;
    logic stored;logic [1:0] store_words;logic [9:0] destination;
  } command_t;
  command_t slots[2];
  logic head,tail,issue_pointer,active_slot;
  logic [1:0] count,live,issued;
  logic [255:0] result_fifo[2];
  logic result_owner[2];
  logic [7:0] result_failure[2];
  logic result_head,result_tail;
  logic [1:0] result_count;
  typedef enum logic [1:0] {N_IDLE,N_ISSUE,N_WAIT} native_state_t;
  typedef enum logic [1:0] {C_IDLE,C_REQUEST,C_ACK,C_TERMINAL} commit_state_t;
  native_state_t ns;
  commit_state_t cs;
  logic piece,stored_q,partial_q;
  logic [7:0] error_q;
  logic cancelled_epoch_valid;
  logic [31:0] cancelled_generation,cancelled_epoch;
  wire owner=result_owner[result_head];
  wire command_push=cmd_valid&&cmd_ready;
  wire terminal_pop=terminal_valid&&terminal_ready;
  wire cancel_match=cancel_valid&&count!=0&&cancel_job_key==slots[head].job_key;
  wire stop_now=halted||cancel_match;
  wire registered_service=
      (slots[issue_pointer].resource_id==0&&slots[issue_pointer].service_id==32)||
      (slots[issue_pointer].resource_id==2&&slots[issue_pointer].service_id==32)||
      (slots[issue_pointer].resource_id==5&&
       (slots[issue_pointer].service_id==32||slots[issue_pointer].service_id==33));
  wire header_ok=slots[issue_pointer].abi_id==ABI_ID&&
      slots[issue_pointer].topology==TOPOLOGY&&slots[issue_pointer].capacity==CAPACITY&&
      slots[issue_pointer].numeric_id==NUMERIC_ID&&slots[issue_pointer].layout_id==LAYOUT_ID&&
      slots[issue_pointer].native_op==0&&registered_service&&
      slots[issue_pointer].provider_id==1&&slots[issue_pointer].function_id==0&&
      (!cancelled_epoch_valid||
       slots[issue_pointer].job_key[127:96]>cancelled_generation||
       (slots[issue_pointer].job_key[127:96]==cancelled_generation&&
        slots[issue_pointer].job_key[63:32]>cancelled_epoch))&&
      ((!slots[issue_pointer].stored&&slots[issue_pointer].store_words==0)||
       (slots[issue_pointer].stored&&
        (slots[issue_pointer].store_words==1||slots[issue_pointer].store_words==2)&&
        {1'b0,slots[issue_pointer].destination}+{9'd0,slots[issue_pointer].store_words}<=11'd1024));
  wire issue_available=live[issue_pointer]&&!issued[issue_pointer]&&result_count<2;
  wire synthetic_result=ns==N_IDLE&&issue_available&&(stop_now||!header_ok);
  wire matching_result=ns==N_WAIT&&result_ticket==slots[active_slot].ticket;
  wire provider_result=result_valid&&result_ready&&matching_result;
  wire result_push=synthetic_result||provider_result;
  wire bad_cancel=cancel_valid&&!cancel_match;
  wire bad_timeout=timeout_valid&&!stop_now;
  wire bad_clear=clear_quarantine&&!quiescent;
  wire bad_resume=resume_after_drain&&!(quiescent&&!quarantine);
  wire bad_result=result_valid&&result_ready&&!matching_result;
  wire matching_ACK=cs==C_ACK&&ack_ticket==slots[owner].ticket&&ack_word==piece;
  wire bad_ACK=ack_valid&&ack_ready&&!matching_ACK;
  wire [2:0] rejected_now={2'b0,bad_cancel}+{2'b0,bad_timeout}+
      {2'b0,bad_clear}+{2'b0,bad_resume}+{2'b0,bad_result}+{2'b0,bad_ACK};
  assign cmd_ready=!reset&&!stop_now&&!quarantine&&count<2&&
      (count==0||cmd_job_key==slots[head].job_key);
  assign native_valid=!reset&&ns==N_ISSUE;
  assign native_ticket=slots[active_slot].ticket;
  assign native_resource=slots[active_slot].resource_id;
  assign native_service=slots[active_slot].service_id;
  assign native_payload=slots[active_slot].payload;
  assign result_ready=!reset&&(!matching_result||result_count<2);
  assign ack_ready=!reset;
  assign s_valid=!reset&&cs==C_REQUEST;
  assign s_ticket=slots[owner].ticket;
  assign s_word=piece;
  assign s_address=slots[owner].destination+{9'd0,piece};
  assign s_data=piece?result_fifo[result_head][255:128]:result_fifo[result_head][127:0];
  assign terminal_valid=!reset&&cs==C_TERMINAL;
  assign terminal_ticket=slots[owner].ticket;
  assign terminal_error=error_q;
  assign terminal_stored=stored_q;
  assign terminal_partial=partial_q;
  assign terminal_data=result_fifo[result_head];
  assign occupied_slots=count;
  assign result_slots_occupied=result_count;
  assign quiescent=count==0&&result_count==0&&ns==N_IDLE&&cs==C_IDLE;
  always_ff @(posedge clk) begin
    if(reset) begin
      head<=0;tail<=0;issue_pointer<=0;active_slot<=0;count<=0;live<=0;issued<=0;
      result_head<=0;result_tail<=0;result_count<=0;ns<=N_IDLE;cs<=C_IDLE;
      piece<=0;stored_q<=0;partial_q<=0;error_q<=0;halted<=0;quarantine<=0;
      rejected_protocol_events<=0;committed_words<=0;
      cancelled_epoch_valid<=0;cancelled_generation<=0;cancelled_epoch<=0;
      for(integer i=0;i<2;i=i+1) begin slots[i]<='0;result_fifo[i]<=0;result_owner[i]<=0;result_failure[i]<=0;end
    end else begin
      case({command_push,terminal_pop})
        2'b10:count<=count+1'b1;
        2'b01:count<=count-1'b1;
        default:;
      endcase
      case({result_push,terminal_pop})
        2'b10:result_count<=result_count+1'b1;
        2'b01:result_count<=result_count-1'b1;
        default:;
      endcase
      if(command_push) begin
        slots[tail]<='{cmd_ticket,cmd_job_key,cmd_abi,cmd_topology,cmd_capacity,
          cmd_numeric,cmd_layout,cmd_resource,cmd_service,cmd_provider,cmd_function,
          cmd_native_op,cmd_payload,cmd_stored,cmd_store_words,cmd_destination};
        live[tail]<=1;issued[tail]<=0;tail<=!tail;
      end
      if(terminal_pop) begin
        live[owner]<=0;head<=!head;result_head<=!result_head;
      end
      if(result_push) begin
        result_owner[result_tail]<=synthetic_result?issue_pointer:active_slot;
        result_fifo[result_tail]<=synthetic_result?256'd0:result_data;
        result_failure[result_tail]<=synthetic_result?(stop_now?8'd5:8'd1):
            (result_error?8'd2:(stop_now?8'd5:8'd0));
        result_tail<=!result_tail;
      end
      if(cancel_match) begin
        halted<=1;cancelled_epoch_valid<=1;
        cancelled_generation<=slots[head].job_key[127:96];
        cancelled_epoch<=slots[head].job_key[63:32];
      end
      if(rejected_now!=0) rejected_protocol_events<=rejected_protocol_events+{29'd0,rejected_now};
      if(timeout_valid&&stop_now) quarantine<=1;
      if(clear_quarantine&&quiescent) quarantine<=0;
      if(resume_after_drain&&quiescent&&!quarantine) halted<=0;
      case(ns)
        N_IDLE:if(issue_available) begin
          if(synthetic_result) begin issued[issue_pointer]<=1;issue_pointer<=!issue_pointer;end
          else begin active_slot<=issue_pointer;ns<=N_ISSUE;end
        end
        N_ISSUE:if(native_valid&&native_ready) begin issued[active_slot]<=1;ns<=N_WAIT;end
        N_WAIT:if(provider_result) begin issue_pointer<=!active_slot;ns<=N_IDLE;end
        default:ns<=N_IDLE;
      endcase
      case(cs)
        C_IDLE:if(result_count!=0) begin
          piece<=0;stored_q<=0;partial_q<=0;error_q<=result_failure[result_head];
          if(result_failure[result_head]!=0) cs<=C_TERMINAL;
          else if(stop_now) begin error_q<=8'd5;cs<=C_TERMINAL;end
          else if(slots[owner].stored) cs<=C_REQUEST;
          else cs<=C_TERMINAL;
        end
        // Proffered writes remain valid until acceptance even after cancellation.
        C_REQUEST:if(s_valid&&s_ready) cs<=C_ACK;
        C_ACK:if(ack_valid&&ack_ready&&matching_ACK) begin
          if(ack_error) begin error_q<=8'd3;cs<=C_TERMINAL;end
          else begin
            committed_words<=committed_words+1'b1;partial_q<=1;
            if(stop_now) begin error_q<=8'd5;cs<=C_TERMINAL;end
            else if((!piece&&slots[owner].store_words==1)||piece) begin stored_q<=1;partial_q<=0;cs<=C_TERMINAL;end
            else begin piece<=1;cs<=C_REQUEST;end
          end
        end
        C_TERMINAL:if(terminal_pop) cs<=C_IDLE;
        default:cs<=C_IDLE;
      endcase
    end
  end
endmodule
