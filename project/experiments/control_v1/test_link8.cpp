#include "Vcontrol_link8.h"
#include "verilated.h"
#include <iostream>
#include <random>
int main(int argc,char**argv){
 Verilated::commandArgs(argc,argv);Vcontrol_link8 v;std::mt19937 rng{162};unsigned checks=0;
 auto check=[&](unsigned expected){++checks;if(v.out_data!=expected){std::cerr<<"link isolation/payload mismatch\n";return false;}return true;};
 // Establish the declared synchronous reset contract before observing outputs.
 v.clk=0;v.reset=1;v.in_data=0;v.eval();v.clk=1;v.eval();if(!check(0))return 1;
 bool active=false;
 for(unsigned cycle=0;cycle<30000;++cycle){
  v.clk=0;v.reset=cycle<4||rng()%17==0;v.in_data=rng()&255;v.eval();if(!check(active?v.in_data:0))return 1;
  active=!v.reset;v.clk=1;v.eval();if(!check(active?v.in_data:0))return 1;
  // All payload changes pass without a new edge while active. Changing reset
  // between edges must not change the registered isolation state.
  for(unsigned turn=0;turn<4;++turn){v.in_data=rng()&255;v.reset=!v.reset;v.eval();if(!check(active?v.in_data:0))return 1;}
 }
 std::cout<<"{\"passed\":true,\"checks\":"<<checks<<",\"cycles\":30000,\"payload_pipeline_stages\":0,\"reset_isolation_state_bits\":1}\n";
}
