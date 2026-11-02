#include "Vblock_feed_s16k_sram.h"
#include "verilated.h"
#include <array>
#include <deque>
#include <random>
#include <stdexcept>
#include <iostream>
using Word=std::array<uint32_t,4>;
using Wide=std::array<uint32_t,16>;
struct N {Word data;uint64_t due;};struct W {Wide data;uint64_t due;};
static Vblock_feed_s16k_sram* p;
#define d (*p)
static std::array<Word,1024> mem;
static std::deque<N> nq;static std::deque<W> wq;
static std::mt19937_64 rng(1431101);
static uint64_t cycles=0,checks=0,naccepted=0,waccepted=0,conflicts=0;
static void ck(bool ok,const char* s){++checks;if(!ok)throw std::runtime_error(s);}
static void check(){
 if(d.reset){ck(!d.valid&&!d.wide_valid&&!d.ready&&!d.wide_ready,"reset gates every handshake");return;}
 bool nv=!nq.empty()&&nq.front().due<=cycles;
 bool wv=!wq.empty()&&wq.front().due<=cycles;
 ck(bool(d.valid)==nv,"narrow response latency/order");
 ck(bool(d.wide_valid)==wv,"wide response latency/order");
 if(nv)for(unsigned j=0;j<4;++j)ck(d.dout[j]==nq.front().data[j],"narrow data/held response");
 if(wv)for(unsigned j=0;j<16;++j)ck(d.wide_dout[j]==wq.front().data[j],"wide data/held response");
}
static void step(){
 d.clk=0;d.eval();check();
 bool nf=d.req&&d.ready,wf=d.wide_req&&d.wide_ready;
 ck(!(nf&&wf),"1RW bank exclusion");
 if(d.reset){nq.clear();wq.clear();}
 else {
  if(d.valid&&d.take)nq.pop_front();
  if(d.wide_valid&&d.wide_take)wq.pop_front();
  if(wf){Wide v{};for(unsigned b=0;b<4;++b)for(unsigned j=0;j<4;++j)v[4*b+j]=mem[4*d.wide_addr+b][j];wq.push_back({v,cycles+2});++waccepted;}
  if(nf){if(d.wr)for(unsigned j=0;j<4;++j)mem[d.addr][j]=d.din[j];nq.push_back({mem[d.addr],cycles+2});++naccepted;}
  if(wf&&d.req)++conflicts;
  ck(nq.size()<=2&&wq.size()<=2,"finite response capacity including inflight");
 }
 d.clk=1;d.eval();++cycles;check();
 d.clk=0;d.eval();check(); // Actual falling-edge SRAM operation.
}
static void quiet(){d.req=0;d.wide_req=0;d.take=1;d.wide_take=1;}
static void drain(){quiet();for(unsigned i=0;(!nq.empty()||!wq.empty())&&i<20;++i)step();ck(nq.empty()&&wq.empty(),"drain");}
static void write(unsigned a){d.req=1;d.wr=1;d.addr=a;for(unsigned j=0;j<4;++j)d.din[j]=uint32_t(rng());d.eval();unsigned n=0;while(!d.ready){ck(++n<20,"write progress");step();}step();}
int main(int argc,char** argv){
 Verilated::commandArgs(argc,argv);p=new Vblock_feed_s16k_sram;
 try{
  quiet();d.reset=1;d.clk=0;d.eval();d.clk=1;d.eval();d.clk=0;d.eval();d.reset=0;d.eval();
  for(unsigned a=0;a<1024;++a)write(a);drain();
  // No request bubble after pipeline fill: 512-bit wide and128-bit narrow.
  d.wide_req=1;auto before=waccepted;
  for(unsigned a=0;a<1024;++a){d.wide_addr=a%256;step();}
  ck(waccepted-before==1024,"one512-bit request per clock");drain();
  d.req=1;d.wr=0;before=naccepted;
  for(unsigned a=0;a<2048;++a){d.addr=a%1024;step();}
  ck(naccepted-before==2048,"one128-bit request per clock");drain();
  // A blocked wide response must not prevent unrelated narrow progress.
  d.wide_take=0;d.wide_req=1;d.wide_addr=255;
  for(unsigned i=0;i<5;++i)step();
  d.req=1;d.wr=0;d.addr=0;before=naccepted;
  for(unsigned i=0;i<20;++i)step();
  ck(naccepted-before==20,"independent narrow response credits");drain();
  d.take=0;d.req=1;d.wr=0;d.addr=1023;
  for(unsigned i=0;i<5;++i)step();
  d.wide_req=1;d.wide_addr=0;before=waccepted;
  for(unsigned i=0;i<20;++i)step();
  ck(waccepted-before==20,"independent wide response credits");drain();
  for(unsigned i=0;i<50000;++i){
   d.reset=(i%991)==990;d.req=(rng()%5)!=0;d.wr=(rng()%3)==0;
   d.addr=rng()%1024;for(unsigned j=0;j<4;++j)d.din[j]=uint32_t(rng());
   d.wide_req=(rng()%3)!=0;d.wide_addr=rng()%256;
   d.take=(rng()%4)!=0;d.wide_take=(rng()%4)!=0;step();
  }
  d.reset=0;drain();
  // Reset kills a pending read; it must not erase previously written bytes.
  d.req=1;d.wr=0;d.addr=1023;step();d.reset=1;step();
  quiet();d.reset=0;d.req=1;d.wr=0;d.addr=1023;step();drain();
  std::cout<<"{\"passed\":true,\"checks\":"<<checks<<",\"cycles\":"<<cycles<<",\"narrow\":"<<naccepted<<",\"wide\":"<<waccepted<<",\"conflicts\":"<<conflicts<<"}\n";
 }catch(const std::exception& e){std::cerr<<"FAIL cycle "<<cycles<<": "<<e.what()<<"\n";return 1;}
}
