#include "Vcontrol_adapter_s.h"
#include "verilated.h"
#include <array>
#include <random>
#include <iostream>
#include <cstdlib>
static unsigned checks=0,cycles=0;
static void need(bool b,const char*m){++checks;if(!b){std::cerr<<m<<" cycle "<<cycles<<"\n";std::exit(1);}}
using A=std::array<uint32_t,5>;using B=std::array<uint32_t,17>;
template<class P,class V>static void drive(V&v,const P&p){for(unsigned i=0;i<p.size();++i)v[i]=p[i];}
template<class P,class V>static bool same(const V&v,const P&p){for(unsigned i=0;i<p.size();++i)if(v[i]!=p[i])return false;return true;}
int main(int argc,char**argv){
 Verilated::commandArgs(argc,argv);Vcontrol_adapter_s v;std::mt19937 rng{162};
 v.clk=0;v.task_valid=0;v.complete_ready=0;v.load_ready=0;v.done_valid=0;v.done_error=0;
 v.s_a_valid=0;v.s_b_valid=0;v.m_a_ready=0;v.m_b_ready=0;
 for(unsigned i=0;i<8;++i)v.task_data[i]=0;
 for(unsigned i=0;i<5;++i)v.s_a_packet[i]=0;for(unsigned i=0;i<17;++i)v.s_b_packet[i]=0;
 auto reset=[&](){v.reset=1;for(unsigned i=0;i<4;++i){v.clk=0;v.eval();v.clk=1;v.eval();++cycles;}
  v.clk=0;v.eval();need(!v.m_a_valid&&!v.m_b_valid&&!v.complete_valid,"reset flushes finite handoff");v.reset=0;};
 reset();unsigned completed=0,loads=0,packets=0;
 for(unsigned trial=0;trial<160;++trial){
  bool invalid=trial%11==0,error=trial%7==0,pending=false,done_ack=false;unsigned drain_delay=0,as=0,bs=0,ar=0,br=0;
  std::array<A,8> aa;std::array<B,2> bb;
  for(auto&p:aa){for(auto&x:p)x=rng();p[4]&=127;}
  for(auto&p:bb){for(auto&x:p)x=rng();p[16]&=31;}
  std::array<uint32_t,8> task{{((trial+1)<<16)|0x0500u,(invalid?9u:8u)|(1<<4),0,128,0,0,1,0}};
  drive(v.task_data,task);v.task_valid=1;bool submitted=false,finished=false;
  bool held_a=false,held_b=false;A old_a{};B old_b{};
  for(unsigned guard=0;guard<3000 && !finished;++guard){
   v.clk=0;v.complete_ready=rng()%4!=0;v.load_ready=!pending&&!done_ack&&rng()%4!=0;
   v.s_a_valid=pending&&as<8;v.s_b_valid=pending&&bs<2;
   if(as<8)drive(v.s_a_packet,aa[as]);if(bs<2)drive(v.s_b_packet,bb[bs]);
   v.done_valid=pending&&as==8&&bs==2;v.done_error=error;
   bool stall_last_a=as==8&&(!done_ack||drain_delay<6);
   bool stall_last_b=bs==2&&(!done_ack||drain_delay<6);
   v.m_a_ready=!stall_last_a&&rng()%3!=0;v.m_b_ready=!stall_last_b&&rng()%3!=0;v.eval();
   if(held_a)need(v.m_a_valid&&same(v.m_a_packet,old_a),"A packet stable under backpressure");
   if(held_b)need(v.m_b_valid&&same(v.m_b_packet,old_b),"B packet stable under backpressure");
   bool ra=v.s_a_ready,rb=v.s_b_ready,ma=v.m_a_ready,mb=v.m_b_ready;
   v.m_a_ready=!ma;v.m_b_ready=!mb;v.eval();need(v.s_a_ready==ra&&v.s_b_ready==rb,"registered handoff breaks M ready to S ready path");
   v.m_a_ready=ma;v.m_b_ready=mb;v.eval();
   held_a=v.m_a_valid&&!v.m_a_ready;held_b=v.m_b_valid&&!v.m_b_ready;
   if(held_a)for(unsigned i=0;i<5;++i)old_a[i]=v.m_a_packet[i];
   if(held_b)for(unsigned i=0;i<17;++i)old_b[i]=v.m_b_packet[i];
   bool task_fire=v.task_valid&&v.task_ready;
   if(v.m_a_valid&&v.m_a_ready){need(ar<as&&same(v.m_a_packet,aa[ar]),"A data and metadata consumed exactly once");++ar;++packets;}
   if(v.m_b_valid&&v.m_b_ready){need(br<bs&&same(v.m_b_packet,bb[br]),"B data and metadata consumed exactly once");++br;++packets;}
   if(v.s_a_valid&&v.s_a_ready)++as;if(v.s_b_valid&&v.s_b_ready)++bs;
   if(v.load_valid&&v.load_ready){need(!invalid&&!pending,"one real feeder launch");need(v.load_rows==8&&v.load_tiles==1&&v.load_bank==1&&v.load_a_base==0&&v.load_b_base==8,"native descriptor fields");pending=true;++loads;}
   if(v.done_valid&&v.done_take){need(as==8&&bs==2,"native done follows real feeder acceptance");pending=false;done_ack=true;}
   if(done_ack)++drain_delay;
   if(v.complete_valid){
    need(invalid||(done_ack&&ar==8&&br==2),"completion waits for actual M consumption");
    need((v.complete_data&0xffff)==trial+1,"tag preserved");
    need(((v.complete_data>>20)&15)==(invalid?2u:error?4u:0u),"completion status preserved");
    if(v.complete_ready){finished=true;++completed;}
   }
   v.clk=1;v.eval();++cycles;if(task_fire){submitted=true;v.task_valid=0;}
  }
  need(submitted&&finished,"bounded task completion");
 }
 need(completed==160&&loads==145&&packets==1450,"finite transfer scoreboard totals");
 v.task_valid=1;drive(v.task_data,std::array<uint32_t,8>{{0x550500,24,0,128,0,0,1,0}});
 v.clk=0;v.eval();need(v.task_ready,"restart ready");v.clk=1;v.eval();v.task_valid=0;
 v.load_ready=1;v.clk=0;v.eval();v.clk=1;v.eval();
 v.s_a_valid=1;v.s_b_valid=1;v.m_a_ready=0;v.m_b_ready=0;v.clk=0;v.eval();v.clk=1;v.eval();
 reset();v.s_a_valid=0;v.s_b_valid=0;v.done_valid=0;v.clk=0;v.eval();need(v.task_ready,"reset releases task owner");
 std::cout<<"{\"passed\":true,\"checks\":"<<checks<<",\"cycles\":"<<cycles<<",\"operand_packets\":"<<packets<<"}\n";
}
