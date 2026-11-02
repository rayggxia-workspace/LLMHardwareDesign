#include "Vblock_feed_s_macro_sram.h"
#include "verilated.h"
#include <array>
#include <deque>
#include <random>
#include <stdexcept>
#include <iostream>
using Word=std::array<uint32_t,4>;
static Vblock_feed_s_macro_sram* p;
#define d (*p)
static std::array<Word,1024> mem;
static std::deque<Word> expected_n;
static std::mt19937_64 rng(14320261101ULL);
static uint64_t cycles=0,checks=0,commands=0,ac=0,bc=0,nc=0;
static void ck(bool ok,const char* msg){++checks;if(!ok)throw std::runtime_error(msg);}
static void step(){
 d.clk=0;d.eval();
 if(d.reset)expected_n.clear();
 else{
  if(d.valid){ck(!expected_n.empty(),"unexpected narrow response");for(unsigned j=0;j<4;++j)ck(d.dout[j]==expected_n.front()[j],"narrow during feeder/ack");if(d.take)expected_n.pop_front();}
  if(d.req&&d.ready){
   if(d.wr)for(unsigned j=0;j<4;++j)mem[d.addr][j]=d.din[j];
   expected_n.push_back(mem[d.addr]);++nc;
  }
 }
 d.clk=1;d.eval();++cycles;d.clk=0;d.eval();
}
static void quiet(){d.req=0;d.take=1;d.load_valid=0;d.done_take=0;d.a_ready=0;d.b_ready=0;}
static void drain(){d.req=0;d.take=1;for(unsigned i=0;!expected_n.empty()&&i<20;++i)step();ck(expected_n.empty(),"narrow drain");}
static void command(unsigned rows,unsigned tiles,bool aw,bool bw,bool reuse,unsigned bank,unsigned abase,unsigned bbase){
 quiet();d.load_rows=rows;d.load_tiles=tiles;d.load_a_wide=aw;d.load_b_wide=bw;
 d.load_reuse_b=reuse;d.load_bank=bank;d.load_a_base=abase;d.load_b_base=bbase;
 d.load_valid=1;d.eval();ck(d.load_ready,"descriptor ready");step();d.load_valid=0;
 unsigned ai=0,bi=0;const unsigned na=rows*tiles,nb=reuse?0:tiles*(bw?2:1);
 for(unsigned t=0;!d.done_valid&&t<5000;++t){
  d.a_ready=(rng()%3)!=0;d.b_ready=(rng()%3)!=0;
  d.req=(rng()%4)==0;d.wr=0;d.addr=rng()%1024;d.take=1;d.eval();
  if(d.a_valid){
   ck(ai<na,"extra A");unsigned tile=ai/rows,row=ai%rows;
   ck(d.a_bank==bank&&d.a_tile==tile&&d.a_row==row&&bool(d.a_wide)==aw,"A metadata/held");
   auto value=mem[abase+tile*(rows>4?8:4)+row];
   for(unsigned j=0;j<4;++j)ck(d.a_data[j]==value[j],"A bank/row/word order");
   if(d.a_ready){++ai;++ac;}
  }
  if(d.b_valid){
   ck(bi<nb,"extra B");unsigned tile=bi/(bw?2:1),half=bw?(bi%2):0;
   ck(d.b_bank==bank&&d.b_tile==tile&&bool(d.b_wide)==bw&&d.b_half==half,"B metadata/held");
   for(unsigned b=0;b<4;++b)for(unsigned j=0;j<4;++j)ck(d.b_data[4*b+j]==mem[bbase+tile*(bw?8:4)+4*half+b][j],"B512 bank order");
   if(d.b_ready){++bi;++bc;}
  }
  step();
 }
 ck(d.done_valid&&!d.done_error&&!d.busy,"completion and progress");ck(ai==na&&bi==nb,"all expected A/B delivered exactly once");
 d.req=0;for(unsigned i=0;i<7;++i){ck(d.done_valid&&!d.load_ready,"done held under backpressure");step();}
 d.done_take=1;step();d.done_take=0;drain();++commands;
}
int main(int argc,char** argv){
 Verilated::commandArgs(argc,argv);p=new Vblock_feed_s_macro_sram;
 try{
  quiet();d.reset=1;step();d.reset=0;
  // Entire finite payload initialized; no SRAM reset or zero-data assumption.
  for(unsigned a=0;a<1024;++a){
   d.req=1;d.wr=1;d.addr=a;for(unsigned j=0;j<4;++j)d.din[j]=uint32_t(rng());d.eval();
   unsigned wait=0;while(!d.ready){ck(++wait<20,"initialization progress");step();}step();
  }drain();
  for(unsigned rows=1;rows<=8;++rows)for(unsigned tiles=1;tiles<=4;++tiles)
   for(unsigned fmt=0;fmt<4;++fmt)for(unsigned reuse=0;reuse<2;++reuse)
    command(rows,tiles,fmt&1,fmt&2,reuse,(rows+tiles)&1,(rows&1)?0:960,(rows&1)?64:960);
  // Invalid descriptors cannot issue a read or become busy.
  quiet();d.load_rows=0;d.load_tiles=1;d.load_valid=1;step();d.load_valid=0;
  ck(d.done_valid&&d.done_error&&!d.busy&&!d.a_valid&&!d.b_valid,"invalid descriptor rejected");
  d.done_take=1;step();d.done_take=0;
  // Interrupt a read in flight, abandon old responses and restart a command.
  d.load_rows=8;d.load_tiles=4;d.load_a_base=0;d.load_b_base=64;d.load_valid=1;
  step();d.load_valid=0;step();step();d.reset=1;step();quiet();d.reset=0;
  command(8,4,true,true,false,1,0,64);
  std::cout<<"{\"passed\":true,\"checks\":"<<checks<<",\"cycles\":"<<cycles<<",\"commands\":"<<commands<<",\"A\":"<<ac<<",\"B\":"<<bc<<",\"narrow\":"<<nc<<"}\n";
 }catch(const std::exception& e){std::cerr<<"FAIL cycle "<<cycles<<": "<<e.what()<<"\n";return 1;}
}
