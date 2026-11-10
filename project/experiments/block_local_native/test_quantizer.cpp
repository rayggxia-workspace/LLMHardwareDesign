#include "Vs32_a16_tile_quantizer.h"
#include "verilated.h"
#include <algorithm>
#include <array>
#include <cstdint>
#include <deque>
#include <iostream>
#include <memory>
#include <random>
#include <stdexcept>
#include <tuple>

static void check(bool x,const char* why){if(!x)throw std::runtime_error(why);}
static int64_t rne(int64_t x,unsigned s){
 if(!s)return x;
 const int64_t divisor=int64_t(1)<<s;
 int64_t q=x/divisor,r=x%divisor;
 if(r<0){--q;r+=divisor;}
 const int64_t twice=2*r;
 return q+(twice>divisor || (twice==divisor && q%2!=0));
}
int main(int argc,char** argv){
 try{
  check(argc==3,"seed/init required");const unsigned seed=unsigned(std::stoul(argv[1])),initial=unsigned(std::stoul(argv[2]));
  std::mt19937 rng(seed);auto context=std::make_unique<VerilatedContext>();context->commandArgs(argc,argv);
  context->randReset(int(initial));context->randSeed(int(seed));auto model=std::make_unique<Vs32_a16_tile_quantizer>(context.get());auto& d=*model;
  auto tick=[&]{d.clk=1;d.eval();context->timeInc(1);d.clk=0;d.eval();context->timeInc(1);};
  d.reset=1;d.cmd_valid=0;d.cancel_valid=0;d.s_ready=0;d.rsp_valid=0;d.done_ready=0;
  for(int n=0;n<3;++n)tick();d.reset=0;d.eval();
  unsigned transactions=0,writes=0,stale=0,cancelled=0,numeric=0,invalid=0;uint32_t shifts=0;
  for(unsigned test=0;test<216;++test){
   std::array<std::array<uint32_t,4>,1024> memory{};std::array<int32_t,128> source{};
   const unsigned target_shift=(test/2)%18;
   uint64_t boundary=std::min(uint64_t(2147483647),uint64_t(32767)<<target_shift);
   for(unsigned n=0;n<128;++n){
    int64_t value=int64_t(rng()%(boundary+1));if(n%2)value=-value;
    source[n]=int32_t(value);
   }
   source[0]=int32_t(boundary);source[1]=-int32_t(boundary);
   if(test%9==0)source[31]=INT32_MIN;
   uint64_t maximum=0;for(auto x:source)maximum=std::max(maximum,x<0?uint64_t(-int64_t(x)):uint64_t(x));
   const uint64_t ratio=(maximum+32766)/32767;unsigned shift=0;while((uint64_t(1)<<shift)<ratio)++shift;
   const bool bad=test%24==0,stop=test%24==7,read_fault=test%24==9,write_fault=test%24==11;
   const bool bad_numeric=test%24==13;
   const bool known=test%2==0 || bad_numeric;
   const unsigned supplied_shift=bad_numeric?0:shift;
   if(bad_numeric){source.fill(1);source[8]=INT32_MAX;}
   for(unsigned n=0;n<128;++n)memory[32+n/4][n%4]=uint32_t(source[n]);
   std::array<uint32_t,4> owner={seed,test,0x80000000U+test,0xcafe1234U};
   for(unsigned n=0;n<4;++n){d.cmd_key[n]=owner[n];d.cancel_key[n]=owner[n];}
   d.cmd_generation=test+1;d.cmd_kk=uint16_t((test%86)*128);d.cmd_source=32;d.cmd_destination=256;
   d.cmd_shift_known=known;d.cmd_shift=supplied_shift;
   if(bad){
    ++invalid;
    switch((test/24)%6){case 0:d.cmd_destination=40;break;case 1:d.cmd_source=1010;break;
     case 2:d.cmd_destination=1010;break;case 3:d.cmd_shift_known=1;d.cmd_shift=18;break;
     case 4:d.cmd_kk=1;break;default:d.cmd_generation=0;break;}
   }
   check(d.cmd_ready,"quantizer did not drain");d.cmd_valid=1;d.eval();tick();d.cmd_valid=0;
   struct Request{unsigned due,address;uint32_t tag;bool write,fault;std::array<uint32_t,4> data;};
   std::deque<Request> pending;
   bool finished=false,stopped=false,offered_held=false,previous_held=false;
   unsigned accepted=0,acks=0,write_acks=0,write_requests=0,write_mask=0;
   std::tuple<uint32_t,uint32_t,uint32_t,std::array<uint32_t,4>> previous;
   for(unsigned cycle=0;cycle<12000 && !finished;++cycle){
    d.rsp_valid=0;d.rsp_error=0;d.cancel_valid=0;d.s_ready=rng()%4!=0;d.done_ready=rng()%4!=0;
    if(stop && accepted>=5 && !stopped)d.s_ready=0;
    d.eval();
    if(stop && accepted>=5 && d.s_valid && !stopped){d.cancel_valid=1;stopped=true;offered_held=true;}
    bool real=false;
    if(!pending.empty() && cycle>=pending.front().due){
     const auto& p=pending.front();
     if(cycle%7==0){d.rsp_valid=1;d.rsp_tag=p.tag^1;for(unsigned n=0;n<4;++n)d.rsp_data[n]=0xdeadbeef;}
     else{
      d.rsp_valid=1;d.rsp_tag=p.tag;d.rsp_error=p.fault;real=true;
      if(!p.fault && p.write)memory[p.address]=p.data;
      for(unsigned n=0;n<4;++n)d.rsp_data[n]=memory[p.address][n];
     }
    }
    d.eval();
    std::array<uint32_t,4> word{};for(unsigned n=0;n<4;++n)word[n]=d.s_data[n];
    const auto current=std::make_tuple(uint32_t(d.s_write),uint32_t(d.s_address),uint32_t(d.s_tag),word);
    if(previous_held)check(d.s_valid && current==previous,"S request changed while held/cancelled");
    previous_held=d.s_valid&&!d.s_ready;previous=current;
    if(d.rsp_valid && d.rsp_ready){
     if(real){++acks;if(pending.front().write&&!pending.front().fault){++write_acks;write_mask|=1U<<(pending.front().address-256);}pending.pop_front();}
     else ++stale;
    }
    if(d.s_valid && d.s_ready){
     check(pending.size()<2,"more than two S transactions outstanding");++accepted;++transactions;
     const bool fault=(read_fault&&!d.s_write&&accepted==3)||(write_fault&&d.s_write&&write_requests==2);
     pending.push_back(Request{cycle+1+unsigned(rng()%5),d.s_address,d.s_tag,bool(d.s_write),fault,word});
     if(d.s_write){++writes;++write_requests;}
    }
    if(d.done_valid && d.done_ready){
     check(pending.empty()&&!d.s_valid && acks==accepted,"terminal before actual response drain");
     for(unsigned n=0;n<4;++n)check(d.done_key[n]==owner[n],"terminal owner mismatch");
     check(d.done_kk==uint16_t(d.cmd_kk),"terminal kk mismatch");
     check(bool(d.done_error)==(bad||read_fault||write_fault||bad_numeric),"wrong terminal error");
     check(bool(d.done_cancelled)==stop,"wrong cancel result");
     unsigned prefix=0;while(prefix<16 && (write_mask&(1U<<prefix)))++prefix;
     check(d.done_words==prefix && d.done_written_mask==write_mask,"actual write ACK prefix/mask lost");
     if(bad||stop||read_fault||write_fault||bad_numeric)check(d.done_shift==0,"failed/cancelled quantization published usable shift");
     else{
      check(d.done_shift==shift && write_acks==16,"wrong dynamic scale/commit count");
      check(accepted==(known?48U:80U),"quantization transaction count mismatch");
      shifts|=1U<<shift;
      for(unsigned n=0;n<128;++n){
       const uint16_t got=uint16_t(memory[256+n/8][n%8/2]>>(16*(n%2)));
       check(int16_t(got)==rne(source[n],shift),"RNE A16 data mismatch");
      }
     }
     if(stop){check(offered_held,"cancel never exercised held request");++cancelled;}
     if(bad_numeric)++numeric;
     finished=true;
    }
    tick();
   }
   check(finished,"quantizer timeout");
  }
  check(shifts==0x3ffff && cancelled==9 && numeric==9 && invalid==9 && stale>0,"coverage incomplete");
  check(d.rejected_responses==stale,"stale response stole transaction identity");
  std::cout<<"PASS quantizer cases=216 transactions="<<transactions<<" writes="<<writes<<" stale="<<stale
   <<" shifts="<<shifts<<" cancelled="<<cancelled<<" numeric="<<numeric<<" invalid="<<invalid<<" initial="<<initial<<"\n";
  return 0;
 }catch(const std::exception& e){std::cerr<<e.what()<<"\n";return 1;}
}
