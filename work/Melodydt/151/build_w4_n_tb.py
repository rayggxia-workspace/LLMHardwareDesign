"""Self-contained real S/helper/N/controller TB, generated math expectations."""
import argparse
import json
from pathlib import Path

BODY=r'''
 reg clk=0;always #5 clk=~clk;
 reg reset=1,owner=0,service_active=0,strict=1;
 reg allow_mem_req=1,allow_mem_rsp=1,allow_s_ack=1,allow_n_cmd=1,allow_n_rsp=1;
 reg corrupt_n=0,inject_mem_error=0;
 reg req_valid=0,rsp_ready=0;wire req_ready,rsp_valid,rsp_error,rsp_saturated,busy;
 reg [1:0] req_mode;reg [15:0] req_count;reg [31:0] req_epsilon;
 reg [9:0] req_src_addr=100,req_gamma_addr=200,req_exp_addr=300,req_dst_addr=400;
 wire mv,mr,mw,mrv,mrr,mre;wire [9:0] ma;wire [127:0] md,mrd;
 wire cv,cr,leaf_cr,rv,rr,re,rsat;wire [3:0] cop,ccount;wire [31:0] cp;wire [127:0] cd,ca,rd;
 wire hv,hr,hw,hrv,hrr,hre;wire [9:0] ha;wire [127:0] hd,hrd;
 reg host_valid=0,host_write=1,host_rsp_ready=0;reg [9:0] host_addr;reg [127:0] host_data;
 wire s_req,s_we,s_ready,s_valid,s_take,helper_take;wire [9:0] s_addr;wire [127:0] s_din,s_dout;
 assign hv=!reset&&allow_mem_req&&(owner?mv:host_valid);assign hw=owner?mw:host_write;
 assign ha=owner?ma:host_addr;assign hd=owner?md:host_data;assign mr=!reset&&owner&&allow_mem_req&&hr;
 assign mrv=!reset&&owner&&allow_mem_rsp&&hrv;assign mrd=hrd;assign mre=hre||inject_mem_error;
 assign hrr=!reset&&allow_mem_rsp&&(owner?mrr:host_rsp_ready);
 assign cr=leaf_cr&&allow_n_cmd;assign s_take=helper_take&&allow_s_ack;
 block_w4_n_ctrl u_ctrl(.clk(clk),.reset(reset),.req_valid(req_valid),.req_ready(req_ready),.req_mode(req_mode),.req_count(req_count),.req_epsilon(req_epsilon),.req_src_addr(req_src_addr),.req_gamma_addr(req_gamma_addr),.req_exp_addr(req_exp_addr),.req_dst_addr(req_dst_addr),.rsp_valid(rsp_valid),.rsp_ready(rsp_ready),.rsp_error(rsp_error),.rsp_saturated(rsp_saturated),.busy(busy),.n_cmd_valid(cv),.n_cmd_ready(cr),.n_cmd_op(cop),.n_cmd_count(ccount),.n_cmd_param(cp),.n_cmd_data(cd),.n_cmd_aux(ca),.n_rsp_valid(rv&&allow_n_rsp),.n_rsp_ready(rr),.n_rsp_data(rd),.n_rsp_error(re),.n_rsp_saturated(rsat),.mem_req_valid(mv),.mem_req_ready(mr),.mem_req_write(mw),.mem_req_addr(ma),.mem_req_data(md),.mem_rsp_valid(mrv),.mem_rsp_ready(mrr),.mem_rsp_data(mrd),.mem_rsp_error(mre));
 block_v2_n u_n(.clk(clk),.reset(reset),.cmd_valid(cv&&allow_n_cmd),.cmd_ready(leaf_cr),.cmd_op(corrupt_n?4'd15:cop),.cmd_count(ccount),.cmd_param(cp),.cmd_data(cd),.cmd_aux(ca),.rsp_valid(rv),.rsp_ready(rr&&allow_n_rsp),.rsp_data(rd),.rsp_error(re),.rsp_saturated(rsat),.busy());
 block_p2_s_ctrl u_helper(.clk(clk),.resetn(!reset),.req_valid(hv),.req_ready(hr),.req_write(hw),.req_addr(ha),.req_data(hd),.rsp_valid(hrv),.rsp_ready(hrr),.rsp_data(hrd),.rsp_error(hre),.s_req(s_req),.s_we(s_we),.s_addr(s_addr),.s_din(s_din),.s_rsp_ready(helper_take),.s_ready(s_ready),.s_rsp_valid(s_valid&&allow_s_ack),.s_dout(s_dout));
 block_feed_s16k u_s(.clk(clk),.reset(reset),.req(s_req),.wr(s_we),.addr(s_addr),.din(s_din),.ready(s_ready),.valid(s_valid),.take(s_take),.dout(s_dout),.wide_req(1'b0),.wide_addr(8'd0),.wide_ready(),.wide_valid(),.wide_take(1'b1),.wide_dout());
 localparam [127:0] POISON=128'hdeadbeef0123456789abcdeffeedface;
 integer cycles=0,cases=0,ci=0,reads=0,writes=0,acks=0,commands=0,responses=0,completions=0;
 integer r0,w0,a0,c0,p0,d0,mem_index=0,cmd_index=0;
 reg pending=0,pending_write;reg [127:0] pending_data;reg [9:0] pending_addr;
 reg hold_cmd=0,hold_mem=0,hold_rsp=0,hold_native=0,hold_s=0;
 reg [127:0] old_cd,old_ca,old_md,old_rd,old_sd;reg [3:0] old_op,old_count;reg [31:0] old_param;reg [9:0] old_addr;
 reg old_mw,old_error,old_sat,old_ne,old_ns;
 function automatic [127:0] ram;
  input integer addr;begin case(addr%4)
   0:ram=u_s.bank0[addr/4];1:ram=u_s.bank1[addr/4];2:ram=u_s.bank2[addr/4];3:ram=u_s.bank3[addr/4];
  endcase end
 endfunction
 function automatic integer expected_op;
  input integer index;integer words;begin words=n_words(ci);
   if(index==0)expected_op=0;else if(index<=words)expected_op=1;else if(index==words+1)expected_op=2;
   else if(n_mode(ci)!=0)expected_op=5;
   else if(index<=2*words+1)expected_op=3;else if(index==2*words+2)expected_op=4;else expected_op=6;
  end
 endfunction
 function automatic integer expected_mem_addr;
  input integer index;integer w,k,t;begin w=n_words(ci);
   if(index<w)expected_mem_addr=100+index;
   else if(n_mode(ci)!=0)begin t=index-w;k=t/3;case(t%3)0:expected_mem_addr=100+k;1:expected_mem_addr=200+k;2:expected_mem_addr=400+k;endcase end
   else if(index<3*w)begin t=index-w;k=t/2;expected_mem_addr=(t%2==0?100:300)+k;end
   else begin t=index-3*w;k=t/2;expected_mem_addr=(t%2==0?300:400)+k;end
  end
 endfunction
 function automatic expected_mem_write;
  input integer index;integer w;begin w=n_words(ci);if(index<w)expected_mem_write=0;
   else if(n_mode(ci)!=0)expected_mem_write=((index-w)%3==2);
   else if(index<3*w)expected_mem_write=((index-w)%2==1);else expected_mem_write=((index-3*w)%2==1);
  end
 endfunction
 always @(posedge clk)begin
  cycles=cycles+1;if(cycles>800000)$fatal(1,"FAIL_W4_N watchdog");
  if(reset)begin pending=0;hold_cmd=0;hold_mem=0;hold_rsp=0;hold_native=0;hold_s=0;end else begin
   if(hold_cmd&&(!cv||cop!==old_op||ccount!==old_count||cp!==old_param||cd!==old_cd||ca!==old_ca))$fatal(1,"FAIL_W4_N command changed under stall");
   if(hold_mem&&(!mv||ma!==old_addr||md!==old_md||mw!==old_mw))$fatal(1,"FAIL_W4_N mem request changed under stall");
   if(hold_rsp&&(!rsp_valid||rsp_error!==old_error||rsp_saturated!==old_sat))$fatal(1,"FAIL_W4_N completion changed under stall");
   if(hold_native&&(!rv||rd!==old_rd||re!==old_ne||rsat!==old_ns))$fatal(1,"FAIL_W4_N native response changed under stall");
   if(hold_s&&(!s_valid||s_dout!==old_sd))$fatal(1,"FAIL_W4_N S ACK changed under stall");
   hold_cmd=cv&&!cr;old_op=cop;old_count=ccount;old_param=cp;old_cd=cd;old_ca=ca;
   hold_mem=owner&&mv&&!mr;old_addr=ma;old_md=md;old_mw=mw;
   hold_rsp=rsp_valid&&!rsp_ready;old_error=rsp_error;old_sat=rsp_saturated;
   hold_native=rv&&!(rr&&allow_n_rsp);old_rd=rd;old_ne=re;old_ns=rsat;
   hold_s=s_valid&&!s_take;old_sd=s_dout;
   if(rsp_valid&&rsp_ready)completions=completions+1;
   if(s_req&&s_ready)begin
    if(pending)$fatal(1,"FAIL_W4_N multiple S owners");pending=1;pending_write=s_we;pending_data=s_din;pending_addr=s_addr;
    if(service_active)begin
     if(strict)begin
      if(s_addr!=expected_mem_addr(mem_index)||s_we!==expected_mem_write(mem_index))$fatal(1,"FAIL_W4_N mem sequence ci%0d step%0d got%0d wr%0d expected%0d",ci,mem_index,s_addr,s_we,expected_mem_addr(mem_index));
      if(s_we&&s_din!==(s_addr>=400?n_output(ci,s_addr-400):n_expword(ci,s_addr-300)))$fatal(1,"FAIL_W4_N write math mismatch ci%0d addr%0d got%032h",ci,s_addr,s_din);
     end
     mem_index=mem_index+1;if(s_we)writes=writes+1;else reads=reads+1;
    end
   end
   if(s_valid&&s_take)begin
    if(!pending)$fatal(1,"FAIL_W4_N response without request");
    if(pending_write&&s_dout!==pending_data)$fatal(1,"FAIL_W4_N write ACK echo");
    pending=0;if(service_active)acks=acks+1;
   end
   if(cv&&cr)begin
    if(strict)begin
     if(cop!=expected_op(cmd_index))$fatal(1,"FAIL_W4_N command phase ci%0d index%0d op%0d",ci,cmd_index,cop);
     if(cop==0&&(cp!==n_mode(ci)||cd[31:0]!==n_epsilon(ci)))$fatal(1,"FAIL_W4_N BEGIN captured params");
     if(cop==1||cop==3||cop==5||cop==6)begin
      if(ccount!=(n_count(ci)-8*u_ctrl.word_index>8?8:n_count(ci)-8*u_ctrl.word_index))$fatal(1,"FAIL_W4_N native count/tail");
      if(cd!==(cop==6?n_expword(ci,u_ctrl.word_index):n_raw(ci,u_ctrl.word_index)))$fatal(1,"FAIL_W4_N raw vs EXP/mask ci%0d op%0d word%0d got%032h",ci,cop,u_ctrl.word_index,cd);
      if(cop==5&&ca!==n_gamma(ci,u_ctrl.word_index))$fatal(1,"FAIL_W4_N gamma replay/mask");
     end
    end
    commands=commands+1;cmd_index=cmd_index+1;
   end
   if(rv&&rr&&allow_n_rsp)responses=responses+1;
   if(service_active&&strict&&rsp_valid&&!rsp_error&&(pending||acks-a0!=n_words(ci)*(n_mode(ci)==0?5:4)))$fatal(1,"FAIL_W4_N completion before all write ACKs");
  end
 end
 task automatic mark;input [8*100-1:0] name;begin cases=cases+1;$display("CASE_PASS %0s",name);end endtask
 task automatic store;input integer address;input [127:0] data;
  begin @(negedge clk);owner=0;host_addr=address;host_data=data;host_valid=1;host_rsp_ready=0;
   while(!hr)@(negedge clk);@(posedge clk);#1;@(negedge clk);host_valid=0;
   while(!hrv)@(negedge clk);if(hrd!==data||hre)$fatal(1,"FAIL_W4_N host store ACK");host_rsp_ready=1;@(posedge clk);#1;@(negedge clk);host_rsp_ready=0;
  end
 endtask
 task automatic prepare;input integer index;integer k;reg [127:0] raw,g;
  begin ci=index;service_active=0;strict=1;
   for(k=0;k<n_words(ci);k=k+1)begin
    raw=n_raw(ci,k);g=n_gamma(ci,k);
    // Nonzero inactive source/gamma lanes must be masked, not included.
    if(k==n_words(ci)-1&&n_count(ci)%8)begin raw=raw|(128'hffffffffffffffffffffffffffffffff<<(16*(n_count(ci)%8)));g=g|(128'h0123456789abcdeffedcba9876543210<<(16*(n_count(ci)%8)));end
    store(100+k,raw);store(200+k,g);store(300+k,POISON);store(400+k,POISON);
   end
   @(negedge clk);owner=1;service_active=1;r0=reads;w0=writes;a0=acks;c0=commands;p0=responses;d0=completions;mem_index=0;cmd_index=0;
  end
 endtask
 task automatic launch;
  begin @(negedge clk);req_mode=n_mode(ci);req_count=n_count(ci);req_epsilon=n_epsilon(ci);req_src_addr=100;req_gamma_addr=200;req_exp_addr=300;req_dst_addr=400;req_valid=1;rsp_ready=0;
   while(!req_ready)@(negedge clk);@(posedge clk);#1;@(negedge clk);req_valid=0;
   req_mode=3;req_count=0;req_epsilon=0;req_src_addr=999;req_gamma_addr=998;req_exp_addr=997;req_dst_addr=996;
  end
 endtask
 task automatic finish;input error_expected,poison_expected;integer k;
  begin while(!rsp_valid)@(negedge clk);
   repeat(5)begin if(!rsp_valid||rsp_error!==error_expected||req_ready||!busy)$fatal(1,"FAIL_W4_N held completion flags");if(!error_expected&&rsp_saturated!==n_sat(ci))$fatal(1,"FAIL_W4_N saturation OR");@(negedge clk);end
   if(!error_expected)begin
    if(reads-r0!=3*n_words(ci)||writes-w0!=(n_mode(ci)==0?2:1)*n_words(ci)||acks-a0!=(n_mode(ci)==0?5:4)*n_words(ci)||commands-c0!=(n_mode(ci)==0?3+3*n_words(ci):2+2*n_words(ci))||responses-p0!=commands-c0||pending)$fatal(1,"FAIL_W4_N conservation ci%0d R%0d W%0d ACK%0d C%0d P%0d",ci,reads-r0,writes-w0,acks-a0,commands-c0,responses-p0);
    for(k=0;k<n_words(ci);k=k+1)begin if(ram(400+k)!==n_output(ci,k))$fatal(1,"FAIL_W4_N stored output");if(n_mode(ci)==0&&ram(300+k)!==n_expword(ci,k))$fatal(1,"FAIL_W4_N exact EXP stored/replayed");end
   end
   rsp_ready=1;@(posedge clk);#1;@(negedge clk);rsp_ready=0;service_active=0;owner=0;repeat(3)@(negedge clk);
   if(completions!=d0+1||rsp_valid||req_ready===poison_expected||busy!==poison_expected)$fatal(1,"FAIL_W4_N completion/reuse/poison");
  end
 endtask
 task automatic hard_reset;
  begin @(negedge clk);reset=1;req_valid=0;host_valid=0;rsp_ready=0;host_rsp_ready=0;service_active=0;owner=0;corrupt_n=0;inject_mem_error=0;
   allow_mem_req=1;allow_mem_rsp=1;allow_s_ack=1;allow_n_cmd=1;allow_n_rsp=1;
   repeat(3)@(negedge clk);reset=0;repeat(3)@(negedge clk);if(rsp_valid||busy||!req_ready||s_valid||rv)$fatal(1,"FAIL_W4_N reset recovery");
  end
 endtask
 task automatic run;input integer index,stall;
  begin prepare(index);if(stall==1)allow_n_cmd=0;if(stall==2)allow_n_rsp=0;if(stall==4)allow_mem_req=0;
   launch();
   if(stall==1)begin while(!cv)@(negedge clk);repeat(5)@(negedge clk);if(commands!=c0)$fatal(1,"FAIL_W4_N command stall accepted");allow_n_cmd=1;end
   if(stall==2)begin while(!rv)@(negedge clk);repeat(5)@(negedge clk);if(responses!=p0||rsp_valid)$fatal(1,"FAIL_W4_N response stall retired");allow_n_rsp=1;end
   if(stall==3)begin wait(mv&&mw&&ma>=400);allow_s_ack=0;while(!s_valid)@(negedge clk);repeat(5)begin @(negedge clk);if(rsp_valid)$fatal(1,"FAIL_W4_N destination write before ACK");end allow_s_ack=1;end
   if(stall==4)begin repeat(5)@(negedge clk);allow_mem_req=1;allow_mem_rsp=0;while(!hrv)@(negedge clk);repeat(5)@(negedge clk);allow_mem_rsp=1;end
   finish(0,0);
  end
 endtask
 task automatic guard;input integer kind;
  begin prepare(0);strict=0;@(negedge clk);req_mode=1;req_count=8;req_epsilon=1;req_src_addr=100;req_gamma_addr=200;req_exp_addr=300;req_dst_addr=400;
   case(kind)0:req_count=0;1:req_count=258;2:req_mode=3;3:req_epsilon=0;4:req_src_addr=1023;5:req_dst_addr=100;6:req_dst_addr=200;7:begin req_mode=0;req_exp_addr=100;end endcase
   // kind4 requires two words to exceed S, not one legal word at1023.
   if(kind==4)req_count=9;
   req_valid=1;while(!req_ready)@(negedge clk);@(posedge clk);#1;@(negedge clk);req_valid=0;finish(1,0);
   if(reads!=r0||writes!=w0||commands!=c0)$fatal(1,"FAIL_W4_N guard touched native or S");
  end
 endtask
 integer i;
 initial begin
  repeat(4)@(negedge clk);reset=0;repeat(2)@(negedge clk);
  for(i=0;i<11;i=i+1)begin run(i,0);mark(case_name(i));end
  run(0,1);mark("W4_N_NATIVE_COMMAND_HOLD");run(5,2);mark("W4_N_NATIVE_RESPONSE_HOLD");run(7,3);mark("W4_N_DESTINATION_ACK_GATE_SOFTMAX257");run(4,4);mark("W4_N_HELPER_REQUEST_RESPONSE_HOLD");
  for(i=0;i<8;i=i+1)begin guard(i);mark(guard_name(i));end
  run(0,0);mark("W4_N_REUSE_AFTER_LOCAL_ADMISSION_ERRORS");
  // A real unsupported native operation: controller must close with poison,
  // never silently restart BEGIN or claim numerical output.
  prepare(0);strict=0;launch();wait(cv&&cop==1);@(negedge clk);corrupt_n=1;@(posedge clk);#1;@(negedge clk);corrupt_n=0;finish(1,1);
  if(writes!=w0||ram(400)!==POISON)$fatal(1,"FAIL_W4_N native error wrote destination");
  hard_reset();run(5,0);mark("W4_N_NATIVE_ERROR_POISON_COORDINATED_RESET_RECOVER");
  prepare(0);strict=0;launch();wait(hrv&&owner);@(negedge clk);inject_mem_error=1;@(posedge clk);#1;@(negedge clk);inject_mem_error=0;finish(1,1);
  if(writes!=w0)$fatal(1,"FAIL_W4_N read error wrote destination");hard_reset();run(0,0);mark("W4_N_MEMORY_READ_ERROR_POISON_RESET_RECOVER");
  // Error on a later actual destination ACK: accepted writes stay visible.
  prepare(4);strict=0;launch();wait(mv&&mw&&ma==401);allow_mem_rsp=0;while(!hrv)@(negedge clk);@(negedge clk);inject_mem_error=1;allow_mem_rsp=1;@(posedge clk);#1;@(negedge clk);inject_mem_error=0;finish(1,1);
  if(writes-w0!=2||ram(400)!==n_output(4,0)||ram(401)!==n_output(4,1)||ram(402)!==POISON)$fatal(1,"FAIL_W4_N partial accepted writes rollback/overrun");
  hard_reset();run(8,0);mark("W4_N_LATE_WRITE_ERROR_PARTIAL_PREFIX_POISON_RESET");
  prepare(7);launch();wait(mv&&mw&&ma==300);allow_s_ack=0;while(!s_valid)@(negedge clk);repeat(4)@(negedge clk);hard_reset();run(0,0);mark("W4_N_RESET_PENDING_EXP_WRITE_ACK_RECOVER");
  prepare(0);allow_n_rsp=0;launch();while(!rv)@(negedge clk);repeat(4)@(negedge clk);hard_reset();run(6,0);mark("W4_N_RESET_HELD_NATIVE_RESPONSE_RECOVER");
  $display("PASS_W4_N cases=%0d cycles=%0d Sread=%0d Swrite=%0d Sack=%0d Ncmd=%0d Nrsp=%0d done=%0d",cases,cycles,reads,writes,acks,commands,responses,completions);$finish;
 end
'''


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--directory',type=Path,default=Path(__file__).resolve().parent);p=parser.parse_args().directory
    d=json.loads((p/'w4-n-vectors.json').read_text(encoding='utf-8'));v=d['vectors'];f=[]
    for name,bits,key,default in [('n_raw',128,'raw_words_hex','0'),('n_gamma',128,'gamma_words_hex','0'),('n_output',128,'output_words_hex','bad'),('n_expword',128,'exp_words_hex','0')]:
        f+=[' function automatic [127:0] '+name+';input integer vec,word;begin case(vec*64+word)']
        f+=['  {}:{}=128\'h{};'.format(x['index']*64+i,name,w) for x in v for i,w in enumerate(x['expected'].get(key,[]))]
        f+=['  default:'+name+"=128'h"+default+';endcase end endfunction']
    for name,key,bits in [('n_mode','mode',2),('n_count','count',16),('n_epsilon','epsilon',32),('n_words','words',8)]:
        f+=[' function automatic [{}:0] {};input integer vec;begin case(vec)'.format(bits-1,name)]
        f+=['  {}:{}={};'.format(x['index'],name,x[key]) for x in v];f+=['  default:'+name+'=0;endcase end endfunction']
    f+=[' function automatic n_sat;input integer vec;begin case(vec)']
    f+=['  {}:n_sat=1\'b{};'.format(x['index'],int(x['expected']['saturated'])) for x in v];f+=['  default:n_sat=0;endcase end endfunction']
    for name,items in [('case_name',[('W4_N_'+x['id'].upper()) for x in v]),('guard_name',['W4_N_GUARD_ZERO_COUNT','W4_N_GUARD_COUNT258','W4_N_GUARD_MODE3','W4_N_GUARD_ZERO_EPSILON','W4_N_GUARD_RANGE_END','W4_N_GUARD_SRC_DST_OVERLAP','W4_N_GUARD_GAMMA_DST_OVERLAP','W4_N_GUARD_SRC_EXP_OVERLAP'])]:
        f+=[' function automatic [8*100-1:0] '+name+';input integer index;begin case(index)']
        f+=['  {}:{}="{}";'.format(i,name,n) for i,n in enumerate(items)];f+=['  default:'+name+'="unknown";endcase end endfunction']
    # Native word index is derived from the accepted command sequence rather
    # than a controller state/array implementation.
    body=BODY.replace('u_ctrl.word_index','native_word_index(cmd_index)')
    f+=[' function automatic integer native_word_index;input integer ix;integer w;begin w=n_words(ci);if(ix>=1&&ix<=w)native_word_index=ix-1;else if(n_mode(ci)!=0)native_word_index=ix-w-2;else if(ix<=2*w+1)native_word_index=ix-w-2;else native_word_index=ix-2*w-3;end endfunction']
    (p/'block_w4_n_tb.sv').write_bytes(('`timescale 1ns/1ps\n// Independent generated math expectations, real leaf N/S/helper.\nmodule block_w4_n_tb;\n'+'\n'.join(f)+'\n'+body+'\nendmodule\n').encode('utf-8'))
    print('Prepared block_w4_n_tb:11 numeric,8 admission,10 protocol/error/reset markers; NOT SIMULATED')


if __name__=='__main__':main()
