#include "s_port.hpp"
#include "Vblock_feed_s16k.h"
#include "verilated.h"
#include <random>
#include <iostream>
#include <stdexcept>
struct Test:sc_module{
 sc_clock clk{"clk",sc_time(1,SC_NS)};SPort s{"s"};Vblock_feed_s16k d;std::mt19937_64 rng{157803};bool passed=false;uint64_t checks=0;
 SC_HAS_PROCESS(Test);Test(sc_module_name n):sc_module(n){s.clk(clk);SC_THREAD(run);}
 void ck(bool v,const char*text){++checks;if(!v)throw std::runtime_error(text);}
 void compare(){ck(bool(d.ready)==s.ready.read(),"narrow ready");ck(bool(d.wide_ready)==s.wide_ready.read(),"wide ready");ck(bool(d.valid)==s.valid.read(),"narrow valid");ck(bool(d.wide_valid)==s.wide_valid.read(),"wide valid");for(unsigned i=0;i<4;++i)ck(d.dout[i]==s.dout.read().range(i*32+31,i*32).to_uint(),"narrow payload");for(unsigned i=0;i<16;++i)ck(d.wide_dout[i]==s.wide_dout.read().range(i*32+31,i*32).to_uint(),"wide payload");}
 void tick(){wait(SC_ZERO_TIME);wait(SC_ZERO_TIME);d.clk=0;d.reset=s.reset.read();d.req=s.req.read();d.wr=s.wr.read();d.addr=s.addr.read().to_uint();d.take=s.take.read();d.wide_req=s.wide_req.read();d.wide_addr=s.wide_addr.read().to_uint();d.wide_take=s.wide_take.read();for(unsigned i=0;i<4;++i)d.din[i]=s.din.read().range(i*32+31,i*32).to_uint();d.eval();compare();wait(clk.posedge_event());wait(SC_ZERO_TIME);wait(SC_ZERO_TIME);d.clk=1;d.eval();compare();}
 void run(){try{
  s.reset=true;s.req=false;s.wide_req=false;s.take=true;s.wide_take=true;
  // Skip comparison before the first common reset edge: physical RAM is unknown.
  d.reset=1;d.clk=0;d.eval();wait(clk.posedge_event());wait(SC_ZERO_TIME);wait(SC_ZERO_TIME);d.clk=1;d.eval();s.reset=false;
  for(unsigned i=0;i<1024;++i){s.req=true;s.wr=true;s.addr=i;sc_biguint<128>data;for(unsigned w=0;w<4;++w)data.range(w*32+31,w*32)=uint32_t(rng());s.din=data;tick();}
  for(unsigned i=0;i<20000;++i){s.reset=i%997==0;s.req=rng()%3!=0;s.wr=rng()&1;s.addr=rng()%1024;s.take=rng()%3!=0;s.wide_req=rng()%3!=0;s.wide_addr=rng()%256;s.wide_take=rng()%3!=0;sc_biguint<128>data;for(unsigned w=0;w<4;++w)data.range(w*32+31,w*32)=uint32_t(rng());s.din=data;tick();}
  ck(s.conflicts>100,"arbitration not covered");ck(s.held_narrow>100&&s.held_wide>100,"backpressure not covered");passed=true;std::cout<<"{\"passed\":true,\"signal_checks\":"<<checks<<",\"cycles\":21024,\"wide_narrow_conflicts\":"<<s.conflicts<<",\"narrow_held\":"<<s.held_narrow<<",\"wide_held\":"<<s.held_wide<<"}\n";
 }catch(const std::exception&e){std::cerr<<e.what()<<'\n';}sc_stop();}
};
int sc_main(int argc,char**argv){Verilated::commandArgs(argc,argv);Test test("test");sc_start();return test.passed?0:1;}
