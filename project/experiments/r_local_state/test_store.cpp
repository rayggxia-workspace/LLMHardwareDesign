#include "Vr_state_store.h"
#include "verilated.h"
#include <array>
#include <deque>
#include <random>
#include <iostream>
#include <stdexcept>
#ifndef WORDS
#define WORDS 256
#endif
struct Read {int sample,due,row;std::array<uint32_t,16> expected;};
struct Write {int due,bank,row;uint8_t mask;std::array<uint32_t,8> data;};
int main(int argc,char**argv){
 Verilated::commandArgs(argc,argv);Vr_state_store d;std::mt19937 rng(166);
 constexpr int rows=WORDS/8;uint32_t mem[2][rows][8]{};
 std::deque<Read> reads;std::deque<Write> writes;int time=0;uint64_t checks=0;
 auto require=[&](bool ok,const char* what){++checks;if(!ok)throw std::runtime_error(std::string(what)+" cycle="+std::to_string(time));};
 auto tick=[&](){
  if(d.reset){reads.clear();writes.clear();}
  else {
   if(d.rd_valid)reads.push_back({time+2,time+3,int(d.rd_row),{}});
   if(d.wr_valid){Write w{time+2,int(d.wr_bank),int(d.wr_row),uint8_t(d.wr_mask),{}};for(int l=0;l<8;++l)w.data[l]=d.wr_data[l];writes.push_back(w);}
   for(auto &r:reads)if(r.sample==time)for(int b=0;b<2;++b)for(int l=0;l<8;++l)r.expected[b*8+l]=mem[b][r.row][l];
   while(!writes.empty()&&writes.front().due==time){auto w=writes.front();writes.pop_front();for(int l=0;l<8;++l)if(w.mask&(1<<l))mem[w.bank][w.row][l]=w.data[l];}
  }
  d.clk=0;d.eval();d.clk=1;d.eval();
  bool expected=!reads.empty()&&reads.front().due==time;
  require(bool(d.out_valid)==expected,"valid");
  if(expected){auto r=reads.front();reads.pop_front();for(int l=0;l<8;++l){require(d.out_bank0[l]==r.expected[l],"bank0");require(d.out_bank1[l]==r.expected[8+l],"bank1");}}
  ++time;
 };
 try {
  d.reset=1;d.rd_valid=0;d.wr_valid=0;tick();tick();d.reset=0;
  for(int b=0;b<2;++b)for(int row=0;row<rows;++row){d.wr_valid=1;d.wr_bank=b;d.wr_row=row;d.wr_mask=255;for(int l=0;l<8;++l)d.wr_data[l]=rng();tick();}
  d.wr_valid=0;for(int n=0;n<5;++n)tick();
  for(int row=0;row<rows;++row){d.rd_valid=1;d.rd_row=row;tick();}
  for(int n=0;n<20000;++n){d.rd_valid=(rng()%4)!=0;d.rd_row=rng()%rows;d.wr_valid=(rng()%3)!=0;d.wr_bank=rng()%2;d.wr_row=(n%4==0)?d.rd_row:rng()%rows;d.wr_mask=rng();for(int l=0;l<8;++l)d.wr_data[l]=rng();if(n%997==996)d.reset=1;tick();d.reset=0;}
  d.rd_valid=0;d.wr_valid=0;for(int n=0;n<8;++n)tick();
  for(int row=0;row<rows;++row){d.rd_valid=1;d.rd_row=row;tick();}
  d.rd_valid=0;for(int n=0;n<5;++n)tick();
  std::cout<<"{\"passed\":true,\"words\":"<<WORDS<<",\"checks\":"<<checks<<",\"cycles\":"<<time<<"}\n";
 }catch(const std::exception&e){std::cerr<<e.what()<<"\n";return 1;}
}
