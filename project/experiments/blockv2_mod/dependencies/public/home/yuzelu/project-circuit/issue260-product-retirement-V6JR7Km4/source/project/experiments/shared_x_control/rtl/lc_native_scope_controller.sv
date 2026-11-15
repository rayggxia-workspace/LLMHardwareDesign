`timescale 1ns/1ps
// New native profile only. The old LC ABI is not silently upgraded.
// One live CALL, one64B input frame, existing128B fetched scope registers,
// real1KiB mutable PM. No native result or descriptor response FIFO here.
module lc_native_scope_controller #(
  parameter logic [7:0] TARGET=0,
  parameter logic [31:0] IMAGE_ID=32'd25001
)(
  input logic clk,reset,
  input logic session_valid,output logic session_ready,
  input logic [31:0] session_generation,session_topology,
  input logic transport_drained,
  input logic cfg_valid,output logic cfg_ready,input logic [1:0] cfg_op,
  input logic [31:0] cfg_generation,cfg_abi,cfg_capacity,cfg_crc,
  input logic [15:0] cfg_bytes,input logic [13:0] cfg_address,input logic [127:0] cfg_data,
  output logic cfg_rsp_valid,input logic cfg_rsp_ready,
  output logic [7:0] cfg_status,output logic [31:0] cfg_actual_crc,
  output logic certified,prepared,
  input logic rx_valid,output logic rx_ready,input logic [127:0] rx_data,
  input logic rx_sop,rx_eop,input logic [7:0] rx_target,
  output logic tx_valid,input logic tx_ready,output logic [127:0] tx_data,
  output logic tx_sop,tx_eop,output logic [7:0] tx_source,
  output logic mc_req_valid,input logic mc_req_ready,
  output logic [63:0] mc_req_address,output logic [31:0] mc_req_tag,
  output logic mc_req_channel,output logic [4:0] mc_req_record_beats,
  output logic mc_close_valid,input logic mc_close_ready,output logic [31:0] mc_close_tag_base,
  input logic mc_rsp_valid,output logic mc_rsp_ready,input logic [31:0] mc_rsp_tag,
  input logic [511:0] mc_rsp_data,
  output logic service_valid,input logic service_ready,
  output logic [127:0] service_owner,output logic [31:0] service_ticket,
  output logic [1023:0] service_descriptor,
  output logic service_cancel_valid,input logic service_cancel_ready,
  input logic service_done_valid,output logic service_done_ready,
  input logic [127:0] service_done_owner,input logic [31:0] service_done_ticket,
  input logic [15:0] service_done_status,
  input logic [31:0] service_done_read_bytes,service_done_write_bytes,
  output logic idle,output logic [31:0] protocol_fault_cycles,
  output logic pm_trace_valid,output logic [13:0] pm_trace_address,
  output logic [31:0] retired_instructions
);
  typedef enum logic [3:0] {IDLE,PM_REQ,PM_RSP,DECODE,META_REQ,META_RSP,
      FETCH_START,FETCH_WAIT,SERVICE_OFFER,WAIT_DONE,RELEASE_SCOPE,DRAIN,RETURN} state_t;
  typedef enum logic [1:0] {RX_IDLE,RX_COLLECT,RX_DROP} rx_state_t;
  state_t state;
  rx_state_t rx_state;
  logic [511:0] rx_packet;
  logic rx_full;
  logic [1:0] rx_word,tx_word;
  logic configured,cancelled,service_live,service_finished,cancel_sent,offer_held;
  logic exec_seen,wait_seen,fetch_taken;
  logic [31:0] generation,topology,last_sequence;
  logic [31:0] active_job,active_epoch,active_sequence;
  logic [7:0] active_token;
  logic [79:0] active_args;
  logic [1:0] pc;
  logic [4:0] meta_word;
  logic [63:0] instruction;
  logic [15:0] terminal_status;
  logic [31:0] read_bytes,write_bytes,scope_read_bytes;
  logic [511:0] terminal_packet;
  logic pm_valid,pm_ready,pm_rsp_valid,pm_rsp_ready,pm_error;
  logic [13:0] pm_address;
  logic [127:0] pm_data;
  logic boot_busy;
  logic [31:0] pm_generation;
  logic [15:0] image_bytes;
  logic fetch_init_ready,fetch_start_ready,fetch_valid,fetch_ready,fetch_release_ready;
  logic [7:0] fetch_status;
  logic [127:0] fetch_owner;
  logic [31:0] fetch_ticket,fetch_faults;
  logic fetch_busy,fetch_cancelled;
  logic [1:0] fetch_outstanding,fetch_confirmed;
  wire frame_fire=rx_valid&&rx_ready;
  wire packet_owner_match=rx_packet[32+:32]==active_job&&rx_packet[64+:32]==active_epoch&&
      rx_packet[96+:32]==active_sequence&&rx_packet[136+:8]==active_token&&
      rx_packet[160+:32]==IMAGE_ID&&rx_packet[192+:32]==topology&&rx_packet[224+:32]==generation;
  wire packet_header_ok=rx_packet[15:0]==2&&rx_packet[24+:8]==TARGET&&
      rx_packet[128+:8]==0&&rx_packet[144+:16]==0;
  wire cancel_match=rx_full&&packet_header_ok&&rx_packet[16+:8]==1&&
      state!=IDLE&&state!=RETURN&&packet_owner_match&&rx_packet[256+:256]==0;
  wire stop_now=cancelled||cancel_match;
  wire service_done_match=service_done_owner==service_owner&&service_done_ticket==active_sequence;
  wire done_fire=service_done_valid&&service_done_ready&&service_done_match&&service_live;
  assign service_owner={generation,active_job,active_epoch,active_sequence};
  assign service_ticket=active_sequence;
  assign service_done_ready=!reset;
  assign service_valid=!reset&&state==SERVICE_OFFER&&(!stop_now||offer_held);
  assign service_cancel_valid=!reset&&service_live&&stop_now&&!cancel_sent;
  assign prepared=!reset&&configured&&certified;
  assign idle=state==IDLE&&!rx_full&&rx_state==RX_IDLE&&!fetch_busy;
  assign session_ready=!reset&&idle&&transport_drained&&session_generation>generation&&fetch_init_ready&&certified;
  assign rx_ready=!reset&&!rx_full;
  assign tx_valid=!reset&&state==RETURN;
  assign tx_data=terminal_packet[128*tx_word+:128];
  assign tx_source=TARGET;
  assign tx_sop=tx_word==0;
  assign tx_eop=tx_word==3;
  assign pm_valid=!reset&&(state==PM_REQ||state==META_REQ);
  assign pm_address=state==META_REQ ? (meta_word<8 ? {5'd0,meta_word,4'd0} : (14'd160+({5'd0,meta_word,4'd0}-14'd128))) :
      (14'd128+{9'd0,pc[1],4'd0});
  assign pm_rsp_ready=state==PM_RSP||state==META_RSP;
  assign pm_trace_valid=pm_valid&&pm_ready;
  assign pm_trace_address=pm_address;
  assign fetch_ready=state==FETCH_WAIT||state==DRAIN;
  // Terminal is composed from retained task fields, not a second64B FIFO.
  always_comb begin
    terminal_packet=0;
    terminal_packet[0+:16]=2;terminal_packet[16+:8]=terminal_status==0?8'd2:8'd3;
    terminal_packet[24+:8]=TARGET;terminal_packet[32+:32]=active_job;
    terminal_packet[64+:32]=active_epoch;terminal_packet[96+:32]=active_sequence;
    terminal_packet[128+:8]=active_token;terminal_packet[136+:8]=255;
    terminal_packet[144+:16]=terminal_status;
    terminal_packet[192+:32]=read_bytes;terminal_packet[224+:32]=write_bytes;
    terminal_packet[256+:32]=0;
    terminal_packet[320+:32]=terminal_status==0?32'hffffffff:{30'd0,pc};
    terminal_packet[352+:32]=generation;terminal_packet[384+:32]=topology;
  end
  lc_program_store_1k pm(
    .clk,.reset,.lc_idle(idle),.transport_drained,
    .cfg_valid,.cfg_ready,.cfg_op,.cfg_generation,.cfg_abi,.cfg_capacity,.cfg_crc,
    .cfg_bytes,.cfg_address,.cfg_data,.cfg_rsp_valid,.cfg_rsp_ready,.cfg_status,.cfg_actual_crc,
    .certified,.boot_busy,.generation(pm_generation),.image_bytes,
    .pm_valid,.pm_ready,.pm_address,.pm_rsp_valid,.pm_rsp_ready,.pm_data,.pm_error
  );
  lc_scope_fetch128 scope_fetch(
    .clk,.reset,.init_valid(session_valid&&session_ready),.init_ready(fetch_init_ready),
    .init_generation(session_generation),.transport_drained,
    .start_valid(state==FETCH_START&&!stop_now),.start_ready(fetch_start_ready),
    .start_owner(service_owner),.start_ticket(active_sequence),
    .start_reference(active_args[63:0]),.start_bytes(active_args[64+:16]),
    .cancel_valid(stop_now&&fetch_busy),.cancel_owner(service_owner),.cancel_ticket(active_sequence),
    .release_valid(state==RELEASE_SCOPE&&fetch_taken),.release_ready(fetch_release_ready),
    .release_owner(service_owner),.release_ticket(active_sequence),
    .fetch_valid,.fetch_ready,.fetch_status,.fetch_owner,.fetch_ticket,
    .descriptor_data(service_descriptor),.mc_req_valid,.mc_req_ready,.mc_req_address,.mc_req_tag,
    .mc_req_channel,.mc_req_record_beats,.mc_close_valid,.mc_close_ready,.mc_close_tag_base,
    .mc_rsp_valid,.mc_rsp_ready,.mc_rsp_tag,.mc_rsp_data,.busy(fetch_busy),.cancelled(fetch_cancelled),
    .outstanding_beats(fetch_outstanding),.confirmed_beats(fetch_confirmed),.protocol_fault_cycles(fetch_faults)
  );
  // Fixed metadata ABI for the registered single-scope kernel. These words
  // are read from actual PM, not a service ID injected by the testbench.
  function automatic logic [127:0] expected_meta(input logic [4:0] word_index);
    case(word_index)
      0:expected_meta=128'h0000016008010002313041534943424c;
      1:expected_meta=128'h00000001000000800000000300000000;
      2:expected_meta=128'h000000e000000000000000a000000001;
      3:expected_meta=128'h000061a9000000010000000300000000;
      4:expected_meta=128'h000000000000000002500002000061a9;
      5:expected_meta=128'h00000000000000000251000100000000;
      6:expected_meta=128'h00000000000000000000000000000000;
      7:expected_meta=128'h00000000000000000000000000000000;
      8:expected_meta=128'h00000000000000000000000000000001;
      9:expected_meta=128'h000061a9000061a90000000100000003;
      10:expected_meta=128'h02500002000000000000000000000000;
      11:expected_meta=128'h00000000000000000000000000000000;
      12:expected_meta=128'h00000000ffffffff0000025000000001;
      13:expected_meta=128'h000000000000ffffffffffff00000000;
      14:expected_meta=128'h00000000000000000000000000000000;
      15:expected_meta=128'h00000000025000020000000000000000;
      16:expected_meta=128'h00000000000000000000000000000000;
      17:expected_meta=128'h00000000000000000000000000000000;
      18:expected_meta=128'h00000000000000000000000000000000;
      19:expected_meta=128'h00000000000000000000000000000000;
      default:expected_meta=0;
    endcase
  endfunction
  always_ff @(posedge clk)begin
    if(reset)begin
      state<=IDLE;rx_state<=RX_IDLE;rx_full<=0;rx_word<=0;tx_word<=0;rx_packet<=0;
      configured<=0;generation<=0;topology<=0;last_sequence<=0;
      active_job<=0;active_epoch<=0;active_sequence<=0;active_token<=0;active_args<=0;
      cancelled<=0;service_live<=0;service_finished<=0;cancel_sent<=0;offer_held<=0;
      exec_seen<=0;wait_seen<=0;fetch_taken<=0;pc<=0;meta_word<=0;instruction<=0;
      terminal_status<=0;read_bytes<=0;write_bytes<=0;scope_read_bytes<=0;protocol_fault_cycles<=0;retired_instructions<=0;
    end else begin
      if(session_valid&&session_ready)begin
        configured<=1;generation<=session_generation;topology<=session_topology;last_sequence<=0;
      end
      // Revoke only when PM actually revokes certification. A rejected
      // configuration request must not destroy the previous deployment.
      if(!certified)configured<=0;
      if(frame_fire)case(rx_state)
        RX_IDLE:if(rx_sop&&!rx_eop&&rx_target==TARGET&&rx_data[24+:8]==TARGET)begin
          rx_packet[127:0]<=rx_data;rx_word<=1;rx_state<=RX_COLLECT;
        end else begin
          protocol_fault_cycles<=protocol_fault_cycles+1'b1;
          if(!rx_eop)rx_state<=RX_DROP;
        end
        RX_COLLECT:if(rx_sop||rx_target!=TARGET||rx_eop!=(rx_word==3))begin
          protocol_fault_cycles<=protocol_fault_cycles+1'b1;
          if(rx_eop)rx_state<=RX_IDLE;else rx_state<=RX_DROP;
        end else begin
          rx_packet[128*rx_word+:128]<=rx_data;
          if(rx_word==3)begin rx_full<=1;rx_state<=RX_IDLE;rx_word<=0;end
          else rx_word<=rx_word+1'b1;
        end
        RX_DROP:if(rx_eop)rx_state<=RX_IDLE;
        default:rx_state<=RX_DROP;
      endcase
      if(rx_full)begin
        rx_full<=0;
        if(cancel_match)cancelled<=1;
        else if(state==IDLE&&packet_header_ok&&rx_packet[16+:8]==0&&configured&&certified&&
            rx_packet[96+:32]>last_sequence&&rx_packet[96+:32]!=0&&rx_packet[136+:8]<16&&
            rx_packet[160+:32]==IMAGE_ID&&rx_packet[192+:32]==topology&&rx_packet[224+:32]==generation)begin
          active_job<=rx_packet[32+:32];active_epoch<=rx_packet[64+:32];active_sequence<=rx_packet[96+:32];
          active_token<=rx_packet[136+:8];active_args<=rx_packet[256+:80];
          last_sequence<=rx_packet[96+:32];pc<=0;cancelled<=0;cancel_sent<=0;offer_held<=0;
          service_live<=0;service_finished<=0;exec_seen<=0;wait_seen<=0;fetch_taken<=0;
          terminal_status<=0;read_bytes<=0;write_bytes<=0;scope_read_bytes<=0;retired_instructions<=0;
          // Packet arguments reference a typed DDR scope, not all its fields.
          if(rx_packet[320+:32]!=32'h00010080||rx_packet[352+:32]!=32'h02510001||
              rx_packet[384+:32]!=topology||rx_packet[416+:32]!=32'h02500002||rx_packet[448+:32]!=0||
              rx_packet[496+:16]!=0||rx_packet[256+:7]!=0||image_bytes!=352)begin terminal_status<=16'd2;state<=RETURN;end
          else state<=PM_REQ;
        end else protocol_fault_cycles<=protocol_fault_cycles+1'b1;
      end
      if(service_valid&&!service_ready)offer_held<=1;
      if(service_cancel_valid&&service_cancel_ready)cancel_sent<=1;
      if(service_done_valid)begin
        if(done_fire)begin
          service_live<=0;service_finished<=1;read_bytes<=service_done_read_bytes+scope_read_bytes;
          write_bytes<=service_done_write_bytes;
          if(service_done_status!=0)terminal_status<=service_done_status;
        end else protocol_fault_cycles<=protocol_fault_cycles+1'b1;
      end
      if(fetch_valid&&fetch_ready)begin
        fetch_taken<=1;
        scope_read_bytes<={24'd0,fetch_confirmed,6'd0};
        read_bytes<={24'd0,fetch_confirmed,6'd0};
        if(fetch_owner!=service_owner||fetch_ticket!=active_sequence)begin terminal_status<=16'd9;state<=DRAIN;end
      end
      case(state)
        IDLE:begin end
        PM_REQ:if(pm_valid&&pm_ready)state<=PM_RSP;
        PM_RSP:if(pm_rsp_valid&&pm_rsp_ready)begin
          if(stop_now)state<=DRAIN;
          else if(pm_error)begin terminal_status<=3;state<=DRAIN;end
          else begin instruction<=pc[0]?pm_data[127:64]:pm_data[63:0];state<=DECODE;end
        end
        DECODE:begin
          if(stop_now)state<=DRAIN;
          else if(instruction==64'h4100000000000000&&!exec_seen&&pc==0)begin
            retired_instructions<=retired_instructions+1'b1;meta_word<=0;state<=META_REQ;
          end else if(instruction==64'h4400000000000001&&exec_seen&&!wait_seen&&pc==1)begin
            retired_instructions<=retired_instructions+1'b1;wait_seen<=1;state<=WAIT_DONE;
          end else if(instruction==64'h4f00000000000000&&exec_seen&&wait_seen&&service_finished&&pc==2)begin
            retired_instructions<=retired_instructions+1'b1;state<=RELEASE_SCOPE;
          end else begin terminal_status<=4;state<=DRAIN;end
        end
        META_REQ:if(pm_valid&&pm_ready)state<=META_RSP;
        META_RSP:if(pm_rsp_valid&&pm_rsp_ready)begin
          if(stop_now)state<=DRAIN;
          else if(pm_error||pm_data!=expected_meta(meta_word))begin terminal_status<=5;state<=DRAIN;end
          else if(meta_word==19)state<=FETCH_START;
          else begin meta_word<=meta_word+1'b1;state<=META_REQ;end
        end
        FETCH_START:if(stop_now)state<=DRAIN;else if(fetch_start_ready)state<=FETCH_WAIT;
        FETCH_WAIT:if(fetch_valid&&fetch_ready)begin
          if(stop_now||fetch_status!=0)begin
            if(!stop_now)terminal_status<=16'd16+{8'd0,fetch_status};state<=DRAIN;
          end else state<=SERVICE_OFFER;
        end
        SERVICE_OFFER:if(service_valid&&service_ready)begin
          service_live<=1;exec_seen<=1;offer_held<=0;pc<=1;
          if(stop_now)state<=DRAIN;else state<=PM_REQ;
        end else if(stop_now&&!offer_held)state<=DRAIN;
        WAIT_DONE:if(stop_now)state<=DRAIN;
          else if(service_finished||done_fire)begin pc<=2;state<=PM_REQ;end
        DRAIN:if(!service_live&&(!fetch_busy||fetch_taken))state<=RELEASE_SCOPE;
        RELEASE_SCOPE:if(!fetch_busy||(fetch_taken&&fetch_release_ready))begin
          if(cancelled)terminal_status<=16'd3;
          tx_word<=0;state<=RETURN;
        end
        RETURN:if(tx_valid&&tx_ready)begin
          if(tx_word==3)begin state<=IDLE;tx_word<=0;end else tx_word<=tx_word+1'b1;
        end
        default:begin terminal_status<=31;state<=DRAIN;end
      endcase
    end
  end
  // Exposed counters are diagnostics, not additional owner/drain proof.
  wire unused_diagnostics=^{boot_busy,pm_generation,fetch_faults,fetch_cancelled,fetch_outstanding,rx_packet[495:480]};
endmodule
