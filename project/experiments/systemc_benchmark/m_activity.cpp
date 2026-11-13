// Native old220 M commands, with exact integer reference and gate VCD.
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
#include <array>

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
  void partial(const Operand& o,bool clear=true,bool readback=true) {
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
    command(10,0,1|2|(clear?4:0)|(1<<4)|(1<<8)|(1<<12)|(1<<15));
    const uint64_t duration=cycles-begin;
    // Accepted profile is checked, rather than assumed by the driver.
    std::cout<<"EXECUTE_CYCLES "<<duration<<"\n";
    if(!readback)return;
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
    if(argc!=4&&argc!=6)throw std::runtime_error("usage: M-activity operands.tsv output.vcd active|idle|stream [begin_K count_K]");
    std::ifstream file(argv[1]);std::vector<Operand> inputs;Operand o;
    while(file>>o.a>>o.b>>o.shift){
      if(o.a< -32768||o.a>32767||o.b< -32768||o.b>32767||o.shift<0||o.shift>31)
        throw std::runtime_error("invalid native operands");
      inputs.push_back(o);
    }
    if(inputs.empty())throw std::runtime_error("no captured operands");
    Bench bench;bench.reset();bench.command(6,0,0);
    if(std::string(argv[3]).rfind("tile",0)==0) {
      const std::string mode=argv[3];
      const bool narrow=mode=="tile-narrow"||mode=="tile-narrow-idle";
      const bool idle=mode=="tile-idle"||mode=="tile-narrow-idle";
      if(mode!="tile"&&mode!="tile-idle"&&!narrow)throw std::runtime_error("invalid tile mode");
      if(argc!=4||inputs.size()!=32*8*3)throw std::runtime_error("expected real K32 N8 tile");
      std::array<int64_t,8> expected{};std::array<uint64_t,3> duration{};
      for(unsigned k=0;k<32;++k)for(unsigned n=0;n<8;++n)for(unsigned c=0;c<3;++c){
        const auto& x=inputs[(k*8+n)*3+c];
        if(x.shift!=(c?16:0)|| (c==2&&x.a!=0&&x.a!=1))throw std::runtime_error("tile component order");
        expected[n]+=int64_t(x.a)*x.b*(int64_t(1)<<x.shift);
      }
      if(!idle)bench.open(argv[2]);
      auto start=bench.cycles,start_ps=bench.ps;
      auto& d=bench.dut;d.b_bank=0;d.b_wide=1;
      for(unsigned t=0;t<4;++t)for(unsigned half=0;half<2;++half){
        for(unsigned j=0;j<16;++j)d.b_data[j]=0;
        for(unsigned n=0;n<4;++n)for(unsigned k=0;k<8;++k){
          const unsigned j=n*8+k;
          d.b_data[j/2]|=uint32_t(uint16_t(inputs[((t*8+k)*8+half*4+n)*3].b))<<(16*(j%2));
        }
        d.b_tile=t;d.b_half=half;d.b_valid=1;d.eval();
        if(!d.b_ready)throw std::runtime_error("tile B stalled");bench.tick();
      }
      d.b_valid=0;d.eval();
      for(unsigned c=0;c<3;++c){
        bench.command(4,0,uint64_t(1)|(uint64_t(c?16:0)<<16));
        const bool wide=!(narrow&&c==2);
        d.a_bank=0;d.a_row=0;d.a_wide=wide;
        for(unsigned t=0;t<4;++t){
          for(unsigned j=0;j<4;++j)d.a_data[j]=0;
          for(unsigned k=0;k<8;++k){
            const auto value=inputs[((t*8+k)*8)*3+c].a;
            if(wide)d.a_data[k/2]|=uint32_t(uint16_t(value))<<(16*(k%2));
            else d.a_data[k/4]|=uint32_t(uint8_t(value))<<(8*(k%4));
          }
          d.a_tile=t;d.a_valid=1;d.eval();
          if(!d.a_ready)throw std::runtime_error("tile A stalled");bench.tick();
        }
        d.a_valid=0;d.eval();const auto begin=bench.cycles;
        bench.command(10,0,unsigned(wide)|2|(c==0?4:0)|(8<<4)|(8<<8)|(4<<12)|(1<<15));
        duration[c]=bench.cycles-begin;
      }
      if(idle){bench.open(argv[2]);start=bench.cycles;start_ps=bench.ps;
        for(unsigned i=0;i<256;++i)bench.tick();}
      bench.trace.dump(bench.ps);bench.trace.close();bench.tracing=false;
      const auto cycles=bench.cycles-start,window=bench.ps-start_ps;
      for(unsigned pair=0;pair<4;++pair){
        auto actual=bench.command(3,pair,0);
        if(int64_t(actual)!=expected[pair*2]||int64_t(actual>>64)!=expected[pair*2+1])
          throw std::runtime_error("packed tile S64 differs");
      }
      std::cout<<"ACTIVITY {\"cycles\":"<<cycles<<",\"window_ps\":"<<window
               <<",\"nominal_clock_hz\":300000000,\"scalar_components\":768,\"execute_cycles\":["
               <<duration[0]<<","<<duration[1]<<","<<duration[2]<<"],\"s64_prefixes\":[";
      for(unsigned n=0;n<8;++n)std::cout<<(n?",":"")<<expected[n];
      std::cout<<"],\"passed\":true}\n";return 0;
    }
    const bool stream_idle=std::string(argv[3])=="stream-idle";
    if(std::string(argv[3])=="stream"||stream_idle) {
      if(argc!=6||inputs.size()!=2048*3)throw std::runtime_error("expected complete 2048-K S32 stream");
      const unsigned begin=std::stoul(argv[4]),count=std::stoul(argv[5]);
      if(!count||begin+count>2048)throw std::runtime_error("invalid stream window");
      uint64_t start_ps=0,start_cycles=0;
      int64_t expected=0;
      for(unsigned i=0;i<(begin+count)*3;++i) {
        if(inputs[i].shift!=(i%3?16:0))throw std::runtime_error("invalid S32 component order");
        if(!stream_idle&&i==begin*3){bench.open(argv[2]);start_ps=bench.ps;start_cycles=bench.cycles;}
        bench.partial(inputs[i],i==0,false);
        expected+=int64_t(inputs[i].a)*inputs[i].b*(int64_t(1)<<inputs[i].shift);
      }
      if(stream_idle){
        bench.open(argv[2]);start_ps=bench.ps;start_cycles=bench.cycles;
        for(unsigned i=0;i<256;++i)bench.tick();
      }
      bench.trace.dump(bench.ps);bench.trace.close();bench.tracing=false;
      const auto window_ps=bench.ps-start_ps,window_cycles=bench.cycles-start_cycles;
      auto actual=bench.command(3,0,0);
      if(int64_t(actual)!=expected||int64_t(actual>>64)!=0)throw std::runtime_error("accumulated native prefix differs");
      std::cout<<"ACTIVITY {\"cycles\":"<<window_cycles<<",\"window_ps\":"<<window_ps
               <<",\"nominal_clock_hz\":300000000,\"operands\":"<<(stream_idle?0:count*3)
               <<",\"warmup_operands\":"<<(stream_idle?(begin+count):begin)*3
               <<",\"s64_prefix\":"<<expected<<",\"passed\":true}\n";
      return 0;
    }
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
