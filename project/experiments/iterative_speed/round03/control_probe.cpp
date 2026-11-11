// Standalone finite control replay. No SystemC, tensor math, or cost guessing.
#include "finite_control.hpp"
#include <iostream>
#include <limits>
#include <sstream>
#include <string>

int main(int argc,char** argv){
 try{
  if(argc!=2||(std::string(argv[1])!="1"&&std::string(argv[1])!="2")){
   throw std::invalid_argument("usage: control_probe BUFFERS(1|2) < cycles.txt");
  }
  finite_m::Model model(argv[1][0]-'0');
  std::string line;std::uint64_t previous=0,rows=0;
  while(std::getline(std::cin,line)){
   if(line.empty()){continue;}
   std::array<std::uint64_t,20> a{};std::istringstream input(line);
   for(auto& value:a){if(!(input>>value)){throw std::invalid_argument("expected20 unsigned input fields");}}
   std::string extra;if(input>>extra){throw std::invalid_argument("extra input field");}
   if(rows&&a[0]!=previous+1){throw std::invalid_argument("cycle trace must be contiguous");}
   previous=a[0];++rows;
   for(unsigned n:{1u,2u,10u,11u,15u,16u,17u,18u,19u}){
    if(a[n]>1){throw std::invalid_argument("non-Boolean signal");}
   }
   if(a[4]>std::numeric_limits<std::uint32_t>::max()){throw std::invalid_argument("tag wider than32bits");}
   for(unsigned n:{3u,5u,6u,7u,8u,9u,12u,13u,14u}){
    if(a[n]>std::numeric_limits<unsigned>::max()){throw std::invalid_argument("command field too wide");}
   }
   finite_m::Inputs in{};
   in.reset=a[1]!=0;in.command_valid=a[2]!=0;
   auto& c=in.command;c.ctx=static_cast<unsigned>(a[3]);c.tag=static_cast<unsigned>(a[4]);
   c.ki=static_cast<unsigned>(a[5]);c.total=static_cast<unsigned>(a[6]);c.k=static_cast<unsigned>(a[7]);
   c.n=static_cast<unsigned>(a[8]);c.shift=static_cast<unsigned>(a[9]);c.first=a[10]!=0;c.last=a[11]!=0;
   c.a=static_cast<unsigned>(a[12]);c.b=static_cast<unsigned>(a[13]);c.out=static_cast<unsigned>(a[14]);
   in.read_ready=a[15]!=0;in.read_response=a[16]!=0;in.write_ready=a[17]!=0;in.write_ack=a[18]!=0;in.done_ready=a[19]!=0;
   const auto o=model.observe(in);
   std::cout<<"CONTROL "<<a[0]<<' '<<o.command_ready<<' '<<o.read_valid<<' '<<o.read_address<<' '<<o.read_take
    <<' '<<o.write_valid<<' '<<o.write_address<<' '<<o.write_take<<' '<<o.done_valid
    <<' '<<o.done_ctx<<' '<<o.done_tag<<' '<<o.done_next<<' '<<o.done_last<<' '<<o.done_error
    <<' '<<o.leaf_valid<<' '<<o.leaf_ready<<' '<<o.leaf_fire<<' '<<o.leaf_ctx<<' '<<o.leaf_end<<' '<<o.leaf_sequence
    <<' '<<o.commit<<' '<<o.commit_ctx<<' '<<o.commit_end<<' '<<o.final_capture
    <<' '<<o.reservations<<' '<<o.reads_outstanding<<' '<<o.live_buffers<<'\n';
   model.tick(in);
  }
  if(rows==0){throw std::invalid_argument("empty control replay");}
  std::cerr<<"FINITE_CONTROL_REPLAY_PASS cycles="<<rows<<'\n';return 0;
 }catch(const std::exception& error){std::cerr<<"CONTROL_ERROR "<<error.what()<<'\n';return 2;}
}
