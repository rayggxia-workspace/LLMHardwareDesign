#include "Vcontrol_reset_distribution.h"
#include "verilated.h"
#include <random>
#include <iostream>
#ifndef TEST_RESET_BRANCHES
#define TEST_RESET_BRANCHES 25
#endif
int main(int argc,char**argv){
 Verilated::commandArgs(argc,argv);Vcontrol_reset_distribution v;std::mt19937 rng{162};unsigned checks=0;
 for(unsigned cycle=0;cycle<30000;++cycle){
  v.clk=0;v.reset_in=cycle<8 || rng()%7==0;v.eval();unsigned expected=v.reset_in?((1u<<TEST_RESET_BRANCHES)-1):0;
  v.clk=1;v.eval();++checks;
  if(v.reset_out!=expected){std::cerr<<"reset bank edge mismatch\n";return 1;}
  v.clk=0;v.eval();unsigned held=v.reset_out;v.reset_in=!v.reset_in;v.eval();++checks;
  if(v.reset_out!=held){std::cerr<<"reset bypasses registered boundary\n";return 1;}
 }
 std::cout<<"{\"passed\":true,\"checks\":"<<checks<<",\"cycles\":30000}\n";
}
