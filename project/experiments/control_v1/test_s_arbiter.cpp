#include "Vcontrol_s_arbiter.h"
#include "verilated.h"
#include <array>
#include <random>
#include <iostream>
#include <cstdlib>
#include <type_traits>
#ifndef TEST_CLIENTS
#define TEST_CLIENTS 6
#endif
template<class W>static void clear_address(W&v){if constexpr(std::is_integral_v<W>)v=0;else for(unsigned i=0;i<(TEST_CLIENTS*10+31)/32;++i)v[i]=0;}
template<class W>static void add_address(W&v,unsigned c,unsigned a){unsigned bit=c*10;if constexpr(std::is_integral_v<W>)v|=uint64_t(a)<<bit;else{unsigned word=bit/32,offset=bit%32;v[word]|=a<<offset;if(offset>22)v[word+1]|=a>>(32-offset);}}
static unsigned checks=0;
static void need(bool b,const char*m){++checks;if(!b){std::cerr<<m<<"\n";std::exit(1);}}
int main(int argc,char**argv){
 Verilated::commandArgs(argc,argv);Vcontrol_s_arbiter v;std::mt19937 rng{162};
 std::array<unsigned,TEST_CLIENTS> issued{},accepted{},captured{},received{};std::array<bool,TEST_CLIENTS> request{};request.fill(true);
 bool pending=false,held_valid=false;unsigned delay=0,owner=0,address=0,held_owner=0;std::array<unsigned,4>held_data{};
 v.clk=0;v.req=0;v.wr=0;clear_address(v.addr);v.take=0;v.s_ready=0;v.s_valid=0;
 for(unsigned n=0;n<TEST_CLIENTS*4;++n)v.din[n]=0;for(unsigned n=0;n<4;++n)v.s_dout[n]=0;
 auto edge=[&](){v.clk=1;v.eval();v.clk=0;v.eval();};v.reset=1;edge();edge();v.reset=0;
 for(unsigned cycle=0;cycle<24000;++cycle){
  v.req=0;v.wr=0;clear_address(v.addr);v.take=0;
  for(unsigned c=0;c<TEST_CLIENTS;++c){
   if(request[c])v.req|=1u<<c;unsigned a=c*128+(issued[c]%128);add_address(v.addr,c,a);v.wr|=(issued[c]&1)<<c;
   if(rng()%4 && cycle%101<85)v.take|=1u<<c;
   for(unsigned n=0;n<4;++n)v.din[c*4+n]=(issued[c]<<8)|(c<<4)|n;
  }
  v.s_ready=!pending&&rng()%4!=0;v.s_valid=pending&&!delay;
  for(unsigned n=0;n<4;++n)v.s_dout[n]=address*4+n;v.eval();
  need(!v.ready || (v.ready&(v.ready-1))==0,"one request grant");need(!v.valid || (v.valid&(v.valid-1))==0,"one response owner");
  // Toggle S combinationally: ACK, valid and a held response must not follow
  // this external input without a clock. This checks the physical boundary.
  unsigned ready=v.ready,valid=v.valid;std::array<unsigned,4> response{};for(unsigned n=0;n<4;++n)response[n]=v.dout[n];
  v.s_ready=!v.s_ready;v.s_valid=!v.s_valid;for(unsigned n=0;n<4;++n)v.s_dout[n]^=0xffffffff;v.eval();
  need(v.ready==ready && v.valid==valid,"S handshake bypasses response pipeline");
  for(unsigned n=0;n<4;++n)need(v.dout[n]==response[n],"S data bypasses response register");
  v.s_ready=!v.s_ready;v.s_valid=!v.s_valid;for(unsigned n=0;n<4;++n)v.s_dout[n]^=0xffffffff;v.eval();
  if(held_valid){need(v.valid==(1u<<held_owner),"response ownership stable under backpressure");for(unsigned n=0;n<4;++n)need(v.dout[n]==held_data[n],"response data stable under backpressure");}
  held_valid=false;
  for(unsigned c=0;c<TEST_CLIENTS;++c){
   if(v.ready&(1u<<c)){need(request[c] && issued[c]<accepted[c],"ACK follows actual S acceptance");++issued[c];if(cycle>=20000)request[c]=false;}
   if(v.valid&(1u<<c)){
    need(received[c]<captured[c],"only captured S responses can be offered");unsigned expected=c*128+(received[c]%128);
    for(unsigned n=0;n<4;++n)need(v.dout[n]==expected*4+n,"correct client receives actual response");
    if(v.take&(1u<<c))++received[c];else{held_valid=true;held_owner=c;for(unsigned n=0;n<4;++n)held_data[n]=v.dout[n];}
   }
  }
  if(pending&&delay)--delay;
  if(v.s_valid&&v.s_take){++captured[owner];pending=false;}
  if(v.s_req&&v.s_ready){
   need(!pending,"one S flight");address=v.s_addr;owner=address/128;
   need(owner<TEST_CLIENTS && address==owner*128+(accepted[owner]%128),"original request address retained");
   need(v.s_wr==(accepted[owner]&1),"write control retained");
   for(unsigned n=0;n<4;++n)need(v.s_din[n]==((accepted[owner]<<8)|(owner<<4)|n),"request payload retained");
   ++accepted[owner];pending=true;delay=1+rng()%6;
  }
  edge();
 }
 for(unsigned c=0;c<TEST_CLIENTS;++c)need(issued[c]==accepted[c]&&accepted[c]==captured[c]&&captured[c]==received[c]&&issued[c]>100,"finite capacity round robin drains all accepted work");
 need(!pending&&!held_valid,"all external and local responses drained");
 std::cout<<"{\"passed\":true,\"checks\":"<<checks<<"}\n";
}
