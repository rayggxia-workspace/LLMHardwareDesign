// H2 G1 typed service executor. Unchanged A/F kernels, one real edge DMA.
// No tensor arrays, arithmetic substitute, generic MEM, or warm-reset isolation.
module block_w5_af_executor(
 input wire clk,reset,abort,job_begin,
 input wire svc_valid,output wire svc_ready,input wire [127:0] svc_record,
 input wire [9:0] svc_a_base,svc_b_base,
 output wire svc_done_valid,input wire svc_done_ready,output wire svc_done_error,
 input wire [31:0] job_generation,input wire [15:0] weights_a_version,weights_f_version,
 input wire parent_start_valid,output wire parent_start_ready,output wire input_stored,
 input wire in_valid,output wire in_ready,input wire [127:0] in_data,
 input wire [9:0] in_index,input wire in_last,input wire [31:0] in_generation,
 output wire out_valid,output wire [127:0] out_data,output wire [9:0] out_index,
 output wire out_last,output wire [31:0] out_generation,
 input wire out_ack_valid,output wire out_ack_ready,input wire [9:0] out_ack_index,
 input wire [31:0] out_ack_generation,
 output wire param_req_valid,input wire param_req_ready,output wire [15:0] param_req_id,
 output wire [1:0] param_req_island,output wire param_req_row,
 output wire [8:0] param_req_words,
 input wire param_valid,output wire param_ready,input wire [127:0] param_data,
 input wire [8:0] param_index,input wire param_last,param_error,
 output wire a_wreq_valid,input wire a_wreq_ready,output wire [31:0] a_wreq_job,
 output wire [15:0] a_wreq_seq,a_wreq_version,output wire [1:0] a_wreq_matrix,
 output wire [3:0] a_wreq_head,output wire [6:0] a_wreq_group,output wire [5:0] a_wreq_chunk,
 input wire a_w_valid,output wire a_w_ready,input wire [31:0] a_w_job,
 input wire [15:0] a_w_seq,a_w_version,input wire [3:0] a_w_index,
 input wire a_w_last,a_w_error,input wire [127:0] a_w_data,
 output wire f_wreq_valid,input wire f_wreq_ready,
 output wire [15:0] f_wreq_job,f_wreq_seq,f_wreq_version,output wire [1:0] f_wreq_matrix,
 output wire [8:0] f_wreq_group,output wire [6:0] f_wreq_chunk,output wire f_wreq_row,
 input wire f_w_valid,output wire f_w_ready,input wire [15:0] f_w_job,f_w_seq,f_w_version,
 input wire [4:0] f_w_index,input wire f_w_last,f_w_error,input wire [127:0] f_w_data,
 output wire busy,child_reset,done_saturated,done_partial,output wire [8:0] done_words
);
 localparam [7:0] OP_IMPORT=2,OP_WAIT_STORED=3,OP_ARM=4,OP_START=5,
  OP_LOAD=6,OP_WAIT_INPUT=7,OP_PARAM=8,OP_WAIT_PARAM=9,OP_WAIT_SEALED=10,
  OP_STORE=11,OP_CLOSE=12,OP_WAIT_RELEASE=13,OP_WAIT_DONE=14,
  OP_EXPORT=19,OP_WAIT_HOST_STORED=20,OP_CLOSE_OUTPUT=21;
 localparam [4:0] IDLE=0,RESP=1,ARM_A=2,DMA_CMD=3,DMA_WAIT=4,
  HIDDEN_ACK=5,PARAM_REQ=6,PARAM_FEED=7,FRAME_ACK=8,
  NATIVE_START=9,SEALED_WAIT=10,RELEASE_WAIT=11,NATIVE_DONE=12;
 localparam [2:0] X_NONE=0,X_IMPORT=1,X_LOAD=2,X_STORE=3,X_EXPORT=4;
 reg [4:0] state;
 reg [2:0] transfer;
 reg [1:0] island;
 reg row_hold,armed,started,frame_seen,hidden_pending,hidden_stored,frame_stored;
 reg result_sealed,result_stored,closed,release_seen;
 reg import_stored,parent_started,export_stored,export_closed;
 reg response_error,poison,internal_reset,saturation_latched;
 reg [31:0] generation_hold,context_hold;
 reg [15:0] parameter_hold,a_version_hold,f_version_hold,f_job_mirror;
 reg [9:0] dma_base_hold,dma_words_hold,hidden_count,native_out_count,import_count;
 reg [8:0] parameter_count,host_words;
 wire [7:0] opcode=svc_record[7:0];
 wire [15:0] field_a=svc_record[31:16],field_b=svc_record[47:32],field_c=svc_record[63:48];
 wire [31:0] immediate=svc_record[95:64];
 wire [15:0] auxiliary=svc_record[127:112];
 wire permit_dma_cmd=1'b1,permit_host=1'b1,permit_hidden=1'b1;
 wire permit_param_req=1'b1,permit_param=1'b1,permit_native_start=1'b1;
 wire permit_native_take=1'b1,permit_child_done=1'b1,permit_parent_start=1'b1;
 wire d_cmd_valid,d_cmd_ready,d_in_valid,d_in_ready,d_out_valid,d_out_ready;
 wire d_done_valid,d_done_ready,d_done_error,d_busy,d_in_last,d_out_last;
 wire [127:0] d_in_data,d_out_data;
 wire [9:0] d_in_index,d_out_index,d_done_words;
 wire a_job_valid,a_job_ready,a_in_valid,a_in_ready,a_input_stored,a_start_valid,a_start_ready,a_busy;
 wire a_done_valid,a_done_ready,a_done_error,a_done_saturated,a_done_partial;
 wire [8:0] a_done_words;
 wire [31:0] a_done_generation,a_out_generation;
 wire a_out_valid,a_out_ready,a_out_last;
 wire [127:0] a_out_data,a_in_data;
 wire [8:0] a_in_index;
 wire a_in_last;
 wire f_in_valid,f_in_ready,f_input_stored,f_start_valid,f_start_ready,f_busy;
 wire f_done_valid,f_done_ready,f_done_error,f_done_saturated,f_out_valid,f_out_ready,f_out_last;
 wire [127:0] f_in_data,f_out_data;
 wire [9:0] a_out_index,f_out_index;
 wire a_child_wreq_valid,a_child_w_ready,f_child_wreq_valid,f_child_w_ready;
 wire a_provider_active,f_provider_active,native_ready,native_stored,native_done;
 wire native_valid,native_last,native_meta_ok,hidden_meta_ok,import_meta_ok,param_meta_ok,ack_meta_ok;
 wire [127:0] native_data;
 wire [9:0] native_index,hidden_words,output_words;
 wire a_frame_lost,f_frame_lost,bad_a_done,bad_f_done,fatal_now;
 wire hidden_capture,hidden_fire,param_fire,native_take,f_start_fire,host_ack_fire;
 wire svc_fire=svc_valid&&svc_ready;

 assign child_reset=reset||abort||internal_reset;
 assign svc_ready=!reset&&!abort&&state==IDLE;
 assign svc_done_valid=!reset&&state==RESP;
 assign svc_done_error=response_error;
 assign input_stored=!child_reset&&!poison&&import_stored;
 assign parent_start_ready=!child_reset&&!poison&&import_stored&&!parent_started&&permit_parent_start;
 assign busy=!reset&&(state!=IDLE||transfer!=X_NONE||armed||import_stored||parent_started);
 assign done_saturated=saturation_latched;
 assign done_words=host_words;
 assign done_partial=poison&&host_words!=0;
 assign hidden_words=island==1 ? 10'd256 : 10'd128;
 assign output_words=hidden_words;
 assign native_ready=island==1 ? a_in_ready : f_in_ready;
 assign native_stored=island==1 ? a_input_stored : f_input_stored;
 assign native_done=island==1 ? a_done_valid : f_done_valid;
 assign native_valid=island==1 ? a_out_valid : f_out_valid;
 assign native_data=island==1 ? a_out_data : f_out_data;
 assign native_index=island==1 ? a_out_index : f_out_index;
 assign native_last=island==1 ? a_out_last : f_out_last;
 assign native_meta_ok=native_out_count<output_words&&native_index==native_out_count&&
  native_last==(native_out_count+10'd1==output_words)&&
  (island!=1||a_out_generation==generation_hold);
 assign hidden_meta_ok=d_out_index==hidden_count&&hidden_count<hidden_words&&
  d_out_last==(hidden_count+10'd1==hidden_words);
 assign import_meta_ok=in_generation==generation_hold&&in_index==import_count&&
  import_count<10'd256&&in_last==(import_count==10'd255);
 assign param_meta_ok=param_index==parameter_count&&parameter_count<param_req_words&&
  param_last==(parameter_count+9'd1==param_req_words)&&!param_error;
 assign ack_meta_ok=out_ack_generation==generation_hold&&out_ack_index==d_out_index;
 assign a_frame_lost=armed&&island==1&&!a_busy&&!a_input_stored&&!a_done_valid;
 assign f_frame_lost=armed&&island==2&&frame_seen&&!f_busy&&!f_input_stored&&!f_done_valid;
 assign bad_a_done=armed&&island==1&&a_done_valid&&
  (a_done_error||!started||native_out_count!=10'd256||a_done_words!=9'd256||
   a_done_generation!=generation_hold||a_done_partial);
 assign bad_f_done=armed&&island==2&&f_done_valid&&
  (f_done_error||!started||native_out_count!=10'd128);
 // Errors are detected at interfaces with real error pins. Native S has none.
 assign fatal_now=!poison&&!child_reset&&
  (a_frame_lost||f_frame_lost||bad_a_done||bad_f_done||
   (transfer!=X_NONE&&d_done_valid&&d_done_error)||
   (transfer==X_IMPORT&&in_valid&&!import_meta_ok)||
   (transfer==X_LOAD&&d_out_valid&&!hidden_meta_ok)||
   (transfer==X_STORE&&native_valid&&!native_meta_ok)||
   (state==PARAM_FEED&&param_valid&&!param_meta_ok)||
   (transfer==X_EXPORT&&d_out_valid&&out_ack_valid&&!ack_meta_ok));

 assign d_cmd_valid=!child_reset&&!poison&&!fatal_now&&state==DMA_CMD&&permit_dma_cmd;
 assign d_in_valid=!child_reset&&!poison&&!fatal_now&&
  (transfer==X_IMPORT ? in_valid&&import_meta_ok&&permit_host :
   transfer==X_STORE ? native_valid&&native_meta_ok&&permit_native_take : 1'b0);
 assign d_in_data=transfer==X_IMPORT ? in_data : native_data;
 assign d_in_index=transfer==X_IMPORT ? in_index : native_index;
 assign d_in_last=transfer==X_IMPORT ? in_last : native_last;
 assign in_ready=!child_reset&&!poison&&!fatal_now&&transfer==X_IMPORT&&permit_host&&d_in_ready;
 assign a_out_ready=!child_reset&&!poison&&!fatal_now&&transfer==X_STORE&&island==1&&
  permit_native_take&&native_meta_ok&&d_in_ready;
 assign f_out_ready=!child_reset&&!poison&&!fatal_now&&transfer==X_STORE&&island==2&&
  permit_native_take&&native_meta_ok&&d_in_ready;
 assign native_take=native_valid&&(island==1 ? a_out_ready : f_out_ready);
 assign d_out_ready=!child_reset&&!poison&&!fatal_now&&
  (transfer==X_LOAD ? hidden_pending&&native_ready&&permit_hidden&&hidden_meta_ok :
   transfer==X_EXPORT ? out_ack_valid&&ack_meta_ok&&permit_host : 1'b0);
 assign hidden_capture=transfer==X_LOAD&&d_out_valid&&!hidden_pending&&
  native_ready&&permit_hidden&&hidden_meta_ok&&!child_reset&&!poison&&!fatal_now;
 assign hidden_fire=transfer==X_LOAD&&d_out_valid&&d_out_ready;
 assign out_valid=!child_reset&&!poison&&!fatal_now&&transfer==X_EXPORT&&permit_host&&d_out_valid;
 assign out_data=d_out_data;assign out_index=d_out_index;
 assign out_last=out_valid&&d_out_last;assign out_generation=generation_hold;
 assign out_ack_ready=!child_reset&&!poison&&transfer==X_EXPORT&&permit_host&&d_out_valid;
 assign host_ack_fire=out_ack_valid&&out_ack_ready&&ack_meta_ok;
 assign d_done_ready=!child_reset&&!poison&&!fatal_now&&d_done_valid&&
  ((state==HIDDEN_ACK&&hidden_count==hidden_words&&native_ready)||
   (state==DMA_WAIT&&context_hold==32'd1)||
   (state==DMA_WAIT&&context_hold==32'd2));

 block_w5_edge_dma u_edge(
  .clk(clk),.reset(child_reset),.abort(1'b0),
  .cmd_valid(d_cmd_valid),.cmd_ready(d_cmd_ready),
  .cmd_write(transfer==X_IMPORT||transfer==X_STORE),.cmd_base(dma_base_hold),.cmd_words(dma_words_hold),
  .in_valid(d_in_valid),.in_ready(d_in_ready),.in_data(d_in_data),.in_index(d_in_index),.in_last(d_in_last),
  .out_valid(d_out_valid),.out_ready(d_out_ready),.out_data(d_out_data),.out_index(d_out_index),.out_last(d_out_last),
  .done_valid(d_done_valid),.done_ready(d_done_ready),.done_error(d_done_error),.done_words(d_done_words),.busy(d_busy));

 assign a_job_valid=!child_reset&&!poison&&!fatal_now&&state==ARM_A;
 assign param_req_valid=!child_reset&&!poison&&!fatal_now&&state==PARAM_REQ&&permit_param_req;
 assign param_req_id=parameter_hold;assign param_req_island=island;
 assign param_req_row=row_hold;assign param_req_words=island==1 ? 9'd192 : 9'd128;
 assign param_ready=!child_reset&&!poison&&!fatal_now&&state==PARAM_FEED&&permit_param&&native_ready;
 assign param_fire=param_valid&&param_ready;
 assign a_in_valid=!child_reset&&!poison&&!fatal_now&&island==1&&
  ((transfer==X_LOAD&&d_out_valid&&!hidden_pending&&permit_hidden&&hidden_meta_ok)||
   (state==PARAM_FEED&&param_valid&&permit_param&&param_meta_ok));
 assign f_in_valid=!child_reset&&!poison&&!fatal_now&&island==2&&
  ((transfer==X_LOAD&&d_out_valid&&!hidden_pending&&permit_hidden&&hidden_meta_ok)||
   (state==PARAM_FEED&&param_valid&&permit_param&&param_meta_ok));
 assign a_in_data=state==PARAM_FEED ? param_data : d_out_data;
 assign f_in_data=a_in_data;
 assign a_in_index=state==PARAM_FEED ? 9'd256+parameter_count : hidden_count[8:0];
 assign a_in_last=state==PARAM_FEED&&parameter_count==9'd191;
 assign a_start_valid=!child_reset&&!poison&&!fatal_now&&state==NATIVE_START&&island==1&&
  a_input_stored&&permit_native_start;
 assign f_start_valid=!child_reset&&!poison&&!fatal_now&&state==NATIVE_START&&island==2&&
  f_input_stored&&f_job_mirror!=16'hffff&&permit_native_start;
 assign f_start_fire=f_start_valid&&f_start_ready;
 assign a_done_ready=!child_reset&&!poison&&!fatal_now&&state==NATIVE_DONE&&island==1&&
  release_seen&&permit_child_done;
 assign f_done_ready=!child_reset&&!poison&&!fatal_now&&state==NATIVE_DONE&&island==2&&
  release_seen&&permit_child_done;
 assign a_provider_active=!child_reset&&!poison&&!fatal_now&&armed&&island==1&&started;
 assign f_provider_active=!child_reset&&!poison&&!fatal_now&&armed&&island==2&&started;
 assign a_wreq_valid=a_provider_active&&a_child_wreq_valid;
 assign a_w_ready=a_provider_active&&a_child_w_ready;
 assign f_wreq_valid=f_provider_active&&f_child_wreq_valid;
 assign f_w_ready=f_provider_active&&f_child_w_ready;
 assign f_wreq_row=row_hold;
 block_w4_afull_top u_a(
  .clk(clk),.reset(child_reset),.abort(1'b0),.job_valid(a_job_valid),.job_ready(a_job_ready),
  .job_generation(generation_hold),.weights_version(a_version_hold),
  .in_valid(a_in_valid),.in_ready(a_in_ready),.in_data(a_in_data),.in_generation(generation_hold),
  .in_index(a_in_index),.in_last(a_in_last),.input_stored(a_input_stored),
  .start_valid(a_start_valid),.start_ready(a_start_ready),.busy(a_busy),
  .done_valid(a_done_valid),.done_ready(a_done_ready),.done_error(a_done_error),
  .done_saturated(a_done_saturated),.done_partial(a_done_partial),.done_words(a_done_words),
  .done_generation(a_done_generation),.out_valid(a_out_valid),.out_ready(a_out_ready),
  .out_data(a_out_data),.out_index(a_out_index),.out_last(a_out_last),.out_generation(a_out_generation),
  .wreq_valid(a_child_wreq_valid),.wreq_ready(a_wreq_ready&&a_provider_active),
  .wreq_job(a_wreq_job),.wreq_seq(a_wreq_seq),.wreq_version(a_wreq_version),.wreq_matrix(a_wreq_matrix),
  .wreq_head(a_wreq_head),.wreq_group(a_wreq_group),.wreq_chunk(a_wreq_chunk),
  .w_valid(a_w_valid&&a_provider_active),.w_ready(a_child_w_ready),.w_job(a_w_job),.w_seq(a_w_seq),
  .w_version(a_w_version),.w_index(a_w_index),.w_last(a_w_last),.w_error(a_w_error),.w_data(a_w_data));
 block_w4_f1024_top u_f(
  .clk(clk),.reset(child_reset),.abort(1'b0),
  .in_valid(f_in_valid),.in_ready(f_in_ready),.in_data(f_in_data),.input_stored(f_input_stored),
  .start_valid(f_start_valid),.start_ready(f_start_ready),.busy(f_busy),
  .done_valid(f_done_valid),.done_ready(f_done_ready),.done_error(f_done_error),.done_saturated(f_done_saturated),
  .out_valid(f_out_valid),.out_ready(f_out_ready),.out_data(f_out_data),.out_index(f_out_index),.out_last(f_out_last),
  .weights_version(f_version_hold),.wreq_valid(f_child_wreq_valid),.wreq_ready(f_wreq_ready&&f_provider_active),
  .wreq_job(f_wreq_job),.wreq_seq(f_wreq_seq),.wreq_version(f_wreq_version),.wreq_matrix(f_wreq_matrix),
  .wreq_group(f_wreq_group),.wreq_chunk(f_wreq_chunk),
  .w_valid(f_w_valid&&f_provider_active),.w_ready(f_child_w_ready),.w_job(f_w_job),.w_seq(f_w_seq),
  .w_version(f_w_version),.w_index(f_w_index),.w_last(f_w_last),.w_error(f_w_error),.w_data(f_w_data));

 always @(posedge clk)begin
  if(child_reset)f_job_mirror<=0;
  else if(f_start_fire)f_job_mirror<=f_job_mirror+16'd1;
 end
 task automatic respond;
  begin state<=RESP;response_error<=0;end
 endtask
 task automatic fail_service;
  begin
   poison<=1;internal_reset<=1;transfer<=X_NONE;armed<=0;started<=0;frame_seen<=0;hidden_pending<=0;
   // An already offered response remains stable; the next service reports poison.
   if(state!=RESP)begin state<=RESP;response_error<=1;end
  end
 endtask
 task automatic clear_job;
  begin
   transfer<=X_NONE;island<=0;row_hold<=0;armed<=0;started<=0;frame_seen<=0;hidden_pending<=0;
   hidden_stored<=0;frame_stored<=0;result_sealed<=0;result_stored<=0;closed<=0;release_seen<=0;
   import_stored<=0;parent_started<=0;export_stored<=0;export_closed<=0;
   response_error<=0;poison<=0;saturation_latched<=0;generation_hold<=0;context_hold<=0;
   parameter_hold<=0;a_version_hold<=0;f_version_hold<=0;dma_base_hold<=0;dma_words_hold<=0;
   hidden_count<=0;native_out_count<=0;import_count<=0;parameter_count<=0;host_words<=0;
  end
 endtask
 always @(posedge clk)begin
  if(reset)begin state<=IDLE;internal_reset<=0;clear_job();end
  else begin
   internal_reset<=0;
   if(abort)begin
    poison<=1;transfer<=X_NONE;armed<=0;started<=0;frame_seen<=0;hidden_pending<=0;
    if(state!=IDLE&&state!=RESP)begin state<=RESP;response_error<=1;end
   end else if(job_begin)begin
    // Top admits a new outer obligation only after the prior cohort has closed.
    state<=IDLE;clear_job();
   end else if(fatal_now)fail_service();
   else begin
    if(parent_start_valid&&parent_start_ready)parent_started<=1;
    if(armed&&started&&!poison)begin
     if(island==1)saturation_latched<=saturation_latched||a_done_saturated;
     else saturation_latched<=saturation_latched||f_done_saturated;
    end
    if(transfer==X_IMPORT&&in_valid&&in_ready)import_count<=import_count+10'd1;
    // Child captures once. Its typed nonfinal hidden ingress reopens only
    // after the true native S ACK, which then retires this edge-read word.
    if(hidden_capture)begin hidden_pending<=1;frame_seen<=1;end
    if(hidden_fire)begin hidden_count<=hidden_count+10'd1;hidden_pending<=0;end
    if(native_take)native_out_count<=native_out_count+10'd1;
    if(host_ack_fire)host_words<=host_words+9'd1;
    case(state)
     IDLE:if(svc_fire)begin
      response_error<=0;
      if(poison)begin state<=RESP;response_error<=1;end
      else case(opcode)
       OP_IMPORT:begin
        if(armed||transfer!=X_NONE||import_stored||immediate!=32'd256)fail_service();
        else begin generation_hold<=job_generation;dma_base_hold<=svc_a_base;dma_words_hold<=10'd256;
         transfer<=X_IMPORT;import_count<=0;context_hold<=0;state<=DMA_CMD;end
       end
       OP_WAIT_STORED:begin
        if((transfer!=X_IMPORT&&transfer!=X_STORE)||!d_done_valid)fail_service();
        else begin context_hold<=32'd1;state<=DMA_WAIT;end
       end
       OP_ARM:begin
        if(!parent_started||armed||transfer!=X_NONE||
           (field_a!=16'd1&&field_a!=16'd2)||field_c>16'd1||
           (field_a==16'd1&&field_c!=0)||weights_f_version==0||
           (field_a==16'd1&&f_job_mirror>16'hfffd)||
           (field_a==16'd2&&((field_c==0&&f_job_mirror>16'hfffd)||f_job_mirror==16'hffff)))fail_service();
        else begin
         island<=field_a[1:0];row_hold<=field_c[0];context_hold<=immediate;parameter_hold<=auxiliary;
         a_version_hold<=weights_a_version;f_version_hold<=weights_f_version;
         hidden_count<=0;parameter_count<=0;native_out_count<=0;frame_seen<=0;hidden_pending<=0;started<=0;
         hidden_stored<=0;frame_stored<=0;result_sealed<=0;result_stored<=0;closed<=0;release_seen<=0;
         if(field_a==1)state<=ARM_A;else begin armed<=1;respond();end
        end
       end
       OP_LOAD:begin
        if(!armed||started||hidden_stored||transfer!=X_NONE||field_b!=island||field_c!={15'd0,row_hold}||
           immediate!={22'd0,hidden_words})fail_service();
        else begin dma_base_hold<=svc_a_base+(island==2&&row_hold ? 10'd128 : 10'd0);
         dma_words_hold<=hidden_words;transfer<=X_LOAD;context_hold<=0;state<=DMA_CMD;end
       end
       OP_WAIT_INPUT:begin
        if(!armed||transfer!=X_LOAD||!d_done_valid||field_b!=island||field_c!={15'd0,row_hold})fail_service();
        else state<=HIDDEN_ACK;
       end
       OP_PARAM:begin
        if(!armed||!hidden_stored||frame_stored||field_a!=parameter_hold||field_b!=island||
           field_c!={15'd0,row_hold}||immediate!={23'd0,param_req_words})fail_service();
        else begin parameter_count<=0;state<=PARAM_REQ;end
       end
       OP_WAIT_PARAM:begin
        if(!armed||field_a!=island||parameter_count!=param_req_words)fail_service();
        else state<=FRAME_ACK;
       end
       OP_START:begin
        if(!armed||started||!frame_stored||!native_stored||field_a!=island||
           (island==2&&f_job_mirror==16'hffff))fail_service();
        else state<=NATIVE_START;
       end
       OP_WAIT_SEALED:begin
        if(!armed||!started||field_a!=island)fail_service();else state<=SEALED_WAIT;
       end
       OP_STORE:begin
        if(!armed||!started||!result_sealed||result_stored||transfer!=X_NONE||field_a!=island||
           field_c!={15'd0,row_hold}||immediate!={22'd0,output_words})fail_service();
        else begin dma_base_hold<=svc_b_base+(island==2&&row_hold ? 10'd128 : 10'd0);
         dma_words_hold<=output_words;transfer<=X_STORE;context_hold<=0;state<=DMA_CMD;end
       end
       OP_CLOSE:begin
        if(!armed||!result_stored||transfer!=X_NONE||field_a!=island||closed)fail_service();
        else begin closed<=1;respond();end
       end
       OP_WAIT_RELEASE:begin
        if(!armed||!closed||field_a!=island)fail_service();else state<=RELEASE_WAIT;
       end
       OP_WAIT_DONE:begin
        if(!armed||!release_seen||field_a!=island)fail_service();else state<=NATIVE_DONE;
       end
       OP_EXPORT:begin
        if(armed||transfer!=X_NONE||export_stored||export_closed||immediate!=32'd256)fail_service();
        else begin dma_base_hold<=svc_a_base;dma_words_hold<=10'd256;transfer<=X_EXPORT;
         context_hold<=0;host_words<=0;state<=DMA_CMD;end
       end
       OP_WAIT_HOST_STORED:begin
        if(transfer!=X_EXPORT||!d_done_valid||host_words!=9'd256)fail_service();
        else begin context_hold<=32'd2;state<=DMA_WAIT;end
       end
       OP_CLOSE_OUTPUT:begin
        if(!export_stored||transfer!=X_NONE||export_closed)fail_service();
        else begin export_closed<=1;respond();end
       end
       default:fail_service();
      endcase
     end
     RESP:if(svc_done_valid&&svc_done_ready)state<=IDLE;
     ARM_A:if(a_job_valid&&a_job_ready)begin armed<=1;respond();end
     DMA_CMD:if(d_cmd_valid&&d_cmd_ready)state<=DMA_WAIT;
     DMA_WAIT:if(d_done_valid)begin
      if(d_done_error||d_done_words!=dma_words_hold)fail_service();
      else if(context_hold==32'd1)begin
       if(transfer==X_IMPORT)import_stored<=1;else result_stored<=1;
       transfer<=X_NONE;context_hold<=0;respond();
      end else if(context_hold==32'd2)begin export_stored<=1;transfer<=X_NONE;context_hold<=0;respond();end
      else respond();
     end
     HIDDEN_ACK:if(d_done_valid&&native_ready&&hidden_count==hidden_words)begin
      transfer<=X_NONE;hidden_stored<=1;respond();end
     PARAM_REQ:if(param_req_valid&&param_req_ready)state<=PARAM_FEED;
     PARAM_FEED:if(param_fire)begin
      parameter_count<=parameter_count+9'd1;
      if(parameter_count+9'd1==param_req_words)respond();
     end
     FRAME_ACK:if(native_stored)begin frame_stored<=1;respond();end
     NATIVE_START:if((island==1&&a_start_valid&&a_start_ready)||f_start_fire)begin started<=1;respond();end
     SEALED_WAIT:if(native_valid&&native_meta_ok)begin result_sealed<=1;respond();end
     RELEASE_WAIT:if(native_done)begin release_seen<=1;respond();end
     NATIVE_DONE:if(native_done&&permit_child_done)begin
      armed<=0;started<=0;frame_seen<=0;respond();end
     default:fail_service();
    endcase
   end
  end
 end
endmodule
