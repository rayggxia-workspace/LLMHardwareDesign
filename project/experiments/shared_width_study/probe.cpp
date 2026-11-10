// Directed probe of the actual generated conditional scheduler, not an RTL claim.
// Inputs are generated independently by check_probe.py; returned addresses select
// payload and dot-product terms. No expected output is passed to this executable.
#define SC_INCLUDE_DYNAMIC_PROCESSES
#include <systemc>
#include <algorithm>
#include <array>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <memory>
#include <stdexcept>
#include <string>
#include <vector>
using namespace sc_core;
using U=uint64_t;
constexpr U C=1000;
U now(){return sc_time_stamp().value();}
U ceildiv(U a,U b){return (a+b-1)/b;}
void pause_until(U t){if(t>now()){wait(sc_time::from_value(t-now()));}}
void require(bool value,const char* message){if(!value){throw std::runtime_error(message);}}
struct Calendar {
 std::vector<std::pair<U,U>> slots;U busy=0,queue_wait=0,calls=0;
 U reserve(U at,U duration){
  auto z=std::remove_if(slots.begin(),slots.end(),[](auto p){return p.second<=now();});slots.erase(z,slots.end());
  U start=at;size_t i=0;
  for(;i<slots.size();++i){if(start+duration<=slots[i].first){break;}start=std::max(start,slots[i].second);}
  slots.insert(slots.begin()+static_cast<long>(i),{start,start+duration});
  busy+=duration;queue_wait+=start-at;++calls;return start+duration;
 }
};
#include "shared_pool.hpp"
struct Request {U row,rows,ki,count;};
struct Case {int id;U rows,k;int stall;std::array<Request,2> requests;
 std::vector<int64_t> A;std::array<std::vector<int64_t>,2>B;};
