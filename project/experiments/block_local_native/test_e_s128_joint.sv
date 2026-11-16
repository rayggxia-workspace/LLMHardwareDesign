`timescale 1ns/1ps
module test_e_s128_joint #(parameter bit AP64=1'b0);
 reg clk;initial clk=0;always #5 clk=~clk;
 reg reset=1,cmd_valid=0,done_ready=0;
 reg [3:0] cmd_op=0,cmd_tail_mask=15;
 reg [7:0] cmd_shift=0;
 reg [2:0] cmd_minus=0;
 reg [9:0] cmd_a=10,cmd_b=42,cmd_c=74,cmd_out=106;
 reg [5:0] cmd_words=1;
 wire cmd_ready,done_valid,done_error;
 wire [5:0] done_words;
 wire [7:0] done_clipped_lanes;
 wire s_req_valid,s_req_write,s_req_ready,s_rsp_valid,s_rsp_ready;
 wire [9:0] s_req_address;
 wire [127:0] s_req_data,s_rsp_data;
 e_s128_frontend #(.AP64(AP64)) dut(.*);

 reg host_req=0,host_wr=0,host_take=0;
 reg [9:0] host_addr=0;
 reg [127:0] host_data=0;
 wire [1:0] cr,rv,occupied;
 wire [63:0] response_tag;
 wire req_valid,req_write,req_ready,rsp_valid,rsp_ready;
 wire [9:0] req_addr;
 wire [127:0] req_data,rsp_data;
 integer mode,cycle,rd,wr,ack;
 reg measuring=0;
 wire req_enable=mode==0||cycle%7>=2;
 wire rsp_enable=mode==0||cycle%11>=4;
 assign s_req_ready=cr[1]&&req_enable;
 assign s_rsp_valid=rv[1]&&rsp_enable;
 assign s_rsp_data=rsp_data;
 wire [127:0] memory_data;
 native_s128_mux2 arb(.clk,.reset,
  .c_valid({s_req_valid&&req_enable,host_req}),.c_write({s_req_write,host_wr}),
  .c_address({s_req_address,host_addr}),.c_data({s_req_data,host_data}),
  .c_tag({32'hE32,32'h123}),.c_ready(cr),.c_response_valid(rv),
  .c_response_ready({s_rsp_ready&&rsp_enable,host_take}),
  .c_response_data(rsp_data),.c_response_tag(response_tag),
  .req_valid,.req_write,.req_address(req_addr),.req_data,.req_ready,
  .rsp_valid,.rsp_ready,.rsp_data(memory_data),.owners_occupied(occupied));
 local_s_base banked(.clk,.reset,.req_valid,.req_write,.req_addr,.req_data,.req_ready,
   .rsp_valid,.rsp_ready,.rsp_data(memory_data));
 task automatic memory(input bit write_en,input integer address,input reg[127:0] data,
                       output reg[127:0] result);
  if(address<0||address>=1024)$fatal(1,"host S address overflow");
  @(negedge clk);host_wr=write_en;host_addr=10'(address);host_data=data;host_req=1;
  do @(posedge clk);while(!cr[0]);@(negedge clk);host_req=0;
  while(!rv[0])@(negedge clk);
  if(response_tag[31:0]!=32'h123)$fatal(1,"wrong host owner");
  result=rsp_data;host_take=1;@(negedge clk);host_take=0;
 endtask
 reg was_stalled;
 reg [138:0] held_request;
 always @(posedge clk)begin
  cycle<=cycle+1;
  if(cycle>80000)$fatal(1,"E real S watchdog");
  if(reset)begin was_stalled<=0;held_request<=0;end
  else begin
   if(was_stalled&&(!s_req_valid||{s_req_write,s_req_address,s_req_data}!==held_request))
      $fatal(1,"E changed a stalled S request");
   was_stalled<=s_req_valid&&!s_req_ready;
   held_request<={s_req_write,s_req_address,s_req_data};
   if(measuring)begin
    if(s_req_valid&&s_req_ready)begin
     if(s_req_write)wr<=wr+1;else rd<=rd+1;
    end
    if(s_rsp_valid&&s_rsp_ready)begin
     if(response_tag[63:32]!=32'hE32)$fatal(1,"wrong E owner");
     ack<=ack+1;
    end
    if(occupied>1)$fatal(1,"E requires extra S outstanding capacity");
   end
  end
 end
 task automatic run_case(input bit bad,input integer exp_words,exp_reads,exp_clip);
  integer begin_cycle,begin_rd,begin_wr,begin_ack;
  @(negedge clk);begin_rd=rd;begin_wr=wr;begin_ack=ack;measuring=1;cmd_valid=1;begin_cycle=cycle;
  do @(posedge clk);while(!cmd_ready);@(negedge clk);cmd_valid=0;
  while(!done_valid)@(negedge clk);
  repeat(4)begin
   if(!done_valid||done_error!=bad||int'(done_words)!=exp_words||cmd_ready||
      int'(done_clipped_lanes)!=exp_clip||rd-begin_rd!=exp_reads||wr-begin_wr!=exp_words||ack-begin_ack!=exp_reads+exp_words||occupied!=0)
      $fatal(1,"E missing true write ACK, output count, error or clips");
   @(negedge clk);
  end
  $display("E_REAL_S mode=%0d op=%0d error=%0d cycles=%0d rd=%0d wr=%0d ack=%0d",
     mode,cmd_op,bad,cycle-begin_cycle-4,rd-begin_rd,wr-begin_wr,ack-begin_ack);
  done_ready=1;@(negedge clk);done_ready=0;measuring=0;
 endtask
 reg [535:0] v[768];
 reg [127:0] value;
 string path;
 integer nr,nclip,legal,badcases;
 initial begin
  cycle=0;rd=0;wr=0;ack=0;legal=0;badcases=0;
  if(!$value$plusargs("mode=%d",mode))mode=0;
  if(!$value$plusargs("vectors=%s",path))$fatal(1,"vectors required");
  $readmemh(path,v);repeat(4)@(negedge clk);reset=0;
  for(integer t=0;t<96;t=t+1)begin
   cmd_op=v[t][512+:4];cmd_shift=v[t][516+:8];cmd_tail_mask=v[t][524+:4];cmd_minus=v[t][528+:3];
   cmd_out=t%2==0?10'd106:10'd10;
   nr=cmd_op==1||cmd_op==9?3:cmd_op==3||cmd_op==4||cmd_op==10||cmd_op==11?1:2;
   nclip=$countones(v[t][531+:4]);
   memory(1,10,v[t][0+:128],value);memory(1,42,v[t][128+:128],value);memory(1,74,v[t][256+:128],value);
   if(v[t][535])begin run_case(1,0,0,0);badcases=badcases+1;end
   else begin
    run_case(0,1,nr,nclip);
    memory(0,int'(cmd_out),0,value);
    if(value!==v[t][384+:128])$fatal(1,"E real S independent integer mismatch row=%0d",t);
    legal=legal+1;
   end
  end
  cmd_op=3;cmd_shift=1;cmd_minus=0;cmd_tail_mask=4'b0101;cmd_words=8;cmd_out=cmd_a;
  for(integer i=0;i<8;i=i+1)memory(1,10+i,{32'd3,32'hffffffff,32'hfffffffd,32'hfffffffb},value);
  run_case(0,8,8,0);
  for(integer i=0;i<8;i=i+1)begin
   memory(0,10+i,0,value);
   if(value!==(i==7?128'h00000000_00000000_00000000_fffffffe:128'h00000002_00000000_fffffffe_fffffffe))
    $fatal(1,"E in-place tail/tie result mismatch");
  end
  cmd_out=11;run_case(1,0,0,0);
  cmd_out=1020;run_case(1,0,0,0);
  cmd_out=106;cmd_words=0;run_case(1,0,0,0);
  $display("PASS e_s128_joint legal=%0d bad=%0d actual_banks=4 extra_SRAM=0 mode=%0d aperture=%0d",legal+1,badcases+3,mode,AP64 ? 64 : 128);
  $finish;
 end
endmodule
