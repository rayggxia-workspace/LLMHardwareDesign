#include "Vcontrol_dma_planner.h"
#include "verilated.h"
#include <array>
#include <random>
#include <iostream>
#include <cstdlib>
static unsigned checks=0,cycles=0;
static void need(bool b,const char*m){++checks;if(!b){std::cerr<<m<<" @"<<cycles<<"\n";std::exit(1);}}
using Desc=std::array<uint32_t,8>;
static Desc desc(uint64_t ext,unsigned loc,unsigned bytes,unsigned rows,unsigned estride,unsigned lstride,unsigned tag=55,bool write=false){
 return {{(tag<<16)|(write?1u:0u),uint32_t(ext),uint32_t(ext>>32)|(loc<<12),bytes,rows|(lstride<<16),estride,0,0}};}
struct Sim {
 Vcontrol_dma_planner v;
 Sim(){v.clk=0;v.reset=1;v.task_valid=0;v.burst_ready=0;v.ack_valid=0;v.ack_id=0;v.ack_error=0;v.complete_ready=0;
  for(auto&i:v.task_data)i=0;for(int n=0;n<3;++n)tick();v.reset=0;tick();}
 void tick(){v.clk=0;v.eval();v.clk=1;v.eval();v.clk=0;v.eval();++cycles;}
 void send(const Desc&d){need(v.task_ready,"descriptor ready");for(unsigned n=0;n<8;++n)v.task_data[n]=d[n];v.task_valid=1;tick();v.task_valid=0;}
};
int main(int argc,char**argv){Verilated::commandArgs(argc,argv);std::mt19937 rng(162);
 for(unsigned bytes: {1u,15u,16u,17u,255u,256u,257u,1024u,4096u})for(unsigned write=0;write<2;++write){
  Sim s;const unsigned stride=(bytes+15)&~15u;const uint64_t base=0x100000ff0ULL;
  s.send(desc(base,0,bytes,2,8192,stride,55,write));s.send(desc(base,0,bytes,2,8192,stride,56,write));
  need(!s.v.task_ready,"two descriptors bounded");
  std::array<bool,2> flight{{false,false}};unsigned words=0;bool stalled=false;uint64_t held_addr=0;unsigned held_id=0,held_beats=0;
  for(unsigned guard=0;guard<10000 && !s.v.complete_valid;++guard){
   s.v.burst_ready=(rng()%4)!=0;s.v.ack_valid=0;s.v.ack_error=0;
   const unsigned ack=rng()%2;if(flight[ack] && rng()%3==0){s.v.ack_valid=1;s.v.ack_id=ack;flight[ack]=false;}
   s.v.eval();
   if(stalled)need(s.v.burst_valid && s.v.burst_address==held_addr && s.v.burst_id==held_id && s.v.burst_beats==held_beats,"stable burst under ACK/backpressure");
   stalled=s.v.burst_valid&&!s.v.burst_ready;
   if(stalled){held_addr=s.v.burst_address;held_id=s.v.burst_id;held_beats=s.v.burst_beats;}
   if(s.v.burst_valid && s.v.burst_ready){
    const unsigned row=words/(stride/16),col=words%(stride/16);
    need(s.v.burst_address==base+row*8192+col*16,"external burst address");
    need(s.v.burst_local_word==row*stride/16+col,"S burst address");
    need(s.v.burst_write==write,"direction");
    need(s.v.burst_beats>0 && s.v.burst_beats<=16 && (s.v.burst_address&4095)+s.v.burst_beats*16<=4096,"AXI 4K/length");
    need(!flight[s.v.burst_id],"no slot reused");flight[s.v.burst_id]=true;
    const bool last=col+s.v.burst_beats==stride/16;
    const unsigned mask=last && bytes%16?((1u<<(bytes%16))-1):65535;
    need(s.v.burst_last_strobe==mask,"tail strobe");words+=s.v.burst_beats;
   }
   s.tick();need(s.v.reserved_words<=32,"payload credit bound");need(!s.v.protocol_error,"valid ACK accepted");
  }
  need(s.v.complete_valid && s.v.complete_data==(uint64_t(bytes*2)<<32|55),"successful completion");
  need(words==2*stride/16,"all padded words covered");
 }
 for(auto d:{desc((1ULL<<40)-16,0,17,1,0,0),desc(0,16368,17,1,0,0),desc(0,0,17,2,32,16),desc(0,0,1,0,0,0)}){
  Sim s;s.send(d);for(unsigned n=0;n<20&&!s.v.complete_valid;++n)s.tick();
  need(s.v.complete_valid && ((s.v.complete_data>>20)&15)==2 && !s.v.burst_valid,"descriptor invalid before side effects");
 }
 {
  Sim s;s.send(desc(0,0,512,1,0,0,9));s.v.burst_ready=1;
  unsigned seen=0;for(unsigned n=0;n<100&&seen<2;++n){s.v.eval();if(s.v.burst_valid)++seen;s.tick();}
  need(seen==2,"two independent outstanding");s.v.ack_valid=1;s.v.ack_id=0;s.v.ack_error=1;s.tick();s.v.ack_valid=0;
  for(unsigned n=0;n<10;++n)s.tick();need(!s.v.complete_valid,"error waits for other flight");
  s.v.ack_valid=1;s.v.ack_id=1;s.v.ack_error=0;s.tick();s.v.ack_valid=0;
  for(unsigned n=0;n<10&&!s.v.complete_valid;++n)s.tick();need(s.v.complete_valid && ((s.v.complete_data>>20)&15)==4,"drained error completion");
 }
 std::cout<<"{\"passed\":true,\"checks\":"<<checks<<",\"cycles\":"<<cycles<<"}\n";
}
