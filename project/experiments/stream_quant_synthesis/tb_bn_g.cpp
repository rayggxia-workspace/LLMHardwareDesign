#include "Vbn_g_bridge.h"
#include "verilated.h"
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <iostream>
#include <memory>
#include <random>
#include <stdexcept>

static void ck(bool value,const char* message){if(!value)throw std::runtime_error(message);}
static int64_t rne(int64_t x,unsigned s){int64_t q=x>>s;uint64_t r=uint64_t(x)&((uint64_t(1)<<s)-1),h=uint64_t(1)<<(s-1);return q+int64_t(r>h||(r==h&&(q&1)));}
// Independent mathematical/LUT-grid reference, same declared contract as test_g.cpp.
static int64_t silu(int16_t raw){
 if(raw< -8192)return 0;if(raw>8192)return raw;
 unsigned offset=int(raw)+8192,index=offset/32,f=offset%32;
 auto fn=[](double x){return x/(1+std::exp(-x));};
 double x=-8.+double(index)/32;
 int64_t lo=std::llrint(fn(x)*1024),hi=std::llrint(fn(index==512?x:x+1./32)*1024);
 return lo+rne((hi-lo)*f,5);
}
struct Expected{uint32_t data;bool sat;};
static uint32_t xv(unsigned seq){return uint16_t(-32768+2*int(seq%32768))|(uint32_t(uint16_t(-32767+2*int(seq%32768)))<<16);}
static uint32_t uv(unsigned seq){return uint16_t(seq*97)|(uint32_t(uint16_t(seq*131))<<16);}
static Expected expected(unsigned seq,bool gated){Expected e{0,false};
 for(unsigned l=0;l<2;++l){int64_t v=silu(int16_t(xv(seq)>>(16*l)));
  if(gated)v=rne(v*int16_t(uv(seq)>>(16*l)),10);
  if(v< -32768){v=-32768;e.sat=true;}if(v>32767){v=32767;e.sat=true;}
  e.data|=uint32_t(uint16_t(v))<<(16*l);
 }return e;
}
int main(int argc,char**argv){try{
 Verilated::commandArgs(argc,argv);auto p=std::make_unique<Vbn_g_bridge>();auto& d=*p;
 auto tick=[&]{d.clk=0;d.eval();d.clk=1;d.eval();d.clk=0;d.eval();};
 std::mt19937 rng(248);
 std::cout<<"{\"passed\":true,\"fifo_bytes\":16,\"cases\":[";
 for(unsigned scenario=0;scenario<5;++scenario){
  bool gated=scenario!=0,stalls=scenario>=2;unsigned total=scenario==3?5504:scenario==4?32768:32;
  d.reset=1;d.x_valid=0;d.u_valid=0;d.out_ready=0;tick();tick();d.reset=0;d.gated=gated;
  unsigned xi=0,ui=0,oi=0,cycles=0,first=0,xpeak=0,upeak=0;bool xp=false,up=false,held=false;
  uint32_t held_data=0;bool held_sat=false;
  while(oi<total){
   if(xi<total&&!xp)xp=!stalls||rng()%5!=0;
   if(ui<total&&!up)up=!stalls||rng()%4==0;
   d.x_valid=xp;d.u_valid=up;d.x_data=xv(xi);d.u_data=uv(ui);
   d.out_ready=!stalls||(cycles%67>=19&&rng()%3!=0);d.eval();
   ck(d.x_level<=2&&d.u_level<=2,"FIFO overflow");
   xpeak=std::max(xpeak,unsigned(d.x_level));upeak=std::max(upeak,unsigned(d.u_level));
   if(held)ck(d.out_valid&&d.out_data==held_data&&bool(d.out_saturated)==held_sat,"output changed while blocked");
   bool xf=d.x_valid&&d.x_ready,uf=d.u_valid&&d.u_ready,of=d.out_valid&&d.out_ready;
   if(of){ck(oi<xi&&oi<ui,"output preceded input acceptance");auto e=expected(oi,gated);
    ck(!d.out_error&&d.out_data==e.data&&bool(d.out_saturated)==e.sat,"G numeric/order mismatch");if(!oi)first=cycles;++oi;}
   held=d.out_valid&&!d.out_ready;held_data=d.out_data;held_sat=d.out_saturated;tick();++cycles;
   if(xf){++xi;xp=false;}if(uf){++ui;up=false;}ck(cycles<1000000,"timeout");
  }
  ck(xi==total&&ui==total&&d.x_level==0&&d.u_level==0,"conservation");
  if(!stalls)ck(cycles<=total+6,"lost native II=1");
  std::cout<<(scenario?",":"")<<"{\"packets\":"<<total<<",\"gated\":"<<gated<<",\"stalls\":"<<stalls<<",\"cycles\":"<<cycles<<",\"first_output_cycle\":"<<first<<",\"x_peak\":"<<xpeak<<",\"u_peak\":"<<upeak<<"}";
 }
 // Reset while output is blocked: all old input ownership and results vanish.
 d.out_ready=0;d.x_valid=1;d.u_valid=1;for(int i=0;i<15;++i)tick();
 ck(d.out_valid,"reset scenario did not fill pipeline");d.reset=1;tick();d.reset=0;d.x_valid=0;d.u_valid=0;d.out_ready=1;
 for(int i=0;i<12;++i){ck(!d.out_valid,"reset leaked old result");tick();}
 ck(d.x_level==0&&d.u_level==0,"reset leaked input");
 std::cout<<"],\"reset_while_blocked\":true}\n";return 0;
 }catch(const std::exception& e){std::cerr<<"FAIL "<<e.what()<<"\n";return 1;}}
