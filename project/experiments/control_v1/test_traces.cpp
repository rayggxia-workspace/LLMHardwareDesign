#include "Vcontrol_c.h"
#include "verilated.h"
#include <array>
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <random>
#include <vector>
static uint64_t checks=0,cycles=0;
static void need(bool x,const char* m){++checks;if(!x){std::cerr<<m<<" cycle "<<cycles<<"\n";std::exit(1);}}
static uint64_t ins(unsigned op,unsigned rd=0,unsigned ra=0,unsigned rb=0,unsigned flags=0,unsigned aux=0,uint32_t imm=0){
 return uint64_t(op)<<56|uint64_t(rd)<<52|uint64_t(ra)<<48|uint64_t(rb)<<44|uint64_t(flags)<<40|uint64_t(aux)<<32|imm;}
struct Sim {
 Vcontrol_c v;std::mt19937 rng{162};
 std::vector<std::array<uint32_t,8>> tasks;
 std::array<uint32_t,8> assembling{};unsigned word=0;
 bool random_ready=false,stall_seen=false;uint32_t held_data=0;unsigned held_ep=0,held_last=0;
 Sim(){v.clk=0;v.reset=1;v.cfg_valid=0;v.cfg_rsp_ready=1;v.cfg_write=0;v.cfg_addr=0;v.cfg_wdata=0;v.cfg_wstrb=15;
  v.task_ready=0;v.done_valid=0;v.done_data=0;v.done_last=0;for(int n=0;n<4;++n) tick();v.reset=0;tick();}
 void tick(){
  v.clk=0;if(random_ready)v.task_ready=(rng()%4)!=0;v.eval();
  if(!v.reset && stall_seen){need(v.task_valid,"task valid retained");need(v.task_data==held_data && v.task_endpoint==held_ep && v.task_last==held_last,"stalled task stable");}
  stall_seen=!v.reset && v.task_valid && !v.task_ready;
  if(stall_seen){held_data=v.task_data;held_ep=v.task_endpoint;held_last=v.task_last;}
  if(!v.reset && v.task_valid && v.task_ready){need(v.task_last==(word==7),"packet framing");need(v.task_endpoint<7,"trace uses current seven-endpoint reference destinations");
   assembling[word++]=v.task_data;if(word==8){tasks.push_back(assembling);word=0;}}
  v.clk=1;v.eval();++cycles;
 }
 uint32_t cfg(bool write,unsigned a,uint32_t d=0,bool error=false){
  unsigned timeout=0;while(!v.cfg_ready){tick();need(++timeout<100,"cfg ready timeout");}
  v.cfg_valid=1;v.cfg_write=write;v.cfg_addr=a;v.cfg_wdata=d;tick();v.cfg_valid=0;
  while(!v.cfg_rsp_valid){tick();need(++timeout<100,"cfg reply timeout");}
  need(bool(v.cfg_error)==error,"cfg error value");const uint32_t result=v.cfg_rdata;tick();return result;
 }
 void load(const std::vector<uint64_t>& p){for(unsigned n=0;n<p.size();++n){cfg(true,0x1000+n*8,uint32_t(p[n]));cfg(true,0x1004+n*8,p[n]>>32);}}
 void complete(uint16_t tag,unsigned ep=1,unsigned status=0,uint32_t result=0){
  v.done_valid=1;v.done_last=0;v.done_data=tag|(ep<<16)|(status<<20);tick();
  v.done_last=1;v.done_data=result;tick();v.done_valid=0;v.done_last=0;tick();
 }
 void wait_end(){for(unsigned n=0;n<1000 && !v.ended && !v.fault;++n)tick();need(v.ended && v.fault==0,"program end");}
};

