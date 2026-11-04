#include "Vhbm_s_pool.h"
#include "verilated.h"
#include <algorithm>
#include <array>
#include <cstdint>
#include <deque>
#include <iostream>
#include <map>
#include <memory>
#include <random>
#include <stdexcept>
#include <string>
#include <vector>

// Time unit = 1/3 ns: exact 300 MHz core and 500/600/300/200 MHz user clocks.
// HBM bank timing is an explicit architecture hypothesis, not JEDEC compliance.
using U128=__uint128_t;
static uint64_t checks=0;
static void ck(bool v,const std::string& s){++checks;if(!v)throw std::runtime_error(s);}
static U128 word(const WData* p){U128 x=0;for(int i=3;i>=0;--i)x=(x<<32)|p[i];return x;}
static void put(WData* p,U128 x){for(int i=0;i<4;++i){p[i]=uint32_t(x);x>>=32;}}
static int avalue(int s,int r,int k){return ((s*13+r*7+k*3)%23)-11;}
static int bvalue(int s,int n,int k){return ((s*11+n*5+k*7)%19)-9;}
static U128 expected(int s,int address){
 U128 x=0;
 if(address<32){int t=address/8,r=address%8;
  for(int k=0;k<8;++k)x|=U128(uint8_t(avalue(s,r,t*8+k)))<<(k*8);
 }else if(address>=64&&address<80){int t=(address-64)/4,w=(address-64)%4;
  for(int j=0;j<16;++j){int at=w*16+j;x|=U128(uint8_t(bvalue(s,at/8,t*8+at%8)))<<(j*8);}
 }else{
  for(int j=0;j<4;++j)x|=U128(uint32_t((s+1)*0x1020304u)^uint32_t(address*65537u+j*0x12345u))<<(32*j);
 }return x;
}
struct Config{
 int active=4,groups=2,channels=2,credits=16,queue=64,burst=4,bulk=256;
 int mem_period=6,phase=1,seed=181,stall=0,width=256,latency=20,refresh=512,refresh_pause=16;
 bool corrupt=false,coordinated_reset=false;
};
struct Sim{
 Config c;std::unique_ptr<Vhbm_s_pool> d;std::mt19937 rng;
 uint64_t now=0,core_cycles=0,mem_cycles=0,af=0,bf=0;
 explicit Sim(Config q):c(q),d(new Vhbm_s_pool),rng(q.seed){
  d->core_clk=0;d->mem_clk=0;d->reset=1;d->in_valid=0;d->out_ready=0;d->hold_core=0;
  d->select_s=0;d->load_valid=0;d->done_take=0;d->a_allow=1;d->b_allow=1;
  d->cmd_valid=0;d->rsp_ready=0;d->cmd_op=0;d->cmd_index=0;d->cmd_data=0;
  d->eval();for(int i=0;i<200;++i)step();d->reset=0;d->eval();
 }
 bool iscore()const{return now%10==0;}
 bool ismem()const{return now%uint64_t(c.mem_period)==uint64_t(c.phase);}
 void step(){
  d->core_clk=0;d->mem_clk=0;d->eval();
  bool a=iscore(),b=ismem();if(a){af+=__builtin_popcount(d->a_fire);bf+=__builtin_popcount(d->b_fire);}
  d->core_clk=a;d->mem_clk=b;d->eval();if(a)++core_cycles;if(b)++mem_cycles;
  d->core_clk=0;d->mem_clk=0;d->eval();++now;
 }
 void corestep(){while(!iscore())step();step();}
 void reset(){d->reset=1;d->in_valid=0;d->out_ready=0;d->hold_core=0;
  for(int i=0;i<200;++i)step();d->reset=0;d->eval();
  ck(!d->out_valid,"reset did not flush response queues");}
 U128 command(int op,int index,uint64_t data){
  d->cmd_valid=0;d->rsp_ready=0;while(!iscore())step();d->eval();ck(d->cmd_ready,"M not ready");
  d->cmd_valid=1;d->cmd_op=op;d->cmd_index=index;d->cmd_data=data;corestep();d->cmd_valid=0;d->eval();
  unsigned n=0;while(!d->rsp_valid){ck(++n<2000,"M response timeout");corestep();}
  ck(!d->rsp_error&&!d->rsp_saturated,"M arithmetic/descriptor error");U128 value=word(d->rsp_data);
  for(int i=0;i<3;++i){corestep();ck(d->rsp_valid&&word(d->rsp_data)==value,"M stalled response changed");}
  d->rsp_ready=1;corestep();d->rsp_ready=0;return value;
 }
 uint64_t matrix(int s){
  uint64_t start=core_cycles,aa=af,bb=bf;d->select_s=s;command(6,0,0);command(4,0,1);
  while(!iscore())step();ck(d->load_ready,"S feeder not ready");d->load_valid=1;corestep();d->load_valid=0;
  unsigned n=0;while(!d->done_valid){ck(++n<2000,"S feeder timeout");
   d->a_allow=(rng()%4)!=0;d->b_allow=(rng()%3)!=0;corestep();}
  ck(!d->done_error,"S feeder rejected staged data");d->a_allow=1;d->b_allow=1;
  ck(af-aa==32&&bf-bb==4,"S feeder A/B packet count");
  d->done_take=1;corestep();d->done_take=0;
  command(10,0,4u|(8u<<4)|(8u<<8)|(4u<<12)|(8u<<15));
  for(int r=0;r<8;++r)for(int p=0;p<4;++p){U128 x=command(3,r*8+p,0);
   for(int j=0;j<2;++j){int ncol=p*2+j;int64_t reference=0;
    for(int k=0;k<32;++k)reference+=int64_t(avalue(s,r,k))*bvalue(s,ncol,k);
    ck(int64_t(x>>(j*64))==reference,"independent S->feeder->M GEMM mismatch");}}
  return core_cycles-start;
 }
};
struct Transaction{int s,tag,address;bool load;U128 data;uint64_t due,issued;};
struct Bank{int row=-1;uint64_t free=0;};
struct Channel{std::deque<Transaction> pending;std::array<Bank,4> banks;
 int rrgroup=0;bool lastwrite=false;uint64_t busfree=0,beats=0,rowhits=0,rowmisses=0,refreshcycles=0;};
