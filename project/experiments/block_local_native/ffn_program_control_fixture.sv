`timescale 1ns/1ps
// Boot the actual MC and three actual LC program stores, then carry framed
// CALLs and terminals. Descriptor payloads travel on shared DMA clients 0..2.
module ffn_program_control_fixture(
 input logic clk,reset,start,transport_drained,
 output logic ready,result_valid,
 input logic result_ready,
 output logic [31:0] terminal_reads,terminal_writes,
 output logic [2:0] service_valid,input logic [2:0] service_ready,
 output logic [383:0] service_owner,output logic [3071:0] service_descriptor,
 output logic [2:0] service_cancel,input logic [2:0] service_cancel_ready,
 input logic [2:0] service_done_valid,output logic [2:0] service_done_ready,
 input logic [383:0] service_done_owner,input logic [47:0] service_done_status,
 input logic [95:0] service_done_reads,service_done_writes,
 output logic [2:0] dr_valid,input logic [2:0] dr_ready,
 output logic [191:0] dr_address,output logic [95:0] dr_tag,
 output logic [2:0] dr_channel,output logic [14:0] dr_length,
 output logic [2:0] dr_close,input logic [2:0] dr_close_ready,output logic [95:0] dr_close_tag,
 input logic [2:0] dr_rsp_valid,output logic [2:0] dr_rsp_ready,
 input logic [95:0] dr_rsp_tag,input logic [1535:0] dr_rsp_data
);
 localparam [31:0] TOPOLOGY=32'd25001,ABI=32'h02500002;
 logic cfg_valid,cfg_ready,cfg_rsp_valid,cfg_take,release_valid,release_ready,deploy;
 logic [2:0] cfg_op;
 logic [13:0] cfg_address;
 logic [127:0] cfg_data,cfg_readback;
 logic [15:0] cfg_status;
 logic [3:0] life;
 logic [31:0] frame_faults,protocol_faults,result_job,result_epoch,result_sequence;
 logic [15:0] result_status;
 logic tx_valid,tx_ready,tx_sop,tx_eop,rx_valid,rx_ready,rx_sop,rx_eop;
 logic [7:0] tx_target,rx_source;
 logic [127:0] tx_data,rx_data;
 logic lc_cfg_valid,lc_cfg_take,lc_session;
 logic [1:0] lc_cfg_op;
 logic [13:0] lc_cfg_address;
 logic [127:0] lc_cfg_data;
 logic [31:0] lc_crc;
 // The existing MC core uses asynchronous reset while its 128-bit bridge
 // samples reset on the clock. This fixture holds the shared reset for edges.
 /* verilator lint_off SYNCASYNCNET */
 logic mother_reset_n;
 /* verilator lint_on SYNCASYNCNET */
 logic [2:0] lc_cfg_ready,lc_cfg_rsp,lc_certified,lc_prepared,lc_session_ready,lc_idle;
 logic [7:0] lc_cfg_status[3];
 logic [2:0] lc_rx_valid,lc_rx_ready,lc_tx_valid,lc_tx_ready,lc_tx_sop,lc_tx_eop;
 logic [2:0][127:0] lc_tx_data;
 logic [23:0] lc_rx_target,lc_rx_header_target;
 logic packet_transport_idle;
 // Runtime drain is independent of PM certification and session readiness.
 wire runtime_drained=transport_drained&&(&lc_idle)&&packet_transport_idle;
 logic [127:0] mother_image[17],local_image[22];
 string mother_file,local_file;
 logic [245:0] unused_mc;
 // The P0 physical view has TARGET=0 baked into its local controller.
 // All three instances below use that same local control implementation.
 mc_lc_packet128_switch #(.ENDPOINTS(3),.REBIND_TARGET(3'b111)) transport(
  .clk,.reset,.tx_valid,.tx_sop,.tx_ready,.tx_target,.tx_header_target(tx_data[24+:8]),
  .lc_rx_valid,.lc_rx_ready,.lc_rx_target,.lc_rx_header_target,
  .lc_tx_valid,.lc_tx_ready,.lc_tx_data,.lc_tx_sop,.lc_tx_eop,
  .rx_valid,.rx_ready,.rx_data,.rx_source,.rx_sop,.rx_eop,
  .transport_idle(packet_transport_idle));
 always @(posedge clk)begin
  if(!reset)begin
   assert(!tx_valid||tx_target<3);
   assert(frame_faults==0&&protocol_faults==0);
   if(result_valid)assert(result_status==0&&result_job==1&&result_epoch==9&&result_sequence==1)
    else $fatal(1,"real MC result status=%0d job=%0d epoch=%0d sequence=%0d",result_status,result_job,result_epoch,result_sequence);
  end
 end
 // A full Down scope takes about 45k cycles with the bounded DDR fixture.
 // Keep the short transport watchdog and budget the admitted service WAIT.
 mother_control_native64_transport128 #(.SERVICE_STALL_LIMIT(131072)) mother(
  .clk_i(clk),.rst_ni(mother_reset_n),.release_valid_i(release_valid),.release_sequence_i(32'd1),.release_epoch_i(32'd1),
  .deploy_valid_i(deploy),.deploy_generation_i(32'd1),.release_ready_o(release_ready),.poison_o(unused_mc[0]),
  .image_valid_o(unused_mc[1]),.cfg_req_valid_i(cfg_valid),.cfg_req_op_i(cfg_op),.cfg_req_generation_i(32'd1),
  .cfg_req_address_i(cfg_address),.cfg_req_data_i(cfg_data),.cfg_req_total_bytes_i(16'd272),.cfg_req_image_id_i(32'd900),
  .cfg_req_topology_id_i(TOPOLOGY),.cfg_req_abi_id_i(ABI),.cfg_req_capacity_id_i(32'h02590003),.cfg_req_proof_i(1'b1),
  .cfg_rsp_ready_i(cfg_take),.cfg_req_ready_o(cfg_ready),.cfg_rsp_valid_o(cfg_rsp_valid),.cfg_rsp_status_o(cfg_status),
  .cfg_rsp_data_o(cfg_readback),.cfg_rsp_generation_o(unused_mc[33:2]),.life_o(life),.seq_o(unused_mc[37:34]),
  .trace_pc_o(unused_mc[69:38]),.trace_retire_o(unused_mc[70]),.trace_opcode_o(unused_mc[78:71]),
  .trace_pm_owner_o(unused_mc[80:79]),.trace_ireg_valid_o(unused_mc[81]),
  .start_valid_i(start),.start_credit_i(&lc_prepared),.start_job_i(32'd1),.start_epoch_i(32'd9),
  .start_sequence_i(32'd1),.start_generation_i(32'd1),.local_image_ids_i({192'd0,{3{TOPOLOGY}}}),
  .local_enabled_i(9'b111),.start_ready_o(ready),.tx_valid,.tx_ready,.tx_data,.tx_target,.tx_sop,.tx_eop,.tx_credit(unused_mc[82]),
  .rx_valid,.rx_ready,.rx_data,.rx_source,.rx_sop,.rx_eop,
  .transport_drained_i(runtime_drained),
  .frame_fault_count(frame_faults),.result_valid_o(result_valid),.result_ready_i(result_ready),
  .result_job_o(result_job),.result_epoch_o(result_epoch),.result_sequence_o(result_sequence),.result_status_o(result_status),
  .result_error_pc_o(unused_mc[114:83]),.result_source_o(unused_mc[122:115]),.result_child_error_pc_o(unused_mc[154:123]),
  .result_failed_task_sequence_o(unused_mc[186:155]),.result_confirmed_read_bytes_o(terminal_reads),
  .result_confirmed_write_bytes_o(terminal_writes),.result_counter_overflow_o(unused_mc[187]),.result_saturated_o(unused_mc[188]),
  .trace_live_tokens_o(unused_mc[204:189]),.trace_block_active_o(unused_mc[213:205]),.trace_terminal_full_o(unused_mc[222:214]),
  .trace_READY_full_o(unused_mc[231:223]),.trace_aborting_o(unused_mc[232]),.recover_valid_i(1'b0),
  .recover_ready_o(unused_mc[233]),.protocol_fault_count_o(protocol_faults));
 assign unused_mc[245:234]=12'd0;
 wire _unused_mc=^unused_mc;

 for(genvar p=0;p<3;p++)begin: local_core
  wire [31:0] actual_crc,ticket,local_faults,retired;
  wire [7:0] local_source;
  wire [13:0] trace_address;
  wire trace_valid;
  lc_native_scope_controller lc(.clk,.reset,
   .session_valid(lc_session&&(&lc_session_ready)),.session_ready(lc_session_ready[p]),
   .session_generation(32'd1),.session_topology(TOPOLOGY),.transport_drained(runtime_drained),
   .cfg_valid(lc_cfg_valid&&(&lc_cfg_ready)),.cfg_ready(lc_cfg_ready[p]),.cfg_op(lc_cfg_op),.cfg_generation(32'd1),
   .cfg_abi(ABI),.cfg_capacity(32'h02510001),.cfg_crc(lc_crc),.cfg_bytes(16'd352),.cfg_address(lc_cfg_address),.cfg_data(lc_cfg_data),
   .cfg_rsp_valid(lc_cfg_rsp[p]),.cfg_rsp_ready(lc_cfg_take),.cfg_status(lc_cfg_status[p]),.cfg_actual_crc(actual_crc),
   .certified(lc_certified[p]),.prepared(lc_prepared[p]),
   .rx_valid(lc_rx_valid[p]),.rx_ready(lc_rx_ready[p]),
   .rx_data({tx_data[127:32],lc_rx_header_target[8*p+:8],tx_data[23:0]}),
   .rx_sop(tx_sop),.rx_eop(tx_eop),.rx_target(lc_rx_target[8*p+:8]),
   .tx_valid(lc_tx_valid[p]),.tx_ready(lc_tx_ready[p]),.tx_data(lc_tx_data[p]),
   .tx_sop(lc_tx_sop[p]),.tx_eop(lc_tx_eop[p]),.tx_source(local_source),
   .mc_req_valid(dr_valid[p]),.mc_req_ready(dr_ready[p]),.mc_req_address(dr_address[64*p+:64]),.mc_req_tag(dr_tag[32*p+:32]),
   .mc_req_channel(dr_channel[p]),.mc_req_record_beats(dr_length[5*p+:5]),.mc_close_valid(dr_close[p]),
   .mc_close_ready(dr_close_ready[p]),.mc_close_tag_base(dr_close_tag[32*p+:32]),
   .mc_rsp_valid(dr_rsp_valid[p]),.mc_rsp_ready(dr_rsp_ready[p]),.mc_rsp_tag(dr_rsp_tag[32*p+:32]),.mc_rsp_data(dr_rsp_data[512*p+:512]),
   .service_valid(service_valid[p]),.service_ready(service_ready[p]),.service_owner(service_owner[128*p+:128]),
   .service_ticket(ticket),.service_descriptor(service_descriptor[1024*p+:1024]),.service_cancel_valid(service_cancel[p]),
   .service_cancel_ready(service_cancel_ready[p]),.service_done_valid(service_done_valid[p]),.service_done_ready(service_done_ready[p]),
   .service_done_owner(service_done_owner[128*p+:128]),.service_done_ticket(service_done_owner[128*p+:32]),
   .service_done_status(service_done_status[16*p+:16]),.service_done_read_bytes(service_done_reads[32*p+:32]),
   .service_done_write_bytes(service_done_writes[32*p+:32]),.idle(lc_idle[p]),.protocol_fault_cycles(local_faults),
   .pm_trace_valid(trace_valid),.pm_trace_address(trace_address),.retired_instructions(retired));
  always @(posedge clk)if(!reset)begin
   assert(local_faults==0);
   assert(local_source==0);
   if(service_valid[p])assert(ticket==service_owner[128*p+:32]&&retired==1);
   if(lc_cfg_take&&lc_cfg_op==2)assert(actual_crc==lc_crc);
  end
  wire _unused=^{trace_valid,trace_address};
 end

 task automatic mother_config(input logic [2:0] op,input logic [13:0] address,input logic [127:0] data);
  cfg_op=op;cfg_address=address;cfg_data=data;cfg_valid=1;
  do @(posedge clk);while(!cfg_ready);
  @(negedge clk);cfg_valid=0;
  while(!cfg_rsp_valid)@(negedge clk);
  assert(cfg_status==0&&((op!=2)||cfg_readback==data))else $fatal(1,"MC PM boot op=%0d status=%0d",op,cfg_status);
  cfg_take=1;@(negedge clk);cfg_take=0;
 endtask
 task automatic local_config(input logic [1:0] op,input logic [13:0] address,input logic [127:0] data);
  lc_cfg_op=op;lc_cfg_address=address;lc_cfg_data=data;lc_cfg_valid=1;
  do @(posedge clk);while(lc_cfg_ready!=3'b111);
  @(negedge clk);lc_cfg_valid=0;
  while(lc_cfg_rsp!=3'b111)@(negedge clk);
  assert(lc_cfg_status[0]==0&&lc_cfg_status[1]==0&&lc_cfg_status[2]==0)else $fatal(1,"LC PM boot op=%0d",op);
  lc_cfg_take=1;@(negedge clk);lc_cfg_take=0;
 endtask
 initial begin
  mother_reset_n=0;
  cfg_valid=0;cfg_take=0;cfg_op=0;cfg_address=0;cfg_data=0;release_valid=0;deploy=0;
  lc_cfg_valid=0;lc_cfg_take=0;lc_cfg_op=0;lc_cfg_address=0;lc_cfg_data=0;lc_session=0;
  if(!$value$plusargs("MOTHER=%s",mother_file)||!$value$plusargs("LOCAL=%s",local_file)||!$value$plusargs("LC_CRC=%h",lc_crc))
   $fatal(1,"actual FFN program files and CRC required");
  $readmemh(mother_file,mother_image);$readmemh(local_file,local_image);
  wait(!reset);@(negedge clk);mother_reset_n=1;
  while(!runtime_drained)@(negedge clk);
  local_config(0,0,0);
  for(integer word=0;word<22;word++)local_config(1,14'(word*16),local_image[word]);
  local_config(2,0,0);
  assert(&lc_certified);
  lc_session=1;do @(posedge clk);while(lc_session_ready!=3'b111);
  @(negedge clk);lc_session=0;
  release_valid=1;do @(posedge clk);while(!release_ready);
  @(negedge clk);release_valid=0;
  mother_config(0,0,0);
  for(integer word=0;word<17;word++)mother_config(1,14'(word*16),mother_image[word]);
  for(integer word=0;word<17;word++)mother_config(2,14'(word*16),mother_image[word]);
  mother_config(3,0,0);mother_config(4,0,0);deploy=1;
  while(life!=5)@(negedge clk);
 end
endmodule
