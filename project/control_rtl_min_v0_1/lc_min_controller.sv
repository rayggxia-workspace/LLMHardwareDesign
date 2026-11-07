// Minimal functional subset of local-control-rtl-boundary/0.1.
// External PM, service adapter, cohort coordinator and packet transport are peers.
`timescale 1ns/1ps
module lc_min_controller #(parameter [7:0] BLOCK_ID = 0,
                           parameter integer unsigned DRAIN_LIMIT = 128,
                           parameter integer unsigned STALL_LIMIT = 128,
                           parameter integer unsigned LOCAL_S_BYTES = 16384,
                           parameter bit ENABLE_M_DOT_STORE = 1'b0,
                           parameter bit M_DOT_STORE_SILU = 1'b0,
                           parameter bit ENABLE_P_HANDOFF = 1'b0,
                           parameter bit ENABLE_F_HANDOFF = 1'b0,
                           parameter bit ENABLE_EXT_HANDOFF = 1'b0,
                           parameter bit ENABLE_F_STORE = 1'b0,
                           parameter bit ENABLE_U_RMS = 1'b0,
                           parameter [1:0] EXTRA_PROFILE = 2'd0,
                           parameter bit ENABLE_NATIVE_P16 = 1'b0,
                           parameter bit ENABLE_NATIVE = 1'b0,
                           parameter [7:0] NATIVE_BLOCK_TYPE = 0,
                           parameter [31:0] NATIVE_TOPOLOGY = 0) (
`include "ports.svh"
);
  localparam [3:0] RESET_WAIT=0, INVALID=1, LOADING=2, VERIFIED=3,
                   PREPARED=4, READY=5, RUNNING=6, CANCELLING=7, POISONED=8;
  localparam [3:0] IDLE=0, TASK_REQ=1, TASK_WAIT=2, FETCH_REQ=3,
                   FETCH_WAIT=4, DECODE=5, DESC_REQ=6, DESC_WAIT=7,
                   ISSUE=8, WAIT_TOKEN=9, REPORT_HOLD=10, END_HOLD=11, FAULT_DRAIN=12;
  reg [3:0] life, seq;
  reg authorized, prepared, poisoned, cfg_busy, cfg_mem_wait;
  reg [31:0] generation, cert_epoch, last_release;
  reg [31:0] image_id, topology, abi_id, capacity_id;
  reg [15:0] total, written, readback;
  reg [2:0] cfg_op;
  reg [13:0] cfg_address;
  reg [127:0] cfg_data;
  reg cfg_response;
  reg [15:0] cfg_status;
  reg [127:0] cfg_read_data;
  reg [1023:0] header;
  reg [511:0] task_packet, task_desc, terminal;
  reg [1023:0] exec_desc;
  reg [511:0] object_desc, transfer_desc;
  reg object_live, object_valid, object_loaded, exec_loaded, transfer_loaded;
  reg [1:0] active_kind;
  reg [31:0] event_sequence;
  reg [31:0] registers[0:7];
  integer ri;
  reg [127:0] ireg;
  reg ireg_valid, terminal_valid;
  reg [31:0] pc, steps, max_steps, next_service, service_sequence;
  reg [2:0] beat, token;
  reg token_live, token_done;
  reg [15:0] task_status;
  reg [31:0] error_pc, reads, writes;
  reg [31:0] issued_pc;
  reg saturated;
  reg [31:0] last_task_sequence;
  reg pm_offered, svc_offered, pm_outstanding;
  reg [31:0] drain_count, stall_count;

  wire [31:0] inst_count = header[20*8 +: 32];
  wire [31:0] inst_offset = header[24*8 +: 32];
  wire [31:0] task_offset = header[36*8 +: 32];
  wire [31:0] object_offset = header[40*8 +: 32];
  wire [31:0] exec_offset = header[44*8 +: 32];
  wire [31:0] transfer_offset = header[48*8 +: 32];
  wire transfer_instruction = opcode==8'h42 || opcode==8'h43;
  wire [31:0] header_steps = header[52*8 +: 32];
  wire [31:0] total32 = {16'b0,total};
  wire [63:0] total64 = {48'b0,total};
  wire [31:0] job = task_packet[4*8 +: 32];
  wire [31:0] epoch = task_packet[8*8 +: 32];
  wire [31:0] task_sequence = task_packet[12*8 +: 32];
  wire [7:0] opcode = ireg[127:120];
  wire [7:0] ia = ireg[111:104], ib = ireg[103:96], ic = ireg[95:88];
  `include "instruction_fetch.svh"
  wire [63:0] table_address = (seq==TASK_REQ ? {32'b0,task_offset} :
       opcode==8'h40 ? {32'b0,object_offset} : transfer_instruction ?
       {32'b0,transfer_offset}+({56'b0,ic}<<6) : {32'b0,exec_offset}+({56'b0,ic}<<7)) + {57'b0,beat,4'b0};
  wire deployed = authorized && prepared && !poisoned && deploy_valid_i && deploy_generation_i==generation;
  wire cfg_fire = cfg_req_valid_i && cfg_req_ready_o;
  wire pm_fire = pm_req_valid_o && pm_req_ready_i;
  wire pm_done = pm_rsp_valid_i && pm_rsp_ready_o;
  wire svc_fire = svc_req_valid_o && svc_req_ready_i;
  wire svc_done = svc_rsp_valid_i && svc_rsp_ready_o;
  wire event_fire = event_valid_o && event_ready_i;
  wire cancel_identity = task_packet_i[0+:16]==1 && task_packet_i[16+:8]==1 &&
       task_packet_i[24+:8]==BLOCK_ID && task_packet_i[32+:96]==task_packet[32+:96] &&
       task_packet_i[128+:8]==task_packet[128+:8] && task_packet_i[136+:8]==task_packet[136+:8] &&
       task_packet_i[144+:16]==0 && task_packet_i[160+:64]==task_packet[160+:64] &&
       task_packet_i[224+:32]==0 && task_packet_i[256+:256]==0;
  wire call_identity = task_packet_i[0+:16]==1 && task_packet_i[16+:8]==0 &&
       task_packet_i[24+:8]==BLOCK_ID && task_packet_i[64+:32]>=cert_epoch &&
       task_packet_i[96+:32]>last_task_sequence && task_packet_i[128+:8]==0 &&
       task_packet_i[136+:8]<8 && task_packet_i[144+:16]==0 &&
       task_packet_i[160+:32]==image_id && task_packet_i[192+:32]==topology &&
       task_packet_i[224+:32]==0;
  wire cancel_fire = task_valid_i && task_ready_o && task_packet_i[16+:8]==1;
  wire cancel_start = cancel_fire && life==RUNNING && !terminal_valid;
  wire cancelling = life==CANCELLING || cancel_start;
  wire normal_issue = life==RUNNING && !cancel_start && deployed;
  `include "m_dot_store_desc.svh"
  `include "f_store_desc.svh"
  `include "u_rms_desc.svh"
  `include "j_lease_desc.svh"
  `include "c_state_desc.svh"
  localparam bit ENABLE_J_LEASE = EXTRA_PROFILE==2'd1;
  localparam bit ENABLE_C_STATE = EXTRA_PROFILE==2'd2;
  localparam [31:0] P_STORE_ABI = M_DOT_STORE_SILU ? M_SILU_STORE_ABI : M_DOT_STORE_ABI;
  localparam [31:0] P_STORE_TOPOLOGY = M_DOT_STORE_SILU ? M_SILU_STORE_TOPOLOGY : M_DOT_STORE_TOPOLOGY;
  localparam [31:0] P_HANDOFF_TOPOLOGY = 32'h1764a303;
  localparam [31:0] F_HANDOFF_TOPOLOGY = 32'h1764f303;
  localparam [31:0] U_HANDOFF_TOPOLOGY = 32'h1764b303;
  localparam [31:0] J_HANDOFF_TOPOLOGY = 32'h1764e303;
  localparam [31:0] C_HANDOFF_TOPOLOGY = 32'h1764c303;
  wire f_handoff_image = ENABLE_F_HANDOFF && topology==F_HANDOFF_TOPOLOGY;
  wire two_word_handoff = ENABLE_EXT_HANDOFF && (topology==U_HANDOFF_TOPOLOGY || topology==J_HANDOFF_TOPOLOGY);
  wire c_handoff_sink = ENABLE_EXT_HANDOFF && BLOCK_ID==1 && topology==C_HANDOFF_TOPOLOGY;
  wire handoff_image = (ENABLE_P_HANDOFF && topology==P_HANDOFF_TOPOLOGY) ||
                       f_handoff_image || two_word_handoff || c_handoff_sink;
  wire handoff_producer = handoff_image && BLOCK_ID==0;
  wire [31:0] handoff_bytes = two_word_handoff ? 32'd32 : 32'd16;
  wire silu_image = ENABLE_M_DOT_STORE && M_DOT_STORE_SILU && abi_id==M_SILU_STORE_ABI;
  wire handoff_cfg_ok = ENABLE_P_HANDOFF && cfg_req_topology_id_i==P_HANDOFF_TOPOLOGY &&
       ((BLOCK_ID==0 && ENABLE_M_DOT_STORE && M_DOT_STORE_SILU && cfg_req_abi_id_i==M_SILU_STORE_ABI) ||
        (BLOCK_ID==1 && cfg_req_abi_id_i==32'h00010001));
  wire f_handoff_cfg_ok = ENABLE_F_HANDOFF && cfg_req_topology_id_i==F_HANDOFF_TOPOLOGY &&
       ((BLOCK_ID==0 && ENABLE_F_STORE && cfg_req_abi_id_i==F_STORE_ABI) ||
        (BLOCK_ID==1 && !ENABLE_F_STORE && cfg_req_abi_id_i==32'h00010001));
  wire u_handoff_cfg = ENABLE_EXT_HANDOFF && BLOCK_ID==0 && cfg_req_topology_id_i==U_HANDOFF_TOPOLOGY;
  wire j_handoff_cfg = ENABLE_EXT_HANDOFF && BLOCK_ID==0 && cfg_req_topology_id_i==J_HANDOFF_TOPOLOGY;
  wire c_handoff_cfg = ENABLE_EXT_HANDOFF && BLOCK_ID==0 && cfg_req_topology_id_i==C_HANDOFF_TOPOLOGY;
  wire ext_cfg_topology = cfg_req_topology_id_i==U_HANDOFF_TOPOLOGY ||
                         cfg_req_topology_id_i==J_HANDOFF_TOPOLOGY || cfg_req_topology_id_i==C_HANDOFF_TOPOLOGY;
  wire ext_handoff_sink_cfg = ENABLE_EXT_HANDOFF && BLOCK_ID==1 && ext_cfg_topology &&
                              cfg_req_abi_id_i==32'h00010001 && LOCAL_S_BYTES==16384;
  localparam [31:0] NATIVE_P16_ABI = 32'h01790160;
  localparam [31:0] NATIVE_P16_TOPOLOGY = 32'h01790161;
  localparam [15:0] NATIVE_P16_MAX_EXEC = 16'd8;
  wire profile_cfg_ok = ENABLE_NATIVE ?
       (!ENABLE_NATIVE_P16 && LOCAL_S_BYTES==16384 && NATIVE_BLOCK_TYPE<=4 &&
        cfg_req_abi_id_i==32'h01930001 && NATIVE_TOPOLOGY!=0 &&
        cfg_req_topology_id_i==NATIVE_TOPOLOGY) :
       ENABLE_NATIVE_P16 ?
       (LOCAL_S_BYTES==16384 && BLOCK_ID<2 && cfg_req_abi_id_i==NATIVE_P16_ABI &&
        cfg_req_topology_id_i==NATIVE_P16_TOPOLOGY) :
       ENABLE_C_STATE ?
       (LOCAL_S_BYTES==16384 && !ENABLE_U_RMS && !ENABLE_F_STORE &&
        cfg_req_abi_id_i==C_STATE_ABI && (cfg_req_topology_id_i==C_STATE_TOPOLOGY || c_handoff_cfg)) :
       ENABLE_J_LEASE ?
       (LOCAL_S_BYTES==16384 && !ENABLE_U_RMS && !ENABLE_F_STORE &&
        cfg_req_abi_id_i==J_LEASE_ABI && (cfg_req_topology_id_i==J_LEASE_TOPOLOGY || j_handoff_cfg)) :
       ENABLE_U_RMS ?
       (LOCAL_S_BYTES==16384 && !ENABLE_F_STORE && cfg_req_abi_id_i==U_RMS_ABI &&
        (cfg_req_topology_id_i==U_RMS_TOPOLOGY || u_handoff_cfg)) :
       ENABLE_F_STORE ?
       (LOCAL_S_BYTES==16384 && cfg_req_abi_id_i==F_STORE_ABI &&
        (cfg_req_topology_id_i==F_STORE_TOPOLOGY || f_handoff_cfg_ok)) :
       (handoff_cfg_ok || f_handoff_cfg_ok || ext_handoff_sink_cfg ||
       (!ext_cfg_topology && cfg_req_topology_id_i!=P_HANDOFF_TOPOLOGY && cfg_req_topology_id_i!=F_HANDOFF_TOPOLOGY &&
       (cfg_req_abi_id_i == 32'h00010001 ||
        ENABLE_M_DOT_STORE && cfg_req_abi_id_i==P_STORE_ABI &&
        cfg_req_topology_id_i==P_STORE_TOPOLOGY)));
  wire cfg_meta_ok = EXTRA_PROFILE!=2'd3 && cfg_req_generation_i > generation && cfg_req_total_bytes_i >= 208 &&
       cfg_req_total_bytes_i <= 8320 && cfg_req_total_bytes_i[3:0]==0 &&
       cfg_req_image_id_i != 0 && cfg_req_topology_id_i != 0 && profile_cfg_ok &&
       cfg_req_capacity_id_i == 32'h17630001;

  wire [31:0] resource_mask = header[448+:32];
  wire [2:0] compute_resource = ENABLE_C_STATE ? C_STATE_RESOURCE : ENABLE_J_LEASE ? J_LEASE_RESOURCE :
                                ENABLE_U_RMS ? U_RMS_RESOURCE[2:0] :
                                ENABLE_F_STORE ? F_STORE_RESOURCE[2:0] : 3'd0;
  wire [7:0] block_type = ENABLE_NATIVE ? NATIVE_BLOCK_TYPE : ENABLE_C_STATE ? C_BLOCK_TYPE : ENABLE_J_LEASE ? J_BLOCK_TYPE :
                          ENABLE_U_RMS ? U_BLOCK_TYPE :
                          ENABLE_F_STORE ? F_BLOCK_TYPE : 8'd0;
  wire compute_only_header = header[240+:16]==0 && header[256+:16]==1 && header[272+:16]==0;
  wire compute_handoff_header = header[240+:16]==1 && header[256+:16]==1 && header[272+:16]==1;
  wire profile_header_ok = ENABLE_NATIVE ?
       (compact_image && header[240+:16]==0 && header[256+:16]!=0 &&
        header[272+:16]==0 && resource_mask==1) :
       ENABLE_NATIVE_P16 ?
       (compact_image && header[240+:16]==0 && header[256+:16]!=0 &&
        header[272+:16]==0 && resource_mask==1) :
       ENABLE_C_STATE ? (compute_only_header && resource_mask==C_STATE_MASK) :
       ENABLE_J_LEASE ? ((two_word_handoff ? compute_handoff_header : compute_only_header) && resource_mask==J_LEASE_MASK) :
       ENABLE_U_RMS ? ((two_word_handoff ? compute_handoff_header : compute_only_header) && resource_mask==U_RMS_MASK) :
       ENABLE_F_STORE ? ((f_handoff_image ? compute_handoff_header : compute_only_header) &&
        (resource_mask==F_G_STORE_MASK || resource_mask==F_GE_STORE_MASK)) :
       (silu_image ? resource_mask==32'h29 : (resource_mask&32'hffffffde)==0);

  // Bounded P profile: one task/object/service, M clear and static RAW16 routes.
  // Host must also verify full SHA, ISA, table usage and deployment bundle.
  wire header_ok = header[63:0]==64'h313041534943424c && instruction_version_ok &&
       header[80+:8]==1 && header[88+:8]==8 && header[96+:32]==total32 &&
       inst_count>0 && inst_count<=256 && header[128+:32]<inst_count && inst_offset==128 &&
       header[224+:16]==1 && header[240+:16]<=1 &&
       header[256+:16]<=(ENABLE_NATIVE ? 16'd32 : ENABLE_NATIVE_P16 ? NATIVE_P16_MAX_EXEC : 16'd1) && header[272+:16]<=2 &&
       {32'b0,task_offset}==instruction_end &&
       (header[240+:16]==0 ? object_offset==0 : {32'b0,object_offset}=={32'b0,task_offset}+64'd64) &&
       (header[256+:16]==0 ? exec_offset==0 : {32'b0,exec_offset}==
         {32'b0,task_offset}+64'd64+({48'b0,header[240+:16]}<<6)) &&
       (header[272+:16]==0 ? transfer_offset==0 : {32'b0,transfer_offset}==
         {32'b0,task_offset}+64'd64+({48'b0,header[240+:16]}<<6)+({48'b0,header[256+:16]}<<7)) &&
       total64=={32'b0,task_offset}+64'd64+({48'b0,header[240+:16]}<<6)+
         ({48'b0,header[256+:16]}<<7)+({48'b0,header[272+:16]}<<6) &&
       header_steps>0 && profile_header_ok &&
       header[480+:32]==image_id && header[512+:32]==topology && header[544+:32]==abi_id &&
       header[576+:16]==0 && header[592+:16]==0 && header[608+:32]==0 &&
       header[640+:32]==0 && header[672+:32]==capacity_id && header[704+:320]==0;

  wire task_ok = task_packet[0+:16]==1 && task_packet[16+:8]==0 &&
       task_packet[24+:8]==BLOCK_ID && epoch>=cert_epoch && task_sequence>last_task_sequence &&
       task_packet[128+:8]==0 && task_packet[136+:8]<8 && task_packet[144+:16]==0 &&
       task_packet[160+:32]==image_id && task_packet[192+:32]==topology && task_packet[224+:32]==0;
  wire task_desc_ok = task_desc[0+:16]==1 && task_desc[16+:8]==block_type && task_desc[24+:8]==0 &&
       task_desc[32+:32]<inst_count && task_desc[64+:16]<=header[240+:16] &&
       task_desc[80+:16]<=header[240+:16] && task_desc[96+:32]==0 && task_desc[128+:32]>0 &&
       task_desc[160+:32]==header[448+:32] &&
       task_desc[192+:32]==image_id && task_desc[224+:32]==topology &&
       task_desc[256+:96]==0 && task_desc[352+:32]==abi_id && task_desc[384+:128]==0;
  wire clear_exec_ok = (!ENABLE_M_DOT_STORE || abi_id!=P_STORE_ABI) &&
       exec_desc[0+:16]==1 && exec_desc[16+:8]==0 && exec_desc[24+:8]==0 &&
       exec_desc[32+:8]==6 && exec_desc[40+:24]==0 && exec_desc[64+:32]==32'hffffffff &&
       exec_desc[96+:64]==0 && exec_desc[160+:48]==48'hffffffffffff &&
       exec_desc[208+:240]==0 && exec_desc[56*8+:32]==abi_id && exec_desc[60*8+:32]==0 && exec_desc[512+:512]==0;
  wire native_p16_exec_ok = exec_desc[0+:32]==1 && exec_desc[48+:16]==0 &&
       exec_desc[64+:32]==32'hffffffff && exec_desc[96+:64]==0 && exec_desc[160+:48]==48'hffffffffffff &&
       exec_desc[208+:240]==0 && exec_desc[448+:32]==NATIVE_P16_ABI && exec_desc[480+:32]==0;
  wire native_exec_ok = exec_desc[0+:32]==1 && exec_desc[48+:16]==0 &&
       exec_desc[64+:32]==32'hffffffff && exec_desc[96+:64]==0 &&
       exec_desc[160+:48]==48'hffffffffffff && exec_desc[208+:240]==0 &&
       exec_desc[448+:32]==abi_id && exec_desc[480+:32]==0;
  wire exec_ok = ENABLE_NATIVE ? native_exec_ok :
       ENABLE_NATIVE_P16 ? native_p16_exec_ok :
       ENABLE_C_STATE ? c_state_desc_ok(exec_desc) : ENABLE_J_LEASE ? j_lease_desc_ok(exec_desc) :
       ENABLE_U_RMS ? u_rms_desc_ok(exec_desc) : ENABLE_F_STORE ?
       (f_store_desc_ok(exec_desc) &&
        resource_mask==(exec_desc[32+:16]==F_GE_STORE_OP ? F_GE_STORE_MASK : F_G_STORE_MASK)) :
       ((clear_exec_ok && !handoff_image) || (ENABLE_M_DOT_STORE && LOCAL_S_BYTES==16384 &&
        abi_id==P_STORE_ABI && m_dot_store_desc_ok(exec_desc, M_DOT_STORE_SILU)));
  // The computed word belongs to the reserved object. Pin the descriptor
  // destination before issuing the native command, then publish on L_WAIT.
  wire [9:0] handoff_result_word = ENABLE_J_LEASE ? exec_desc[544+:10] : exec_desc[532+:10];
  wire handoff_dst_ok = object_live && !object_valid &&
       object_desc[32+:32]=={18'b0,handoff_result_word,4'b0};

  // One static RAW16 object reservation; no data becomes valid at OPEN.
  wire object_fields_ok = object_desc[0+:16]==1 && object_desc[16+:8]==0 && object_desc[24+:8]==0 &&
       object_desc[64+:32]==handoff_bytes && object_desc[96+:32]==0 && object_desc[128+:8]==4 &&
       object_desc[136+:8]==4 && object_desc[144+:16]==0 && object_desc[160+:32]==1 &&
       object_desc[192+:16]==16'hffff && object_desc[208+:16]==0 && object_desc[224+:32]==handoff_bytes &&
       object_desc[256+:32]==abi_id && object_desc[288+:224]==0;
  wire object_range_ok = LOCAL_S_BYTES>=16 && object_desc[32+:4]==0 &&
       {32'b0,object_desc[32+:32]}+{32'b0,handoff_bytes}<=64'(LOCAL_S_BYTES);
  wire transfer_fields_ok = transfer_desc[0+:16]==1 && transfer_desc[16+:8]==(opcode==8'h43 ? 8'd1 : 8'd0) &&
       transfer_desc[24+:8]==4 && transfer_desc[32+:16]==0 && transfer_desc[48+:16]==16'hffff &&
       transfer_desc[64+:32]==0 && transfer_desc[96+:32]==handoff_bytes && transfer_desc[128+:32]==16 &&
       transfer_desc[168+:16]==0 && transfer_desc[184+:8]==8'hff && transfer_desc[224+:32]==1 &&
       transfer_desc[256+:32]==0 && transfer_desc[288+:8]==8'hff && transfer_desc[296+:24]==0 &&
       transfer_desc[320+:32]==1 && transfer_desc[352+:32]==handoff_bytes && transfer_desc[384+:128]==0;
  wire transfer_route_ok = (topology==32'd393400001 || handoff_image) &&
       ((opcode==8'h42 && BLOCK_ID==0 && !handoff_image && transfer_desc[160+:8]==255 && transfer_desc[192+:32]==11) ||
        (opcode==8'h42 && BLOCK_ID==1 && transfer_desc[160+:8]==0 && transfer_desc[192+:32]==12) ||
        (opcode==8'h43 && BLOCK_ID==0 && transfer_desc[160+:8]==1 && transfer_desc[192+:32]==12));
  wire simple_fields_ok = ireg[119:112]==0 && ia==0 && ireg[103:0]==0;
  wire open_commit = normal_issue && seq==DECODE && ireg_valid && opcode==8'h40 &&
       simple_fields_ok && header[240+:16]==1 && header[453] && !object_live &&
       object_loaded && object_fields_ok && object_range_ok;
  wire drop_commit = normal_issue && seq==DECODE && ireg_valid && opcode==8'h49 &&
       simple_fields_ok && object_live && !token_live;
  wire movi_commit = normal_issue && seq==DECODE && ireg_valid && opcode==8'h45 &&
       ireg[119:112]==0 && ia<8 && ireg[103:64]==0 && ireg[31:0]==0;

  assign life_o=life;
  assign seq_o=seq;
  assign release_ready_o=rst_ni && life==RESET_WAIT;
  assign poison_o=poisoned;
  assign image_valid_o=rst_ni && deployed;
  assign cfg_req_ready_o=rst_ni && authorized && !cfg_busy && !poisoned &&
       (life==INVALID || life==LOADING || life==VERIFIED || life==PREPARED || life==READY);
  assign cfg_rsp_valid_o=rst_ni && cfg_response;
  assign cfg_rsp_status_o=cfg_status;
  assign cfg_rsp_data_o=cfg_read_data;
  assign cfg_rsp_generation_o=generation;
  assign task_ready_o=rst_ni &&
       ((life==READY && deployed && task_credit_i && !cfg_busy &&
         (!task_valid_i || call_identity) && !(cfg_req_valid_i && cfg_req_ready_o)) ||
        ((life==RUNNING || life==CANCELLING) && cancel_identity &&
         !(terminal_valid && terminal[16+:8]<2)));
  assign pm_req_valid_o=rst_ni &&
       (pm_offered || (!poisoned &&
        ((cfg_busy && !cfg_response && !cfg_mem_wait && (cfg_op==1 || cfg_op==2)) ||
         (normal_issue && (seq==TASK_REQ || seq==DESC_REQ ||
          (seq==FETCH_REQ && pc<inst_count && fetch_address+64'd16<=total64 && steps<max_steps))))));
  assign pm_req_write_o=cfg_busy && cfg_op==1;
  assign pm_req_address_o=cfg_busy ? cfg_address : seq==FETCH_REQ ? fetch_address[13:0] : table_address[13:0];
  assign pm_req_data_o=cfg_busy && cfg_op==1 ? cfg_data : 128'b0;
  assign pm_rsp_ready_o=rst_ni && pm_outstanding;
  assign trace_pm_owner_o=cfg_busy ? 0 : (seq==FETCH_REQ || seq==FETCH_WAIT) ? 1 : 2;
  assign svc_req_valid_o=rst_ni && (svc_offered || normal_issue && seq==ISSUE);
  assign svc_req_kind_o=opcode==8'h42 ? 1 : opcode==8'h43 ? 2 : 0;
  assign svc_req_resource_o=transfer_instruction ? 3'd5 : compute_resource;
  assign svc_req_token_o=token;
  assign svc_req_sequence_o=service_sequence;
  assign svc_req_job_o=job;
  assign svc_req_epoch_o=epoch;
  assign svc_req_task_sequence_o=task_sequence;
  assign svc_req_descriptor_o=transfer_instruction ? {512'b0,transfer_desc} : exec_desc;
  assign svc_req_object_base_o=transfer_instruction ? {32'b0,object_desc[32+:32]} : 0;
  assign svc_req_object_length_o=transfer_instruction ? object_desc[224+:32] : 0;
  assign svc_req_object_version_o=transfer_instruction ? object_desc[160+:32] : 0;
  // An invalid/stale response is never accepted as completion. The adapter must
  // quarantine it. Poison retains ownership until a coordinated external reset.
  assign svc_rsp_ready_o=rst_ni && (life==RUNNING || life==CANCELLING || life==POISONED) && token_live && !token_done &&
       svc_rsp_kind_i==active_kind && svc_rsp_token_i==token && svc_rsp_sequence_i==service_sequence &&
       svc_rsp_job_i==job && svc_rsp_epoch_i==epoch && svc_rsp_task_sequence_i==task_sequence;
  assign event_valid_o=rst_ni && terminal_valid;
  assign event_packet_o=terminal;
  assign close_req_valid_o=0;
  assign close_req_sequence_o=0;
  assign close_req_job_o=0;
  assign close_req_epoch_o=0;
  assign close_req_task_sequence_o=0;
  assign close_req_token_o=0;
  assign close_rsp_ready_o=0;
  assign trace_pc_o=pc;
  assign trace_opcode_o=opcode;
  assign trace_ireg_valid_o=ireg_valid;
  assign trace_retire_o=rst_ni && ireg_valid && !poisoned &&
       (open_commit || drop_commit || movi_commit || svc_fire ||
        normal_issue && seq==DECODE && task_ok && opcode==8'h4b && compact_image && branch_fields_ok && branch_targets_ok || normal_issue && (seq==WAIT_TOKEN && token_done ||
        event_fire && (opcode==8'h4f && seq==END_HOLD || opcode==8'h4a && seq==REPORT_HOLD)));
  assign trace_cancel_token_retire_o=rst_ni && life==CANCELLING && token_live && token_done;
  assign trace_cancel_object_drop_o=rst_ni && life==CANCELLING && object_live && !token_live &&
       !pm_outstanding && !pm_offered && !svc_offered;

  task fault;
    input [15:0] status;
    begin
      if (task_status==0) begin task_status<=status; error_pc<=pc; end
      ireg_valid<=0;
      seq<=FAULT_DRAIN;
    end
  endtask

  always @(posedge clk_i or negedge rst_ni) begin
    if (!rst_ni) begin
      life<=RESET_WAIT; seq<=IDLE; authorized<=0; prepared<=0; poisoned<=0;
      generation<=0; cert_epoch<=0; last_release<=0; image_id<=0; topology<=0; abi_id<=0; capacity_id<=0;
      total<=0; written<=0; readback<=0; header<=0;
      cfg_busy<=0; cfg_mem_wait<=0; cfg_op<=0; cfg_address<=0; cfg_data<=0;
      cfg_response<=0; cfg_status<=0; cfg_read_data<=0;
      task_packet<=0; task_desc<=0; exec_desc<=0; object_desc<=0; object_live<=0; object_valid<=0; object_loaded<=0; exec_loaded<=0; transfer_loaded<=0; transfer_desc<=0; active_kind<=0; event_sequence<=0;
      for (ri=0;ri<8;ri=ri+1) registers[ri]<=0;
      ireg<=0; ireg_valid<=0;
      pc<=0; steps<=0; max_steps<=0; next_service<=0; service_sequence<=0;
      beat<=0; token<=0; token_live<=0; token_done<=0; task_status<=0;
      reads<=0; writes<=0; saturated<=0; error_pc<=32'hffffffff; issued_pc<=0;
      terminal<=0; terminal_valid<=0; last_task_sequence<=0;
      pm_offered<=0; svc_offered<=0; pm_outstanding<=0; drain_count<=0; stall_count<=0;
    end else begin
      pm_offered<=pm_req_valid_o && !pm_req_ready_i;
      svc_offered<=svc_req_valid_o && !svc_req_ready_i;
      if (pm_fire) pm_outstanding<=1;
      if (pm_done) pm_outstanding<=0;
      if (release_valid_i && release_ready_o && release_sequence_i>last_release && release_epoch_i>0) begin
        authorized<=1; cert_epoch<=release_epoch_i; last_release<=release_sequence_i; life<=INVALID;
      end
      if (cfg_response && cfg_rsp_ready_i) begin
        cfg_response<=0; cfg_busy<=0;
        if (cfg_op==2 && cfg_status==0) readback<=readback+16;
      end
      if (cfg_fire) begin
        cfg_busy<=1; cfg_op<=cfg_req_op_i; cfg_address<=cfg_req_address_i; cfg_data<=cfg_req_data_i;
        cfg_mem_wait<=0; cfg_response<=1; cfg_status<=0; cfg_read_data<=0;
        if (cfg_req_op_i==0) begin
          if ((life==INVALID || life==READY) && cfg_meta_ok) begin
            generation<=cfg_req_generation_i; total<=cfg_req_total_bytes_i;
            image_id<=cfg_req_image_id_i; topology<=cfg_req_topology_id_i;
            abi_id<=cfg_req_abi_id_i; capacity_id<=cfg_req_capacity_id_i;
            written<=0; readback<=0; header<=0; prepared<=0; life<=LOADING;
          end else cfg_status<=3;
        end else if (cfg_req_generation_i!=generation) begin
          cfg_status<=8;
          if (life==LOADING || life==VERIFIED || life==PREPARED) begin prepared<=0; life<=INVALID; end
        end
        else case (cfg_req_op_i)
          1,2: begin
            if (life==LOADING && cfg_req_address_i[3:0]==0 &&
                {2'b0,cfg_req_address_i}+16'd16<=total &&
                (cfg_req_op_i==1 ? {2'b0,cfg_req_address_i}==written : written==total && {2'b0,cfg_req_address_i}==readback))
              cfg_response<=0;
            else begin
              cfg_status<=6;
              if (life==LOADING || life==VERIFIED || life==PREPARED) begin prepared<=0; life<=INVALID; end
            end
          end
          3: begin
            if (life==LOADING && written==total && readback==total && cfg_req_proof_i && header_ok)
              life<=VERIFIED;
            else begin cfg_status<=3; prepared<=0; life<=INVALID; end
          end
          4: begin
            if (life==VERIFIED) begin prepared<=1; life<=PREPARED; end
            else begin cfg_status<=7; if (life==LOADING || life==PREPARED) begin prepared<=0; life<=INVALID; end end
          end
          5: begin prepared<=0; life<=INVALID; end
          default: begin
            cfg_status<=1;
            if (life==LOADING || life==VERIFIED || life==PREPARED) begin prepared<=0; life<=INVALID; end
          end
        endcase
      end
      if (life==PREPARED && deployed && !cfg_busy) life<=READY;
      // Loss of a previously committed cohort grant is an external reset fault.
      if (life==READY && !deployed) begin prepared<=0; life<=INVALID; end
      if ((life==RUNNING || life==CANCELLING) && !deployed) begin
        poisoned<=1; prepared<=0; life<=POISONED;
      end
      if (pm_fire) begin
        if (cfg_busy) cfg_mem_wait<=1;
        else case (seq)
          TASK_REQ: seq<=TASK_WAIT;
          FETCH_REQ: seq<=FETCH_WAIT;
          DESC_REQ: seq<=DESC_WAIT;
          default: begin end
        endcase
      end
      if (pm_done) begin
        if (cfg_busy) begin
          cfg_mem_wait<=0; cfg_response<=1;
          if (pm_rsp_error_i) begin cfg_status<=10; prepared<=0; life<=INVALID; end
          else if (cfg_op==1) begin
            written<=written+16;
            if (cfg_address<128) header[cfg_address*8 +: 128]<=cfg_data;
          end else begin
            cfg_read_data<=pm_rsp_data_i;
            if(bad_instruction_padding) cfg_status<=5;
          end
        end else if (cancelling || life==POISONED) begin
          // Consume only the previously accepted beat; never start the rest of a record.
          if (pm_rsp_error_i && (task_status==0 || task_status==11)) begin task_status<=10; error_pc<=pc; end
          else if (seq==FETCH_WAIT) begin ireg<=fetch_instruction; ireg_valid<=1; end
          seq<=FAULT_DRAIN;
        end else if (pm_rsp_error_i) fault(10);
        else case (seq)
          TASK_WAIT: begin
            task_desc[beat*128 +: 128]<=pm_rsp_data_i;
            if (beat==3) begin seq<=DECODE; beat<=0; end
            else begin beat<=beat+1; seq<=TASK_REQ; end
          end
          FETCH_WAIT: begin ireg<=fetch_instruction; ireg_valid<=1; seq<=DECODE; end
          DESC_WAIT: begin
            if (opcode==8'h40) object_desc[beat*128 +: 128]<=pm_rsp_data_i;
            else if (transfer_instruction) transfer_desc[beat*128 +: 128]<=pm_rsp_data_i;
            else exec_desc[beat*128 +: 128]<=pm_rsp_data_i;
            if (beat==(opcode==8'h40 || transfer_instruction ? 3 : 7)) begin
              if (opcode==8'h40) object_loaded<=1; else if (transfer_instruction) transfer_loaded<=1; else exec_loaded<=1;
              seq<=DECODE; beat<=0; end
            else begin beat<=beat+1; seq<=DESC_REQ; end
          end
          default: begin end
        endcase
      end
      if (task_valid_i && task_ready_o && task_packet_i[16+:8]==0) begin
        task_packet<=task_packet_i; task_desc<=0; exec_desc<=0; object_desc<=0; object_live<=0; object_valid<=0; object_loaded<=0; exec_loaded<=0; transfer_loaded<=0; transfer_desc<=0; active_kind<=0; event_sequence<=0;
        for (ri=0;ri<8;ri=ri+1) registers[ri]<=0;
        life<=RUNNING; seq<=TASK_REQ; beat<=0; ireg_valid<=0; pc<=0; steps<=0;
        max_steps<=header_steps; task_status<=0; error_pc<=32'hffffffff;
        token_live<=0; token_done<=0; next_service<=0; terminal_valid<=0;
        reads<=0; writes<=0; saturated<=0;
        drain_count<=0;
      end
      if (normal_issue) begin
        case (seq)
          DECODE: begin
            if (!task_ok) fault(2);
            else if (!ireg_valid) begin
              if (!task_desc_ok) fault(5);
              else begin
                pc<=task_desc[32+:32];
                max_steps<=task_desc[128+:32]<header_steps ? task_desc[128+:32] : header_steps;
                seq<=FETCH_REQ;
              end
            end else case (opcode)
              8'h40: begin
                if (ireg[119:112]!=0 || ireg[103:0]!=0) fault(2);
                else if ({8'b0,ia}>=header[240+:16]) fault(5);
                else if (!header[453]) fault(4);
                else if (object_live) fault(7);
                else if (!object_loaded) begin beat<=0; seq<=DESC_REQ; end
                else if (!object_fields_ok) fault(5);
                else if (!object_range_ok) fault(6);
                else begin object_live<=1; object_valid<=0; ireg_valid<=0; pc<=pc+1; steps<=steps+1; seq<=FETCH_REQ; end
              end
              8'h49: begin
                if (ireg[119:112]!=0 || ireg[103:0]!=0) fault(2);
                else if (ia!=0 || !object_live || token_live) fault(7);
                else begin object_live<=0; object_valid<=0; object_desc<=0; object_loaded<=0; ireg_valid<=0; pc<=pc+1; steps<=steps+1; seq<=FETCH_REQ; end
              end
              8'h45: begin
                if (!movi_commit) fault(2);
                else begin registers[ia[2:0]]<=ireg[63:32]; ireg_valid<=0; pc<=pc+1; steps<=steps+1; seq<=FETCH_REQ; end
              end
              8'h41: begin
                if (ireg[119:112]!=0 || ib>=8 || ireg[87:0]!=0) fault(2);
                else if (ia!={5'b0,compute_resource}) fault(4);
                else if ({8'b0,ic}>=header[256+:16]) fault(5);
                else if (!resource_mask[{2'b0,compute_resource}] || (!ENABLE_NATIVE && !ENABLE_NATIVE_P16 && header[256+:16]!=1) ||
                         token_live || next_service==32'hffffffff) fault(7);
                else if (!exec_loaded) begin beat<=0; seq<=DESC_REQ; end
                else if (!exec_ok || (handoff_producer && !handoff_dst_ok)) fault(5);
                else begin token<=ib[2:0]; service_sequence<=next_service; seq<=ISSUE; end
              end
              8'h42,8'h43: begin
                if (ireg[119:112]!=0 || ia!=0 || ib>=8 || ireg[87:0]!=0) fault(2);
                else if ({8'b0,ic}>=header[272+:16]) fault(5);
                else if (!header[453] || !(opcode==8'h42 ? task_desc[64] : task_desc[80])) fault(4);
                else if (!object_live || token_live || next_service==32'hffffffff || opcode==8'h43 && !object_valid) fault(7);
                else if (!transfer_loaded) begin beat<=0; seq<=DESC_REQ; end
                else if (!transfer_fields_ok || !transfer_route_ok) fault(5);
                else begin token<=ib[2:0]; service_sequence<=next_service; seq<=ISSUE; end
              end
              8'h4a: begin
                if (ireg[119:112]!=0 || ia>=32 || ib>=8 || ic!=0 || ireg[87:0]!=0) fault(2);
                else if (task_status!=0 || svc_done && svc_rsp_status_i!=0)
                  fault(task_status!=0 ? task_status : svc_rsp_status_i);
                else if (!token_live || active_kind!=1 || event_sequence==32'hffffffff) fault(7);
                else begin
                  terminal<=0; terminal[0+:16]<=1; terminal[16+:8]<=0; terminal[24+:8]<=BLOCK_ID;
                  terminal[32+:32]<=job; terminal[64+:32]<=epoch; terminal[96+:32]<=task_sequence;
                  terminal[128+:8]<=255; terminal[136+:8]<=ia; terminal[160+:32]<=registers[ib[2:0]];
                  terminal[288+:32]<=event_sequence+1; terminal[320+:32]<=32'hffffffff;
                  event_sequence<=event_sequence+1; terminal_valid<=1; seq<=REPORT_HOLD;
                end
              end
              8'h44: begin
                if (ireg[119:64]!=0 || ireg[31:0]!=0 || !token_live ||
                    ireg[63:32]!=(32'd1<<token)) fault(7);
                else seq<=WAIT_TOKEN;
              end
              8'h4b: begin
                if(!compact_image) fault(1);
                else if(!branch_fields_ok) fault(2);
                else if(!branch_targets_ok) fault(6);
                else begin pc<=branch_next_pc; ireg_valid<=0; steps<=steps+1; seq<=FETCH_REQ; end
              end
              8'h4f: begin
                if (ireg[119:0]!=0 || token_live || object_live) fault(7);
                else begin
                  terminal<=0; terminal[0+:16]<=1;
                  terminal[16+:8]<=task_status==0 ? 2 : 3;
                  terminal[24+:8]<=BLOCK_ID;
                  terminal[32+:32]<=job; terminal[64+:32]<=epoch; terminal[96+:32]<=task_sequence;
                  terminal[128+:8]<=task_packet[136+:8]; terminal[136+:8]<=8'hff;
                  terminal[144+:16]<=task_status; terminal[192+:32]<=reads; terminal[224+:32]<=writes;
                  terminal[256+:32]<={31'b0,saturated}; terminal[320+:32]<=error_pc;
                  terminal_valid<=1; seq<=END_HOLD;
                end
              end
              default: fault(1);
            endcase
          end
          FETCH_REQ: begin
            if (steps>=max_steps) fault(12);
            else if (pc>=inst_count || fetch_address+64'd16>total64) fault(6);
          end
          ISSUE: begin end // The acceptance path also handles a held request after CANCEL.
          WAIT_TOKEN: if (token_done) begin
            token_live<=0; token_done<=0;
            if (task_status!=0) begin ireg_valid<=0; seq<=FAULT_DRAIN; end
            else begin
              if (active_kind==1 || (handoff_producer && active_kind==0)) object_valid<=1;
              ireg_valid<=0; pc<=pc+1; steps<=steps+1; seq<=FETCH_REQ;
            end
          end
          REPORT_HOLD: if (event_fire) begin
            terminal_valid<=0; ireg_valid<=0; pc<=pc+1; steps<=steps+1;
            seq<=task_status!=0 ? FAULT_DRAIN : FETCH_REQ;
          end
          FAULT_DRAIN: if (!token_live && object_live) begin object_live<=0; object_valid<=0; object_desc<=0; object_loaded<=0; end
          else if (!token_live && !object_live && !pm_outstanding && !pm_offered && !svc_offered) begin
            terminal<=0; terminal[0+:16]<=1; terminal[16+:8]<=3; terminal[24+:8]<=BLOCK_ID;
            terminal[32+:32]<=job; terminal[64+:32]<=epoch; terminal[96+:32]<=task_sequence;
            terminal[128+:8]<=task_packet[136+:8]; terminal[136+:8]<=8'hff;
            terminal[144+:16]<=task_status; terminal[192+:32]<=reads; terminal[224+:32]<=writes;
            terminal[256+:32]<={31'b0,saturated}; terminal[320+:32]<=error_pc;
            terminal_valid<=1; seq<=END_HOLD;
          end else if (token_done) begin token_live<=0; token_done<=0; end
          END_HOLD: if (event_fire) begin
            terminal_valid<=0; ireg_valid<=0; last_task_sequence<=task_sequence;
            life<=READY; seq<=IDLE; steps<=steps+1;
          end
          default: begin end
        endcase
      end
      if (svc_fire) begin
        issued_pc<=pc; active_kind<=svc_req_kind_o; token_live<=1; token_done<=0; next_service<=next_service+1;
        exec_desc<=0; exec_loaded<=0; transfer_desc<=0; transfer_loaded<=0; ireg_valid<=0; pc<=pc+1; steps<=steps+1;
        seq<=cancelling || life==POISONED ? FAULT_DRAIN : FETCH_REQ;
      end
      if (cancel_start) begin
        life<=CANCELLING; drain_count<=0;
        if (task_status==0 && !(pm_done && pm_rsp_error_i)) begin task_status<=11; error_pc<=pc; end
        if (!pm_outstanding && !pm_offered && !pm_fire && !svc_offered && !svc_fire) seq<=FAULT_DRAIN;
      end
      if (life==CANCELLING) begin
        if (trace_cancel_token_retire_o) begin token_live<=0; token_done<=0; end
        if (trace_cancel_object_drop_o) begin object_live<=0; object_valid<=0; object_desc<=0; object_loaded<=0; end
        if (!terminal_valid && !pm_outstanding && !pm_offered && !svc_offered && !token_live && !object_live) begin
          terminal<=0; terminal[0+:16]<=1; terminal[16+:8]<=3; terminal[24+:8]<=BLOCK_ID;
          terminal[32+:32]<=job; terminal[64+:32]<=epoch; terminal[96+:32]<=task_sequence;
          terminal[128+:8]<=task_packet[136+:8]; terminal[136+:8]<=8'hff;
          terminal[144+:16]<=task_status; terminal[192+:32]<=reads; terminal[224+:32]<=writes;
          terminal[256+:32]<={31'b0,saturated}; terminal[320+:32]<=error_pc;
          terminal_valid<=1; seq<=END_HOLD;
        end
        if (event_fire) begin
          terminal_valid<=0; ireg_valid<=0; last_task_sequence<=task_sequence;
          life<=READY; seq<=IDLE;
        end
        if (!terminal_valid) begin
          if (DRAIN_LIMIT!=0 && drain_count>=DRAIN_LIMIT-1 &&
              ((pm_outstanding && !pm_done) || (pm_offered && !pm_fire) ||
               (svc_offered && !svc_fire) || (token_live && !token_done && !svc_done))) begin
            poisoned<=1; prepared<=0; life<=POISONED;
          end else if (drain_count!=32'hffffffff) drain_count<=drain_count+1;
        end
      end
      // Bound a non-progressing external obligation, not terminal backpressure.
      // Deadline only quarantines; it never fabricates completion or a credit.
      if (life==RUNNING && !terminal_valid &&
          (pm_offered || pm_outstanding || svc_offered || token_live && !token_done)) begin
        if (pm_fire || pm_done || svc_fire || svc_done) stall_count<=0;
        else if (STALL_LIMIT!=0 && stall_count>=STALL_LIMIT-1) begin
          poisoned<=1; prepared<=0; life<=POISONED;
        end else if (stall_count!=32'hffffffff) stall_count<=stall_count+1;
      end else stall_count<=0;
      if (svc_done) begin
        token_done<=1; reads<=reads+svc_rsp_read_bytes_i; writes<=writes+svc_rsp_write_bytes_i;
        saturated<=saturated || svc_rsp_saturated_i;
        if (svc_rsp_status_i!=0) begin task_status<=svc_rsp_status_i; error_pc<=issued_pc; end
        else if (active_kind==0 &&
                 (ENABLE_C_STATE ? (svc_rsp_read_bytes_i!=16 || svc_rsp_write_bytes_i!=16) :
                  ENABLE_J_LEASE ? (svc_rsp_read_bytes_i!=96 || svc_rsp_write_bytes_i!=64) :
                  ENABLE_U_RMS ? (svc_rsp_read_bytes_i!=64 || svc_rsp_write_bytes_i!=32) :
                  ((handoff_producer || ENABLE_F_STORE) && svc_rsp_write_bytes_i!=16))) begin
          task_status<=9; error_pc<=issued_pc;
        end
      end
    end
  end
endmodule
