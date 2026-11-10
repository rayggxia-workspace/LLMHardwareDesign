`timescale 1ns/1ps
// Original bank DELAY=3ns, deliberately 10ns functional clock: not STA.
module test_quantizer_real_s;
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
 reg h_valid=0,h_write=0,h_take=0;
 reg [9:0] h_address=0;
 reg [127:0] h_data=0;
 wire h_ready,h_response_valid,raw_response;
 wire [127:0] data_shared;
 wire [63:0] tags_shared;
 wire req_valid,req_write,req_ready,rsp_valid_mem,rsp_ready_mem,raw_req_ready;
 wire [9:0] req_address;
 wire [127:0] req_data,rsp_data_mem;
 wire [1:0] occupied;
 integer cycle,mode=0,seed=1;
 wire request_enable=mode==0 || cycle%5!=2;
 wire response_enable=mode==0 || cycle%7>=3;
 assign rsp_valid=raw_response&&response_enable;
 assign rsp_data=data_shared;
 assign rsp_tag=tags_shared[63:32];
 native_s128_mux2 arbiter(.clk,.reset,
  .c_valid({s_valid,h_valid}),.c_write({s_write,h_write}),.c_address({s_address,h_address}),
  .c_data({s_data,h_data}),.c_tag({s_tag,32'h80000000}),.c_ready({s_ready,h_ready}),
  .c_response_valid({raw_response,h_response_valid}),.c_response_ready({rsp_ready&&response_enable,h_take}),
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
   for(integer i=0;i<16;i=i+1)begin
    host_access(0,256+i,0,word_data);
    for(integer j=0;j<8;j=j+1)begin
     expected=reference_round(values[8*i+j],amount);
     if(expected < -32768 || expected > 32767)$fatal(1,"reference does not fit A16");
     if($signed(word_data[16*j+:16])!==16'(expected))$fatal(1,"actual S A16 result %0d",8*i+j);
    end
   end
  end
  $display("PASS quantizer_real_s cases=12 actual_banks=4 metadata_after_true_ACK=1 payload_register_bytes=32 mode=%0d",mode);
  $finish;
 end
endmodule
