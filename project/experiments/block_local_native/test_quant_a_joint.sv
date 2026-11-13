`timescale 1ns/1ps
// Original bank DELAY=3ns, deliberately 10ns functional clock: not STA.
module test_quant_a_joint;
 reg clk;initial clk=0;always #5 clk=!clk;
 reg reset=1,cmd_valid=0,cancel_valid=0,done_ready=0;
 wire cmd_ready;
 reg [127:0] cmd_key=128'h1250,cancel_key=0;
 reg [15:0] cmd_generation=1,cmd_kk=0;
 reg [9:0] cmd_source=32,cmd_destination=256;
 reg cmd_shift_known=0;
 reg [5:0] cmd_shift=0;
 wire s_valid,s_ready,s_write,rsp_valid,rsp_ready,done_valid,done_error,done_cancelled;
 wire [9:0] s_address;
 wire [127:0] s_data,rsp_data,done_key;
 wire [31:0] s_tag,rsp_tag,rejected_responses;
 wire [15:0] done_kk;
 wire [4:0] done_words;
 wire [15:0] done_written_mask;
 wire [5:0] done_shift;
 s32_a16_tile_quantizer quantizer(.*,.rsp_error(1'b0));
 reg dir_cfg_valid=0;
 wire dir_cfg_ready,dir_cfg_rejected,scale_valid,publish_ready,publish_rejected;
 wire [5:0] scale_shift;
 wire [31:0] rejected_publications;
 reg metadata_sent;
 wire publish_valid=done_valid && !metadata_sent;
 wire [1:0] aa_live_slots;
 a_scale_directory32 directory(.clk,.reset,.cfg_valid(dir_cfg_valid),.cfg_ready(dir_cfg_ready),
  .cfg_key(cmd_key),.cfg_first_kk(cmd_kk),.cfg_tiles(6'd1),.cfg_stride3(1'b0),.storage_released(1'b1),.leases_drained(aa_live_slots==0),
  .cfg_rejected(dir_cfg_rejected),.publish_valid,.publish_ready,.publish_key(done_key),.publish_kk(done_kk),
  .publish_shift(done_shift),.publish_written_mask(done_written_mask),.publish_error(done_error||done_cancelled),
  .publish_rejected,.lookup_key(cmd_key),.lookup_kk(cmd_kk),.lookup_valid(scale_valid),.lookup_shift(scale_shift),.rejected_publications);
 always @(posedge clk)begin
  if(reset)metadata_sent<=0;
  else begin
   if(cmd_valid && cmd_ready)metadata_sent<=0;
   if(publish_valid && publish_ready)metadata_sent<=1;
  end
 end
 reg aa_cmd_valid=0,aa_slot=0,aa_load_take=0,aa_w_valid=0,aa_use_valid=0,aa_take=0,aa_close_valid=0,aa_release_valid=0;
 reg [15:0] aa_sequence=1;
 wire aa_cmd_ready,aa_load_valid,aa_load_error,aa_load_slot,aa_w_ready,aa_use_ready,aa_valid,aa_close_ready,aa_release_ready;
 wire [127:0] aa_load_key,aa_key;
 wire [15:0] aa_load_gen,aa_gen,aa_kk,aa_use_sequence;
 wire [255:0] aa_data;
 wire [2:0] aa_step;
 wire [31:0] aa_record,aa_faults;
 wire [5:0] aa_shift;
 wire aa_s_valid,aa_s_ready,aa_rsp_valid,aa_rsp_ready,aa_quiescent,aa_reads_drained;
 wire [9:0] aa_s_address;
 wire [31:0] aa_s_tag;
 private_a_scaled_frontend front(.clk,.reset,.halt(1'b0),.flush(1'b0),
  .scale_valid,.scale_key(cmd_key),.scale_kk(cmd_kk),.scale_shift,
  .cmd_valid(aa_cmd_valid),.cmd_ready(aa_cmd_ready),.cmd_slot(aa_slot),.cmd_generation,
  .cmd_kk,.cmd_planned_uses(16'd2),.cmd_key,.cmd_S_base(10'd256),.cmd_copy_offset(10'd0),
  .copy_key(done_key),.copy_committed_prefix(done_written_mask==16'hffff ? 11'd16 : 11'd0),
  .load_done_valid(aa_load_valid),.load_done_ready(aa_load_take),.load_done_slot(aa_load_slot),
  .load_done_error(aa_load_error),.load_done_generation(aa_load_gen),.load_done_key(aa_load_key),
  .s_valid(aa_s_valid),.s_ready(aa_s_ready),.s_address(aa_s_address),.s_tag(aa_s_tag),
  .response_valid(aa_rsp_valid),.response_ready(aa_rsp_ready),.response_tag(tags_shared[63:32]),.response_data(data_shared),
  .w_valid(aa_w_valid),.w_ready(aa_w_ready),.w_slot(aa_slot),.w_generation(cmd_generation),.w_kk(cmd_kk),
  .w_use_sequence(aa_sequence),.w_key(cmd_key),.w_record(32'd1984),
  .use_valid(aa_use_valid),.use_ready(aa_use_ready),.use_slot(aa_slot),.use_generation(cmd_generation),
  .use_kk(cmd_kk),.use_sequence(aa_sequence),.use_key(cmd_key),
  .a_valid(aa_valid),.a_ready(aa_take),.a_data(aa_data),.a_step(aa_step),.a_weight_record(aa_record),
  .a_key(aa_key),.a_slot(aa_active_slot),.a_generation(aa_gen),.a_kk(aa_kk),.a_use_sequence(aa_use_sequence),.a_shift(aa_shift),
  .close_valid(aa_close_valid),.close_ready(aa_close_ready),.close_slot(aa_slot),.close_generation(cmd_generation),
  .release_valid(aa_release_valid),.release_ready(aa_release_ready),.release_slot(aa_slot),.release_generation(cmd_generation),
  .quiescent(aa_quiescent),.source_reads_drained(aa_reads_drained),.live_slots(aa_live_slots),.fault_cycles(aa_faults));
 wire aa_active_slot;
 reg h_valid=0,h_write=0,h_take=0;
 reg [9:0] h_address=0;
 reg [127:0] h_data=0;
 wire h_ready,h_response_valid,raw_response;
 wire [127:0] data_shared;
 wire [95:0] tags_shared;
 wire req_valid,req_write,req_ready,rsp_valid_mem,rsp_ready_mem,raw_req_ready;
 wire [9:0] req_address;
 wire [127:0] req_data,rsp_data_mem;
 wire [1:0] occupied;
 integer cycle,mode=0,seed=1;
 wire request_enable=mode==0 || cycle%5!=2;
 wire response_enable=mode==0 || cycle%7>=3;
 assign rsp_valid=raw_response&&response_enable;
 assign rsp_data=data_shared;
 assign rsp_tag=tags_shared[95:64];
 native_s128_mux3 arbiter(.clk,.reset,
  .c_valid({s_valid,aa_s_valid,h_valid}),.c_write({s_write,1'b0,h_write}),.c_address({s_address,aa_s_address,h_address}),
  .c_data({s_data,128'd0,h_data}),.c_tag({s_tag,aa_s_tag,32'h80000000}),.c_ready({s_ready,aa_s_ready,h_ready}),
  .c_response_valid({raw_response,aa_rsp_valid,h_response_valid}),.c_response_ready({rsp_ready&&response_enable,aa_rsp_ready,h_take}),
  .c_response_data(data_shared),.c_response_tag(tags_shared),
  .req_valid,.req_write,.req_address,.req_data,.req_ready,
  .rsp_valid(rsp_valid_mem),.rsp_ready(rsp_ready_mem),.rsp_data(rsp_data_mem),.owners_occupied(occupied));
 assign req_ready=raw_req_ready&&request_enable;
 local_s_base storage(.clk,.reset,.req_valid(req_valid&&request_enable),.req_write,
  .req_addr(req_address),.req_data,.req_ready(raw_req_ready),
  .rsp_valid(rsp_valid_mem),.rsp_ready(rsp_ready_mem),.rsp_data(rsp_data_mem));

 task automatic host_access(input bit write_en,input integer address,input reg [127:0] data,
                            output reg [127:0] result);
  if(address<0 || address>=1024)$fatal(1,"host address outside SRAM");
  @(negedge clk);h_valid=1;h_write=write_en;h_address=10'(address);h_data=data;
  do @(posedge clk);while(!h_ready);
  @(negedge clk);h_valid=0;
  while(!h_response_valid)@(negedge clk);
  if(tags_shared[31:0]!=32'h80000000)$fatal(1,"host response owner tag");
  result=data_shared;h_take=1;
  @(negedge clk);h_take=0;
 endtask
 function automatic signed [63:0] reference_round(input signed [31:0] value,input integer amount);
  reg signed [63:0] divisor,q,r;
  begin
   divisor=64'sd1<<amount;q=64'(value)/divisor;r=64'(value)%divisor;
   if(r<0)begin q=q-1;r=r+divisor;end
   reference_round=q+64'(2*r>divisor || (2*r==divisor && q[0]));
  end
 endfunction
 integer first_request,last_ack,reads,writes,acks,started;
 reg measuring=0;
 always @(posedge clk)begin
  cycle=cycle+1;
  if(!reset && measuring)begin
   if(s_valid&&s_ready)begin
    $display("QUANTIZER_EVENT cycle=%0d kind=REQ write=%0d address=%0d tag=%h",cycle,s_write,s_address,s_tag);
    if(first_request<0)first_request=cycle;
    if(s_write)writes=writes+1;else reads=reads+1;
   end
   if(rsp_valid&&rsp_ready)begin
    $display("QUANTIZER_EVENT cycle=%0d kind=ACK write=%0d tag=%h",cycle,rsp_tag[15:14]==2'd3,rsp_tag);
    if(rsp_tag[15:14]==2'd3)begin acks=acks+1;last_ack=cycle;end
   end
   if(aa_s_valid && !metadata_sent)$fatal(1,"A read before committed scale publication");
   if(aa_cmd_valid && aa_cmd_ready && (!scale_valid || done_written_mask!=16'hffff))$fatal(1,"A lease joined incomplete data/scale");
   if(occupied>2)$fatal(1,"ordinary S response owner overflow");
  end
  if(cycle>50000)$fatal(1,"real S watchdog");
 end
 reg signed [31:0] values[0:127];
 reg [127:0] scratch,word_data;
 reg signed [63:0] expected;
 integer amount;
 initial begin
  cycle=0;
  if(!$value$plusargs("mode=%d",mode))mode=0;
  if(!$value$plusargs("seed=%d",seed))seed=1;
  seed=$urandom(seed);
  repeat(4)@(negedge clk);reset=0;
  for(integer test_id=0;test_id<12;test_id=test_id+1)begin
   amount=(test_id/2)*3;
   for(integer i=0;i<128;i=i+1)begin
    values[i]=32'((i%2==0?1:-1)*(i*61+1)*(1<<amount));
   end
   values[0]=32'(32767<<amount);
   // INT_MIN independently exercises the maximum unsigned magnitude and s17.
   if(test_id>=10)begin values[31]=32'h80000000;amount=17;end
   for(integer i=0;i<32;i=i+1)begin
    host_access(1,32+i,{values[4*i+3],values[4*i+2],values[4*i+1],values[4*i]},scratch);
    if(scratch!==0)$fatal(1,"ordinary S write response must not echo payload");
   end
   @(negedge clk);
   cmd_generation=16'(test_id+1);cmd_kk=16'(test_id*128);cmd_key=128'(test_id+1);
   cmd_shift_known=1'(test_id%2);cmd_shift=6'(amount);
   dir_cfg_valid=1;
   do @(posedge clk);while(!dir_cfg_ready);
   @(negedge clk);dir_cfg_valid=0;
   if(dir_cfg_rejected)$fatal(1,"scale directory configuration failed");
   aa_slot=1'(test_id%2);aa_cmd_valid=1;
   first_request=-1;last_ack=-1;reads=0;writes=0;acks=0;measuring=1;
   cmd_valid=1;started=cycle;
   do @(posedge clk);while(!cmd_ready);
   @(negedge clk);cmd_valid=0;
   while(!done_valid)@(negedge clk);
   if(done_error||done_cancelled || done_words!=16 || done_written_mask!=16'hffff || done_shift!=6'(amount) ||
      done_key!=cmd_key || done_kk!=cmd_kk || reads!=(cmd_shift_known?32:64) || writes!=16 || acks!=16 || rejected_responses!=0)
    $fatal(1,"quantizer real-S terminal/counts mismatch %0d %0d %0d %0d",done_shift,reads,writes,acks);
   $display("QUANTIZER_REAL_S mode=%0d known=%0d shift=%0d cmd_to_done=%0d first_request=%0d last_true_ACK=%0d occupied_cycles=%0d reads=%0d writes=%0d ACK=%0d",
     mode,cmd_shift_known,amount,cycle-started,first_request,last_ack,last_ack-first_request+1,reads,writes,acks);
   repeat(3)begin
    @(negedge clk);
    if(!done_valid || done_shift!=6'(amount)||cmd_ready || s_valid)$fatal(1,"scale metadata hold lost");
   end
   done_ready=1;@(negedge clk);done_ready=0;measuring=0;
   while(!aa_load_valid)@(negedge clk);
   aa_cmd_valid=0;
   if(aa_load_error || aa_load_key!=cmd_key || aa_load_gen!=cmd_generation || aa_load_slot!=aa_slot)$fatal(1,"scaled LOAD identity");
   aa_load_take=1;@(negedge clk);aa_load_take=0;
   for(integer use_id=1;use_id<=2;use_id=use_id+1)begin
    aa_sequence=16'(use_id);aa_w_valid=1;
    do @(posedge clk);while(!aa_w_ready);
    @(negedge clk);aa_w_valid=0;aa_use_valid=1;
    do @(posedge clk);while(!aa_use_ready);
    @(negedge clk);aa_use_valid=0;
    for(integer beat=0;beat<8;beat=beat+1)begin
     while(!aa_valid)@(negedge clk);
     if(aa_step!=3'(beat)||aa_shift!=6'(amount)||aa_key!=cmd_key||aa_gen!=cmd_generation||aa_kk!=cmd_kk||
        aa_use_sequence!=16'(use_id)||aa_record!=1984||aa_active_slot!=aa_slot)$fatal(1,"scaled A lease identity");
     for(integer lane=0;lane<16;lane=lane+1)begin
      expected=reference_round(values[16*beat+lane],amount);
      if(expected < -32768 || expected > 32767 || aa_data[16*lane+:16]!==16'(expected))$fatal(1,"quantizer to actual A16 mismatch");
     end
     repeat(test_id%3)@(negedge clk);
     aa_take=1;@(negedge clk);aa_take=0;
    end
   end
   aa_close_valid=1;do @(posedge clk);while(!aa_close_ready);
   @(negedge clk);aa_close_valid=0;aa_release_valid=1;
   do @(posedge clk);while(!aa_release_ready);
   @(negedge clk);aa_release_valid=0;
   if(!aa_quiescent || !aa_reads_drained || aa_live_slots!=0 || aa_faults!=0 || publish_rejected || rejected_publications!=0)$fatal(1,"scale/A lease drain failed");
   for(integer i=0;i<16;i=i+1)begin
    host_access(0,256+i,0,word_data);
    for(integer j=0;j<8;j=j+1)begin
     expected=reference_round(values[8*i+j],amount);
     if(expected < -32768 || expected > 32767)$fatal(1,"reference does not fit A16");
     if($signed(word_data[16*j+:16])!==16'(expected))$fatal(1,"actual S A16 result %0d",8*i+j);
    end
   end
  end
  $display("PASS quant_a_joint cases=12 actual_banks=4 A_uses=24 dynamic_scale_same_object=1 mode=%0d",mode);
  $finish;
 end
endmodule
