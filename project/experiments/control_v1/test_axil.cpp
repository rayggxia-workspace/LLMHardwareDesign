#include "Vcontrol_axil_bridge.h"
#include "verilated.h"
#include <array>
#include <deque>
#include <random>
#include <iostream>
#include <cstdlib>
static unsigned checks=0;
static void need(bool b,const char*m){++checks;if(!b){std::cerr<<m<<"\n";std::exit(1);}}
int main(int argc,char**argv){Verilated::commandArgs(argc,argv);Vcontrol_axil_bridge v;std::mt19937 rng(162);
 std::array<uint32_t,64> mem{};std::deque<unsigned> aw,ar;std::deque<std::pair<uint32_t,unsigned>> w;
 std::deque<unsigned> b_expected;std::deque<std::pair<uint32_t,unsigned>> r_expected;
 auto edge=[&](){v.clk=1;v.eval();v.clk=0;v.eval();};
 v.clk=0;v.reset=1;v.axil_awvalid=0;v.axil_wvalid=0;v.axil_arvalid=0;v.axil_bready=0;v.axil_rready=0;
 v.cfg_ready=0;v.cfg_rsp_valid=0;v.cfg_rdata=0;v.cfg_error=0;edge();edge();v.reset=0;
 unsigned na=0,nw=0,nr=0,nb=0,nread=0;bool pending=false;unsigned delay=0;uint32_t value=0;bool error=false;
 bool bstalled=false,rstalled=false;unsigned held_b=0,held_rr=0;uint32_t held_rd=0;
 bool cfg_stalled=false;std::array<uint32_t,4> held_cfg{};
 for(unsigned cycle=0;cycle<10000;++cycle){
  v.axil_awvalid=na<300 && rng()%3!=0;v.axil_awaddr=(na%64)*4;v.axil_awprot=rng()%8;
  v.axil_wvalid=nw<300 && rng()%3!=0;v.axil_wdata=0x12340000u+nw;v.axil_wstrb=nw%7?15:3;
  v.axil_arvalid=nr<300 && rng()%3!=0;v.axil_araddr=(nr%64)*4;v.axil_arprot=rng()%8;
  v.axil_bready=rng()%4!=0;v.axil_rready=rng()%4!=0;
  v.cfg_ready=!pending && rng()%4!=0;
  v.cfg_rsp_valid=pending && delay==0;v.cfg_rdata=value;v.cfg_error=error;v.eval();
  if(bstalled)need(v.axil_bvalid && v.axil_bresp==held_b,"B stable");
  if(rstalled)need(v.axil_rvalid && v.axil_rresp==held_rr && v.axil_rdata==held_rd,"R stable");
  if(cfg_stalled)need(v.cfg_valid && std::array<uint32_t,4>{{v.cfg_write,v.cfg_addr,v.cfg_wdata,v.cfg_wstrb}}==held_cfg,"configuration stable");
  bstalled=v.axil_bvalid&&!v.axil_bready;if(bstalled)held_b=v.axil_bresp;
  rstalled=v.axil_rvalid&&!v.axil_rready;if(rstalled){held_rr=v.axil_rresp;held_rd=v.axil_rdata;}
  cfg_stalled=v.cfg_valid&&!v.cfg_ready;if(cfg_stalled)held_cfg={{v.cfg_write,v.cfg_addr,v.cfg_wdata,v.cfg_wstrb}};
  if(v.axil_bvalid&&v.axil_bready){need(!b_expected.empty() && v.axil_bresp==b_expected.front(),"B response");b_expected.pop_front();++nb;}
  if(v.axil_rvalid&&v.axil_rready){need(!r_expected.empty() && v.axil_rdata==r_expected.front().first && v.axil_rresp==r_expected.front().second,"R response");r_expected.pop_front();++nread;}
  if(v.axil_awvalid&&v.axil_awready){aw.push_back(v.axil_awaddr);++na;}
  if(v.axil_wvalid&&v.axil_wready){w.push_back({v.axil_wdata,v.axil_wstrb});++nw;}
  if(v.axil_arvalid&&v.axil_arready){ar.push_back(v.axil_araddr);++nr;}
  if(v.cfg_rsp_valid&&v.cfg_rsp_ready)pending=false;
  if(v.cfg_valid&&v.cfg_ready){
   if(v.cfg_write){need(!aw.empty()&&!w.empty(),"AW/W independently buffered");
    need(v.cfg_addr==aw.front() && v.cfg_wdata==w.front().first && v.cfg_wstrb==w.front().second,"write fields preserved");
    error=v.cfg_wstrb!=15;value=0;if(!error)mem[(aw.front()/4)%64]=w.front().first;
    aw.pop_front();w.pop_front();b_expected.push_back(error?2:0);
   } else {need(!ar.empty() && v.cfg_addr==ar.front(),"AR preserved");error=false;value=mem[(ar.front()/4)%64];ar.pop_front();r_expected.push_back({value,0});}
   pending=true;delay=rng()%5;
  } else if(pending && delay) --delay;
  edge();
 }
 need(na==300 && nw==300 && nr==300 && nb==300 && nread==300,"all transactions drain");
 need(aw.empty()&&w.empty()&&ar.empty()&&b_expected.empty()&&r_expected.empty()&&!pending,"no hidden outstanding");
 std::cout<<"{\"passed\":true,\"checks\":"<<checks<<",\"writes\":"<<nb<<",\"reads\":"<<nread<<"}\n";
}
