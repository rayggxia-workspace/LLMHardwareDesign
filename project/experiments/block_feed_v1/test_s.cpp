#include "Vblock_feed_s16k.h"
#include "verilated.h"
#include <array>
#include <cstdint>
#include <iostream>
#include <random>
#include <stdexcept>
using Word=std::array<uint32_t,4>;
using Wide=std::array<uint32_t,16>;
static Vblock_feed_s16k* ptr;
#define d (*ptr)
static std::mt19937_64 rng(130);
static std::array<Word,1024> mem;
static bool nv=false,wv=false;static Word nd{};static Wide wd{};
static uint64_t cycles=0,checks=0,naccess=0,waccess=0,conflicts=0;
static void ck(bool ok,const char* msg){++checks;if(!ok)throw std::runtime_error(msg);}
static void check(){
 ck(bool(d.valid)==nv&&bool(d.wide_valid)==wv,"response valid scoreboard");
 if(nv)for(unsigned i=0;i<4;++i)ck(d.dout[i]==nd[i],"narrow response mismatch/stability");
 if(wv)for(unsigned i=0;i<16;++i)ck(d.wide_dout[i]==wd[i],"wide response mismatch/stability");
}
static void step(){
 d.clk=0;d.eval();check();
 bool wf=!d.reset&&d.wide_req&&(!wv||d.wide_take);
 bool nr=!d.reset&&(!nv||d.take)&&!wf;
 ck(bool(d.wide_ready)==(!d.reset&&(!wv||d.wide_take)),"wide readiness");
 ck(bool(d.ready)==nr,"single1RW bank conflict/readiness");
 bool nf=d.req&&nr;
 ck(!(nf&&wf),"simultaneous conflicting bank access");
 if(d.reset){nv=wv=false;}
 else{
  if(nv&&d.take)nv=false;if(wv&&d.wide_take)wv=false;
  if(wf){wv=true;for(unsigned b=0;b<4;++b)for(unsigned j=0;j<4;++j)wd[4*b+j]=mem[4*d.wide_addr+b][j];++waccess;}
  if(nf){nv=true;if(d.wr)for(unsigned j=0;j<4;++j)mem[d.addr][j]=d.din[j];nd=mem[d.addr];++naccess;}
  if(d.req&&wf)++conflicts;
 }
 d.clk=1;d.eval();++cycles;d.clk=0;d.eval();check();
}
int main(int argc,char** argv){
 Verilated::commandArgs(argc,argv);ptr=new Vblock_feed_s16k;
 try{
  d.reset=1;d.req=0;d.wide_req=0;d.take=0;d.wide_take=0;
  // Initial random DUT state is intentionally unknown before the first reset.
  d.clk=0;d.eval();d.clk=1;d.eval();d.clk=0;d.eval();d.reset=0;
  d.req=1;d.wr=1;d.take=1;
  for(unsigned a=0;a<1024;++a){d.addr=a;for(unsigned j=0;j<4;++j)d.din[j]=uint32_t(rng());step();}
  d.req=0;step();d.wide_req=1;d.wide_take=1;
  auto before=waccess;for(unsigned a=0;a<256;++a){d.wide_addr=a;step();}
  ck(waccess-before==256,"continuous512-bit read throughput");
  d.wide_req=0;step();d.req=1;d.wr=0;
  before=naccess;for(unsigned a=0;a<4096;++a){d.addr=a%1024;step();}
  ck(naccess-before==4096,"continuous128-bit read throughput");
  for(unsigned i=0;i<24000;++i){
   d.reset=i%997==996;d.req=rng()%5!=0;d.wr=rng()%3==0;d.addr=rng()%1024;
   for(unsigned j=0;j<4;++j)d.din[j]=uint32_t(rng());
   d.take=rng()%3!=0;d.wide_req=rng()%3!=0;d.wide_take=rng()%4!=0;d.wide_addr=rng()%256;step();
  }
  std::cout<<"{\"passed\":true,\"checks\":"<<checks<<",\"cycles\":"<<cycles
           <<",\"narrow_accesses\":"<<naccess<<",\"wide_accesses\":"<<waccess
           <<",\"actual_conflicts\":"<<conflicts<<",\"wide_stream_requests\":256,\"wide_stream_cycles\":256}\n";
 }catch(const std::exception& e){std::cerr<<"FAIL cycle="<<cycles<<": "<<e.what()<<"\n";return 1;}
}
