#include "Vblock_v2_g.h"
#include "verilated.h"
#include <cstdint>
#include <fstream>
#include <iostream>
#include <memory>
#include <random>
#include <stdexcept>
#include <vector>
struct Packet{unsigned gated;uint32_t x,up,y;unsigned sat;};
int main(int argc,char**argv){try{
 Verilated::commandArgs(argc,argv);if(argc!=2)throw std::runtime_error("vectors required");
 std::ifstream file(argv[1]);std::vector<Packet> packets;Packet value{};
 while(file>>std::dec>>value.gated>>std::hex>>value.x>>value.up>>value.y>>std::dec>>value.sat)packets.push_back(value);
 if(!file.eof()||packets.empty())throw std::runtime_error("invalid vectors");
 auto ptr=std::make_unique<Vblock_v2_g>();auto& d=*ptr;std::mt19937 rng(24817);
 auto tick=[&]{d.clk=0;d.eval();d.clk=1;d.eval();d.clk=0;d.eval();};
 d.reset=1;d.in_valid=0;d.out_ready=0;tick();tick();d.reset=0;
 size_t accepted=0,delivered=0,cycles=0;bool held=false;uint32_t held_data=0;bool held_sat=false;
 while(delivered<packets.size()){
  d.in_valid=accepted<packets.size();d.out_ready=cycles%71>=23&&rng()%5!=0;
  if(d.in_valid){auto& p=packets[accepted];d.in_fn=0;d.in_gated=p.gated;d.in_x=p.x;d.in_gate=p.up;}
  d.eval();if(held&&(!d.out_valid||d.out_data!=held_data||bool(d.out_saturated)!=held_sat))throw std::runtime_error("held response changed");
  bool take=d.in_valid&&d.in_ready;
  if(d.out_valid&&d.out_ready){
   if(delivered>=accepted)throw std::runtime_error("unrequested response");auto& p=packets[delivered];
   if(d.out_error||d.out_data!=p.y||unsigned(d.out_saturated)!=p.sat)throw std::runtime_error("real G vector mismatch at "+std::to_string(delivered));++delivered;
  }
  held=d.out_valid&&!d.out_ready;held_data=d.out_data;held_sat=d.out_saturated;tick();++cycles;if(take)++accepted;
  if(cycles>1000000)throw std::runtime_error("timeout");
 }
 if(accepted!=packets.size())throw std::runtime_error("conservation failure");
 std::cout<<"{\"passed\":true,\"packets\":"<<accepted<<",\"cycles\":"<<cycles<<",\"backpressure\":true}\n";return 0;
 }catch(const std::exception& e){std::cerr<<"FAIL "<<e.what()<<"\n";return 1;}}
