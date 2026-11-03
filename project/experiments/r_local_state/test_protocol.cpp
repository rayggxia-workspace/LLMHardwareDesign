#include "Vr_stream_local.h"
#include "verilated.h"
#include <deque>
#include <random>
#include <iostream>
#include <stdexcept>
#ifndef TEST_WORDS
#define TEST_WORDS 256
#endif
int main(int argc,char**argv){Verilated::commandArgs(argc,argv);Vr_stream_local d;unsigned cycles=0,checks=0;std::mt19937 rng(166);std::deque<unsigned> pending;
 auto ck=[&](bool ok){++checks;if(!ok)throw std::runtime_error("protocol cycle="+std::to_string(cycles));};
 auto tick=[&](){d.clk=0;d.eval();d.clk=1;d.eval();d.clk=0;d.eval();++cycles;};
 try{
 d.reset=1;d.load_valid=0;d.cmd_valid=0;d.rd_valid=0;d.rd_rsp_ready=0;d.rsp_ready=0;tick();tick();d.reset=0;tick();
 for(unsigned b=0;b<2;++b)for(unsigned i=0;i<TEST_WORDS/4;++i){
  while(!d.load_ready)tick();d.load_valid=1;d.load_target=b;d.load_index=i;for(unsigned j=0;j<4;++j)d.load_data[j]=0x16600000u+b*0x10000u+i*4+j;tick();d.load_valid=0;d.eval();
 }
 while(!d.cmd_ready)tick();
 // Simultaneous command and host read must have a winner, not deadlock.
 d.cmd_valid=1;d.cmd_op=7;d.rd_valid=1;d.rd_index=0;d.rd_bank=0;d.eval();ck(d.cmd_ready);ck(!d.rd_ready);tick();d.cmd_valid=0;d.rd_valid=0;d.rsp_ready=1;tick();d.rsp_ready=0;
 for(unsigned n=0;n<10000;++n){
  d.rd_valid=(rng()%4)!=0;d.rd_bank=rng()%2;d.rd_index=rng()%(TEST_WORDS/4);d.rd_rsp_ready=(rng()%4)==0;d.eval();
  if(d.rd_rsp_valid){ck(!pending.empty());unsigned code=pending.front(),b=code/1024,i=code%1024;for(unsigned j=0;j<4;++j)ck(d.rd_data[j]==0x16600000u+b*0x10000u+i*4+j);if(d.rd_rsp_ready)pending.pop_front();}
  if(d.rd_valid&&d.rd_ready)pending.push_back(d.rd_bank*1024+d.rd_index);
  ck(pending.size()<=4);tick();
 }
 d.rd_valid=0;d.rd_rsp_ready=1;d.eval();for(unsigned n=0;!pending.empty()||d.rd_rsp_valid;++n){ck(n<100);if(d.rd_rsp_valid){ck(!pending.empty());unsigned code=pending.front();for(unsigned j=0;j<4;++j)ck(d.rd_data[j]==0x16600000u+(code/1024)*0x10000u+(code%1024)*4+j);pending.pop_front();}tick();}
 // Reset cancels queued and in-flight responses.
 d.rd_valid=1;d.rd_rsp_ready=0;for(unsigned n=0;n<8;++n)tick();d.reset=1;tick();d.rd_valid=0;d.reset=0;for(unsigned n=0;n<8;++n){tick();ck(!d.rd_rsp_valid);}
 std::cout<<"{\"passed\":true,\"checks\":"<<checks<<",\"cycles\":"<<cycles<<"}\n";
 }catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}}
