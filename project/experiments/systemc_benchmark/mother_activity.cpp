// Timing/activity harness for the existing public-port mother regression.
// Testbench assertions check real program SRAM and finite peer messages.
#include "Vtb_mother.h"
#include "verilated.h"
#include "verilated_vcd_c.h"
#include <fstream>
#include <iostream>
#include <memory>
#include <stdexcept>

int main(int argc,char**argv) {
 try {
  if(argc<2)throw std::runtime_error("usage: mother-activity waveform.vcd +IMAGE=... ...");
  auto context=std::make_unique<VerilatedContext>();context->commandArgs(argc,argv);
  context->traceEverOn(true);context->threads(1);
  auto top=std::make_unique<Vtb_mother>(context.get(),"bench");
  auto wave=std::make_unique<VerilatedVcdC>();top->trace(wave.get(),99);
  bool started=false;uint64_t first=0,first_cycle=0,last=0;
  while(!context->gotFinish()) {
   top->eval();
   if(top->benchmark_runtime&&!started) {
    first=context->time();first_cycle=top->benchmark_cycle;wave->open(argv[1]);started=true;
   }
   if(started)wave->dump(context->time());
   if(context->gotFinish())break;
   if(!top->eventsPending())throw std::runtime_error("testbench has no next clock event");
   last=top->nextTimeSlot();
   if(last<=context->time())throw std::runtime_error("nonmonotone event time");
   context->time(last);
  }
  top->final();wave->close();
  if(!started||context->time()<=first)throw std::runtime_error("no positive runtime activity window");
  std::cout<<"FUNCTIONAL {\"timing\":{\"passed\":true,\"window_ps\":"<<context->time()-first
   <<",\"window_cycles\":"<<uint64_t(top->benchmark_cycle)-first_cycle
   <<",\"first_ps\":"<<first<<",\"last_ps\":"<<context->time()
   <<"},\"calls\":"<<top->benchmark_calls<<",\"results\":"<<top->benchmark_results
   <<",\"clock_hz\":300000000,\"finite_peer_delays_are_fixture_only\":true}\n";
  return 0;
 }catch(const std::exception&e){std::cerr<<e.what()<<"\n";return 1;}
}
