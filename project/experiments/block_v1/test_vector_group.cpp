#include "Vblock_v1_v_group.h"
#include "verilated.h"
#include <random>
#include <iostream>
#include <stdexcept>
using U=__uint128_t;static Vblock_v1_v_group d;static uint64_t checks=0;
static void need(bool x){++checks;if(!x)throw std::runtime_error("group arithmetic/protocol mismatch");}
static void tick(){d.clk=0;d.eval();d.clk=1;d.eval();}
static void put(VlWide<4>&p,U v){for(int j=0;j<4;++j){p[j]=uint32_t(v);v>>=32;}}
static U get(const VlWide<4>&p){U v=0;for(int j=3;j>=0;--j)v=v<<32|p[j];return v;}
static U root(U n){U l=0,h=U(1)<<64;while(l+1<h){U m=(l+h)/2;if(m*m<=n)l=m;else h=m;}return l;}
int main(int argc,char**argv){try{Verilated::commandArgs(argc,argv);d.reset=1;d.in_valid=0;d.out_ready=0;tick();tick();d.reset=0;tick();std::mt19937_64 r(121);
 for(unsigned i=0;i<4000;++i){bool sqrt=i&1;U n=U(r())<<64|r(),den=U(r())<<64|r();if(i<128){n=U(1)<<(i/2);den=i%3?1:0;}need(d.in_ready);d.in_valid=1;d.square_root=sqrt;put(d.numerator,n);put(d.denominator,den);tick();d.in_valid=0;unsigned latency=0;while(!d.out_valid){tick();need(++latency<130);}need(latency==(sqrt?64:den?128:0));need(bool(d.error)==(!sqrt&&!den));
  U q=sqrt?root(n):den?n/den:0,rem=sqrt?n-q*q:den?n%den:0;need(get(d.quotient)==q&&get(d.remainder)==rem);
  for(unsigned k=0;k<3;++k){d.in_valid=1;tick();need(!d.in_ready&&d.out_valid&&get(d.quotient)==q&&get(d.remainder)==rem);}d.in_valid=0;d.out_ready=1;tick();d.out_ready=0;need(d.in_ready);
 }
 std::cout<<"{\"passed\":true,\"cases\":4000,\"checks\":"<<checks<<"}\n";return 0;
}catch(const std::exception&e){std::cerr<<e.what()<<"\n";return 1;}}
