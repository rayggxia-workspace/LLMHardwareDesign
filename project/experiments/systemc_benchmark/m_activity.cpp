// Native old220 scalar M commands, with exact integer reference and gate VCD.
// Each input row is a real old220 S16 component, S16 weight and scale shift.
#include "Vblock_v2_m.h"
#include "verilated.h"
#include "verilated_vcd_c.h"
#include <cstdint>
#include <fstream>
#include <iostream>
#include <memory>
#include <stdexcept>
#include <string>
#include <vector>

struct Operand { int a,b,shift; };
struct Bench {
  Vblock_v2_m dut{"dut"};
  VerilatedVcdC trace;
  uint64_t ps=0,cycles=0;
  bool tracing=false;
  void tick() {
    const uint64_t next=((cycles+1)*10000+2)/3;
    dut.clk=0;dut.eval();if(tracing)trace.dump(ps);ps+=(next-ps)/2;
    dut.clk=1;dut.eval();if(tracing)trace.dump(ps);ps=next;
    dut.clk=0;dut.eval();++cycles;
  }
  void reset() {
    dut.reset=1;dut.cmd_valid=0;dut.a_valid=0;dut.b_valid=0;dut.rsp_ready=0;
    tick();tick();dut.reset=0;tick();
  }
  __uint128_t command(unsigned op,unsigned index,uint64_t data) {
    if(!dut.cmd_ready)throw std::runtime_error("M not ready");
    dut.cmd_op=op;dut.cmd_index=index;dut.cmd_data=data;dut.cmd_valid=1;tick();dut.cmd_valid=0;
    unsigned wait=0;
    while(!dut.rsp_valid){if(++wait>1000)throw std::runtime_error("M timeout");tick();}
    if(dut.rsp_error||dut.rsp_saturated)throw std::runtime_error("M command error/saturation");
    __uint128_t value=0;
    for(int i=3;i>=0;--i)value=(value<<32)|dut.rsp_data[i];
    dut.rsp_ready=1;tick();dut.rsp_ready=0;dut.eval();return value;
  }
  void partial(const Operand& o) {
    command(4,0,uint64_t(1)|(uint64_t(o.shift)<<16));
    dut.a_bank=0;dut.a_row=0;dut.a_tile=0;dut.a_wide=1;
    for(int i=0;i<4;++i)dut.a_data[i]=0;
    dut.a_data[0]=uint16_t(o.a);dut.a_valid=1;dut.eval();
    if(!dut.a_ready)throw std::runtime_error("M A stalled");
    tick();dut.a_valid=0;
    dut.b_bank=0;dut.b_tile=0;dut.b_wide=1;
    for(unsigned h=0;h<2;++h){
      for(int i=0;i<16;++i)dut.b_data[i]=0;
      if(h==0)dut.b_data[0]=uint16_t(o.b);
      dut.b_half=h;dut.b_valid=1;dut.eval();
      if(!dut.b_ready)throw std::runtime_error("M B stalled");
      tick();
    }
    dut.b_valid=0;dut.eval();
    const uint64_t begin=cycles;
    command(10,0,1|2|4|(1<<4)|(1<<8)|(1<<12)|(1<<15));
    const uint64_t duration=cycles-begin;
    // Accepted profile is checked, rather than assumed by the driver.
    std::cout<<"EXECUTE_CYCLES "<<duration<<"\n";
    auto result=command(3,0,0);
    const int64_t reference=int64_t(o.a)*int64_t(o.b)*(int64_t(1)<<o.shift);
    if(int64_t(result)!=reference||int64_t(result>>64)!=0)
      throw std::runtime_error("native S64 arithmetic differs");
  }
  void open(const char* file) {
    dut.trace(&trace,99);trace.open(file);tracing=true;
  }
};

int main(int argc,char** argv) {
  Verilated::commandArgs(argc,argv);Verilated::traceEverOn(true);
  try {
    if(argc!=4)throw std::runtime_error("usage: M-activity operands.tsv output.vcd active|idle");
    std::ifstream file(argv[1]);std::vector<Operand> inputs;Operand o;
    while(file>>o.a>>o.b>>o.shift){
      if(o.a< -32768||o.a>32767||o.b< -32768||o.b>32767||o.shift<0||o.shift>31)
        throw std::runtime_error("invalid native operands");
      inputs.push_back(o);
    }
    if(inputs.empty())throw std::runtime_error("no captured operands");
    Bench bench;bench.reset();bench.command(6,0,0);
    if(std::string(argv[3])=="idle")bench.partial(inputs.back());
    bench.open(argv[2]);
    const uint64_t begin=bench.ps,begin_cycles=bench.cycles;
    if(std::string(argv[3])=="active")for(auto& x:inputs)bench.partial(x);
    else if(std::string(argv[3])=="idle")for(unsigned i=0;i<256;++i)bench.tick();
    else throw std::runtime_error("unknown activity mode");
    bench.trace.dump(bench.ps);bench.trace.close();bench.tracing=false;
    std::cout<<"ACTIVITY {\"cycles\":"<<(bench.cycles-begin_cycles)<<",\"window_ps\":"<<bench.ps-begin
             <<",\"nominal_clock_hz\":300000000,\"operands\":"<<inputs.size()<<",\"passed\":true}\n";
    return 0;
  }catch(const std::exception& e){std::cerr<<e.what()<<"\n";return 1;}
}
