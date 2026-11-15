// Same DRAMsim3 and strict-write semantics. Batch only until the first return.
#include <cstdint>
#include <memory>
#include <vector>
#include <utility>
#include <stdexcept>
#include "memory_system.h"
using Callback=void(*)(uint64_t,bool);
struct Handle {
 std::unique_ptr<dramsim3::MemorySystem> model;
 Callback done;
 std::vector<std::pair<uint64_t,bool>> returned;
};
static Handle& h(void* p){return *static_cast<Handle*>(p);}
extern "C" void* native_dram_open(const char* config,const char* output,Callback done){
 auto p=std::make_unique<Handle>();auto raw=p.get();raw->done=done;
 raw->model.reset(dramsim3::GetMemorySystem(config,output,
  [raw](uint64_t a){raw->returned.emplace_back(a,false);},
  [raw](uint64_t a){raw->returned.emplace_back(a,true);}));
 if(raw->model->GetBusBits()*raw->model->GetBurstLength()!=512)
  throw std::runtime_error("64-byte bursts required");
 raw->model->EnableStrictWrites();return p.release();
}
extern "C" double native_dram_period_ns(void* p){return h(p).model->GetTCK();}
extern "C" bool native_dram_offer(void* p,uint64_t a,bool w){
 auto& m=*h(p).model;return m.WillAcceptTransaction(a,w)&&m.AddTransaction(a,w);
}
extern "C" void native_dram_flush(void* p){
 auto& x=h(p);auto rows=std::move(x.returned);x.returned.clear();
 for(auto r:rows)x.done(r.first,r.second);
}
extern "C" void native_dram_tick(void* p){
 h(p).model->ClockTick();native_dram_flush(p);
}
extern "C" uint64_t native_dram_pair_ticks(void* a,void* b,uint64_t limit){
 auto& x=h(a);auto& y=h(b);
 if(!x.returned.empty()||!y.returned.empty())return 0;
 uint64_t count=0;
 while(count<limit){
  x.model->ClockTick();y.model->ClockTick();++count;
  if(!x.returned.empty()||!y.returned.empty())break;
 }
 return count;
}
extern "C" void native_dram_close(void* p){
 auto x=std::unique_ptr<Handle>(static_cast<Handle*>(p));x->model->PrintStats();
}
