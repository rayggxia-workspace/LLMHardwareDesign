#include "Vpair_re.h"
#include "verilated.h"
#include <array>
#include <cstdint>
#include <iostream>
#include <random>
#include <stdexcept>
#include <memory>
using P=std::array<uint32_t,4>;
static uint64_t checks=0;
static void ck(bool v,const char* s){++checks;if(!v)throw std::runtime_error(s);}
static int64_t round_even(int32_t x,unsigned shift){
 int64_t v=x; if(!shift)return v;
 uint64_t mag=v<0?uint64_t(-v):uint64_t(v),den=uint64_t(1)<<shift;
 uint64_t q=mag/den,r=mag%den;if(r>den-r||(r==den-r&&(q&1)))++q;
 return v<0?-int64_t(q):int64_t(q);
}
int main(int argc,char**argv){try{
 Verilated::commandArgs(argc,argv);ck(argc>=4,"usage shift bank stall");
 unsigned shift=std::stoul(argv[1]),bank=std::stoul(argv[2]),stall=std::stoul(argv[3]);
 unsigned oracle_shift=argc>4&&argv[4][0]!='+'?std::stoul(argv[4]):shift;
 std::unique_ptr<Vpair_re> p(new Vpair_re);auto& d=*p;
 std::mt19937 rng(162+shift*37+bank*13+stall);uint64_t cycles=0;
 auto tick=[&](){d.clk=0;d.eval();d.clk=1;d.eval();d.clk=0;d.eval();++cycles;};
 d.reset=1;d.load_valid=0;d.rd_valid=0;d.out_ready=0;d.shift=shift;tick();tick();d.reset=0;tick();
 std::array<std::array<P,64>,2> packets;
 const uint32_t edge[]={0,1,0xffffffff,0x7fffffff,0x80000000,32767,32768,0xffff8000,0xffff7fff,65535,65536,0xffff0000};
 for(unsigned b=0;b<2;++b)for(unsigned i=0;i<64;++i){
  for(unsigned j=0;j<4;++j)packets[b][i][j]=i<12?edge[(i+j)%12]:rng();
  for(unsigned w=0;!d.load_ready;++w){ck(w<100,"load timeout");tick();}
  d.load_target=b;d.load_index=i;for(unsigned j=0;j<4;++j)d.load_data[j]=packets[b][i][j];
  d.load_valid=1;tick();d.load_valid=0;
 }
 unsigned sent=0,raw=0,received=0,hold_cycles=0;bool held=false,saw_raw_stall=false;P held_data{};bool held_sat=false;
 for(unsigned watchdog=0;received<64;++watchdog){
  ck(watchdog<100000,"stream timeout");d.rd_bank=bank;d.rd_index=sent;d.rd_valid=sent<64;
  // Long output stalls fill E and then R's finite read-response FIFO.
  d.out_ready=!stall||(watchdog%97>=60);d.clk=0;d.eval();
  bool request=d.rd_valid&&d.rd_ready,accept=d.out_valid&&d.out_ready,raw_accept=d.raw_valid&&d.raw_ready;
  if(d.raw_valid&&!d.raw_ready)saw_raw_stall=true;
  if(held){ck(d.out_valid,"valid lost under backpressure");for(unsigned j=0;j<4;++j)ck(d.out_data[j]==held_data[j],"held payload changed");ck(bool(d.out_saturated)==held_sat,"held flag changed");}
  if(d.raw_valid){for(unsigned j=0;j<4;++j)ck(d.raw_data[j]==packets[bank][raw][j],"R read/ordering mismatch");}
  if(d.out_valid){
   bool saturated=false;uint64_t expected=0;
   for(unsigned j=0;j<4;++j){int64_t x=round_even(int32_t(packets[bank][received][j]),oracle_shift);if(x>32767){x=32767;saturated=true;}if(x<-32768){x=-32768;saturated=true;}expected|=uint64_t(uint16_t(x))<<(j*16);}
   ck(!d.out_error,"E rejected legal conversion");ck(d.out_data[0]==uint32_t(expected)&&d.out_data[1]==uint32_t(expected>>32),"R-E numeric mismatch");
   ck(d.out_data[2]==0&&d.out_data[3]==0,"upper E lanes not zero");ck(bool(d.out_saturated)==saturated,"saturation flag mismatch");
  }
  held=d.out_valid&&!d.out_ready;if(held){for(unsigned j=0;j<4;++j)held_data[j]=d.out_data[j];held_sat=d.out_saturated;++hold_cycles;}
  tick();if(request)++sent;if(raw_accept)++raw;if(accept)++received;
 }
 ck(sent==64&&raw==64,"packet lost/duplicated");if(stall)ck(saw_raw_stall&&hold_cycles>0,"backpressure not exercised");
 d.reset=1;tick();ck(!d.out_valid&&!d.raw_valid,"reset did not flush valid state");
 std::cout<<"{\"passed\":true,\"checks\":"<<checks<<",\"cycles\":"<<cycles<<",\"packets\":"<<received<<",\"shift\":"<<shift<<",\"bank\":"<<bank<<",\"stall\":"<<stall<<",\"backpressure_cycles\":"<<hold_cycles<<"}\n";return 0;
}catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}}
