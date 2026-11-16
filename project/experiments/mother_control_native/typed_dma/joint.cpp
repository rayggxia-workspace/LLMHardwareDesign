#include "Vmc_dma_stage64_joint.h"
#include "verilated.h"
#include <algorithm>
#include <array>
#include <cstdint>
#include <deque>
#include <fstream>
#include <iostream>
#include <map>
#include <memory>
#include <random>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>
using Data=std::array<uint32_t,16>;using Key=std::pair<int,uint32_t>;
struct Packet{int client=0,beat=0,length=0,channel=0;uint32_t tag=0;uint64_t address=0;Data data{};bool bad=false;};
struct Ext{Packet p;int due=0;bool offered=false,delivered=false;};
struct Stage {
 Packet p;int dst=0,first=0,words=0,requests=0,acks=0,capture=-1,raw_first=-1,last_ack=-1,raw_ack=-1;
 bool cancelled=false;
};
struct Held{bool valid=false,duplicate=false,invalid=false;uint64_t tag=0;Data data{};};
std::unique_ptr<Vmc_dma_stage64_joint>top;
#define t (*top)
std::mt19937 rng;std::ofstream trace;int cycle=0,accepted=0,issued=0,returned=0,cancelled=0,faults=0,fences=0,peak_beats=0,peak_desc=0,peak_issue=0;
std::array<std::deque<Packet>,12>queues;std::map<Key,Packet>expected;std::map<uint64_t,Ext>ext;
std::array<Held,4>held;std::array<bool,4>request_held{};std::array<uint64_t,4>old_request_tag{},old_request_address{};
std::array<bool,12>response_held{};std::array<Data,12>old_response{};std::array<uint32_t,12>old_response_tag{};
std::array<std::array<int,2>,2>history{};std::array<std::deque<uint32_t>,12>closes,cancels;
std::array<std::vector<int>,2>issue_cycles;
bool block_backend=false,block_clients=false,ideal=false,pause_fault=false,duplicate_next=false;
bool fence_request=false;int fence_client=9;uint32_t fence_cookie=0;uint16_t fence_epoch=0;
bool backend_fence=false;int fence_due=0;uint32_t backend_generation=0;
bool boot_purged=false,forced_bad_fence=false;
uint8_t mode_pending=0,mode_choice=0,client_drained=7;
int mode_accepts=0,native_legal=0,native_bad=0,stage_done=0,stage_reject=0,stage_cancel=0,stage_reads=0;
uint8_t hold_done=0,cancel_pending=0;
std::array<uint32_t,3>cancel_tags{};
std::map<Key,Stage>stages;
std::array<int,3>peak_stages{};
int dst(const Packet&p){return int((p.tag>>1)%160)*4;}
int nwords(const Packet&p){return (p.tag&2)?2:4;}
int first_word(const Packet&p){return nwords(p)==2&&p.tag&4?2:0;}
uint64_t last_global=0;int last_channel=0;
void need(bool b,const std::string&m){if(!b)throw std::runtime_error(m+" cycle="+std::to_string(cycle));}
template<class P>uint64_t u64(const P&p,int offset){return uint64_t(p[offset])|(uint64_t(p[offset+1])<<32);}
template<class P>void set64(P&p,int offset,uint64_t v){p[offset]=uint32_t(v);p[offset+1]=uint32_t(v>>32);}
template<class P>void zero(P&p,int words){for(int i=0;i<words;++i)p[i]=0;}
Data payload(int c,uint32_t tag){Data d{};for(int i=0;i<16;++i)d[size_t(i)]=0x250d0000U^uint32_t(c*65537)^tag^uint32_t(i*0x10203);return d;}
Packet packet(int client,int object,int beat,int length,int channel){Packet p;p.client=client;p.beat=beat;p.length=length;p.channel=channel;p.tag=uint32_t(object)<<(client<9?1:5);p.tag|=uint32_t(beat);p.address=0x1000000ULL+uint64_t(object)*4096+uint64_t(channel)*2048+uint64_t(beat)*64;p.data=payload(client,p.tag);return p;}
void add_record(int client,int object,int length,int channel,int first=0,int end=-1){if(end<0)end=length;for(int b=first;b<end;++b)queues[size_t(client)].push_back(packet(client,object,b,length,channel));}
bool source_empty(){for(auto&q:queues)if(!q.empty())return false;return true;}
bool all_idle(){return source_empty()&&expected.empty()&&ext.empty()&&stages.empty()&&t.debug_beats==0&&t.debug_descriptors==0&&!t.fault_valid&&!backend_fence;}
void advance(uint64_t goal){
 while(t.eventsPending()&&t.nextTimeSlot()<goal){
  Verilated::timeInc(t.nextTimeSlot()-Verilated::time());t.eval();
 }
 Verilated::timeInc(goal-Verilated::time());
}
void tick(){
 t.clk=0;t.p_mode_valid=mode_pending;t.p_mode_native64=mode_choice;t.p_mode_client_drained=client_drained;
 t.dyn_cmd_valid=0;zero(t.dyn_cmd_address,6);zero(t.dyn_cmd_tag,3);t.dyn_cmd_dst=0;t.dyn_cmd_first=0;t.dyn_cmd_words=0;t.dyn_force_bad_channel=0;
 t.dyn_cancel_valid=cancel_pending;for(int c=0;c<3;++c)t.dyn_cancel_tag[c]=cancel_tags[c];
 t.dyn_done_ready=uint8_t((ideal?7U:rng()&7U)&~hold_done);
 t.block_S_req=uint8_t(block_clients?7U:(ideal?0U:(rng()&rng())&7U));
 t.block_S_ack=uint8_t(ideal?0U:(rng()&rng())&7U);
 t.c_req_valid=0;zero(t.c_req_address,24);zero(t.c_req_tag,12);t.c_req_channel=0;t.c_req_record_beats=0;t.c_close_valid=0;zero(t.c_close_tag_base,12);t.c_cancel_valid=0;zero(t.c_cancel_tag,12);
 for(int c=0;c<12;++c){
  if(!queues[size_t(c)].empty()){
   auto&p=queues[size_t(c)].front();
   if(c<3&&((t.p_mode_active>>c)&1U)){
    t.dyn_cmd_valid|=uint8_t(1U<<c);set64(t.dyn_cmd_address,c*2,p.address);t.dyn_cmd_tag[c]=p.tag;
    t.dyn_cmd_dst|=uint32_t(dst(p))<<(10*c);t.dyn_cmd_words|=uint16_t(nwords(p)<<(3*c));
    t.dyn_cmd_first|=uint8_t(first_word(p)<<(2*c));t.dyn_force_bad_channel|=uint8_t((p.channel^int((p.address>>11)&1U))<<c);
   }else{
    t.c_req_valid|=uint16_t(1U<<c);set64(t.c_req_address,c*2,p.address);t.c_req_tag[c]=p.tag;
    t.c_req_channel|=uint16_t(p.channel<<c);t.c_req_record_beats|=uint64_t(p.length)<<(5*c);
   }
  }
  if(!closes[size_t(c)].empty()){t.c_close_valid|=uint16_t(1U<<c);t.c_close_tag_base[c]=closes[size_t(c)].front();}
  if(!cancels[size_t(c)].empty()){t.c_cancel_valid|=uint16_t(1U<<c);t.c_cancel_tag[c]=cancels[size_t(c)].front();}
 }
 t.c_rsp_ready=block_clients?0:uint16_t(ideal?4095:rng()&4095U);t.c_cancel_ack_ready=uint16_t(ideal?4095:rng()&4095U);t.fault_ready=!pause_fault;
 t.d_req_ready=block_backend?0:uint8_t(ideal?15:rng()&15U);t.d_rsp_valid=0;zero(t.d_rsp_tag,8);zero(t.d_rsp_data,64);
 for(int lane=0;lane<4;++lane){
  if(!held[size_t(lane)].valid){
   std::vector<uint64_t>ready;for(auto&[tag,x]:ext)if(!x.offered&&!x.delivered&&x.due<=cycle&&x.p.channel==lane/2)ready.push_back(tag);
   if(!ready.empty()){uint64_t tag=ready[size_t(rng()%ready.size())];auto&x=ext.at(tag);x.offered=true;held[size_t(lane)]={true,false,false,tag,x.p.data};
    if(duplicate_next&&(lane%2==0)&&!held[size_t(lane+1)].valid){held[size_t(lane+1)]={true,true,false,tag,x.p.data};duplicate_next=false;}
   }
  }
  auto&h=held[size_t(lane)];if(h.valid){t.d_rsp_valid|=uint8_t(1U<<lane);set64(t.d_rsp_tag,lane*2,h.tag);for(int i=0;i<16;++i)t.d_rsp_data[lane*16+i]=h.data[size_t(i)];}
 }
 t.c_fence_valid=fence_request?uint16_t(1U<<fence_client):0;zero(t.c_fence_cookie,12);zero(t.c_fence_epoch,4);t.c_fence_cookie[fence_client]=fence_cookie;
 for(int b=0;b<9;++b)if((fence_epoch>>b)&1U)t.c_fence_epoch[(fence_client*9+b)/32]|=uint32_t(1U<<((fence_client*9+b)%32));
 t.c_fence_done_ready=uint16_t(ideal?4095:rng()&4095U);t.d_fence_ready=ideal||cycle%3!=0;t.d_fence_done_valid=forced_bad_fence||(backend_fence&&cycle>=fence_due);t.d_fence_done_generation=forced_bad_fence?0xdeadbeefU:backend_generation;t.eval();
 if(!t.reset){
  for(int c=0;c<3;++c){
   if((t.dyn_cmd_admit>>c)&1U){
    auto p=queues[size_t(c)].front();Key key={c,p.tag};need(!stages.count(key),"duplicate stage admission");
    Stage v;v.p=p;v.dst=dst(p);v.first=first_word(p);v.words=nwords(p);stages.emplace(key,v);
    int live=0;for(auto&[k,sv]:stages){(void)sv;live+=k.first==c;}
    peak_stages[c]=std::max(peak_stages[c],live);need(live<=2,"stage owner over capacity");
    trace<<"STAGE_CMD,"<<cycle<<","<<c<<","<<p.tag<<","<<v.dst<<","<<v.first<<","<<v.words<<"\n";
   }
   if(((t.dyn_cancel_valid&t.dyn_cancel_ready)>>c)&1U){
    auto tag=cancel_tags[c];need(stages.count({c,tag}),"cancel missing admitted owner");stages.at({c,tag}).cancelled=true;
    cancel_pending&=uint8_t(~(1U<<c));trace<<"STAGE_CANCEL,"<<cycle<<","<<c<<","<<tag<<"\n";
   }
   if(((t.p_mode_active&t.c_rsp_valid)>>c)&1U){
    auto tag=t.c_rsp_tag[c];need(stages.count({c,tag}),"real raw has no matching stage");auto&v=stages.at({c,tag});
    if(v.raw_first<0){v.raw_first=cycle;need(v.capture>=0&&v.capture<cycle,"raw before backend landing");
     trace<<"STAGE_RAW_FIRST,"<<cycle<<","<<c<<","<<tag<<"\n";}
    if((t.mon_s_ack>>c)&1U){need(v.acks<v.requests,"orphan true SACK");++v.acks;v.last_ack=cycle;
     trace<<"STAGE_SACK,"<<cycle<<","<<c<<","<<tag<<","<<v.acks<<"\n";}
    if((t.mon_s_req>>c)&1U){
     need(v.requests<v.words&&v.requests-v.acks<2,"S req bounds");
     int addr=int((t.mon_s_address>>(c*10))&1023U);need(addr==v.dst+v.requests,"true S write address");
     for(int q=0;q<4;++q)need(t.mon_s_data[c*4+q]==v.p.data[(v.first+v.requests)*4+q],"true S write payload");
     ++v.requests;trace<<"STAGE_SREQ,"<<cycle<<","<<c<<","<<tag<<","<<addr<<"\n";
    }
    if((t.mon_raw_retire>>c)&1U){
     need(v.acks==v.requests&&(v.last_ack<cycle)&&v.acks==(v.cancelled?0:v.words),"raw release before true S drain");
     v.raw_ack=cycle;trace<<"STAGE_RAW_ACK,"<<cycle<<","<<c<<","<<tag<<"\n";
    }
   }else need(!((t.mon_s_req|t.mon_s_ack|t.mon_raw_retire)&(1<<c)),"S/response owner absent");
   if(((t.dyn_done_valid&t.dyn_done_ready)>>c)&1U){
    auto tag=t.dyn_done_tag[c];need(stages.count({c,tag}),"unknown stage terminal");auto v=stages.at({c,tag});
    bool e=(t.dyn_done_error>>c)&1U,x=(t.dyn_done_cancelled>>c)&1U;int mask=(t.dyn_done_mask>>(4*c))&15;
    need(e==v.p.bad&&x==v.cancelled&&mask==(e||x?0:(1<<v.words)-1),"stage terminal status/word proof");
    if(e){need(v.capture<0&&v.raw_first<0&&v.requests==0,"rejected stage consumed payload");++stage_reject;}
    else {need(v.raw_ack>=0&&v.raw_ack<cycle,"terminal before true raw retire");if(x)++stage_cancel;}
    trace<<"STAGE_DONE,"<<cycle<<","<<c<<","<<tag<<","<<mask<<","<<int(e)<<","<<int(x)<<"\n";
    stages.erase({c,tag});++stage_done;
   }
  }
  uint8_t mfire=t.p_mode_valid&t.p_mode_ready;
  if(mfire){need(boot_purged,"mode admitted before actual startup purge");
   for(int c=0;c<3;++c)if(mfire&(1<<c)){++mode_accepts;trace<<"MODE,"<<cycle<<","<<c<<","<<((mode_choice>>c)&1)<<"\n";}
   mode_pending&=~mfire;
  }
  std::array<int,2>now{};
  for(int lane=0;lane<4;++lane){
   bool valid=(t.d_req_valid>>lane)&1U,ready=(t.d_req_ready>>lane)&1U;uint64_t tag=u64(t.d_req_tag,lane*2),address=u64(t.d_req_address,lane*2);
   if(request_held[size_t(lane)]){need(valid&&tag==old_request_tag[size_t(lane)]&&address==old_request_address[size_t(lane)],"offered DDR request withdrawn/changed");}request_held[size_t(lane)]=valid&&!ready;old_request_tag[size_t(lane)]=tag;old_request_address[size_t(lane)]=address;
   if(valid&&ready){int client=int((tag>>6)&15U);need(client<12,"global tag client");Packet*found=nullptr;for(auto&[key,p]:expected)if(p.client==client&&p.address==address)found=&p;need(found!=nullptr,"DDR issue without accepted source reservation");need(found->channel==lane/2,"DDR channel remap");need(!ext.count(tag),"global ticket reused while live");ext[tag]={*found,cycle+3+int(rng()%7),false,false};last_global=tag;last_channel=lane/2;++issued;++now[size_t(lane/2)];issue_cycles[size_t(lane/2)].push_back(cycle);trace<<"ISSUE,"<<cycle<<","<<client<<","<<found->tag<<","<<lane<<","<<tag<<"\n";}
  }
  for(int ch=0;ch<2;++ch){need(now[size_t(ch)]+history[size_t(ch)][0]+history[size_t(ch)][1]<=4,"rolling3 actual issue budget exceeded");peak_issue=std::max(peak_issue,now[size_t(ch)]);history[size_t(ch)][1]=history[size_t(ch)][0];history[size_t(ch)][0]=now[size_t(ch)];}
  for(int c=0;c<12;++c){
   bool valid=(t.c_rsp_valid>>c)&1U,ready=(t.mon_rsp_ready>>c)&1U;Data data{};for(int i=0;i<16;++i)data[size_t(i)]=t.c_rsp_data[c*16+i];
   if(response_held[size_t(c)]){need(valid&&t.c_rsp_tag[c]==old_response_tag[size_t(c)]&&data==old_response[size_t(c)],"client return changed under backpressure");}response_held[size_t(c)]=valid&&!ready;old_response_tag[size_t(c)]=t.c_rsp_tag[c];old_response[size_t(c)]=data;
   if(valid&&ready){Key key={c,t.c_rsp_tag[c]};need(expected.count(key)&&expected.at(key).data==data,"return bytes/local ownership/duplicate");uint64_t gid=0;bool found=false;for(auto&[tag,x]:ext)if(x.p.client==c&&x.p.tag==key.second){need(x.delivered,"client return before real backend return");gid=tag;found=true;}need(found,"client return absent real DDR issue");ext.erase(gid);expected.erase(key);++returned;trace<<"CLIENT_RETURN,"<<cycle<<","<<c<<","<<key.second<<"\n";}
   if((((t.c_req_valid&t.c_req_ready)|(t.dyn_cmd_valid&t.dyn_cmd_ready))>>c)&1U){need(boot_purged,"source accepted before real reset-startup purge");auto p=queues[size_t(c)].front();queues[size_t(c)].pop_front();
    if(c<3){need(bool((t.p_req_rejected>>c)&1U)==p.bad,"typed source false allocation or missing rejection");
      if((t.p_mode_active>>c)&1U){if(p.bad)++native_bad;else ++native_legal;}}
    if(!p.bad){need(!expected.count({c,p.tag}),"source reused live local tag");expected[{c,p.tag}]=p;++accepted;trace<<"RESERVE,"<<cycle<<","<<c<<","<<p.tag<<","<<p.channel<<"\n";}else trace<<"REJECTED_SOURCE,"<<cycle<<","<<c<<","<<p.tag<<"\n";}
   if(((t.c_close_valid&t.c_close_ready)>>c)&1U){trace<<"CLOSE,"<<cycle<<","<<c<<","<<closes[size_t(c)].front()<<"\n";closes[size_t(c)].pop_front();}
   if(((t.c_cancel_valid&t.c_cancel_ready)>>c)&1U)cancels[size_t(c)].pop_front();
   if(((t.c_cancel_ack_valid&t.c_cancel_ack_ready)>>c)&1U){if(!((t.c_cancel_ack_rejected>>c)&1U)){Key key={c,t.c_cancel_ack_tag[c]};need(expected.count(key),"cancel ACK without reservation");for(auto&[tag,x]:ext){(void)tag;need(!(x.p.client==c&&x.p.tag==key.second),"cancelled offered/issued DDR beat");}expected.erase(key);++cancelled;}trace<<"CANCEL_ACK,"<<cycle<<","<<c<<","<<t.c_cancel_ack_tag[c]<<","<<((t.c_cancel_ack_rejected>>c)&1U)<<"\n";}
  }
  for(int lane=0;lane<4;++lane)if(((t.d_rsp_valid&t.d_rsp_ready)>>lane)&1U){auto h=held[size_t(lane)];need(h.valid,"missing external held packet");if(!h.invalid){need(ext.count(h.tag),"unknown backend packet");if(!ext.at(h.tag).delivered){auto &p=ext.at(h.tag).p;
      if(stages.count({p.client,p.tag})){auto&v=stages.at({p.client,p.tag});v.capture=cycle;
       trace<<"STAGE_CAPTURE,"<<cycle<<","<<p.client<<","<<p.tag<<"\n";}
      ext.at(h.tag).delivered=true;}else need(h.duplicate,"normal backend packet duplicated");}trace<<"DDR_RETURN,"<<cycle<<","<<lane<<","<<h.tag<<","<<int(h.invalid||h.duplicate)<<"\n";held[size_t(lane)].valid=false;}
  if(t.fault_valid&&t.fault_ready){if(t.fault_kind<=2)need(t.fault_client==15,"unowned transport blamed a reused client");++faults;trace<<"FAULT,"<<cycle<<","<<int(t.fault_kind)<<","<<int(t.fault_client)<<","<<t.fault_global_tag<<"\n";}
  if(t.c_fence_valid&t.c_fence_ready)fence_request=false;
  if(t.d_fence_valid&&t.d_fence_ready){need(!backend_fence&&expected.empty()&&ext.empty(),"backend FENCE before actual issued return drain");backend_fence=true;backend_generation=t.d_fence_generation;fence_due=cycle+4;++fences;trace<<"FENCE_OFFER,"<<cycle<<","<<backend_generation<<"\n";}
  if(t.d_fence_done_valid&&t.d_fence_done_ready){if(forced_bad_fence)forced_bad_fence=false;else{backend_fence=false;boot_purged=true;}}
  if(t.c_fence_done_valid&t.c_fence_done_ready){need(t.c_fence_done_cookie[fence_client]==fence_cookie,"fence cookie");uint32_t epoch=0;for(int b=0;b<9;++b)epoch|=((t.c_fence_done_epoch[(fence_client*9+b)/32]>>((fence_client*9+b)%32))&1U)<<b;need(epoch==fence_epoch,"fence epoch");}
  for(int ch=0;ch<2;++ch){int b=int((t.debug_beats>>(ch*6))&63U),d=int((t.debug_descriptors>>(ch*6))&63U);need(b<=32&&d<=32,"global channel credit overflow");peak_beats=std::max(peak_beats,b);peak_desc=std::max(peak_desc,d);}
 }
 advance(Verilated::time()+5000);t.clk=1;t.eval();
 advance(Verilated::time()+5000);t.clk=0;t.eval();++cycle;
}
template<class F>void wait(F fn,const std::string&m){for(int n=0;n<200000;++n){if(fn())return;tick();}throw std::runtime_error(m+" timeout cycle="+std::to_string(cycle));}
void quiet(){wait([]{return all_idle();},"actual transport drain");for(int n=0;n<12;++n)tick();wait([]{return all_idle();},"post-drain finite fence");}
void set_modes(uint8_t mask,uint8_t bits){
 mode_pending=mask;mode_choice=bits;
 wait([]{return mode_pending==0;},"actual mode acceptance");
 need((t.p_mode_active&mask)==(bits&mask),"mode selection didn't bind");
}
Packet one(int client,int serial,int channel){
 auto p=packet(client,serial,0,1,channel);
 p.address+=64;return p; // legally not 128B-aligned
}
void submit_bad(Packet p){
 int old=faults,oa=accepted,oi=issued;p.bad=true;
 queues[size_t(p.client)].push_back(p);
 wait([&]{return source_empty()&&faults==old+1;},"bounded typed rejection");
 for(int i=0;i<4;++i)tick();
 need(accepted==oa&&issued==oi,"bad typed request reserved/issued data");
}
void read_words(const Packet&p){
 int c=p.client;uint8_t bit=uint8_t(1U<<c);need(stages.empty(),"readback while stage still owns S");
 t.rd_mode=bit;t.rd_rsp_ready=bit;
 for(int j=0;j<nwords(p);++j){
  t.rd_address=uint32_t(dst(p)+j)<<(c*10);t.rd_valid=bit;t.eval();
  wait([&]{return (t.rd_ready&bit)!=0;},"actual S read request");tick();t.rd_valid=0;t.eval();
  wait([&]{return (t.rd_rsp_valid&bit)!=0;},"actual S read response");
  for(int q=0;q<4;++q)need(t.rd_data[c*4+q]==p.data[(first_word(p)+j)*4+q],"actual bank readback mismatch");
  tick();++stage_reads;
 }
 t.rd_mode=0;t.rd_rsp_ready=0;
}
int main(int argc,char**argv){try{
 need(argc==4,"usage seed initial trace");rng.seed(uint32_t(std::stoul(argv[1])));Verilated::randReset(std::stoi(argv[2]));Verilated::randSeed(int(std::stoul(argv[1])));top=std::make_unique<Vmc_dma_stage64_joint>();trace.open(argv[3]);t.rd_mode=0;t.rd_valid=0;t.rd_address=0;t.rd_rsp_ready=0;t.reset=1;for(int n=0;n<4;++n)tick();t.reset=0;
 need(t.p_mode_active==0,"startup default must remain legacy");
 // All twelve real source classes/channels, finite ports, OOO returns,
 // stalls, two DDR lanes targeting one single-port client and duplicate race.
 duplicate_next=true;
 for(int round=0;round<4;++round)for(int c=0;c<12;++c)add_record(c,1000+round*20+c,c<9?2:17+(round&1),(round+c)&1);
 quiet();need(faults==1,"same-cycle duplicate did not produce one bounded diagnostic");
 // Closed-record credits cannot retire merely because current data is idle.
 int before=returned;add_record(9,2000,17,0,0,3);wait([&]{return source_empty()&&returned==before+3&&expected.empty();},"partial record data returned");for(int n=0;n<5;++n){tick();need((t.debug_descriptors&63U)==1,"partial descriptor freed without CLOSE");}closes[9].push_back(uint32_t(2000<<5));quiet();
 // A true pre-offer reservation can cancel; no issue or return is invented.
 ideal=true;int oldaccepted=accepted,oldcancel=cancelled;add_record(10,2010,17,1,0,1);wait([&]{return accepted==oldaccepted+1;},"single reservation");cancels[10].push_back(uint32_t(2010<<5));closes[10].push_back(uint32_t(2010<<5));wait([&]{return cancelled==oldcancel+1;},"reservation cancel ACK");quiet();
 // Offered request stays stable, cannot cancel, then genuinely issues/returns.
 block_backend=true;add_record(11,2020,18,0,0,1);wait([]{return t.d_req_valid!=0;},"held offered request");int oldcancelled=cancelled;cancels[11].push_back(uint32_t(2020<<5));for(int n=0;n<7;++n)tick();need(cancelled==oldcancelled,"offered request was cancelled");block_backend=false;closes[11].push_back(uint32_t(2020<<5));quiet();ideal=false;
 // Thirty-two unclosed two-beat scopes reach both exact independent limits.
 block_backend=true;for(int i=0;i<32;++i)add_record(0,3000+i,2,0,0,1);wait([]{return source_empty()&&(t.debug_beats&63U)==32;},"exact 32-beat capacity");need((t.debug_descriptors&63U)==32,"exact descriptor capacity");add_record(1,3032,2,0,0,1);int atcap=accepted;for(int n=0;n<8;++n){tick();need(accepted==atcap,"33rd beat/descriptor accepted");}block_backend=false;
 // Keep the denied 33rd VALID stable on client1; client0 can still close
 // its admitted records instead of an artificial source head-of-line stall.
 for(int i=0;i<32;++i){add_record(0,3000+i,2,0,1,2);}add_record(1,3032,2,0,1,2);quiet();
 // A real purge can occur while another logical record remains open; data
 // already returned is preserved and the future beat gets a new global tag.
 before=returned;add_record(1,4000,2,1,0,1);wait([&]{return source_empty()&&returned==before+1;},"open descriptor prefix");fence_client=9;fence_cookie=0x2500abcd;fence_epoch=17;fence_request=true;int oldf=fences;wait([&]{return !fence_request&&fences>oldf&&!backend_fence&&!t.c_fence_done_valid;},"actual explicit FENCE");add_record(1,4000,2,1,1,2);quiet();
 // Unknown old global tag cannot borrow the owner now using that entry.
 int oldfault=faults;held[size_t(last_channel*2)]={true,false,true,last_global,payload(9,0)};wait([&]{return faults==oldfault+1;},"old global tag diagnostic");quiet();
 // A bad DDR return and a bad fence-done cannot both consume the sole fault
 // slot. The second producer must honestly remain held until the slot frees.
 oldfault=faults;pause_fault=true;held[size_t(last_channel*2)]={true,false,true,last_global,payload(9,0)};forced_bad_fence=true;wait([]{return t.fault_valid;},"held unowned diagnostic");for(int n=0;n<5;++n){tick();need(forced_bad_fence&&!t.d_fence_done_ready,"second bad transport consumed without diagnostic credit");}pause_fault=false;wait([&]{return faults==oldfault+2&&!forced_bad_fence;},"two bounded bad transport diagnostics");quiet();
 // The registry's 128B scope alignment is stricter than a 64B DDR beat.
 // Invalid source fields retire only through the fault slot, never data.
 oldfault=faults;auto bad_scope=packet(2,5000,0,2,0);bad_scope.address+=64;bad_scope.bad=true;queues[2].push_back(bad_scope);wait([&]{return source_empty()&&faults==oldfault+1;},"misaligned scope rejected");quiet();
 // Independent raw-fabric service stress, not a claim about complete M/LC
 // throughput. Three single-port clients interleave finite typed records.
 // With no backend/client stalls both channels must approach the contracted
 // 4/3 rate; serial-limit3 honestly includes actual namespace-purge pauses.
 ideal=true;std::array<size_t,2>perf_start={issue_cycles[0].size(),issue_cycles[1].size()};uint32_t perf_generation=t.debug_generation;
 trace<<"PERF_BEGIN,"<<cycle<<"\n";
 for(int round=0;round<20;++round)for(int beat=0;beat<17;++beat)for(int object=0;object<4;++object)for(int client=9;client<12;++client){queues[size_t(client)].push_back(packet(client,6000+round*20+(client-9)*4+object,beat,17,(object+client)&1));}
 quiet();
 for(int ch=0;ch<2;++ch){auto&v=issue_cycles[size_t(ch)];size_t first=perf_start[size_t(ch)]+100,last=v.size()-101;need(last>first,"service stress too short");double efficiency=double(last-first+1)*3.0/(4.0*double(v[last]-v[first]+1));trace<<"PERF_WINDOW,"<<ch<<","<<v[first]<<","<<v[last]<<","<<last-first+1<<","<<efficiency<<","<<t.debug_generation-perf_generation<<"\n";trace.flush();if(t.debug_generation==perf_generation)need(efficiency>.97,"raw fabric cannot approach its physical service rate");}
 // Old scope mode still rejects native64 and protects one local descriptor
 // identity across both DDR channels while its other half is outstanding.
 submit_bad(one(0,10000,1));
 add_record(0,10100,2,0,0,1);
 int pre=returned;wait([&]{return returned==pre+1&&source_empty();},"legacy prefix returned");
 auto cross=packet(0,10100,0,2,1);submit_bad(cross);
 mode_pending=1;mode_choice=1;
 for(int i=0;i<8;++i){tick();need(mode_pending==1&&t.p_mode_active==0,"mode switched with open legacy descriptor");}
 add_record(0,10100,2,0,1,2);
 wait([]{return mode_pending==0;},"prefix descriptor drain then typed mode");
 need(t.p_mode_active==1,"native mode after true legacy drain");
 // A held return occupies a real skid, and a local DONE must drain even
 // after transport credits disappear. Neither state permits a mode change.
 block_clients=true;queues[0].push_back(one(0,11000,0));
 wait([]{return (t.c_rsp_valid&1)!=0;},"held native result");
 mode_pending=1;mode_choice=0;hold_done=1;
 for(int i=0;i<8;++i){tick();need(mode_pending==1&&t.p_mode_active==1,"undrained native return changed mode");}
 block_clients=false;
 wait([]{return expected.empty()&&ext.empty()&&t.debug_beats==0&&t.debug_descriptors==0&&(t.dyn_done_valid&1);},"actual raw/S drain with DONE retained");
 for(int i=0;i<8;++i){tick();need(mode_pending==1&&t.p_mode_active==1,"local DONE owner did not block mode transition");}
 hold_done=0;wait([]{return mode_pending==0;},"transport+client drained");need(t.p_mode_active==0,"back to scope");
 set_modes(7,7);
 submit_bad(one(0,11000,1)); // replay even after mode switch/other channel
 auto odd=one(1,11001,0);odd.tag|=1;submit_bad(odd);
 auto mis=one(1,11001,0);mis.address+=16;submit_bad(mis);
 auto wrong=one(2,11001,0);wrong.channel=1;submit_bad(wrong);

 // A rejected tag never advances its monotonic cursor. Three new request
 // owners contend with ordinary W and unmodified scope sources.
 ideal=false;
 for(int row=0;row<144;++row){
  for(int c=0;c<3;++c)queues[size_t(c)].push_back(one(c,11100+row,(row+c)&1));
  if(row%8==0){
   add_record(3,13000+row,2,1);
   add_record(9,14000+row,17,0);
   add_record(11,15000+row,18,1);
  }
 }
 quiet();need(native_legal==433&&native_bad==4,"native64 valid/reject coverage");
 // Only this client's accepted FENCE DONE resets its local replay cursor;
 // global serial auto-purge is independent of a local namespace reset.
 fence_client=0;fence_cookie=0x25000bc1;fence_epoch=21;fence_request=true;
 oldf=fences;wait([&]{return !fence_request&&fences>oldf&&!backend_fence&&!t.c_fence_done_valid;},
                 "real typed-client FENCE");
 queues[0].push_back(one(0,7,0));quiet();
 submit_bad(one(1,7,0));
 need(native_legal==434&&native_bad==5,"typed client FENCE namespace");
 for(int c=0;c<3;++c)read_words(one(c,11243,(143+c)&1));
 // Cancel a stage before raw arrives. The request still issues/returns,
 // but it produces no S write and cannot bypass the held raw drain.
 block_backend=true;int base_legal=native_legal;auto cp=one(0,16000,1);queues[0].push_back(cp);
 wait([&]{return native_legal==base_legal+1;},"admitted real early cancel");
 cancel_tags[0]=cp.tag;cancel_pending=1;
 wait([]{return cancel_pending==0;},"stage exact early cancel");
 block_backend=false;quiet();need(stage_cancel==1,"expected one drained stage cancel");
 set_modes(7,0);
 add_record(0,10100,2,0);add_record(2,15100,2,1);quiet();
 need(stage_done==440&&stage_reject==5&&stage_reads==6&&peak_stages[0]==2&&peak_stages[1]==2&&peak_stages[2]==2,"actual three-stage terminal/ownership/readback coverage");
 need(mode_accepts==8&&t.p_mode_active==0,"runtime mode transition count");
 need(expected.empty()&&accepted==returned+cancelled&&issued==returned,"source/return/cancel work conservation");need(peak_beats==32&&peak_desc==32&&peak_issue==2,"finite resources or both physical lanes not exercised");
 std::cout<<"PASS DMA clients=12 accepted="<<accepted<<" issued="<<issued<<" returned="<<returned<<" reserved_cancelled="<<cancelled<<" faults="<<faults<<" backend_fences="<<fences<<" peak_beats_per_channel="<<peak_beats<<" peak_descriptors_per_channel="<<peak_desc<<" max_issue_per_channel="<<peak_issue<<" rolling3_bound=4 native64="<<native_legal<<" native64_rejects="<<native_bad<<" stage_done="<<stage_done<<" stage_rejected="<<stage_reject<<" stage_cancel="<<stage_cancel<<" true_S_reads="<<stage_reads<<" mode_accepts="<<mode_accepts<<" cycles="<<cycle<<"\n";
 top->final();top.reset();return 0;
 }catch(const std::exception&e){std::cerr<<"FAIL "<<e.what()<<"\n";if(top){top->final();top.reset();}return 1;}}
