#include "Vm_joint_top.h"
#include "verilated.h"
#include <algorithm>
#include <array>
#include <deque>
#include <fstream>
#include <iostream>
#include <map>
#include <memory>
#include <random>
#include <stdexcept>
#include <string>
#include <vector>
using V8=std::array<uint32_t,8>;using V4=std::array<uint32_t,4>;using V16=std::array<uint32_t,16>;
struct R{bool head=false,allocated=false;int n=8,id=0,bank=0,gen=0,read=0;bool ack=false;uint64_t shifts=0;V8 bias{},final{};std::vector<V8> prefix;std::vector<V16> dma;std::array<V8,8>a{};std::array<bool,18> issued{},returned{};};
struct E{int kind=0,ctx=0,owner=0,ticket=0,record=0,bank=0,gen=0,use=0,next=0,full=0,group=0,n=0;bool final=false,snapshot=false,error=false;uint32_t tag=0;V8 data{};};
std::unique_ptr<Vm_joint_top> top;
#define t (*top)
std::deque<E> expected,terminals;std::map<int,E> commands,committed;
std::vector<R*> live;R* reading=nullptr;R* issuing=nullptr;R* filling=nullptr;
std::mt19937 rng;int cycle=0,credit=0,responses=0,groups=0,a_beats=0,weight_faults=0,native_faults=0,native_issues=0,input_acks=0,s_acks=0,peak_results=0;
std::ofstream timing;int exec_start=0,first_a=0,last_a=0,input_done_cycle=0,raw_groups=0,rf_groups=0;
bool force_a=false,pause_store=false,allow_capture=true,use_guard=true,inject_a=false,ideal_ports=false;
bool f_alloc=false,f_issue=false,f_fill=false,f_exec=false,f_control=false,f_cancel=false,f_drain=false,f_gu=false;
bool held=false;std::vector<uint32_t> saved;
struct PendingAck{bool live=false;V16 ticket{};int word=0,due=0;} ack;
template<size_t N>std::array<uint32_t,N> hx(const std::string&s){std::array<uint32_t,N>v{};for(size_t n=0;n<N;++n){size_t end=s.size()>n*8?s.size()-n*8:0,begin=end>8?end-8:0;if(end)v[n]=uint32_t(std::stoul(s.substr(begin,end-begin),nullptr,16));}return v;}
template<class P,size_t N>void put(P&p,const std::array<uint32_t,N>&v){for(size_t i=0;i<N;++i)p[i]=v[i];}
template<class P,size_t N>bool eq(const P&p,const std::array<uint32_t,N>&v){for(size_t i=0;i<N;++i)if(p[i]!=v[i])return false;return true;}
template<class P>void key(P&p){p[0]=0x101;p[1]=1;p[2]=0x250;p[3]=1;}
template<class P>void own(P&p,int id){p[0]=uint32_t(id);p[1]=1;p[2]=0x250;p[3]=2;}
void need(bool v,const std::string&m){if(!v)throw std::runtime_error(m+" cycle="+std::to_string(cycle));}
#define ID(P,R) t.P##_bank=(R).bank;t.P##_generation=(R).gen;key(t.P##_key);t.P##_record=(R).id
V16 ticket(const E&e){V16 v{};auto add=[&](uint32_t x,int at,int bits){for(int b=0;b<bits;++b)if((x>>b)&1U)v[size_t((at+b)/32)]|=1U<<((at+b)%32);};add(uint32_t(e.kind),0,3);add(uint32_t(e.ctx),3,4);add(uint32_t(e.record),7,32);add(uint32_t(e.ticket),39,32);
 V4 k{0x101,1,0x250,1},o{uint32_t(e.owner),1,0x250,2};for(int i=0;i<4;++i){add(e.record?k[size_t(i)]:0,71+i*32,32);add(o[size_t(i)],199+i*32,32);}return v;}
