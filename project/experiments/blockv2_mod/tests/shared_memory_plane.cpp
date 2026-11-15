#include "Vnative_shared_memory_plane.h"
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
uint32_t data(uint64_t a,int c,int b){return uint32_t(a)^(b*0x10203U)^uint32_t(c*0x7755U);}
struct Work{int c,due;uint64_t address;bool error=false,offered=false;};
struct Held{bool valid=false;uint64_t tag=0;};
int main(int argc,char** argv){try{
 unsigned seed=argc>1?std::stoul(argv[1]):17;
 std::mt19937 rng(seed);Verilated::randReset(2);Verilated::randSeed(seed);
 auto top=std::make_unique<Vnative_shared_memory_plane>();auto& t=*top;
 std::array<int,18> sent{},returned{};
 std::array<bool,18> active{},committed{},error{};
 std::array<uint64_t,18> owner{},address{};
 std::map<uint64_t,Work> pending;std::array<Held,4> held{};
 std::array<bool,4> offer_held{},old_write{};std::array<uint64_t,4> old_tag{},old_address{};
 std::array<std::array<uint32_t,16>,4> old_write_data{};
 std::array<bool,18> rsp_held{};std::array<uint64_t,18> old_owner{};
 std::array<std::array<uint32_t,16>,18> old_data{};
 std::array<std::array<int,2>,2> history{};
 bool fence=false,boot=false;uint32_t generation=0;
 int fence_due=0,fences=0,accepted=0,completed=0,cycle=0,write_commits=0,write_errors=0;
 t.c_req_valid=0;t.c_req_channel=0;t.c_req_record_beats=0;
 clear(t.c_req_address,24);clear(t.c_req_tag,12);
 t.c_rsp_ready=4095;t.c_close_valid=0;clear(t.c_close_tag_base,12);
 t.c_cancel_valid=0;clear(t.c_cancel_tag,12);t.c_cancel_ack_ready=4095;
 t.c_fence_valid=0;clear(t.c_fence_cookie,12);clear(t.c_fence_epoch,4);t.c_fence_done_ready=4095;
 for(;cycle<250000;cycle++){
  t.clk=0;t.reset=cycle<4;t.service_req_valid=0;t.write_req_valid=0;
  t.service_rsp_ready=rng()&511;t.write_done_ready=rng()&511;
  clear(t.service_req_address,18);clear(t.service_req_tag,18);
  clear(t.write_req_address,18);clear(t.write_req_tag,18);clear(t.write_req_data,144);
  for(int c=0;c<18;c++){
   int k=c%9;uint64_t a=0x1000000ULL+uint64_t(sent[c])*4096+uint64_t((sent[c]+c)&1)*2048+64;
   uint64_t tag=(uint64_t(0x80000000U+c*1000+sent[c])<<32)|0x5511;
   if(c<9){
    put64(t.service_req_address,k*2,a);put64(t.service_req_tag,k*2,tag);
    if(sent[c]<200)t.service_req_valid|=1U<<k;
   }else{
    put64(t.write_req_address,k*2,a);put64(t.write_req_tag,k*2,tag);
    for(int b=0;b<16;b++)t.write_req_data[k*16+b]=data(a,c,b);
    if(sent[c]<200)t.write_req_valid|=1U<<k;
   }
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
    if(w.c<9){for(int b=0;b<16;b++)t.d_rsp_data[lane*16+b]=data(w.address,w.c,b);}
    else t.d_rsp_data[lane*16]=w.error;
   }
  }
  t.fault_ready=1;t.d_fence_ready=cycle%3!=0;
  t.d_fence_done_valid=fence&&cycle>=fence_due;t.d_fence_done_generation=generation;
  t.eval();
  if(!t.reset){
   need(!t.fault_valid&&!t.service_protocol_fault&&!t.write_protocol_fault,"unexpected protocol error");
   need(t.c_rsp_valid==0,"service return leaked into LC/M namespace");
   std::array<int,2> issues{};
   for(int lane=0;lane<4;lane++){
    bool valid=(t.d_req_valid>>lane)&1,ready=(t.d_req_ready>>lane)&1,wr=(t.d_req_write>>lane)&1;
    uint64_t tag=get64(t.d_req_tag,lane*2),a=get64(t.d_req_address,lane*2);
    if(offer_held[lane]){
     need(valid&&tag==old_tag[lane]&&a==old_address[lane]&&wr==old_write[lane],"unstable DDR offer");
     for(int b=0;b<16;b++)need(t.d_req_data[lane*16+b]==old_write_data[lane][b],"unstable held write payload");
    }
    offer_held[lane]=valid&&!ready;old_tag[lane]=tag;old_address[lane]=a;old_write[lane]=wr;
    for(int b=0;b<16;b++)old_write_data[lane][b]=t.d_req_data[lane*16+b];
    if(valid&&ready){
     int c=int((tag>>5)&31)-12;
     need(c>=0&&c<18&&active[c]&&address[c]==a,"unowned service DDR request");
     need(wr==(c>=9),"wrong backend read/write operation");
     if(wr)for(int b=0;b<16;b++)need(t.d_req_data[lane*16+b]==data(a,c,b),"wrong write payload");
     need(!pending.count(tag),"live transport tag reuse");
     pending[tag]={c,cycle+3+int(rng()%13),a,error[c],false};issues[lane/2]++;
    }
   }
   for(int ch=0;ch<2;ch++){
    need(issues[ch]+history[ch][0]+history[ch][1]<=4,"combined read/write bandwidth exceeded");
    history[ch][1]=history[ch][0];history[ch][0]=issues[ch];
   }
   for(int c=0;c<18;c++){
    int k=c%9;bool valid=((c<9?t.service_rsp_valid:t.write_done_valid)>>k)&1;
    bool ready=((c<9?t.service_rsp_ready:t.write_done_ready)>>k)&1;
    uint64_t tag=c<9?get64(t.service_rsp_tag,k*2):get64(t.write_done_tag,k*2);
    bool err=((c<9?t.service_rsp_error:t.write_done_error)>>k)&1;
    if(rsp_held[c]){
     need(valid&&tag==old_owner[c],"unstable upstream response tag");
     if(c<9)for(int b=0;b<16;b++)need(t.service_rsp_data[k*16+b]==old_data[c][b],"unstable response data");
     else need(err==bool(old_data[c][0]),"unstable write error response");
    }
    rsp_held[c]=valid&&!ready;old_owner[c]=tag;
    if(c<9)for(int b=0;b<16;b++)old_data[c][b]=t.service_rsp_data[k*16+b];
    else old_data[c][0]=err;
    if(valid&&ready){
     need(active[c]&&committed[c]&&tag==owner[c]&&err==error[c],"early completion or lost full owner/error");
     if(c<9)for(int b=0;b<16;b++)need(t.service_rsp_data[k*16+b]==data(address[c],c,b),"wrong read payload");
     else if(err)write_errors++;
     active[c]=false;returned[c]++;completed++;
    }
    bool fire=((c<9?(t.service_req_valid&t.service_req_ready):(t.write_req_valid&t.write_req_ready))>>k)&1;
    if(fire){
     need(boot&&!active[c],"accepted before startup purge or owner free");
     active[c]=true;committed[c]=false;error[c]=c>=9&&sent[c]%37==0;
     owner[c]=c<9?get64(t.service_req_tag,k*2):get64(t.write_req_tag,k*2);
     address[c]=c<9?get64(t.service_req_address,k*2):get64(t.write_req_address,k*2);
     sent[c]++;accepted++;
    }
   }
   for(int lane=0;lane<4;lane++)if(((t.d_rsp_valid&t.d_rsp_ready)>>lane)&1){
    need(held[lane].valid&&pending.count(held[lane].tag),"duplicate backend return");
    int c=pending.at(held[lane].tag).c;committed[c]=true;if(c>=9)write_commits++;
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
  if(completed==3600&&pending.empty()&&!fence&&t.service_idle==511&&t.write_idle==511&&t.debug_beats==0&&t.debug_descriptors==0)break;
 }
 need(completed==3600&&accepted==3600&&fences>100,"incomplete mixed-client stress");
 for(int c=0;c<18;c++)need(returned[c]==200,"missing service owner work");
 need(write_commits==1800&&write_errors==54,"missing real write commit/error cases");
 std::cout<<"PASS shared_memory_plane seed="<<seed<<" read_clients=9 write_clients=9 accepted="<<accepted<<" completed="<<completed<<" write_commits="<<write_commits<<" write_errors="<<write_errors<<" fences="<<fences<<" cycles="<<cycle<<" full_tag_bits=64 rolling3_shared_limit=4\n";
 return 0;
}catch(const std::exception& e){std::cerr<<"FAIL "<<e.what()<<"\n";return 1;}}
