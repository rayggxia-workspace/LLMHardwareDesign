#include "Vweight_test_top.h"
#include "verilated.h"
#include <algorithm>
#include <array>
#include <deque>
#include <fstream>
#include <iostream>
#include <memory>
#include <random>
#include <stdexcept>
#include <string>
#include <vector>

using A8=std::array<uint32_t,8>;
using W32=std::array<uint32_t,32>;
using D16=std::array<uint32_t,16>;
struct Record {
 bool head=false;int n=8,rid=0,bank=0,gen=0,read=0;bool ack=false,error=false;
 std::vector<D16> dma;std::array<A8,8> a,dot;std::array<W32,8> w;
 std::array<std::array<uint32_t,4>,8> scale;
 std::array<bool,18> issued{},returned{};
};
struct Expected {uint32_t tag;int n;A8 value;};
std::unique_ptr<Vweight_test_top> top;
#define t (*top)
std::deque<Expected> expected;
std::vector<Record*> live;
Record *reading=nullptr,*issuing=nullptr,*filling=nullptr;
bool issue_ok=true,fill_ok=true,force_w=false,force_raw=false;
bool fire_alloc=false,fire_issue=false,fire_fill=false,fire_start=false,fire_consumed=false,fire_cancel=false,fire_drain=false;
int cycle=0,faults=0,raw_outputs=0,w_beats=0,concurrent_fill_read=0,concurrent_issue_lc=0,credit=0,epoch=1;
bool w_held=false,raw_held=false;
std::vector<uint32_t> held_w,held_raw;
std::mt19937 rng;
void need(bool v,const std::string& m){if(!v)throw std::runtime_error(m+" cycle="+std::to_string(cycle));}
template<size_t N>std::array<uint32_t,N> hex(const std::string& s){
 std::array<uint32_t,N> v{};for(size_t n=0;n<N;++n){size_t end=s.size()>n*8?s.size()-n*8:0;size_t begin=end>8?end-8:0;if(end)v[n]=uint32_t(std::stoul(s.substr(begin,end-begin),nullptr,16));}return v;
}
template<class Port,size_t N>void set(Port& p,const std::array<uint32_t,N>& a){for(size_t n=0;n<N;++n)p[n]=a[n];}
template<class Port,size_t N>bool same(const Port& p,const std::array<uint32_t,N>& a){for(size_t n=0;n<N;++n)if(p[n]!=a[n])return false;return true;}
template<class Port>void key(Port& p,int rid){p[0]=uint32_t(rid);p[1]=uint32_t(epoch);p[2]=0x250;p[3]=1;}
#define IDENT(P,R) t.P##_bank=(R).bank;t.P##_generation=(R).gen;key(t.P##_key,(R).rid);t.P##_record=(R).rid
std::vector<uint32_t> snapshot_w(){std::vector<uint32_t> v;for(int i=0;i<32;++i)v.push_back(t.w_data[i]);for(int i=0;i<4;++i)v.push_back(t.w_scale[i]);v.push_back(t.w_raw_tag);v.push_back(t.w_offset);v.push_back(t.w_first);v.push_back(t.w_last);v.push_back(t.w_generation);return v;}
std::vector<uint32_t> snapshot_raw(){std::vector<uint32_t> v;for(int i=0;i<8;++i)v.push_back(t.raw_data[i]);v.push_back(t.raw_tag);v.push_back(t.raw_n);v.push_back(t.raw_error);return v;}
void tick(){
 t.clk=0;t.allow_w=!force_w&&cycle%7!=0;t.raw_out_ready=!force_raw&&cycle%13<9;t.eval();
 if(t.w_valid){need(reading!=nullptr,"unowned W");int beat=t.w_group_k==16?t.w_group_index:t.w_offset/16;need(beat>=0&&beat<8,"W beat");set(t.a_data,reading->a[size_t(beat)]);t.eval();}
 fire_alloc=t.alloc_valid&&t.alloc_ready;fire_issue=t.issue_valid&&t.issue_ready;fire_fill=t.fill_valid&&t.fill_ready;
 fire_start=t.start_valid&&t.start_ready;fire_consumed=t.consumed_valid&&t.consumed_ready;fire_cancel=t.cancel_valid&&t.cancel_ready;fire_drain=t.drain_valid&&t.drain_ready;
 if(!t.reset){
  if(w_held&&!fire_cancel)need(t.w_valid&&snapshot_w()==held_w,"W changed under backpressure");
  if(raw_held&&!t.raw_cancel_reset)need(t.raw_valid&&snapshot_raw()==held_raw,"raw changed under backpressure");
  w_held=t.w_valid&&!t.w_ready;held_w=snapshot_w();raw_held=t.raw_valid&&!t.raw_out_ready;held_raw=snapshot_raw();
  if(fire_issue&&issue_ok){need(issuing!=nullptr,"issue owner");issuing->issued[t.issue_beat]=true;++credit;
   if(fire_alloc||fire_start||fire_consumed||fire_cancel||fire_drain)++concurrent_issue_lc;}
  if(fire_fill&&fill_ok){need(filling!=nullptr,"return owner");filling->returned[t.fill_beat]=true;--credit;}
  if(t.fill_ack_valid&&t.fill_ack_ready){bool found=false;for(auto* r:live)if(r->rid==int(t.fill_ack_record)&&r->bank==int(t.fill_ack_bank)&&r->gen==int(t.fill_ack_generation)){
   need(std::all_of(r->returned.begin(),r->returned.begin()+long(r->dma.size()),[](bool v){return v;}),"early FILLACK");r->ack=true;r->error=t.fill_ack_error;found=true;}
   need(found,"unknown FILLACK");}
  if(t.fault_valid&&t.fault_ready)++faults;
  if(t.w_valid&&t.w_ready){auto& r=*reading;int beat=r.read;
   need(beat<8&&int(t.w_record)==r.rid&&int(t.w_generation)==r.gen,"W identity/order");
   need(same(t.w_data,r.w[size_t(beat)])&&same(t.w_scale,r.scale[size_t(beat)]),"checkpoint W/scale byte mismatch");
   need(int(t.w_n)==r.n&&int(t.w_first)==int(r.head||beat==0)&&int(t.w_last)==int(r.head||beat==7),"raw group boundary");
   need(t.w_raw_tag==uint32_t(r.rid*8+(r.head?beat:0)),"raw compact tag");
   ++r.read;++w_beats;if(fire_fill&&fill_ok){need(t.fill_bank!=t.w_bank,"same-bank fill/read");++concurrent_fill_read;}
  }
  if(t.raw_valid&&t.raw_out_ready){need(!expected.empty(),"unexpected raw output");auto e=expected.front();expected.pop_front();
   need(!t.raw_error&&t.raw_tag==e.tag&&int(t.raw_n)==e.n&&same(t.raw_data,e.value),"public checkpoint M dot mismatch");++raw_outputs;}
 }
 t.clk=1;t.eval();t.clk=0;t.eval();++cycle;
 if(!t.reset)need(int(t.outstanding)==credit&&credit>=0&&credit<=32,"inflight credit conservation");
}
template<class F>void wait_for(F f,const char* message){for(int n=0;n<20000;++n){if(f())return;tick();}throw std::runtime_error(message);}
void clear_requests(){t.alloc_valid=0;t.issue_valid=0;t.fill_valid=0;t.start_valid=0;t.consumed_valid=0;t.cancel_valid=0;t.drain_valid=0;issuing=nullptr;filling=nullptr;issue_ok=fill_ok=true;}
void allocation(Record& r){
 t.alloc_valid=1;key(t.alloc_key,r.rid);t.alloc_record=r.rid;t.alloc_head16=r.head;t.alloc_n=r.n;
 do{tick();if(fire_issue){t.issue_valid=0;issuing=nullptr;}}while(!fire_alloc);t.alloc_valid=0;
 wait_for([]{return t.alloc_ack_valid;},"allocation ACK timeout");need(!t.alloc_ack_error,"allocation rejected");
 r.bank=t.alloc_ack_bank;r.gen=t.alloc_ack_generation;live.push_back(&r);t.alloc_ack_ready=1;tick();t.alloc_ack_ready=0;
}
void fill_group(const std::vector<Record*>& rows,bool returns_only=false){
 auto complete=[&]{for(auto* r:rows)for(size_t j=0;j<r->dma.size();++j)if((!returns_only||r->issued[j])&&!r->returned[j])return false;return true;};
 for(int guard=0;!complete()&&guard<30000;++guard){
  if(!t.issue_valid&&!returns_only){std::vector<std::pair<Record*,int>> choices;for(auto* r:rows)for(size_t j=0;j<r->dma.size();++j)if(!r->issued[j])choices.push_back({r,int(j)});
   if(!choices.empty()){auto p=choices[rng()%choices.size()];issuing=p.first;IDENT(issue,*issuing);t.issue_beat=p.second;t.issue_valid=1;}}
  if(!t.fill_valid){std::vector<std::pair<Record*,int>> choices;for(auto* r:rows)for(size_t j=0;j<r->dma.size();++j)if(r->issued[j]&&!r->returned[j])choices.push_back({r,int(j)});
   if(!choices.empty()&&guard%4!=0){auto p=choices[rng()%choices.size()];filling=p.first;IDENT(fill,*filling);t.fill_beat=p.second;t.fill_last=p.second==int(filling->dma.size())-1;set(t.fill_data,filling->dma[size_t(p.second)]);t.fill_valid=1;}}
  tick();if(fire_issue){t.issue_valid=0;issuing=nullptr;}if(fire_fill){t.fill_valid=0;filling=nullptr;}
 }
 need(complete(),"DMA issue/return timeout");t.issue_valid=0;t.fill_valid=0;issuing=filling=nullptr;
}
void wait_ack(Record& r){t.fill_ack_ready=1;wait_for([&]{return r.ack;},"FILLACK timeout");need(!r.error,"valid payload rejected");}
void begin_read(Record& r){
 reading=&r;t.start_valid=1;IDENT(start,r);t.start_use=uint16_t(r.rid+17);t.start_raw_tag=uint32_t(r.rid*8);
 for(int g=0;g<(r.head?8:1);++g)expected.push_back({uint32_t(r.rid*8+g),r.n,r.dot[size_t(g)]});
 do{tick();if(fire_issue){t.issue_valid=0;issuing=nullptr;}}while(!fire_start);t.start_valid=0;
}
void release(Record& r){
 need(r.read==8,"early input release in harness");t.consumed_valid=1;IDENT(consumed,r);t.consumed_use=uint16_t(r.rid+17);
 do{tick();}while(!fire_consumed);t.consumed_valid=0;need((t.free_mask&(1<<r.bank))!=0,"input consumed did not free bank");
}
void fault_drain(int before){wait_for([&]{return faults>before;},"expected protocol rejection missing");}
void wrong_release(Record& r,bool wrong_gen){int before=faults;t.consumed_valid=1;IDENT(consumed,r);t.consumed_use=uint16_t(r.rid+17+(wrong_gen?0:1));if(wrong_gen)++t.consumed_generation;do{tick();}while(!fire_consumed);t.consumed_valid=0;fault_drain(before);}
void drain_cancelled(Record& r){t.drain_valid=1;IDENT(drain,r);do{tick();if(fire_issue){t.issue_valid=0;issuing=nullptr;}}while(!fire_drain);t.drain_valid=0;wait_for([]{return t.drain_done_valid;},"cancel drain completion missing");t.drain_done_ready=1;tick();}
Record clone(const Record& r,int rid){Record v=r;v.rid=rid;v.read=0;v.ack=v.error=false;v.issued.fill(false);v.returned.fill(false);return v;}
int main(int argc,char** argv){
 try{
  need(argc==4,"usage fixture seed initial_state");rng.seed(uint32_t(std::stoul(argv[2])));
  Verilated::randReset(std::stoi(argv[3]));Verilated::randSeed(int(std::stoul(argv[2])));
  top=std::make_unique<Vweight_test_top>();
  std::ifstream f(argv[1]);int count;f>>count;need(count==34,"fixture count");std::vector<Record> rows(size_t(count),Record{});
  for(auto& r:rows){int head;f>>head>>r.n>>r.rid;r.head=head;std::string s;
   for(int n=0;n<(r.head?18:17);++n){f>>s;r.dma.push_back(hex<16>(s));}
   for(auto& a:r.a){f>>s;a=hex<8>(s);}for(auto& w:r.w){f>>s;w=hex<32>(s);}for(auto& scale:r.scale){f>>s;scale=hex<4>(s);}
   for(int g=0;g<(r.head?8:1);++g){f>>s;r.dot[size_t(g)]=hex<8>(s);}}
  need(bool(f),"fixture parse");clear_requests();t.reset=1;t.alloc_ack_ready=0;t.fill_ack_ready=0;t.fault_ready=1;t.drain_done_ready=1;t.raw_cancel_reset=0;for(int j=0;j<4;++j)tick();t.reset=0;
  for(int i=0;i<4;++i){if(i>0){issuing=&rows[size_t(i-1)];IDENT(issue,*issuing);t.issue_beat=0;t.issue_valid=1;}allocation(rows[size_t(i)]);}
  // Reserve all32 in-flight slots before allowing a single return.
  while(credit<32){Record* candidate=nullptr;int beat=0;for(int i=0;i<4&&!candidate;++i)for(size_t b=0;b<rows[size_t(i)].dma.size()&&!candidate;++b)if(!rows[size_t(i)].issued[b]){candidate=&rows[size_t(i)];beat=int(b);}
   need(candidate!=nullptr,"no credit test candidate");issuing=candidate;IDENT(issue,*issuing);t.issue_beat=beat;t.issue_valid=1;do{tick();}while(!fire_issue);t.issue_valid=0;issuing=nullptr;}
  auto& blocked=rows[3];issuing=&blocked;IDENT(issue,blocked);t.issue_beat=1;t.issue_valid=1;for(int j=0;j<4;++j){tick();need(!fire_issue,"32-credit cap ignored");}t.issue_valid=0;issuing=nullptr;
  fill_group({&rows[0],&rows[1],&rows[2],&rows[3]});
  wait_for([]{return t.fill_ack_valid;},"backpressured FILLACK missing");auto saved=std::array<uint32_t,4>{t.fill_ack_record,t.fill_ack_generation,t.fill_ack_bank,uint32_t(t.fill_ack_error)};
  for(int j=0;j<5;++j){tick();need(saved==std::array<uint32_t,4>{t.fill_ack_record,t.fill_ack_generation,t.fill_ack_bank,uint32_t(t.fill_ack_error)},"FILLACK changed");}
  // All bytes present still does not authorize M before the true FILLACK.
  auto& early=rows[size_t(t.fill_ack_record-1)];int before_early=faults;
  t.start_valid=1;IDENT(start,early);t.start_use=0;t.start_raw_tag=0;
  do{tick();}while(!fire_start);t.start_valid=0;fault_drain(before_early);
  need(t.ready_mask==0,"unacknowledged fill exposed READY");
  for(int i=0;i<4;++i)wait_ack(rows[size_t(i)]);
  begin_read(rows[0]);
  for(int i=0;i<count;++i){auto& r=rows[size_t(i)];wait_for([&]{return r.read==8;},"native W read timeout");
   if(i==0){wrong_release(r,true);wrong_release(r,false);}
   release(r);
   if(i+4<count)allocation(rows[size_t(i+4)]);
   if(i+1<count){if(i+4<count){issuing=&rows[size_t(i+4)];IDENT(issue,*issuing);t.issue_beat=0;t.issue_valid=1;}begin_read(rows[size_t(i+1)]);}
   if(i+4<count){fill_group({&rows[size_t(i+4)]});wait_ack(rows[size_t(i+4)]);}
  }
  reading=nullptr;wait_for([]{return expected.empty();},"raw dot completion timeout");need(concurrent_fill_read>0,"no concurrent different-bank fill/read exercised");
  // Malformed scales/pad/inactive weights are complete record errors; an
  // inactive NaN scale is ignored and canonicalized at the output, not rejected.
  std::vector<Record> bad;bad.reserve(6);
  for(int i=0;i<6;++i){bad.push_back(clone(i==5?rows[24]:rows[0],1000+i));auto& r=bad.back();
   if(i==0)r.dma[16][0]&=0xffff0000U;
   if(i==1)r.dma[16][0]=(r.dma[16][0]&0xffff0000U)|0x7c00;
   if(i==2)r.dma[16][4]=1;
   if(i==3){r.n=1;for(int b=0;b<16;++b)for(int j=0;j<16;++j)if((b%2)*4+j/4>=1)r.dma[size_t(b)][size_t(j)]=0;r.dma[0][4]=1;}
   if(i==4)r.dma[16][0]=(r.dma[16][0]&0xffff0000U)|0xbc00;
   if(i==5)r.dma[17][12]=(r.dma[17][12]&0xffff0000U)|0x7e00;
   allocation(r);fill_group({&r});wait_for([&]{return r.ack;},"bad record ACK");need(r.error,"bad record accepted");need(t.free_mask&(1<<r.bank),"bad record retained bank");
  }
  auto inactive=clone(rows[28],1100);inactive.dma[16][3]=0x7c007c00;allocation(inactive);fill_group({&inactive});wait_ack(inactive);begin_read(inactive);wait_for([&]{return inactive.read==8;},"inactive scale read");release(inactive);reading=nullptr;wait_for([]{return expected.empty();},"inactive scale raw");
  // Cancel with real DMA in flight; DRAIN cannot manufacture its returns.
  auto cancelled=clone(rows[0],1200);allocation(cancelled);
  for(int beat=0;beat<4;++beat){issuing=&cancelled;IDENT(issue,cancelled);t.issue_beat=beat;t.issue_valid=1;do{tick();}while(!fire_issue);t.issue_valid=0;issuing=nullptr;}
  issuing=&cancelled;IDENT(issue,cancelled);t.issue_beat=4;t.issue_valid=1;
  t.cancel_valid=1;IDENT(cancel,cancelled);do{tick();need(!fire_issue,"same-bank cancel accepted new DMA");}while(!fire_cancel);t.cancel_valid=0;t.issue_valid=0;issuing=nullptr;
  int before=faults;t.drain_valid=1;IDENT(drain,cancelled);do{tick();}while(!fire_drain);t.drain_valid=0;fault_drain(before);need(!(t.free_mask&(1<<cancelled.bank)),"early cancel drain freed pending DMA");
  fill_group({&cancelled},true);
  auto cancel_peer=clone(rows[1],1201);allocation(cancel_peer);
  issuing=&cancel_peer;IDENT(issue,cancel_peer);t.issue_beat=0;t.issue_valid=1;
  drain_cancelled(cancelled);need(cancel_peer.issued[0],"unrelated MC issue blocked by drain");need(t.free_mask&(1<<cancelled.bank),"cancel did not free");
  fill_group({&cancel_peer});wait_ack(cancel_peer);begin_read(cancel_peer);wait_for([&]{return cancel_peer.read==8;},"cancel peer read");release(cancel_peer);reading=nullptr;wait_for([]{return expected.empty();},"cancel peer raw");
  before=faults;fill_ok=false;IDENT(fill,cancelled);t.fill_beat=0;t.fill_last=0;t.fill_valid=1;do{tick();}while(!fire_fill);t.fill_valid=0;fill_ok=true;fault_drain(before);
  // Last actual DMA return and cancellation in one cycle must not publish
  // a ready record or fabricate a FILLACK that could reauthorize the owner.
  auto final_cancel=clone(rows[0],1202);allocation(final_cancel);
  for(int beat=0;beat<17;++beat){issuing=&final_cancel;IDENT(issue,final_cancel);t.issue_beat=beat;t.issue_valid=1;do{tick();}while(!fire_issue);t.issue_valid=0;issuing=nullptr;}
  for(int beat=0;beat<16;++beat){filling=&final_cancel;IDENT(fill,final_cancel);t.fill_beat=beat;t.fill_last=0;set(t.fill_data,final_cancel.dma[size_t(beat)]);t.fill_valid=1;do{tick();}while(!fire_fill);t.fill_valid=0;filling=nullptr;}
  filling=&final_cancel;IDENT(fill,final_cancel);t.fill_beat=16;t.fill_last=1;set(t.fill_data,final_cancel.dma[16]);t.fill_valid=1;
  t.cancel_valid=1;IDENT(cancel,final_cancel);tick();need(fire_fill&&fire_cancel,"final return/cancel did not rendezvous");t.fill_valid=0;t.cancel_valid=0;filling=nullptr;
  for(int j=0;j<4;++j){tick();need(!(t.ready_mask&(1<<final_cancel.bank))&&!final_cancel.ack,"cancelled final return reauthorized record");}
  drain_cancelled(final_cancel);
  // A reused bank rejects an old generation/key even while a new fill lives.
  auto duplicate=clone(rows[0],1250);allocation(duplicate);
  // Full job/object identity is checked in addition to bank generation.
  before=faults;issue_ok=false;t.fault_ready=0;IDENT(issue,duplicate);t.issue_key[1]^=1;t.issue_beat=0;t.issue_valid=1;
  do{tick();}while(!fire_issue);t.issue_valid=0;
  need(t.fault_valid&&t.fault_key[1]==uint32_t(epoch^1),"wrong epoch was not reported");
  auto held_fault=std::array<uint32_t,4>{t.fault_record,t.fault_generation,t.fault_bank,t.fault_op};
  IDENT(issue,duplicate);t.issue_beat=0;t.issue_valid=1;
  for(int j=0;j<5;++j){tick();need(!fire_issue&&t.fault_valid&&held_fault==std::array<uint32_t,4>{t.fault_record,t.fault_generation,t.fault_bank,t.fault_op},"bounded fault slot overwritten");}
  t.issue_valid=0;t.fault_ready=1;fault_drain(before);issue_ok=true;
  issuing=&duplicate;IDENT(issue,duplicate);t.issue_beat=0;t.issue_valid=1;do{tick();}while(!fire_issue);t.issue_valid=0;issuing=nullptr;
  before=faults;issue_ok=false;IDENT(issue,duplicate);t.issue_beat=0;t.issue_valid=1;do{tick();}while(!fire_issue);t.issue_valid=0;issue_ok=true;fault_drain(before);
  filling=&duplicate;IDENT(fill,duplicate);t.fill_beat=0;t.fill_last=0;set(t.fill_data,duplicate.dma[0]);t.fill_valid=1;do{tick();}while(!fire_fill);t.fill_valid=0;filling=nullptr;
  before=faults;fill_ok=false;IDENT(fill,duplicate);t.fill_beat=0;t.fill_last=0;t.fill_valid=1;do{tick();}while(!fire_fill);t.fill_valid=0;fill_ok=true;fault_drain(before);
  before=faults;fill_ok=false;IDENT(fill,duplicate);--t.fill_generation;t.fill_beat=1;t.fill_valid=1;do{tick();}while(!fire_fill);t.fill_valid=0;fill_ok=true;fault_drain(before);
  fill_group({&duplicate});wait_ack(duplicate);begin_read(duplicate);wait_for([&]{return duplicate.read==8;},"duplicate rejection retry");release(duplicate);reading=nullptr;wait_for([]{return expected.empty();},"duplicate retry raw");
  // Partial raw group cancellation requires coordinated raw flush, then a
  // new tagged record. No atomic rollback is claimed by the weight banks.
  auto partial=clone(rows[0],1300);allocation(partial);fill_group({&partial});wait_ack(partial);begin_read(partial);
  wait_for([&]{return partial.read>=3;},"partial raw start");force_w=true;
  t.cancel_valid=1;IDENT(cancel,partial);do{tick();}while(!fire_cancel);t.cancel_valid=0;
  need(partial.read<8,"cancel too late");expected.clear();t.raw_cancel_reset=1;raw_held=false;w_held=false;tick();t.raw_cancel_reset=0;force_w=false;drain_cancelled(partial);reading=nullptr;
  auto retry=clone(rows[1],1301);allocation(retry);fill_group({&retry});wait_ack(retry);begin_read(retry);wait_for([&]{return retry.read==8;},"retry read");release(retry);reading=nullptr;wait_for([]{return expected.empty();},"retry raw completion");
  need(t.free_mask==15&&t.outstanding==0,"final ownership leak");need(concurrent_issue_lc>0,"MC request serialized through LC");
  std::cout<<"PASS weights records="<<count<<" Wbeats="<<w_beats<<" raw_outputs="<<raw_outputs<<" faults="<<faults<<" concurrent_fill_read="<<concurrent_fill_read<<" concurrent_issue_lc="<<concurrent_issue_lc<<" cycles="<<cycle<<"\n";t.final();top.reset();return 0;
 }catch(const std::exception& e){std::cerr<<"FAIL "<<e.what()<<"\n";top.reset();return 1;}
}
