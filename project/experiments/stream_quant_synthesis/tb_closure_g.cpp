#include "Vclosure_g32.h"
#include "verilated.h"
#include <array>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <random>
#include <stdexcept>
#include <string>
#include <vector>
struct Row {uint64_t a,b;std::array<uint32_t,4> result;};
std::array<uint32_t,4> wide(std::string s){
 std::array<uint32_t,4> r{};size_t i=0;
 while(!s.empty()){size_t n=std::min<size_t>(8,s.size());if(i==4)throw std::runtime_error("width");
  r[i++]=uint32_t(std::stoul(s.substr(s.size()-n),nullptr,16));s.resize(s.size()-n);}
 return r;
}
int main(int argc,char** argv){
 try{
  if(argc<3)throw std::runtime_error("vectors stalls required");
  std::ifstream f(argv[1]);std::vector<Row> rows;std::string a,b,y;
  while(f>>a>>b>>y)rows.push_back({std::stoull(a,nullptr,16),std::stoull(b,nullptr,16),wide(y)});
  if(!f.eof()||rows.empty())throw std::runtime_error("vectors");
  const bool stalls=std::stoi(argv[2])!=0;std::mt19937 rng(24832);Vclosure_g32 d;
  auto tick=[&]{d.clk=0;d.eval();d.clk=1;d.eval();};
  d.reset=1;d.in_valid=0;d.out_ready=0;for(int i=0;i<3;++i)tick();d.reset=0;
  size_t sent=0,got=0;uint64_t cycles=0,first=0;bool holding=false,blocked=false;std::array<uint32_t,4> held{};
  for(;got<rows.size()&&cycles<1000000;++cycles){
   d.clk=0;d.eval();
   if(sent<rows.size()){
    holding=holding||!stalls||rng()%4!=0;d.in_valid=holding;d.in_a=rows[sent].a;d.in_b=rows[sent].b;
   }else d.in_valid=0;
   d.out_ready=!stalls||(cycles%73>=19&&rng()%5!=0);d.eval();
   if(blocked){if(!d.out_valid)throw std::runtime_error("lost stalled response");
    for(int j=0;j<4;++j)if(d.out_data[j]!=held[j])throw std::runtime_error("unstable response");}
   blocked=d.out_valid&&!d.out_ready;
   if(blocked)for(int j=0;j<4;++j)held[j]=d.out_data[j];
   if(d.out_valid&&d.out_ready){
    if(!got)first=cycles;
    for(int j=0;j<4;++j)if(d.out_data[j]!=rows[got].result[j])throw std::runtime_error("G32 arithmetic mismatch at "+std::to_string(got));
    ++got;
   }
   const bool accepted=d.in_valid&&d.in_ready;tick();if(accepted){++sent;holding=false;}
  }
  if(sent!=rows.size()||got!=rows.size())throw std::runtime_error("conservation");
  // Flush an actual held response, then ensure no stale payload survives reset.
  d.in_valid=1;d.in_a=rows[0].a;d.in_b=rows[0].b;d.out_ready=0;tick();d.in_valid=0;
  for(int i=0;i<8&&!d.out_valid;++i)tick();
  if(!d.out_valid)throw std::runtime_error("reset fixture");
  d.reset=1;for(int i=0;i<3;++i)tick();d.reset=0;d.out_ready=1;
  for(int i=0;i<8;++i){tick();if(d.out_valid)throw std::runtime_error("stale reset");}
  std::cout<<"{\"passed\":true,\"packets\":"<<got<<",\"cycles\":"<<cycles<<",\"first\":"<<first
           <<",\"stalls\":"<<(stalls?"true":"false")<<",\"reset_held\":true}\n";
 }catch(const std::exception& e){std::cerr<<e.what()<<"\n";return 1;}
}
