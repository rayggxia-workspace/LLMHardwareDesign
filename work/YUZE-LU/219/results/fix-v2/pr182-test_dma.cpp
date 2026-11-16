#include "Vhbm_dma_system.h"
#include "verilated.h"
#include <algorithm>
#include <array>
#include <cstdint>
#include <deque>
#include <iostream>
#include <map>
#include <memory>
#include <optional>
#include <random>
#include <stdexcept>
#include <string>
#include <vector>
using U128=__uint128_t;
static uint64_t checks=0;
static void ck(bool x,const std::string& m){++checks;if(!x)throw std::runtime_error(m);}
static U128 get(const WData* p){U128 x=0;for(int j=3;j>=0;--j)x=(x<<32)|p[j];return x;}
static void put(WData* p,U128 x){for(int j=0;j<4;++j){p[j]=uint32_t(x);x>>=32;}}
static int av(int s,int r,int k){return (s*13+r*7+k*3)%23-11;}
static int bv(int s,int n,int k){return (s*11+n*5+k*7)%19-9;}
static U128 dataword(int s,int a){
 U128 x=0;
 if(a<32){for(int j=0;j<8;++j)x|=U128(uint8_t(av(s,a%8,a/8*8+j)))<<(j*8);}
 else if(a>=64&&a<80){for(int j=0;j<16;++j){int index=(a-64)%4*16+j;x|=U128(uint8_t(bv(s,index/8,(a-64)/4*8+index%8)))<<(j*8);}}
 else{for(int j=0;j<4;++j)x|=U128(uint32_t((s+1)*0x1020304u)^uint32_t(a*65537u+j*0x12345u))<<(j*32);}
 return x;
}
static uint64_t source(int s){return uint64_t(s+1)*0x100000;}
static uint64_t destination(int s){return 0x10000000ULL+uint64_t(s)*0x100000;}
struct Config{int groups=2,per=2,channels=2,credits=4,queue=32,words=256,seed=181;
 int period=6,phase=1,latency=20,stall=0,cplhold=0,error=0,fault=0;bool pause=false,mixed=false,reset=false,corrupt=false,boundary=false;};
struct Request{uint16_t id;uint64_t address,due,accepted;bool write;U128 data;unsigned status=0;};
struct Bank{int64_t row=-1;uint64_t free=0;};
struct Channel{std::deque<Request> q;std::optional<Request> held;std::array<Bank,4> bank;
 uint64_t busfree=0;bool write=false;};
struct Job{bool write;uint64_t address;int local,words;uint16_t tag;};
struct Result{uint64_t ticks=0,bytes=0,requests=0,completions=0,acks=0,isolated=0,held=0;
 uint64_t maxlive=0,maxqueue=0,request_stalls=0,response_stalls=0,maxbypass=0;
 std::array<uint64_t,16> per_requests{},per_acks{},per_words{};};
