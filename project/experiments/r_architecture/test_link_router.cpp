#include "Vlink_router.h"
#include "verilated.h"
#include <random>
#include <array>
#include <iostream>
#include <stdexcept>
static void ck(bool x,const char*s){if(!x)throw std::runtime_error(s);}
int main(int argc,char**argv){try{Verilated::commandArgs(argc,argv);Vlink_router d;std::mt19937 rng(15745);auto tick=[&](){d.clk=0;d.eval();d.clk=1;d.eval();d.clk=0;d.eval();};d.reset=1;tick();d.reset=0;bool valid=false;unsigned route=0,rr=0,checks=0;std::array<uint32_t,4>payload{};
for(unsigned cycle=0;cycle<30000;++cycle){d.reset=cycle%997==996;d.in_valid=rng()&15;d.in_route=rng()&255;d.out_ready=rng()&15;for(int j=0;j<16;++j)d.in_data[j]=rng();d.eval();
 unsigned chosen=4;for(int k=0;k<4;++k)if(chosen==4&&(d.in_valid&(1u<<((rr+k)%4))))chosen=(rr+k)%4;
 unsigned ready=!d.reset&&chosen<4&&(!valid||(d.out_ready&(1<<route)))?1u<<chosen:0;ck(d.in_ready==ready,"input arbitration mismatch");ck(d.out_valid==(!d.reset&&valid?1u<<route:0),"output valid mismatch");if(valid&&!d.reset)for(int j=0;j<4;++j)ck(d.out_data[route*4+j]==payload[j],"payload mismatch");checks+=2+4*valid;
 if(d.reset){valid=false;rr=0;}else if(ready){for(int j=0;j<4;++j)payload[j]=d.in_data[chosen*4+j];route=d.in_route>>(chosen*2)&3;rr=(chosen+1)%4;valid=true;}else if(valid&&(d.out_ready&(1<<route)))valid=false;tick();}
std::cout<<"{\"passed\":true,\"cycles\":30000,\"checks\":"<<checks<<"}\n";return 0;}catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}}
