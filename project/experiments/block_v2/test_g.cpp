#include "Vblock_v2_g.h"
#include "verilated.h"
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <deque>
#include <iostream>
#include <memory>
#include <random>
#include <stdexcept>
static std::unique_ptr<Vblock_v2_g> p;
#define d (*p)
static uint64_t checks=0,cycles=0,accepted=0,delivered=0;
static std::mt19937 rng(143);
static void ck(bool x,const char*s){++checks;if(!x)throw std::runtime_error(s);}
static void tick(){d.clk=0;d.eval();d.clk=1;d.eval();++cycles;d.clk=0;d.eval();}
static int64_t rne(int64_t x,unsigned s){if(!s)return x;int64_t q=x>>s;uint64_t r=uint64_t(x)&((uint64_t(1)<<s)-1),h=uint64_t(1)<<(s-1);return q+int64_t(r>h||(r==h&&(q&1)));}
static double fn(unsigned n,double x){switch(n){case 0:return x/(1+std::exp(-x));case 1:return 1/(1+std::exp(-x));case 2:return .5*x*(1+std::tanh(std::sqrt(2/std::acos(-1.))*(x+.044715*x*x*x)));default:return std::log1p(std::exp(x));}}
static int64_t activation(unsigned n,int16_t raw){int lim=n==3?16384:8192;
 if(raw< -lim)return 0;if(raw>lim)return n==1?16384:raw;
 unsigned offset=int(raw)+lim,index=offset/32,f=offset%32;
 double x=-double(lim)/1024+double(index)/32;
 double scale=n==1?16384:1024;
 int64_t lo=std::llrint(fn(n,x)*scale),hi=std::llrint(fn(n,index==unsigned(lim/16)?x:x+1./32)*scale);
 return lo+rne((hi-lo)*f,5);
}
struct Expected{uint32_t data;bool error,sat;};
static Expected oracle(unsigned n,bool gated,uint32_t x,uint32_t g){Expected e{0,n>3,false};if(e.error)return e;
 for(unsigned l=0;l<2;++l){int64_t f=activation(n,int16_t(x>>(16*l)));int64_t y=gated?rne(f*int16_t(g>>(16*l)),n==1?14:10):f;
  if(y< -32768){y=-32768;e.sat=true;}if(y>32767){y=32767;e.sat=true;}e.data|=uint32_t(uint16_t(y))<<(16*l);
 }return e;}
int main(int argc,char**argv){try{Verilated::commandArgs(argc,argv);p=std::make_unique<Vblock_v2_g>();d.reset=1;d.in_valid=0;d.out_ready=0;tick();tick();d.reset=0;tick();
 std::deque<Expected> queue;bool held=false;Expected hold{};uint64_t seq=0,total=4*2*32768+2000;
 std::array<double,4> errors{};
 while(seq<total||!queue.empty()||d.out_valid){
  unsigned n=0;bool gated=false;uint32_t x=0,g=0;
  if(seq<4*2*32768){n=seq/(2*32768);gated=(seq/32768)%2;int32_t raw=-32768+2*int(seq%32768);
   x=uint16_t(raw)|(uint32_t(uint16_t(raw+1))<<16);g=uint16_t(int16_t(seq*97))|(uint32_t(uint16_t(int16_t(seq*131)))<<16);
   if(!gated)for(unsigned l=0;l<2;++l){int16_t q=int16_t(x>>(16*l));errors[n]=std::max(errors[n],std::abs(double(activation(n,q))/(n==1?16384:1024)-fn(n,double(q)/1024)));}
  }else{n=(seq%8);gated=seq&1;x=uint32_t(seq*1234567);g=uint32_t(seq*76543);}
  d.in_valid=seq<total;d.in_fn=n;d.in_gated=gated;d.in_x=x;d.in_gate=g;d.out_ready=rng()%5!=0;d.eval();
  if(held){ck(d.out_valid,"lost held valid");ck(d.out_data==hold.data&&bool(d.out_error)==hold.error&&bool(d.out_saturated)==hold.sat,"held payload changed");}
  bool fire=d.in_valid&&d.in_ready;
  if(fire){queue.push_back(oracle(n,gated,x,g));++accepted;}
  if(d.out_valid&&d.out_ready){ck(!queue.empty(),"unrequested output");auto e=queue.front();queue.pop_front();
   ck(d.out_data==e.data,"numeric mismatch");ck(bool(d.out_error)==e.error,"error mismatch");ck(bool(d.out_saturated)==e.sat,"sat mismatch");++delivered;}
  held=d.out_valid&&!d.out_ready;hold={d.out_data,bool(d.out_error),bool(d.out_saturated)};tick();if(fire)++seq;
  ck(cycles<1000000,"timeout");
 }
 ck(accepted==total&&delivered==total,"conservation");
 ck(errors[0]<.004&&errors[1]<.0005&&errors[2]<.0015&&errors[3]<.001,"float error budget");
 d.in_valid=1;d.in_fn=0;tick();tick();d.reset=1;tick();d.reset=0;d.in_valid=0;tick();ck(!d.out_valid,"reset pipeline");
 std::cout<<"{\"passed\":true,\"checks\":"<<checks<<",\"cycles\":"<<cycles<<",\"accepted\":"<<accepted<<",\"delivered\":"<<delivered<<",\"max_abs_error\":[";
 for(unsigned i=0;i<4;++i)std::cout<<(i?",":"")<<errors[i];std::cout<<"]}\n";p.reset();return 0;
 }catch(const std::exception&e){std::cerr<<"FAIL "<<cycles<<" "<<e.what()<<"\n";p.reset();return 1;}}
