#ifdef TOP_NATIVE
#include "Vc_wide_native.h"
using Core=Vc_wide_native;
#elif defined(TOP_E)
#include "Vc_wide_e.h"
using Core=Vc_wide_e;
#else
#include "Vc_wide_m.h"
using Core=Vc_wide_m;
#endif
#include "verilated.h"
#include <array>
#include <random>
#include <iostream>
#include <stdexcept>
using I=__int128_t;
static void ck(bool b,const char*s){if(!b)throw std::runtime_error(s);}
int main(int argc,char**argv){try{Verilated::commandArgs(argc,argv);Core d;uint64_t cycles=0,checks=0;std::mt19937_64 rng(157801);
 auto tick=[&](){d.clk=0;d.eval();d.clk=1;d.eval();d.clk=0;d.eval();++cycles;};d.reset=1;d.in_valid=0;d.out_ready=0;tick();tick();d.reset=0;tick();
 std::array<unsigned,3>lat{};
 for(unsigned kind=0;kind<3;++kind)for(unsigned t=0;t<80;++t){
  std::array<int32_t,8>a;std::array<uint32_t,8>b;
  for(unsigned l=0;l<8;++l){a[l]=t<2?(l&1?INT32_MIN:INT32_MAX):int32_t(rng());b[l]=kind==0?uint32_t(int32_t(int16_t(rng()))):uint32_t(rng());if(t==0)b[l]=kind==0?uint32_t(-32768):0xffffffffu;if(t==1)b[l]=kind==0?32767:0x80000000u;d.in_a[l]=uint32_t(a[l]);d.in_b[l]=b[l];}
  ck(d.in_ready,"wide core not ready");d.in_kind=kind;d.in_valid=1;tick();d.in_valid=0;unsigned n=0;while(!d.out_valid){tick();ck(++n<2000,"wide timeout");}
  if(!t)lat[kind]=n;ck(n==lat[kind],"variable latency");ck(!d.out_error,"unexpected wide error");
#ifdef TOP_NATIVE
  ck(n==2&&d.command_count==1,"wrong native latency/count");
#else
  ck(d.command_count==(kind==0?15:25),"wrong M command count");
#endif
  for(unsigned l=0;l<8;++l){uint64_t got=uint64_t(d.out_data[2*l])|(uint64_t(d.out_data[2*l+1])<<32);I expect=I(a[l])*(kind==2?I(b[l]):I(int32_t(b[l])));ck(int64_t(got)==expect,"wide multiplication mismatch");++checks;}
  for(unsigned delay=0;delay<t%4;++delay){tick();ck(d.out_valid&&!d.in_ready,"wide output backpressure");}
  d.out_ready=1;tick();d.out_ready=0;
 }
 std::cout<<"{\"passed\":true,\"cases\":240,\"product_checks\":"<<checks<<",\"latency_S32S16_S32S32_S32U32\":["<<lat[0]<<','<<lat[1]<<','<<lat[2]<<"],\"cycles\":"<<cycles<<"}\n";return 0;
}catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}}
