"""Text derivation: require real full-identity ABORT before cancel completion."""

def extend(s):
    def replace(old,new):
        nonlocal s
        assert old in s,old
        s=s.replace(old,new)
    replace("  output logic [511:0] input_consumed_ticket,output logic input_consumed_error,", """  output logic [511:0] input_consumed_ticket,output logic input_consumed_error,
  output logic native_abort_valid,input logic native_abort_ready,
  output logic [511:0] native_abort_ticket,output logic [15:0] native_abort_next_k,""")
    replace("cancel_drained_ready&&stop_now&&", "cancel_drained_ready&&stop_now&&abort_seen&&abort_delivered&&")
    replace("typedef enum logic [2:0] {R_IDLE,R_META,R_LOW,R_HIGH,R_DROP,R_CONTROL}",
            "typedef enum logic [3:0] {R_IDLE,R_META,R_LOW,R_HIGH,R_DROP,R_CONTROL,R_ABORT_META,R_ABORT_KEY,R_ABORT_OWNER}")
    replace("  logic serial_snapshot;", "  logic serial_snapshot;\n  logic abort_seen,abort_delivered;\n  logic [15:0] abort_next_k;")
    replace("  wire control_header=", """  wire abort_header=native_header&&incoming_event==5&&incoming_status==0&&incoming_flags==16'h4000&&stop_now&&expected[217]&&!abort_seen;
  wire abort_meta_ok=!lr_sop&&!lr_eop&&lr_data[3:0]==expected[99:96]&&lr_data[15:4]==0&&lr_data[127:32]==0&&
      expected[127:112]>=128&&lr_data[31:16]<=expected[127:112]&&lr_data[31:16]>=expected[127:112]-16'd128&&
      (expected[111:104]==16?lr_data[19:16]==0:lr_data[22:16]==0);
  wire control_header=""")
    replace("R_IDLE&&!input_header&&!rf_header&&!control_header", "R_IDLE&&!input_header&&!rf_header&&!abort_header&&!control_header")
    replace("(stream_state==R_HIGH&&(lr_sop||!lr_eop)));", """(stream_state==R_HIGH&&(lr_sop||!lr_eop))||
       (stream_state==R_ABORT_META&&!abort_meta_ok)||
       (stream_state==R_ABORT_KEY&&(lr_sop||lr_eop||lr_data!=slots[active_slot].ticket[255:128]))||
       (stream_state==R_ABORT_OWNER&&(lr_sop||!lr_eop||lr_data!=slots[active_slot].ticket[383:256])));""")
    replace("  assign control_valid=", """  assign native_abort_valid=!reset&&abort_seen&&!abort_delivered;
  assign native_abort_ticket=slots[active_slot].ticket;
  assign native_abort_next_k=abort_next_k;
  assign control_valid=""")
    replace("(stream_state==R_IDLE&&control_header)", "(stream_state==R_IDLE&&control_header&&!abort_header)")
    replace("if(control_header) lr_ready", "if(control_header&&!abort_header) lr_ready")
    replace("serial_snapshot<=0;input_seen<=0;", "serial_snapshot<=0;input_seen<=0;abort_seen<=0;abort_delivered<=0;abort_next_k<=0;")
    replace("if(native_valid&&native_ready) input_seen<=0;", """if(native_valid&&native_ready) begin input_seen<=0;abort_seen<=0;abort_delivered<=0;end
      if(native_abort_valid&&native_abort_ready) abort_delivered<=1;""")
    replace("if(control_header) stream_state<=R_CONTROL;", "if(abort_header) stream_state<=R_ABORT_META;\n          else if(control_header) stream_state<=R_CONTROL;")
    replace("        R_CONTROL:if(lr_eop) stream_state<=R_IDLE;", """        R_CONTROL:if(lr_eop) stream_state<=R_IDLE;
        R_ABORT_META:begin
          if(!abort_meta_ok) stream_state<=lr_eop?R_IDLE:R_DROP;
          else begin abort_next_k<=lr_data[31:16];stream_state<=R_ABORT_KEY;end
        end
        R_ABORT_KEY:begin
          if(lr_sop||lr_eop||lr_data!=slots[active_slot].ticket[255:128]) stream_state<=lr_eop?R_IDLE:R_DROP;
          else stream_state<=R_ABORT_OWNER;
        end
        R_ABORT_OWNER:begin
          stream_state<=lr_eop?R_IDLE:R_DROP;
          if(!lr_sop&&lr_eop&&lr_data==slots[active_slot].ticket[383:256]) abort_seen<=1;
        end""")
    return s
