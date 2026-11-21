// Standalone compact E activity calibration. Samples are explicitly scoped;
// they do not reproduce a full compiler trace or qualify full-chip energy.
#include "Vblock_v2_e_compact.h"
#include "verilated.h"
#include "verilated_vcd_c.h"
#include <algorithm>
#include <array>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

struct Sample { int a,b,shift; };
struct EBench {
 Vblock_v2_e_compact dut{"dut"};
 VerilatedVcdC trace;
 uint64_t cycles=0,ps=0;
 bool tracing=false;
 void tick(){
  uint64_t next=((cycles+1)*10000+2)/3;
  dut.clk=0;dut.eval();if(tracing)trace.dump(ps);ps+=(next-ps)/2;
  dut.clk=1;dut.eval();if(tracing)trace.dump(ps);ps=next;
  dut.clk=0;dut.eval();++cycles;
 }
 void reset(){
  dut.reset=1;dut.in_valid=0;dut.out_ready=0;dut.in_op=0;dut.in_shift=0;
  for(unsigned i=0;i<4;++i)dut.in_data[i]=0;
  tick();tick();dut.reset=0;tick();
 }
 uint64_t command(unsigned op,const Sample&s){
  const auto begin=cycles;
  // Low lane only, matching scalar record service packing. Other lanes zero.
  int a=op==5?s.a:s.b,b=op==5?0:s.a,c=s.a<0;
  for(unsigned beat=0;beat<(op==6?3u:2u);++beat){
   dut.in_op=op;dut.in_shift=0;
   for(unsigned i=0;i<4;++i)dut.in_data[i]=0;
   dut.in_data[0]=uint16_t(beat==0?a:beat==1?b:c);
   dut.in_valid=1;dut.eval();
   if(!dut.in_ready)throw std::runtime_error("E beat not ready");
   tick();dut.in_valid=0;
  }
  unsigned guard=0;
  while(!dut.out_valid){if(++guard>1000)throw std::runtime_error("E response timeout");tick();}
  const int expected=op==5?std::min(a,b):(c?a:b);
  if(dut.out_error||dut.out_saturated||int16_t(dut.out_data[0])!=expected||
     (dut.out_data[0]>>16)||dut.out_data[1]||dut.out_data[2]||dut.out_data[3])
   throw std::runtime_error("E independent integer result mismatch");
  dut.out_ready=1;tick();dut.out_ready=0;dut.eval();
  return cycles-begin;
 }
};
int main(int argc,char**argv){
 Verilated::commandArgs(argc,argv);Verilated::traceEverOn(true);
 try{
  if(argc<5)throw std::runtime_error("usage: operands.tsv output.vcd active|idle op [Verilator options]");
  unsigned op=std::stoul(argv[4]);if(op!=5&&op!=6)throw std::runtime_error("sample covers Min/Select only");
  std::ifstream file(argv[1]);std::vector<Sample> samples;Sample s;
  while(file>>s.a>>s.b>>s.shift){
   if(s.a< -32768||s.a>32767||s.b< -32768||s.b>32767)throw std::runtime_error("not S16");
   samples.push_back(s);
  }
  if(samples.empty())throw std::runtime_error("missing real operand fixture");
  EBench b;b.reset();uint64_t period=0;
  for(unsigned i=0;i<512;++i){
   auto ticks=b.command(op,samples[i%samples.size()]);
   if(i&&period!=ticks)throw std::runtime_error("nonconstant serialized sample period");period=ticks;
  }
  bool active=std::string(argv[3])=="active";
  if(!active&&std::string(argv[3])!="idle")throw std::runtime_error("bad mode");
  b.dut.trace(&b.trace,99);b.trace.open(argv[2]);b.tracing=true;
  auto begin=b.cycles,start_ps=b.ps;
  if(active)for(unsigned i=0;i<512;++i)b.command(op,samples[i%samples.size()]);
  else for(uint64_t i=0;i<512*period;++i)b.tick();
  b.dut.eval();b.trace.dump(b.ps);b.trace.close();b.tracing=false;
  std::cout<<"FUNCTIONAL {\"timing\":{\"cycles\":"<<b.cycles-begin
   <<",\"window_ps\":"<<b.ps-start_ps<<",\"nominal_clock_hz\":300000000"
   <<",\"commands\":"<<(active?512:0)<<",\"serialized_command_cycles\":"<<period
   <<",\"op\":"<<op<<",\"passed\":true},\"scope\":\"scalar low-lane compact E representative sample; not whole-workload energy\"}\n";
  return 0;
 }catch(const std::exception&e){std::cerr<<e.what()<<"\n";return 1;}
}
