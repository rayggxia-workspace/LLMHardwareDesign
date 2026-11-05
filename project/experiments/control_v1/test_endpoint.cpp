#include "Vcontrol_endpoint_queue.h"
#include "verilated.h"
#include <array>
#include <deque>
#include <random>
#include <iostream>
#include <cstdlib>
static unsigned checks=0;
static void need(bool b,const char*m){++checks;if(!b){std::cerr<<m<<"\n";std::exit(1);}}
int main(int argc,char**argv){
 Verilated::commandArgs(argc,argv);Vcontrol_endpoint_queue v;std::mt19937 rng(162);
 auto edge=[&](){v.clk=1;v.eval();v.clk=0;v.eval();};
 v.reset=1;v.cmd_valid=0;v.complete_valid=0;v.task_ready=0;v.done_ready=0;edge();edge();v.reset=0;v.eval();
 std::deque<std::array<uint32_t,8>> tasks;std::deque<uint64_t> completions;
 std::array<uint32_t,8> packet{};unsigned cw=0,dw=0;uint64_t assembled=0;
 unsigned sent=0,received=0,dsent=0,dreceived=0;
 for(unsigned cycle=0;cycle<20000;++cycle){
  v.cmd_valid=cycle<18000 && rng()%4!=0;v.cmd_data=sent*8+cw;v.cmd_last=cw==7;
  v.task_ready=rng()%4!=0;v.complete_valid=cycle<18000 && rng()%3!=0;
  v.complete_data=(uint64_t(dsent)<<32)|(dsent^0x12345678);v.done_ready=rng()%4!=0;v.eval();
  if(v.task_valid && v.task_ready){need(!tasks.empty(),"unsolicited task");for(unsigned k=0;k<8;++k)need(v.task_data[k]==tasks.front()[k],"task queue data");tasks.pop_front();++received;}
  if(v.done_valid && v.done_ready){need(!completions.empty(),"unsolicited done");need(v.done_last==(dw==1),"done framing");
   assembled|=uint64_t(v.done_data)<<(32*dw);if(++dw==2){need(assembled==completions.front(),"done queue data");completions.pop_front();dw=0;assembled=0;++dreceived;}}
  if(v.cmd_valid && v.cmd_ready){packet[cw]=v.cmd_data;if(++cw==8){tasks.push_back(packet);cw=0;++sent;}}
  if(v.complete_valid && v.complete_ready){completions.push_back(v.complete_data);++dsent;}
  edge();need(!v.protocol_error,"valid packet accepted");
  need(tasks.size()<=2 && completions.size()<=2,"finite queue capacities");
 }
 need(tasks.empty() && completions.empty() && sent==received && dsent==dreceived,"queues drained");
 // Early LAST is rejected, not silently turned into a valid task.
 v.task_ready=0;v.cmd_valid=1;v.cmd_last=1;v.eval();edge();need(v.protocol_error,"malformed frame rejected");
 std::cout<<"{\"passed\":true,\"checks\":"<<checks<<",\"tasks\":"<<received<<",\"completions\":"<<dreceived<<"}\n";
}
