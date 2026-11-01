// Transport unit bench. Native arithmetic is separately tested in pair/system.
#include "verilated.h"
#if ROLE==3
#include "Vcontrol_adapter_e.h"
using Model=Vcontrol_adapter_e;
#elif ROLE==4
#include "Vcontrol_adapter_g.h"
using Model=Vcontrol_adapter_g;
#else
#include "Vcontrol_adapter_n.h"
using Model=Vcontrol_adapter_n;
#endif
#include <array>
#include <random>
#include <iostream>
#include <cstdlib>
using Word=std::array<uint32_t,4>;
static unsigned checks=0,cycles=0;
static void need(bool b,const char*m){++checks;if(!b){std::cerr<<m<<" cycle "<<cycles<<"\n";std::exit(1);}}
struct Sim{
 Model v;std::mt19937 rng{162};std::array<Word,1024> mem{};Word reply{};bool sp=false,cp=false;unsigned sd=0,cd=0,sa=0;uint64_t result=0;unsigned done=0,commands=0;
 Sim(){v.clk=0;v.task_valid=0;v.complete_ready=0;v.s_ready=0;v.s_valid=0;for(unsigned i=0;i<4;++i)v.s_dout[i]=0;for(unsigned i=0;i<8;++i)v.task_data[i]=0;
#if ROLE==2
  v.cmd_ready=0;v.rsp_valid=0;v.rsp_error=0;v.rsp_saturated=0;for(unsigned i=0;i<4;++i)v.rsp_data[i]=0;
#else
  v.in_ready=0;v.out_valid=0;v.out_error=0;v.out_saturated=0;
#if ROLE==4
  v.out_data=0;
#else
  for(unsigned i=0;i<4;++i)v.out_data[i]=0;
#endif
#endif
  v.reset=1;for(unsigned i=0;i<4;++i){v.clk=0;v.eval();v.clk=1;v.eval();}v.reset=0;v.clk=0;v.eval();}
 void tick(){v.clk=0;v.complete_ready=rng()%4!=0;v.s_ready=!sp && rng()%3!=0;v.s_valid=sp && !sd;
  if(v.s_valid)for(unsigned i=0;i<4;++i)v.s_dout[i]=mem[sa][i];
#if ROLE==2
  v.cmd_ready=!cp && rng()%4!=0;v.rsp_valid=cp && !cd;for(unsigned i=0;i<4;++i)v.rsp_data[i]=reply[i];
#else
  v.in_ready=!cp && rng()%4!=0;v.out_valid=cp && !cd;
#if ROLE==4
  v.out_data=reply[0];
#else
  for(unsigned i=0;i<4;++i)v.out_data[i]=reply[i];
#endif
#endif
  v.eval();if(v.complete_valid&&v.complete_ready){result=v.complete_data;++done;}
  if(sp && sd)--sd;if(v.s_valid&&v.s_take)sp=false;
  if(v.s_req&&v.s_ready){need(!sp,"one real S transaction");sa=v.s_addr;if(v.s_wr)for(unsigned i=0;i<4;++i)mem[sa][i]=v.s_din[i];sp=true;sd=1+rng()%5;}
  if(cp&&cd)--cd;
#if ROLE==2
  if(v.rsp_valid&&v.rsp_ready)cp=false;
  if(v.cmd_valid&&v.cmd_ready){for(unsigned i=0;i<4;++i)reply[i]=v.cmd_data[i];cp=true;cd=2+rng()%4;++commands;}
#else
  if(v.out_valid&&v.out_ready)cp=false;
  if(v.in_valid&&v.in_ready){
#if ROLE==4
   reply[0]=v.in_x;
#else
   for(unsigned i=0;i<4;++i)reply[i]=v.in_a[i];
#endif
   cp=true;cd=2+rng()%4;++commands;}
#endif
  v.clk=1;v.eval();++cycles;
 }
 uint64_t task(unsigned count,unsigned destination=4096){unsigned target=done+1;const std::array<uint32_t,8>d{{(55<<16)|(ROLE<<8)|(4<<12)|(ROLE==2?5:0),count,0,0,0,destination,0,0}};
  for(unsigned i=0;i<8;++i)v.task_data[i]=d[i];v.task_valid=1;v.eval();unsigned guard=0;while(!v.task_ready){tick();need(++guard<10000,"task ready");}tick();v.task_valid=0;
  while(done!=target){tick();need(++guard<10000,"task completion");}return result;
 }
};
int main(int argc,char**argv){Verilated::commandArgs(argc,argv);Sim s;
 for(unsigned w=0;w<3;++w)for(unsigned i=0;i<4;++i)s.mem[w][i]=0x12341234u+w*0x10001u+i*0x10001u;
 need(((s.task(17)>>20)&15)==0,"transport accepted");for(unsigned n=0;n<17;++n){auto a=s.mem[n/8][(n%8)/2],b=s.mem[256+n/8][(n%8)/2];need(((a>>(16*(n%2)))&65535)==((b>>(16*(n%2)))&65535),"all elements transferred");}
 for(unsigned n=17;n<24;++n)need(((s.mem[256+n/8][(n%8)/2]>>(16*(n%2)))&65535)==0,"tail zeroed");
 need(s.commands==(ROLE==4?9:3),"finite packet count");need(((s.task(16,16)>>20)&15)==2,"unsafe alias rejected");need(((s.task(8193)>>20)&15)==2,"capacity rejected");
 for(unsigned n=0;n<20;++n)s.tick();need(!s.sp&&!s.cp,"drained interfaces");std::cout<<"{\"passed\":true,\"checks\":"<<checks<<",\"cycles\":"<<cycles<<"}\n";
}
