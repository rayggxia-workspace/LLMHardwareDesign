"""Text-only generation of a streaming variant; original guard ABI is intact."""
from pathlib import Path

HERE = Path(__file__).resolve().parent
s = (HERE / "rtl/bounded_service_guard.sv").read_text(encoding="utf8")
s = s.replace("module bounded_service_guard #(", "module bounded_serial_m_guard #(")
s = s.replace("  input logic result_valid,output logic result_ready,\n  input logic [511:0] result_ticket,input logic [255:0] result_data,\n  input logic result_error,", """  // Product M ABI 0x02504d02 response; no assembly data FIFO.
  input logic lr_valid,output logic lr_ready,
  input logic lr_sop,lr_eop,input logic [127:0] lr_data,
  output logic input_consumed_valid,input logic input_consumed_ready,
  output logic [511:0] input_consumed_ticket,output logic input_consumed_error,
  // Other native control frames go directly to the finite service FSM.
  output logic control_valid,input logic control_ready,
  output logic control_sop,control_eop,output logic [127:0] control_data,
  // The coordinator may complete cancellation only after native ABORT identity,
  // A/raw flush and actual outstanding DMA/transport drain have all joined.
  input logic cancel_drained_valid,output logic cancel_drained_ready,
  input logic [511:0] cancel_drained_ticket,""")
start = s.index("  wire registered_service=")
end = s.index("  wire header_ok=", start)
s = s[:start] + "  wire registered_service=slots[issue_pointer].resource_id==0&&slots[issue_pointer].service_id==32;\n" + s[end:]
s = s.replace("slots[issue_pointer].provider_id==1&&slots[issue_pointer].function_id==0&&", """slots[issue_pointer].provider_id==1&&slots[issue_pointer].function_id==0&&
      slots[issue_pointer].payload[255:218]==0&&
      slots[issue_pointer].payload[216]==slots[issue_pointer].stored&&
      (!slots[issue_pointer].stored||slots[issue_pointer].store_words==2)&&""")
s = s.replace("  wire matching_result=ns==N_WAIT&&result_ticket==slots[active_slot].ticket;\n  wire provider_result=result_valid&&result_ready&&matching_result;", """  wire cancelled_result=cancel_drained_valid&&cancel_drained_ready&&stop_now&&
      ns==N_WAIT&&cancel_drained_ticket==slots[active_slot].ticket;
  wire provider_result=serial_complete||cancelled_result;
  wire result_error=serial_complete&&serial_status!=0;""")
s = s.replace("  wire bad_result=result_valid&&result_ready&&!matching_result;", """  wire bad_result=serial_bad||(cancel_drained_valid&&cancel_drained_ready&&!cancelled_result);""")
s = s.replace("  assign result_ready=!reset&&(!matching_result||result_count<2);", "  assign cancel_drained_ready=!reset&&stream_state==R_IDLE&&result_count<2;")
s = s.replace("  assign result_slots_occupied=result_count;", "  assign result_slots_occupied=result_count+{1'b0,serial_reserved};")
s = s.replace("  assign quiescent=count==0&&result_count==0&&ns==N_IDLE&&cs==C_IDLE;", "  assign quiescent=count==0&&result_count==0&&ns==N_IDLE&&cs==C_IDLE&&stream_state==R_IDLE;")
parser = r"""
  // cmd_payload is a finite expected-response ticket, NOT a packed M command.
  // Its exact layout is in serial_guard_contract.json. Full owner stays in
  // the existing command slot; session+record can never replace that owner.
  typedef enum logic [2:0] {R_IDLE,R_META,R_LOW,R_HIGH,R_DROP,R_CONTROL} stream_state_t;
  stream_state_t stream_state;
  logic serial_reserved,input_seen;
  logic [7:0] serial_event,serial_status;
  logic serial_snapshot;
  wire [217:0] expected=slots[active_slot].payload[217:0];
  wire [31:0] expected_session=expected[31:0],expected_record=expected[63:32];
  wire [127:0] rf_meta={14'b0,expected[177:162],expected[161:146],expected[145:144],
      expected[95:64],expected[143:128],expected[127:112],expected[111:104],expected[103:100],expected[99:96]};
  wire [127:0] input_meta={29'b0,expected[95:64],expected[210:195],expected[194:179],
      expected[178],expected[177:162],expected[161:146],expected[145:144]};
  wire [7:0] incoming_event=lr_data[39:32],incoming_status=lr_data[47:40];
  wire [15:0] incoming_flags=lr_data[127:112];
  wire [11:0] expected_rf_flags={1'b0,expected[213:211],expected[99:96],2'b0,expected[215],expected[216]};
  wire native_header=lr_sop&&!lr_eop&&!expected[214]&&lr_data[31:0]==32'h02504d02&&ns==N_WAIT&&
      lr_data[79:48]==expected_session&&lr_data[111:80]==expected_record;
  wire input_header=native_header&&incoming_event==3&&incoming_flags==16'h2000&&!input_seen&&expected[217];
  wire rf_header=native_header&&incoming_event==4&&(!expected[217]||input_seen)&&
      ((incoming_status==0&&incoming_flags[11:0]==expected_rf_flags&&
        incoming_flags[15:12]==(expected[216]?4'd4:4'd2))||
       (incoming_status!=0&&incoming_flags[15:12]==2&&!incoming_flags[0]));
  wire control_header=lr_sop&&!lr_eop&&lr_data[31:0]==32'h02504d02&&
      (((incoming_event==1||incoming_event==2||incoming_event==6||incoming_event==8||incoming_event==9||incoming_event==10)&&incoming_flags[15:12]==2)||
       (incoming_event==5&&incoming_flags[15:12]==4)||(incoming_event==7&&incoming_flags[15:12]==3));
  wire meta_matches=(serial_event==3)?lr_data==input_meta:lr_data==rf_meta;
  wire meta_framed=!lr_sop&&lr_eop==!serial_snapshot;
  wire input_end=stream_state==R_META&&serial_event==3&&meta_matches&&meta_framed;
  wire serial_complete=lr_valid&&lr_ready&&
      ((stream_state==R_META&&serial_event==4&&meta_matches&&meta_framed&&!serial_snapshot)||
       (stream_state==R_HIGH&&!lr_sop&&lr_eop));
  wire serial_bad=lr_valid&&lr_ready&&
      ((stream_state==R_IDLE&&!input_header&&!rf_header&&!control_header)||
       (stream_state==R_META&&(!meta_matches||!meta_framed))||
       (stream_state==R_LOW&&(lr_sop||lr_eop))||
       (stream_state==R_HIGH&&(lr_sop||!lr_eop)));
  assign input_consumed_valid=!reset&&lr_valid&&input_end;
  assign input_consumed_ticket=slots[active_slot].ticket;
  assign input_consumed_error=serial_status!=0;
  assign control_valid=!reset&&lr_valid&&(stream_state==R_CONTROL||(stream_state==R_IDLE&&control_header));
  assign control_sop=lr_sop;assign control_eop=lr_eop;assign control_data=lr_data;
  always_comb begin
    lr_ready=!reset;
    if(stream_state==R_IDLE) begin
      if(control_header) lr_ready=!reset&&control_ready;
      else if(rf_header) lr_ready=!reset&&result_count<2;
    end else if(stream_state==R_CONTROL) lr_ready=!reset&&control_ready;
    else if(input_end) lr_ready=!reset&&input_consumed_ready;
  end
"""
s = s.replace("  always_ff @(posedge clk) begin", parser + "\n  always_ff @(posedge clk) begin", 1)
s = s.replace("      cancelled_epoch_valid<=0;cancelled_generation<=0;cancelled_epoch<=0;", """      cancelled_epoch_valid<=0;cancelled_generation<=0;cancelled_epoch<=0;
      stream_state<=R_IDLE;serial_reserved<=0;serial_event<=0;serial_status<=0;serial_snapshot<=0;input_seen<=0;""")
