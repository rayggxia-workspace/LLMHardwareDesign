// Real N RTL executes the compiler transcript; independent NEngine uses [x,0].
#include "Vblock_v2_n.h"
#include "verilated.h"
#include "n.hpp"
#include <array>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <stdexcept>

class Driver {
 Vblock_v2_n dut;
 uint64_t cycles=0;
 void tick(){dut.clk=0;dut.eval();dut.clk=1;dut.eval();++cycles;}
public:
 Driver(){dut.reset=1;dut.cmd_valid=0;dut.rsp_ready=0;tick();tick();dut.reset=0;tick();}
 uint16_t execute(unsigned op,unsigned count,uint64_t raw,unsigned stall){
  for(unsigned wait=0;!dut.cmd_ready;++wait){if(wait>10000)throw std::runtime_error("N command timeout");tick();}
  dut.cmd_op=op;dut.cmd_count=count;dut.cmd_param=0;
  dut.cmd_data[0]=uint32_t(raw);dut.cmd_data[1]=uint32_t(raw>>32);
  dut.cmd_data[2]=0x12345678;dut.cmd_data[3]=0x87654321;
  // Zero really is a zero packet, including all lanes.
  if(!raw)for(unsigned i=0;i<4;++i)dut.cmd_data[i]=0;
  for(unsigned i=0;i<4;++i)dut.cmd_aux[i]=0;
  dut.cmd_valid=1;tick();dut.cmd_valid=0;
  for(unsigned wait=0;!dut.rsp_valid;++wait){if(wait>10000)throw std::runtime_error("N response timeout");tick();}
  std::array<uint32_t,4> reply{};for(unsigned i=0;i<4;++i)reply[i]=dut.rsp_data[i];
  const bool error=dut.rsp_error,saturated=dut.rsp_saturated;
  for(unsigned i=0;i<stall;++i){tick();
   if(!dut.rsp_valid||dut.rsp_error!=error||dut.rsp_saturated!=saturated)throw std::runtime_error("N stalled flags changed");
   for(unsigned j=0;j<4;++j)if(reply[j]!=dut.rsp_data[j])throw std::runtime_error("N stalled payload changed");
  }
  dut.rsp_ready=1;tick();dut.rsp_ready=0;
  if(error)throw std::runtime_error("N native command rejected");
  if(op==3&&(reply[0]>>16||reply[1]||reply[2]||reply[3]))throw std::runtime_error("N EXP record is not zero extended");
  return uint16_t(reply[0]);
 }
 uint64_t ticks()const{return cycles;}
};

int main(int argc,char** argv){try{
 Verilated::commandArgs(argc,argv);if(argc<2)throw std::runtime_error("transcript argument required");
 std::ifstream input(argv[1]);if(!input)throw std::runtime_error("missing transcript");Driver driver;
 int value;unsigned commands,cases=0,negative=0;uint64_t reads=0;
 while(input>>value>>commands){
  blocks::NEngine oracle;blocks::NCommand c;oracle.execute(c);
  c=blocks::NCommand{};c.op=blocks::NCommand::Op::Stats;c.count=2;c.data[0]=uint16_t(value);c.data[1]=0;oracle.execute(c);
  c=blocks::NCommand{};c.op=blocks::NCommand::Op::Finalize;oracle.execute(c);
  c=blocks::NCommand{};c.op=blocks::NCommand::Op::Exp;c.count=1;c.data[0]=uint16_t(value);
  const auto expected=oracle.execute(c);if(expected.error)throw std::runtime_error("independent reference error");
  uint16_t actual=0;unsigned exp_commands=0;
  for(unsigned i=0;i<commands;++i){unsigned op,count;uint64_t raw;
   if(!(input>>op>>count>>raw))throw std::runtime_error("short transcript");
   auto result=driver.execute(op,count,raw,(cases+i)%4);if(op==1||op==3)++reads;
   if(op==3){actual=result;++exp_commands;}
  }
  if(exp_commands!=1||actual!=uint16_t(expected.lane[0])){
   std::cerr<<"NEXP_SEMANTIC_MISMATCH input="<<value<<" actual="<<actual<<" expected="<<expected.lane[0]<<'\n';return 3;
  }
  ++cases;if(value<0)++negative;
 }
 if(cases==0||!input.eof())throw std::runtime_error("empty or malformed transcript");
 std::cout<<"NEXP_NATIVE_PASS cases="<<cases<<" negative="<<negative<<" scalar_reads="<<reads
  <<" driver_cycles_with_backpressure="<<driver.ticks()<<" scope=native_N_only\n";return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
