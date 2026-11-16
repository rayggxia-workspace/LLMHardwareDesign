#include "Va_scale_directory32.h"
#include "verilated.h"
#include <algorithm>
#include <array>
#include <cstdint>
#include <iostream>
#include <memory>
#include <numeric>
#include <random>
#include <stdexcept>
static void check(bool x,const char* why){if(!x)throw std::runtime_error(why);}
int main(int argc,char** argv){try{
 check(argc==3,"seed/init required");const unsigned seed=unsigned(std::stoul(argv[1])),initial=unsigned(std::stoul(argv[2]));
 std::mt19937 rng(seed);auto context=std::make_unique<VerilatedContext>();context->commandArgs(argc,argv);context->randReset(int(initial));context->randSeed(int(seed));
 auto model=std::make_unique<Va_scale_directory32>(context.get());auto& d=*model;
 auto tick=[&]{d.clk=1;d.eval();context->timeInc(1);d.clk=0;d.eval();context->timeInc(1);};
 d.reset=1;d.cfg_valid=0;d.publish_valid=0;d.storage_released=0;d.leases_drained=0;
 for(int i=0;i<3;++i)tick();d.reset=0;d.eval();
 unsigned publications=0,rejected=0;
 for(unsigned scope=0;scope<48;++scope){
  std::array<uint32_t,4> key={seed,scope,0xa0000000U+scope,0xdeadbeef};
  const unsigned first=(scope%10)*128,step=(scope%2)?384:128;
  for(unsigned w=0;w<4;++w){d.cfg_key[w]=key[w];d.publish_key[w]=key[w];d.lookup_key[w]=key[w];}
  d.cfg_first_kk=first;d.cfg_tiles=32;d.cfg_stride3=scope%2;d.cfg_valid=1;
  d.storage_released=0;d.leases_drained=1;d.eval();check(!d.cfg_ready,"rebound live S storage");tick();
  d.storage_released=1;d.leases_drained=0;d.eval();check(!d.cfg_ready,"rebound live A lease");tick();
  d.leases_drained=1;d.eval();check(d.cfg_ready,"valid directory cfg stalled");tick();d.cfg_valid=0;d.eval();check(!d.cfg_rejected,"valid cfg rejected");
  std::array<unsigned,32> order{};std::iota(order.begin(),order.end(),0);std::shuffle(order.begin(),order.end(),rng);
  for(auto index:order){
   d.lookup_kk=first+index*step;d.eval();check(!d.lookup_valid && d.lookup_shift==0,"uncommitted tile appeared ready");
   d.publish_kk=first+index*step;d.publish_shift=(index+scope)%18;d.publish_written_mask=0xfffe;d.publish_error=0;d.publish_valid=1;
   d.cfg_valid=1;d.eval();check(d.publish_ready&&!d.cfg_ready,"simultaneous publication/config deadlocked or overwrote");
   tick();++rejected;check(d.publish_rejected,"partial ACK mask accepted");d.cfg_valid=0;
   d.publish_written_mask=0xffff;d.publish_key[2]^=1;d.eval();tick();++rejected;check(d.publish_rejected,"wrong object metadata accepted");d.publish_key[2]^=1;
   d.publish_shift=18;d.eval();tick();++rejected;check(d.publish_rejected,"unsupported dynamic shift accepted");
   d.publish_shift=(index+scope)%18;d.publish_error=1;d.eval();tick();++rejected;check(d.publish_rejected,"numeric failure metadata accepted");d.publish_error=0;
   d.eval();tick();++publications;check(!d.publish_rejected,"valid commit rejected");d.publish_valid=0;d.eval();
   check(d.lookup_valid&&d.lookup_shift==(index+scope)%18,"committed scale mismatch");
   d.publish_shift=(index+scope+1)%18;d.publish_valid=1;d.eval();tick();++rejected;check(d.publish_rejected,"duplicate overwrote committed scale");
   d.publish_valid=0;d.eval();check(d.lookup_shift==(index+scope)%18,"duplicate changed committed scale");
  }
  d.lookup_kk=first+32*step;d.eval();check(!d.lookup_valid&&d.lookup_shift==0,"out-of-range lookup accepted");
  if(step==384){d.lookup_kk=first+128;d.eval();check(!d.lookup_valid,"foreign stripe tile accepted");}
  d.lookup_kk=first+1;d.eval();check(!d.lookup_valid,"unaligned lookup accepted");
  d.lookup_kk=first;d.lookup_key[0]^=1;d.eval();check(!d.lookup_valid,"wrong owner lookup accepted");d.lookup_key[0]^=1;
  d.cfg_tiles=0;d.cfg_valid=1;d.eval();tick();check(d.cfg_rejected,"invalid config accepted");d.cfg_valid=0;d.lookup_kk=first;d.eval();
  check(d.lookup_valid && d.lookup_shift==scope%18,"invalid config destroyed old metadata");
 }
 check(d.rejected_publications==rejected,"publication rejection accounting mismatch");
 std::cout<<"PASS scale_directory scopes=48 tiles="<<publications<<" rejected="<<rejected<<" initial="<<initial<<"\n";return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<"\n";return 1;}}