struct Simulation{
 Config c;std::unique_ptr<Vhbm_dma_system> d;std::mt19937 rng;uint64_t now=0,cores=0,mems=0;
 uint64_t stage_start=0;bool transfer=false,paused_once=false,injected=false,read_error=false,write_error=false;
 std::array<Channel,4> channel;std::map<uint64_t,U128> memory;std::map<uint16_t,Request> outstanding;
 std::array<Job,16> job{};std::vector<int> active;Result stats;
 std::array<bool,4> memheld{};std::array<std::array<uint32_t,6>,4> mempacket{};
 std::array<bool,16> sheld{},cheld{};std::array<U128,16> sdata{};std::array<int,16> saddr{},swrite{};
 std::array<uint64_t,16> cpacket{};std::array<unsigned,16> bypass{};
 uint64_t matrices=0,matrix_values=0,failed_completions=0,boundary_transfers=0;
 explicit Simulation(Config cfg):c(cfg),d(new Vhbm_dma_system),rng(cfg.seed){
  for(int g=0;g<c.groups;++g)for(int j=0;j<c.per;++j)active.push_back(g*4+j);
  for(int s=0;s<16;++s)for(int a=0;a<1024;++a)memory[source(s)+uint64_t(a)*16]=dataword(s,a);
  d->core_clk=0;d->mem_clk=0;d->reset=1;d->channel_count=c.channels;d->credit_limit=c.credits;
  d->desc_valid=0;d->desc_write=0;d->complete_ready=0;d->hold_s=0;d->mem_ready=0;d->response_valid=0;
  d->load_valid=0;d->done_take=0;d->select_s=0;d->cmd_valid=0;d->rsp_ready=0;d->a_allow=1;d->b_allow=1;
  d->eval();for(int t=0;t<200;++t)step();d->reset=0;d->eval();
 }
 bool coreedge()const{return now%10==0&&!(transfer&&c.pause&&now-stage_start>=2000&&now-stage_start<4000);}
 bool memedge()const{return now%uint64_t(c.period)==uint64_t(c.phase);}
 int route(int s)const{return (s/4)%c.channels;}
 void step(){
  d->core_clk=0;d->mem_clk=0;d->eval();bool a=coreedge(),b=memedge();
  d->core_clk=a;d->mem_clk=b;d->eval();if(a)++cores;if(b)++mems;
  d->core_clk=0;d->mem_clk=0;d->eval();++now;
 }
 void corestep(){while(!coreedge())step();step();}
 void reset_all(){
  d->reset=1;d->desc_valid=0;d->complete_ready=0;d->hold_s=0;d->response_valid=0;d->mem_ready=0;
  transfer=false;for(int t=0;t<200;++t)step();d->reset=0;
  for(auto& ch:channel){ch=Channel{};}
  outstanding.clear();memheld.fill(false);sheld.fill(false);cheld.fill(false);bypass.fill(0);
  d->eval();ck(!d->protocol_error&&!d->busy&&!d->complete_valid,"coordinated reset left live state");
 }
 void memory_event(){
  d->mem_ready=0;d->response_valid=0;
  if(!memedge())return;
  for(int ch=0;ch<c.channels;++ch){auto& m=channel[ch];
   bool valid=(d->mem_valid>>ch)&1;
   if(memheld[ch]){ck(valid,"memory request valid dropped under stall");for(int k=0;k<6;++k)ck(d->mem_data[ch][k]==mempacket[ch][k],"memory request changed under stall");}
   bool ready=int(m.q.size()+size_t(m.held.has_value()))<c.queue&&rng()%5!=0;
   if(ready)d->mem_ready|=1u<<ch;
   memheld[ch]=valid&&!ready;
   if(memheld[ch]){++stats.request_stalls;for(int k=0;k<6;++k)mempacket[ch][k]=d->mem_data[ch][k];}
   if(valid&&ready){auto* p=d->mem_data[ch].data();
    Request r{uint16_t((p[5]>>8)&65535),uint64_t(p[4])|(uint64_t(p[5]&255)<<32),0,now,bool((p[5]>>24)&1),get(p),0};
    int s=(r.id>>3)&15;ck(route(s)==ch,"request emitted on wrong channel");ck(!outstanding.count(r.id),"duplicate live memory ID");
    ck((r.address&15)==0,"unaligned native memory request");
    const Job& j=job[s];ck(r.write==j.write&&r.address>=j.address&&r.address<j.address+uint64_t(j.words)*16,"RTL descriptor address/direction mismatch");
    ++stats.requests;++stats.per_requests[s];outstanding[r.id]=r;
    auto& bank=m.bank[(r.address/64)%4];int64_t row=int64_t(r.address/1024);
    uint64_t command=std::max(mems,bank.free);r.due=command+c.latency+(bank.row==row?0:6);bank.free=command+2;bank.row=row;
    m.q.push_back(r);stats.maxqueue=std::max(stats.maxqueue,uint64_t(m.q.size()+size_t(m.held.has_value())));
   }
   bool refresh=(mems%512)<16;
   if(!m.held&&!refresh&&mems>=m.busfree&&rng()%5!=0){
    std::vector<size_t> candidates;for(size_t i=0;i<m.q.size();++i)if(m.q[i].due<=mems)candidates.push_back(i);
    if(!candidates.empty()){
     size_t at=candidates[rng()%candidates.size()];auto r=m.q[at];
     if(m.write!=r.write){m.write=r.write;m.busfree=mems+4;}
     else{
      m.q.erase(m.q.begin()+at);int s=(r.id>>3)&15;
      if((c.error==1&&!r.write&&!read_error)||(c.error==2&&r.write&&!write_error)){
       if(s==active.front()){r.status=1;if(r.write)write_error=true;else read_error=true;}}
      if(!r.write){auto found=memory.find(r.address);if(found==memory.end()){r.status=2;r.data=0;}else r.data=found->second;}
      if(c.corrupt&&!r.write&&!injected){r.data^=1;injected=true;}
      m.held=r;
     }
    }
   }
   if(m.held){auto r=*m.held;
    if(c.fault==1&&!injected){r.id^=0x8000;injected=true;m.held=r;}
    put(d->response_data[ch].data(),r.data);d->response_data[ch][4]=uint32_t(r.id)|(r.status<<16);
    d->response_valid|=1u<<ch;d->eval();
    if(d->response_ready&(1u<<ch)){
     if(c.fault==1&&r.id!=m.held->id)ck(false,"fault injection bookkeeping");
     uint16_t original=r.id;if(c.fault==1&&injected&&!outstanding.count(original))original^=0x8000;
     // A duplicate is deliberately outside the normal controller response contract.
     bool duplicate=outstanding.count(original)==0;
     if(!duplicate){ck(outstanding.erase(original)==1,"unknown memory completion");
      if(r.write&&r.status==0)memory[r.address]=r.data;
      if(r.write&&r.status==0)++stats.per_words[(original>>3)&15];}
     else ck(c.fault==2,"unexpected duplicate model response");
     if(c.fault==2&&!injected){Request repeat=r;repeat.due=mems+10;m.q.push_back(repeat);injected=true;}
     m.held.reset();
    }else ++stats.response_stalls;
   }
  }
 }
 void check_core_before(){
  if(!coreedge())return;
  for(int s=0;s<16;++s){
   ck(d->live_count[s]<=c.credits,"RTL exceeded configured in-flight credit");stats.maxlive=std::max(stats.maxlive,uint64_t(d->live_count[s]));
   if(sheld[s])ck((d->observed_request&(1u<<s))&&get(d->observed_data[s].data())==sdata[s]&&
     d->observed_address[s]==saddr[s]&&int((d->observed_write>>s)&1)==swrite[s],"S request changed under stall");
   sheld[s]=(d->observed_request&(1u<<s))&&!(d->observed_ready&(1u<<s));
   if(sheld[s]){sdata[s]=get(d->observed_data[s].data());saddr[s]=d->observed_address[s];swrite[s]=(d->observed_write>>s)&1;}
   if(d->s_accept&(1u<<s)){
    const auto& j=job[s];int at=d->observed_address[s];ck(at>=j.local&&at<j.local+j.words,"S local address escaped descriptor");
    if(!j.write){uint64_t address=j.address+uint64_t(at-j.local)*16;
     ck(memory.count(address)&&get(d->observed_data[s].data())==memory.at(address),"S write payload differs from independent external image");}}
   if(d->s_ack&(1u<<s)){++stats.per_acks[s];++stats.acks;
    if(!job[s].write&&s!=active.front()&&c.stall&&now-stage_start<uint64_t(c.stall)*10)++stats.isolated;}
   uint64_t cp=uint64_t(d->complete_tag[s])|(uint64_t(d->complete_status[s])<<16)|(uint64_t(d->completed_words[s])<<18);
   if(cheld[s])ck((d->complete_valid&(1u<<s))&&cp==cpacket[s],"completion changed under backpressure");
   cheld[s]=(d->complete_valid&(1u<<s))&&!(d->complete_ready&(1u<<s));cpacket[s]=cp;if(cheld[s])++stats.held;
  }
 }
 Result execute(std::array<Job,16> jobs,bool expect_protocol=false){
  job=jobs;stats=Result{};bypass.fill(0);stage_start=now;transfer=true;
  uint32_t pending=0,finished=0,mask=0;for(int s:active)pending|=1u<<s;mask=pending;
  while(finished!=mask){
   ck(now-stage_start<5000000,"RTL DMA failed to drain");
   d->desc_valid=pending;d->desc_write=0;d->complete_ready=0;
   for(int s:active){const Job& j=job[s];d->desc_address[s]=j.address;d->desc_local[s]=j.local;d->desc_words[s]=j.words;d->desc_tag[s]=j.tag;
    if(j.write)d->desc_write|=1u<<s;
    if(now-stage_start>=uint64_t(c.cplhold)*10&&rng()%4!=0)d->complete_ready|=1u<<s;}
   d->hold_s=(c.stall&&now-stage_start<uint64_t(c.stall)*10)?(1u<<active.front()):0;
   d->eval();memory_event();d->eval();
   bool edge=coreedge();uint32_t elig=d->eligible_debug;
   if(edge){check_core_before();pending&=~uint32_t(d->desc_ready);
    for(int s:active)if((d->complete_valid&d->complete_ready)&(1u<<s)){
     ck(!(finished&(1u<<s)),"duplicate task completion");ck(d->complete_tag[s]==job[s].tag,"wrong descriptor completion tag");
     bool error=(s==active.front())&&((c.error==1&&!job[s].write)||(c.error==2&&job[s].write));
     ck(d->complete_status[s]==(error?3:0),"wrong DMA completion status");
     if(error)++failed_completions;
     if(!error){ck(d->completed_words[s]==job[s].words,"successful completion omitted words");
      ck((job[s].write?stats.per_words[s]:stats.per_acks[s])==uint64_t(job[s].words),"completion preceded actual write acknowledgement");}
     finished|=1u<<s;++stats.completions;
    }}
   step();
   if(edge){for(int s=0;s<16;++s)if(!(elig&(1u<<s)))bypass[s]=0;
    for(int ch=0;ch<c.channels;++ch)if(d->grant_valid&(1u<<ch)){
     int selected=d->grant_s[ch];ck(elig&(1u<<selected),"arbiter selected ineligible source");
     for(int s:active)if(route(s)==ch&&(elig&(1u<<s))){if(s==selected)bypass[s]=0;else ++bypass[s];
      stats.maxbypass=std::max(stats.maxbypass,uint64_t(bypass[s]));ck(bypass[s]<16,"two-level arbiter starved eligible source");}}}
   if(d->protocol_error){ck(expect_protocol,"unexpected RTL protocol error");stats.ticks=now-stage_start;transfer=false;return stats;}
  }
  d->desc_valid=0;d->complete_ready=0;d->hold_s=0;transfer=false;stats.ticks=now-stage_start;
  ck(!expect_protocol,"injected bad response was accepted without protocol error");
  ck(!d->busy,"completion while a descriptor remained active");
  for(int s:active)ck(d->live_count[s]==0,"leaked RTL transaction slot");
  ck(outstanding.empty(),"model in-flight request leak");
  for(const auto& ch:channel)ck(ch.q.empty()&&!ch.held,"model response queue not drained");
  for(int s:active){bool error=(s==active.front())&&((c.error==1&&!job[s].write)||(c.error==2&&job[s].write));
   if(!error){ck(stats.per_requests[s]==uint64_t(job[s].words),"RTL did not issue each descriptor word exactly once");stats.bytes+=uint64_t(job[s].words)*16;}}
  return stats;
 }
 std::array<Job,16> jobs(bool write,int words){std::array<Job,16> j{};
  for(int s:active){j[s]={write,write?destination(s):source(s),0,words,uint16_t(100+s+(write?32:0))};}
  return j;}
 U128 command(int op,int index,uint64_t value){
  while(!coreedge()){step();}
  ck(d->cmd_ready,"M not ready");d->cmd_op=op;d->cmd_index=index;d->cmd_data=value;d->cmd_valid=1;d->rsp_ready=0;
  corestep();d->cmd_valid=0;unsigned n=0;while(!d->rsp_valid){ck(++n<2000,"M response timeout");corestep();}
  ck(!d->rsp_error&&!d->rsp_saturated,"M error");U128 x=get(d->rsp_data);
  d->rsp_ready=1;corestep();d->rsp_ready=0;return x;
 }
 void matrix_check(){
  for(int s:active){d->select_s=s;command(6,0,0);command(4,0,1);
   while(!coreedge()){step();}
   ck(d->load_ready,"feeder not ready");d->load_valid=1;corestep();d->load_valid=0;
   unsigned n=0;while(!d->done_valid){ck(++n<2000,"feeder timeout");d->a_allow=rng()%4!=0;d->b_allow=rng()%3!=0;corestep();}
   ck(!d->done_error,"feeder error");d->a_allow=d->b_allow=1;d->done_take=1;corestep();d->done_take=0;
   command(10,0,4u|(8u<<4)|(8u<<8)|(4u<<12)|(8u<<15));
   for(int r=0;r<8;++r)for(int p=0;p<4;++p){U128 result=command(3,r*8+p,0);
    for(int j=0;j<2;++j){int64_t reference=0;for(int k=0;k<32;++k)reference+=int64_t(av(s,r,k))*bv(s,p*2+j,k);
     ck(int64_t(result>>(64*j))==reference,"independent M matrix result mismatch");++matrix_values;}}
   ++matrices;
  }
 }
 void invalid_descriptors(){
  d->complete_ready=0;d->desc_write=0;int s=active.front();
  const std::array<Job,4> bad={Job{false,source(s),0,0,701},Job{false,source(s),1020,8,702},
   Job{false,source(s)+1,0,1,703},Job{false,(1ULL<<40)-16,0,2,704}};
  for(auto j:bad){while(!coreedge())step();ck(d->desc_ready&(1u<<s),"bad-descriptor receiver not ready");
   d->desc_address[s]=j.address;d->desc_local[s]=j.local;d->desc_words[s]=j.words;d->desc_tag[s]=j.tag;d->desc_valid=1u<<s;
   corestep();d->desc_valid=0;ck((d->complete_valid&(1u<<s))&&d->complete_status[s]==2&&d->complete_tag[s]==j.tag,"invalid descriptor not rejected in RTL");
   for(int k=0;k<4;++k){corestep();ck(d->complete_valid&(1u<<s),"invalid completion not held");ck(!d->mem_valid,"invalid descriptor emitted memory traffic");}
   d->complete_ready=1u<<s;corestep();d->complete_ready=0;}
  for(int kind=0;kind<2;++kind){
   d->credit_limit=kind==0?0:c.credits;d->channel_count=kind==1?3:c.channels;
   d->desc_address[s]=source(s);d->desc_local[s]=0;d->desc_words[s]=1;d->desc_tag[s]=uint16_t(710+kind);
   d->desc_valid=1u<<s;corestep();d->desc_valid=0;
   ck((d->complete_valid&(1u<<s))&&d->complete_status[s]==2&&!d->mem_valid,"bad credit/channel configuration not rejected in RTL");
   d->complete_ready=1u<<s;corestep();d->complete_ready=0;
  }
  d->credit_limit=c.credits;d->channel_count=c.channels;
 }
 void boundary_check(){
  auto saved=active;active={saved.front()};int s=active.front();uint64_t top=(1ULL<<40)-16;
  memory[top]=dataword(s,1023);std::array<Job,16> desc{};desc[s]={false,top,1023,1,800};
  execute(desc);desc[s]={true,top-16,1023,1,801};execute(desc);
  ck(memory[top-16]==dataword(s,1023),"40bit external/16KiB local upper boundary mismatch");
  boundary_transfers+=2;active=saved;
 }
};
static void printstats(const Result& r){std::cout<<"{\"ticks\":"<<r.ticks<<",\"bytes\":"<<r.bytes<<",\"requests\":"<<r.requests
 <<",\"gbps\":"<<(double(r.bytes)*3/r.ticks)<<",\"completions\":"<<r.completions<<",\"s_acks\":"<<r.acks
 <<",\"max_live\":"<<r.maxlive<<",\"max_queue\":"<<r.maxqueue<<",\"request_stalls\":"<<r.request_stalls
 <<",\"response_stalls\":"<<r.response_stalls<<",\"max_bypass\":"<<r.maxbypass<<",\"held_completion_cycles\":"<<r.held
 <<",\"other_s_acks_during_hold\":"<<r.isolated<<'}';}
