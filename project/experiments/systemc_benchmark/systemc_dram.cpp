// SystemC/DRAMsim3 queue and completion bridge; not a full chip model.
// Requests are 64-byte DRAM bursts, not implicit packed 16-byte S records.
#define SC_INCLUDE_DYNAMIC_PROCESSES
#include <systemc>
#include "memory_system.h"
#include <cmath>
#include <fstream>
#include <iostream>
#include <map>
#include <memory>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

struct Request {
 uint64_t id=0,address=0,release=0,submitted_tick=0,submitted_ps=0,done_tick=0;
 int after=-1;bool write=false,submitted=false,done=false;
};
std::vector<Request> read_requests(const std::string& path) {
 std::ifstream file(path);if(!file)throw std::runtime_error("missing input trace");
 std::vector<Request> out;std::set<uint64_t> addresses;std::string line;
 while(std::getline(file,line)) {
  if(line.empty()||line[0]=='#')continue;
  Request q;unsigned write;std::istringstream row(line);std::string extra;
  if(!(row>>q.id>>q.address>>write>>q.release>>q.after)||(row>>extra)||
     q.id!=out.size()||write>1||q.address%64||q.after>=int(q.id)||q.after< -1||
     !addresses.insert(q.address).second)
   throw std::runtime_error("trace requires unique aligned bursts and earlier dependency IDs");
  q.write=write;out.push_back(q);
 }
 return out;
}
uint64_t period_ps(const dramsim3::MemorySystem& memory) {
 double value=memory.GetTCK()*1000.;auto rounded=uint64_t(std::llround(value));
 if(!rounded||std::abs(value-double(rounded))>1e-6)
  throw std::runtime_error("DRAM period not representable at 1ps");
 if(memory.GetBusBits()*memory.GetBurstLength()!=512)
  throw std::runtime_error("this bridge requires explicit 64-byte bursts");
 return rounded;
}
struct Bridge:sc_core::sc_module {
 std::vector<Request> requests;std::map<uint64_t,size_t> index;
 std::unique_ptr<dramsim3::MemorySystem> memory;
 sc_core::sc_event clock_event,completion;uint64_t ticks=0,limit,period,retries=0;
 std::ofstream accepted;
 Bridge(sc_core::sc_module_name name,const std::string& config,const std::string& output,
        std::vector<Request> input,uint64_t stop):sc_module(name),requests(std::move(input)),limit(stop),
        accepted(output+"/accepted.tsv") {
  if(!accepted)throw std::runtime_error("cannot create accepted trace");
  for(size_t i=0;i<requests.size();++i)index.emplace(requests[i].address,i);
  memory.reset(dramsim3::GetMemorySystem(config,output,
      [this](uint64_t a){callback(a,false);},[this](uint64_t a){callback(a,true);}));
  period=period_ps(*memory);SC_THREAD(clock);
  for(size_t i=0;i<requests.size();++i)sc_core::sc_spawn([this,i](){issue(i);});
 }
 void callback(uint64_t address,bool write) {
  auto& q=requests.at(index.at(address));
  if(!q.submitted||q.done||q.write!=write)throw std::runtime_error("unexpected DRAM callback");
  q.done=true;q.done_tick=ticks;completion.notify(sc_core::SC_ZERO_TIME);
 }
 void clock() {
  while(ticks<limit) {
   wait(sc_core::sc_time::from_value(period));++ticks;memory->ClockTick();
   clock_event.notify(sc_core::SC_ZERO_TIME);
  }
  memory->PrintStats();accepted.flush();sc_core::sc_stop();
 }
 void issue(size_t i) {
  auto& q=requests[i];if(q.release)wait(sc_core::sc_time::from_value(q.release));
  while(q.after>=0&&!requests[size_t(q.after)].done)wait(completion);
  while(!memory->WillAcceptTransaction(q.address,q.write)){++retries;wait(clock_event);}
  q.submitted=true;q.submitted_tick=ticks;q.submitted_ps=sc_core::sc_time_stamp().value();
  accepted<<q.id<<'\t'<<q.address<<'\t'<<q.write<<'\t'<<ticks<<'\n';
  if(!memory->AddTransaction(q.address,q.write))throw std::runtime_error("queue acceptance changed");
 }
};
void result(const char* engine,const std::vector<Request>& rows,uint64_t ticks,uint64_t period,uint64_t retries) {
 bool complete=true;for(auto& q:rows)complete&=q.done;
 std::cout<<"RESULT {\"engine\":\""<<engine<<"\",\"ticks\":"<<ticks<<",\"period_ps\":"<<period
  <<",\"window_ps\":"<<ticks*period<<",\"queue_retry_events\":"<<retries
  <<",\"callbacks_complete\":"<<(complete?"true":"false")<<",\"requests\":[";
 for(size_t i=0;i<rows.size();++i){auto& q=rows[i];if(i)std::cout<<",";
  std::cout<<"{\"id\":"<<q.id<<",\"address\":"<<q.address<<",\"write\":"<<(q.write?"true":"false")
   <<",\"submitted\":"<<(q.submitted?"true":"false")<<",\"submitted_tick\":"<<q.submitted_tick
   <<",\"callback_tick\":"<<q.done_tick<<"}";}
 std::cout<<"],\"scope\":\"synthetic DRAM queue bridge; no chip or token/s claim; write callback is buffer acceptance, not physical DRAM completion\"}\n";
 if(!complete)throw std::runtime_error("bounded DRAM window ended before callbacks");
}
int sc_main(int argc,char**argv) {
 try {
  if(argc!=6)throw std::runtime_error("usage: systemc-dram sc|direct config output input stop_ticks");
  const std::string mode=argv[1],config=argv[2],output=argv[3];uint64_t limit=std::stoull(argv[5]);
  if(!limit||limit>10000000)throw std::runtime_error("invalid bounded window");
  sc_core::sc_set_time_resolution(1,sc_core::SC_PS);
  if(mode=="sc") {
   Bridge bridge("bridge",config,output,read_requests(argv[4]),limit);sc_core::sc_start();
   result("SystemC_3_DRAMsim3",bridge.requests,bridge.ticks,bridge.period,bridge.retries);
  }else if(mode=="direct") {
   struct Input {uint64_t id,address,tick;bool write;};
   std::ifstream file(argv[4]);if(!file)throw std::runtime_error("missing accepted trace");
   std::vector<Input> input;uint64_t id,address,tick;unsigned write;
   while(file>>id>>address>>write>>tick)input.push_back({id,address,tick,bool(write)});
   std::vector<Request> rows(input.size());std::map<uint64_t,size_t> index;uint64_t ticks=0;
   auto callback=[&](uint64_t a,bool w){auto& q=rows.at(index.at(a));
    if(!q.submitted||q.done||q.write!=w)throw std::runtime_error("direct callback differs");
    q.done=true;q.done_tick=ticks;};
   std::unique_ptr<dramsim3::MemorySystem> memory(dramsim3::GetMemorySystem(config,output,
       [&](uint64_t a){callback(a,false);},[&](uint64_t a){callback(a,true);}));
   auto period=period_ps(*memory);size_t next=0;
   while(ticks<limit) {
    while(next<input.size()&&input[next].tick==ticks){auto q=input[next++];
     if(q.id>=rows.size()||!memory->WillAcceptTransaction(q.address,q.write))
      throw std::runtime_error("accepted trace illegal in direct reference");
     auto& r=rows[q.id];r.id=q.id;r.address=q.address;r.write=q.write;r.submitted=true;r.submitted_tick=ticks;
     if(!index.emplace(q.address,q.id).second||!memory->AddTransaction(q.address,q.write))
      throw std::runtime_error("duplicate/invalid direct request");
    }
    ++ticks;memory->ClockTick();
   }
   if(next!=input.size())throw std::runtime_error("accepted trace not exhausted");
   memory->PrintStats();result("DRAMsim3_direct_reference",rows,ticks,period,0);
  }else throw std::runtime_error("unknown engine");
  return 0;
 }catch(const std::exception& e){std::cerr<<e.what()<<"\n";return 1;}
}
