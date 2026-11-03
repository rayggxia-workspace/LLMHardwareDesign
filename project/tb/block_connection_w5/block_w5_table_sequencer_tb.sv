`timescale 1ns/1ps
// Protocol-only test: permanent G1 ROM/metadata, delayed MOCK service endpoint.
// No A/F arithmetic, native S/T ACK, peer endpoint or physical ROM qualification.
module block_w5_table_sequencer_tb;
 reg clk=0;always #5 clk=~clk;
 reg reset=1,abort=0,job_valid=0,done_ready=0;
 reg [31:0] job_generation=0;
 wire job_ready,busy,done_valid,done_error,cohort_abort;
 wire [31:0] done_generation;
 wire rom_req_valid,rom_req_ready,rom_rsp_ready;
 wire [7:0] rom_req_addr;
 reg rom_rsp_valid=0,rom_rsp_error=0;
 reg [127:0] rom_rsp_data=0;
 wire [4:0] meta_addr;
 reg [511:0] meta_data;
 wire svc_valid,svc_ready,svc_done_ready;
 wire [127:0] svc_record;
 wire [9:0] svc_a_base,svc_b_base;
 reg svc_done_valid=0,svc_done_error=0;
 reg [127:0] rom[0:255];reg [511:0] meta[0:16];
 reg allow_rom=1,allow_svc=1,allow_complete=1,pattern=0;
 reg r_pending=0,s_pending=0;
 reg [127:0] r_word=0,s_word=0;
 reg r_error=0,s_error=0;
 integer r_delay=0,s_delay=0,cycle=0,fault_mode=0,cases=0;
 integer jobs=0,dones=0,rom_requests=0,rom_responses=0,services=0,service_dones=0,aborts_seen=0;
 integer obligation=0;reg [31:0] expected_generation=0;
 reg h_rom=0,h_svc=0,h_done=0;
 reg [7:0] h_rom_addr;
 reg [147:0] h_service;
 reg [32:0] h_completion;
 string rom_path,meta_path;
 block_w5_table_sequencer dut(.*);
 assign rom_req_ready=allow_rom&&!r_pending&&!rom_rsp_valid&&(!pattern||cycle%3!=0);
 assign svc_ready=allow_svc&&!s_pending&&!svc_done_valid&&(!pattern||cycle%4!=0);
 function automatic [127:0] rec(input [7:0] op,input [15:0] a,b,c,input [31:0] imm,input [15:0] nxt,aux);
  rec={aux,nxt,imm,c,b,a,8'd0,op};
 endfunction
 function automatic integer first_op(input integer op);
  integer i;
  begin first_op=-1;for(i=47;i>=0;i=i-1)if(rom[i][7:0]==op)first_op=i;end
 endfunction
 function automatic [127:0] fetched(input [7:0] addr);
  reg [127:0] w;
  begin
   w=rom[addr];
   if(addr==0)case(fault_mode)
    1:w[7:0]=255;2:w[15:8]=1;3:w[47:32]=1;4:w[31:16]=17;
    13:w=rec(16,0,0,0,0,1,0);
    14:w[111:96]=256;
    15:w=rec(18,0,0,0,0,0,0);
    default:begin end
   endcase
   if(addr==1)case(fault_mode)
    6:w[95:64]=255;
    7:w=rec(15,0,0,0,0,2,0);
    default:begin end
   endcase
   if(addr==first_op(6)&&fault_mode==8)w=rec(5,1,0,0,0,{8'd0,addr}+1,0);
   if(addr==first_op(6)&&fault_mode==9)begin w=rom[first_op(4)];w[111:96]={8'd0,addr}+1;end
   if(addr==first_op(11)&&fault_mode==10)w=rec(12,1,0,0,0,{8'd0,addr}+1,0);
   if(addr==first_op(13)&&fault_mode==11)w=rec(14,1,0,0,0,{8'd0,addr}+1,0);
   if(addr==first_op(21)&&fault_mode==12)w=rec(19,2,0,0,256,{8'd0,addr}+1,0);
   fetched=w;
  end
 endfunction
 always @*begin
  meta_data=meta_addr<17?meta[meta_addr]:512'd0;
  if(meta_addr==0)begin
   if(fault_mode==5)meta_data[143:136]=12;
   if(fault_mode==18)meta_data[15:0]=1;
   if(fault_mode==20)meta_data[175:160]=2;
  end
 end
 // All model state changes use NBA at the capture edge; stimulus uses negedges.
 always @(posedge clk)begin
  cycle<=cycle+1;
  if(reset||cohort_abort)begin
   r_pending<=0;s_pending<=0;rom_rsp_valid<=0;svc_done_valid<=0;
   rom_rsp_error<=0;svc_done_error<=0;r_delay<=0;s_delay<=0;
  end else begin
   if(rom_rsp_valid&&rom_rsp_ready)rom_rsp_valid<=0;
   if(rom_req_valid&&rom_req_ready)begin
    r_pending<=1;r_word<=fetched(rom_req_addr);r_error<=fault_mode==17&&rom_req_addr==0;
    r_delay<=pattern?3:1;
   end
   if(r_pending)begin
    if(r_delay!=0)r_delay<=r_delay-1;
    else begin rom_rsp_valid<=1;rom_rsp_data<=r_word;rom_rsp_error<=r_error;r_pending<=0;end
   end
   if(svc_done_valid&&svc_done_ready)svc_done_valid<=0;
   if(svc_valid&&svc_ready)begin
    s_pending<=1;s_word<=svc_record;s_error<=fault_mode==16&&svc_record[7:0]==2;
    s_delay<=pattern?5:2;
   end
   if(s_pending&&allow_complete)begin
    if(s_delay!=0)s_delay<=s_delay-1;
    else begin svc_done_valid<=1;svc_done_error<=s_error;s_pending<=0;end
   end
  end
 end
 task fail(input string message);begin $fatal(1,"FAIL_W5_TABLE_SEQUENCER %s cycle=%0d",message,cycle);end endtask
 always @(posedge clk)begin
  if(reset)begin obligation=0;h_rom=0;h_svc=0;h_done=0;end
  else begin
   if(h_done&&(!done_valid||{done_error,done_generation}!==h_completion))fail("held DONE changed");
   if(!abort&&!cohort_abort)begin
    if(h_rom&&(!rom_req_valid||rom_req_addr!==h_rom_addr))fail("ROM request not stable");
    if(h_svc&&(!svc_valid||{svc_record,svc_a_base,svc_b_base}!==h_service))fail("service not stable");
   end
   if(job_valid&&job_ready)begin
    if(obligation)fail("duplicate task admission");obligation=1;expected_generation=job_generation;jobs=jobs+1;
   end
   if(done_valid&&done_ready)begin
    if(!obligation||done_generation!==expected_generation)fail("terminal ownership");
    obligation=0;dones=dones+1;
   end
   if(done_valid&&done_generation!==expected_generation)fail("terminal generation");
   if(cohort_abort)aborts_seen=aborts_seen+1;
   if(rom_req_valid&&rom_req_ready)rom_requests=rom_requests+1;
   if(rom_rsp_valid&&rom_rsp_ready)rom_responses=rom_responses+1;
   if(svc_done_valid&&svc_done_ready)service_dones=service_dones+1;
   if(svc_valid&&svc_ready)begin
    services=services+1;
    if(fault_mode==0)begin
     if(svc_record!==rom[dut.pc])fail("real ROM record mismatch");
     if(svc_record[7:0]==2||svc_record[7:0]==6||svc_record[7:0]==19)
      if(svc_a_base!==(svc_record[31:16]==1?10'd256:10'd0))fail("first-free source base");
     if(svc_record[7:0]==4||svc_record[7:0]==11)
      if(svc_b_base!==(svc_record[47:32]==1?10'd256:10'd0))fail("first-free destination base");
    end
   end
   h_rom=rom_req_valid&&!rom_req_ready&&!abort&&!cohort_abort;h_rom_addr=rom_req_addr;
   h_svc=svc_valid&&!svc_ready&&!abort&&!cohort_abort;h_service={svc_record,svc_a_base,svc_b_base};
   h_done=done_valid&&!done_ready;h_completion={done_error,done_generation};
  end
  if(cycle>200000)fail("global watchdog");
 end
 task ticks(input integer n);repeat(n)@(negedge clk);endtask
 task mark(input string id);begin cases=cases+1;$display("CASE_PASS %s",id);$fflush();end endtask
 task admit;
  integer w;
  begin
   @(negedge clk);job_generation=job_generation+1;job_valid=1;w=0;
   while(!job_ready)begin @(negedge clk);w=w+1;if(w>100)fail("admission timeout");end
   @(posedge clk);@(negedge clk);job_valid=0;
  end
 endtask
 task finish(input bit error_expected,input bit abort_with_ready);
  integer w,old_dones;reg [32:0] snapshot;
  begin
   w=0;while(!done_valid)begin @(negedge clk);w=w+1;if(w>10000)fail("completion timeout");end
   if(done_error!==error_expected||done_generation!==job_generation)fail("completion status");
   snapshot={done_error,done_generation};old_dones=dones;ticks(4);
   if(!done_valid||{done_error,done_generation}!==snapshot||!busy||job_ready)fail("DONE holding");
   done_ready=1;abort=abort_with_ready;@(posedge clk);@(negedge clk);done_ready=0;abort=0;ticks(2);
   if(dones!=old_dones+1||done_valid||busy||!job_ready)fail("DONE exactly once/reuse");
  end
 endtask
 task normal(input string id);
  integer rq,rr,ss,sd,aa;
  begin
   fault_mode=0;allow_rom=1;allow_svc=1;allow_complete=1;
   rq=rom_requests;rr=rom_responses;ss=services;sd=service_dones;aa=aborts_seen;
   admit();finish(0,0);
   if(rom_requests-rq!=48||rom_responses-rr!=48||services-ss!=41||service_dones-sd!=41||aborts_seen!=aa)
    fail("normal48ROM/41mockservice counts");
   if(dut.slot_used!=0||dut.live!=0)fail("HALT slot leak");mark(id);
  end
 endtask
 task negative(input integer mode,input string id);
  integer aa;
  begin
   fault_mode=mode;allow_rom=1;allow_svc=1;allow_complete=1;aa=aborts_seen;
   admit();finish(1,0);if(aborts_seen!=aa+1)fail("error cohort pulse exactly once");
   fault_mode=0;mark(id);
  end
 endtask
 task abort_now;
  begin abort=1;@(posedge clk);@(negedge clk);abort=0;finish(1,0);end
 endtask
 initial begin
  for(integer j=0;j<256;j=j+1)rom[j]=0;
  for(integer j=0;j<17;j=j+1)meta[j]=0;
  if(!$value$plusargs("rom=%s",rom_path)||!$value$plusargs("meta=%s",meta_path))fail("required +rom/+meta");
  $readmemh(rom_path,rom);$readmemh(meta_path,meta);
  if(rom[0][7:0]!=1||rom[47][7:0]!=18||meta[0][63:32]!=4096)fail("wrong frozen G1 input files");
  ticks(3);reset=0;ticks(2);
  normal("W5_SEQ_G1_NORMAL_REAL_TABLE");
  pattern=1;normal("W5_SEQ_G1_NORMAL_REUSE");pattern=0;
  allow_rom=0;admit();ticks(6);if(!rom_req_valid||done_valid)fail("ROM stall");
  allow_rom=1;finish(0,0);mark("W5_SEQ_ROM_REQUEST_BACKPRESSURE");
  allow_svc=0;admit();while(!svc_valid)@(negedge clk);ticks(6);
  if(!svc_valid||done_valid)fail("service command stall");allow_svc=1;finish(0,0);mark("W5_SEQ_SERVICE_BACKPRESSURE");
  allow_complete=0;admit();while(!s_pending)@(negedge clk);ticks(6);
  if(done_valid||rom_req_valid||svc_valid)fail("must wait independent service completion");
  allow_complete=1;finish(0,0);mark("W5_SEQ_SERVICE_COMPLETION_WAIT");
  admit();finish(0,1);mark("W5_SEQ_HELD_DONE_ABORT_READY_ONCE");
  allow_rom=0;admit();ticks(3);abort_now();allow_rom=1;mark("W5_SEQ_ABORT_FETCH");
  allow_svc=0;admit();while(!svc_valid)@(negedge clk);abort_now();allow_svc=1;mark("W5_SEQ_ABORT_SERVICE_SEND");
  allow_complete=0;admit();while(!s_pending)@(negedge clk);abort_now();allow_complete=1;mark("W5_SEQ_ABORT_SERVICE_INFLIGHT");
  allow_complete=0;admit();while(!s_pending)@(negedge clk);reset=1;ticks(2);reset=0;allow_complete=1;ticks(3);
  if(done_valid||busy||!job_ready)fail("hard reset must cancel without DONE");mark("W5_SEQ_HARD_RESET_INFLIGHT");
  negative(1,"W5_SEQ_BAD_OPCODE");negative(2,"W5_SEQ_BAD_FLAGS");negative(3,"W5_SEQ_BAD_RESERVED");
  negative(4,"W5_SEQ_BAD_OBJECT_INDEX");negative(5,"W5_SEQ_BAD_META_FIN");negative(6,"W5_SEQ_BAD_IMPORT_LENGTH");
  negative(7,"W5_SEQ_FREE_BEFORE_ACK");negative(8,"W5_SEQ_START_BEFORE_FRAME");negative(9,"W5_SEQ_REENTRY_BEFORE_RELEASE");
  negative(10,"W5_SEQ_CLOSE_BEFORE_STORE_ACK");negative(11,"W5_SEQ_DONE_BEFORE_RELEASE");negative(12,"W5_SEQ_DUPLICATE_EXPORT");
  negative(13,"W5_SEQ_IF_UNSUPPORTED");negative(14,"W5_SEQ_BAD_NEXT_PC");negative(15,"W5_SEQ_EARLY_HALT");
  negative(16,"W5_SEQ_SERVICE_ERROR");negative(17,"W5_SEQ_ROM_ERROR");negative(18,"W5_SEQ_META_ID");
  negative(20,"W5_SEQ_META_REFCOUNT");
  normal("W5_SEQ_NORMAL_RECOVERY_AFTER_ERRORS");
  if(cases!=30)fail("predeclared CASE count");
  $display("W5_TABLE_COUNTS jobs=%0d dones=%0d rom_req=%0d svc=%0d",jobs,dones,rom_requests,services);
  $display("PASS_W5_TABLE_SEQUENCER cases=%0d",cases);$fflush();$finish;
 end
endmodule
