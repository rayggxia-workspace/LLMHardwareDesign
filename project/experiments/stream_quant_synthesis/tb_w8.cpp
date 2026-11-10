#include "Vw8_dot_candidate.h"
#include "verilated.h"
#include <array>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <random>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>
#ifndef ABITS
#define ABITS 8
#endif
constexpr int AW=ABITS==8?32:40;
struct Packet {int ctx,first,last,k,n,offset;std::string a,b,result;};
std::vector<uint32_t> words(std::string s,int n){
 std::vector<uint32_t> v(n,0);int i=0;
 while(!s.empty()){
  const auto take=std::min<size_t>(8,s.size());
  if(i>=n)throw std::runtime_error("hex overflow");
  v[i++]=static_cast<uint32_t>(std::stoul(s.substr(s.size()-take),nullptr,16));s.resize(s.size()-take);
 }return v;
}
int main(int argc,char** argv){
 try{
  Verilated::commandArgs(argc,argv);if(argc!=2)throw std::runtime_error("vectors required");
  std::ifstream f(argv[1]);std::vector<Packet> packets;Packet p;
  while(f>>p.ctx>>p.first>>p.last>>p.k>>p.n>>p.offset>>p.a>>p.b>>p.result)packets.push_back(p);
  if(!f.eof()||packets.empty())throw std::runtime_error("bad vectors");
  Vw8_dot_candidate d;uint64_t ticks=0,outputs=0,acks=0;std::mt19937 rng(248);
  auto tick=[&](){d.clk=0;d.eval();d.clk=1;d.eval();++ticks;};
  d.reset=1;d.cmd_valid=0;d.dma_valid=0;d.out_ready=0;
  for(int i=0;i<3;++i)tick();d.reset=0;
  size_t issued=0,expected=0;int phase=0;bool holding_cmd=false,holding_dma=false;
  std::vector<uint32_t> held;int held_ctx=0,held_error=0;bool stalled=false;
  for(;ticks<2000000&&(issued<packets.size()||outputs<36);){
   d.clk=0;d.eval();d.out_ready=(rng()%5)!=0;
   if(issued<packets.size()){
    const auto& x=packets[issued];auto a=words(x.a,16*ABITS/32);auto b=words(x.b,32);
    if(phase==0){
     holding_cmd=holding_cmd||rng()%4!=0;d.cmd_valid=holding_cmd;d.dma_valid=0;
     d.cmd_ctx=x.ctx;d.cmd_first=x.first;d.cmd_last=x.last;d.cmd_k=x.k;d.cmd_n=x.n;d.cmd_offset=x.offset;
     for(size_t j=0;j<a.size();++j)d.cmd_a[j]=a[j];
    }else{
     d.cmd_valid=0;holding_dma=holding_dma||rng()%4!=0;d.dma_valid=holding_dma;
     for(int j=0;j<16;++j)d.dma_data[j]=b[(phase-1)*16+j];
    }
   }else{d.cmd_valid=0;d.dma_valid=0;}
   d.eval();
   if(stalled){
    if(!d.out_valid||int(d.out_ctx)!=held_ctx||int(d.out_error)!=held_error)throw std::runtime_error("stalled output metadata changed");
    for(size_t j=0;j<held.size();++j)if(d.out_data[j]!=held[j])throw std::runtime_error("stalled data changed");
   }
   stalled=d.out_valid&&!d.out_ready;
   if(stalled){held.assign(d.out_data.begin(),d.out_data.end());held_ctx=d.out_ctx;held_error=d.out_error;}
   if(d.out_valid&&d.out_ready){
    while(expected<packets.size()&&!packets[expected].last)++expected;
    if(expected==packets.size())throw std::runtime_error("unexpected response");
    const auto& x=packets[expected++];auto ref=words(x.result,8*AW/32);
    if(d.out_error||d.out_ctx!=x.ctx)throw std::runtime_error("response error/tag");
    for(size_t j=0;j<ref.size();++j)if(d.out_data[j]!=ref[j])throw std::runtime_error("integer mismatch");
    ++outputs;
   }
   const bool cmd=d.cmd_valid&&d.cmd_ready,dma=d.dma_valid&&d.dma_ready;
   if(d.fill_ack)++acks;
   tick();
   if(cmd){phase=1;holding_cmd=false;}
   if(dma){holding_dma=false;if(phase==2){phase=0;++issued;}else ++phase;}
  }
  if(issued!=packets.size()||outputs!=36||acks!=packets.size())throw std::runtime_error("missing completions/ACK");
  // Reset while an accepted B packet is only half filled. No stale response.
  d.cmd_valid=1;d.cmd_ctx=0;d.cmd_first=1;d.cmd_last=1;d.cmd_k=1;d.cmd_n=1;d.cmd_offset=0;
  d.dma_valid=0;d.out_ready=0;d.clk=0;d.eval();if(!d.cmd_ready)throw std::runtime_error("not drained");tick();
  d.cmd_valid=0;d.dma_valid=1;tick();d.dma_valid=0;d.reset=1;tick();d.reset=0;d.out_ready=1;
  for(int i=0;i<12;++i){tick();if(d.out_valid||d.fill_ack)throw std::runtime_error("stale reset response");}
  std::cout<<"W8_RTL_PASS abits="<<ABITS<<" packets="<<packets.size()<<" outputs="<<outputs<<" fill_ACK="<<acks<<" ticks="<<ticks<<"\n";
 }catch(const std::exception& e){std::cerr<<e.what()<<"\n";return 1;}
}
