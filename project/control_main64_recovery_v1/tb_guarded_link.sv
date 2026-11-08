module tb_guarded_link;
 reg clk_i=0;always #5 clk_i=~clk_i;
 reg rst_ni=0,halt_i=0,source_valid=0,source_legal=1,destination_reserved=0,destination_ready=0,destination_ack=0,ack_ready=0;
 reg [9:0] source_address=73;reg [127:0] source_data=128'h123456789abcdef0123456789abcdef0;
 reg [511:0] source_identity=512'h1930001176300010000004d000000030000000b00000000;
 wire source_ready,destination_valid,destination_ack_ready,ack_valid,ack_abort,ack_committed,store_commit,busy,fault_o;
 wire [9:0] destination_address;wire [127:0] destination_data;wire [511:0] ack_identity;
 main64_guarded_link dut(.*);
 reg [511:0] gold_identity;reg [127:0] gold_data;integer mode=0,commits=0,acks=0;
 always @(posedge clk_i)if(rst_ni)begin
  if(store_commit)commits<=commits+1;
  if(ack_valid && ack_ready)acks<=acks+1;
 end
 task tick;@(negedge clk_i);endtask
 task start_word;
  begin
   gold_identity=source_identity;gold_data=source_data;
   source_valid=1;do @(posedge clk_i);while(!source_ready);tick();source_valid=0;
   source_address=99;source_data=~gold_data;source_identity=~gold_identity;
   if(destination_address!=73 || destination_data!==gold_data)$fatal(1,"captured payload/address changed");
  end
 endtask
 task accept_ack(input bit aborted,input bit committed_word);
  begin
   while(!ack_valid)tick();
   repeat(8)begin
    if(!ack_valid || ack_identity!==gold_identity || ack_abort!==aborted || ack_committed!==committed_word ||
       destination_address!=73 || destination_data!==gold_data)$fatal(1,"ACK/source lease changed under backpressure");
    tick();
   end
   ack_ready=1;tick();ack_ready=0;tick();
   if(busy || ack_valid)$fatal(1,"ACK did not retire one word");
  end
 endtask
 initial begin
  void'($value$plusargs("MODE=%d",mode));repeat(4)tick();rst_ni=1;tick();
  if(mode==1 || mode==5)begin
   halt_i=mode==1;destination_ack=1;
   repeat(8)begin tick();if(ack_valid || store_commit || destination_ack_ready || busy)$fatal(1,"spurious ACK without ownership");end
  end else begin
   source_legal=mode!=6;start_word();
   if(mode==2 || mode==6)begin
    repeat(5)begin tick();if(destination_valid || ack_valid)$fatal(1,"unoffered word committed early");end
    if(mode==6 && !fault_o)$fatal(1,"illegal source not recorded");
    halt_i=1;accept_ack(1,0);
   end else begin
    destination_reserved=1;while(!destination_valid)tick();
    repeat(3)tick();
    if(mode==3)halt_i=1;
    destination_reserved=0;
    // Once valid was offered, reservation changes or halt cannot revoke it.
    repeat(8)begin tick();if(!destination_valid || destination_data!==gold_data || ack_valid)$fatal(1,"irrevocable offer was withdrawn");end
    destination_ready=1;tick();destination_ready=0;
    if(mode==4)halt_i=1;
    repeat(5)begin tick();if(ack_valid)$fatal(1,"ACK preceded actual SRAM callback");end
    destination_ack=1;while(!destination_ack_ready)tick();tick();destination_ack=0;tick();
    accept_ack(mode==3 || mode==4,1);
   end
  end
  if(commits!=(mode==0 || mode==3 || mode==4) || acks!=(mode!=1 && mode!=5))$fatal(1,"commit/ACK duplication");
  $display("PASS guarded-link mode=%0d commits=%0d acks=%0d",mode,commits,acks);$finish;
 end
 initial begin #100000;$fatal(1,"guarded-link unit watchdog");end
endmodule