struct Probe:sc_module {
 std::vector<Case> cases;std::ofstream events,actual;bool passed=false;
 Probe(sc_module_name n,const char* input,const char* event_path,const char* actual_path):sc_module(n),events(event_path),actual(actual_path){
  std::ifstream f(input);int size;f>>size;
  for(int i=0;i<size;++i){Case c;f>>c.id>>c.rows>>c.k>>c.stall;
   for(auto& r:c.requests){f>>r.row>>r.rows>>r.ki>>r.count;}
   c.A.resize(c.rows*c.k);for(auto& value:c.A){f>>value;}
   for(auto& weights:c.B){weights.resize(c.k);for(auto& value:weights){f>>value;}}
   cases.push_back(std::move(c));}
  require(bool(f)&&bool(events)&&bool(actual),"directed probe input/output");SC_THREAD(run);
 }
 void run(){
  bool comma=false;actual<<"{\"cases\":[";
  for(const auto& c:cases){
   shared_pool::Pool pool;pool.configure(32768,4,2,1);
   const U base=4096;require(pool.begin(base,c.rows,c.k,4,256),"disabled directed object");
   require(pool.cached_k()==c.k,"directed shape must fit in fixed32KiB");
   U ack=now();
   for(U row=0;row<c.rows;++row){for(U off=0;off<c.k*4;off+=64){ack=pool.write(ack,row*pool.stride+off,std::min<U>(64,c.k*4-off));}}
   pause_until(ack);pool.filled();const U epoch=pool.epoch;
   events<<"{\"kind\":\"begin\",\"case\":"<<c.id<<",\"epoch\":"<<epoch<<",\"prefix_k\":"<<pool.cached_k()<<",\"stride\":"<<pool.stride<<",\"time\":"<<now()<<"}\n";
   std::array<int64_t,2> dots{{0,0}};std::array<U,2> totals{{0,0}};
   pool.consumer_ready_at=[&](const shared_pool::Consumed& e){
    events<<"{\"kind\":\"select\",\"case\":"<<c.id<<",\"worker\":"<<e.worker<<",\"tile\":"<<e.tile_id<<",\"epoch\":"<<e.epoch
     <<",\"row\":"<<e.row<<",\"pool\":"<<e.pool_address<<",\"bytes\":"<<e.bytes<<",\"ready\":"<<e.ready_at<<",\"chosen\":"<<e.consumed_at-C<<"}\n";
    const U delay=c.stall==2?(e.pool_address==0?20:0):
      (c.stall?U(((e.source_address/4)%17==0)?19:3):0);
    return e.consumed_at+delay*C;
   };
   pool.on_issue=[&](const shared_pool::Issued& e){
    events<<"{\"kind\":\"issue\",\"case\":"<<c.id<<",\"worker\":"<<e.worker<<",\"tile\":"<<e.tile_id<<",\"epoch\":"<<e.epoch
     <<",\"pool\":"<<e.pool_address<<",\"bytes\":"<<e.bytes<<",\"issued\":"<<e.issued_at<<",\"ready\":"<<e.ready_at
     <<",\"release\":"<<e.credit_release_at<<",\"outstanding\":"<<e.outstanding<<"}\n";
   };
   pool.on_consume=[&](const shared_pool::Consumed& e){
    require(e.worker>=0&&e.worker<2&&e.bytes%4==0&&e.source_address%4==0,"directed element alignment");
    require(e.source_address>=base&&e.source_address+e.bytes<=base+c.A.size()*4,"directed source bounds");
    for(U i=0;i<e.bytes;i+=4){U index=(e.source_address-base+i)/4;dots[e.worker]+=c.A[index]*c.B[e.worker][index%c.k];}
    totals[e.worker]+=e.bytes;
    events<<"{\"kind\":\"consume\",\"case\":"<<c.id<<",\"worker\":"<<e.worker<<",\"tile\":"<<e.tile_id<<",\"epoch\":"<<e.epoch
     <<",\"row\":"<<e.row<<",\"source\":"<<e.source_address<<",\"pool\":"<<e.pool_address<<",\"bytes\":"<<e.bytes
     <<",\"ready\":"<<e.ready_at<<",\"consumed\":"<<e.consumed_at<<"}\n";
   };
   std::vector<sc_process_handle> jobs;
   for(int worker=0;worker<2;++worker){if(c.requests[worker].rows){jobs.push_back(sc_spawn([&,worker]{
    const auto& r=c.requests[worker];const U tile=U(c.id)*2+U(worker)+1;
    events<<"{\"kind\":\"tile\",\"case\":"<<c.id<<",\"worker\":"<<worker<<",\"tile\":"<<tile<<",\"start\":"<<r.ki
     <<",\"count\":"<<r.count<<",\"row_start\":"<<r.row<<",\"rows\":"<<r.rows<<",\"col\":"<<worker<<",\"local_ready\":0}\n";
    U got=pool.feed(worker,r.row,r.rows,r.ki,r.count,tile);
    require(got==totals[worker],"directed callback receipt mismatch");
    events<<"{\"kind\":\"endtile\",\"case\":"<<c.id<<",\"worker\":"<<worker<<",\"tile\":"<<tile<<",\"bytes\":"<<got<<",\"time\":"<<now()<<"}\n";
   }));}}
   for(auto& job:jobs){if(!job.terminated()){wait(job.terminated_event());}}
   pool.end();events<<"{\"kind\":\"end\",\"case\":"<<c.id<<",\"epoch\":"<<epoch<<",\"time\":"<<now()<<"}\n";
   if(comma){actual<<",";}comma=true;
   actual<<"{\"id\":"<<c.id<<",\"dot\":["<<dots[0]<<","<<dots[1]<<"]}";
  }
  actual<<"]}\n";actual.flush();events.flush();passed=true;sc_stop();
 }
};
int sc_main(int argc,char** argv){
 try{require(argc==4,"probe arguments");sc_set_time_resolution(1,SC_PS);Probe p("probe",argv[1],argv[2],argv[3]);sc_start();require(p.passed,"probe incomplete");return 0;}
 catch(const std::exception& e){std::cerr<<e.what()<<"\n";return 1;}
}
