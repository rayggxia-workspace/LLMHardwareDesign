`timescale 1ns/1ps
module tb_packer;
 reg clk;initial begin clk=0;forever #5 clk=~clk;end
 reg reset=1,cmd_valid=0,out_ready=0;
 wire cmd_ready,s_valid,r_ready,out_valid,out_weight,out_error;
 reg [31:0] cmd_tag,cmd_scalar_base,cmd_k_stride,cmd_n_stride;
 reg cmd_weight,cmd_k_major;reg [2:0] cmd_digit,cmd_n_count;reg [4:0] cmd_k_count;
 wire [31:0] s_address,s_tag,out_tag;
 reg s_ready,r_valid,r_error;reg [31:0] r_tag;reg [127:0] r_data;
 wire [511:0] out_data;
 dynamic_s32_packer dut(.*);
 reg pending;integer requests,reads_before;
`ifndef REAL_S
 integer delay_left;
`endif
 reg [31:0] saved_tag;reg [1:0] inject;
`ifndef REAL_S
 reg [31:0] saved_address;
`endif
 integer ideal;
 initial if(!$value$plusargs("ideal=%d",ideal))ideal=0;
 function automatic [31:0] scalar(input [33:0] index);
  reg [31:0] raw;reg [3:0] rem11;
  begin
   raw=index[31:0]*32'd1103515245+32'd12345;rem11=4'(index%34'd11);
   case(rem11)
    0:scalar=32'h80000000;1:scalar=32'h7fffffff;2:scalar=32'hffffffff;
    3:scalar=0;4:scalar=127;5:scalar=32768;6:scalar=-32'd32769;
    default:scalar=raw;
   endcase
  end
 endfunction
 always @(posedge clk)begin
  if(reset)requests=0;
  else begin
   if(s_valid && s_ready)begin
    if(pending)$fatal(1,"more than one outstanding read");
    pending=1;saved_tag=s_tag;
`ifndef REAL_S
    saved_address=s_address;delay_left=ideal!=0 ? 1 : 1+int'($urandom_range(0,6));
`else
    if(s_address[31:10]!=0)$fatal(1,"read outside actual private S");
`endif
    requests=requests+1;
    $display("PACK_REQ cycle=%0d tag=%0d addr=%0d",$time/10,s_tag,s_address);
   end
   if(r_valid && r_ready)begin
    if(!pending)$fatal(1,"orphan read return");
    pending=0;
    $display("PACK_RSP cycle=%0d tag=%0d",$time/10,r_tag);
   end
  end
 end
`ifndef REAL_S
 always @(negedge clk)begin
  if(reset)begin pending=0;r_valid=0;s_ready=0;r_error=0;delay_left=0;end
  else begin
   s_ready=!pending && (ideal!=0 || $urandom_range(0,3)!=0);
   if(!pending)r_valid=0;
   else if(delay_left>0)begin delay_left=delay_left-1;r_valid=0;end
   else begin
    r_valid=1;r_tag=saved_tag^(inject==1 ? 32'd1 : 32'd0);r_error=inject==2;
    for(integer j=0;j<4;j=j+1)r_data[j*32+:32]=scalar({saved_address,2'b0}+34'(j));
   end
  end
 end
`else
 // Real four 1RW SRAM banks. 10ns functional clock honors the generated
 // bank model's 3ns delay; this protocol test is not 300MHz STA.
 reg booting,boot_valid,request_permit,response_permit;
 reg [9:0] boot_address;reg [127:0] boot_data;
 wire bank_ready,bank_valid;wire [127:0] bank_data;
 local_s_base storage(.clk,.reset,.req_valid(booting ? boot_valid : s_valid && request_permit),
  .req_write(booting),.req_addr(booting ? boot_address : s_address[9:0]),.req_data(boot_data),
  .req_ready(bank_ready),.rsp_valid(bank_valid),.rsp_ready(booting ? 1'b1 : r_ready && response_permit),
  .rsp_data(bank_data));
 always @*begin
  s_ready=!booting && request_permit && bank_ready;
  r_valid=!booting && response_permit && bank_valid;
  r_tag=saved_tag^(inject==1 ? 32'd1 : 32'd0);r_error=inject==2;r_data=bank_data;
 end
 always @(negedge clk)begin
  if(reset)begin pending=0;request_permit=0;response_permit=0;end
  else begin
   request_permit=ideal!=0 || $urandom_range(0,3)!=0;
   response_permit=ideal!=0 || $urandom_range(0,3)!=0;
  end
 end
`endif
 string path;integer fd,got,count=0,expected_reads;reg expected_error;reg [511:0] expected,held;
 initial begin
  if(!$value$plusargs("vectors=%s",path))$fatal(1,"vectors missing");
  fd=$fopen(path,"r");if(fd==0)$fatal(1,"vectors unreadable");
`ifdef REAL_S
  booting=1;boot_valid=0;boot_address=0;boot_data=0;
`endif
  repeat(4)@(negedge clk);reset=0;
  // Drive commands away from the memory peer's negedge activity.
  @(posedge clk);#1;
`ifdef REAL_S
  booting=1;boot_valid=0;
  for(integer word_index=0;word_index<1024;word_index=word_index+1)begin
   boot_address=10'(word_index);
   for(integer lane=0;lane<4;lane=lane+1)boot_data[lane*32+:32]=scalar(34'(word_index*4+lane));
   boot_valid=1;do @(posedge clk);while(!bank_ready);
   #1;boot_valid=0;
   while(!bank_valid)begin @(posedge clk);#1;end
   @(posedge clk);#1;
  end
  booting=0;
`endif
  while(!$feof(fd))begin
   got=$fscanf(fd,"%h %h %h %h %h %h %h %h %h %h %h %h %h\n",cmd_tag,cmd_weight,
     cmd_k_major,cmd_digit,cmd_scalar_base,cmd_k_stride,cmd_n_stride,cmd_k_count,
     cmd_n_count,inject,expected_error,expected,expected_reads);
   if(got!=13)$fatal(1,"bad packer vector");
   reads_before=requests;cmd_valid=1;
   do @(posedge clk);while(!cmd_ready);
   $display("PACK_CMD cycle=%0d tag=%0d weight=%0d major=%0d",$time/10,cmd_tag,cmd_weight,cmd_k_major);
   #1;cmd_valid=0;
   while(!out_valid)begin @(posedge clk);#1;end
   $display("PACK_DONE cycle=%0d tag=%0d reads=%0d error=%0d",$time/10,cmd_tag,requests-reads_before,out_error);
   if(out_tag!==cmd_tag || out_weight!==cmd_weight || out_error!==expected_error || out_data!==expected)
    $fatal(1,"packer mismatch cmd%0d tag%0d goterr%0d experr%0d",count,cmd_tag,out_error,expected_error);
   if(pending || requests-reads_before!=expected_reads)$fatal(1,"packer real read count mismatch");
   held=out_data;
   repeat($urandom_range(0,6))begin
    @(posedge clk);#1;if(!out_valid || out_data!==held || cmd_ready)$fatal(1,"held packet changed");
   end
   out_ready=1;@(posedge clk);#1;out_ready=0;count=count+1;
  end
  $display("PASS packer commands=%0d requests=%0d",count,requests);$finish;
 end
 initial begin #1000000000;$fatal(1,"watchdog");end
endmodule
