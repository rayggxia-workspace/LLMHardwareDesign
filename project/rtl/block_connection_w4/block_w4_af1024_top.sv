// Issue151 L4-AF1024: fixed AFULL -> two sequential baseline F1024 jobs.
// Original children remain unchanged. One explicit 2KiB F-gamma FF bank;
// Y stays in the real A T and streams into the real F ingress, no Y array.
module block_w4_af1024_top(
 input wire clk,reset,abort,
 input wire job_valid,output wire job_ready,input wire [31:0] job_generation,
 input wire [15:0] weights_a_version,weights_f_version,
 input wire in_valid,output wire in_ready,input wire [127:0] in_data,
 input wire [31:0] in_generation,input wire [9:0] in_index,input wire in_last,
 output wire input_stored,input wire start_valid,output wire start_ready,output wire busy,
 output wire done_valid,input wire done_ready,output wire done_error,done_saturated,done_partial,
 output wire [8:0] done_words,output wire [31:0] done_generation,
 output wire out_valid,input wire out_ready,output wire [127:0] out_data,
 output wire [9:0] out_index,output wire out_last,output wire [31:0] out_generation,
 output wire a_wreq_valid,input wire a_wreq_ready,
 output wire [31:0] a_wreq_job,output wire [15:0] a_wreq_seq,a_wreq_version,
 output wire [1:0] a_wreq_matrix,output wire [3:0] a_wreq_head,
 output wire [6:0] a_wreq_group,output wire [5:0] a_wreq_chunk,
 input wire a_w_valid,output wire a_w_ready,input wire [31:0] a_w_job,
 input wire [15:0] a_w_seq,a_w_version,input wire [3:0] a_w_index,
 input wire a_w_last,a_w_error,input wire [127:0] a_w_data,
 output wire f_wreq_valid,input wire f_wreq_ready,
 output wire [15:0] f_wreq_job,f_wreq_seq,f_wreq_version,
 output wire [1:0] f_wreq_matrix,output wire [8:0] f_wreq_group,
 output wire [6:0] f_wreq_chunk,output wire f_wreq_row,
 input wire f_w_valid,output wire f_w_ready,
 input wire [15:0] f_w_job,f_w_seq,f_w_version,input wire [4:0] f_w_index,
 input wire f_w_last,f_w_error,input wire [127:0] f_w_data
);
 localparam [3:0] WAIT_JOB=0,A_ADMIT=1,INPUT=2,STORED=3,A_START=4,
  F_HIDDEN=5,F_GAMMA=6,F_STORED=7,F_START=8,F_OUTPUT=9,F_DONE=10,
  WAIT_A_DONE=11,DONE=12;
 reg [3:0] state;
 reg [9:0] input_index;
 reg [6:0] hidden_index,gamma_index;
 reg row_index,frame_active,frame_stored;
 reg a_admitted,a_started,a_closed,f_frame_seen,f_started,f_y_pending;
 reg error_latched,saturation_latched,internal_reset;
 reg [31:0] generation_hold;
 reg [15:0] a_version_hold,f_version_hold;
 reg [15:0] f_job_mirror;
 reg [8:0] a_words_taken,output_count;
 reg [7:0] f_out_count;
 reg [127:0] gamma_bank[0:127];
 wire permit_a_job=1'b1,permit_a_feed=1'b1,permit_a_start=1'b1;
 wire permit_a_take=1'b1,permit_a_done=1'b1;
 wire permit_f_feed=1'b1,permit_f_start=1'b1,permit_f_done=1'b1;
 wire child_reset,input_fire,input_meta_ok,start_fire,a_transfer,f_start_fire,f_hidden_capture;
 wire a_job_valid,a_job_ready,a_in_valid,a_in_ready,a_input_stored,a_start_valid,a_start_ready,a_busy;
 wire a_done_valid,a_done_ready,a_done_error,a_done_saturated;
 wire [8:0] a_done_words;
 wire [31:0] a_done_generation;
 wire a_done_partial,a_out_valid,a_out_ready,a_out_last;
 wire [127:0] a_out_data;
 wire [9:0] a_out_index;
 wire [31:0] a_out_generation;
 wire f_in_valid,f_in_ready,f_input_stored,f_start_valid,f_start_ready,f_busy;
 wire f_done_valid,f_done_ready,f_done_error,f_done_saturated;
 wire f_out_valid,f_out_ready,f_out_last;
 wire [127:0] f_in_data,f_out_data;
 wire [9:0] f_out_index;
 wire a_child_wreq_valid,a_child_w_ready,f_child_wreq_valid,f_child_w_ready;
 wire a_provider_active,f_provider_active,a_frame_lost,f_frame_lost;
 wire a_meta_ok,f_meta_ok,a_bad_output,f_bad_output;
 wire a_bad_done,f_bad_done,fatal_child_now,a_close_fire;
 wire a_sat_observed,f_sat_observed;

 assign child_reset=reset||abort||internal_reset;
 assign job_ready=!child_reset&&state==WAIT_JOB;
 assign input_meta_ok=in_generation==generation_hold&&in_index==input_index&&in_last==(input_index==10'd575);
 assign a_frame_lost=a_admitted&&!a_closed&&!a_busy&&!a_input_stored&&!a_done_valid;
 assign f_frame_lost=f_frame_seen&&!f_busy&&!f_input_stored&&!f_done_valid;
 assign a_meta_ok=a_words_taken<9'd256&&a_out_generation==generation_hold&&
  a_out_index=={1'd0,a_words_taken}&&a_out_last==(a_words_taken==9'd255);
 assign f_meta_ok=f_out_count<8'd128&&f_out_index=={2'd0,f_out_count}&&f_out_last==(f_out_count==8'd127);
 assign a_bad_output=a_started&&!a_closed&&a_out_valid&&!a_meta_ok;
 assign f_bad_output=f_started&&f_out_valid&&(state!=F_OUTPUT||!f_meta_ok);
 assign a_bad_done=a_admitted&&!a_closed&&a_done_valid&&
  (a_done_error||!a_started||a_words_taken!=9'd256||a_done_words!=9'd256||
   a_done_generation!=generation_hold||a_done_partial);
 assign f_bad_done=f_frame_seen&&f_done_valid&&(f_done_error||!f_started||state!=F_DONE);
 assign fatal_child_now=a_frame_lost||f_frame_lost||a_bad_output||f_bad_output||a_bad_done||f_bad_done;
 assign in_ready=!child_reset&&state==INPUT&&input_index<10'd576&&!fatal_child_now&&
  (input_index<10'd448 ? (permit_a_feed&&a_in_ready) : 1'b1);
 assign input_fire=in_valid&&in_ready;
 assign a_job_valid=!child_reset&&state==A_ADMIT&&permit_a_job;
 assign a_in_valid=!child_reset&&state==INPUT&&input_index<10'd448&&permit_a_feed&&
  !fatal_child_now&&in_valid&&input_meta_ok;
 assign input_stored=!reset&&!abort&&frame_stored;
 assign start_ready=!child_reset&&state==STORED&&frame_stored&&a_input_stored&&!fatal_child_now;
 assign start_fire=start_valid&&start_ready;
 assign busy=!reset&&(frame_active||state==DONE);
 assign done_valid=!reset&&state==DONE;
 assign done_error=error_latched;assign done_saturated=saturation_latched;
 assign done_partial=error_latched&&output_count!=0;
 assign done_words=output_count;assign done_generation=generation_hold;
 assign a_start_valid=!child_reset&&state==A_START&&permit_a_start&&!fatal_child_now;

 // Capture into F once without consuming A_T. For hidden words0..127, the
 // unchanged F reopens in_ready only after that word's S ACK retires. Pending
 // plus reopened ready permits the later source take; no extra Y holding.
 assign f_in_valid=!child_reset&&!fatal_child_now&&permit_f_feed&&
  ((state==F_HIDDEN&&!f_y_pending&&permit_a_take&&a_out_valid&&a_meta_ok)||state==F_GAMMA);
 assign f_in_data=state==F_HIDDEN ? a_out_data : gamma_bank[gamma_index];
 assign f_hidden_capture=state==F_HIDDEN&&f_in_valid&&f_in_ready;
 assign a_out_ready=!child_reset&&!fatal_child_now&&state==F_HIDDEN&&
  f_y_pending&&permit_a_take&&a_meta_ok&&f_in_ready;
 assign a_transfer=a_out_valid&&a_out_ready;
 assign f_start_valid=!child_reset&&!fatal_child_now&&state==F_START&&
  permit_f_start&&f_input_stored&&f_job_mirror!=16'hffff;
 assign f_start_fire=f_start_valid&&f_start_ready;

 // A may close while F is filling/running row1. It cannot close after row0:
 // A_T must retain word128 through the entire first F execution and release.
 assign a_done_ready=!child_reset&&!fatal_child_now&&a_started&&!a_closed&&
  a_words_taken==9'd256&&a_done_words==9'd256&&a_done_generation==generation_hold&&
  !a_done_error&&!a_done_partial&&permit_a_done;
 assign a_close_fire=a_done_valid&&a_done_ready;
 assign f_done_ready=!child_reset&&!fatal_child_now&&state==F_DONE&&
  f_started&&!f_done_error&&permit_f_done;
 assign a_sat_observed=state!=DONE&&a_started&&!a_closed&&a_done_saturated;
 assign f_sat_observed=state!=DONE&&f_started&&f_done_saturated;

 assign out_valid=!child_reset&&!fatal_child_now&&state==F_OUTPUT&&f_started&&f_out_valid&&f_meta_ok;
 assign f_out_ready=!child_reset&&!fatal_child_now&&state==F_OUTPUT&&f_started&&f_meta_ok&&out_ready;
 assign out_data=f_out_data;
 assign out_index={2'd0,row_index,7'd0}+f_out_index;
 assign out_last=out_valid&&row_index&&f_out_last;
 assign out_generation=generation_hold;

 // The two independent providers retain their child ABI and policies:
 // A strictly rejects accepted bad tags; baseline F may drain older tags.
 assign a_provider_active=!child_reset&&!fatal_child_now&&state!=DONE&&a_started&&!a_closed;
 assign f_provider_active=!child_reset&&!fatal_child_now&&state!=DONE&&f_started;
 assign a_wreq_valid=a_provider_active&&a_child_wreq_valid;
 assign a_w_ready=a_provider_active&&a_child_w_ready;
 assign f_wreq_valid=f_provider_active&&f_child_wreq_valid;
 assign f_w_ready=f_provider_active&&f_child_w_ready;
 assign f_wreq_row=row_index;

 block_w4_afull_top u_a(
  .clk(clk),.reset(child_reset),.abort(1'b0),
  .job_valid(a_job_valid),.job_ready(a_job_ready),.job_generation(generation_hold),.weights_version(a_version_hold),
  .in_valid(a_in_valid),.in_ready(a_in_ready),.in_data(in_data),.in_generation(generation_hold),
  .in_index(input_index[8:0]),.in_last(input_index==10'd447),
  .input_stored(a_input_stored),.start_valid(a_start_valid),.start_ready(a_start_ready),.busy(a_busy),
  .done_valid(a_done_valid),.done_ready(a_done_ready),.done_error(a_done_error),.done_saturated(a_done_saturated),
  .done_partial(a_done_partial),.done_words(a_done_words),.done_generation(a_done_generation),
  .out_valid(a_out_valid),.out_ready(a_out_ready),.out_data(a_out_data),.out_index(a_out_index),
  .out_last(a_out_last),.out_generation(a_out_generation),
  .wreq_valid(a_child_wreq_valid),.wreq_ready(a_wreq_ready&&a_provider_active),
  .wreq_job(a_wreq_job),.wreq_seq(a_wreq_seq),.wreq_version(a_wreq_version),.wreq_matrix(a_wreq_matrix),
  .wreq_head(a_wreq_head),.wreq_group(a_wreq_group),.wreq_chunk(a_wreq_chunk),
  .w_valid(a_w_valid&&a_provider_active),.w_ready(a_child_w_ready),.w_job(a_w_job),.w_seq(a_w_seq),
  .w_version(a_w_version),.w_index(a_w_index),.w_last(a_w_last),.w_error(a_w_error),.w_data(a_w_data));
 block_w4_f1024_top u_f(
  .clk(clk),.reset(child_reset),.abort(1'b0),
  .in_valid(f_in_valid),.in_ready(f_in_ready),.in_data(f_in_data),
  .input_stored(f_input_stored),.start_valid(f_start_valid),.start_ready(f_start_ready),.busy(f_busy),
  .done_valid(f_done_valid),.done_ready(f_done_ready),.done_error(f_done_error),.done_saturated(f_done_saturated),
  .out_valid(f_out_valid),.out_ready(f_out_ready),.out_data(f_out_data),.out_index(f_out_index),.out_last(f_out_last),
  .weights_version(f_version_hold),.wreq_valid(f_child_wreq_valid),.wreq_ready(f_wreq_ready&&f_provider_active),
  .wreq_job(f_wreq_job),.wreq_seq(f_wreq_seq),.wreq_version(f_wreq_version),.wreq_matrix(f_wreq_matrix),
  .wreq_group(f_wreq_group),.wreq_chunk(f_wreq_chunk),
  .w_valid(f_w_valid&&f_provider_active),.w_ready(f_child_w_ready),.w_job(f_w_job),.w_seq(f_w_seq),
  .w_version(f_w_version),.w_index(f_w_index),.w_last(f_w_last),.w_error(f_w_error),.w_data(f_w_data));

 // Public child start handshakes mirror F's finite ID capacity. No private
 // counter is read. A normal parent completion does not reset this mirror.
 always @(posedge clk)begin
  if(child_reset)f_job_mirror<=0;
  else if(f_start_fire)f_job_mirror<=f_job_mirror+16'd1;
 end
 task automatic empty_job;
  begin
   state<=WAIT_JOB;input_index<=0;hidden_index<=0;gamma_index<=0;row_index<=0;
   frame_active<=0;frame_stored<=0;a_admitted<=0;a_started<=0;a_closed<=0;
   f_frame_seen<=0;f_started<=0;f_y_pending<=0;error_latched<=0;saturation_latched<=0;
   generation_hold<=0;a_version_hold<=0;f_version_hold<=0;
   a_words_taken<=0;f_out_count<=0;output_count<=0;
  end
 endtask
 task automatic fail_job;
  begin state<=DONE;frame_stored<=0;f_y_pending<=0;error_latched<=1;internal_reset<=1;end
 endtask
 always @(posedge clk)begin
  if(reset)begin
   empty_job();internal_reset<=0;
   // Validity, not old FF contents, gates reuse. Every admitted frame must
   // write all128 gamma words before any of them is replayed into a child.
  end else begin
   internal_reset<=0;
   if(state!=DONE)saturation_latched<=saturation_latched||a_sat_observed||f_sat_observed;
   if(abort)begin
    if(state==DONE)begin if(done_ready)empty_job();end
    else if(frame_active)fail_job();
    else begin empty_job();internal_reset<=1;end
   end else if(frame_active&&state!=DONE&&fatal_child_now)fail_job();
   else begin
    if(a_close_fire)a_closed<=1;
    case(state)
     WAIT_JOB:if(job_valid&&job_ready)begin
      frame_active<=1;generation_hold<=job_generation;
      a_version_hold<=weights_a_version;f_version_hold<=weights_f_version;
      // F version0 cannot start; reserve two nonwrapping F IDs up front.
      if(weights_f_version==16'd0||f_job_mirror>16'hfffd)fail_job();
      else state<=A_ADMIT;
     end
     A_ADMIT:if(a_job_valid&&a_job_ready)begin a_admitted<=1;state<=INPUT;end
     INPUT:begin
      if(input_fire)begin
       if(!input_meta_ok)fail_job();
       else begin
        if(input_index>=10'd448)gamma_bank[input_index-10'd448]<=in_data;
        input_index<=input_index+1'b1;
       end
      end
      if(input_index==10'd576&&a_input_stored)begin frame_stored<=1;state<=STORED;end
     end
     STORED:if(start_fire)begin row_index<=0;hidden_index<=0;gamma_index<=0;state<=A_START;end
     A_START:if(a_start_valid&&a_start_ready)begin a_started<=1;state<=F_HIDDEN;end
     F_HIDDEN:begin
      if(f_hidden_capture)begin f_y_pending<=1;f_frame_seen<=1;end
      if(a_transfer)begin
       f_y_pending<=0;a_words_taken<=a_words_taken+1'b1;
       if(hidden_index==7'd127)begin gamma_index<=0;state<=F_GAMMA;end
       else hidden_index<=hidden_index+1'b1;
      end
     end
     F_GAMMA:if(f_in_valid&&f_in_ready)begin
      f_frame_seen<=1;
      if(gamma_index==7'd127)state<=F_STORED;
      else gamma_index<=gamma_index+1'b1;
     end
     F_STORED:if(f_input_stored)state<=F_START;
     F_START:if(f_job_mirror==16'hffff)fail_job();
      else if(f_start_fire)begin f_started<=1;f_out_count<=0;state<=F_OUTPUT;end
     F_OUTPUT:if(out_valid&&out_ready)begin
      output_count<=output_count+1'b1;f_out_count<=f_out_count+1'b1;
      if(f_out_count==8'd127)state<=F_DONE;
     end
     F_DONE:if(f_done_valid&&f_done_ready)begin
      f_started<=0;f_frame_seen<=0;
      if(!row_index)begin row_index<=1;hidden_index<=0;gamma_index<=0;f_out_count<=0;f_y_pending<=0;state<=F_HIDDEN;end
      else if(a_closed||a_close_fire)state<=DONE;
      else state<=WAIT_A_DONE;
     end
     WAIT_A_DONE:if(a_closed||a_close_fire)state<=DONE;
     DONE:if(done_valid&&done_ready)empty_job();
     default:begin if(frame_active)fail_job();else begin empty_job();internal_reset<=1;end end
    endcase
   end
  end
 end
endmodule
