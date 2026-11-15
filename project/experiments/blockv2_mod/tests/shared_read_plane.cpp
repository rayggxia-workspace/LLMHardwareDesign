#include "Vnative_shared_read_plane.h"
#include "verilated.h"
#include <array>
#include <map>
#include <random>
#include <stdexcept>
#include <iostream>
#include <memory>
#include <cstdint>
template<class T>void clear(T& x,int n){for(int i=0;i<n;i++)x[i]=0;}
template<class T>void put64(T& x,int i,uint64_t v){x[i]=v;x[i+1]=v>>32;}
template<class T>uint64_t get64(T& x,int i){return uint64_t(x[i])|(uint64_t(x[i+1])<<32);}
void need(bool v,const char* s){if(!v)throw std::runtime_error(s);}
struct Work{int c,due;uint64_t address;bool offered=false;};
struct Held{bool valid=false;uint64_t tag=0;};
int main(int argc,char** argv){try{
 unsigned seed=argc>1?std::stoul(argv[1]):17;
 std::mt19937 rng(seed);Verilated::randReset(2);Verilated::randSeed(seed);
 auto top=std::make_unique<Vnative_shared_read_plane>();auto& t=*top;
 std::array<int,9> sent{},returned{};
 std::array<bool,9> active{};std::array<uint64_t,9> owner{},address{};
 std::map<uint64_t,Work> pending;std::array<Held,4> held{};
 std::array<bool,4> offer_held{};std::array<uint64_t,4> old_tag{},old_address{};
 std::array<bool,9> rsp_held{};std::array<uint64_t,9> old_owner{};
 std::array<std::array<uint32_t,16>,9> old_data{};
 bool fence=false,boot=false;uint32_t generation=0;int fence_due=0,fences=0,accepted=0,completed=0,cycle=0;
 t.c_req_valid=0;t.c_req_channel=0;t.c_req_record_beats=0;
 clear(t.c_req_address,24);clear(t.c_req_tag,12);
 t.c_rsp_ready=4095;t.c_close_valid=0;clear(t.c_close_tag_base,12);
 t.c_cancel_valid=0;clear(t.c_cancel_tag,12);t.c_cancel_ack_ready=4095;
 t.c_fence_valid=0;clear(t.c_fence_cookie,12);clear(t.c_fence_epoch,4);t.c_fence_done_ready=4095;
 for(;cycle<200000;cycle++){
  t.clk=0;t.reset=cycle<4;t.service_req_valid=0;t.service_rsp_ready=rng()&511;
  clear(t.service_req_address,18);clear(t.service_req_tag,18);
  for(int c=0;c<9;c++){
   uint64_t a=0x1000000ULL+uint64_t(sent[c])*4096+uint64_t((sent[c]+c)&1)*2048+64;
   // Low 32 bits deliberately repeat; only the full upstream tag identifies work.
   uint64_t tag=(uint64_t(0x80000000U+c*1000+sent[c])<<32)|0x5511;
   put64(t.service_req_address,c*2,a);put64(t.service_req_tag,c*2,tag);
   if(sent[c]<200)t.service_req_valid|=1U<<c;
  }
  t.d_req_ready=rng()&15;t.d_rsp_valid=0;clear(t.d_rsp_tag,8);clear(t.d_rsp_data,64);
  for(int lane=0;lane<4;lane++){
   if(!held[lane].valid){
    for(auto it=pending.rbegin();it!=pending.rend();++it){
     auto& w=it->second;
     if(!w.offered&&w.due<=cycle&&int((w.address>>11)&1)==lane/2){
      held[lane]={true,it->first};w.offered=true;break;
     }
    }
   }
   if(held[lane].valid){
    t.d_rsp_valid|=1U<<lane;put64(t.d_rsp_tag,lane*2,held[lane].tag);
    auto& w=pending.at(held[lane].tag);
    for(int b=0;b<16;b++)t.d_rsp_data[lane*16+b]=uint32_t(w.address)^(b*0x10203U)^uint32_t(w.c*0x7755U);
   }
  }
  t.fault_ready=1;t.d_fence_ready=cycle%3!=0;
  t.d_fence_done_valid=fence&&cycle>=fence_due;t.d_fence_done_generation=generation;
  t.eval();
  if(!t.reset){
   need(!t.fault_valid&&!t.service_protocol_fault,"unexpected protocol error");
   need(t.c_rsp_valid==0,"service return leaked into LC/M namespace");
   for(int lane=0;lane<4;lane++){
    bool valid=(t.d_req_valid>>lane)&1,ready=(t.d_req_ready>>lane)&1;
    uint64_t tag=get64(t.d_req_tag,lane*2),a=get64(t.d_req_address,lane*2);
    if(offer_held[lane])need(valid&&tag==old_tag[lane]&&a==old_address[lane],"unstable DDR offer");
    offer_held[lane]=valid&&!ready;old_tag[lane]=tag;old_address[lane]=a;
    if(valid&&ready){
     int c=int((tag>>5)&31)-12;
     need(c>=0&&c<9&&active[c]&&address[c]==a,"unowned service DDR request");
     need(!pending.count(tag),"live transport tag reuse");
     pending[tag]={c,cycle+3+int(rng()%13),a,false};
    }
   }
   for(int c=0;c<9;c++){
    bool valid=(t.service_rsp_valid>>c)&1,ready=(t.service_rsp_ready>>c)&1;
    uint64_t tag=get64(t.service_rsp_tag,c*2);
    if(rsp_held[c]){
     need(valid&&tag==old_owner[c],"unstable upstream response tag");
     for(int b=0;b<16;b++)need(t.service_rsp_data[c*16+b]==old_data[c][b],"unstable upstream response bytes");
    }
    rsp_held[c]=valid&&!ready;old_owner[c]=tag;
    for(int b=0;b<16;b++)old_data[c][b]=t.service_rsp_data[c*16+b];
    if(valid&&ready){
     need(active[c]&&tag==owner[c]&&!((t.service_rsp_error>>c)&1),"lost full 64-bit owner tag");
     for(int b=0;b<16;b++)need(t.service_rsp_data[c*16+b]==(uint32_t(address[c])^(b*0x10203U)^uint32_t(c*0x7755U)),"wrong service payload");
     active[c]=false;returned[c]++;completed++;
    }
    if(((t.service_req_valid&t.service_req_ready)>>c)&1){
     need(boot&&!active[c],"service accepted without startup purge or free owner");
     active[c]=true;owner[c]=get64(t.service_req_tag,c*2);address[c]=get64(t.service_req_address,c*2);
     sent[c]++;accepted++;
    }
   }
   for(int lane=0;lane<4;lane++)if(((t.d_rsp_valid&t.d_rsp_ready)>>lane)&1){
    need(held[lane].valid&&pending.count(held[lane].tag),"duplicate backend return");
    pending.erase(held[lane].tag);held[lane].valid=false;
   }
   if(t.d_fence_valid&&t.d_fence_ready){
    need(!fence&&pending.empty(),"physical fence before backend drain");
    for(bool a:active)need(!a,"physical fence before client consumption");
    fence=true;generation=t.d_fence_generation;fence_due=cycle+4;fences++;
   }
   if(t.d_fence_done_valid&&t.d_fence_done_ready){fence=false;boot=true;}
  }
  t.clk=1;t.eval();t.clk=0;t.eval();
  if(completed==1800&&pending.empty()&&!fence&&t.service_idle==511&&t.debug_beats==0&&t.debug_descriptors==0)break;
 }
 need(completed==1800&&accepted==1800&&fences>100,"incomplete native-client/fence stress");
 for(int c=0;c<9;c++)need(returned[c]==200,"missing service owner work");
 std::cout<<"PASS shared_read_plane seed="<<seed<<" clients=9 requests="<<accepted<<" completed="<<completed<<" fences="<<fences<<" cycles="<<cycle<<" full_tag_bits=64\n";
 return 0;
}catch(const std::exception& e){std::cerr<<"FAIL "<<e.what()<<"\n";return 1;}}
