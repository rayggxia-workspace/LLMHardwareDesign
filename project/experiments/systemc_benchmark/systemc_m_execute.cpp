// Independent transaction-level timing model of accepted native M Execute.
// Two partial banks and a serial two-lane scale pipeline are real resources.
// No measured descriptor latency is read by this model. This is not a complete
// macro model: payload arithmetic, load arbitration and stalled replies need
// separate checks; no Qwen timing or energy claim follows from this fixture.
#define SC_INCLUDE_DYNAMIC_PROCESSES
#include <systemc>
#include <algorithm>
#include <array>
#include <fstream>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

struct Descriptor {
 unsigned wa,wb,rows,tiles,tail,columns;
};
uint64_t edge_ps(uint64_t cycle) {return (cycle*10000+2)/3;}
void until_cycle(uint64_t cycle) {
 const uint64_t time=edge_ps(cycle),now=sc_core::sc_time_stamp().value();
 if(time<now)throw std::runtime_error("clock moved backwards");
 if(time>now)sc_core::wait(sc_core::sc_time::from_value(time-now));
}
struct Model:sc_core::sc_module {
 struct Bank {bool busy=false,ready=false;uint64_t ready_cycle=0,free_cycle=0;};
 std::array<Bank,2> banks;
 std::vector<Descriptor> input;
 sc_core::sc_event start,partial_ready,bank_free,finished;
 uint64_t base=0,cycles=0;unsigned commits=0;
 Descriptor descriptor{};
 Model(sc_core::sc_module_name name,std::vector<Descriptor> values):
     sc_module(name),input(std::move(values)) {
  SC_THREAD(control);SC_THREAD(issue);SC_THREAD(scale);
 }
 void control() {
  for(size_t id=0;id<input.size();++id) {
   descriptor=input[id];commits=0;cycles=0;banks={};
   start.notify(sc_core::SC_ZERO_TIME);wait(finished);
   const unsigned loads=descriptor.tiles*(descriptor.rows+(descriptor.wb?2:1));
   std::cout<<"ROW "<<id<<' '<<loads<<' '<<cycles<<' '<<descriptor.rows*8<<'\n';
   base+=cycles+1;until_cycle(base);
  }
  std::cout<<"RESULT {\"descriptors\":"<<input.size()
    <<",\"full_model_qualified\":false,\"energy_qualified\":false}\n";
  sc_core::sc_stop();
 }
 void issue() {
  while(true) {
   wait(start);
   const unsigned issue_ticks=descriptor.tiles*(descriptor.wa?3:1)*(descriptor.wb?3:1);
   uint64_t first=base+1;
   for(unsigned row=0;row<descriptor.rows;++row) {
    auto& bank=banks[row%2];until_cycle(first);
    if(bank.busy) {
     do {wait(bank_free);} while(bank.busy);
     first=bank.free_cycle+2;until_cycle(first);
    } else if(bank.free_cycle) {
     first=std::max(first,bank.free_cycle+2);until_cycle(first);
    }
    bank.busy=true;bank.ready=false;
    // One product stage and one reduction stage after the last issue edge.
    const uint64_t partial=first+issue_ticks+1;
    sc_core::sc_spawn([this,row,partial](){
     until_cycle(partial);auto& target=banks[row%2];
     if(!target.busy||target.ready)throw std::runtime_error("partial-bank collision");
     target.ready=true;target.ready_cycle=partial;
     partial_ready.notify(sc_core::SC_ZERO_TIME);
    });
    first+=issue_ticks+1; // actual row switch needs its bank-acquisition edge
   }
  }
 }
 void scale() {
  while(true) {
   wait(start);uint64_t next_fetch=base;
   for(unsigned row=0;row<descriptor.rows;++row) {
    auto& bank=banks[row%2];
    while(!bank.ready)wait(partial_ready);
    // Partial-ready is observed at the following edge. Four two-lane
    // fetches serialize here, independent of active output-column count.
    const uint64_t first=std::max(next_fetch,bank.ready_cycle+1);
    const uint64_t last=first+3;until_cycle(last);
    bank.ready=false;bank.busy=false;bank.free_cycle=last;
    bank_free.notify(sc_core::SC_ZERO_TIME);next_fetch=last+1;
    const uint64_t commit=last+4;
    sc_core::sc_spawn([this,commit](){
     until_cycle(commit);++commits;
     if(commits==descriptor.rows) {
      // Drain observes final atomic row commit one edge later. The native
      // fixture observes rsp_valid and explicitly consumes that response.
      until_cycle(commit+1);
      const uint64_t done=commit+3;until_cycle(done);
      cycles=done-base;finished.notify(sc_core::SC_ZERO_TIME);
     }
    });
   }
  }
 }
};
int sc_main(int argc,char**argv) {
 try {
  if(argc!=2)throw std::runtime_error("usage: systemc-m-execute descriptors.tsv");
  sc_core::sc_set_time_resolution(1,sc_core::SC_PS);
  std::ifstream file(argv[1]);if(!file)throw std::runtime_error("missing descriptors");
  std::vector<Descriptor> input;std::string line;
  while(std::getline(file,line)) {
   if(line.empty()||line[0]=='#')continue;
   Descriptor d{};std::string extra;std::istringstream row(line);
   if(!(row>>d.wa>>d.wb>>d.rows>>d.tiles>>d.tail>>d.columns)||(row>>extra)||
      d.wa>1||d.wb>1||d.rows<1||d.rows>8||d.tiles<1||d.tiles>4||
      d.tail<1||d.tail>8||d.columns<1||d.columns>8)
    throw std::runtime_error("unsupported native descriptor");
   input.push_back(d);
  }
  if(input.empty())throw std::runtime_error("empty descriptor stream");
  Model model("M",input);sc_core::sc_start();return 0;
 }catch(const std::exception& error){std::cerr<<error.what()<<'\n';return 1;}
}
