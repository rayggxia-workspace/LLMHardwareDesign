`timescale 1ns/1ps
// LOCAL_S_PACK64 is a separately named source; no DDR request/byte is hidden.
module tb_weight_source;
 reg clk;initial begin clk=0;forever #5 clk=~clk;end
 reg reset=1;
 reg bind_valid=0,bind_ack_ready=1,release_valid=0,cancel_valid=0,close_valid=0;
 wire bind_ready,bind_ack_valid,bind_ack_error,release_ready,cancel_ready,close_ready;
 reg [127:0] bind_key,release_key,cancel_key;wire [127:0] bind_ack_key;
 reg [63:0] bind_record_base;
 reg [31:0] bind_scalar_base,bind_k_stride,bind_n_stride;
 reg [7:0] bind_length;reg [3:0] bind_n;reg [2:0] bind_digit;reg bind_k_major;
 reg [31:0] close_tag_base;
 reg req_valid=0,rsp_ready=0;wire req_ready,rsp_valid;reg [63:0] req_address;reg [31:0] req_tag;
 reg [4:0] req_record_beats=17;
 wire [31:0] rsp_tag;wire [511:0] rsp_data;
 wire s_valid,s_ready,r_valid,r_ready;wire [31:0] s_address,s_tag,r_tag;wire [127:0] r_data;
 wire r_error=0;
 wire fault_valid,active,quiescent;reg fault_ready=0;wire [3:0] fault_reason;
 wire [31:0] fault_tag;wire [63:0] fault_address;wire [4:0] returned_beats;
 dynamic_s32_weight_source dut(.*);
 reg booting=1,boot_valid=0;reg [9:0] boot_address;reg [127:0] boot_data;
 wire bank_ready,bank_valid;wire [127:0] bank_data;
 reg [31:0] saved_tag;reg request_permit,response_permit;reg source_bad_tag=0;
 wire bank_req_valid=booting ? boot_valid : s_valid && request_permit;
 wire bank_rsp_ready=booting ? 1'b1 : r_ready && response_permit;
 local_s_base storage(.clk,.reset,.req_valid(bank_req_valid),.req_write(booting),
  .req_addr(booting ? boot_address : s_address[9:0]),.req_data(boot_data),
  .req_ready(bank_ready),.rsp_valid(bank_valid),.rsp_ready(bank_rsp_ready),.rsp_data(bank_data));
 assign s_ready=!booting && request_permit && bank_ready;
 assign r_valid=!booting && response_permit && bank_valid;
 assign r_data=bank_data;assign r_tag=saved_tag^(source_bad_tag ? 32'd1 : 32'd0);
 always @(negedge clk)begin
  if(reset)begin request_permit=0;response_permit=0;end
  else begin request_permit=$urandom_range(0,3)!=0;response_permit=$urandom_range(0,3)!=0;end
 end
 integer cycle,reads,returns;
 always @(posedge clk)begin
  if(reset)begin cycle=0;reads=0;returns=0;saved_tag=0;end
  else begin
   cycle=cycle+1;
   if(bind_valid && bind_ready)$display("LOCAL_BIND cycle=%0d key=%0d length=%0d n=%0d digit=%0d",cycle,bind_key,bind_length,bind_n,bind_digit);
   if(req_valid && req_ready)$display("LOCAL_MC_REQ cycle=%0d tag=%0d address=%0d",cycle,req_tag,req_address);
   if(rsp_valid && rsp_ready)$display("LOCAL_MC_RETURN cycle=%0d tag=%0d",cycle,rsp_tag);
   if(s_valid && s_ready)begin
    if(s_address[31:10]!=0)$fatal(1,"source escaped private16KiB S");
    saved_tag=s_tag;reads=reads+1;
    $display("LOCAL_S_REQ cycle=%0d tag=%0d address=%0d",cycle,s_tag,s_address);
   end
   if(r_valid && r_ready)begin returns=returns+1;$display("LOCAL_S_ACK cycle=%0d tag=%0d",cycle,r_tag);end
  end
 end
 function automatic [31:0] scalar(input integer index);
  reg [31:0] raw;
  begin
   raw=32'(index)*32'd1103515245+32'd12345;
   case(index%11)
    0:scalar=32'h80000000;1:scalar=32'h7fffffff;2:scalar=32'hffffffff;
    3:scalar=0;4:scalar=127;5:scalar=32768;6:scalar=-32'd32769;default:scalar=raw;
   endcase
  end
 endfunction
 task automatic bind_source(input bit expect_error);
  begin
   bind_valid=1;do @(posedge clk);while(!bind_ready);#1;bind_valid=0;
   while(!bind_ack_valid)begin @(posedge clk);#1;end
   if(bind_ack_error!==expect_error || bind_ack_key!==bind_key)$fatal(1,"binding ack mismatch");
   @(posedge clk);#1;
  end
 endtask
 task automatic take_fault(input [3:0] reason);
  reg [99:0] held;
  begin
   while(!fault_valid)begin @(posedge clk);#1;end
   if(fault_reason!==reason)$fatal(1,"wrong fault reason");
   held={fault_reason,fault_tag,fault_address};
   repeat(3)begin @(posedge clk);#1;if(!fault_valid || {fault_reason,fault_tag,fault_address}!==held)$fatal(1,"fault changed");end
   fault_ready=1;@(posedge clk);#1;fault_ready=0;
  end
 endtask
 task automatic request_beat(input [4:0] b,input [31:0] tag_base_value);
  begin
   req_address=bind_record_base+{53'd0,b,6'd0};req_tag=tag_base_value+{27'd0,b};req_valid=1;
   do @(posedge clk);while(!req_ready);#1;req_valid=0;
  end
 endtask
 task automatic take_response(input [511:0] expected,input [31:0] tag_value);
  reg [543:0] held;
  begin
   while(!rsp_valid)begin @(posedge clk);#1;end
   if(rsp_data!==expected || rsp_tag!==tag_value)$fatal(1,"source beat payload/tag mismatch tag%0d",tag_value);
   held={rsp_tag,rsp_data};
   repeat($urandom_range(0,4))begin
    @(posedge clk);#1;if(!rsp_valid || {rsp_tag,rsp_data}!==held)$fatal(1,"held MC beat changed");
   end
   rsp_ready=1;@(posedge clk);#1;rsp_ready=0;
  end
 endtask
 string path;integer fd,got,count=0;reg [511:0] expected[0:16];reg [31:0] test_tag_base;
 reg [511:0] cancel_expected[0:1];reg [6:0] numeric_digit;integer total_reads,total_returns;
 initial begin
  if(!$value$plusargs("vectors=%s",path))$fatal(1,"vectors missing");
  fd=$fopen(path,"r");if(fd==0)$fatal(1,"source vectors missing");
  repeat(4)@(negedge clk);reset=0;@(posedge clk);#1;
  for(integer word_index=0;word_index<1024;word_index=word_index+1)begin
   boot_address=10'(word_index);
   for(integer lane=0;lane<4;lane=lane+1)boot_data[lane*32+:32]=scalar(word_index*4+lane);
   boot_valid=1;do @(posedge clk);while(!bank_ready);#1;boot_valid=0;
   while(!bank_valid)begin @(posedge clk);#1;end
   @(posedge clk);#1;
  end
  booting=0;
  while(!$feof(fd))begin
   got=$fscanf(fd,"%h %h %h %h %h %h %h\n",bind_length,bind_n,bind_digit,bind_k_major,
     bind_scalar_base,bind_k_stride,bind_n_stride);
   if(got!=7)$fatal(1,"bad source header");
   for(integer j=0;j<17;j=j+1)begin got=$fscanf(fd,"%h\n",expected[j]);if(got!=1)$fatal(1,"bad source data");end
   bind_key=128'(count+123);bind_record_base=64'h100000+64'(count*2048);test_tag_base=32'h8000+32'(count*32);
   bind_source(0);
   if(close_ready)$fatal(1,"ordinary source accepted cancel CLOSE");
   // Invalid addresses/tags may not change the valid owner's issued set.
   req_address=bind_record_base+1;req_tag=test_tag_base;req_valid=1;
   do @(posedge clk);while(!req_ready);#1;req_valid=0;take_fault(4);
   req_record_beats=18;req_address=bind_record_base;req_tag=test_tag_base;req_valid=1;
   do @(posedge clk);while(!req_ready);#1;req_valid=0;take_fault(4);req_record_beats=17;
   for(integer b=0;b<17;b=b+1)begin
    request_beat(5'(b),test_tag_base);take_response(expected[b],test_tag_base+32'(b));
    if(returned_beats!==5'(b+1))$fatal(1,"returned beat count");
    if(b!=16 && release_ready)$fatal(1,"source released before17 true returns");
   end
   release_key=bind_key+1'b1;release_valid=1;
   do @(posedge clk);while(!release_ready);#1;release_valid=0;take_fault(1);
   if(!active)$fatal(1,"bad owner released source");
   release_key=bind_key;release_valid=1;
   do @(posedge clk);while(!release_ready);#1;release_valid=0;
   if(active || !quiescent)$fatal(1,"source binding did not drain");
   count=count+1;
  end
  bind_key=999;bind_length=128;bind_n=8;bind_digit=0;bind_k_major=0;
  bind_record_base=64'h100001;bind_scalar_base=0;bind_k_stride=1;bind_n_stride=128;bind_source(1);
  bind_record_base=64'h100000;bind_scalar_base=4095;bind_source(1);
  // Cancel before any request has no global descriptor and may drain directly.
  bind_scalar_base=0;bind_source(0);cancel_key=998;cancel_valid=1;
  do @(posedge clk);while(!cancel_ready);#1;cancel_valid=0;take_fault(2);
  cancel_key=999;cancel_valid=1;do @(posedge clk);while(!cancel_ready);#1;cancel_valid=0;
  release_key=999;release_valid=1;do @(posedge clk);while(!release_ready);#1;release_valid=0;
  if(active || reads!=returns)$fatal(1,"source conservation/drain");
  // A held, not-yet-accepted beat1 survives cancellation of pending beat0.
  // Source retains only metadata; the MC peer still holds the actual offer.
  bind_source(0);test_tag_base=32'heee0;
  for(integer b=0;b<2;b=b+1)begin
   cancel_expected[b]=0;
   for(integer n=0;n<4;n=n+1)for(integer k=0;k<16;k=k+1)begin
    numeric_digit=7'(scalar((b*4+n)*128+k));
    cancel_expected[b][(n*16+k)*8+:8]={1'b0,numeric_digit};
   end
  end
  request_beat(0,test_tag_base);
  req_address=bind_record_base+64;req_tag=test_tag_base+1;req_valid=1;
  cancel_key=999;cancel_valid=1;do @(posedge clk);while(!cancel_ready);#1;cancel_valid=0;
  if(req_ready)$fatal(1,"pending source lost its return owner");
  take_response(cancel_expected[0],test_tag_base);
  do @(posedge clk);while(!req_ready);#1;req_valid=0;
  close_tag_base=test_tag_base;close_valid=1;do @(posedge clk);while(!close_ready);#1;close_valid=0;
  if(release_ready)$fatal(1,"CLOSE falsely implied the accepted beat returned");
  take_response(cancel_expected[1],test_tag_base+1);
  if(returned_beats!=2 || !release_ready)$fatal(1,"partial true-return drain failed");
  release_key=999;release_valid=1;@(posedge clk);#1;release_valid=0;
  if(active || !quiescent || reads!=returns)$fatal(1,"canceled source did not drain");
  total_reads=reads;total_returns=returns;
  // A true S response identity error cannot become a fabricated successful
  // MC64 return. MC has no error-data wire: source quarantines until reset.
  bind_source(0);source_bad_tag=1;request_beat(0,test_tag_base);take_fault(5);
  if(quiescent || release_ready || rsp_valid || returned_beats!=0)$fatal(1,"poisoned source faked successful drain");
  if(reads!=returns)$fatal(1,"failed S response was not consumed");
  reset=1;repeat(4)@(posedge clk);#1;reset=0;source_bad_tag=0;
  if(active || !quiescent)$fatal(1,"reset did not release quarantined binding");
  $display("PASS local_source records=%0d S128reads=%0d S128ACKs=%0d DDRbytes=0 held_cancel=1 quarantine=1",count,total_reads,total_returns);$finish;
 end
 initial begin #1000000000;$fatal(1,"watchdog");end
endmodule
