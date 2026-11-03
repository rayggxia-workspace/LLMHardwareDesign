#include "Vcontrol_adapter_r.h"
#include "verilated.h"
#include <array>
#include <cstdint>
#include <iostream>
#include <random>
#include <stdexcept>
#include <memory>
#include <vector>
using D=std::array<uint32_t,8>;using P=std::array<uint32_t,4>;
static uint64_t checks=0,cycles=0;
static void ck(bool b,const char*s){++checks;if(!b)throw std::runtime_error(s);}
struct Sim{
 Vcontrol_adapter_r d;std::mt19937 rng{162};bool sp=false,rp=false,cp=false,error=false;
 unsigned sd=0,rd=0,cd=0,writes=0,loads=0,reads=0,commands=0;P sr{},rr{};
 std::array<uint32_t,16>response{};std::vector<P> written,loaded;
 Sim(){d.reset=1;d.task_valid=0;d.complete_ready=0;d.s_ready=0;d.s_valid=0;d.load_ready=0;d.rd_ready=0;d.rd_rsp_valid=0;d.cmd_ready=0;d.rsp_valid=0;d.rsp_error=0;tick();tick();d.reset=0;}
 void tick(){
  if(d.reset){
   d.clk=0;d.s_ready=0;d.s_valid=0;d.load_ready=0;d.rd_ready=0;d.rd_rsp_valid=0;d.cmd_ready=0;d.rsp_valid=0;
   d.eval();d.clk=1;d.eval();d.clk=0;d.eval();++cycles;
   sp=rp=cp=false;sd=rd=cd=0;writes=loads=reads=commands=0;written.clear();loaded.clear();return;
  }
  d.clk=0;d.s_ready=!sp&&rng()%3!=0;d.s_valid=sp&&sd==0;
  d.load_ready=rng()%3!=0;d.rd_ready=!rp&&rng()%3!=0;d.rd_rsp_valid=rp&&rd==0;
  d.cmd_ready=!cp&&rng()%3!=0;d.rsp_valid=cp&&cd==0;d.rsp_error=error;
  for(unsigned i=0;i<4;++i){d.s_dout[i]=sr[i];d.rd_data[i]=rr[i];}
  for(unsigned i=0;i<16;++i)d.rsp_data[i]=response[i];d.eval();
  bool sa=d.s_req&&d.s_ready,st=d.s_valid&&d.s_take,ra=d.rd_valid&&d.rd_ready,rt=d.rd_rsp_valid&&d.rd_rsp_ready,ca=d.cmd_valid&&d.cmd_ready,ct=d.rsp_valid&&d.rsp_ready;
  P store;unsigned index=d.rd_index,addr=d.s_addr,bank=d.rd_bank;bool wr=d.s_wr;
  for(unsigned i=0;i<4;++i)store[i]=d.s_din[i];
  if(d.load_valid&&d.load_ready){P p;for(unsigned i=0;i<4;++i)p[i]=d.load_data[i];loaded.push_back(p);++loads;}
  d.clk=1;d.eval();++cycles;
  if(st)sp=false;if(sd)--sd;if(rd)--rd;if(cd)--cd;if(rt)rp=false;if(ct)cp=false;
  if(sa){sp=true;sd=1+rng()%4;for(unsigned i=0;i<4;++i)sr[i]=wr?store[i]:addr*4+i;if(wr){written.push_back(store);++writes;}}
  if(ra){rp=true;rd=1+rng()%4;++reads;for(unsigned i=0;i<4;++i)rr[i]=bank*4096+index*4+i;}
  if(ca){cp=true;cd=1+rng()%4;++commands;}
  d.clk=0;d.eval();
 }
 unsigned task(D words){
  words[0]|=0x12340000;for(unsigned i=0;i<8;++i)d.task_data[i]=words[i];d.task_valid=1;d.clk=0;d.eval();
  for(unsigned i=0;!d.task_ready;++i){ck(i<1000,"task readiness timeout");tick();}
  tick();d.task_valid=0;
  for(unsigned i=0;!d.complete_valid;++i){ck(i<10000,"completion timeout");tick();}
  uint64_t result=uint64_t(d.complete_data);ck((result&0xffff)==0x1234,"completion tag mismatch");ck(((result>>16)&15)==7,"completion endpoint mismatch");
  for(unsigned i=0;i<11;++i){tick();ck(d.complete_valid&&uint64_t(d.complete_data)==result,"completion lost under backpressure");ck(!d.task_ready,"accepted task over held completion");}
  d.complete_ready=1;tick();d.complete_ready=0;return (result>>20)&15;
 }
};
int main(int argc,char**argv){try{Verilated::commandArgs(argc,argv);
 for(unsigned target=0;target<8;++target){Sim x;unsigned n=target<2?64:target<4?4:target==5?1:target==7?4:6;
  ck(x.task({{0x700,n,256,0,target,0,0,0}})==0,"legal load rejected");ck(x.loads==n&&x.writes==0&&x.reads==0,"load transfer counts");
  for(unsigned i=0;i<n;++i)for(unsigned j=0;j<4;++j)ck(x.loaded[i][j]==64+i*4+j,"S-to-R payload mismatch");
 }
 for(unsigned bank=0;bank<2;++bank){Sim x;ck(x.task({{0x701,64,0,0,bank,0,0,0}})==0,"legal read rejected");ck(x.reads==64&&x.writes==64,"read/write counts");for(unsigned i=0;i<64;++i)for(unsigned j=0;j<4;++j)ck(x.written[i][j]==bank*4096+i*4+j,"R-to-S ordering");}
 for(unsigned packed=0;packed<2;++packed){Sim x;for(unsigned i=0;i<16;++i)x.response[i]=0xabc00000+i;
  ck(x.task({{0x1702|(packed<<13),5,0,0,0,0,0,0}})==0,"saved command rejected");ck(x.commands==1&&x.writes==(packed?2:4),"saved response size");
  for(unsigned i=0;i<x.writes;++i)for(unsigned j=0;j<4;++j)ck(x.written[i][j]==x.response[packed?(i*4+j)*2:i*4+j],"native response packing");
 }
 {Sim x;x.error=true;ck(x.task({{0x1702,5,0,0,0,0,0,0}})==4,"core error not propagated");ck(!x.writes,"failed command wrote result");}
 const D invalid[]={{{0x700,65,0,0,0,0,0,0}},{{0x700,5,0,0,2,0,0,0}},{{0x701,2,0,63,0,0,0,0}},{{0x702,33*8,0,0,0,0,0,0}},{{0x3702,5,16368,0,0,0,0,0}},{{0x2702,5,0,0,0,0,0,0}},{{0x700,1,1,0,0,0,0,0}},{{0x700,1,0,0,0,0,0,1}},{{0x703,0,0,0,0,0,0,0}}};
 for(auto t:invalid){Sim x;ck(x.task(t)==2,"invalid descriptor accepted");ck(x.loads+x.reads+x.writes+x.commands==0,"invalid task had side effects");}
 {Sim x;x.d.task_data[0]=0x12340701;x.d.task_data[1]=64;x.d.task_data[2]=0;x.d.task_data[3]=0;for(unsigned i=4;i<8;++i)x.d.task_data[i]=0;x.d.task_valid=1;x.tick();x.d.task_valid=0;for(unsigned i=0;i<3;++i)x.tick();x.d.reset=1;x.tick();ck(!x.d.complete_valid&&!x.d.s_req&&!x.d.load_valid&&!x.d.cmd_valid&&!x.d.rd_valid,"reset left outgoing work valid");}
 std::cout<<"{\"passed\":true,\"checks\":"<<checks<<",\"cycles\":"<<cycles<<",\"component_only\":true}\n";return 0;
}catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}}
