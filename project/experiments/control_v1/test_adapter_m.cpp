#include "Vcontrol_adapter_m.h"
#include "verilated.h"
#include <array>
#include <random>
#include <iostream>
#include <cstdlib>
static unsigned checks=0,cycles=0;
static void need(bool b,const char*m){++checks;if(!b){std::cerr<<m<<" cycle "<<cycles<<"\n";std::exit(1);}}
int main(int argc,char**argv){Verilated::commandArgs(argc,argv);Vcontrol_adapter_m v;std::mt19937 rng{162};
 bool cp=false,sp=false;unsigned cd=0,sd=0,sequence=0,writes=0,done=0;std::array<uint32_t,4> data{};uint64_t result=0;
 v.clk=0;v.task_valid=0;v.complete_ready=0;v.cmd_ready=0;v.rsp_valid=0;v.rsp_error=0;v.rsp_saturated=0;v.s_ready=0;v.s_valid=0;
 for(unsigned n=0;n<4;++n)v.rsp_data[n]=0;for(unsigned n=0;n<8;++n)v.task_data[n]=0;
 v.reset=1;for(unsigned n=0;n<4;++n){v.clk=0;v.eval();v.clk=1;v.eval();}v.reset=0;
 auto tick=[&](){v.clk=0;v.complete_ready=rng()%4!=0;v.cmd_ready=!cp&&rng()%3!=0;v.rsp_valid=cp&&!cd;v.s_ready=!sp&&rng()%3!=0;v.s_valid=sp&&!sd;
  for(unsigned n=0;n<4;++n)v.rsp_data[n]=data[n];v.eval();
  if(v.complete_valid&&v.complete_ready){result=v.complete_data;++done;}
  if(cp&&cd)--cd;if(v.rsp_valid&&v.rsp_ready)cp=false;
  if(sp&&sd)--sd;if(v.s_valid&&v.s_take)sp=false;
  if(v.cmd_valid&&v.cmd_ready){need(!cp,"single native command");++sequence;for(unsigned n=0;n<4;++n)data[n]=0x12340000u|uint32_t(v.cmd_index)<<4|n;cp=true;cd=2+rng()%5;}
  if(v.s_req&&v.s_ready){need(v.s_wr,"M only writes S");need(v.s_addr==32+writes,"sequential result addresses");for(unsigned n=0;n<4;++n)need(v.s_din[n]==data[n],"native response retained until S");++writes;sp=true;sd=2+rng()%6;}
  v.clk=1;v.eval();++cycles;};
 auto task=[&](std::array<uint32_t,8>d){unsigned target=done+1;for(unsigned n=0;n<8;++n)v.task_data[n]=d[n];v.task_valid=1;v.clk=0;v.eval();unsigned guard=0;
  while(!v.task_ready){tick();need(++guard<10000,"M ready");}tick();v.task_valid=0;while(done<target){tick();need(++guard<10000,"M completion");}return result;};
 need(((task({{0x370100,0x41884,0,1,0,0,0,0}})>>20)&15)==0,"scale and execute");need(sequence==2,"two native commands");
 const auto c=task({{0x380102,8,0,0,0,512,512,0}});need(((c>>20)&15)==0 && (c>>32)==256,"complete eight row drain");need(writes==16 && sequence==18,"finite two-word per row drain");
 need(((task({{0x390102,8,1,0,0,512,512,0}})>>20)&15)==2,"row overflow rejected");
 for(unsigned n=0;n<20;++n)tick();need(!sp&&!cp,"native and S drained");std::cout<<"{\"passed\":true,\"checks\":"<<checks<<",\"cycles\":"<<cycles<<"}\n";
}
