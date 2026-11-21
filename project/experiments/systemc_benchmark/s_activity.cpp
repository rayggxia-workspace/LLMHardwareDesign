// Ordinary 128-bit private-S transactions; feeder transfers are not covered.
#ifdef S_FEEDER
#include "Vlocal_s_p.h"
using STop=Vlocal_s_p;
#else
#include "Vlocal_s_base.h"
using STop=Vlocal_s_base;
#endif
#include "verilated.h"
#include "verilated_vcd_c.h"
#include <array>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

using Word=std::array<uint32_t,4>;
struct SBench {
 STop dut{"dut"};VerilatedVcdC trace;
 uint64_t cycles=0,ps=0;bool tracing=false;
 std::array<Word,1024> memory{};
 uint64_t reads=0,writes=0,period=0;
 void tick(){
  const uint64_t next=((cycles+1)*10000+2)/3;
  dut.clk=0;dut.eval();if(tracing)trace.dump(ps);ps+=(next-ps)/2;
  dut.clk=1;dut.eval();if(tracing)trace.dump(ps);ps=next;
  dut.clk=0;dut.eval();++cycles;
 }
 void reset(){
  dut.reset=1;dut.req_valid=0;dut.req_write=0;dut.req_addr=0;
  for(unsigned i=0;i<4;++i)dut.req_data[i]=0;
  dut.rsp_ready=0;
#ifdef S_FEEDER
  dut.load_valid=0;dut.load_bank=0;dut.load_a_wide=0;dut.load_b_wide=0;
  dut.load_reuse_b=0;dut.load_rows=0;dut.load_tiles=0;
  dut.load_a_base=0;dut.load_b_base=0;dut.done_take=0;
  dut.a_ready=0;dut.b_ready=0;
#endif
  tick();tick();dut.reset=0;tick();
 }
 uint64_t command(bool write,unsigned addr,const Word&data,unsigned stall=0){
  const auto begin=cycles;
  dut.req_valid=1;dut.req_write=write;dut.req_addr=addr;
  for(unsigned i=0;i<4;++i)dut.req_data[i]=data[i];
  dut.eval();if(!dut.req_ready)throw std::runtime_error("S not ready at serialized boundary");
  tick();dut.req_valid=0;dut.eval();
  unsigned guard=0;
  while(!dut.rsp_valid){if(++guard>100)throw std::runtime_error("S response timeout");tick();}
  Word expected=write?Word{}:memory[addr];
  auto check=[&](){
   if(!dut.rsp_valid)throw std::runtime_error("S dropped held response");
   for(unsigned i=0;i<4;++i)if(dut.rsp_data[i]!=expected[i])
    throw std::runtime_error("S read/write-ACK differs from independent array");
  };
  check();for(unsigned i=0;i<stall;++i){tick();check();}
  dut.rsp_ready=1;tick();dut.rsp_ready=0;dut.eval();
  if(write){memory[addr]=data;++writes;}else ++reads;
  const auto elapsed=cycles-begin;
  if(!stall){if(period&&period!=elapsed)throw std::runtime_error("nonconstant serialized S period");period=elapsed;}
  return elapsed;
 }
 void quiesce(){
  // Restore every bank's registered output, both response slots and FIFO
  // pointers to the same state for active/idle subtraction. Total six commands.
  for(unsigned i=0;i<4;++i)command(false,i,Word{});
  command(true,0,Word{});command(true,0,Word{});
 }
};
int main(int argc,char**argv){
 Verilated::commandArgs(argc,argv);Verilated::traceEverOn(true);
 try{
  if(argc<5)throw std::runtime_error("usage: operands.tsv output.vcd active|idle read|write|mixed");
  std::ifstream file(argv[1]);int a,b,shift;std::vector<std::pair<int,int>> samples;
  while(file>>a>>b>>shift){
   if(a< -32768||a>32767||b< -32768||b>32767)throw std::runtime_error("fixture not S16 components");
   samples.emplace_back(a,b);
  }
  if(samples.empty())throw std::runtime_error("missing operand fixture");
  const std::string kind=argv[4],mode=argv[3];
  if(kind!="read"&&kind!="write"&&kind!="mixed")throw std::runtime_error("invalid transaction pattern");
  if(mode!="active"&&mode!="idle")throw std::runtime_error("invalid activity mode");
  auto data=[&](unsigned addr,bool alternate){
   Word w{};if(addr)w[0]=uint32_t(int32_t(alternate?samples[addr%samples.size()].second:samples[addr%samples.size()].first));
   return w;
  };
  SBench s;s.reset();
  for(unsigned i=0;i<1024;++i)s.command(true,i,data(i,false));
  // Probe native response ownership before the measured window.
  for(unsigned i=0;i<4;++i)s.command(false,i,Word{},i+1);
  s.quiesce();
  const auto initial=s.memory;
  s.dut.trace(&s.trace,99);s.trace.open(argv[2]);s.tracing=true;
  const auto begin=s.cycles,start_ps=s.ps,r0=s.reads,w0=s.writes;
  if(mode=="active"){
   if(kind=="read")for(unsigned i=0;i<512;++i)s.command(false,i,Word{});
   if(kind=="write")for(unsigned i=0;i<512;++i)s.command(true,i%256,data(i%256,i<256));
   if(kind=="mixed")for(unsigned i=0;i<128;++i){
    s.command(true,i,data(i,true));s.command(false,i,Word{});
    s.command(true,i,data(i,false));s.command(false,i,Word{});
   }
   s.quiesce();
  }else for(uint64_t i=0;i<518*s.period;++i)s.tick();
  if(initial!=s.memory)throw std::runtime_error("active window changed final SRAM contents");
  s.dut.eval();s.trace.dump(s.ps);s.trace.close();s.tracing=false;
  std::cout<<"FUNCTIONAL {\"timing\":{\"cycles\":"<<s.cycles-begin
   <<",\"window_ps\":"<<s.ps-start_ps<<",\"nominal_clock_hz\":300000000"
   <<",\"reads\":"<<s.reads-r0<<",\"writes\":"<<s.writes-w0
   <<",\"serialized_command_cycles\":"<<s.period<<",\"passed\":true}"
   <<",\"same_final_memory\":true,\"backpressure_checked\":true"
   <<",\"scope\":\"ordinary S port, representative sign-extended scalar records; no feeder or full-workload energy\"}\n";
  return 0;
 }catch(const std::exception&e){std::cerr<<e.what()<<"\n";return 1;}
}
