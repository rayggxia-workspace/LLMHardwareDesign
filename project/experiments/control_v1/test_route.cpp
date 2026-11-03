#include "Vcontrol_route.h"
#include "verilated.h"
#include <array>
#include <random>
#include <iostream>
#include <cstdlib>
#ifndef TEST_ENDPOINTS
#define TEST_ENDPOINTS 7
#endif
static unsigned checks=0;
static void need(bool b,const char*m){++checks;if(!b){std::cerr<<m<<"\n";std::exit(1);}}
int main(int argc,char**argv){Verilated::commandArgs(argc,argv);Vcontrol_route v;std::mt19937 rng{162};std::array<unsigned,TEST_ENDPOINTS> sent{};std::array<bool,TEST_ENDPOINTS> half{};
 bool consumer_half=false;unsigned consumer_owner=0,commands=0,completions=0;
 v.clk=0;v.task_valid=0;v.task_endpoint=0;v.cmd_ready=0;v.endpoint_valid=0;v.endpoint_last=0;v.done_ready=0;for(unsigned n=0;n<TEST_ENDPOINTS;++n)v.endpoint_data[n]=0;
 auto edge=[&](){v.clk=1;v.eval();v.clk=0;v.eval();};v.reset=1;edge();edge();v.reset=0;
 for(unsigned cycle=0;cycle<20000;++cycle){v.task_valid=rng()%3!=0;v.task_endpoint=rng()%16;v.cmd_ready=rng()%(1u<<TEST_ENDPOINTS);v.done_ready=rng()%4!=0;v.endpoint_valid=0;v.endpoint_last=0;
  for(unsigned n=0;n<TEST_ENDPOINTS;++n){if(sent[n]<200)v.endpoint_valid|=1u<<n;if(half[n])v.endpoint_last|=1u<<n;v.endpoint_data[n]=(n<<24)|(sent[n]<<1)|unsigned(half[n]);}v.eval();
  need(v.cmd_valid==(v.task_valid&&v.task_endpoint<TEST_ENDPOINTS?(1u<<v.task_endpoint):0),"correct command destination");
  need(v.task_ready==(v.task_endpoint<TEST_ENDPOINTS && bool(v.cmd_ready&(1u<<v.task_endpoint))),"selected destination credit");if(v.task_valid&&v.task_ready)++commands;
  if(v.done_valid&&v.done_ready){unsigned owner=v.done_data>>24;need(owner<TEST_ENDPOINTS && v.endpoint_ready==(1u<<owner),"completion owner");
   need(v.done_last==consumer_half,"two-flit completion boundary");if(consumer_half)need(owner==consumer_owner,"no interleaved completion packet");else consumer_owner=owner;
   need(v.done_data==((owner<<24)|(sent[owner]<<1)|unsigned(half[owner])),"exact completion payload");consumer_half=!consumer_half;half[owner]=!half[owner];if(!half[owner]){++sent[owner];++completions;}}
  edge();
 }
 need(completions==200*TEST_ENDPOINTS && commands>1000 && !consumer_half,"finite traffic drains");std::cout<<"{\"passed\":true,\"checks\":"<<checks<<"}\n";
}
