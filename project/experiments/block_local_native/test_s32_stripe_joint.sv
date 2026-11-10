`timescale 1ns/1ps
// Two actual four-bank S instances. No additional tile storage in the DUT.
module test_s32_stripe_joint;
 reg clk;initial clk=0;always #5 clk=!clk;
 reg reset=1,start_valid=0,done_ready=0,window_released=1;
 reg [127:0] start_key=0;
 reg [15:0] generation=0,written_mask=16'hffff;
 reg [31:0] first_col=0;
 reg [9:0] ring_base=720;
 reg [4:0] words=16;
 wire start_ready,done_valid,done_error,quiescent;
 wire [31:0] faults,committed;
 wire [10:0] prefix;
 wire [127:0] copy_key;
 wire source_valid,source_ready,source_response_valid,source_response_ready;
 wire [9:0] source_address;
 wire [31:0] source_tag,source_response_tag;
 wire [127:0] source_response_data;
 wire destination_valid,destination_ready,destination_ack_valid,destination_ack_ready;
 wire [9:0] destination_address;
 wire [31:0] destination_tag,destination_ack_tag;
 wire [127:0] destination_data;
 s32_stripe_copy dut(.clk,.reset,.halt(1'b0),.start_valid,.start_ready,.start_key,.start_generation(generation),
  .start_first_col(first_col),.start_source_base(10'd32),.start_ring_base(ring_base),.start_words(words),
  .start_written_mask(written_mask),.start_producer_error(1'b0),.destination_window_released(window_released),
  .source_valid,.source_ready,.source_address,.source_tag,.source_response_valid,.source_response_ready,
  .source_response_tag,.source_response_data,.source_response_error(1'b0),
  .destination_valid,.destination_ready,.destination_address,.destination_tag,.destination_data,
  .destination_ack_valid,.destination_ack_ready,.destination_ack_tag,.destination_ack_error(1'b0),
  .copy_key,.committed_prefix(prefix),.done_valid,.done_ready,.done_error,.quiescent,.fault_cycles(faults),.committed_words(committed));
 reg host_valid=0,host_write=0,host_take=0,host_memory=0;
 reg [9:0] host_address=0;reg [127:0] host_data=0;
 wire host_ready,host_response;wire [127:0] host_result;
 wire [1:0] cv[2],cw[2],cr[2],rv[2],rr[2];
 wire [19:0] ca[2];wire [255:0] cd[2];wire [63:0] ct[2],rt[2];
 wire [127:0] rd[2];wire [1:0] occupied[2];
 wire [1:0] nv,nw,nready,nrv,nrr;
 wire [9:0] na[2];wire [127:0] nd[2],nrd[2];
 integer cycle,mode=0,seed=1;
 wire responses=mode==0||cycle%7>=3;
 assign cv[0]={source_valid,host_valid&&!host_memory};assign cw[0]={1'b0,host_write};
 assign ca[0]={source_address,host_address};assign cd[0]={128'd0,host_data};assign ct[0]={source_tag,32'h80000000};
 assign cv[1]={destination_valid,host_valid&&host_memory};assign cw[1]={1'b1,host_write};
 assign ca[1]={destination_address,host_address};assign cd[1]={destination_data,host_data};assign ct[1]={destination_tag,32'h80000000};
 assign rr[0]={source_response_ready,host_take}&{2{responses}};
 assign rr[1]={destination_ack_ready,host_take}&{2{responses}};
 assign host_ready=cr[host_memory][0];assign host_response=rv[host_memory][0]&&responses;assign host_result=rd[host_memory];
 assign source_ready=cr[0][1];assign source_response_valid=rv[0][1]&&responses;
 assign source_response_tag=rt[0][63:32];assign source_response_data=rd[0];
 assign destination_ready=cr[1][1];assign destination_ack_valid=rv[1][1]&&responses;assign destination_ack_tag=rt[1][63:32];
 for(genvar m=0;m<2;m=m+1)begin: memories
  native_s128_mux2 mux(.clk,.reset,.c_valid(cv[m]),.c_write(cw[m]),.c_address(ca[m]),.c_data(cd[m]),.c_tag(ct[m]),
   .c_ready(cr[m]),.c_response_valid(rv[m]),.c_response_ready(rr[m]),.c_response_data(rd[m]),.c_response_tag(rt[m]),
   .req_valid(nv[m]),.req_write(nw[m]),.req_address(na[m]),.req_data(nd[m]),.req_ready(nready[m]),
   .rsp_valid(nrv[m]),.rsp_ready(nrr[m]),.rsp_data(nrd[m]),.owners_occupied(occupied[m]));
  local_s_base storage(.clk,.reset,.req_valid(nv[m]),.req_write(nw[m]),.req_addr(na[m]),.req_data(nd[m]),
   .req_ready(nready[m]),.rsp_valid(nrv[m]),.rsp_ready(nrr[m]),.rsp_data(nrd[m]));
 end
 task automatic access_s(input bit memory_id,input bit write_en,input integer address,input reg[127:0] data,output reg[127:0] result);
  if(address<0||address>=1024)$fatal(1,"host S bounds");
  @(negedge clk);host_memory=memory_id;host_write=write_en;host_address=10'(address);host_data=data;host_valid=1;
  do @(posedge clk);while(!host_ready);@(negedge clk);host_valid=0;
  while(!host_response)@(negedge clk);
  if(rt[memory_id][31:0]!=32'h80000000)$fatal(1,"host S response owner");
  result=host_result;host_take=1;@(negedge clk);host_take=0;
 endtask
 integer source_reads,destination_writes,acks;
 reg measuring=0;
 always @(posedge clk)begin
  cycle=cycle+1;
  if(cycle>300000)$fatal(1,"stripe copy watchdog");
  if(!reset&&measuring)begin
   if(source_valid&&source_ready)source_reads=source_reads+1;
   if(destination_valid&&destination_ready)begin
    destination_writes=destination_writes+1;
    if(destination_address<ring_base||{1'b0,destination_address}>={1'b0,ring_base}+11'd64)$fatal(1,"stripe destination escaped ring");
   end
   if(destination_ack_valid&&destination_ack_ready)acks=acks+1;
   if(occupied[0]>2||occupied[1]>2)$fatal(1,"stripe ordinary S owner capacity");
  end
 end
 reg [127:0] expected[64],scratch,word_data;
 integer address_index,before_faults,before_committed,begin_cycle,legal_cases=0,bad_cases=0;
 initial begin
  cycle=0;
  if(!$value$plusargs("mode=%d",mode))mode=0;
  if(!$value$plusargs("seed=%d",seed))seed=1;
  seed=$urandom(seed);repeat(4)@(negedge clk);reset=0;
  for(integer i=0;i<64;i=i+1)begin expected[i]=128'h123456;access_s(1,1,720+i,expected[i],scratch);end
  // Includes wrap at 256, three producer interleave, a 64-value tail and
  // a large global index whose upper bits cannot alter modulo addressing.
  for(integer t=0;t<30;t=t+1)begin
   @(negedge clk);generation=16'(t+1);start_key={32'h250,32'd8,32'(t),32'd1};
   first_col=32'((t/3)*192+(t%3)*8);if(t==29)first_col=32'hfffffef0;
   words=t>=24?5'(4+2*(t%3)):5'd16;written_mask=16'hffff>>(16-words);
   if(t==27)written_mask=0;
   if(t==28)ring_base=980;
   for(integer i=0;i<int'(words);i=i+1)begin
    for(integer lane=0;lane<4;lane=lane+1)word_data[lane*32+:32]=32'(100000*t+100*i+lane);
    access_s(0,1,32+i,word_data,scratch);
    address_index=int'(((first_col/4)+(i/2)*6+(i%2))%64);
    if(address_index<0||address_index>=64)$fatal(1,"reference ring bounds");
    if(t!=27&&t!=28)expected[address_index]=word_data;
   end
   source_reads=0;destination_writes=0;acks=0;before_faults=int'(faults);before_committed=int'(committed);measuring=1;
   if(t==1)begin
    window_released=0;start_valid=1;
    repeat(7)begin @(negedge clk);if(start_ready||source_valid||destination_valid)$fatal(1,"copy stole live consumer window");end
    window_released=1;
   end else start_valid=1;
   begin_cycle=cycle;do @(posedge clk);while(!start_ready);@(negedge clk);start_valid=0;
   while(!done_valid)@(negedge clk);
   if(t==27||t==28)begin
    if(!done_error||source_reads!=0||destination_writes!=0||acks!=0||int'(faults)!=before_faults+1||int'(committed)!=before_committed)
     $fatal(1,"invalid stripe recipe issued traffic");
    bad_cases=bad_cases+1;
   end else begin
    if(done_error||copy_key!=start_key||prefix!={6'd0,words}||source_reads!=int'(words)||destination_writes!=int'(words)||
      acks!=int'(words)||int'(committed)!=before_committed+int'(words)||int'(faults)!=before_faults)$fatal(1,"stripe true ACK conservation");
    legal_cases=legal_cases+1;
    $display("STRIPE_REAL_S case=%0d mode=%0d words=%0d cycles=%0d reads=%0d writes=%0d ACK=%0d",t,mode,words,cycle-begin_cycle,source_reads,destination_writes,acks);
   end
   done_ready=1;@(negedge clk);done_ready=0;measuring=0;ring_base=720;
   if(!quiescent)$fatal(1,"stripe did not drain source/ACK owners");
   for(integer i=0;i<64;i=i+1)begin access_s(1,0,720+i,0,scratch);if(scratch!==expected[i])$fatal(1,"stripe ring numeric/untouched word case=%0d index=%0d",t,i);end
  end
  $display("PASS s32_stripe_joint legal=%0d bad=%0d actual_banks=8 extra_SRAM=0 mode=%0d",legal_cases,bad_cases,mode);$finish;
 end
endmodule
