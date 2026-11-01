#include "Vcontrol_adapter_t.h"
#include "verilated.h"
#include <array>
#include <random>
#include <iostream>
#include <cstdlib>
using Word=std::array<uint32_t,4>;
static unsigned checks=0,cycles=0;
static void need(bool b,const char*m){++checks;if(!b){std::cerr<<m<<" cycle "<<cycles<<"\n";std::exit(1);}}
int main(int argc,char**argv){Verilated::commandArgs(argc,argv);Vcontrol_adapter_t v;std::mt19937 rng{162};
 std::array<Word,1024> mem{};std::array<Word,384> payload{};unsigned state=0,size=0,received=0,cursor=0,done=0,sd=0,sa=0;bool sp=false;uint64_t result=0;
 for(unsigned w=0;w<33;++w)for(unsigned n=0;n<4;++n)mem[w][n]=w*16+n;
 v.clk=0;v.task_valid=0;v.complete_ready=0;for(unsigned n=0;n<8;++n)v.task_data[n]=0;v.begin_ready=0;v.write_ready=0;v.commit_ready=0;v.revoke_ready=0;
 v.read_valid=0;v.read_index=0;v.read_last=0;v.release_ready=0;v.t_busy=0;v.t_sealed=0;v.t_committed=0;v.t_error=0;v.s_ready=0;v.s_valid=0;
 for(unsigned n=0;n<4;++n){v.read_data[n]=0;v.s_dout[n]=0;}v.reset=1;for(unsigned n=0;n<4;++n){v.clk=0;v.eval();v.clk=1;v.eval();}v.reset=0;
 auto tick=[&](){v.clk=0;v.complete_ready=rng()%4!=0;v.s_ready=!sp&&rng()%3!=0;v.s_valid=sp&&!sd;
  if(v.s_valid)for(unsigned n=0;n<4;++n)v.s_dout[n]=mem[sa][n];
  v.begin_ready=state==0 && v.begin_words>0 && v.begin_words<=384;v.write_ready=state==1 && v.write_index==received && rng()%3!=0;
  v.commit_ready=state==2;v.revoke_ready=state==1||state==2;v.read_valid=state==3;v.read_index=cursor;v.read_last=state==3&&cursor+1==size;
  if(state==3)for(unsigned n=0;n<4;++n)v.read_data[n]=payload[cursor][n];v.release_ready=state==4;v.t_busy=state!=0;v.t_sealed=state==2;v.t_committed=state>=3;v.eval();
  if(v.complete_valid&&v.complete_ready){result=v.complete_data;++done;}
  if(sp&&sd)--sd;if(v.s_valid&&v.s_take)sp=false;
  if(v.s_req&&v.s_ready){need(!sp,"single S slot");sa=v.s_addr;if(v.s_wr)for(unsigned n=0;n<4;++n)mem[sa][n]=v.s_din[n];sp=true;sd=2+rng()%6;}
  if(v.begin_valid&&v.begin_ready){need(v.begin_owner==1&&v.begin_generation==42,"T owner and generation");size=v.begin_words;received=0;cursor=0;state=1;}
  if(v.write_valid&&v.write_ready){for(unsigned n=0;n<4;++n)payload[received][n]=v.write_data[n];if(++received==size)state=2;}
  if(v.commit_valid&&v.commit_ready)state=3;if(v.read_valid&&v.read_take){if(++cursor==size)state=4;}
  if(v.release_valid&&v.release_ready)state=0;if(v.revoke_valid&&v.revoke_ready)state=0;
  v.clk=1;v.eval();++cycles;};
 auto task=[&](unsigned op,unsigned words=0,unsigned address=0){std::array<uint32_t,8>d{{(55<<16)|0x600|op,words,address,0,0,0,op==0?1u:0u,op==0?42u:0u}};
  unsigned target=done+1;for(unsigned n=0;n<8;++n)v.task_data[n]=d[n];v.task_valid=1;v.clk=0;v.eval();unsigned guard=0;
  while(!v.task_ready){tick();need(++guard<10000,"T ready");}tick();v.task_valid=0;while(done<target){tick();need(++guard<10000,"T bounded completion");}return result;};
 need(((task(0,33)>>20)&15)==0,"begin");need(((task(1,33)>>20)&15)==0,"fill");need(received==33&&state==2,"all words sealed");need(((task(2)>>20)&15)==0,"commit");
 need(((task(4)>>20)&15)==2,"early release rejected without queue deadlock");need(((task(3,33,4096)>>20)&15)==0,"drain");
 for(unsigned w=0;w<33;++w)for(unsigned n=0;n<4;++n)need(mem[256+w][n]==mem[w][n],"T data held until actual S write ACK");need(state==4,"all committed words consumed");need(((task(4)>>20)&15)==0&&state==0,"release");
 need(((task(0,33)>>20)&15)==0,"second begin");need(((task(5)>>20)&15)==0&&state==0,"revoke provisional session");
 std::cout<<"{\"passed\":true,\"checks\":"<<checks<<",\"cycles\":"<<cycles<<"}\n";
}
