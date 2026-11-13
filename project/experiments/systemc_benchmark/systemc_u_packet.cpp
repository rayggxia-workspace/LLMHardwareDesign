// Composable clocked timing of the existing U E13/S/N packet service.
// Models the shared S arbiter and registered response, both service FSMs,
// and resident E/N pipelines. No measured whole-service duration is read.
// Payload math is verified independently by the corresponding actual RTL TB.
// Current descriptor scope: one E13 conversion and N softmax Begin/Stats2/
// Finalize/Exp1. This is not LC execution or full Qwen time/energy.
#include <systemc>
#include <array>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

struct Service {
 enum Phase {Idle,ReadReq,ReadRsp,Exec,Result,WriteReq,WriteRsp,Done};
 Phase phase=Idle;unsigned op=0,remaining=0;bool store=false;
 bool leaf_valid=false;unsigned leaf_remaining=0;bool seen=false;
 bool request()const{return phase==ReadReq||phase==WriteReq;}
 bool take()const{return phase==ReadRsp||phase==WriteRsp;}
};
struct UTiming {
 enum Arb {Idle,Send,Return};
 Arb arb=Idle;unsigned owner=0,next_owner=0;
 bool pending=false;unsigned responses=0;
 std::array<Service,2> clients; // physical S clients: N0, E1
 struct Drive {unsigned kind=0,op=0,sources=0;bool store=false,valid=false,ready=false;};
 // kind:0 IO write(client2),1 E(client1),2 IO read(client3),3 N(client0)
 std::vector<std::string> events;
 void event(unsigned c,const std::string& kind,unsigned client){
  events.push_back("EV "+std::to_string(c)+" "+kind+" "+std::to_string(client));
 }
 bool issue_ready(const Drive& d)const {
  if(d.kind==1||d.kind==3)return clients[d.kind==1?1:0].phase==Service::Idle;
  return arb==Idle;
 }
 bool output_valid(const Drive& d)const {
  if(d.kind==1||d.kind==3)return clients[d.kind==1?1:0].phase==Service::Done;
  return arb==Return&&owner==(d.kind==0?2U:3U)&&responses;
 }
 void step(unsigned c,const Drive& d){
  std::array<bool,4> req{},take{};
  for(unsigned i=0;i<2;++i){req[i]=clients[i].request();take[i]=clients[i].take();}
  if(d.kind==0||d.kind==2){unsigned i=d.kind==0?2:3;req[i]=d.valid;take[i]=d.ready;}
  unsigned selected=4;
  if(arb==Idle)for(unsigned k=0;k<4;++k){unsigned i=(next_owner+k)%4;if(req[i]){selected=i;break;}}
  const bool memory_accept=arb==Send&&responses+unsigned(pending)<2;
  const bool response=arb==Return&&responses;
  const bool consume=response&&take[owner];
  const unsigned old_owner=owner;
  if(selected<4)event(c,"S_REQ",selected);
  if(consume)event(c,"S_RSP",owner);
  // Every decision below uses pre-edge signals, just like the RTL NBAs.
  for(unsigned i=0;i<2;++i){
   auto& s=clients[i];const auto old=s.phase;
   const bool command=(d.kind==(i==1?1U:3U))&&d.valid&&old==Service::Idle;
   const bool ack=(d.kind==(i==1?1U:3U))&&d.ready;
   const bool leaf_response=s.leaf_valid;
   if(command){event(c,"CMD",i==1?0:1);s.seen=false;}
   if(old==Service::Done&&!s.seen){event(c,"DONE",i==1?0:1);s.seen=true;}
   if(old==Service::Done&&ack)event(c,"TAKE",i==1?0:1);
   if(old==Service::Result&&leaf_response)s.leaf_valid=false;
   if(s.leaf_remaining&&!--s.leaf_remaining)s.leaf_valid=true;
   switch(old){
    case Service::Idle:if(command){s.op=d.op;s.store=d.store;s.remaining=d.sources;s.phase=d.sources?Service::ReadReq:Service::Exec;}break;
    case Service::ReadReq:if(selected==i)s.phase=Service::ReadRsp;break;
    case Service::ReadRsp:if(response&&old_owner==i){if(!--s.remaining)s.phase=Service::Exec;else s.phase=Service::ReadReq;}break;
    case Service::Exec:
     if(s.leaf_valid||s.leaf_remaining)throw std::runtime_error("leaf unexpectedly busy");
     if(i==1)s.leaf_remaining=3; // E MUL/TOTAL/WRITE after acceptance
     else if(s.op==1||s.op==3)s.leaf_remaining=2; // N pair CALC/ACCUM
     else s.leaf_valid=true; // softmax Begin/Finalize reply at acceptance
     s.phase=Service::Result;break;
    case Service::Result:if(leaf_response)s.phase=s.store?Service::WriteReq:Service::Done;break;
    case Service::WriteReq:if(selected==i)s.phase=Service::WriteRsp;break;
    case Service::WriteRsp:if(response&&old_owner==i)s.phase=Service::Done;break;
    case Service::Done:if(ack)s.phase=Service::Idle;break;
   }
  }
  if(pending)++responses;
  if(consume){if(!responses)throw std::runtime_error("S response underflow");--responses;}
  pending=memory_accept;
  if(selected<4){owner=selected;next_owner=(selected+1)%4;arb=Send;}
  else if(memory_accept)arb=Return;
  else if(consume)arb=Idle;
  if(responses+unsigned(pending)>2)throw std::runtime_error("S response capacity exceeded");
 }
};
struct Test:sc_core::sc_module {
 UTiming u;unsigned final_cycle=0;
 Test(sc_core::sc_module_name name):sc_module(name){SC_THREAD(run);}
 void until(uint64_t ps){auto now=sc_core::sc_time_stamp().value();if(ps<now)throw std::runtime_error("nonmonotone U clock");if(ps>now)wait(sc_core::sc_time::from_value(ps-now));}
 void run(){
  struct Operation{unsigned kind,op,sources,hold;bool store;};
  std::vector<Operation> operations;
  for(unsigned input=0;input<11;++input){
   operations.push_back({0,0,0,2,false}); // canonical input write + held ACK
   operations.push_back({1,13,1,3,true}); // E13 format + stored result
   operations.push_back({2,0,0,0,false}); // read back complete packet
   operations.push_back({3,0,0,3,false}); // Begin softmax
   operations.push_back({3,1,1,3,false}); // Stats two lanes, one S word
   operations.push_back({3,2,0,3,false}); // Finalize softmax
   operations.push_back({3,3,1,3,true}); // Exp one lane, stored result
   operations.push_back({2,0,0,0,false}); // read back complete answer
  }
  unsigned current=0,stage=0,left=0; // issue / wait / hold / take
  for(unsigned c=3;c<100000;++c){
   const auto op=operations.at(current);
   UTiming::Drive d{op.kind,op.op,op.sources,op.store,stage==0,stage==3};
   const bool issued=d.valid&&u.issue_ready(d),taken=d.ready&&u.output_valid(d);
   until((uint64_t(c)*10000+5002)/3);u.step(c,d);
   until((uint64_t(c+1)*10000+2)/3); // fixture samples on negative edge
   if(stage==0&&issued)stage=1;
   else if(stage==1&&u.output_valid(d)){left=op.hold;stage=left?2:3;}
   else if(stage==2&&!--left)stage=3;
   else if(stage==3&&taken){if(++current==operations.size()){final_cycle=c;sc_core::sc_stop();return;}stage=0;}
  }
  throw std::runtime_error("U packet fixture deadlocked");
 }
};
int sc_main(int argc,char**){
 try{
  if(argc!=1)throw std::runtime_error("no input latency table or trace accepted");
  sc_core::sc_set_time_resolution(1,sc_core::SC_PS);Test test("U");sc_core::sc_start();
  for(const auto& e:test.u.events)std::cout<<e<<'\n';
  std::cout<<"RESULT {\"events\":"<<test.u.events.size()<<",\"elapsed_ps\":"<<sc_core::sc_time_stamp().value()<<",\"full_model_qualified\":false,\"energy_qualified\":false}\n";return 0;
 }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
}
