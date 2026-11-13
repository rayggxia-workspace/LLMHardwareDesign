// Finite FIFO architectural timing model, calibrated against accepted P-S RTL.
// Payload numerics belong to the independent RTL/array tests, not this model.
#include <systemc>
#include <deque>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

struct Tag {bool b=false;unsigned tile=0,row=0,half=0;};
struct Event {unsigned cycle;char kind;unsigned row=0,tile=0,half=0;};
struct Feeder:sc_core::sc_module {
 unsigned rows,tiles;bool wide_b,reuse,stall;
 bool pending=false,memory_pending=false,phase_a,requests_done=false,weight_valid=false;
 unsigned response_count=0,tile=0,group=0,half=0,word=0,reads=0;
 Tag pending_tag,weight;std::deque<Tag> a_queue;std::vector<Event> events;
 unsigned done_cycle=0;
 Feeder(sc_core::sc_module_name name,unsigned r,unsigned t,bool b,bool reuse_b,bool stalled):
  sc_module(name),rows(r),tiles(t),wide_b(b),reuse(reuse_b),stall(stalled),phase_a(reuse_b){
  if(!r||r>8||!t||t>4)throw std::runtime_error("invalid feeder shape");
  SC_THREAD(run);
 }
 void until(unsigned cycle) {
  // Exact rational 300MHz periods rounded upward at each boundary, not 3333ps drift.
  uint64_t next=(uint64_t(cycle)*10000+2)/3,now=sc_core::sc_time_stamp().value();
  if(next<now)throw std::runtime_error("nonmonotone architectural clock");
  if(next>now)wait(sc_core::sc_time::from_value(next-now));
 }
 bool step(unsigned cycle) {
  const bool ar=!stall||cycle%7>=3,br=!stall||cycle%11>=4;
  const bool a_fire=!a_queue.empty()&&ar,b_fire=weight_valid&&br;
  const unsigned a_row=a_queue.empty()?0:a_queue.front().row+word;
  const bool pop=a_fire&&(word==3||a_row+1==rows);
  const bool space=a_queue.size()<2||pop,weight_space=!weight_valid||b_fire;
  const bool received=pending&&response_count&&(pending_tag.b?weight_space:space);
  const bool request=!requests_done&&(!pending||received)&&(phase_a?space:weight_space);
  const bool memory_ready=response_count+unsigned(memory_pending)<2||received;
  const bool fire=request&&memory_ready;
  const bool complete=requests_done&&!pending&&a_queue.empty()&&!weight_valid;
  if(a_fire)events.push_back({cycle,'A',a_row,a_queue.front().tile,0});
  if(b_fire)events.push_back({cycle,'B',0,weight.tile,weight.half});
  // All right-hand sides above use the same pre-edge state. Retiring an old
  // response and issuing its successor may occur together, as may A and B.
  if(a_fire) {if(pop){a_queue.pop_front();word=0;}else ++word;}
  if(b_fire)weight_valid=false;
  const Tag old_tag=pending_tag;
  if(received) {
   --response_count;pending=false;
   if(old_tag.b){weight=old_tag;weight_valid=true;}
   else a_queue.push_back(old_tag);
  }
  if(memory_pending)++response_count;
  memory_pending=fire;
  if(fire) {
   ++reads;pending=true;pending_tag={!phase_a,tile,group?4U:0U,half};
   if(!phase_a) {
    if(wide_b&&!half)half=1;
    else{half=0;phase_a=true;}
   }else if(rows>4&&!group)group=1;
   else {
    group=0;if(tile+1==tiles)requests_done=true;
    else{++tile;phase_a=reuse;}
   }
  }
  if(a_queue.size()>2||response_count+unsigned(memory_pending)>2)
   throw std::runtime_error("finite feeder/memory response capacity exceeded");
  return complete;
 }
 void run() {
  events.push_back({0,'L'});
  for(unsigned cycle=1;cycle<1000;++cycle) {
   until(cycle);
   if(step(cycle)) {
    done_cycle=cycle+1;until(done_cycle);events.push_back({done_cycle,'D'});
    // Match the independent fixture's three-cycle held completion and ACK.
    until(done_cycle+3);events.push_back({done_cycle+3,'T'});
    until(done_cycle+4);sc_core::sc_stop();return;
   }
  }
  throw std::runtime_error("architectural feeder deadlock");
 }
};
int sc_main(int argc,char**argv) {
 try {
  if(argc!=6)throw std::runtime_error("usage: systemc-feeder rows tiles wide_b reuse_b stalled");
  sc_core::sc_set_time_resolution(1,sc_core::SC_PS);
  Feeder f("feeder",std::stoul(argv[1]),std::stoul(argv[2]),std::stoul(argv[3]),std::stoul(argv[4]),std::stoul(argv[5]));
  sc_core::sc_start();
  std::cout<<"RESULT {\"makespan_ps\":"<<sc_core::sc_time_stamp().value()
   <<",\"period_cycles_with_done_hold3\":"<<f.done_cycle+4<<",\"done_visible_cycles\":"<<f.done_cycle
   <<",\"wide_memory_reads\":"<<f.reads<<",\"events\":[";
  for(size_t i=0;i<f.events.size();++i){auto e=f.events[i];if(i)std::cout<<",";
   std::cout<<"{\"cycle\":"<<e.cycle<<",\"kind\":\""<<e.kind<<"\",\"row\":"<<e.row
    <<",\"tile\":"<<e.tile<<",\"half\":"<<e.half<<"}";}
  std::cout<<"],\"scope\":\"timing-only finite architectural feeder; calibrated RTL data path separate; not full-model time or energy\"}\n";
  return 0;
 }catch(const std::exception&e){std::cerr<<e.what()<<"\n";return 1;}
}
