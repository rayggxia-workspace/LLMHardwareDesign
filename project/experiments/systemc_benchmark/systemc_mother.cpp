// Runtime-only architectural mother model, independent of Verilated RTL.
// Deployed compact images; CALL/WAIT/MOVI/END, two targets, eight tokens.
// PM explicitly traverses its real request/bank-response/response states.
// Configuration, faults, EVENT bindings and nine-target hardware are not modeled.
#include <systemc>
#include <array>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

struct MotherEvent { unsigned cycle; char kind; unsigned value,detail; std::array<unsigned,8> arguments{}; };
struct Peer {bool busy=false,valid=false; unsigned timer=0;};
struct Mother:sc_core::sc_module {
 enum Seq {IDLE,FETCH,WAIT_PM,DECODE,CALL_HOLD,RESULT_HOLD};
 Seq seq=IDLE;
 enum PM {PM_IDLE,PM_ISSUE,PM_WAIT,PM_RESPOND};
 PM pm=PM_IDLE;
 std::vector<sc_dt::sc_biguint<128>> memory;
 std::array<Peer,2> peers{};
 std::array<bool,2> active{},terminal{};
 std::array<unsigned,2> token{};
 std::array<unsigned,8> registers{};
 unsigned live=0,rr=0,pc=0,steps=0,count=0,max_steps=0,request_pc=0;
 unsigned runs,started=0,retired=0,next_start=0,hold_age=0,result_visible=0;
 unsigned delay0,delay1,hold_cycles;
 int hold_target;
 bool bank_pending=false;unsigned bank_count=0;
 uint64_t instruction=0;
 bool result_seen=false;
 std::vector<MotherEvent> events;
 unsigned period_cycles=0;
 Mother(sc_core::sc_module_name name,const std::string& image,unsigned jobs,
        unsigned d0,unsigned d1,int ht,unsigned hc):sc_module(name),runs(jobs),
        delay0(d0),delay1(d1),hold_cycles(hc),hold_target(ht) {
  std::ifstream input(image);std::string word;
  if(!input)throw std::runtime_error("missing image");
  while(input>>word) {
   if(word.size()!=32||word.find_first_not_of("0123456789abcdefABCDEF")!=std::string::npos)
    throw std::runtime_error("expected128bit hex image words");
   memory.emplace_back(("0x"+word).c_str());
  }
  if(memory.size()<9||!runs||hold_target< -1||hold_target>1)
   throw std::runtime_error("invalid image or fixture scope");
  count=memory[1].range(63,32).to_uint();max_steps=memory[3].range(63,32).to_uint();
  if(memory[0].range(79,64).to_uint()!=2||memory[1].range(95,64).to_uint()!=128||
     memory[4].range(79,64).to_uint()!=0||!count||count>256||!max_steps||
     memory.size()!=8+(count+1)/2)
   throw std::runtime_error("only deployed compact images without EVENT bindings are modeled");
  SC_THREAD(run);
 }
 void until(unsigned cycle) {
  uint64_t next=(uint64_t(cycle)*10000+2)/3,now=sc_core::sc_time_stamp().value();
  if(next<now)throw std::runtime_error("nonmonotone clock");
  if(next>now)wait(sc_core::sc_time::from_value(next-now));
 }
 void event(unsigned cycle,char kind,unsigned value=0,unsigned detail=0) {
  events.push_back({cycle,kind,value,detail,kind=='C'?registers:std::array<unsigned,8>{}});
 }
 bool step(unsigned cycle) {
  const unsigned op=instruction>>56,a=(instruction>>48)&255,b=(instruction>>40)&255;
  const bool start=seq==IDLE&&started<runs&&cycle>=next_start;
  const bool pm_fire=seq==FETCH&&pm==PM_IDLE;
  const bool pm_done=seq==WAIT_PM&&pm==PM_RESPOND;
  const bool call=seq==CALL_HOLD&&!peers[a].busy&&
                  !(int(a)==hold_target&&hold_age<hold_cycles);
  const unsigned selected=peers[rr].valid?rr:1-rr;
  const bool returned=peers[selected].valid;
  const bool was_result=seq==RESULT_HOLD;
  const bool first_result=was_result&&!result_seen;
  const bool ack=was_result&&result_seen&&cycle>=result_visible+5;
  const bool memory_take=pm==PM_WAIT&&bank_count;
  const bool bank_request=pm==PM_ISSUE;
  // Simultaneous actions below all consume the same pre-edge state.
  if(start)event(cycle,'S');
  if(call)event(cycle,'C',a,b);
  if(returned)event(cycle,'R',selected);
  if(first_result)event(cycle,'D');
  if(ack)event(cycle,'A');
  for(unsigned i=0;i<2;++i) {
   if(peers[i].busy&&!peers[i].valid) {
    if(peers[i].timer)--peers[i].timer;else peers[i].valid=true;
   }
  }
  if(seq==CALL_HOLD&&int(a)==hold_target)++hold_age;
  switch(pm) {
   case PM_IDLE:if(pm_fire){pm=PM_ISSUE;request_pc=pc;}break;
   case PM_ISSUE:pm=PM_WAIT;break;
   case PM_WAIT:if(memory_take)pm=PM_RESPOND;break;
   case PM_RESPOND:if(pm_done)pm=PM_IDLE;break;
  }
  if(memory_take)--bank_count;
  if(bank_pending)++bank_count;
  bank_pending=bank_request;
  if(bank_count+unsigned(bank_pending)>2)throw std::runtime_error("PM bank overflow");
  if(start) {
   seq=FETCH;pc=steps=hold_age=live=0;active={};terminal={};registers={};
   result_seen=false;++started;
  }else if(pm_fire) {
   if(pc>=count||steps>=max_steps)throw std::runtime_error("program bound exceeded");
   seq=WAIT_PM;
  }else if(pm_done) {
   const auto word=memory.at(8+request_pc/2);
   instruction=request_pc%2?word.range(127,64).to_uint64():word.range(63,0).to_uint64();
   seq=DECODE;
  }else if(seq==DECODE) {
   if(op==0x10) {
    if(a>=2||b>=8||((instruction>>32)&255)||(instruction&0xffffffffULL)||
       active[a]||(live&(1U<<b)))throw std::runtime_error("illegal CALL");
    active[a]=true;terminal[a]=false;token[a]=b;live|=1U<<b;seq=CALL_HOLD;
   }else if(op==0x11) {
    if(instruction&0x00ffffff00000000ULL)throw std::runtime_error("reserved WAIT fields");
    unsigned mask=instruction&0xffffffffULL,done=0;
    for(unsigned i=0;i<2;++i)if(terminal[i])done|=1U<<token[i];
    if(!mask||(mask&~live))throw std::runtime_error("WAIT without allocated tokens");
    if(!(mask&~done)) {
     live&=~mask;
     for(unsigned i=0;i<2;++i)if(active[i]&&(mask&(1U<<token[i])))active[i]=terminal[i]=false;
     event(cycle,'I',pc,op);++pc;++steps;seq=FETCH;
    }
   }else if(op==0x13) {
    if(a>=8||(instruction&0x0000ffff00000000ULL))throw std::runtime_error("illegal MOVI");
    registers[a]=instruction&0xffffffffULL;event(cycle,'I',pc,op);++pc;++steps;seq=FETCH;
   }else if(op==0x1f) {
    if((instruction&0x00ffffffffffffffULL)||live||active[0]||active[1])
     throw std::runtime_error("END before drain");
    seq=RESULT_HOLD;result_seen=false;
   }else throw std::runtime_error("unsupported runtime opcode; do not assign a free cost");
  }
  if(call) {
   peers[a]={true,false,a?delay1:delay0};event(cycle,'I',pc,op);++pc;++steps;seq=FETCH;
  }
  if(returned) {
   if(!active[selected]||terminal[selected])throw std::runtime_error("unowned terminal return");
   peers[selected]={};terminal[selected]=true;rr=1-selected;
  }
  if(first_result){result_seen=true;result_visible=cycle;}
  if(ack) {
   if(peers[0].busy||peers[1].busy||live)throw std::runtime_error("result before peer drain");
   event(cycle,'I',pc,op);++retired;seq=IDLE;next_start=cycle+1;
  }
  return retired==runs;
 }
 void run() {
  for(unsigned cycle=0;cycle<100000;++cycle) {
   until(cycle);
   if(step(cycle)){period_cycles=cycle+1;until(period_cycles);sc_core::sc_stop();return;}
  }
  throw std::runtime_error("mother runtime deadlock");
 }
};
int sc_main(int argc,char**argv) {
 try {
  if(argc!=7)throw std::runtime_error("usage: systemc-mother image runs delay0 delay1 hold_target hold_cycles");
  sc_core::sc_set_time_resolution(1,sc_core::SC_PS);
  Mother m("mother",argv[1],std::stoul(argv[2]),std::stoul(argv[3]),std::stoul(argv[4]),std::stoi(argv[5]),std::stoul(argv[6]));
  sc_core::sc_start();
  std::cout<<"RESULT {\"cycles\":"<<m.period_cycles<<",\"makespan_ps\":"<<sc_core::sc_time_stamp().value()<<",\"events\":[";
  for(size_t i=0;i<m.events.size();++i){const auto&e=m.events[i];if(i)std::cout<<",";
   std::cout<<"{\"cycle\":"<<e.cycle<<",\"kind\":\""<<e.kind<<"\",\"value\":"<<e.value<<",\"detail\":"<<e.detail;
   if(e.kind=='C'){std::cout<<",\"arguments\":[";for(unsigned j=0;j<8;++j){if(j)std::cout<<",";std::cout<<e.arguments[j];}std::cout<<"]";}
   std::cout<<"}";}
  std::cout<<"],\"complete_system_qualified\":false,\"energy_qualified\":false}\n";return 0;
 }catch(const std::exception&e){std::cerr<<e.what()<<"\n";return 1;}
}
