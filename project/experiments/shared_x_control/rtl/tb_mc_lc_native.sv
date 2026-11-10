`timescale 1ns/1ps
// Real native LC PM/boot, physical128bit CALL/return, real DDR fetch/CRC,
// root's actual typed decoder and six-ticket range iterator. Record-provider
// completions below are finite peers, not numerical M/real S qualification.
module tb_mc_lc_native;
 logic clk,reset;
 initial clk=0;
 always #5 clk=~clk;
 logic session_valid,session_ready,transport_drained;
 logic [31:0] session_generation,session_topology;
 logic cfg_valid,cfg_ready,cfg_rsp_valid,cfg_rsp_ready,certified,prepared;
 logic [1:0] cfg_op;
 logic [31:0] cfg_generation,cfg_abi,cfg_capacity,cfg_crc,cfg_actual_crc;
 logic [15:0] cfg_bytes;
 logic [13:0] cfg_address;
 logic [127:0] cfg_data;
 logic [7:0] cfg_status;
 logic rx_valid,rx_ready,rx_sop,rx_eop;
 logic [127:0] rx_data;
 logic [7:0] rx_target;
 logic tx_valid,tx_ready,tx_sop,tx_eop;
 logic [127:0] tx_data;
 logic [7:0] tx_source;
 logic mc_req_valid,mc_req_ready,mc_req_channel,mc_rsp_valid,mc_rsp_ready;
 logic [63:0] mc_req_address;
 logic [31:0] mc_req_tag,mc_rsp_tag,mc_close_tag_base;
 logic [4:0] mc_req_record_beats;
 logic [511:0] mc_rsp_data;
 logic mc_close_valid,mc_close_ready;
 logic service_valid,service_ready,service_cancel_valid,service_cancel_ready;
 logic [127:0] service_owner,service_done_owner;
 logic [31:0] service_ticket,service_done_ticket;
 logic [1023:0] service_descriptor;
 logic service_done_valid,service_done_ready;
 logic [15:0] service_done_status;
 logic [31:0] service_done_read_bytes,service_done_write_bytes;
 logic idle,pm_trace_valid;
 logic [31:0] protocol_fault_cycles,retired_instructions;
 logic [13:0] pm_trace_address;
 lc_native_scope_controller dut(.*);
 logic [127:0] input_key;
 logic [31:0] rf_object_base0,rf_object_base1,output_version;
 logic [63:0] bias_address0,bias_address1;
 logic [9:0] input_s_base,output_s_base0,output_s_base1,scratch_s_base,snapshot_s_base;
 logic record_valid,record_ready,record_way,record_head16,record_create,record_restore,record_final,record_spill;
 logic record_A_first,record_A_last;
 logic [4:0] record_A_uses;
 logic [127:0] record_owner,complete_owner;
 logic [31:0] record_sequence,record_col,complete_sequence;
 logic [63:0] record_address;
 logic [15:0] record_bytes,record_full_k,record_k,complete_next_k;
 logic [3:0] record_context,record_n,complete_context;
 logic complete_valid,complete_ready,complete_error,rejected_complete;
 logic [31:0] native_confirmed_read_bytes,native_confirmed_write_bytes;
 p_scope_range_service service_provider(
   .clk,.reset,.service_valid,.service_ready,.service_owner,.service_ticket,.service_descriptor,
   .expected_topology(session_topology),.service_cancel_valid,.service_cancel_ready,
   .service_done_valid,.service_done_ready,.service_done_owner,.service_done_ticket,.service_done_status,
   .native_confirmed_read_bytes,.native_confirmed_write_bytes,.service_done_read_bytes,.service_done_write_bytes,
   .input_key,.rf_object_base0,.rf_object_base1,.output_version,.bias_address0,.bias_address1,
   .input_s_base,.output_s_base0,.output_s_base1,.scratch_s_base,.snapshot_s_base,
   .record_valid,.record_ready,.record_owner,.record_sequence,.record_address,.record_bytes,.record_full_k,.record_k,
   .record_col,.record_context,.record_n,.record_way,.record_head16,.record_create,.record_restore,.record_final,.record_spill,
   .record_A_first,.record_A_last,.record_A_uses,.complete_valid,.complete_ready,.complete_owner,.complete_sequence,
   .complete_context,.complete_next_k,.complete_error,.rejected_complete
 );
 logic [127:0] image[22],bad_image[22];
 logic [511:0] scope_images[8];
 logic request_enable,close_enable,record_enable,inject_record_error;
 integer desc_mode,seed,cycle,pm_reads,requests,records,completed;
 logic [31:0] good_crc,bad_crc;
 string path,bad_path,scope_path,trace;
 integer trace_fd;
 logic [1:0] pending_reads;
 logic [31:0] pending_tags[2];
 logic [511:0] pending_data[2];
 integer read_delay[2];
 logic [5:0] pending_records;
 logic [127:0] record_keys[6];
 logic [31:0] record_ids[6];
 logic [3:0] record_contexts[6];
 logic [15:0] record_next[6];
 logic record_snapshots[6];
 integer record_delay[6];
 logic response_slot;
 logic [2:0] complete_slot;
 logic available_record;
 logic [2:0] free_record_slot;
 always_comb begin
   available_record=0;free_record_slot=0;
   for(integer i=0;i<6;i=i+1)if(!pending_records[i]&&!available_record)begin available_record=1;free_record_slot=3'(i);end
 end
 assign mc_req_ready=request_enable&&!pending_reads[mc_req_tag[0]]&&!mc_rsp_valid;
 assign mc_close_ready=close_enable;
 assign record_ready=record_enable&&available_record;
 task automatic pause(input int n=1);repeat(n)@(negedge clk);endtask
 task automatic cfg_send(input logic [1:0] op,input logic [7:0] expected=0);
   cfg_op=op;cfg_valid=1;do @(posedge clk);while(!cfg_ready);@(negedge clk);cfg_valid=0;
   while(!cfg_rsp_valid)@(negedge clk);
   assert(cfg_status==expected)else $fatal(1,"cfg status %0d != %0d",cfg_status,expected);
   cfg_rsp_ready=1;pause();cfg_rsp_ready=0;
 endtask
 task automatic boot(input int gen,input bit bad_table=0);
   cfg_generation=32'(gen);cfg_send(0);
   for(integer i=0;i<22;i=i+1)begin cfg_address=14'(16*i);cfg_data=bad_table?bad_image[i]:image[i];cfg_send(1);end
   cfg_crc=bad_table?bad_crc:good_crc;cfg_send(2);assert(certified);
 endtask
 task automatic configure_session(input int gen);
   session_generation=32'(gen);session_valid=1;
   do @(posedge clk);while(!session_ready);@(negedge clk);session_valid=0;
 endtask

 logic  release_valid_i;
 logic [31:0] release_sequence_i;
 logic [31:0] release_epoch_i;
 logic  deploy_valid_i;
 logic [31:0] deploy_generation_i;
 logic  release_ready_o;
 logic  poison_o;
 logic  image_valid_o;
 logic  cfg_req_valid_i;
 logic [2:0] cfg_req_op_i;
 logic [31:0] cfg_req_generation_i;
 logic [13:0] cfg_req_address_i;
 logic [127:0] cfg_req_data_i;
 logic [15:0] cfg_req_total_bytes_i;
 logic [31:0] cfg_req_image_id_i;
 logic [31:0] cfg_req_topology_id_i;
 logic [31:0] cfg_req_abi_id_i;
 logic [31:0] cfg_req_capacity_id_i;
 logic  cfg_req_proof_i;
 logic  cfg_rsp_ready_i;
 logic  cfg_req_ready_o;
 logic  cfg_rsp_valid_o;
 logic [15:0] cfg_rsp_status_o;
 logic [127:0] cfg_rsp_data_o;
 logic [31:0] cfg_rsp_generation_o;
 logic [3:0] life_o;
 logic [3:0] seq_o;
 logic [31:0] trace_pc_o;
 logic  trace_retire_o;
 logic [7:0] trace_opcode_o;
 logic [1:0] trace_pm_owner_o;
 logic  trace_ireg_valid_o;
 logic  start_valid_i;
 logic  start_credit_i;
 logic [31:0] start_job_i;
 logic [31:0] start_epoch_i;
 logic [31:0] start_sequence_i;
 logic [31:0] start_generation_i;
 logic [287:0] local_image_ids_i;
 logic  start_ready_o;
 logic [31:0] frame_fault_count;
 logic  result_valid_o;
 logic  result_ready_i;
 logic [31:0] result_job_o;
 logic [31:0] result_epoch_o;
 logic [31:0] result_sequence_o;
 logic [15:0] result_status_o;
 logic [31:0] result_error_pc_o;
 logic [7:0] result_source_o;
 logic [31:0] result_child_error_pc_o;
 logic [31:0] result_failed_task_sequence_o;
 logic [31:0] result_confirmed_read_bytes_o;
 logic [31:0] result_confirmed_write_bytes_o;
 logic  result_counter_overflow_o;
 logic  result_saturated_o;
 logic [15:0] trace_live_tokens_o;
 logic [8:0] trace_block_active_o;
 logic [8:0] trace_terminal_full_o;
 logic [8:0] trace_READY_full_o;
 logic  trace_aborting_o;
 logic  recover_valid_i;
 logic  recover_ready_o;
 logic [31:0] protocol_fault_count_o;
 logic mother_tx_credit,mother_rx_valid,mother_rx_ready,mother_rx_sop,mother_rx_eop;
 logic [127:0] mother_rx_data;
 logic [7:0] mother_rx_source;
 logic inject_valid;
 logic [1:0] inject_word;
 logic [511:0] inject_packet;
 assign mother_rx_valid=inject_valid||tx_valid;
 assign mother_rx_data=inject_valid?inject_packet[128*inject_word+:128]:tx_data;
 assign mother_rx_source=inject_valid?8'd8:tx_source;
 assign mother_rx_sop=inject_valid?inject_word==0:tx_sop;
 assign mother_rx_eop=inject_valid?inject_word==3:tx_eop;
 assign tx_ready=mother_rx_ready&&!inject_valid;
 mother_control_native64_transport128 mother(
   .clk_i(clk),
   .rst_ni(!reset),
   .release_valid_i(release_valid_i),
   .release_sequence_i(release_sequence_i),
   .release_epoch_i(release_epoch_i),
   .deploy_valid_i(deploy_valid_i),
   .deploy_generation_i(deploy_generation_i),
   .release_ready_o(release_ready_o),
   .poison_o(poison_o),
   .image_valid_o(image_valid_o),
   .cfg_req_valid_i(cfg_req_valid_i),
   .cfg_req_op_i(cfg_req_op_i),
   .cfg_req_generation_i(cfg_req_generation_i),
   .cfg_req_address_i(cfg_req_address_i),
   .cfg_req_data_i(cfg_req_data_i),
   .cfg_req_total_bytes_i(cfg_req_total_bytes_i),
   .cfg_req_image_id_i(cfg_req_image_id_i),
   .cfg_req_topology_id_i(cfg_req_topology_id_i),
   .cfg_req_abi_id_i(cfg_req_abi_id_i),
   .cfg_req_capacity_id_i(cfg_req_capacity_id_i),
   .cfg_req_proof_i(cfg_req_proof_i),
   .cfg_rsp_ready_i(cfg_rsp_ready_i),
   .cfg_req_ready_o(cfg_req_ready_o),
   .cfg_rsp_valid_o(cfg_rsp_valid_o),
   .cfg_rsp_status_o(cfg_rsp_status_o),
   .cfg_rsp_data_o(cfg_rsp_data_o),
   .cfg_rsp_generation_o(cfg_rsp_generation_o),
   .life_o(life_o),
   .seq_o(seq_o),
   .trace_pc_o(trace_pc_o),
   .trace_retire_o(trace_retire_o),
   .trace_opcode_o(trace_opcode_o),
   .trace_pm_owner_o(trace_pm_owner_o),
   .trace_ireg_valid_o(trace_ireg_valid_o),
   .start_valid_i(start_valid_i),
   .start_credit_i(start_credit_i),
   .start_job_i(start_job_i),
   .start_epoch_i(start_epoch_i),
   .start_sequence_i(start_sequence_i),
   .start_generation_i(start_generation_i),
   .local_image_ids_i(local_image_ids_i),
   .local_enabled_i({8'd0,prepared}),
   .start_ready_o(start_ready_o),
   .tx_valid(rx_valid),
   .tx_ready(rx_ready),
   .tx_data(rx_data),
   .tx_target(rx_target),
   .tx_sop(rx_sop),
   .tx_eop(rx_eop),
   .tx_credit(mother_tx_credit),
   .rx_valid(mother_rx_valid),
   .rx_ready(mother_rx_ready),
   .rx_data(mother_rx_data),
   .rx_source(mother_rx_source),
   .rx_sop(mother_rx_sop),
   .rx_eop(mother_rx_eop),
   .transport_drained_i(idle&&!rx_valid&&!tx_valid&&!inject_valid),
   .frame_fault_count(frame_fault_count),
   .result_valid_o(result_valid_o),
   .result_ready_i(result_ready_i),
   .result_job_o(result_job_o),
   .result_epoch_o(result_epoch_o),
   .result_sequence_o(result_sequence_o),
   .result_status_o(result_status_o),
   .result_error_pc_o(result_error_pc_o),
   .result_source_o(result_source_o),
   .result_child_error_pc_o(result_child_error_pc_o),
   .result_failed_task_sequence_o(result_failed_task_sequence_o),
   .result_confirmed_read_bytes_o(result_confirmed_read_bytes_o),
   .result_confirmed_write_bytes_o(result_confirmed_write_bytes_o),
   .result_counter_overflow_o(result_counter_overflow_o),
   .result_saturated_o(result_saturated_o),
   .trace_live_tokens_o(trace_live_tokens_o),
   .trace_block_active_o(trace_block_active_o),
   .trace_terminal_full_o(trace_terminal_full_o),
   .trace_READY_full_o(trace_READY_full_o),
   .trace_aborting_o(trace_aborting_o),
   .recover_valid_i(recover_valid_i),
   .recover_ready_o(recover_ready_o),
   .protocol_fault_count_o(protocol_fault_count_o)
 );
 logic [127:0] mother_image[14];
 string mother_path;
 integer MC_calls,MC_cancels,MC_flits,MC_returns,MC_PM_reads;
 always @(posedge clk)if(reset)begin
   MC_calls<=0;MC_cancels<=0;MC_flits<=0;MC_returns<=0;MC_PM_reads<=0;
 end else begin
   if(rx_valid&&rx_ready)begin
     MC_flits<=MC_flits+1;
     if(rx_sop)begin if(rx_data[16+:8]==0)MC_calls<=MC_calls+1;else MC_cancels<=MC_cancels+1;end
   end
   if(tx_valid&&tx_ready&&tx_eop)MC_returns<=MC_returns+1;
   if(mother.mother.pm_req_valid_o&&mother.mother.pm_req_ready_i&&!mother.mother.pm_req_write_o)
     MC_PM_reads<=MC_PM_reads+1;
   if(result_valid_o)assert(trace_live_tokens_o==0&&trace_block_active_o==0&&!poison_o);
   if(mc_close_valid)assert(mc_close_tag_base=={pending_tags[0][31:1],1'b0});
 end
 task automatic mother_config(input logic [2:0] op,input int address=0,input logic [127:0] value=0);
   cfg_req_op_i=op;cfg_req_address_i=14'(address);cfg_req_data_i=value;cfg_req_valid_i=1;
   do @(posedge clk);while(!cfg_req_ready_o);@(negedge clk);cfg_req_valid_i=0;
   while(!cfg_rsp_valid_o)@(negedge clk);
   assert(cfg_rsp_status_o==0);
   if(op==2)assert(cfg_rsp_data_o==mother_image[address>>4]);
   cfg_rsp_ready_i=1;pause();cfg_rsp_ready_i=0;
 endtask
 task automatic run_mother(input int job_sequence,input int mode=0);
   assert(idle&&pending_records==0&&pending_reads==0&&!mc_rsp_valid&&!complete_valid);
   desc_mode=mode;records=0;completed=0;native_confirmed_read_bytes=0;native_confirmed_write_bytes=0;
   start_job_i=7;start_epoch_i=8;start_sequence_i=32'(job_sequence);start_generation_i=1;start_valid_i=1;
   do @(posedge clk);while(!start_ready_o);@(negedge clk);start_valid_i=0;
 endtask
 task automatic take_mother_result(input logic [15:0] status_code,input bit success=0);
   while(!result_valid_o)@(negedge clk);pause(seed%3+2);
   assert(result_status_o==status_code&&result_job_o==7&&result_epoch_o==8&&result_sequence_o==start_sequence_i);
   assert(idle&&pending_records==0&&pending_reads==0&&!mc_rsp_valid&&!complete_valid);
   if(success)assert(records==8&&completed==8&&result_confirmed_read_bytes_o==native_confirmed_read_bytes+128&&
      result_confirmed_write_bytes_o==128&&!result_counter_overflow_o&&!result_saturated_o&&retired_instructions==3);
   result_ready_i=1;pause();result_ready_i=0;pause();assert(life_o==5&&image_valid_o);
 endtask
 wire unused_mother_outputs=^{release_ready_o,poison_o,image_valid_o,cfg_req_ready_o,cfg_rsp_valid_o,cfg_rsp_status_o,cfg_rsp_data_o,cfg_rsp_generation_o,life_o,seq_o,trace_pc_o,trace_retire_o,trace_opcode_o,trace_pm_owner_o,trace_ireg_valid_o,start_ready_o,frame_fault_count,result_valid_o,result_job_o,result_epoch_o,result_sequence_o,result_status_o,result_error_pc_o,result_source_o,result_child_error_pc_o,result_failed_task_sequence_o,result_confirmed_read_bytes_o,result_confirmed_write_bytes_o,result_counter_overflow_o,result_saturated_o,trace_live_tokens_o,trace_block_active_o,trace_terminal_full_o,trace_READY_full_o,trace_aborting_o,recover_ready_o,protocol_fault_count_o,mother_tx_credit};

 // Finite DDR and native-completion peers. They expose real request/return
 // events but do not claim real W arithmetic, SRAM writes or DDR51.2GB/s.
 always @(posedge clk)begin
   if(reset)begin
     cycle<=0;pm_reads<=0;requests<=0;pending_reads<=0;mc_rsp_valid<=0;mc_rsp_tag<=0;mc_rsp_data<=0;
     response_slot<=0;pending_records<=0;complete_valid<=0;complete_owner<=0;complete_sequence<=0;
     complete_context<=0;complete_next_k<=0;complete_error<=0;complete_slot<=0;
     for(integer i=0;i<2;i=i+1)begin pending_tags[i]<=0;pending_data[i]<=0;read_delay[i]<=0;end
     for(integer i=0;i<6;i=i+1)begin record_keys[i]<=0;record_ids[i]<=0;record_contexts[i]<=0;record_next[i]<=0;record_snapshots[i]<=0;record_delay[i]<=0;end
   end else begin
     cycle<=cycle+1;
     if(rx_valid&&rx_ready)$fwrite(trace_fd,"%0d,RX,%0d\n",cycle,int'(rx_eop));
     if(service_valid&&service_ready)$fwrite(trace_fd,"%0d,SERVICE,0\n",cycle);
     if(service_done_valid&&service_done_ready)$fwrite(trace_fd,"%0d,SERVICE_DONE,%0d\n",cycle,service_done_status);
     if(pm_trace_valid)begin pm_reads<=pm_reads+1;$fwrite(trace_fd,"%0d,PM,%0d\n",cycle,pm_trace_address);end
     if(mc_req_valid&&mc_req_ready)begin
       assert(mc_req_address==64'h4000+(mc_req_tag[0]?64'd64:0)&&mc_req_record_beats==2&&!mc_req_channel);
       pending_reads[mc_req_tag[0]]<=1;pending_tags[mc_req_tag[0]]<=mc_req_tag;
       pending_data[mc_req_tag[0]]<=scope_images[2*desc_mode+int'(mc_req_tag[0])];
       read_delay[mc_req_tag[0]]<=2+seed%3+int'(!mc_req_tag[0]);requests<=requests+1;
       $fwrite(trace_fd,"%0d,DDR_REQ,%0d\n",cycle,mc_req_tag);
     end
     for(integer i=0;i<2;i=i+1)if(pending_reads[i]&&read_delay[i]>0)read_delay[i]<=read_delay[i]-1;
     if(mc_rsp_valid&&mc_rsp_ready)begin mc_rsp_valid<=0;pending_reads[response_slot]<=0;$fwrite(trace_fd,"%0d,DDR_RSP,%0d\n",cycle,mc_rsp_tag);end
     if(!mc_rsp_valid)begin
       if(pending_reads[1]&&read_delay[1]==0)begin response_slot<=1;mc_rsp_tag<=pending_tags[1];mc_rsp_data<=pending_data[1];mc_rsp_valid<=1;end
       else if(pending_reads[0]&&read_delay[0]==0)begin response_slot<=0;mc_rsp_tag<=pending_tags[0];mc_rsp_data<=pending_data[0];mc_rsp_valid<=1;end
     end
     if(record_valid&&record_ready)begin
       assert(record_owner==service_owner&&record_full_k==256&&record_n==8&&record_context<4&&record_col<16);
       assert(record_bytes==(record_head16?1152:1088)&&record_create==(record_k==0)&&record_final==(record_k==128));
       assert(!record_restore&&!record_spill&&record_A_uses==4);
       assert(input_key==128'h00000001000000090000000800000007&&rf_object_base0==4096&&rf_object_base1==8192&&output_version==1);
       assert(bias_address0==0&&bias_address1==0&&input_s_base==0&&output_s_base0==256&&output_s_base1==320&&scratch_s_base==512&&snapshot_s_base==768);
       pending_records[free_record_slot]<=1;record_keys[free_record_slot]<=record_owner;record_ids[free_record_slot]<=record_sequence;
       record_contexts[free_record_slot]<=record_context;record_next[free_record_slot]<=record_k+128;
       record_snapshots[free_record_slot]<=record_final||record_spill;record_delay[free_record_slot]<=12+seed%4;
       records<=records+1;native_confirmed_read_bytes<=native_confirmed_read_bytes+{16'd0,record_bytes};
       $fwrite(trace_fd,"%0d,RECORD,%0d\n",cycle,record_sequence);
     end
     for(integer i=0;i<6;i=i+1)if(pending_records[i]&&record_delay[i]>0)record_delay[i]<=record_delay[i]-1;
     if(complete_valid&&complete_ready)begin
       pending_records[complete_slot]<=0;complete_valid<=0;completed<=completed+1;
       if(record_snapshots[complete_slot])native_confirmed_write_bytes<=native_confirmed_write_bytes+32;
       $fwrite(trace_fd,"%0d,COMPLETED,%0d\n",cycle,complete_sequence);
     end
     if(!complete_valid)begin
       for(integer i=5;i>=0;i=i-1)if(pending_records[i]&&record_delay[i]==0)begin
         complete_slot<=3'(i);complete_valid<=1;complete_owner<=record_keys[i];complete_sequence<=record_ids[i];
         complete_context<=record_contexts[i];complete_next_k<=record_next[i];complete_error<=inject_record_error&&record_ids[i]==100;
       end
     end
     if(tx_valid&&tx_ready)$fwrite(trace_fd,"%0d,RETURN,%0d\n",cycle,int'(tx_eop));
   end
 end
 initial begin
   reset=1;session_valid=0;session_generation=1;session_topology=25001;transport_drained=1;
   cfg_valid=0;cfg_rsp_ready=0;cfg_op=0;cfg_generation=1;cfg_abi=32'h02500002;cfg_capacity=32'h02510001;
   cfg_bytes=352;cfg_address=0;cfg_data=0;cfg_crc=0;
   request_enable=1;close_enable=1;record_enable=1;inject_record_error=0;desc_mode=0;records=0;completed=0;
   native_confirmed_read_bytes=0;native_confirmed_write_bytes=0;seed=1;
   if($value$plusargs("SEED=%d",seed))begin end
   path="kernel.mem";bad_path="bad-table.mem";scope_path="scopes.mem";trace="lc-native.csv";
   if($value$plusargs("IMAGE=%s",path))begin end
   if($value$plusargs("BAD_IMAGE=%s",bad_path))begin end
   if($value$plusargs("SCOPES=%s",scope_path))begin end
   if($value$plusargs("TRACE=%s",trace))begin end
   assert($value$plusargs("CRC=%h",good_crc));assert($value$plusargs("BAD_CRC=%h",bad_crc));
   $readmemh(path,image);$readmemh(bad_path,bad_image);$readmemh(scope_path,scope_images);trace_fd=$fopen(trace,"w");

   release_valid_i=0;
   release_sequence_i=0;
   release_epoch_i=0;
   deploy_valid_i=0;
   deploy_generation_i=0;
   cfg_req_valid_i=0;
   cfg_req_op_i=0;
   cfg_req_generation_i=0;
   cfg_req_address_i=0;
   cfg_req_data_i=0;
   cfg_req_total_bytes_i=0;
   cfg_req_image_id_i=0;
   cfg_req_topology_id_i=0;
   cfg_req_abi_id_i=0;
   cfg_req_capacity_id_i=0;
   cfg_req_proof_i=0;
   cfg_rsp_ready_i=0;
   start_valid_i=0;
   start_credit_i=0;
   start_job_i=0;
   start_epoch_i=0;
   start_sequence_i=0;
   start_generation_i=0;
   local_image_ids_i=0;
   result_ready_i=0;
   recover_valid_i=0;
   inject_valid=0;inject_word=0;inject_packet=0;
   mother_path="mother.mem";if($value$plusargs("MOTHER_IMAGE=%s",mother_path))begin end
   $readmemh(mother_path,mother_image);
   pause(3);reset=0;pause();boot(1);configure_session(1);
   release_valid_i=1;release_sequence_i=1;release_epoch_i=1;
   do @(posedge clk);while(!release_ready_o);@(negedge clk);release_valid_i=0;
   cfg_req_generation_i=1;cfg_req_total_bytes_i=224;cfg_req_image_id_i=900;cfg_req_topology_id_i=25001;
   cfg_req_abi_id_i=32'h02500002;cfg_req_capacity_id_i=32'h02590003;cfg_req_proof_i=1;
   mother_config(0);
   for(integer i=0;i<14;i=i+1)mother_config(1,16*i,mother_image[i]);
   for(integer i=0;i<14;i=i+1)mother_config(2,16*i);
   mother_config(3);mother_config(4);
   local_image_ids_i=0;local_image_ids_i[31:0]=25001;
   assert(prepared);
   deploy_generation_i=1;deploy_valid_i=1;start_credit_i=1;
   while(life_o!=5)@(negedge clk);
   run_mother(1);take_mother_result(0,1);
   run_mother(2,3);take_mother_result(0,1);
   run_mother(3,1);take_mother_result(36);assert(records==0);
   record_enable=0;run_mother(4);while(!record_valid)@(negedge clk);
   // Wrong-source complete frame provokes real MC fault17 and real CANCEL.
   // It cannot release the still-live P task or the held range record.
   inject_packet=0;inject_packet[0+:16]=2;inject_packet[16+:8]=2;inject_packet[24+:8]=8;
   inject_packet[32+:32]=7;inject_packet[64+:32]=8;inject_packet[96+:32]=4;
   inject_packet[136+:8]=255;inject_packet[320+:32]=32'hffffffff;
   inject_packet[352+:32]=1;inject_packet[384+:32]=25001;inject_valid=1;
   for(integer w=0;w<4;w=w+1)begin inject_word=2'(w);do @(posedge clk);while(!mother_rx_ready);@(negedge clk);end
   inject_valid=0;pause(20);assert(!result_valid_o&&record_valid&&trace_block_active_o[0]);
   record_enable=1;take_mother_result(17);
   assert(MC_calls==4&&MC_cancels==1&&MC_returns==4&&MC_flits==20&&protocol_fault_count_o==1&&frame_fault_count==0&&protocol_fault_cycles==0);
   $display("PASS actual_MC_LC seed=%0d CALL=%0d CANCEL=%0d LC_PM=%0d MC_PM=%0d cycles=%0d",seed,MC_calls,MC_cancels,pm_reads,MC_PM_reads,cycle);
   $fclose(trace_fd);$finish;
 end
 wire unused_observed=^{cfg_actual_crc,rejected_complete,record_address,record_way,record_A_first,record_A_last};
 initial begin #2000000;$fatal(1,"native LC timeout state=%0d records=%0d completed=%0d",dut.state,records,completed);end
endmodule