std::vector<uint32_t> snap(){std::vector<uint32_t>v;for(int i=0;i<8;++i)v.push_back(t.rsp_data[i]);for(int i=0;i<4;++i){v.push_back(t.rsp_owner[i]);v.push_back(t.rsp_key[i]);}for(uint32_t x:{t.rsp_ticket,t.rsp_record,uint32_t(t.rsp_generation),uint32_t(t.rsp_next_k),uint32_t(t.rsp_error),uint32_t(t.rsp_kind),uint32_t(t.rsp_snapshot)})v.push_back(x);return v;}
void tick(){
 t.clk=0;t.guard_enable=use_guard;t.allow_capture=allow_capture;
 t.a_valid=reading&&reading->read<8&&!force_a&&(ideal_ports||cycle%7!=0);
 if(t.a_valid){auto&r=*reading;key(t.a_key);if(inject_a)t.a_key[1]^=1;t.a_record=r.id;t.a_slot=r.id&1;t.a_generation=uint16_t(r.id+3);t.a_kk=t.exec_kk;t.a_use=uint16_t(r.id+17);t.a_beat=r.read;put(t.a_data,r.a[size_t(r.read)]);}
 t.input_done_ready=ideal_ports||cycle%5!=0;t.abort_done_ready=0;
 t.gu_native_ready=1;t.gu_s_ready=!pause_store&&(ideal_ports||cycle%5!=0);t.gu_terminal_ready=ideal_ports||cycle%11<8;
 t.gu_ack_valid=ack.live&&!pause_store&&cycle>=ack.due;put(t.gu_ack_ticket,ack.ticket);t.gu_ack_word=ack.word;t.gu_ack_error=0;t.eval();
 f_alloc=t.alloc_valid&&t.alloc_ready;f_issue=t.issue_valid&&t.issue_ready;f_fill=t.fill_valid&&t.fill_ready;f_exec=t.exec_valid&&t.exec_ready;f_control=t.control_valid&&t.control_ready;f_cancel=t.cancel_valid&&t.cancel_ready;f_drain=t.drain_valid&&t.drain_ready;f_gu=t.gu_cmd_valid&&t.gu_cmd_ready;
 if(!t.reset){
  if(held&&!f_cancel){need(t.rsp_valid&&snap()==saved,"M held response changed/reused W identity");}held=t.rsp_valid&&!t.rsp_ready;saved=snap();
  if(f_issue){need(issuing!=nullptr,"unowned MC issue");issuing->issued[t.issue_beat]=true;++credit;}
  if(f_fill){need(filling!=nullptr,"unowned MC return");filling->returned[t.fill_beat]=true;--credit;}
  if(t.fill_ack_valid&&t.fill_ack_ready){bool found=false;for(auto*r:live)if(r->id==int(t.fill_ack_record)&&r->gen==int(t.fill_ack_generation)&&r->bank==int(t.fill_ack_bank)){need(!t.fill_ack_error,"public record invalid");r->ack=true;found=true;}need(found,"unknown FILLACK");}
  if(t.fault_valid&&t.fault_ready){++weight_faults;}if(t.native_fault_valid&&t.native_fault_ready){++native_faults;}
  if(f_exec){exec_start=cycle;first_a=last_a=input_done_cycle=-1;}
  if(t.a_valid&&t.a_ready&&!inject_a){need(reading!=nullptr,"unowned A");if(reading->read==0)first_a=cycle;last_a=cycle;++reading->read;++a_beats;}
  if(t.input_done_valid&&t.input_done_ready){need(reading&&reading->read==8&&int(t.input_done_record)==reading->id&&int(t.input_done_generation)==reading->gen,"input ACK identity");input_done_cycle=cycle;++input_acks;}
  if(t.dbg_raw_fire){++raw_groups;timing<<"RAW,"<<cycle<<","<<(reading?reading->id:0)<<","<<t.exec_ticket<<","<<t.dbg_raw_offset<<","<<t.dbg_raw_tag<<"\n";}
  if(t.dbg_rf_retire){++rf_groups;timing<<"RF,"<<cycle<<","<<(reading?reading->id:0)<<","<<t.exec_ticket<<","<<t.dbg_rf_next<<","<<int(t.dbg_rf_error)<<"\n";}
  if(t.gu_native_valid&&t.gu_native_ready)++native_issues;
  if(t.rsp_valid&&t.rsp_ready){need(!expected.empty(),"unexpected M completion");auto e=expected.front();expected.pop_front();
   need(int(t.rsp_kind)==e.kind&&int(t.rsp_context)==e.ctx&&t.rsp_owner[0]==uint32_t(e.owner)&&t.rsp_owner[3]==2,"RF response owner/kind");
   need(t.rsp_ticket==uint32_t(e.ticket)&&t.rsp_tag==e.tag&&int(t.rsp_record)==e.record,"completion ticket/order");
   need(int(t.rsp_next_k)==e.next&&int(t.rsp_full_k)==e.full&&int(t.rsp_group_k)==e.group&&int(t.rsp_n)==e.n,"actual RF snapshot metadata");
   need(bool(t.rsp_final)==e.final&&bool(t.rsp_snapshot)==e.snapshot&&bool(t.rsp_error)==e.error&&eq(t.rsp_data,e.data),"exact FP16-scaled context value");
   if(e.record){need(t.rsp_key[0]==0x101&&int(t.rsp_bank)==e.bank&&int(t.rsp_generation)==e.gen&&int(t.rsp_use)==e.use,"reused W generation corrupted result");}
   ++responses;
   if(e.record)timing<<"RECORD,"<<cycle<<","<<e.record<<","<<e.ticket<<","<<exec_start<<","<<first_a<<","<<last_a<<","<<input_done_cycle<<","<<int(ideal_ports)<<","<<int(e.error)<<"\n";
  }
  if(t.gu_s_valid&&t.gu_s_ready){need(!ack.live,"more than one physical S write outstanding");V16 id{};for(int i=0;i<16;++i)id[size_t(i)]=t.gu_s_ticket[i];int tid=int((uint64_t(id[1])>>7)|(uint64_t(id[2])<<25));auto it=commands.find(tid);need(it!=commands.end()&&it->second.snapshot,"non-FINAL/SPILL wrote S");auto&e=it->second;
   need(eq(t.gu_s_ticket,ticket(e)),"S write ticket changed");int word=t.gu_s_word;for(int j=0;j<4;++j)need(t.gu_s_data[j]==e.data[size_t(word*4+j)],"S write word data");need(int(t.gu_s_address)==(e.ticket%400)*2+word,"S destination");ack={true,id,word,cycle+(ideal_ports?1:3+int(rng()%7))};}
  if(t.gu_ack_valid&&t.gu_ack_ready){need(ack.live,"ACK without physical S request");ack.live=false;++s_acks;}
  if(t.gu_terminal_valid&&t.gu_terminal_ready){need(!terminals.empty(),"unexpected guard terminal");auto e=terminals.front();terminals.pop_front();need(eq(t.gu_terminal_ticket,ticket(e))&&eq(t.gu_terminal_data,e.data),"S terminal immutable identity/data");need(bool(t.gu_terminal_stored)==e.snapshot,"S store policy/real ACK");need(bool(t.gu_terminal_error)==e.error,"guard error propagation");if(e.snapshot)committed[e.ticket]=e;}
  peak_results=std::max(peak_results,int(t.gu_result_count));need(t.gu_result_count<=2&&t.gu_count<=2,"unbounded external guard");
 }
 t.clk=1;t.eval();t.clk=0;t.eval();++cycle;if(!t.reset)need(credit==int(t.outstanding)&&credit>=0&&credit<=32,"native credit conservation");
}
template<class F>void wait(F f,const std::string&m){for(int n=0;n<60000;++n){if(f())return;tick();}throw std::runtime_error(m+" cycle="+std::to_string(cycle));}
void enqueue(const E&e){expected.push_back(e);if(!use_guard)return;commands[e.ticket]=e;put(t.gu_cmd_ticket,ticket(e));key(t.gu_cmd_key);t.gu_cmd_stored=e.snapshot;t.gu_cmd_destination=(e.ticket%400)*2;t.gu_cmd_valid=1;int goal=native_issues+1;do{tick();}while(!f_gu);t.gu_cmd_valid=0;terminals.push_back(e);wait([&]{return native_issues>=goal;},"guard native acceptance");}
void allocate(R&r){t.alloc_valid=1;key(t.alloc_key);t.alloc_record=r.id;t.alloc_head16=r.head;t.alloc_n=r.n;do{tick();}while(!f_alloc);t.alloc_valid=0;wait([]{return t.alloc_ack_valid;},"alloc ACK");need(!t.alloc_ack_error,"allocation rejected");r.bank=t.alloc_ack_bank;r.gen=t.alloc_ack_generation;r.allocated=true;live.push_back(&r);t.alloc_ack_ready=1;tick();t.alloc_ack_ready=0;}
void fill(const std::vector<R*>&rs){for(int guard=0;guard<60000;++guard){bool complete=true;for(auto*r:rs)for(size_t b=0;b<r->dma.size();++b)complete&=r->returned[b];if(complete)break;
 if(!t.issue_valid){std::vector<std::pair<R*,int>>v;for(auto*r:rs)for(size_t b=0;b<r->dma.size();++b)if(!r->issued[b])v.push_back({r,int(b)});if(!v.empty()){auto p=v[rng()%v.size()];issuing=p.first;ID(issue,*issuing);t.issue_beat=p.second;t.issue_valid=1;}}
 if(!t.fill_valid){std::vector<std::pair<R*,int>>v;for(auto*r:rs)for(size_t b=0;b<r->dma.size();++b)if(r->issued[b]&&!r->returned[b])v.push_back({r,int(b)});if(!v.empty()&&guard%4!=0){auto p=v[rng()%v.size()];filling=p.first;ID(fill,*filling);t.fill_beat=p.second;t.fill_last=p.second==int(filling->dma.size())-1;put(t.fill_data,filling->dma[size_t(p.second)]);t.fill_valid=1;}}
 tick();if(f_issue){t.issue_valid=0;issuing=nullptr;}if(f_fill){t.fill_valid=0;filling=nullptr;}}
 for(auto*r:rs){wait([&]{return r->ack;},"record fill ACK");} }
