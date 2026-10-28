// Port-observed M benchmark. No internal DUT counters or unbounded hardware FIFO.
#include "Vblock_v1_m.h"
#include "Vblock_v1_m___024root.h"
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
 uint64_t product_cycles=0,reduce_cycles=0,accumulate_cycles=0,arithmetic_union=0,valid_digit_products=0;
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
  auto*r=d.rootp;unsigned state=r->block_v1_m__DOT__state;
  bool product=state==1,reduction=state==2,accumulation=state==3;
  unsigned valid_k=r->block_v1_m__DOT__active_k;
#ifdef BENCH_REVISED
  if(state==8||state==9){
   product=state==8;reduction=r->block_v1_m__DOT__product_valid;accumulation=r->block_v1_m__DOT__reduce_valid;
   valid_k=r->block_v1_m__DOT__issue_tile+1<r->block_v1_m__DOT__tile_count?8:r->block_v1_m__DOT__last_k;
  }
#endif
  s.product_cycles+=product;s.reduce_cycles+=reduction;s.accumulate_cycles+=accumulation;
  s.arithmetic_union+=product||reduction||accumulation;
  if(product)s.valid_digit_products+=valid_k*r->block_v1_m__DOT__active_n;
  if(held)ck(d.rsp_valid&&get()==held_data&&!d.rsp_error&&!d.rsp_saturated,"unstable response");
  bool push=offer&&d.cmd_ready,pop=d.rsp_valid&&d.rsp_ready;
  // Exactly one cycle attribution, ordered by externally observed pressure.
  if(d.rsp_valid&&!d.rsp_ready)++s.output_wait;
  else if(sent<q.size()&&!offer&&d.cmd_ready)++s.producer_gap;
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
static void loads(std::vector<Beat>&q,bool packed,unsigned bank,unsigned tiles,bool wa,bool wb,unsigned last_k,unsigned n){
 for(unsigned t=0;t<tiles;++t){
  unsigned k=t+1==tiles?last_k:8;
  if(packed){
   unsigned base=bank*32+t*8;q.push_back({7,base+unsigned(wa),pack_a(wa,true),0,k*(wa?2u:1u)});
   for(unsigned c=0;c<(wb?n:(n+1)/2);++c){
    U128 v=0;
    for(unsigned j=0;j<(wb?8u:16u);++j)v|=wb?U128(uint16_t(b(c,j,true)))<<(16*j):U128(uint8_t(b(2*c+j/8,j%8,false)))<<(8*j);
    q.push_back({wb?9u:8u,base+c,v,0,wb?2*k:k*std::min(2u,n-2*c)});
   }
  }else{
   q.push_back({0,0,pack_a(wa,false),0,k*(wa?2u:1u)});
   for(unsigned r=0;r<n;++r){U128 v=0;for(unsigned j=0;j<8;++j)v|=U128(uint16_t(b(r,j,wb)))<<(16*j);q.push_back({1,r,v,0,k*(wb?2u:1u)});}
  }
 }
}
static U128 descriptor(bool wa,bool wb,bool clear,unsigned k,unsigned n,unsigned tiles){return U128(wa)|(U128(wb)<<1)|(U128(clear)<<2)|(U128(k)<<4)|(U128(n)<<8)|(U128(tiles)<<12);}
static void emit(const Counts&s){
 std::cout<<"{\"cycles\":"<<s.cycles<<",\"accepted_commands\":"<<s.requests<<",\"retired_responses\":"<<s.replies
 <<",\"operand_effective_bytes\":"<<s.input_useful<<",\"command_container_bytes\":"<<s.input_container<<",\"response_container_bytes\":"<<s.output_container
 <<",\"cycle_attribution\":{\"output_backpressure\":"<<s.output_wait<<",\"producer_gap\":"<<s.producer_gap
 <<",\"accepted_operand\":"<<s.operand<<",\"accepted_compute\":"<<s.compute<<",\"accepted_control\":"<<s.control
 <<",\"dependency_wait\":"<<s.dependency<<",\"drain\":"<<s.drain<<"},\"simultaneous_request_response_cycles\":"<<s.overlap
 <<",\"resource_occupancy_may_overlap\":{\"product_issue_cycles\":"<<s.product_cycles<<",\"reduction_cycles\":"<<s.reduce_cycles
 <<",\"accumulation_cycles\":"<<s.accumulate_cycles<<",\"arithmetic_union_cycles\":"<<s.arithmetic_union<<",\"valid_s8_digit_products\":"<<s.valid_digit_products<<"}}";
}
int main(int argc,char**argv){try{
 Verilated::commandArgs(argc,argv);ck(argc>=2,"need layout");bool packed=std::string(argv[1])=="packed";
 std::cout<<"{\"passed\":true,\"counting_scope\":\"port handshakes and sampled RTL stage/valid signals; exclusive primary cycle buckets; resource occupancies may overlap and must not be summed\",\"cases\":[";
 bool first=true;
 const std::array<std::array<unsigned,2>,4> shapes={{{512,8},{576,8},{1024,8},{1280,8}}};
 for(auto shape:shapes)for(unsigned format=0;format<4;++format)for(unsigned scenario=0;scenario<4;++scenario){
  unsigned k_total=shape[0],n=shape[1],tile_total=(k_total+7)/8;
  bool wa=format&1,wb=format&2,resident=scenario==0;unsigned stimulus=scenario==2?1:scenario==3?2:0;
  reset();std::vector<Beat> pre,work,last;
  if(resident)loads(pre,packed,0,packed?std::min(4u,tile_total):1,wa,wb,packed&&tile_total<=4?(k_total-1)%8+1:8,n);
  for(unsigned pos=0,sequence=0;pos<tile_total;++sequence){
   unsigned tiles=packed?std::min(4u,tile_total-pos):1;
   unsigned last_k=std::min(8u,k_total-8*(pos+tiles-1));
   if(!resident)loads(work,packed,sequence%2,tiles,wa,wb,last_k,n);
   if(packed)work.push_back({10,resident?0u:(sequence%2)*32,descriptor(wa,wb,pos==0,last_k,n,tiles)});
   else work.push_back({2,0,U128(wa)|(U128(wb)<<1)|(U128(pos==0)<<2)|(U128(last_k)<<4)|(U128(n)<<8)});
   pos+=tiles;
  }
  std::array<int64_t,8> answer{};for(unsigned r=0;r<n;++r)for(unsigned j=0;j<k_total;++j)answer[r]+=int64_t(a(j%8,wa))*b(r,j%8,wb);
  for(unsigned g=0;g<4;++g)last.push_back({3,g,0,U128(uint64_t(answer[2*g]))|(U128(uint64_t(answer[2*g+1]))<<64)});
  last.push_back({4,0,U128(1)|(U128(1)<<39)});
  // Shift8 avoids saturating any shape/format; independent signed RNE oracle.
  for(unsigned g=0;g<(n+3)/4;++g){
   U128 value=0;for(unsigned j=0;j<4;++j){
    int64_t x=answer[4*g+j],quo=x>>8;uint64_t rem=uint64_t(x)&255;
    quo+=rem>128||(rem==128&&(quo&1));ck(quo>=INT32_MIN&&quo<=INT32_MAX,"oracle overflow");
    value|=U128(uint32_t(quo))<<(32*j);
   }
   last.push_back({5,g,U128(8)|(U128(2)<<8),value});
  }
  auto p=execute(pre,false,0),w=execute(work,packed,stimulus),f=execute(last,false,stimulus);
  ck(w.valid_digit_products==uint64_t(k_total)*n*(wa?3:1)*(wb?3:1),"measured issue work differs from numeric operation");
  if(!first)std::cout<<",";first=false;
  std::cout<<"{\"format_a_bits\":"<<(wa?16:8)<<",\"format_b_bits\":"<<(wb?16:8)<<",\"scenario\":\""
   <<(resident?"resident_reuse":scenario==1?"continuous_supply":scenario==2?"producer_gaps":"downstream_backpressure")
   <<"\",\"logical_k\":"<<k_total<<",\"logical_n\":"<<n<<",\"logical_macs\":"<<uint64_t(k_total)*n<<",\"base_s8_products_per_logical_mac\":"<<(wa?3:1)*(wb?3:1)
   <<",\"final_effective_output_bytes\":"<<4*n<<",\"charged_partial_verification_container_bytes\":64,\"reset_cycles_outside_window\":2,\"preload\":";
  emit(p);std::cout<<",\"work\":";emit(w);std::cout<<",\"finalization_and_readback\":";emit(f);
  std::cout<<",\"total_cycles\":"<<p.cycles+w.cycles+f.cycles<<",\"resident_work_excludes_preload_but_total_includes_it\":true}";
 }
 std::cout<<"]}\n";return 0;
}catch(const std::exception&e){std::cerr<<e.what()<<" at "<<time_cycle<<"\n";return 1;}}
