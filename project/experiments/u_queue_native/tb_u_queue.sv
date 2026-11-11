module tb_u_queue #(parameter integer DEPTH=0,PIPE=0);
 `include "tb_u_ports.svh"
 assign nv=0;assign nmeta=0;assign nsrc=0;assign ndst=0;assign ntake=1;
 // [311:308]op [307:303]shift [302:301]sources [300]store [299]direct [298]abort
 // [297:268]src [267:258]dst [257:130]direct-data [129:0]expected
 reg [311:0] commands[0:4095];reg [127:0] initial_mem[0:1023],final_mem[0:1023];
 integer expected_reads[0:4095],expected_writes[0:4095];
 string init_path,final_path,cmd_path,name;integer total,stress,contention;
 integer sent=0,received=0,first_tick=0,end_tick=0,peak=0,reads=0,writes=0,write_acks=0,memory_kind=0;
 integer input_wait=0,done_wait=0,core_inputs=0,core_outputs=0,direct_index=0,direct_count=0;
 reg active=0,accepted=0,held=0;reg [129:0] held_data;reg direct_taken=0;
 reg [127:0] ignored,got;
 always @(posedge clk)begin
  if(!reset&&active)begin
   accepted=ev&&eready;direct_taken=direct_ready&&(direct_valid||direct_abort);
   if(accepted)begin if(sent==0)first_tick=ticks;sent++;end
   if(ev&&!eready)input_wait++;
   if(held&&(!edone||{eerror,esat,edata}!==held_data))$fatal(1,"done changed under backpressure");
   if(dut.request[1]&&dut.accept[1])begin
    memory_kind=dut.write[1];if(dut.write[1])writes++;else reads++;
   end
   if(dut.response[1]&&dut.take[1]&&memory_kind)write_acks++;
   if(dut.e_valid&&dut.e_ready)core_inputs++;
   if(dut.er_valid&&dut.er_ready)core_outputs++;
   if(edone&&etake)begin
    if(received>=sent||{eerror,esat,edata}!==commands[received][129:0])$fatal(1,"queue numeric/order case=%s item=%0d got=%h expected=%h",name,received,{eerror,esat,edata},commands[received][129:0]);
    if(write_acks<expected_writes[received])$fatal(1,"completion before write ACK");
    received++;end_tick=ticks;
   end
   if(sent-received>peak)peak=sent-received;
   if(sent-received>(DEPTH==0?1:DEPTH))$fatal(1,"unbounded queue");
   held=edone&&!etake;held_data={eerror,esat,edata};if(held)done_wait++;
  end
 end
 task automatic reset_cut(input integer cut);
  begin
   @(negedge clk);ev=1;esources=2;eop=0;eshift=0;esrc={10'd0,10'd1,10'd0};edst=900;estore=1;edirect=0;etake=0;
   do @(posedge clk);while(!eready);@(negedge clk);ev=0;
   if(cut==0)begin do @(posedge clk);while(!(dut.request[1]&&dut.accept[1]));end
   if(cut==1)begin do @(posedge clk);while(!(dut.e_valid&&dut.e_ready));end
   if(cut==2)begin do @(posedge clk);while(!edone);end
   @(negedge clk);reset=1;repeat(3)@(negedge clk);reset=0;etake=1;
   repeat(30)begin @(negedge clk);if(edone)$fatal(1,"ghost completion after reset");end
   etake=0;
  end
 endtask
 initial begin
  if(!$value$plusargs("INIT=%s",init_path)||!$value$plusargs("FINAL=%s",final_path)||!$value$plusargs("COMMANDS=%s",cmd_path)||
     !$value$plusargs("NAME=%s",name)||!$value$plusargs("COUNT=%d",total)||!$value$plusargs("STRESS=%d",stress)||!$value$plusargs("CONTENTION=%d",contention))$fatal(1,"missing queue inputs");
  $readmemh(init_path,initial_mem);$readmemh(final_path,final_mem);$readmemh(cmd_path,commands,0,total-1);
  begin integer r=0,w=0;
   for(integer i=0;i<total;i++)begin
    r+=int'(commands[i][302:301])-int'(commands[i][299]&&commands[i][302:301]!=0);
    if(commands[i][298])r-=int'(commands[i][302:301])-1;
    w+=int'(commands[i][300]&&!commands[i][129]);expected_reads[i]=r;expected_writes[i]=w;
   end
  end
  repeat(4)@(negedge clk);reset=0;
  access(0,1,0,0,0,ignored);access(0,1,1,0,0,ignored);
  for(integer cut=0;cut<3;cut++)reset_cut(cut);
  for(integer a=0;a<1024;a++)access(0,1,10'(a),initial_mem[a],0,ignored);
  @(negedge clk);active=1;
  fork
   begin
    while(received<total)begin
     if(!ev||accepted)begin
      ev=sent<total&&(stress==0||ticks%7!=2);
      if(sent<total)begin
       eop=commands[sent][311:308];eshift=commands[sent][307:303];esources=commands[sent][302:301];
       estore=commands[sent][300];edirect=commands[sent][299];esrc=commands[sent][297:268];edst=commands[sent][267:258];
      end
     end
     if(direct_taken)begin direct_count++;direct_index++;end
     while(direct_index<total&&(!commands[direct_index][299]||commands[direct_index][302:301]==0))direct_index++;
     direct_valid=direct_index<sent&&!commands[direct_index][298];
     direct_abort=direct_index<sent&&commands[direct_index][298];
     direct_data=direct_index<total?commands[direct_index][257:130]:128'd0;
     etake=stress==0||(ticks%19>=9);
     @(negedge clk);
     if(ticks>500000)$fatal(1,"queue deadlock %s sent=%0d received=%0d",name,sent,received);
    end
    ev=0;direct_valid=0;direct_abort=0;etake=0;active=0;
   end
   begin
    while(active)begin
     if(contention)begin access(1,0,1000,0,5,ignored);repeat(3)@(negedge clk);end
     else @(negedge clk);
    end
   end
  join
  if(reads!=expected_reads[total-1]||writes!=expected_writes[total-1]||write_acks!=writes)$fatal(1,"queue traffic mismatch %s r=%0d/%0d w=%0d/%0d ack=%0d",name,reads,expected_reads[total-1],writes,expected_writes[total-1],write_acks);
  for(integer a=0;a<1024;a++)begin access(0,0,10'(a),0,0,got);if(got!==final_mem[a])$fatal(1,"final S mismatch %s address=%0d",name,a);end
  $display("QUEUE_MEASURE depth=%0d pipe=%0d commands=%0d cycles=%0d peak=%0d reads=%0d writes=%0d ACKs=%0d input_wait=%0d done_wait=%0d core_inputs=%0d core_outputs=%0d direct=%0d",DEPTH,PIPE,total,end_tick-first_tick+1,peak,reads,writes,write_acks,input_wait,done_wait,core_inputs,core_outputs,direct_count);
  $display("QUEUE_PASS values=%0d memory_words=1024 reset_cuts=3",total*8);$finish;
 end
endmodule