E control(int kind,int ctx,int owner,int tid,int full,int offset,int group,int n,const V8&data={},bool error=false,int desc_full=-1){E e;e.kind=kind;e.ctx=ctx;e.owner=owner;e.ticket=tid;e.tag=uint32_t(tid);e.next=error?0:offset;e.full=error?0:full;e.group=error?0:group;e.n=error?0:n;e.error=error;e.snapshot=kind==3&&!error;e.data=data;
 enqueue(e);t.control_kind=kind;t.control_context=ctx;own(t.control_owner,owner);t.control_ticket=tid;t.control_full_k=desc_full<0?full:desc_full;t.control_k_offset=offset;t.control_group_k=desc_full<0?group:16;t.control_n=desc_full<0?n:1;put(t.control_previous,data);t.control_valid=1;do{tick();}while(!f_control);t.control_valid=0;wait([]{return expected.empty();},"control response");return e;}
void start(R&r,int ctx,int owner,int tid,int full,int offset,const V8&value,bool error=false,bool queue=true){E e;e.kind=2;e.ctx=ctx;e.owner=owner;e.ticket=tid;e.tag=uint32_t(r.id*8+(error?0:(r.head?7:0)));e.record=r.id;e.bank=r.bank;e.gen=r.gen;e.use=r.id+17;e.next=error?0:offset+128;e.full=error?0:full;e.group=error?0:(r.head?16:128);e.n=error?0:r.n;e.final=!error&&offset+128==full;e.snapshot=e.final;e.error=error;e.data=value;
 if(queue){enqueue(e);}reading=&r;t.exec_valid=1;ID(exec,r);t.exec_use=uint16_t(r.id+17);t.exec_raw_tag=uint32_t(r.id*8);t.exec_ticket=tid;own(t.exec_owner,owner);t.exec_context=ctx;t.exec_full_k=full;t.exec_k_offset=offset;t.exec_kk=uint16_t(offset/128);t.exec_a_slot=r.id&1;t.exec_a_generation=uint16_t(r.id+3);t.exec_a_shifts=r.shifts;put(t.exec_bias,r.bias);do{tick();}while(!f_exec);t.exec_valid=0;groups+=r.head?8:1;}
