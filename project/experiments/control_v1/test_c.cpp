#include "Vcontrol_c.h"
#include "verilated.h"
#include <array>
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <random>
#include <vector>
static uint64_t checks=0,cycles=0;
static void need(bool x,const char* m){++checks;if(!x){std::cerr<<m<<" cycle "<<cycles<<"\n";std::exit(1);}}
static uint64_t ins(unsigned op,unsigned rd=0,unsigned ra=0,unsigned rb=0,unsigned flags=0,unsigned aux=0,uint32_t imm=0){
 return uint64_t(op)<<56|uint64_t(rd)<<52|uint64_t(ra)<<48|uint64_t(rb)<<44|uint64_t(flags)<<40|uint64_t(aux)<<32|imm;}
struct Sim {
 Vcontrol_c v;std::mt19937 rng{162};
 std::vector<std::array<uint32_t,8>> tasks;
 std::array<uint32_t,8> assembling{};unsigned word=0;
 bool random_ready=false,stall_seen=false;uint32_t held_data=0;unsigned held_ep=0,held_last=0;
 Sim(){v.clk=0;v.reset=1;v.cfg_valid=0;v.cfg_rsp_ready=1;v.cfg_write=0;v.cfg_addr=0;v.cfg_wdata=0;v.cfg_wstrb=15;
  v.task_ready=0;v.done_valid=0;v.done_data=0;v.done_last=0;for(int n=0;n<4;++n) tick();v.reset=0;tick();}
 void tick(){
  v.clk=0;if(random_ready)v.task_ready=(rng()%4)!=0;v.eval();
  if(!v.reset && stall_seen){need(v.task_valid,"task valid retained");need(v.task_data==held_data && v.task_endpoint==held_ep && v.task_last==held_last,"stalled task stable");}
  stall_seen=!v.reset && v.task_valid && !v.task_ready;
  if(stall_seen){held_data=v.task_data;held_ep=v.task_endpoint;held_last=v.task_last;}
  if(!v.reset && v.task_valid && v.task_ready){need(v.task_last==(word==7),"packet framing");need(v.task_endpoint==1,"M route");
   assembling[word++]=v.task_data;if(word==8){tasks.push_back(assembling);word=0;}}
  v.clk=1;v.eval();++cycles;
 }
 uint32_t cfg(bool write,unsigned a,uint32_t d=0,bool error=false){
  unsigned timeout=0;while(!v.cfg_ready){tick();need(++timeout<100,"cfg ready timeout");}
  v.cfg_valid=1;v.cfg_write=write;v.cfg_addr=a;v.cfg_wdata=d;tick();v.cfg_valid=0;
  while(!v.cfg_rsp_valid){tick();need(++timeout<100,"cfg reply timeout");}
  need(bool(v.cfg_error)==error,"cfg error value");const uint32_t result=v.cfg_rdata;tick();return result;
 }
 void load(const std::vector<uint64_t>& p){for(unsigned n=0;n<p.size();++n){cfg(true,0x1000+n*8,uint32_t(p[n]));cfg(true,0x1004+n*8,p[n]>>32);}}
 void complete(uint16_t tag,unsigned ep=1,unsigned status=0,uint32_t result=0){
  v.done_valid=1;v.done_last=0;v.done_data=tag|(ep<<16)|(status<<20);tick();
  v.done_last=1;v.done_data=result;tick();v.done_valid=0;v.done_last=0;tick();
 }
 void wait_end(){for(unsigned n=0;n<1000 && !v.ended && !v.fault;++n)tick();need(v.ended && v.fault==0,"program end");}
};
int main(int argc,char**argv){Verilated::commandArgs(argc,argv);{
 Sim s;need(s.cfg(false,0)==0x43310001,"version");
 s.load({ins(1,0,0,0,0,0,3),ins(1,1,0,0,0,0,7),ins(9,0,0),ins(2,2,2,1),ins(10),
  ins(7,1,0,0,0,255,0xfffffff0),ins(8,1,1,0,0,0,15),ins(18)});
 s.cfg(true,4,1);s.wait_end();need(s.cfg(false,0x48)==21,"loop arithmetic");
 need(s.cfg(false,0x88)==0xffffffff && s.cfg(false,0x8c)==255,"40bit address");
 s.load({ins(8,1,1,0,0,0,1)});s.cfg(true,4,1);for(unsigned n=0;n<20&&!s.v.fault;++n)s.tick();
 need(s.v.fault==2,"address overflow fault");s.cfg(true,4,2);need(s.v.fault==0,"idle fault reset");
 }
 {
 Sim s;s.cfg(true,0x2000,0x101);s.cfg(true,0x2004,64);
 s.load({ins(13,1,0,0,1,2),ins(14,2,1),ins(18)});s.cfg(true,4,1);
 for(unsigned n=0;n<50;++n)s.tick();need(s.v.task_valid,"backpressured task");
 s.cfg(true,0x1000,0,true); // rewriting running program forbidden
 s.random_ready=true;
 for(unsigned n=0;n<200 && s.tasks.empty();++n)s.tick();need(s.tasks.size()==1,"one task received");
 const auto t=s.tasks[0];need((t[0]&65535)==0x101 && t[1]==64,"task payload");
 for(unsigned n=2;n<8;++n)need(t[n]==0,"unwritten descriptor words zero");
 const uint16_t tag=t[0]>>16;s.complete(tag,1,0,99);s.wait_end();need(s.cfg(false,0x48)==99,"WAIT result");
 s.complete(tag);need(s.v.fault==3,"duplicate completion fault");s.cfg(true,4,2);
 need(!s.v.busy && !s.v.fault,"drained recovery");
 }
 {
 Sim s;s.cfg(true,0x2000,0x101);s.load({ins(1,0,0,0,0,0,33),ins(9,0,0),ins(13,1,0),ins(10),ins(15),ins(18)});
 s.random_ready=true;s.cfg(true,4,1);for(unsigned n=0;n<4000 && s.tasks.size()<32;++n)s.tick();
 need(s.tasks.size()==32,"all32 events issued");for(unsigned n=0;n<100;++n)s.tick();
 need(s.tasks.size()==32,"event overflow stalled");
 // Fault an accepted task, then drain all other outstanding completions.
 for(unsigned n=0;n<32;++n)s.complete(s.tasks[n][0]>>16,1,n==0?1:0);
 need(s.v.fault==4 && !s.v.busy,"remote error drains");s.cfg(true,4,2);need(s.v.fault==0,"fault cleanup");
 }
 {
 Sim s;s.cfg(true,0x2000,7<<8);s.load({ins(13),ins(18)});s.cfg(true,4,1);
 for(unsigned n=0;n<20&&!s.v.fault;++n)s.tick();need(s.v.fault==5,"R disabled");
 }
 std::cout<<"{\"passed\":true,\"checks\":"<<checks<<",\"cycles\":"<<cycles<<"}\n";return 0;
}
