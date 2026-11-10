`timescale 1ns/1ps
// Streaming product-M response → existing two-entry guard; no assembly FIFO.
// Command metadata: two slots. Result data: independent 2x32B FIFO.
// Native engine can compute #2 while commit engine waits for #1's S ACK.
module bounded_serial_m_guard2 #(
  parameter logic [31:0] ABI_ID=32'h02500001, TOPOLOGY=32'd25001,
  parameter logic [31:0] CAPACITY=32'd1, NUMERIC_ID=32'h53333251,
  parameter logic [31:0] LAYOUT_ID=32'h4b313633,
  parameter logic EXEC_ISSUE_PROFILE=1'b0
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
  // Product M ABI 0x02504d02 response; no assembly data FIFO.
  input logic lr_valid,output logic lr_ready,
  input logic lr_sop,lr_eop,input logic [127:0] lr_data,
  output logic input_consumed_valid,input logic input_consumed_ready,
  output logic [511:0] input_consumed_ticket,output logic input_consumed_error,
  output logic native_abort_valid,input logic native_abort_ready,
  output logic [511:0] native_abort_ticket,output logic [15:0] native_abort_next_k,output logic native_abort_error,
  // Other native control frames go directly to the finite service FSM.
  output logic control_valid,input logic control_ready,
  output logic control_sop,control_eop,output logic [127:0] control_data,
  // The coordinator may complete cancellation only after native ABORT identity,
  // A/raw flush and actual outstanding DMA/transport drain have all joined.
  input logic cancel_drained_valid,output logic cancel_drained_ready,
  input logic [511:0] cancel_drained_ticket,
  output logic s_valid,input logic s_ready,output logic [511:0] s_ticket,
  output logic s_word,output logic [9:0] s_address,output logic [127:0] s_data,
  input logic ack_valid,output logic ack_ready,input logic [511:0] ack_ticket,
  input logic ack_word,ack_error,
  output logic terminal_valid,input logic terminal_ready,
  output logic [511:0] terminal_ticket,output logic [7:0] terminal_error,
  output logic terminal_stored,terminal_partial,output logic [255:0] terminal_data,
  input logic cancel_valid,input logic [127:0] cancel_job_key,

  // Per-ticket native cancellation is independent of whole-job cancellation.
  input logic cancel_one_valid,output logic cancel_one_ready,
  input logic [511:0] cancel_one_ticket,
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
  logic [1:0] count,live,issued,waiting_rf,result_have,cancelled_slots;
  logic [255:0] result_fifo[2];
  logic [7:0] result_failure[2];
  logic [1:0] result_count;
  typedef enum logic {N_IDLE,N_ISSUE} native_state_t;
  typedef enum logic [1:0] {C_IDLE,C_REQUEST,C_ACK,C_TERMINAL} commit_state_t;
  native_state_t ns;commit_state_t cs;
  logic lane_busy,lane_slot;
  logic piece,stored_q,partial_q;
  logic [7:0] error_q;
  logic cancelled_epoch_valid;
  logic [31:0] cancelled_generation,cancelled_epoch;
  wire owner=head;
  wire command_push=cmd_valid&&cmd_ready;
  wire terminal_pop=terminal_valid&&terminal_ready;
  wire cancel_match=cancel_valid&&count!=0&&cancel_job_key==slots[head].job_key;
  wire stop_now=halted||cancel_match;
  logic cancel_one_found,cancel_one_slot;
  always_comb begin
    cancel_one_found=0;cancel_one_slot=0;
    for(integer i=0;i<2;i=i+1)if(live[i]&&cancel_one_ticket==slots[i].ticket)begin cancel_one_found=1;cancel_one_slot=1'(i);end
  end
  assign cancel_one_ready=!reset;
  wire cancel_one_fire=cancel_one_valid&&cancel_one_ready&&cancel_one_found;
  wire issue_stopped=stop_now||cancelled_slots[issue_pointer]||(cancel_one_fire&&cancel_one_slot==issue_pointer);
  wire owner_stopped=stop_now||cancelled_slots[owner]||(cancel_one_fire&&cancel_one_slot==owner);

  wire [255:218] issue_frame_metadata=slots[issue_pointer].payload[255:218];
  wire [15:0] issue_next_k=slots[issue_pointer].payload[127:112];
  wire issue_profile_ok=EXEC_ISSUE_PROFILE ?
      (issue_frame_metadata[255:240]==0&&issue_frame_metadata[239:234]<=17&&issue_frame_metadata[233:218]!=0&&
       slots[issue_pointer].payload[217]&&slots[issue_pointer].payload[213:211]==3'd2&&
       slots[issue_pointer].payload[215]==slots[issue_pointer].payload[216]&&
       slots[issue_pointer].ticket[511:384]==slots[issue_pointer].job_key&&
       slots[issue_pointer].ticket[63:0]==slots[issue_pointer].payload[63:0]&&
       issue_next_k>=128&&issue_next_k[6:0]==0&&issue_next_k<=slots[issue_pointer].payload[143:128]&&
       slots[issue_pointer].payload[210:195]==(issue_next_k>>7)-16'd1&&
       slots[issue_pointer].payload[103:100]!=0&&slots[issue_pointer].payload[103:100]<=8&&
       (slots[issue_pointer].payload[111:104]==16||slots[issue_pointer].payload[111:104]==128)) :
      issue_frame_metadata==0;
  wire registered_service=slots[issue_pointer].resource_id==0&&slots[issue_pointer].service_id==32;
  wire header_ok=slots[issue_pointer].abi_id==ABI_ID&&
      slots[issue_pointer].topology==TOPOLOGY&&slots[issue_pointer].capacity==CAPACITY&&
      slots[issue_pointer].numeric_id==NUMERIC_ID&&slots[issue_pointer].layout_id==LAYOUT_ID&&
      slots[issue_pointer].native_op==0&&registered_service&&
      slots[issue_pointer].provider_id==1&&slots[issue_pointer].function_id==0&&
      issue_profile_ok&&slots[issue_pointer].payload[31:0]!=0&&
      !(live[!issue_pointer]&&slots[!issue_pointer].payload[63:0]==slots[issue_pointer].payload[63:0])&&
      slots[issue_pointer].payload[216]==slots[issue_pointer].stored&&
      (!slots[issue_pointer].stored||slots[issue_pointer].store_words==2)&&
      (!cancelled_epoch_valid||
       slots[issue_pointer].job_key[127:96]>cancelled_generation||
       (slots[issue_pointer].job_key[127:96]==cancelled_generation&&
        slots[issue_pointer].job_key[63:32]>cancelled_epoch))&&
      ((!slots[issue_pointer].stored&&slots[issue_pointer].store_words==0)||
       (slots[issue_pointer].stored&&
        (slots[issue_pointer].store_words==1||slots[issue_pointer].store_words==2)&&
        {1'b0,slots[issue_pointer].destination}+{9'd0,slots[issue_pointer].store_words}<=11'd1024));

  wire issue_available=live[issue_pointer]&&!issued[issue_pointer]&&!result_have[issue_pointer];
  wire synthetic_result=ns==N_IDLE&&issue_available&&(issue_stopped||!header_ok);
  typedef enum logic [3:0] {R_IDLE,R_META,R_LOW,R_HIGH,R_DROP,R_CONTROL,R_ABORT_META,R_ABORT_KEY,R_ABORT_OWNER} stream_state_t;
  stream_state_t stream_state;
  logic stream_slot,serial_reserved;
  logic [1:0] input_seen,abort_seen,abort_delivered,early_rf_error,abort_error;
  logic [15:0] abort_next[2];
  logic [7:0] serial_event,serial_status;
  logic serial_snapshot;
  logic lookup_found,lookup_slot,drain_found,drain_slot,abort_found,abort_slot;
  always_comb begin
    lookup_found=0;lookup_slot=0;drain_found=0;drain_slot=0;abort_found=0;abort_slot=0;
    for(integer i=1;i>=0;i=i-1)begin
      if(live[i]&&issued[i]&&waiting_rf[i]&&lr_data[79:48]==slots[i].payload[31:0]&&lr_data[111:80]==slots[i].payload[63:32])begin lookup_found=1;lookup_slot=1'(i);end
      if(live[i]&&waiting_rf[i]&&cancel_drained_ticket==slots[i].ticket)begin drain_found=1;drain_slot=1'(i);end
      if(live[i]&&abort_seen[i]&&!abort_delivered[i])begin abort_found=1;abort_slot=1'(i);end
    end
  end
  wire response_slot=stream_state==R_IDLE?lookup_slot:stream_slot;
  wire [217:64] expected=slots[response_slot].payload[217:64];
  wire response_stopped=stop_now||cancelled_slots[response_slot]||(cancel_one_fire&&cancel_one_slot==response_slot);
  wire [127:0] rf_meta={14'b0,expected[177:162],expected[161:146],expected[145:144],
      expected[95:64],expected[143:128],expected[127:112],expected[111:104],expected[103:100],expected[99:96]};
  wire [127:0] rf_error_meta={14'b0,expected[177:162],expected[161:146],expected[145:144],
      expected[95:64],44'd0,expected[99:96]};
  wire [127:0] input_meta={29'b0,expected[95:64],expected[210:195],expected[194:179],
      expected[178],expected[177:162],expected[161:146],expected[145:144]};
  wire [7:0] incoming_event=lr_data[39:32],incoming_status=lr_data[47:40];
  wire [15:0] incoming_flags=lr_data[127:112];
  wire [11:0] expected_rf_flags={1'b0,expected[213:211],expected[99:96],2'b0,expected[215],expected[216]};
  wire native_header=lookup_found&&lr_sop&&!lr_eop&&!expected[214]&&lr_data[31:0]==32'h02504d02;
  wire input_header=native_header&&incoming_event==3&&incoming_flags==16'h2000&&!input_seen[response_slot]&&expected[217];
  wire rf_header=native_header&&incoming_event==4&&!early_rf_error[response_slot]&&
      (!expected[217]||input_seen[response_slot]||incoming_status!=0)&&
      ((incoming_status==0&&incoming_flags[11:0]==expected_rf_flags&&incoming_flags[15:12]==(expected[216]?4'd4:4'd2))||
       (incoming_status==1&&incoming_flags[15:12]==2&&incoming_flags[11:2]==expected_rf_flags[11:2]&&incoming_flags[1:0]==0));
  wire abort_header=native_header&&incoming_event==5&&(incoming_status==0||incoming_status==1)&&incoming_flags==16'h4000&&response_stopped&&expected[217]&&!abort_seen[response_slot];
  wire abort_meta_ok=!lr_sop&&!lr_eop&&lr_data[3:0]==expected[99:96]&&lr_data[15:4]==0&&lr_data[127:32]==0&&
      ((serial_status==1&&lr_data[31:16]==0)||
       (serial_status==0&&expected[127:112]>=128&&lr_data[31:16]<=expected[127:112]&&
        lr_data[31:16]>=expected[127:112]-16'd128&&(expected[111:104]==16?lr_data[19:16]==0:lr_data[22:16]==0)));
  wire side_context_control=EXEC_ISSUE_PROFILE&&incoming_event==4&&lr_data[111:80]==0&&
      incoming_flags[15:12]==2&&incoming_flags[1:0]==0&&(incoming_flags[10:8]==0||incoming_flags[10:8]==4);
  wire control_header=lr_sop&&!lr_eop&&lr_data[31:0]==32'h02504d02&&
      (((incoming_event==1||incoming_event==2||incoming_event==6||incoming_event==8||incoming_event==9||incoming_event==10)&&incoming_flags[15:12]==2)||
       (incoming_event==5&&incoming_flags[15:12]==4)||(incoming_event==7&&incoming_flags[15:12]==3)||side_context_control);
  wire meta_matches=(serial_event==3)?lr_data==input_meta:lr_data==(serial_status==0?rf_meta:rf_error_meta);
  wire meta_framed=!lr_sop&&lr_eop==!serial_snapshot;
  wire input_end=stream_state==R_META&&serial_event==3&&meta_matches&&meta_framed;
  wire serial_complete=lr_valid&&lr_ready&&
      ((stream_state==R_META&&serial_event==4&&meta_matches&&meta_framed&&!serial_snapshot)||
       (stream_state==R_HIGH&&!lr_sop&&lr_eop));
  wire serial_bad=lr_valid&&lr_ready&&
      ((stream_state==R_IDLE&&!input_header&&!rf_header&&!abort_header&&!control_header)||
       (stream_state==R_META&&(!meta_matches||!meta_framed))||
       (stream_state==R_LOW&&(lr_sop||lr_eop))||(stream_state==R_HIGH&&(lr_sop||!lr_eop))||
       (stream_state==R_ABORT_META&&!abort_meta_ok)||
       (stream_state==R_ABORT_KEY&&(lr_sop||lr_eop||lr_data!=slots[stream_slot].ticket[255:128]))||
       (stream_state==R_ABORT_OWNER&&(lr_sop||!lr_eop||lr_data!=slots[stream_slot].ticket[383:256])));
  assign cancel_drained_ready=!reset&&stream_state==R_IDLE&&(!drain_found||!result_have[drain_slot]);
  wire cancelled_result=cancel_drained_valid&&cancel_drained_ready&&drain_found&&
      (stop_now||cancelled_slots[drain_slot]||(cancel_one_fire&&cancel_one_slot==drain_slot))&&abort_seen[drain_slot]&&abort_delivered[drain_slot];
  // An early RF error owns no payload and cannot release the lane before
  // real INPUT EOP or matching CANCEL/ABORT/DRAIN. Hold the original owner.
  wire early_error_now=serial_complete&&serial_status!=0&&expected[217]&&!input_seen[stream_slot];
  wire drained_error=lr_valid&&lr_ready&&input_end&&early_rf_error[stream_slot];
  wire provider_result=(serial_complete&&!early_error_now)||drained_error||cancelled_result;
  wire provider_owner=cancelled_result?drain_slot:stream_slot;
  wire provider_stopped=stop_now||cancelled_slots[provider_owner]||(cancel_one_fire&&cancel_one_slot==provider_owner);
  wire bad_cancel=cancel_valid&&!cancel_match;
  wire bad_one=cancel_one_valid&&cancel_one_ready&&!cancel_one_found;
  wire bad_timeout=timeout_valid&&!stop_now;
  wire bad_clear=clear_quarantine&&!quiescent;
  wire bad_resume=resume_after_drain&&!(quiescent&&!quarantine);
  wire bad_result=serial_bad||(cancel_drained_valid&&cancel_drained_ready&&!cancelled_result);
  wire matching_ACK=cs==C_ACK&&ack_ticket==slots[owner].ticket&&ack_word==piece;
  wire bad_ACK=ack_valid&&ack_ready&&!matching_ACK;
  wire [2:0] rejected_now={2'b0,bad_cancel}+{2'b0,bad_one}+{2'b0,bad_timeout}+{2'b0,bad_clear}+
      {2'b0,bad_resume}+{2'b0,bad_result}+{2'b0,bad_ACK};
  assign cmd_ready=!reset&&!stop_now&&!quarantine&&count<2&&(count==0||cmd_job_key==slots[head].job_key);
  assign native_valid=!reset&&ns==N_ISSUE;
  assign native_ticket=slots[active_slot].ticket;assign native_resource=slots[active_slot].resource_id;
  assign native_service=slots[active_slot].service_id;assign native_payload=slots[active_slot].payload;
  assign input_consumed_valid=!reset&&lr_valid&&input_end;
  assign input_consumed_ticket=slots[stream_slot].ticket;assign input_consumed_error=serial_status!=0;
  assign native_abort_valid=!reset&&abort_found;
  assign native_abort_ticket=slots[abort_slot].ticket;assign native_abort_next_k=abort_next[abort_slot];
  assign native_abort_error=abort_error[abort_slot];
  assign control_valid=!reset&&lr_valid&&(stream_state==R_CONTROL||(stream_state==R_IDLE&&control_header&&!abort_header));
  assign control_sop=lr_sop;assign control_eop=lr_eop;assign control_data=lr_data;
  always_comb begin
    lr_ready=!reset;
    if(stream_state==R_IDLE)begin
      if(control_header&&!abort_header)lr_ready=!reset&&control_ready;
      else if(rf_header)lr_ready=!reset&&!result_have[lookup_slot];
    end else if(stream_state==R_CONTROL)lr_ready=!reset&&control_ready;
    else if(input_end)lr_ready=!reset&&input_consumed_ready;
  end
  assign ack_ready=!reset;
  assign s_valid=!reset&&cs==C_REQUEST;assign s_ticket=slots[owner].ticket;
  assign s_word=piece;assign s_address=slots[owner].destination+{9'd0,piece};
  assign s_data=piece?result_fifo[owner][255:128]:result_fifo[owner][127:0];
  assign terminal_valid=!reset&&cs==C_TERMINAL;assign terminal_ticket=slots[owner].ticket;
  assign terminal_error=error_q;assign terminal_stored=stored_q;assign terminal_partial=partial_q;assign terminal_data=result_fifo[owner];
  assign occupied_slots=count;
  assign result_count={1'b0,result_have[0]}+{1'b0,result_have[1]};
  assign result_slots_occupied=result_count+{1'b0,serial_reserved};
  assign quiescent=count==0&&result_count==0&&ns==N_IDLE&&!lane_busy&&cs==C_IDLE&&stream_state==R_IDLE;
  always_ff @(posedge clk)begin
    if(reset)begin
      head<=0;tail<=0;issue_pointer<=0;active_slot<=0;count<=0;live<=0;issued<=0;waiting_rf<=0;result_have<=0;cancelled_slots<=0;
      ns<=N_IDLE;cs<=C_IDLE;lane_busy<=0;lane_slot<=0;piece<=0;stored_q<=0;partial_q<=0;error_q<=0;
      halted<=0;quarantine<=0;rejected_protocol_events<=0;committed_words<=0;cancelled_epoch_valid<=0;cancelled_generation<=0;cancelled_epoch<=0;
      stream_state<=R_IDLE;stream_slot<=0;serial_reserved<=0;serial_event<=0;serial_status<=0;serial_snapshot<=0;
      input_seen<=0;abort_seen<=0;abort_delivered<=0;early_rf_error<=0;abort_error<=0;
      for(integer i=0;i<2;i=i+1)begin slots[i]<='0;result_fifo[i]<=0;result_failure[i]<=0;abort_next[i]<=0;end
    end else begin
      if(native_abort_valid&&native_abort_ready)abort_delivered[abort_slot]<=1;
      if(lr_valid&&lr_ready)case(stream_state)
        R_IDLE:begin
          if(abort_header)begin stream_slot<=lookup_slot;serial_status<=incoming_status;stream_state<=R_ABORT_META;end
          else if(control_header)stream_state<=R_CONTROL;
          else if(input_header||rf_header)begin
            stream_slot<=lookup_slot;stream_state<=R_META;serial_event<=incoming_event;serial_status<=incoming_status;
            serial_snapshot<=incoming_event==4&&incoming_flags[0];serial_reserved<=incoming_event==4;
          end else stream_state<=lr_eop?R_IDLE:R_DROP;
        end
        R_META:begin
          if(!meta_matches||!meta_framed)begin serial_reserved<=0;stream_state<=lr_eop?R_IDLE:R_DROP;end
          else if(serial_event==3)begin
            input_seen[stream_slot]<=1;if(lane_busy&&lane_slot==stream_slot)lane_busy<=0;stream_state<=R_IDLE;
          end else if(serial_snapshot)stream_state<=R_LOW;
          else begin serial_reserved<=0;stream_state<=R_IDLE;end
        end
        R_LOW:if(lr_sop||lr_eop)begin serial_reserved<=0;stream_state<=lr_eop?R_IDLE:R_DROP;end
          else begin result_fifo[stream_slot][127:0]<=lr_data;stream_state<=R_HIGH;end
        R_HIGH:begin
          serial_reserved<=0;
          if(lr_sop||!lr_eop)stream_state<=lr_eop?R_IDLE:R_DROP;
          else begin result_fifo[stream_slot][255:128]<=lr_data;stream_state<=R_IDLE;end
        end
        R_DROP:if(lr_eop)stream_state<=R_IDLE;
        R_CONTROL:if(lr_eop)stream_state<=R_IDLE;
        R_ABORT_META:if(!abort_meta_ok)stream_state<=lr_eop?R_IDLE:R_DROP;
          else begin abort_next[stream_slot]<=lr_data[31:16];stream_state<=R_ABORT_KEY;end
        R_ABORT_KEY:if(lr_sop||lr_eop||lr_data!=slots[stream_slot].ticket[255:128])stream_state<=lr_eop?R_IDLE:R_DROP;else stream_state<=R_ABORT_OWNER;
        R_ABORT_OWNER:begin stream_state<=lr_eop?R_IDLE:R_DROP;if(!lr_sop&&lr_eop&&lr_data==slots[stream_slot].ticket[383:256])begin abort_seen[stream_slot]<=1;abort_error[stream_slot]<=serial_status!=0;end end
        default:stream_state<=R_IDLE;
      endcase
      case({command_push,terminal_pop})2'b10:count<=count+1'b1;2'b01:count<=count-1'b1;default:;endcase
      if(command_push)begin
        slots[tail]<='{cmd_ticket,cmd_job_key,cmd_abi,cmd_topology,cmd_capacity,cmd_numeric,cmd_layout,
            cmd_resource,cmd_service,cmd_provider,cmd_function,cmd_native_op,cmd_payload,cmd_stored,cmd_store_words,cmd_destination};
        live[tail]<=1;issued[tail]<=0;waiting_rf[tail]<=0;cancelled_slots[tail]<=0;
        input_seen[tail]<=0;abort_seen[tail]<=0;abort_delivered[tail]<=0;early_rf_error[tail]<=0;abort_error[tail]<=0;tail<=!tail;
      end
      if(terminal_pop)begin live[owner]<=0;result_have[owner]<=0;head<=!head;end
      if(synthetic_result)begin
        issued[issue_pointer]<=1;result_have[issue_pointer]<=1;result_fifo[issue_pointer]<=0;
        result_failure[issue_pointer]<=issue_stopped?8'd5:8'd1;issue_pointer<=!issue_pointer;
      end
      if(early_error_now)early_rf_error[stream_slot]<=1;
      if(provider_result)begin
        waiting_rf[provider_owner]<=0;result_have[provider_owner]<=1;
        if(cancelled_result||drained_error||serial_status!=0||!serial_snapshot)result_fifo[provider_owner]<=0;
        result_failure[provider_owner]<=cancelled_result?8'd5:((serial_status!=0||drained_error)?8'd2:(provider_stopped?8'd5:8'd0));
        if(lane_busy&&lane_slot==provider_owner)lane_busy<=0;
      end
      if(cancel_one_fire)cancelled_slots[cancel_one_slot]<=1;
      if(cancel_match)begin halted<=1;cancelled_epoch_valid<=1;cancelled_generation<=slots[head].job_key[127:96];cancelled_epoch<=slots[head].job_key[63:32];end
      if(rejected_now!=0)rejected_protocol_events<=rejected_protocol_events+{29'd0,rejected_now};
      if(timeout_valid&&stop_now)quarantine<=1;
      if(clear_quarantine&&quiescent)quarantine<=0;
      if(resume_after_drain&&quiescent&&!quarantine)halted<=0;
      case(ns)
        N_IDLE:if(issue_available&&!synthetic_result&&!lane_busy)begin active_slot<=issue_pointer;ns<=N_ISSUE;end
        N_ISSUE:if(native_valid&&native_ready)begin
          issued[active_slot]<=1;waiting_rf[active_slot]<=1;input_seen[active_slot]<=0;abort_seen[active_slot]<=0;abort_delivered[active_slot]<=0;
          lane_busy<=1;lane_slot<=active_slot;issue_pointer<=!active_slot;ns<=N_IDLE;
        end
        default:ns<=N_IDLE;
      endcase
      case(cs)
        C_IDLE:if(result_have[head]) begin
          piece<=0;stored_q<=0;partial_q<=0;error_q<=result_failure[head];
          if(result_failure[head]!=0) cs<=C_TERMINAL;
          else if(owner_stopped) begin error_q<=8'd5;cs<=C_TERMINAL;end
          else if(slots[owner].stored) cs<=C_REQUEST;
          else cs<=C_TERMINAL;
        end
        // Proffered writes remain valid until acceptance even after cancellation.
        C_REQUEST:if(s_valid&&s_ready) cs<=C_ACK;
        C_ACK:if(ack_valid&&ack_ready&&matching_ACK) begin
          if(ack_error) begin error_q<=8'd3;cs<=C_TERMINAL;end
          else begin
            committed_words<=committed_words+1'b1;partial_q<=1;
            if(owner_stopped) begin error_q<=8'd5;cs<=C_TERMINAL;end
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