void done(){wait([]{return !t.busy;},"native record completion");need(expected.empty(),"missing record response");reading=nullptr;}
R clone(const R&r,int id){R x=r;x.id=id;x.allocated=false;x.read=0;x.ack=false;x.issued.fill(false);x.returned.fill(false);return x;}
void proof(const E&e){t.control_snapshot_ticket=e.ticket;t.restore_commit_valid=1;own(t.restore_commit_owner,e.owner);t.restore_commit_context=e.ctx;t.restore_commit_ticket=e.ticket;t.restore_commit_next_k=e.next;t.restore_commit_full_k=e.full;t.restore_commit_group_k=e.group;t.restore_commit_n=e.n;}
int main(int argc,char**argv){try{need(argc==6,"usage records joint seed initial timing");rng.seed(uint32_t(std::stoul(argv[3])));Verilated::randReset(std::stoi(argv[4]));Verilated::randSeed(int(std::stoul(argv[3])));top=std::make_unique<Vm_joint_top>();timing.open(argv[5]);
 std::ifstream f(argv[1]),j(argv[2]);int count,jcount;f>>count;j>>jcount;need(count==34&&jcount==34,"fixture count");std::vector<R>rs(size_t(count),R{});std::string s;
 for(auto&r:rs){int head;f>>head>>r.n>>r.id;r.head=head;for(int b=0;b<(r.head?18:17);++b){f>>s;r.dma.push_back(hx<16>(s));}for(auto&a:r.a){f>>s;a=hx<8>(s);}for(int q=0;q<16+(r.head?8:1);++q)f>>s;int id;j>>id>>s;need(id==r.id,"joint identity");r.shifts=std::stoull(s,nullptr,16);j>>s;r.bias=hx<8>(s);for(int g=0;g<(r.head?8:1);++g){j>>s;r.prefix.push_back(hx<8>(s));}j>>s;r.final=hx<8>(s);}
 V8 cross_ordinary{},cross_head{};j>>s;cross_ordinary=hx<8>(s);j>>s;cross_head=hx<8>(s);need(bool(f)&&bool(j),"fixture parse");
 t.alloc_valid=0;t.alloc_ack_ready=0;t.issue_valid=0;t.fill_valid=0;t.fill_ack_ready=1;t.cancel_valid=0;t.drain_valid=0;t.drain_done_ready=1;t.fault_ready=1;t.exec_valid=0;t.control_valid=0;t.native_fault_ready=1;t.restore_commit_valid=0;t.gu_cmd_valid=0;t.reset=1;for(int n=0;n<4;++n)tick();t.reset=0;
 for(int i=0;i<4;++i){allocate(rs[size_t(i)]);}fill({&rs[0],&rs[1],&rs[2],&rs[3]});
 control(0,0,100,10001,128,0,128,rs[0].n);control(0,1,101,10002,128,0,128,rs[1].n);wait([]{return t.gu_count==0;},"precreate terminal drain");pause_store=true;
 for(int i=0;i<count;++i){auto&r=rs[size_t(i)];int owner=100+i,ctx=i%16;if(i>=2)control(0,ctx,owner,10000+i+1,128,0,r.head?16:128,r.n);
  if(i==1){allow_capture=false;}start(r,ctx,owner,20000+i,128,0,r.final);
  if(i==1){wait([&]{return r.read==8&&(t.free_mask&(1<<r.bank));},"early W release");wait([]{return t.rsp_valid;},"held RF result");auto before=snap();int oldgen=r.gen;
   allocate(rs[4]);allocate(rs[5]);fill({&rs[4],&rs[5]});need(rs[5].bank==r.bank&&rs[5].gen!=oldgen,"same bank was not really reused");need(snap()==before,"scale/result lost after real W reuse");
   int oldfault=weight_faults;t.cancel_valid=1;ID(cancel,r);do{tick();}while(!f_cancel);t.cancel_valid=0;wait([&]{return weight_faults>oldfault;},"late cancel rejection");need(!t.abort_done_valid&&t.busy,"late recycled-W cancel aborted result");allow_capture=true;pause_store=false;}
  done();
  if(i>=2&&i+4<count&&!rs[size_t(i+4)].allocated){allocate(rs[size_t(i+4)]);fill({&rs[size_t(i+4)]});}
 }
 wait([]{return t.gu_count==0&&!ack.live;},"final record S writes");need(peak_results==2,"actual two-result RTL guard never filled");
 // Two actual named source K slices concatenated into an explicit unit DAG.
 // The original model K coordinates are deliberately retained in manifest.
 std::deque<R> extras;
 for(int h=0;h<2;++h){extras.push_back(clone(rs[size_t(h?24:0)],3000+h*10));extras.push_back(clone(rs[size_t(h?25:1)],3001+h*10));auto&first=extras[extras.size()-2];auto&second=extras.back();int ctx=4+h,owner=700+h,group=h?16:128;
  allocate(first);allocate(second);fill({&first,&second});control(0,ctx,owner,31000+h*100,256,0,group,8);
  start(first,ctx,owner,31001+h*100,256,0,first.prefix.back());done();
  auto spill=control(3,ctx,owner,31002+h*100,256,128,group,8,first.prefix.back(),false,640);
  // SPILL captured and RF freed, but the real S words have not both ACKed.
  need(!committed.count(spill.ticket),"SPILL unexpectedly already stored");t.restore_commit_valid=0;control(1,ctx,owner,31003+h*100,256,128,group,8,V8{},true);
  wait([&]{return committed.count(spill.ticket)!=0;},"two real S word ACKs");proof(spill);++t.restore_commit_next_k;control(1,ctx,owner,31004+h*100,256,128,group,8,V8{},true);proof(spill);
  control(1,ctx,owner,31005+h*100,256,128,group,8,spill.data);t.restore_commit_valid=0;
  start(second,ctx,owner,31006+h*100,256,128,h?cross_head:cross_ordinary);done();
 }
 wait([]{return t.gu_count==0&&!ack.live;},"cross-record S commit");
 // Native input identity rejection must not consume a raw operand.
 auto bad_a=clone(rs[0],4000);allocate(bad_a);fill({&bad_a});control(0,6,800,40000,128,0,128,8);inject_a=true;int before_nf=native_faults;start(bad_a,6,800,40001,128,0,bad_a.final);wait([&]{return native_faults>before_nf;},"A wrong epoch rejection");need(bad_a.read==0,"wrong A was consumed");inject_a=false;done();
 // Out-of-order head cursor faults once externally; suffix drains without
 // fabricating seven more guard results or mutating the preserved RF.
 auto wrong_k=clone(rs[24],4100);allocate(wrong_k);fill({&wrong_k});control(0,7,810,41000,256,0,16,8);start(wrong_k,7,810,41001,256,128,V8{},true);done();control(4,7,810,41002,256,0,16,8);
 wait([]{return t.gu_count==0&&!ack.live;},"guard quiet before cancel");use_guard=false;
 // Partial head cancellation commits exactly the three real K16 prefixes;
 // abort waits until raw/RF drain and never claims atomic rollback.
 auto cancelled=clone(rs[24],4200);allocate(cancelled);fill({&cancelled});control(0,8,820,42000,128,0,16,8);start(cancelled,8,820,42001,128,0,V8{},false,false);wait([&]{return cancelled.read==3;},"head partial start");force_a=true;
 t.cancel_valid=1;ID(cancel,cancelled);do{tick();}while(!f_cancel);t.cancel_valid=0;wait([]{return t.abort_done_valid;},"native abort drain");need(t.abort_done_next_k==48&&int(t.abort_done_record)==cancelled.id,"head actual completed prefix");
 t.drain_valid=1;ID(drain,cancelled);for(int k=0;k<3;++k){tick();need(!f_drain,"W drained before raw abort acceptance");}t.drain_valid=0;
 t.abort_done_ready=1;t.clk=0;t.eval();t.clk=1;t.eval();t.clk=0;t.eval();++cycle;t.abort_done_ready=0;force_a=false;reading=nullptr;
 t.drain_valid=1;ID(drain,cancelled);do{tick();}while(!f_drain);t.drain_valid=0;control(3,8,820,42002,128,48,16,8,cancelled.prefix[2]);
 // Isolated no-backpressure timing with identical real payload/arithmetic.
 // W DMA fill/setup happens before exec and remains separately charged.
 ideal_ports=true;use_guard=true;
 for(int h=0;h<2;++h){extras.push_back(clone(rs[size_t(h?24:0)],5000+h));auto&r=extras.back();allocate(r);fill({&r});control(0,9+h,900+h,50000+h*2,128,0,h?16:128,8);start(r,9+h,900+h,50001+h*2,128,0,r.final);done();wait([]{return t.gu_count==0&&!ack.live;},"isolated real S write ACKs");}
 need(t.outstanding==0&&t.free_mask==15&&!t.busy&&expected.empty(),"joint final lease leak");need(t.gu_rejected==0,"guard rejected legitimate native result identity");
 need(raw_groups==rf_groups,"raw/RF group conservation");
 std::cout<<"PASS native records=34 planned_groups="<<groups<<" raw_groups="<<raw_groups<<" RF_groups="<<rf_groups<<" Abeats="<<a_beats<<" RFresponses="<<responses<<" inputACKs="<<input_acks<<" S128ACKs="<<s_acks<<" peak_result_slots="<<peak_results<<" native_faults="<<native_faults<<" weight_faults="<<weight_faults<<" cycles="<<cycle<<"\n";t.final();top.reset();return 0;
}catch(const std::exception&e){std::cerr<<"FAIL "<<e.what()<<"\n";top.reset();return 1;}}
