// Port-observed M benchmark. No internal DUT counters or unbounded hardware FIFO.
#include "Vblock_v1_m.h"
#include "verilated.h"
#include <array>
#include <algorithm>
#include <cstdint>
#include <deque>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>
using U128=__uint128_t;
struct Beat { unsigned op,index; U128 data,expected=0; unsigned useful=0; };
struct Counts {
 uint64_t cycles=0,requests=0,replies=0,input_useful=0,input_container=0,output_container=0;
 uint64_t output_wait=0,producer_gap=0,operand=0,compute=0,control=0,dependency=0,drain=0,overlap=0;
};
static Vblock_v1_m d;
static uint64_t time_cycle=0;
static void ck(bool p,const char*s){if(!p)throw std::runtime_error(s);}
static void tick(){d.clk=0;d.eval();d.clk=1;d.eval();++time_cycle;}
static void put(U128 v){for(int i=0;i<4;++i){d.cmd_data[i]=uint32_t(v);v>>=32;}}
static U128 get(){U128 v=0;for(int i=3;i>=0;--i)v=(v<<32)|d.rsp_data[i];return v;}
static void reset(){d.reset=1;d.cmd_valid=0;d.rsp_ready=0;tick();tick();d.reset=0;d.eval();}
static Counts execute(const std::vector<Beat>&q,bool tagged,unsigned scenario){
 Counts s;size_t sent=0;std::deque<U128> expected;
 unsigned completions=0,descriptors=0;bool held=false;U128 held_data=0;
 while(sent<q.size()||s.replies<s.requests){
  ck(s.cycles<1000000,"benchmark timeout");
  d.clk=0;
  bool offer=sent<q.size()&&(scenario!=1||time_cycle%7<4);
  d.cmd_valid=offer;
  if(sent<q.size()){d.cmd_op=q[sent].op;d.cmd_index=q[sent].index;put(q[sent].data);}
  d.rsp_ready=scenario!=2||time_cycle%5!=0;d.eval();
  if(held)ck(d.rsp_valid&&get()==held_data&&!d.rsp_error&&!d.rsp_saturated,"unstable response");
  bool push=offer&&d.cmd_ready,pop=d.rsp_valid&&d.rsp_ready;
  // Exactly one cycle attribution, ordered by externally observed pressure.
  if(d.rsp_valid&&!d.rsp_ready)++s.output_wait;
  else if(sent<q.size()&&!offer)++s.producer_gap;
  else if(push){
   if(q[sent].op==0||q[sent].op==1||(q[sent].op>=7&&q[sent].op<=9))++s.operand;
   else if(q[sent].op==2||q[sent].op==10)++s.compute;
   else ++s.control;
  } else if(sent<q.size())++s.dependency;else ++s.drain;
  if(pop){
   ck(!d.rsp_error&&!d.rsp_saturated,"unexpected response flag");
   if(tagged){
    if(get()==(U128(1)<<127))++completions;
    else ck(get()==0,"invalid loader acknowledgement");
   }else{ck(!expected.empty(),"response without request");ck(get()==expected.front(),"numerical mismatch");expected.pop_front();}
   ++s.replies;s.output_container+=16;
  }
  if(push){
   if(!tagged)expected.push_back(q[sent].expected);
   if(q[sent].op==10)++descriptors;
   s.input_useful+=q[sent].useful;s.input_container+=16;++s.requests;++sent;
  }
  if(push&&pop)++s.overlap;
  held=d.rsp_valid&&!d.rsp_ready;held_data=get();tick();++s.cycles;
 }
 ck(expected.empty()&&(!tagged||completions==descriptors),"unfinished work");
 ck(s.output_wait+s.producer_gap+s.operand+s.compute+s.control+s.dependency+s.drain==s.cycles,"cycle attribution mismatch");
 d.cmd_valid=0;d.rsp_ready=0;d.eval();return s;
}
static int a(unsigned j,bool wide){return (j%2?-1:1)*int(j+1)*(wide?1234:1);}
static int b(unsigned r,unsigned j,bool wide){return int(r+1)*(int(j%3)-1)*(wide?257:1);}
static U128 pack_a(bool wide,bool packed){
 U128 v=0;for(unsigned j=0;j<8;++j)v|=packed&&!wide?U128(uint8_t(a(j,wide)))<<(8*j):U128(uint16_t(a(j,wide)))<<(16*j);return v;
}
static void loads(std::vector<Beat>&q,bool packed,unsigned bank,unsigned tiles,bool wa,bool wb){
 for(unsigned t=0;t<tiles;++t){
  if(packed){
   unsigned base=bank*32+t*8;q.push_back({7,base+unsigned(wa),pack_a(wa,true),0,wa?16u:8u});
   for(unsigned c=0;c<(wb?8u:4u);++c){
    U128 v=0;
    for(unsigned j=0;j<(wb?8u:16u);++j)v|=wb?U128(uint16_t(b(c,j,true)))<<(16*j):U128(uint8_t(b(2*c+j/8,j%8,false)))<<(8*j);
    q.push_back({wb?9u:8u,base+c,v,0,16});
   }
  }else{
   q.push_back({0,0,pack_a(wa,false),0,wa?16u:8u});
   for(unsigned r=0;r<8;++r){U128 v=0;for(unsigned j=0;j<8;++j)v|=U128(uint16_t(b(r,j,wb)))<<(16*j);q.push_back({1,r,v,0,wb?16u:8u});}
  }
 }
}
static U128 descriptor(bool wa,bool wb,bool clear){return U128(wa)|(U128(wb)<<1)|(U128(clear)<<2)|(U128(8)<<4)|(U128(8)<<8)|(U128(4)<<12);}
static void emit(const Counts&s){
 std::cout<<"{\"cycles\":"<<s.cycles<<",\"accepted_commands\":"<<s.requests<<",\"retired_responses\":"<<s.replies
 <<",\"operand_effective_bytes\":"<<s.input_useful<<",\"command_container_bytes\":"<<s.input_container<<",\"response_container_bytes\":"<<s.output_container
 <<",\"cycle_attribution\":{\"output_backpressure\":"<<s.output_wait<<",\"producer_gap\":"<<s.producer_gap
 <<",\"accepted_operand\":"<<s.operand<<",\"accepted_compute\":"<<s.compute<<",\"accepted_control\":"<<s.control
 <<",\"dependency_wait\":"<<s.dependency<<",\"drain\":"<<s.drain<<"},\"simultaneous_request_response_cycles\":"<<s.overlap<<"}";
}
int main(int argc,char**argv){try{
 Verilated::commandArgs(argc,argv);ck(argc>=2,"need layout");bool packed=std::string(argv[1])=="packed";
 std::cout<<"{\"passed\":true,\"counting_scope\":\"port handshakes; cycle buckets exclusive; no internal issue utilization claim\",\"cases\":[";
 bool first=true;
 for(unsigned format=0;format<4;++format)for(unsigned scenario=0;scenario<4;++scenario){
  bool wa=format&1,wb=format&2,resident=scenario==0;unsigned stimulus=scenario==2?1:scenario==3?2:0;
  reset();std::vector<Beat> pre,work,last;
  if(resident)loads(pre,packed,0,packed?4:1,wa,wb);
  for(unsigned t=0;t<(packed?32u:128u);++t){
   if(!resident)loads(work,packed,t%2,packed?4:1,wa,wb);
   if(packed)work.push_back({10,resident?0u:(t%2)*32,descriptor(wa,wb,t==0)});
   else work.push_back({2,0,U128(wa)|(U128(wb)<<1)|(U128(t==0)<<2)|(U128(8)<<4)|(U128(8)<<8)});
  }
  std::array<int64_t,8> answer{};for(unsigned r=0;r<8;++r)for(unsigned j=0;j<8;++j)answer[r]+=int64_t(a(j,wa))*b(r,j,wb)*128;
  for(unsigned g=0;g<4;++g)last.push_back({3,g,0,U128(uint64_t(answer[2*g]))|(U128(uint64_t(answer[2*g+1]))<<64)});
  last.push_back({4,0,U128(1)|(U128(1)<<39)});
  // Shift8 avoids saturating any of the four formats; these data are exact
  // multiples of128, so implement independent arithmetic ties-to-even.
  for(unsigned g=0;g<2;++g){
   U128 value=0;for(unsigned j=0;j<4;++j){
    int64_t x=answer[4*g+j],quo=x>>8;uint64_t rem=uint64_t(x)&255;
    quo+=rem>128||(rem==128&&(quo&1));ck(quo>=INT32_MIN&&quo<=INT32_MAX,"oracle overflow");
    value|=U128(uint32_t(quo))<<(32*j);
   }
   last.push_back({5,g,U128(8)|(U128(2)<<8),value});
  }
  auto p=execute(pre,false,0),w=execute(work,packed,stimulus),f=execute(last,false,stimulus);
  if(!first)std::cout<<",";first=false;
  std::cout<<"{\"format_a_bits\":"<<(wa?16:8)<<",\"format_b_bits\":"<<(wb?16:8)<<",\"scenario\":\""
   <<(resident?"resident_reuse":scenario==1?"continuous_supply":scenario==2?"producer_gaps":"downstream_backpressure")
   <<"\",\"logical_k\":1024,\"logical_n\":8,\"logical_macs\":8192,\"base_s8_products_per_logical_mac\":"<<(wa?3:1)*(wb?3:1)
   <<",\"final_effective_output_bytes\":32,\"charged_partial_verification_bytes\":64,\"reset_cycles_outside_window\":2,\"preload\":";
  emit(p);std::cout<<",\"work\":";emit(w);std::cout<<",\"finalization_and_readback\":";emit(f);
  std::cout<<",\"total_cycles\":"<<p.cycles+w.cycles+f.cycles<<",\"resident_work_excludes_preload_but_total_includes_it\":true}";
 }
 std::cout<<"]}\n";return 0;
}catch(const std::exception&e){std::cerr<<e.what()<<" at "<<time_cycle<<"\n";return 1;}}

