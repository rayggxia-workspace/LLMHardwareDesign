#include "Vcontrol_adapter_s.h"
#include "verilated.h"
#include <array>
#include <random>
#include <iostream>
#include <cstdlib>
static unsigned checks=0,cycles=0;
static void need(bool b,const char*m){++checks;if(!b){std::cerr<<m<<" cycle "<<cycles<<"\n";std::exit(1);}}
int main(int argc,char**argv){Verilated::commandArgs(argc,argv);Vcontrol_adapter_s v;std::mt19937 rng{162};bool pending=false;unsigned delay=0,done=0,loads=0;uint64_t result=0;
 v.clk=0;v.task_valid=0;v.complete_ready=0;v.load_ready=0;v.done_valid=0;v.done_error=0;for(unsigned n=0;n<8;++n)v.task_data[n]=0;v.reset=1;
 for(unsigned n=0;n<4;++n){v.clk=0;v.eval();v.clk=1;v.eval();}v.reset=0;
 auto tick=[&](){v.clk=0;v.complete_ready=rng()%4!=0;v.load_ready=!pending && rng()%4!=0;v.done_valid=pending&&!delay;v.eval();
  if(v.complete_valid&&v.complete_ready){result=v.complete_data;++done;}if(pending&&delay)--delay;if(v.done_valid&&v.done_take)pending=false;
  if(v.load_valid&&v.load_ready){need(v.load_rows==8 && v.load_tiles==1 && v.load_a_base==0 && v.load_b_base==8 && v.load_bank==1,"real feeder fields");pending=true;delay=20+rng()%20;++loads;}
  v.clk=1;v.eval();++cycles;};
 auto task=[&](unsigned rows){std::array<uint32_t,8>d{{0x370500,rows|(1<<4),0,128,0,0,1,0}};unsigned target=done+1;for(unsigned n=0;n<8;++n)v.task_data[n]=d[n];v.task_valid=1;v.clk=0;v.eval();unsigned guard=0;
  while(!v.task_ready){tick();need(++guard<1000,"S ready");}tick();v.task_valid=0;while(done<target){tick();need(++guard<1000,"S native completion");}return result;};
 for(unsigned n=0;n<20;++n)need(((task(8)>>20)&15)==0,"feeder completes");need(loads==20,"one feeder launch per task");need(((task(9)>>20)&15)==2,"invalid dimensions rejected");
 std::cout<<"{\"passed\":true,\"checks\":"<<checks<<",\"cycles\":"<<cycles<<"}\n";
}