s = s.replace("    end else begin\n      case({command_push,terminal_pop})", """    end else begin
      if(native_valid&&native_ready) input_seen<=0;
      if(lr_valid&&lr_ready) case(stream_state)
        R_IDLE:begin
          if(control_header) stream_state<=R_CONTROL;
          else if(input_header||rf_header) begin
            stream_state<=R_META;serial_event<=incoming_event;serial_status<=incoming_status;
            serial_snapshot<=incoming_event==4&&incoming_flags[0];
            serial_reserved<=incoming_event==4;
          end else stream_state<=lr_eop?R_IDLE:R_DROP;
        end
        R_META:begin
          if(!meta_matches||!meta_framed) begin serial_reserved<=0;stream_state<=lr_eop?R_IDLE:R_DROP;end
          else if(serial_event==3) begin input_seen<=1;stream_state<=R_IDLE;end
          else if(serial_snapshot) stream_state<=R_LOW;
          else begin serial_reserved<=0;stream_state<=R_IDLE;end
        end
        R_LOW:begin
          if(lr_sop||lr_eop) begin serial_reserved<=0;stream_state<=lr_eop?R_IDLE:R_DROP;end
          else begin result_fifo[result_tail][127:0]<=lr_data;stream_state<=R_HIGH;end
        end
        R_HIGH:begin
          serial_reserved<=0;
          if(lr_sop||!lr_eop) stream_state<=lr_eop?R_IDLE:R_DROP;
          else begin result_fifo[result_tail][255:128]<=lr_data;stream_state<=R_IDLE;end
        end
        R_DROP:if(lr_eop) stream_state<=R_IDLE;
        R_CONTROL:if(lr_eop) stream_state<=R_IDLE;
        default:stream_state<=R_IDLE;
      endcase
      case({command_push,terminal_pop})""")
s = s.replace("        result_fifo[result_tail]<=synthetic_result?256'd0:result_data;", """        if(synthetic_result||cancelled_result||result_error||!serial_snapshot) result_fifo[result_tail]<=0;
        // Snapshot low/high words were written directly into this same FIFO
        // entry. HIGH capture and publication happen on the identical EOP.""")
s = s.replace("// Internal LC/native boundary, not a new 512bit leaf-macro interface.", "// Streaming product-M response → existing two-entry guard; no assembly FIFO.")
from serial_abort_extension import extend
s=extend(s)
(HERE / "rtl/bounded_serial_m_guard.sv").write_text(s, encoding="utf8", newline="\n")