// These programs validate C instruction/descriptor capacity and task transport.
// Endpoint completions below are an oracle, not numerical execution of models.
int main(int argc,char**argv){Verilated::commandArgs(argc,argv);
 struct Profile{const char*name;unsigned layers,h,ff;bool qknorm,gelu,moe,recurrent;};
 const std::array<Profile,8> profiles{{
  {"Qwen2.5-3B",36,2048,11008,false,false,false,false},
  {"Qwen3-0.6B",28,1024,3072,true,false,false,false},
  {"Llama-3.2-1B",16,2048,8192,false,false,false,false},
  {"Gemma-3-4B",34,2560,10240,true,true,false,false},
  {"Phi-4-mini",32,3072,8192,false,false,false,false},
  {"Qwen3.5-4B",32,2560,9216,true,false,false,true},
  {"Granite-3.3B",32,1536,512,false,false,true,false},
  {"Falcon-H1-3B",32,2560,6144,false,false,false,true}}};
 std::cout<<"{\"passed\":true,\"scope\":\"C control transport and program capacity only; oracle completions, no endpoint numerical/model or physical qualification\",\"profiles\":[";
 unsigned profile_index=0;
 for(const auto&p:profiles){Sim s;s.random_ready=true;
  // Distinct stage descriptors retain shape and stage identity through C.
  const std::array<unsigned,16> roles{{0,2,2,2,2,1,3,1,2,2,2,3,4,3,1,0}};
  for(unsigned d=0;d<16;++d){s.cfg(true,0x2000+d*32,roles[d]<<8);s.cfg(true,0x2004+d*32,p.h);
   s.cfg(true,0x2008+d*32,p.ff);s.cfg(true,0x200c+d*32,d);}
  std::vector<unsigned> stages{0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15};
  if(p.qknorm)stages.insert(stages.begin()+6,{1,2,3,4});
  if(p.gelu)stages.insert(stages.end()-3,12);
  if(p.moe)for(unsigned expert=0;expert<8;++expert)stages.insert(stages.end()-1,{5,12,13,14});
  if(stages.size()%2)stages.push_back(15);
  std::vector<uint64_t> code{ins(1,0,0,0,0,0,p.layers),ins(9,0,0)};
  for(unsigned n=0;n<stages.size();n+=2){code.push_back(ins(13,1,stages[n]));code.push_back(ins(13,2,stages[n+1]));code.push_back(ins(14,3,2));code.push_back(ins(14,4,1));}
  code.push_back(ins(10));code.push_back(ins(18));need(code.size()<=256,"finite program capacity");s.load(code);s.cfg(true,4,1);
  unsigned consumed=0,guard=0;
  while(!s.v.ended && !s.v.fault){s.tick();need(++guard<300000,"finite trace completion");
   if(s.tasks.size()>=consumed+2){
    for(unsigned j=0;j<2;++j){auto&t=s.tasks[consumed+j];unsigned stage=stages[(consumed+j)%stages.size()];
     need(((t[0]>>8)&15)==roles[stage],"independent expected endpoint order");need(t[1]==p.h && t[2]==p.ff && t[3]==stage,"shape and stage fields retained");}
    // Deliberately complete the second asynchronous event before the first.
    for(unsigned j:{1u,0u}){auto&t=s.tasks[consumed+j];s.complete(t[0]>>16,(t[0]>>8)&15,0,consumed+j);}
    consumed+=2;
   }
  }
  need(s.v.ended && !s.v.fault,"trace program ended");need(consumed==p.layers*stages.size(),"independent layer/stage task count");
  need(s.cfg(false,0x10)==consumed && s.cfg(false,0x14)==consumed,"submitted/completed CSR counts");
  // For recurrent profiles, separately prove R dispatch is rejected rather
  // than silently replacing the unaccepted recurrence by an attention path.
  if(p.recurrent){s.cfg(true,4,2);s.cfg(true,0x2000,7<<8);s.load({ins(13),ins(18)});s.cfg(true,4,1);
   for(unsigned n=0;n<30&&!s.v.fault;++n)s.tick();need(s.v.fault==5,"recurrent R admission forbidden");}
  if(profile_index++)std::cout<<',';
  std::cout<<"{\"name\":\""<<p.name<<"\",\"program_words\":"<<code.size()<<",\"descriptors\":16,\"issued_tasks\":"<<consumed<<",\"recurrent_path_blocked\":"<<(p.recurrent?"true":"false")<<",\"full_model_supported\":false}";
 }
 std::cout<<"],\"checks\":"<<checks<<",\"cycles\":"<<cycles<<"}\n";
}
