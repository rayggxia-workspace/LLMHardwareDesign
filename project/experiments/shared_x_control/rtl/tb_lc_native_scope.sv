`timescale 1ns/1ps
// Real native LC PM/boot, physical128bit CALL/return, real DDR fetch/CRC,
// root's actual typed decoder and six-ticket range iterator. Record-provider
// completions below are finite peers, not numerical M/real S qualification.
module tb_lc_native_scope;
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
 logic [511:0] active_packet;
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
 task automatic send_frame(input logic [511:0] packet);
   for(integer w=0;w<4;w=w+1)begin
     rx_valid=1;rx_data=packet[128*w+:128];rx_sop=w==0;rx_eop=w==3;
     do @(posedge clk);while(!rx_ready);@(negedge clk);rx_valid=0;pause(seed%2);
   end
   rx_sop=0;rx_eop=0;
 endtask
 task automatic call(input int seq,input int mode=0,input logic [31:0] r2=32'h00010080);
   assert(idle&&pending_records==0&&pending_reads==0&&!mc_rsp_valid&&!complete_valid);
   desc_mode=mode;records=0;completed=0;native_confirmed_read_bytes=0;native_confirmed_write_bytes=0;
   active_packet=0;active_packet[0+:16]=2;active_packet[24+:8]=0;active_packet[32+:32]=7;
   active_packet[64+:32]=8;active_packet[96+:32]=32'(seq);active_packet[136+:8]=2;
   active_packet[160+:32]=25001;active_packet[192+:32]=25001;active_packet[224+:32]=session_generation;
   active_packet[256+:64]=64'h4000;active_packet[320+:32]=r2;active_packet[352+:32]=32'h02510001;
   active_packet[384+:32]=25001;active_packet[416+:32]=32'h02500002;
   send_frame(active_packet);
 endtask
 task automatic cancel_call(input bit stale=0,input bit malformed=0);
   logic [511:0] p;
   p=active_packet;p[16+:8]=1;p[256+:256]=0;
   if(stale)p[224+:32]=session_generation-1;
   if(malformed)p[256]=1;
   send_frame(p);
 endtask
 task automatic terminal(input logic [15:0] expected_status,input bit success=0);
   logic [511:0] p;
   logic [127:0] held;
   p=0;
   for(integer w=0;w<4;w=w+1)begin
     while(!tx_valid)@(negedge clk);
     held=tx_data;pause(seed%3+1);
     assert(tx_valid&&tx_data==held&&tx_sop==(w==0)&&tx_eop==(w==3)&&tx_source==0);
     p[128*w+:128]=tx_data;tx_ready=1;pause();tx_ready=0;
   end
   assert(p[24+:8]==0&&p[288+:32]==0&&p[160+:32]==0&&p[0+:16]==2&&p[32+:96]==active_packet[32+:96]&&p[128+:8]==2&&p[136+:8]==255);
   assert(p[352+:32]==session_generation&&p[384+:32]==25001&&p[416+:96]==0);
   assert(p[144+:16]==expected_status)else $fatal(1,"terminal status %0d expected %0d",p[144+:16],expected_status);
   if(success)begin
     assert(p[16+:8]==2&&p[320+:32]==32'hffffffff&&p[256+:32]==0&&retired_instructions==3);
     assert(records==8&&completed==8&&p[192+:32]==native_confirmed_read_bytes+128&&p[224+:32]==128);
   end else assert(p[16+:8]==3);
   pause();assert(idle&&pending_records==0&&pending_reads==0&&!complete_valid&&!mc_rsp_valid);
 endtask
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
   cfg_bytes=352;cfg_address=0;cfg_data=0;cfg_crc=0;rx_valid=0;rx_data=0;rx_sop=0;rx_eop=0;rx_target=0;tx_ready=0;
   request_enable=1;close_enable=1;record_enable=1;inject_record_error=0;desc_mode=0;records=0;completed=0;
   native_confirmed_read_bytes=0;native_confirmed_write_bytes=0;active_packet=0;seed=1;
   if($value$plusargs("SEED=%d",seed))begin end
   path="kernel.mem";bad_path="bad-table.mem";scope_path="scopes.mem";trace="lc-native.csv";
   if($value$plusargs("IMAGE=%s",path))begin end
   if($value$plusargs("BAD_IMAGE=%s",bad_path))begin end
   if($value$plusargs("SCOPES=%s",scope_path))begin end
   if($value$plusargs("TRACE=%s",trace))begin end
   assert($value$plusargs("CRC=%h",good_crc));assert($value$plusargs("BAD_CRC=%h",bad_crc));
   $readmemh(path,image);$readmemh(bad_path,bad_image);$readmemh(scope_path,scope_images);trace_fd=$fopen(trace,"w");
   pause(3);reset=0;pause();
   session_valid=1;pause(3);assert(!session_ready);session_valid=0; // no premature serial burn.
   boot(1);configure_session(1);assert(prepared);cfg_send(0,2);assert(certified); // invalid BEGIN preserves deployment.
   call(1);terminal(0,1);assert(pm_reads==23);
   send_frame(active_packet);pause(8);assert(idle&&!tx_valid); // duplicate CALL never reruns.
   call(2,1);terminal(36);assert(records==0); // service2 is deliberately unsupported.
   call(3,2);terminal(18);assert(records==0); // actual inline CRC failure.
   call(4,3);terminal(0,1);
   record_enable=0;call(5);while(!record_valid)@(negedge clk);
   cancel_call(0,1);pause(5);assert(record_valid&&!tx_valid); // nonzero CANCEL payload rejected.
   cancel_call(1);pause(5);assert(record_valid&&!tx_valid); // stale generation cannot cancel.
   cfg_generation=2;cfg_send(0,5);assert(certified); // boot cannot revoke live owner.
   cancel_call();pause(5);assert(record_valid&&!tx_valid);
   record_enable=1;terminal(3);
   request_enable=0;close_enable=0;call(6);while(!mc_req_valid)@(negedge clk);pause(3);
   cancel_call();pause(3);assert(mc_req_valid&&!tx_valid);request_enable=1;
   while(!mc_close_valid)@(negedge clk);pause(8);assert(!tx_valid&&mc_close_tag_base=={pending_tags[0][31:1],1'b0});
   close_enable=1;terminal(3);assert(records==0);
   call(7,0,32'h00010040);terminal(2);assert(records==0);
   boot(2,1);configure_session(2);call(8);terminal(5);assert(records==0); // CRC-valid bad native-op table.
   boot(3);configure_session(3);call(9);terminal(0,1);
   inject_record_error=1;call(10);terminal(1);inject_record_error=0;
   assert(protocol_fault_cycles>=3&&pending_records==0&&pending_reads==0);
   $display("PASS native_lc seed=%0d PMreads=%0d DDRbeats=%0d cycles=%0d faults=%0d",seed,pm_reads,requests,cycle,protocol_fault_cycles);
   $fclose(trace_fd);$finish;
 end
 wire unused_observed=^{cfg_actual_crc,rejected_complete,record_address,record_way,record_A_first,record_A_last};
 initial begin #2000000;$fatal(1,"native LC timeout state=%0d records=%0d completed=%0d",dut.state,records,completed);end
endmodule
