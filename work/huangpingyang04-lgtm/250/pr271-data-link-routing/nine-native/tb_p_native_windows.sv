module tb_p_native_windows;
 logic clk=0,reset=1,halt=0,flush=0;
 always #5 clk=!clk;
 logic abort_valid=0,abort_ready,abort_transport_drained=1;
 logic [127:0] abort_key=0;
 logic abort_slot=0;
 logic [15:0] abort_generation=0,abort_kk=0,abort_use_sequence=0;
 logic cmd_valid=0,cmd_ready,cmd_slot=0;
 logic [15:0] cmd_generation=0,cmd_kk=0,cmd_planned_uses=1;
 logic [127:0] cmd_key=128'h1234,copy_key=128'h1234;
 logic [9:0] cmd_S_base=0,cmd_copy_offset=0;
 logic [10:0] copy_committed_prefix=0;
 logic load_done_valid,load_done_ready=0,load_done_slot,load_done_error;
 logic [15:0] load_done_generation;
 logic [127:0] load_done_key;
 logic s_valid,s_ready=0;
 logic [9:0] s_address;
 logic [31:0] s_tag;
 logic response_valid=0,response_ready;
 logic [31:0] response_tag=0;
 logic [127:0] response_data=0;
 logic w_valid=0,w_ready,w_slot=0;
 logic [15:0] w_generation=0,w_kk=0,w_use_sequence=1;
 logic [127:0] w_key=128'h1234;
 logic [31:0] w_record=0;
 logic use_valid=0,use_ready,use_slot=0;
 logic [15:0] use_generation=0,use_kk=0,use_sequence=1;
 logic [127:0] use_key=128'h1234;
 logic a_valid,a_ready=0;
 logic [255:0] a_data;
 logic [2:0] a_step;
 logic [31:0] a_weight_record;
 logic [127:0] a_key;
 logic a_slot;
 logic [15:0] a_generation,a_kk,a_use_sequence;
 logic close_valid=0,close_ready,close_slot=0;
 logic [15:0] close_generation=0;
 logic release_valid=0,release_ready,release_slot=0;
 logic [15:0] release_generation=0;
 logic quiescent,source_reads_drained;
 logic [1:0] live_slots;
 logic [31:0] fault_cycles;
 private_a_tile_abort_frontend actual_native_A (.*);
 int cycles=0,read_count=0;
 int delay_count=0;
 logic pending=0;
 logic [31:0] pending_tag;
 logic [9:0] pending_address;
 always @(negedge clk) begin
   cycles=cycles+1;s_ready=!reset && cycles%5!=0 && !pending && !response_valid;
 end
 always @(posedge clk) begin
   if(!reset) begin
     if(s_valid && s_ready) begin
       if(s_address<cmd_S_base || s_address>=cmd_S_base+copy_committed_prefix)
         $fatal(1,"read before remote committed prefix");
       pending<=1;pending_tag<=s_tag;pending_address<=s_address;delay_count<=3;
       read_count<=read_count+1;
     end
     if(pending && !response_valid) begin
       if(delay_count!=0) delay_count<=delay_count-1;
       else begin
         response_valid<=1;response_tag<=pending_tag;
         response_data<={4{32'(pending_address+1)}};pending<=0;
       end
     end
     if(response_valid && response_ready) response_valid<=0;
   end
 end
 task automatic window(input int number);
   int before_reads;
   logic [255:0] held;
   @(negedge clk);
   cmd_slot=1'(number%2);cmd_generation=16'(number/2+1);cmd_kk=16'(number*128);
   cmd_S_base=10'(number*32);copy_committed_prefix=0;before_reads=read_count;
   cmd_valid=1;
   do @(posedge clk); while(!cmd_ready);
   @(negedge clk);cmd_valid=0;
   repeat(6) @(negedge clk);
   if(s_valid || read_count!=before_reads) $fatal(1,"speculative window read");
   copy_committed_prefix=8;
   wait(read_count==before_reads+8);
   repeat(12) @(negedge clk);
   if(read_count!=before_reads+8 || load_done_valid) $fatal(1,"crossed prefix boundary");
   copy_committed_prefix=16;
   wait(load_done_valid);
   if(load_done_error || !source_reads_drained || load_done_key!=cmd_key ||
      load_done_generation!=cmd_generation || load_done_slot!=cmd_slot || read_count!=before_reads+16)
     $fatal(1,"native A load proof mismatch");
   repeat(3) @(negedge clk);
   load_done_ready=1;
   @(negedge clk);load_done_ready=0;
   w_slot=cmd_slot;w_generation=cmd_generation;w_kk=cmd_kk;w_record=32'(number+19);w_valid=1;
   do @(posedge clk); while(!w_ready);
   @(negedge clk);w_valid=0;
   use_slot=cmd_slot;use_generation=cmd_generation;use_kk=cmd_kk;use_valid=1;
   do @(posedge clk); while(!use_ready);
   @(negedge clk);use_valid=0;
   close_slot=cmd_slot;close_generation=cmd_generation;close_valid=1;
   do @(posedge clk); while(!close_ready);
   @(negedge clk);close_valid=0;
   release_slot=cmd_slot;release_generation=cmd_generation;
   for(int beat=0;beat<8;beat++) begin
     wait(a_valid);
     held=a_data;
     repeat(2) begin
       @(negedge clk);
       if(!a_valid || a_data!==held || release_ready) $fatal(1,"unstable stream or early tile release");
     end
     if(a_step!=beat || a_data!=={ {4{32'(number*32+2*beat+2)}}, {4{32'(number*32+2*beat+1)}} } ||
        a_key!=cmd_key || a_generation!=cmd_generation || a_kk!=cmd_kk || a_weight_record!=w_record)
       $fatal(1,"window/word/weight association mismatch");
     a_ready=1;
     @(negedge clk);a_ready=0;
   end
   wait(release_ready);release_valid=1;
   @(negedge clk);release_valid=0;
   repeat(2) @(negedge clk);
   if(live_slots!=0 || fault_cycles!=0) $fatal(1,"window not retired cleanly");
 endtask
 initial begin
   repeat(3) @(negedge clk);reset=0;
   window(0);window(1);window(2);
   $display("PASS: native P A frontend: 3 remote K windows, 48 tagged reads, committed-prefix gating, stalled 256b delivery, safe slot reuse");
   $finish;
 end
 initial begin repeat(5000) @(posedge clk);$fatal(1,"timeout");end
endmodule
