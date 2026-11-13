// Issue234: event-driven resource arbitration, not a replay of precomputed starts.
// Time unit in the input is integer ps. Energy is nJ; '?' remains unknown.
#define SC_INCLUDE_DYNAMIC_PROCESSES
#include <systemc>
#include <algorithm>
#include <cmath>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <map>
#include <optional>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

struct Task {
  std::string id;
  uint64_t duration=0;
  std::vector<std::string> deps,resources;
  std::optional<double> energy;
  bool launched=false,done=false;
  uint64_t start=0,end=0;
};
std::vector<std::string> split(const std::string& s,char delimiter) {
  std::vector<std::string> out;std::stringstream in(s);std::string v;
  while(std::getline(in,v,delimiter))out.push_back(v);
  return out;
}
struct Runtime:sc_core::sc_module {
  std::vector<Task> tasks;std::map<std::string,size_t> ids;std::set<std::string> busy;
  sc_core::sc_event completion;size_t retired=0;double energy=0;bool energy_complete=true;
  Runtime(sc_core::sc_module_name name,std::vector<Task> input):sc_module(name),tasks(std::move(input)) {
    for(size_t i=0;i<tasks.size();++i)if(!ids.emplace(tasks[i].id,i).second)throw std::runtime_error("duplicate id");
    for(auto& t:tasks)for(auto& d:t.deps)if(!ids.count(d))throw std::runtime_error("unknown dependency");
    SC_THREAD(run);
  }
  void finish(size_t i) {
    auto& t=tasks[i];wait(sc_core::sc_time::from_value(t.duration));
    t.end=sc_core::sc_time_stamp().value();t.done=true;++retired;
    for(auto& r:t.resources)busy.erase(r);
    if(t.energy)energy+=*t.energy;else energy_complete=false;
    completion.notify(sc_core::SC_ZERO_TIME);
  }
  void run() {
    while(retired<tasks.size()) {
      bool running=false;
      for(size_t i=0;i<tasks.size();++i) {
        auto& t=tasks[i];if(t.launched){running|=!t.done;continue;}
        bool ready=true;
        for(auto& d:t.deps)ready&=tasks[ids.at(d)].done;
        for(auto& r:t.resources)ready&=!busy.count(r);
        if(!ready)continue;
        t.launched=true;t.start=sc_core::sc_time_stamp().value();running=true;
        for(auto& r:t.resources)busy.insert(r);
        sc_core::sc_spawn([this,i](){finish(i);});
      }
      if(retired==tasks.size())break;
      if(!running)throw std::runtime_error("dependency deadlock");
      wait(completion);
    }
    sc_core::sc_stop();
  }
};
int sc_main(int argc,char** argv) {
  try {
    if(argc!=2)throw std::runtime_error("usage: timed-resources trace.tsv");
    sc_core::sc_set_time_resolution(1,sc_core::SC_PS);
    std::ifstream in(argv[1]);if(!in)throw std::runtime_error("cannot read trace");
    std::vector<Task> tasks;std::string line;
    while(std::getline(in,line)) {
      if(line.empty()||line[0]=='#')continue;
      auto f=split(line,'\t');if(f.size()!=5)throw std::runtime_error("trace columns: id duration_ps deps resources energy_nJ");
      Task t;t.id=f[0];
      if(t.id.empty()||t.id.find_first_of("\\\"\r\n")!=std::string::npos)throw std::runtime_error("invalid id");
      if(f[1].empty()||!std::all_of(f[1].begin(),f[1].end(),[](char c){return c>='0'&&c<='9';}))throw std::runtime_error("invalid duration");
      t.duration=std::stoull(f[1]);if(f[2]!="-")t.deps=split(f[2],',');
      if(f[3]!="-")t.resources=split(f[3],',');
      if(t.duration==0||t.resources.empty())throw std::runtime_error("positive duration and resources required");
      if(std::set<std::string>(t.resources.begin(),t.resources.end()).size()!=t.resources.size())throw std::runtime_error("duplicate resource");
      if(f[4]!="?"){t.energy=std::stod(f[4]);if(!std::isfinite(*t.energy)||*t.energy<0)throw std::runtime_error("invalid energy");}
      tasks.push_back(std::move(t));
    }
    if(tasks.empty())throw std::runtime_error("empty trace");
    Runtime runtime("runtime",std::move(tasks));sc_core::sc_start();
    std::cout<<"RESULT {\"makespan_ps\":"<<sc_core::sc_time_stamp().value()<<",\"known_dynamic_nJ\":"<<std::setprecision(16)<<runtime.energy
             <<",\"energy_complete\":"<<(runtime.energy_complete?"true":"false")<<",\"tasks\":[";
    for(size_t i=0;i<runtime.tasks.size();++i){auto& t=runtime.tasks[i];if(i)std::cout<<",";
      // IDs in this foundation TSV must not contain JSON escape characters.
      std::cout<<"{\"id\":\""<<t.id<<"\",\"start_ps\":"<<t.start<<",\"end_ps\":"<<t.end<<"}";}
    std::cout<<"]}\n";return 0;
  }catch(const std::exception& e){std::cerr<<e.what()<<"\n";return 1;}
}
