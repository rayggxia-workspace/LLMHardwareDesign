`timescale 1ns/1ps
module tb_resident_row_probe;
 `include "p_resident_common.svh"
 logic[127:0] fixture[0:VECTOR_WORDS-1];
 integer profile_start=-1,profile_key,profile_elapsed,profile_cycle=0;
 integer pc[0:32767],pmin[0:32767],pmax[0:32767];
 integer fc[1:8][0:1],fmin[1:8][0:1],fmax[1:8][0:1];
 integer fs=-1,fr,fkey,cases=0;
 always @(posedge clk)begin
  profile_cycle=profile_cycle+1;
  if(reset)begin profile_start=-1;fs=-1;end
  else begin
   if(cmd_valid && cmd_ready)begin
    if(profile_start>=0)$fatal(1,"row P profile overlap");
    profile_start=profile_cycle;
    if(cmd_op==4)profile_key=int'(rows)*2048;
    else if(cmd_op==10)profile_key=int'(rows)*2048+int'(cmd_data[7:4]);
    else if(cmd_op==5)profile_key=int'(rows)*2048+64+int'(cmd_data[9:8])*64+int'(cmd_data[5:0]);
    else $fatal(1,"unexpected row command");
   end
   if(profile_start>=0 && cmd_done)begin
    profile_elapsed=profile_cycle-profile_start;
    pc[profile_key]=pc[profile_key]+1;
    if(profile_elapsed<pmin[profile_key])pmin[profile_key]=profile_elapsed;
    if(profile_elapsed>pmax[profile_key])pmax[profile_key]=profile_elapsed;
    profile_start=-1;
   end
   if(load_valid && load_ready)begin
    if(fs>=0)$fatal(1,"row feeder profile overlap");
    fs=profile_cycle;fr=int'(rows);fkey=int'(reuse_b);
   end
   if(fs>=0 && load_done)begin
    profile_elapsed=profile_cycle-fs;fc[fr][fkey]=fc[fr][fkey]+1;
    if(profile_elapsed<fmin[fr][fkey])fmin[fr][fkey]=profile_elapsed;
    if(profile_elapsed>fmax[fr][fkey])fmax[fr][fkey]=profile_elapsed;
    fs=-1;
   end
  end
 end
 for(genvar bank=0;bank<4;bank=bank+1)begin: controlled_sram_initial_state
  initial begin
   integer pattern;logic[127:0] seed;
   if($value$plusargs("sinit=%d",pattern))begin
    if(pattern<0 || pattern>2)$fatal(1,"invalid SRAM state");
    for(integer wi=0;wi<256;wi=wi+1)begin
     seed=pattern==0?128'd0:pattern==1?{128{1'b1}}:
      {32'h9e3779b9^32'(wi),32'h85ebca6b^32'(bank),32'hc2b2ae35^32'(wi*17+bank),32'h27d4eb2f^32'(wi*97+bank)};
     dut.store.storage.banks[bank].memory.mem[wi]=seed;
    end
   end
  end
 end
 task automatic run_row(input integer id,input integer nr,input integer nk,input integer nt,
  input integer abase,input integer bbase,input integer dst,input integer inputbase,
  input integer termbase,input integer goldbase,input integer bits,input integer shift);
  logic[127:0] got,expected;
  integer began,ack0,a0,b0,w0,prior_b;
  @(negedge clk);reset=1;repeat(4)@(negedge clk);reset=0;rows=4'(nr);
  repeat(4)@(negedge clk);
  load_a_address=10'(abase);load_b_address=10'(bbase);
  // Every unused wide-read word is actually initialized through S's port.
  for(integer j=0;j<8;j=j+1)begin access(1,abase+j,0,got);access(1,bbase+j,0,got);end
  began=cycle;ack0=store_acks;a0=a_fires;b0=b_fires;w0=wide_reads;prior_b=-1;
  for(integer term=0;term<nt;term=term+1)begin
   for(integer rr=0;rr<nr;rr=rr+1)access(1,abase+rr,fixture[inputbase+term*nr+rr],got);
   // fixture term layout: B word, signed16 coefficient, scale shift.
   if(prior_b<0 || fixture[termbase+3*term]!==fixture[termbase+3*prior_b])begin
    access(1,bbase,fixture[termbase+3*term],got);feed(0);
   end else feed(1);
   command(4,0,(fixture[termbase+3*term+1]&128'hffff) |
    ((fixture[termbase+3*term+2]&128'h1f)<<16),0,0,got);
   command(10,0,(64'(nr)<<15) | 64'h1103 | (64'(nk)<<4) | (term==0?64'd4:64'd0),0,0,got);
   prior_b=term;
  end
  for(integer rr=0;rr<nr;rr=rr+1)begin
   command(5,rr<<3,(bits==16?64'h100:64'h200)|64'(shift),1,dst+rr,got);
   expected=fixture[goldbase+rr];
   if(got!==expected)$fatal(1,"row result differs id=%0d row=%0d got=%h expected=%h",id,rr,got,expected);
   access(0,dst+rr,0,got);
   if(got!==expected)$fatal(1,"row SRAM/ACK differs id=%0d row=%0d",id,rr);
  end
  if(store_acks-ack0!=nr || a_fires-a0!=nr*nt)$fatal(1,"row native count differs id=%0d",id);
  $display("ROW_CASE {\"id\":%0d,\"a_fires\":%0d,\"b_fires\":%0d,\"wide_reads\":%0d,\"write_acks\":%0d,\"cycles\":%0d}",
   id,a_fires-a0,b_fires-b0,wide_reads-w0,store_acks-ack0,cycle-began);
  cases=cases+1;
 endtask
 initial begin
  for(integer i=0;i<32768;i=i+1)begin pc[i]=0;pmin[i]=2147483647;pmax[i]=0;end
  for(integer r=1;r<=8;r=r+1)begin
   for(integer key=0;key<32;key=key+1)begin p_count[r][key]=0;p_min[r][key]=2147483647;p_max[r][key]=0;end
   for(integer key=0;key<16;key=key+1)begin m_count[r][key]=0;m_min[r][key]=2147483647;m_max[r][key]=0;end
   for(integer key=0;key<2;key=key+1)begin
    f_count[r][key]=0;f_min[r][key]=2147483647;f_max[r][key]=0;
    fc[r][key]=0;fmin[r][key]=2147483647;fmax[r][key]=0;
   end
  end
  $readmemh("vectors.hex",fixture);
  `include "cases.svh"
  if(cases!=CASE_COUNT)$fatal(1,"row case coverage differs");
  if(profile_start>=0 || fs>=0)$fatal(1,"row profile unfinished");
  for(integer key=0;key<32768;key=key+1)if(pc[key]>0)
   $display("ROW_PROFILE {\"boundary\":\"P\",\"rows\":%0d,\"key\":%0d,\"samples\":%0d,\"min\":%0d,\"max\":%0d}",key/2048,key%2048,pc[key],pmin[key],pmax[key]);
  for(integer r=1;r<=8;r=r+1)for(integer key=0;key<2;key=key+1)if(fc[r][key]>0)
   $display("ROW_PROFILE {\"boundary\":\"feeder\",\"rows\":%0d,\"key\":%0d,\"samples\":%0d,\"min\":%0d,\"max\":%0d}",r,key,fc[r][key],fmin[r][key],fmax[r][key]);
  $display("PASS native resident row services");$finish;
 end
endmodule
