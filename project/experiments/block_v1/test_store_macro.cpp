#include "Vblock_v1_s16k.h"
#include "verilated.h"
#include <array>
#include <cstdint>
#include <iostream>
#include <random>
#include <stdexcept>
using Word=std::array<uint32_t,4>;
static Vblock_v1_s16k d;
static std::mt19937 rng(12116);
static uint64_t checks=0;
static void ck(bool p){++checks;if(!p)throw std::runtime_error("S16K protocol/data mismatch");}
static void tick(){d.clk=0;d.eval();d.clk=1;d.eval();}
static Word get(){Word w;for(int i=0;i<4;++i)w[i]=d.dout[i];return w;}
static void transaction(bool wr,unsigned addr,const Word&data,const Word&expected){
 ck(d.ready&&!d.valid);d.req=1;d.wr=wr;d.addr=addr;d.take=0;
 for(int i=0;i<4;++i)d.din[i]=data[i];tick();d.req=0;
 ck(d.valid&&!d.ready);Word reply=get();ck(reply==(wr?Word{}:expected));
 for(unsigned stall=0,n=rng()%7;stall<n;++stall){d.req=1;d.wr=1;d.addr=rng()%1024;
  for(int i=0;i<4;++i)d.din[i]=rng();tick();ck(d.valid&&!d.ready&&get()==reply);}
 // A simultaneous request at response consumption is not accepted.
 d.req=1;d.wr=1;d.take=1;tick();ck(!d.valid&&d.ready);d.req=0;d.take=0;
}
int main(int argc,char**argv){try{
 Verilated::commandArgs(argc,argv);d.reset=1;d.req=0;d.take=0;tick();d.reset=0;tick();ck(d.ready&&!d.valid);
 std::array<Word,1024> ref{};
 for(unsigned a=0;a<1024;++a){for(auto&v:ref[a])v=rng();transaction(true,a,ref[a],{});}
 for(unsigned a=0;a<1024;++a)transaction(false,a,{},ref[a]);
 for(unsigned it=0;it<10000;++it){unsigned a=rng()%1024;
  if(rng()&1){Word w;for(auto&v:w)v=rng();transaction(true,a,w,{});ref[a]=w;}
  else transaction(false,a,{},ref[a]);}
 // Reset abandons response, retains payload; no uninitialized address read.
 d.req=1;d.wr=0;d.addr=512;tick();ck(d.valid);d.reset=1;tick();ck(!d.valid&&d.ready);
 d.req=0;d.reset=0;tick();
 for(unsigned a=0;a<1024;++a)transaction(false,a,{},ref[a]);
 std::cout<<"{\"passed\":true,\"addresses\":1024,\"random_transactions\":10000,\"checks\":"<<checks<<"}\n";
 return 0;
}catch(const std::exception&e){std::cerr<<e.what()<<"\n";return 1;}}