int main(int argc,char** argv){
 Verilated::commandArgs(argc,argv);Config c;
 try{
  for(int i=1;i<argc;++i){std::string a=argv[i];auto p=a.find('=');if(p==std::string::npos)continue;std::string k=a.substr(0,p);int v=std::stoi(a.substr(p+1));
   if(k=="--groups")c.groups=v;else if(k=="--per")c.per=v;else if(k=="--channels")c.channels=v;else if(k=="--credits")c.credits=v;
   else if(k=="--queue")c.queue=v;else if(k=="--words")c.words=v;else if(k=="--seed")c.seed=v;else if(k=="--period")c.period=v;
   else if(k=="--phase")c.phase=v;else if(k=="--latency")c.latency=v;else if(k=="--stall")c.stall=v;else if(k=="--cplhold")c.cplhold=v;
   else if(k=="--error")c.error=v;else if(k=="--fault")c.fault=v;else if(k=="--pause")c.pause=v;else if(k=="--mixed")c.mixed=v;
   else if(k=="--reset")c.reset=v;else if(k=="--corrupt")c.corrupt=v;else if(k=="--boundary")c.boundary=v;}
  ck(c.groups>0&&c.groups<=4&&c.per>0&&c.per<=4,"invalid active configuration");
  ck((c.channels==1||c.channels==2||c.channels==4)&&c.credits>0&&c.credits<=8&&c.queue>0,"invalid capacity configuration");
  ck(c.words>=80&&c.words<=1024&&c.period>=2&&c.phase>=0&&c.phase<c.period,"invalid extent or clock");
  Simulation sim(c);bool recovered=false;
  if(c.fault){sim.execute(sim.jobs(false,c.words),true);ck(sim.d->protocol_error,"protocol error not latched");sim.reset_all();sim.c.fault=0;recovered=true;}
  Result load=sim.execute(sim.jobs(false,c.words));
  if(c.error!=1)sim.matrix_check();
  if(c.reset){sim.reset_all();sim.c.error=0;load=sim.execute(sim.jobs(false,c.words));}
  if(c.error==1){sim.c.error=0;sim.read_error=false;load=sim.execute(sim.jobs(false,c.words));sim.matrix_check();}
  auto stores=sim.jobs(true,c.words);
  if(c.mixed)for(size_t i=0;i<sim.active.size();i+=2){int s=sim.active[i];stores[s]=sim.jobs(false,c.words)[s];}
  Result store=sim.execute(stores);
  for(int s:sim.active)if(stores[s].write&&!(c.error==2&&s==sim.active.front()))
   for(int a=0;a<c.words;++a)ck(sim.memory[destination(s)+uint64_t(a)*16]==dataword(s,a),"STORE output differs from independent image");
  sim.invalid_descriptors();
  if(c.boundary)sim.boundary_check();
  if(c.stall)ck(load.isolated>0,"held S blocked all peers");
  if(c.pause)ck(load.response_stalls>0,"core-pause case did not fill response CDC FIFO");
  std::cout<<"{\"pass\":true,\"checks\":"<<checks<<",\"groups\":"<<c.groups<<",\"per_group\":"<<c.per
   <<",\"active_s\":"<<sim.active.size()<<",\"channels\":"<<c.channels<<",\"credits\":"<<c.credits<<",\"queue\":"<<c.queue
   <<",\"words\":"<<c.words<<",\"period\":"<<c.period<<",\"phase\":"<<c.phase<<",\"seed\":"<<c.seed
   <<",\"error\":"<<c.error<<",\"fault\":"<<c.fault<<",\"protocol_recovered\":"<<(recovered?"true":"false")
   <<",\"mixed\":"<<(c.mixed?"true":"false")<<",\"matrices\":"<<sim.matrices<<",\"matrix_values\":"<<sim.matrix_values
   <<",\"invalid_descriptors\":6,\"failed_completions\":"<<sim.failed_completions<<",\"boundary_transfers\":"<<sim.boundary_transfers
   <<",\"load\":";printstats(load);std::cout<<",\"store\":";printstats(store);std::cout<<"}\n";
 }catch(const std::exception& e){std::cerr<<"FAIL: "<<e.what()<<" checks="<<checks<<'\n';return 1;}
}
