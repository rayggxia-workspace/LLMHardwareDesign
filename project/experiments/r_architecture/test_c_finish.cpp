#include "Vc_finish.h"
#include "verilated.h"
#include <random>
#include <iostream>
#include <stdexcept>
#include <array>
using I=__int128_t;static void ck(bool b,const char*s){if(!b)throw std::runtime_error(s);}
static I rne(I v,unsigned s){if(!s)return v;I q=v>>s,r=v-q*(I(1)<<s),h=I(1)<<(s-1);return q+(r>h||(r==h&&(q&1)));}
int main(int argc,char**argv){try{Verilated::commandArgs(argc,argv);Vc_finish d;std::mt19937_64 rng(157802);auto tick=[&](){d.clk=0;d.eval();d.clk=1;d.eval();d.clk=0;d.eval();};d.reset=1;d.in_valid=0;d.out_ready=0;tick();tick();d.reset=0;tick();unsigned checks=0;
 for(unsigned t=0;t<1000;++t){unsigned op=t%3,shift=t%64;std::array<int64_t,8>expect;bool bad=false;for(unsigned l=0;l<8;++l){int64_t a=int64_t(rng()),b=int64_t(rng());if(t<20){a=int64_t(l)-4;b=l&1?INT32_MIN:INT32_MAX;}I value=(op==2?I(a):rne(a,shift))+(op?I(b):0);bad|=op==2?(value<INT64_MIN||value>INT64_MAX):(value<INT32_MIN||value>INT32_MAX);expect[l]=op==2?int64_t(uint64_t(value)):int32_t(uint32_t(value));d.in_a[2*l]=uint32_t(a);d.in_a[2*l+1]=uint64_t(a)>>32;d.in_b[2*l]=uint32_t(b);d.in_b[2*l+1]=uint64_t(b)>>32;}
  d.in_op=op;d.in_shift=shift;d.in_valid=1;ck(d.in_ready,"finish not ready");tick();d.in_valid=0;unsigned latency=0;while(!d.out_valid){tick();ck(++latency<20,"finish timeout");}ck(latency==8,"finish latency");ck(bool(d.out_error)==bad,"finish overflow mismatch");for(unsigned l=0;l<8;++l){uint64_t x=uint64_t(d.out_data[l*2])|(uint64_t(d.out_data[l*2+1])<<32);ck(int64_t(x)==expect[l],"finish value mismatch");++checks;}d.out_ready=1;tick();d.out_ready=0;
 }
 std::cout<<"{\"passed\":true,\"cases\":1000,\"checks\":"<<checks<<",\"latency\":8}\n";return 0;
}catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}}
