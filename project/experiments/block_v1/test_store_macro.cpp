#include "Vblock_v1_s16k.h"
#include "verilated.h"
#include <array>
#include <cstdint>
#include <deque>
#include <iostream>
#include <random>
#include <stdexcept>
using Word=std::array<uint32_t,4>;
static Vblock_v1_s16k d;
static std::mt19937 rng(12116);
static uint64_t checks=0;
static void ck(bool p){++checks;if(!p)throw std::runtime_error("S16K protocol/data mismatch");}
static Word get(){Word w;for(int i=0;i<4;++i)w[i]=d.dout[i];return w;}
static uint64_t cycles=0,accepted=0,retired=0,stalls=0,overlaps=0;
static std::array<Word,1024> ref{};
static std::array<bool,1024> initialized{};
static std::deque<Word> expected;
static bool held=false;static Word held_word{};
static void step(){
 d.clk=0;d.eval();
 if(d.reset){ck(!d.ready);expected.clear();held=false;}
 else {
  ck(bool(d.valid)==!expected.empty());
  if(d.valid)ck(get()==expected.front());
  if(held)ck(d.valid&&get()==held_word);
  bool pop=d.valid&&d.take,push=d.req&&d.ready;
  if(pop){expected.pop_front();++retired;}
  if(push){
   if(d.wr){for(int i=0;i<4;++i)ref[d.addr][i]=d.din[i];initialized[d.addr]=true;expected.push_back(Word{});}
   else {ck(initialized[d.addr]);expected.push_back(ref[d.addr]);}
   ++accepted;
  }
  if(push&&pop)++overlaps;
  if(d.req&&!d.ready)++stalls;
  held=d.valid&&!d.take;held_word=get();ck(expected.size()<=1);
 }
 d.clk=1;d.eval();++cycles;
}
static void request(bool wr,unsigned addr){d.req=1;d.wr=wr;d.addr=addr;for(int i=0;i<4;++i)d.din[i]=rng();}
static void drain(){d.req=0;d.take=1;step();ck(expected.empty());}
int main(int argc,char**argv){try{
 Verilated::commandArgs(argc,argv);d.reset=1;d.req=0;d.take=0;step();d.reset=0;step();d.take=1;
 for(unsigned a=0;a<1024;++a){request(true,a);step();}
 for(unsigned a=0;a<1024;++a){request(true,a);step();request(false,a);step();}
 drain();uint64_t start=cycles,n=accepted;
 for(unsigned a=0;a<4096;++a){request(false,a%1024);step();}
 ck(accepted-n==4096&&cycles-start==4096);drain();
 for(unsigned it=0;it<20000;++it){d.take=rng()%4!=0;d.req=rng()%5!=0;d.wr=rng()&1;d.addr=rng()%1024;for(int i=0;i<4;++i)d.din[i]=rng();step();}
 drain();request(false,512);d.take=0;step();d.reset=1;step();d.req=0;d.reset=0;d.take=0;step();
 for(unsigned a=0;a<1024;++a){request(false,a);d.take=1;step();}drain();
 ck(stalls>0&&overlaps>4096);
 std::cout<<"{\"passed\":true,\"addresses\":1024,\"random_cycles\":20000,\"continuous_read_words\":4096,\"continuous_read_cycles\":4096,\"accepted\":"<<accepted<<",\"retired\":"<<retired<<",\"overlap_edges\":"<<overlaps<<",\"backpressure_cycles\":"<<stalls<<",\"checks\":"<<checks<<"}\n";
 return 0;
}catch(const std::exception&e){std::cerr<<e.what()<<"\n";return 1;}}
