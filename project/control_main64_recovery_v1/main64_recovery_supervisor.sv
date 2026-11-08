`timescale 1ns/1ps
// This host/result island survives the coordinated inner-cohort reset.
module main64_recovery_supervisor #(parameter integer DRAIN_LIMIT=1024, KIND0=0, KIND1=KIND0)(
 input wire [2:0] route_image_valid_i,
 output reg route_update_i,route_direction_i,output reg [9:0] route_base_i,
 output reg [2:0] route_count_i,output reg [31:0] route_first_i,route_tag_i,output reg [7:0] route_stride_i,
 input wire clk_i,rst_ni,input wire cmd_valid_i,output wire cmd_ready_o,
 input wire [3:0] cmd_op_i,input wire [1:0] cmd_target_i,input wire [13:0] cmd_address_i,input wire [255:0] cmd_data_i,
 output wire reply_valid_o,input wire reply_ready_i,output wire [15:0] reply_status_o,output wire [511:0] reply_data_o,
 output wire engine_cmd_valid_i,input wire engine_cmd_ready_o,output wire [3:0] engine_cmd_op_i,
 output wire [1:0] engine_cmd_target_i,output wire [13:0] engine_cmd_address_i,output wire [255:0] engine_cmd_data_i,
 input wire engine_reply_valid_o,output wire engine_reply_ready_i,input wire [15:0] engine_reply_status_o,input wire [511:0] engine_reply_data_o,
 input wire run_active_o,link_pending_o,reset_ready_o,input wire [2:0] image_valid_o,poison_o,
 input wire [31:0] commit_count_o,ack_count_o,input wire quiescent_o,fault_o,engine_result_valid_o,
 input wire [31:0] observed_reads_o,observed_writes_o,output wire inner_rst_ni,halt_i
);
 localparam [2:0] NORMAL=0,DRAIN=1,RESET=2,WAIT_READY=3,FAILED=4,QUARANTINE=5;
 reg [2:0] state;reg [31:0] deadline;reg [2:0] reset_cycles;
 reg pass,pass_terminal,local_reply,consume_result,failure_valid,publish_needed;
 reg [3:0] pass_op;reg [255:0] pass_data;
 reg [15:0] response_status,reason;reg [511:0] response_data,failure;
 reg [31:0] job,epoch,job_sequence,generation,epoch_watermark;
 reg [31:0] saved_reads,saved_writes,saved_commits,saved_acks;
 reg [7:0] requested_mask;
 wire automatic_fault=state==NORMAL && run_active_o && fault_o;
 wire stale_release=state==NORMAL && cmd_op_i==0 && cmd_data_i[63:32]<=epoch_watermark;
 wire special=cmd_op_i==15 || state!=NORMAL || stale_release;
 wire fire=cmd_valid_i && cmd_ready_o;
 wire response_fire=reply_valid_o && reply_ready_i;
 wire identity_ok=cmd_data_i[47:16]==job && cmd_data_i[79:48]==epoch &&
                  cmd_data_i[111:80]==job_sequence && cmd_data_i[143:112]==generation;
 assign halt_i=state!=NORMAL;
 assign inner_rst_ni=rst_ni && state!=RESET;
 assign cmd_ready_o=rst_ni && !pass && !local_reply && !automatic_fault && (special || engine_cmd_ready_o);
 assign engine_cmd_valid_i=rst_ni && cmd_valid_i && cmd_ready_o && !special;
 assign engine_cmd_op_i=cmd_op_i;assign engine_cmd_target_i=cmd_target_i;
 assign engine_cmd_address_i=cmd_address_i;assign engine_cmd_data_i=cmd_data_i;
 assign engine_reply_ready_i=rst_ni && pass && reply_ready_i;
 assign reply_valid_o=rst_ni && (local_reply || pass && engine_reply_valid_o);
 assign reply_status_o=local_reply ? response_status : engine_reply_status_o;
 assign reply_data_o=local_reply ? response_data : engine_reply_data_o;
 function automatic [511:0] status_word;
  reg [511:0] v;
  begin
   v=0;v[2:0]=image_valid_o;v[5:3]=poison_o;v[16]=run_active_o;
   v[17]=link_pending_o || state==DRAIN || state==RESET || state==WAIT_READY || state==QUARANTINE;
   v[18]=failure_valid || state==NORMAL && engine_result_valid_o;v[19]=state==QUARANTINE;
   v[22:20]=state;v[23]=quiescent_o;v[31:24]=requested_mask;
   v[63:32]=epoch_watermark;v[79:64]=reason;v[111:80]=observed_reads_o;v[143:112]=observed_writes_o;
   v[175:144]=commit_count_o;v[207:176]=ack_count_o;status_word=v;
  end
 endfunction
 task snapshot_failure;
  input [15:0] status;input quarantined;
  reg [511:0] v;
  begin
   v=0;v[31:0]=job;v[63:32]=epoch;v[95:64]=job_sequence;v[111:96]=status;
   v[143:112]=32'hffffffff;v[151:144]=255;v[183:152]=32'hffffffff;
   v[247:216]=quarantined ? observed_reads_o : saved_reads;
   v[279:248]=quarantined ? observed_writes_o : saved_writes;
   v[282]=1;v[283]=quarantined;v[284]=1;
   v[316:285]=quarantined ? commit_count_o : saved_commits;
   v[348:317]=quarantined ? ack_count_o : saved_acks;
   v[356:349]=requested_mask;failure<=v;failure_valid<=1;
  end
 endtask
 always @(posedge clk_i or negedge rst_ni)begin
  if(!rst_ni)begin
   state<=NORMAL;deadline<=0;reset_cycles<=0;pass<=0;pass_terminal<=0;local_reply<=0;consume_result<=0;
   failure_valid<=0;publish_needed<=0;pass_op<=0;pass_data<=0;response_status<=0;reason<=0;
   response_data<=0;failure<=0;job<=0;epoch<=0;job_sequence<=0;generation<=0;epoch_watermark<=0;
   route_update_i<=0;route_direction_i<=0;route_base_i<=0;route_count_i<=0;route_first_i<=0;route_tag_i<=0;route_stride_i<=0;
   saved_reads<=0;saved_writes<=0;saved_commits<=0;saved_acks<=0;requested_mask<=0;
  end else begin
   route_update_i<=0;
   if(response_fire)begin
    if(local_reply)begin
     local_reply<=0;
     if(consume_result)begin failure_valid<=0;consume_result<=0;if(state==FAILED)state<=NORMAL;end
    end else begin
     pass<=0;
     if(pass_op==0 && engine_reply_status_o==0)epoch_watermark<=pass_data[63:32];
    end
   end
   if(fire)begin
    if(!special)begin
     pass<=1;pass_op<=cmd_op_i;pass_data<=cmd_data_i;
     pass_terminal<=cmd_op_i==10 && cmd_target_i==3 && cmd_address_i==0 && cmd_data_i==0 && engine_result_valid_o;
     if(cmd_op_i==8 && !run_active_o)begin job<=cmd_data_i[31:0];epoch<=cmd_data_i[63:32];job_sequence<=cmd_data_i[95:64];generation<=cmd_data_i[127:96];end
    end else begin
     local_reply<=1;response_status<=0;response_data<=0;consume_result<=0;
     if(cmd_op_i==15)begin
      if(cmd_target_i!=3)response_status<=16'h102;
      else if(cmd_address_i!=0 || cmd_data_i[255:144]!=0)response_status<=16'h103;
      else case(cmd_data_i[7:0])
       0,1:begin
        if(state!=NORMAL || engine_result_valid_o)response_status<=16'h106;
        else if(cmd_data_i[7:0]==0 && !run_active_o)response_status<=16'h105;
        else if(cmd_data_i[7:0]==0 && cmd_data_i[15:8]!=0 || cmd_data_i[7:0]==1 && (cmd_data_i[15:8]==0 || cmd_data_i[15:8]>3))response_status<=16'h103;
        else if(run_active_o && !identity_ok || !run_active_o && cmd_data_i[143:16]!=0)response_status<=16'h107;
        else begin
         state<=DRAIN;deadline<=0;reason<=11;publish_needed<=run_active_o;
         requested_mask<=cmd_data_i[7:0]==0 ? 8'd3 : cmd_data_i[15:8];
        end
       end
       2:if(cmd_data_i[143:8]!=0)response_status<=16'h103;else response_data<=status_word();
       3:begin
        if(cmd_data_i[143:8]!=0)response_status<=16'h103;
        else if(state!=QUARANTINE || failure_valid)response_status<=16'h105;
        else begin state<=DRAIN;deadline<=0;publish_needed<=0;end
       end
       4:begin
        if(state!=NORMAL || run_active_o || engine_result_valid_o || |route_image_valid_i || link_pending_o)response_status<=16'h106;
        else if(cmd_data_i[255:94]!=0 || cmd_data_i[21:19]>4 ||
                ({1'b0,cmd_data_i[18:9]}+{8'b0,cmd_data_i[21:19]})>1024)response_status<=16'h103;
        else if(cmd_data_i[21:19]!=0 && !(KIND0==0 && KIND1==0 && cmd_data_i[21:19]==2 && cmd_data_i[61:54]==3 ||
                 !cmd_data_i[8] && KIND1==3 && (KIND0==0 || KIND0==1 || KIND0==2) && cmd_data_i[61:54]==1 ||
                 !cmd_data_i[8] && KIND0==4 && KIND1==3 && cmd_data_i[61:54]==0))response_status<=16'h103;
        else begin
         route_update_i<=1;route_direction_i<=cmd_data_i[8];route_base_i<=cmd_data_i[18:9];route_count_i<=cmd_data_i[21:19];
         route_first_i<=cmd_data_i[53:22];route_stride_i<=cmd_data_i[61:54];route_tag_i<=cmd_data_i[93:62];
        end
       end
       default:response_status<=16'h101;
      endcase
     end else if(cmd_op_i==9)begin
      if(cmd_target_i!=3 || cmd_address_i!=0 || cmd_data_i!=0)response_status<=16'h103;
      else response_data<=status_word();
     end else if(cmd_op_i==10)begin
      if(cmd_target_i!=3 || cmd_address_i!=0 || cmd_data_i!=0)response_status<=16'h103;
      else if(!failure_valid)response_status<=16'h105;
      else begin response_data<=failure;consume_result<=1;end
     end else response_status<=stale_release ? 16'h107 : 16'h106;
    end
   end
   if(automatic_fault)begin
    state<=DRAIN;deadline<=0;reason<=16'h200;requested_mask<=3;
    // A forwarded RESULT already owns the terminal response. Recover health,
    // but do not publish a second terminal for that same job.
    publish_needed<=!(pass && pass_op==10 && pass_terminal);
   end
   if(state==DRAIN)begin
    if(quiescent_o)begin
     deadline<=0;
     // Host response backpressure is not a hardware drain timeout.
     if(!pass)begin
      saved_reads<=observed_reads_o;saved_writes<=observed_writes_o;
      saved_commits<=commit_count_o;saved_acks<=ack_count_o;reset_cycles<=0;state<=RESET;
     end
    end else if(deadline>=DRAIN_LIMIT-1)begin
     state<=QUARANTINE;
     if(publish_needed)begin snapshot_failure(16'h201,1'b1);publish_needed<=0;end
    end else deadline<=deadline+1;
   end
   if(state==RESET)begin
    if(reset_cycles==3)state<=WAIT_READY;else reset_cycles<=reset_cycles+1'b1;
   end
   if(state==WAIT_READY && reset_ready_o)begin
    if(publish_needed)begin snapshot_failure(reason,1'b0);publish_needed<=0;state<=FAILED;end
    else state<=NORMAL;
   end
  end
 end
endmodule
