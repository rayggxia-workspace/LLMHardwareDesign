#include "Vcontrol_status.h"
#include "verilated.h"
#include <cstdlib>
#include <iostream>
#include <random>
int main(int argc,char**argv){
 Verilated::commandArgs(argc,argv);Vcontrol_status v;std::mt19937 rng{162};bool expected=false;unsigned checks=0;
 for(unsigned n=0;n<20000;++n){
  v.clk=0;v.reset=n<4 || n%97==0;v.queue_error=(rng()%13==0)?(1u<<(rng()%7)):0;
  v.dma_error=rng()%31==0;v.transaction_error=rng()%29==0;v.eval();
  expected=v.reset?false:(expected || v.queue_error || v.dma_error || v.transaction_error);
  v.clk=1;v.eval();++checks;if(bool(v.protocol_error)!=expected){std::cerr<<"sticky status mismatch\n";return 1;}
 }
 std::cout<<"{\"passed\":true,\"checks\":"<<checks<<",\"cycles\":20000}\n";
}
