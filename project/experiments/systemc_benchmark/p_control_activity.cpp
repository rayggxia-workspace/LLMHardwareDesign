// Existing P native fixture assertions remain responsible for data correctness.
// Capture only deployed start through result ACK; final SRAM checks still run.
#include "Vtb_native_pair.h"
#include "verilated.h"
#include "verilated_vcd_c.h"
#include <iostream>
#include <memory>
#include <stdexcept>

int main(int argc,char**argv) {
 try {
  if(argc<2)throw std::runtime_error("usage: p-control-activity wave.vcd +MOTHER=... ...");
  auto context=std::make_unique<VerilatedContext>();context->commandArgs(argc,argv);
  context->traceEverOn(true);context->threads(1);
  auto top=std::make_unique<Vtb_native_pair>(context.get(),"bench");
  auto wave=std::make_unique<VerilatedVcdC>();top->trace(wave.get(),99);
  bool opened=false,closed=false;uint64_t first=0,last=0,first_cycle=0,last_cycle=0;
  while(!context->gotFinish()) {
   top->eval();
   if(top->benchmark_runtime&&!opened) {
    first=context->time();first_cycle=top->benchmark_cycle;wave->open(argv[1]);opened=true;
   }
   if(opened&&!closed) {
    wave->dump(context->time());
    if(!top->benchmark_runtime) {
     last=context->time();last_cycle=top->benchmark_cycle;wave->close();closed=true;
    }
   }
   if(context->gotFinish())break;
   if(!top->eventsPending())throw std::runtime_error("missing next fixture event");
   const uint64_t next=top->nextTimeSlot();
   if(next<=context->time())throw std::runtime_error("nonmonotone fixture clock");
   context->time(next);
  }
  top->final();
  if(!opened||!closed||last<=first||last_cycle<=first_cycle)
   throw std::runtime_error("positive complete deployed runtime window required");
  std::cout<<"FUNCTIONAL {\"timing\":{\"passed\":true,\"window_ps\":"<<last-first
   <<",\"window_cycles\":"<<last_cycle-first_cycle<<",\"first_ps\":"<<first
   <<",\"last_ps\":"<<last<<"},\"clock_hz\":300000000,\"full_model_qualified\":false}\n";
  return 0;
 }catch(const std::exception& error){std::cerr<<error.what()<<'\n';return 1;}
}
