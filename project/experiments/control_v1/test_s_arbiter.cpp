#include "Vcontrol_s_arbiter.h"
#include "verilated.h"
#include <array>
#include <random>
#include <iostream>
#include <cstdlib>
static unsigned checks=0;
static void need(bool b,const char*m){++checks;if(!b){std::cerr<<m<<"\n";std::exit(1);}}
int main(int argc,char**argv){Verilated::commandArgs(argc,argv);Vcontrol_s_arbiter v;std::mt19937 rng{162};std::array<unsigned,6> sent{},received{};
 bool pending=false;unsigned delay=0,owner=0,address=0;v.clk=0;v.req=0;v.wr=0;v.addr=0;v.take=0;v.s_ready=0;v.s_valid=0;
 for(unsigned n=0;n<24;++n)v.din[n]=0;for(unsigned n=0;n<4;++n)v.s_dout[n]=0;
 auto edge=[&](){v.clk=1;v.eval();v.clk=0;v.eval();};v.reset=1;edge();edge();v.reset=0;
 for(unsigned cycle=0;cycle<20000;++cycle){v.req=cycle<18000?63:0;v.wr=0;v.addr=0;v.take=0;
  for(unsigned c=0;c<6;++c){unsigned a=c*128+(sent[c]%128);v.addr|=uint64_t(a)<<(c*10);v.wr|=(sent[c]&1)<<c;if(rng()%4)v.take|=1u<<c;for(unsigned n=0;n<4;++n)v.din[c*4+n]=(sent[c]<<8)|(c<<4)|n;}
  v.s_ready=!pending&&rng()%4!=0;v.s_valid=pending&&!delay;for(unsigned n=0;n<4;++n)v.s_dout[n]=address*4+n;v.eval();
  need(!v.ready || (v.ready&(v.ready-1))==0,"one request grant");need(!v.valid || (v.valid&(v.valid-1))==0,"one response owner");
  if(pending&&delay)--delay;
  if(v.s_valid&&v.s_take){need(v.valid==(1u<<owner),"response to original requester");for(unsigned n=0;n<4;++n)need(v.dout[n]==address*4+n,"actual shared response");++received[owner];pending=false;}
  if(v.s_req&&v.s_ready){need(!pending,"one S flight");address=v.s_addr;owner=address/128;need(owner<6 && v.ready==(1u<<owner),"correct request owner");
   need(v.s_wr==(sent[owner]&1),"write control retained");for(unsigned n=0;n<4;++n)need(v.s_din[n]==((sent[owner]<<8)|(owner<<4)|n),"request payload retained");++sent[owner];pending=true;delay=1+rng()%6;}
  edge();
 }
 for(unsigned c=0;c<6;++c)need(sent[c]==received[c]&&sent[c]>100,"round robin progresses and drains");need(!pending,"shared port drained");
 std::cout<<"{\"passed\":true,\"checks\":"<<checks<<"}\n";
}