struct Stats{
 uint64_t ticks=0,issued=0,retired=0,maxwait=0,maxq=0,fullstall=0,eligible_skip=0,refreshcycles=0;
 uint64_t other_before_release=0,cycles=0;std::vector<uint64_t> bytes,latencies,requests,maxcredit;
 std::vector<uint64_t> channelbeats;std::vector<unsigned> maxgap;
};
struct Fabric{
 Sim& sim;Config c;std::vector<Channel> channel;std::vector<int> addresses,next,credit,rrlocal,group_tokens;
 std::vector<std::map<int,Transaction>> live;std::vector<std::vector<U128>> memory,stored;
 std::vector<unsigned> gap;Stats stats;uint64_t start;bool load;
 Fabric(Sim& s,bool loading):sim(s),c(s.c),channel(c.channels),next(c.active),credit(c.active),rrlocal(c.groups),
  group_tokens(c.groups,2),live(c.active),memory(c.active,std::vector<U128>(1024)),
  stored(c.active,std::vector<U128>(1024)),gap(c.active),start(s.now),load(loading){
  for(int a=0;a<32;++a)addresses.push_back(a);for(int a=64;a<80;++a)addresses.push_back(a);
  for(int a=128;a<128+c.bulk;++a)addresses.push_back(a);
  for(int i=0;i<c.active;++i)for(int a:addresses)memory[i][a]=expected(i,a);
  stats.bytes.resize(c.active);stats.requests.resize(c.active);stats.maxcredit.resize(c.active);stats.maxgap.resize(c.active);
 }
 int group(int s)const{return s/(c.active/c.groups);}
 int mapped(int s)const{return group(s)%c.channels;}
 bool remaining(int s)const{return next[s]<int(addresses.size());}
 bool eligible(int s)const{return remaining(s)&&credit[s]<c.credits;}
 void reserve(const Transaction& t){ck(!live[t.s].count(t.tag),"duplicate live transaction tag");
  live[t.s][t.tag]=t;++credit[t.s];++stats.issued;++stats.requests[t.s];
  stats.maxcredit[t.s]=std::max(stats.maxcredit[t.s],uint64_t(credit[t.s]));
  ck(credit[t.s]<=c.credits,"credit overflow");}
 void retire(Transaction t){
  ck(live[t.s].erase(t.tag)==1,"unknown/duplicate completion");ck(credit[t.s]>0,"credit underflow");
  --credit[t.s];++stats.retired;stats.bytes[t.s]+=16;uint64_t latency=sim.now-t.issued;
  stats.latencies.push_back(latency);stats.maxwait=std::max(stats.maxwait,latency);
  if(c.stall&&t.s!=0&&sim.now-start<uint64_t(c.stall)*10)++stats.other_before_release;
 }
 Transaction make(int s){int tag=next[s]++;int a=addresses[tag];return {s,tag,a,load,0,0,sim.now};}
 void schedule(Transaction t){
  auto& ch=channel[mapped(t.s)];ck(int(ch.pending.size())<c.queue,"HBM queue overflow");
  Bank& bank=ch.banks[(t.address/4)%4];int row=t.address/64;
  bool hit=bank.row==row;hit?++ch.rowhits:++ch.rowmisses;
  uint64_t tcycle=sim.mem_cycles;uint64_t command_at=std::max(tcycle,bank.free);
  bank.free=command_at+2;bank.row=row;
  t.due=command_at+c.latency+(hit?0:6);ch.pending.push_back(t);
  stats.maxq=std::max(stats.maxq,uint64_t(ch.pending.size()));
 }
 int choose(int ch){
  int per=c.active/c.groups;auto& cc=channel[ch];
  std::vector<int> candidates;
  for(int k=0;k<c.groups;++k){int g=(cc.rrgroup+k)%c.groups;if(g%c.channels!=ch)continue;
   for(int j=0;j<per;++j){int s=g*per+(rrlocal[g]+j)%per;
    if(eligible(s)){candidates.push_back(s);break;}else if(remaining(s))++stats.eligible_skip;}}
  if(candidates.empty())return -1;int selected=candidates.front();
  for(int s=0;s<c.active;++s)if(mapped(s)==ch){
   if(s==selected||!eligible(s)){stats.maxgap[s]=std::max(stats.maxgap[s],gap[s]);gap[s]=0;}
   else{++gap[s];stats.maxgap[s]=std::max(stats.maxgap[s],gap[s]);}}
  int g=group(selected);cc.rrgroup=(g+1)%c.groups;rrlocal[g]=(selected%per+1)%per;return selected;
 }
 bool refresh(Channel& ch){bool r=c.refresh>0&&int(sim.mem_cycles%c.refresh)<c.refresh_pause;
  if(r)++ch.refreshcycles;return r;}
 void drive_packet(int s,const Transaction& t,U128 value){
  ck(!(sim.d->in_valid&(1u<<s)),"two packets targeted one physical FIFO input");
  put(sim.d->in_data[s].data(),value);sim.d->in_data[s][4]=uint32_t(t.address)|(uint32_t(t.tag)<<10)|(uint32_t(t.load)<<26);
  sim.d->in_valid|=1u<<s;
 }
 void event(){
  sim.d->in_valid=0;sim.d->out_ready=0;
  sim.d->hold_core=(c.stall&&sim.now-start<uint64_t(c.stall)*10)?1:0;
  if(sim.iscore())for(auto& x:group_tokens)x=std::min(2,x+1);
  sim.d->eval();
  if(!sim.ismem())return;
  // Check a held response before choosing ready; payload and tag must be stable.
  for(int s=0;s<c.active;++s)if(sim.d->out_valid&(1u<<s)){
   auto* p=sim.d->out_data[s].data();int a=p[4]&1023,tag=(p[4]>>10)&65535;bool wr=(p[4]>>26)&1;
   ck(live[s].count(tag)==1,"response routed to wrong S/tag");auto t=live[s].at(tag);
   ck(a==t.address&&wr==load,"response metadata mismatch");
   ck(word(p)==expected(s,a),load?"S write ACK payload mismatch":"S readback mismatch");
   bool space=load||int(channel[mapped(s)].pending.size())<c.queue;
   if(space&&sim.rng()%4!=0){sim.d->out_ready|=1u<<s;
    if(load)retire(t);else{t.data=word(p);schedule(t);}}
  }
  // A read delivery and a write consume the same per-channel data-bus slots.
  for(int chno=0;chno<c.channels;++chno){auto& ch=channel[chno];if(refresh(ch))continue;
   for(int slot=0;slot<c.width/128;++slot){if(sim.mem_cycles<ch.busfree)break;
    auto it=std::find_if(ch.pending.begin(),ch.pending.end(),[&](const Transaction& t){
     return t.due<=sim.mem_cycles&&(!t.load||
      ((sim.d->in_ready&(1u<<t.s))&&!(sim.d->in_valid&(1u<<t.s))&&group_tokens[group(t.s)]>0));});
    if(it==ch.pending.end()){if(!ch.pending.empty())++stats.fullstall;break;}
    bool write=!it->load;if(write!=ch.lastwrite){ch.lastwrite=write;ch.busfree=sim.mem_cycles+4;break;}
    Transaction t=*it;ch.pending.erase(it);++ch.beats;
    if(t.load){U128 value=memory[t.s][t.address];if(c.corrupt&&t.s==0&&t.address==0)value^=1;
     drive_packet(t.s,t,value);--group_tokens[group(t.s)];}
    else{stored[t.s][t.address]=t.data;retire(t);}
   }
  }
  // Each grant is bounded to burst words. Credit is held until S ACK (LOAD)
  // or modeled HBM write completion (STORE), including all CDC/FIFO waiting.
  for(int ch=0;ch<c.channels;++ch){int s=choose(ch);if(s<0)continue;
   if(load){for(int j=0;j<c.burst&&eligible(s)&&int(channel[ch].pending.size())<c.queue;++j){
     Transaction t=make(s);reserve(t);schedule(t);}}
   else if((sim.d->in_ready&(1u<<s))&&!(sim.d->in_valid&(1u<<s))&&group_tokens[group(s)]>0){
    Transaction t=make(s);reserve(t);drive_packet(s,t,0);--group_tokens[group(s)];}
  }
  sim.d->eval();
 }
 Stats run(){
  uint64_t expected_count=uint64_t(c.active)*addresses.size();unsigned busyreset=0;
  while(stats.retired<expected_count){
   ck(sim.now-start<5000000,"transport failed to drain / timeout");event();sim.step();
   if(c.coordinated_reset&&!busyreset&&stats.issued>uint64_t(c.active)*8&&stats.retired<stats.issued){
    busyreset=1;sim.reset();
    // Coordinated reset flushes controller queues, software descriptors/credits,
    // and BOTH RTL FIFO domains. All addresses are subsequently overwritten.
    for(auto& ch:channel){ch.pending.clear();ch.banks={};ch.lastwrite=false;ch.busfree=0;}
    for(int s=0;s<c.active;++s){next[s]=0;credit[s]=0;live[s].clear();stats.bytes[s]=0;stats.requests[s]=0;}
    stats.issued=stats.retired=0;stats.latencies.clear();start=sim.now;
   }
  }
  sim.d->in_valid=0;sim.d->out_ready=0;sim.d->hold_core=0;sim.d->eval();
  stats.ticks=sim.now-start;stats.cycles=stats.ticks/10;
  ck(stats.issued==expected_count&&stats.retired==expected_count,"incomplete transactions");
  for(int s=0;s<c.active;++s){ck(credit[s]==0&&live[s].empty(),"leaked transaction/credit");
   ck(stats.bytes[s]==addresses.size()*16,"per-S byte count");
   if(!load)for(int a:addresses)ck(stored[s][a]==expected(s,a),"modeled HBM STORE result mismatch");}
  for(const auto& ch:channel){ck(ch.pending.empty(),"HBM queue not drained");
   stats.channelbeats.push_back(ch.beats);stats.refreshcycles+=ch.refreshcycles;}
  ck(!c.coordinated_reset||busyreset,"coordinated reset was not exercised");
  return stats;
 }
};
template<class T>static void arrayjson(const std::vector<T>& v){std::cout<<'[';for(size_t i=0;i<v.size();++i){if(i)std::cout<<',';std::cout<<v[i];}std::cout<<']';}
static void show(const Stats& s){
 auto lat=s.latencies;std::sort(lat.begin(),lat.end());
 std::cout<<"{\"ticks\":"<<s.ticks<<",\"bytes\":"<<s.retired*16<<",\"issued\":"<<s.issued<<",\"retired\":"<<s.retired
  <<",\"gbps\":"<<(double(s.retired*16)*3.0/s.ticks)<<",\"max_latency_ticks\":"<<s.maxwait
  <<",\"p50_latency_ticks\":"<<lat[lat.size()/2]<<",\"p99_latency_ticks\":"<<lat[(lat.size()-1)*99/100]
  <<",\"max_queue\":"<<s.maxq<<",\"blocked_or_wait_cycles\":"<<s.fullstall<<",\"credit_skip\":"<<s.eligible_skip
  <<",\"refresh_channel_cycles\":"<<s.refreshcycles<<",\"other_completions_during_s0_hold\":"<<s.other_before_release
  <<",\"per_s_bytes\":";arrayjson(s.bytes);std::cout<<",\"per_s_max_credit\":";arrayjson(s.maxcredit);
 std::cout<<",\"per_s_max_arbitration_gap\":";arrayjson(s.maxgap);std::cout<<",\"channel_beats\":";arrayjson(s.channelbeats);std::cout<<'}';
}
int main(int argc,char** argv){
 Verilated::commandArgs(argc,argv);Config c;
 try{
  for(int i=1;i<argc;++i){std::string a=argv[i];auto eq=a.find('=');if(eq==std::string::npos)continue;
   std::string k=a.substr(0,eq);int v=std::stoi(a.substr(eq+1));
   if(k=="--active")c.active=v;else if(k=="--groups")c.groups=v;else if(k=="--channels")c.channels=v;
   else if(k=="--credits")c.credits=v;else if(k=="--queue")c.queue=v;else if(k=="--burst")c.burst=v;
   else if(k=="--bulk")c.bulk=v;else if(k=="--period")c.mem_period=v;else if(k=="--phase")c.phase=v;
   else if(k=="--seed")c.seed=v;else if(k=="--stall")c.stall=v;else if(k=="--width")c.width=v;
   else if(k=="--latency")c.latency=v;else if(k=="--refresh")c.refresh=v;
   else if(k=="--corrupt")c.corrupt=v;else if(k=="--reset")c.coordinated_reset=v;
  }
  ck(c.active>0&&c.active<=16&&c.groups>0&&c.active%c.groups==0,"invalid S/group destination configuration");
  ck(c.channels>0&&c.channels<=16&&c.credits>0&&c.credits<=256&&c.queue>0&&c.queue<=512,"invalid finite capacity");
  ck(c.burst>0&&c.burst<=16&&c.bulk>=0&&c.bulk<=896,"invalid burst/address extent");
  ck(c.mem_period>=2&&c.phase>=0&&c.phase<c.mem_period&&c.latency>=0,"invalid timing configuration");
  ck(c.width==128||c.width==256||c.width==512,"invalid channel width");
  Sim sim(c);Fabric incoming(sim,true);Stats in=incoming.run();uint64_t matrixcycles=0;
  for(int s=0;s<c.active;++s)matrixcycles+=sim.matrix(s);
  Fabric outgoing(sim,false);Stats out=outgoing.run();
  if(c.stall)ck(in.other_before_release>0,"blocked S0 stalled all other destinations");
  std::cout<<"{\"pass\":true,\"checks\":"<<checks<<",\"active_s\":"<<c.active<<",\"groups\":"<<c.groups
   <<",\"channels\":"<<c.channels<<",\"credits\":"<<c.credits<<",\"queue\":"<<c.queue<<",\"burst\":"<<c.burst
   <<",\"bulk\":"<<c.bulk<<",\"mem_period_ticks\":"<<c.mem_period<<",\"phase_ticks\":"<<c.phase
   <<",\"channel_width\":"<<c.width<<",\"latency_mem_cycles\":"<<c.latency<<",\"seed\":"<<c.seed
   <<",\"stall_core_cycles\":"<<c.stall<<",\"coordinated_reset\":"<<(c.coordinated_reset?"true":"false")
   <<",\"matrices\":"<<c.active<<",\"matrix_results\":"<<c.active*64<<",\"matrix_cycles\":"<<matrixcycles
   <<",\"core_cycles\":"<<sim.core_cycles<<",\"load\":";show(in);std::cout<<",\"store\":";show(out);std::cout<<"}\n";
 }catch(const std::exception& e){std::cerr<<"FAIL: "<<e.what()<<" checks="<<checks<<'\n';return 1;}
}
