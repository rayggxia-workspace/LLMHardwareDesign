#define SC_INCLUDE_DYNAMIC_PROCESSES
#include <systemc>
#include <fstream>
#include <iostream>
#include <memory>
#include <stdexcept>
#include <vector>
using namespace sc_core;
using Tick=unsigned long long;
struct Task {Tick duration=0,end=0;bool done=false;std::vector<unsigned> parents;sc_event completed;};
int sc_main(int argc,char** argv) {
 try {
  if(argc!=2)throw std::runtime_error("input required");
  sc_set_time_resolution(1,SC_NS);
  std::ifstream input(argv[1]);unsigned count;input>>count;
  if(!input || !count)throw std::runtime_error("invalid task count");
  std::vector<std::unique_ptr<Task>> tasks;
  for(unsigned i=0;i<count;i++)tasks.emplace_back(new Task);
  for(auto& t:tasks){unsigned n;input>>t->duration>>n;t->parents.resize(n);for(auto& p:t->parents){input>>p;if(p>=count)throw std::runtime_error("parent outside graph");}}
  if(!input)throw std::runtime_error("short task graph");
  unsigned completed=0;
  for(unsigned i=0;i<count;i++)sc_spawn([&,i](){
   auto& t=*tasks[i];
   for(auto p:t.parents)while(!tasks[p]->done)wait(tasks[p]->completed);
   wait(sc_time::from_value(t.duration));t.end=sc_time_stamp().value();t.done=true;
   t.completed.notify(SC_ZERO_TIME);completed++;
  });
  sc_start();Tick end=0;
  for(auto& t:tasks)end=std::max(end,t->end);
  if(completed!=count)throw std::runtime_error("deadlocked/incomplete graph");
  std::cout<<"{\"completed\":"<<completed<<",\"model_ticks\":"<<end<<",\"systemc\":\""<<sc_version()<<"\"}\n";
  return 0;
 }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
}
