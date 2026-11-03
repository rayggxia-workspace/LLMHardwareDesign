// Issue151 W4 fixed A16 -> two F16 rows, parentcd8dfc9/native7078786.
// New L4 validation wrapper only; both original children remain unchanged.
// Explicit parameter/output FF holding. No L5 storedACK or generic island ABI.
module block_w4_af16_top(
 input wire clk,reset,abort,
 input wire in_valid,output wire in_ready,input wire [127:0] in_data,
 output wire input_stored,input wire start_valid,output wire start_ready,
 output wire busy,output wire done_valid,input wire done_ready,
 output wire done_error,done_saturated,
 output wire out_valid,input wire out_ready,
 output wire [127:0] out_data,output wire [9:0] out_index,output wire out_last
);
 localparam [3:0] INPUT=0,A_START=1,A_CAPTURE=2,A_DONE=3,
  F_FEED=4,F_STORED=5,F_START=6,F_OUTPUT=7,F_DONE=8,DONE=9;
 reg [3:0] state;
 reg [5:0] input_index;
 reg [4:0] f_feed_index;
 reg [1:0] a_capture_count;
 reg row_index,frame_active,frame_stored,running;
 reg error_latched,saturation_latched,internal_reset;
 reg a_frame_seen,f_frame_seen,a_started,f_started;
 reg [127:0] parameter_bank[0:12];
 reg [127:0] a_rows[0:1];
 // Fixed observation/stall points, not host configuration inputs.
 wire permit_a_start=1'b1,permit_capture=1'b1;
 wire permit_f_feed=1'b1,permit_f_start=1'b1;
 wire permit_a_done=1'b1,permit_f_done=1'b1;
 wire child_reset,input_fire,start_fire;
 wire a_in_valid,a_in_ready,a_input_stored,a_start_valid,a_start_ready,a_busy;
 wire a_done_valid,a_done_ready,a_done_error,a_done_saturated;
 wire a_out_valid,a_out_ready,a_out_last;
 wire [127:0] a_out_data;
 wire [9:0] a_out_index;
 wire f_in_valid,f_in_ready,f_input_stored,f_start_valid,f_start_ready,f_busy;
 wire f_done_valid,f_done_ready,f_done_error,f_done_saturated;
 wire f_out_valid,f_out_ready,f_out_last;
 wire [127:0] f_in_data,f_out_data;
 wire [9:0] f_out_index;
 wire a_frame_lost,f_frame_lost,a_meta_ok,f_meta_ok;
 wire a_sat_observed,f_sat_observed;

 assign child_reset=reset||abort||internal_reset;
 assign a_frame_lost=a_frame_seen&&!a_busy&&!a_input_stored;
 assign f_frame_lost=f_frame_seen&&!f_busy&&!f_input_stored;
 assign in_ready=!child_reset&&state==INPUT&&!frame_stored&&input_index<6'd40&&
  !a_frame_lost&&!a_done_valid&&(input_index<6'd27 ? a_in_ready : 1'b1);
 assign a_in_valid=!child_reset&&state==INPUT&&!frame_stored&&input_index<6'd27&&
  !a_frame_lost&&!a_done_valid&&in_valid;
 assign input_fire=in_valid&&in_ready;
 // The marker remains bound during RUN, after the child A frame is closed.
 assign input_stored=!reset&&!abort&&frame_stored&&
  (running||state==DONE||a_input_stored);
 assign start_ready=!child_reset&&state==INPUT&&frame_stored&&!running&&
  a_input_stored&&!a_frame_lost&&!a_done_valid;
 assign start_fire=start_valid&&start_ready;
 assign busy=!reset&&(frame_active||running||state==DONE);
 assign done_valid=!reset&&state==DONE;
 assign done_error=error_latched;
 assign done_saturated=saturation_latched;

 assign a_start_valid=!child_reset&&state==A_START&&permit_a_start&&!a_frame_lost&&!a_done_valid;
 assign a_meta_ok=a_capture_count<2&&a_out_index=={8'd0,a_capture_count}&&
  a_out_last==(a_capture_count==1);
 assign a_out_ready=!child_reset&&state==A_CAPTURE&&permit_capture&&a_meta_ok&&!a_done_valid;
 assign a_done_ready=!child_reset&&state==A_DONE&&permit_a_done&&!a_done_error;
 // Current-child ownership gates prevent stale flags from an old frame from
 // entering the aggregate, including while the next F frame is being filled.
 assign a_sat_observed=a_started&&(state==A_CAPTURE||state==A_DONE)&&a_done_saturated;
 assign f_sat_observed=f_started&&(state==F_OUTPUT||state==F_DONE)&&f_done_saturated;

 assign f_in_valid=!child_reset&&state==F_FEED&&permit_f_feed&&!f_frame_lost&&!f_done_valid;
 assign f_in_data=f_feed_index==0 ? a_rows[row_index] :
  f_feed_index<4 ? 128'd0 : f_feed_index<16 ? parameter_bank[f_feed_index-5'd4] : parameter_bank[12];
 assign f_start_valid=!child_reset&&state==F_START&&permit_f_start&&!f_frame_lost&&!f_done_valid;
 assign f_meta_ok=f_out_index==0&&f_out_last;
 // Invalid child metadata is never exposed as a host payload handshake.
 assign out_valid=!child_reset&&state==F_OUTPUT&&f_out_valid&&f_meta_ok&&!f_done_valid;
 assign f_out_ready=!child_reset&&state==F_OUTPUT&&out_ready&&f_meta_ok&&!f_done_valid;
 assign out_data=f_out_data;
 assign out_index={9'd0,row_index};
 assign out_last=out_valid&&row_index;
 assign f_done_ready=!child_reset&&state==F_DONE&&permit_f_done&&!f_done_error;

 block_w4_a16_top u_a(
  .clk(clk),.reset(child_reset),.abort(1'b0),
  .in_valid(a_in_valid),.in_ready(a_in_ready),.in_data(in_data),
  .input_stored(a_input_stored),.start_valid(a_start_valid),.start_ready(a_start_ready),
  .busy(a_busy),.done_valid(a_done_valid),.done_ready(a_done_ready),
  .done_error(a_done_error),.done_saturated(a_done_saturated),
  .out_valid(a_out_valid),.out_ready(a_out_ready),.out_data(a_out_data),.out_index(a_out_index),.out_last(a_out_last)
 );
 block_w4_f16_top u_f(
  .clk(clk),.reset(child_reset),.abort(1'b0),
  .in_valid(f_in_valid),.in_ready(f_in_ready),.in_data(f_in_data),
  .input_stored(f_input_stored),.start_valid(f_start_valid),.start_ready(f_start_ready),
  .busy(f_busy),.done_valid(f_done_valid),.done_ready(f_done_ready),
  .done_error(f_done_error),.done_saturated(f_done_saturated),
  .out_valid(f_out_valid),.out_ready(f_out_ready),.out_data(f_out_data),.out_index(f_out_index),.out_last(f_out_last)
 );

 task automatic empty_frame;
  begin
   state<=INPUT;input_index<=0;f_feed_index<=0;a_capture_count<=0;row_index<=0;
   frame_active<=0;frame_stored<=0;running<=0;
   error_latched<=0;saturation_latched<=0;
   a_frame_seen<=0;f_frame_seen<=0;a_started<=0;f_started<=0;
  end
 endtask
 task automatic fail_job;
  begin
   state<=DONE;frame_active<=0;frame_stored<=0;running<=0;
   error_latched<=1;internal_reset<=1;
  end
 endtask
 always @(posedge clk)begin
  if(reset)begin
   empty_frame();internal_reset<=0;
   for(integer k=0;k<13;k=k+1)parameter_bank[k]<=0;
   for(integer k=0;k<2;k=k+1)a_rows[k]<=0;
  end else begin
   internal_reset<=0;
   saturation_latched<=saturation_latched||a_sat_observed||f_sat_observed;
   if(abort)begin
    if(state==DONE)begin if(done_ready)empty_frame();end
    else if(running)fail_job();
    else begin empty_frame();internal_reset<=1;end
   end else case(state)
    INPUT:begin
     // A child ingress error has no child DONE. A remembered accepted beat
     // distinguishes actual frame loss from the initial empty child IDLE.
     if(a_frame_lost||a_done_valid)begin empty_frame();internal_reset<=1;end
     else begin
      if(input_fire)begin
       frame_active<=1;input_index<=input_index+1'b1;
       if(input_index<6'd27)a_frame_seen<=1;
       else parameter_bank[input_index-6'd27]<=in_data;
      end
      if(input_index==6'd40&&a_input_stored)frame_stored<=1;
      if(start_fire)begin
       running<=1;error_latched<=0;saturation_latched<=0;
       a_capture_count<=0;row_index<=0;f_feed_index<=0;
       a_started<=0;f_started<=0;f_frame_seen<=0;state<=A_START;
      end
     end
    end
    A_START:begin
     if(a_frame_lost||a_done_valid)fail_job();
     else if(a_start_valid&&a_start_ready)begin a_started<=1;state<=A_CAPTURE;end
    end
    A_CAPTURE:begin
     if(a_done_valid||(a_out_valid&&!a_meta_ok))fail_job();
     else if(a_out_valid&&a_out_ready)begin
      a_rows[a_capture_count[0]]<=a_out_data;a_capture_count<=a_capture_count+1'b1;
      if(a_capture_count==1)state<=A_DONE;
     end
    end
    A_DONE:begin
     if(a_out_valid||(a_done_valid&&a_done_error))fail_job();
     else if(a_done_valid&&a_done_ready)begin
      row_index<=0;f_feed_index<=0;f_frame_seen<=0;f_started<=0;state<=F_FEED;
     end
    end
    F_FEED:begin
     if(f_frame_lost||f_done_valid)fail_job();
     else if(f_in_valid&&f_in_ready)begin
      f_frame_seen<=1;
      if(f_feed_index==5'd16)state<=F_STORED;else f_feed_index<=f_feed_index+1'b1;
     end
    end
    F_STORED:begin
     if(f_frame_lost||f_done_valid)fail_job();
     else if(f_input_stored)state<=F_START;
    end
    F_START:begin
     if(f_frame_lost||f_done_valid)fail_job();
     else if(f_start_valid&&f_start_ready)begin f_started<=1;state<=F_OUTPUT;end
    end
    F_OUTPUT:begin
     if(f_done_valid||(f_out_valid&&!f_meta_ok))fail_job();
     else if(out_valid&&out_ready)state<=F_DONE;
    end
    F_DONE:begin
     if(f_out_valid||(f_done_valid&&f_done_error))fail_job();
     else if(f_done_valid&&f_done_ready)begin
      if(!row_index)begin
       row_index<=1;f_feed_index<=0;f_frame_seen<=0;f_started<=0;state<=F_FEED;
      end else begin state<=DONE;running<=0;error_latched<=0;end
     end
    end
    DONE:if(done_ready)empty_frame();
    default:if(running)fail_job();else begin empty_frame();internal_reset<=1;end
   endcase
  end
 end
endmodule
