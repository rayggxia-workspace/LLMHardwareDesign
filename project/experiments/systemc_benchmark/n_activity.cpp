// Serialized native N factor/relative-exp samples, not whole-workload energy.
#include "Vblock_v2_n.h"
#include "verilated.h"
#include "verilated_vcd_c.h"
#include <array>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <map>
#include <stdexcept>
#include <string>
#include <vector>

struct Fixture {unsigned mode,epsilon,expected;std::vector<int16_t> values;};
struct NBench {
 Vblock_v2_n dut{"dut"};VerilatedVcdC trace;
 uint64_t cycles=0,ps=0;bool tracing=false;
 std::map<std::string,std::pair<uint64_t,uint64_t>> commands;
 void tick(){
  const auto next=((cycles+1)*10000+2)/3;
  dut.clk=0;dut.eval();if(tracing)trace.dump(ps);ps+=(next-ps)/2;
  dut.clk=1;dut.eval();if(tracing)trace.dump(ps);ps=next;
  dut.clk=0;dut.eval();++cycles;
 }
 void reset(){
  dut.reset=1;dut.cmd_valid=0;dut.cmd_op=0;dut.cmd_count=0;dut.cmd_param=0;dut.rsp_ready=0;
  for(unsigned i=0;i<4;++i)dut.cmd_data[i]=dut.cmd_aux[i]=0;
  tick();tick();dut.reset=0;tick();
 }
 void command(unsigned op,unsigned count,unsigned param,const std::array<uint32_t,4>&data,
              uint32_t expected=0,unsigned stall=0){
  auto begin=cycles;dut.cmd_op=op;dut.cmd_count=count;dut.cmd_param=param;
  for(unsigned i=0;i<4;++i){dut.cmd_data[i]=data[i];dut.cmd_aux[i]=0;}
  dut.cmd_valid=1;dut.eval();if(!dut.cmd_ready)throw std::runtime_error("N not ready at serialized boundary");
  tick();dut.cmd_valid=0;dut.eval();unsigned guard=0;
  while(!dut.rsp_valid){if(++guard>1000)throw std::runtime_error("N response timeout");tick();}
  auto check=[&](){
   if(!dut.rsp_valid||dut.rsp_error||dut.rsp_saturated||dut.rsp_data[0]!=expected||
      dut.rsp_data[1]||dut.rsp_data[2]||dut.rsp_data[3])
    throw std::runtime_error("N response differs from independent integer reference");
  };
  check();for(unsigned i=0;i<stall;++i){tick();check();}
  dut.rsp_ready=1;tick();dut.rsp_ready=0;dut.eval();
  if(!stall){
   auto key=std::to_string(op)+":"+std::to_string(count)+":"+std::to_string(op==0?param:0);
   auto &entry=commands[key];auto duration=cycles-begin;
   if(entry.first&&entry.second!=duration)throw std::runtime_error("N command timing depends on sampled data");
   ++entry.first;entry.second=duration;
  }
 }
 void service(const Fixture&f,bool stall=false){
  command(0,0,f.mode,{f.epsilon,0,0,0},0,stall?2:0);
  if(f.mode==0){
   // The reference exp is relative to max(x,0), not max(x) alone.
   command(1,2,0,{uint16_t(f.values.at(0)),0,0,0});
   command(2,0,0,{});
   command(3,1,0,{uint16_t(f.values.at(0)),0,0,0},f.expected);
  }else{
   for(auto x:f.values)command(1,1,0,{uint16_t(x),0,0,0});
   command(2,0,0,{});
   command(11,0,0,{},f.expected);
  }
 }
};
int main(int argc,char**argv){
 Verilated::commandArgs(argc,argv);Verilated::traceEverOn(true);
 try{
  if(argc<4)throw std::runtime_error("usage: n-fixture.tsv output.vcd active|idle [Verilator options]");
  std::ifstream file(argv[1]);std::vector<Fixture> fixtures;unsigned mode,epsilon,n,expected;
  while(file>>mode>>epsilon>>n>>expected){
   if(mode>2||!epsilon||!n||n>2048||(mode==0&&n!=1))throw std::runtime_error("unsupported N fixture contract");
   Fixture f{mode,epsilon,expected,{}};
   for(unsigned i=0;i<n;++i){int x;if(!(file>>x)||x< -32768||x>32767)throw std::runtime_error("invalid S16 fixture");f.values.push_back(int16_t(x));}
   fixtures.push_back(f);
  }
  if(fixtures.empty())throw std::runtime_error("missing N fixture");
  const std::string mode_name=argv[3];if(mode_name!="active"&&mode_name!="idle")throw std::runtime_error("invalid activity mode");
  NBench b;b.reset();for(auto &f:fixtures)b.service(f,true);
  constexpr unsigned repeats=8;uint64_t period=0;
  for(unsigned j=0;j<repeats;++j){auto start=b.cycles;for(auto &f:fixtures)b.service(f);if(j&&period!=b.cycles-start)throw std::runtime_error("nonconstant N service batch");period=b.cycles-start;}
  b.commands.clear();b.dut.trace(&b.trace,99);b.trace.open(argv[2]);b.tracing=true;
  auto start=b.cycles,start_ps=b.ps;
  if(mode_name=="active")for(unsigned j=0;j<repeats;++j)for(auto &f:fixtures)b.service(f);
  else for(uint64_t i=0;i<repeats*period;++i)b.tick();
  b.dut.eval();b.trace.dump(b.ps);b.trace.close();b.tracing=false;
  std::cout<<"FUNCTIONAL {\"timing\":{\"cycles\":"<<b.cycles-start<<",\"window_ps\":"<<b.ps-start_ps
   <<",\"nominal_clock_hz\":300000000,\"services\":"<<(mode_name=="active"?repeats*fixtures.size():0)
   <<",\"batch_cycles\":"<<period<<",\"passed\":true},\"commands\":{";
  bool first=true;for(auto &entry:b.commands){if(!first)std::cout<<",";first=false;
   std::cout<<"\""<<entry.first<<"\":{\"count\":"<<entry.second.first<<",\"serialized_cycles\":"<<entry.second.second<<"}";}
  std::cout<<"},\"backpressure_checked\":true,\"scope\":\"sampled scalar N factor/relative-exp services; not whole-model energy\"}\n";
  return 0;
 }catch(const std::exception&e){std::cerr<<e.what()<<"\n";return 1;}
}
