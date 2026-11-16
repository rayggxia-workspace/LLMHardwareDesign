#include "Vm_leaf_test_top.h"
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
using V4=std::array<uint32_t,4>;using V8=std::array<uint32_t,8>;using V16=std::array<uint32_t,16>;using F=std::array<V4,8>;
struct R{int id=0,n=8,scope=0,sg=0,bank=-1,gen=0,observed_bank=-1,observed_generation=0,epoch=0,read=0;bool head=false,fill=false,input=false,complete=false,descriptor_live=false,descriptor_closed=false;uint64_t base=0;uint32_t alloc_session=0,exec_session=0,ticket=0;V8 bias{},final{};std::vector<V8>prefix;std::array<V8,8>a{};std::vector<V16>dma;std::array<bool,18>issued{},returned{};};
struct E{int kind=0,scope=0,owner=0,full=0,next=0,group=0,n=0;uint32_t session=0,record=0,ticket=0;bool snapshot=false,error=false;V8 data{};};
struct Return{R*r;int beat;uint32_t tag;int due;};
std::unique_ptr<Vm_leaf_test_top>top;
#define t (*top)
std::mt19937 rng;std::ofstream trace;
std::deque<R>extras;std::vector<R*>records;R*reading=nullptr;
std::deque<Return>pending;Return returning{};bool return_live=false,duplicate_return=false;
std::map<uint32_t,E>rf_expected,guard_commands,committed;std::deque<E>terminals;
std::map<std::pair<uint32_t,int>,V16>received;
std::array<int,16>scope_gen{};std::array<int,2>outstanding{},descriptors{};
uint32_t last_input_session=0,last_rf_ticket=0;
int cycle=0,mc_accepted=0,mc_returned=0,Aaccepted=0,responses=0,RFcomplete=0,Sacks=0,peak_results=0,native_issues=0,faults=0,peak_credit=0;
uint32_t sequence=1;bool pause_RF=false,pause_S=false,pause_returns=false,force_A=false,force_MC=false,inject_bad_A=false,ideal=false;
bool pause_CLOSE=false,close_held=false;uint32_t close_tag=0;
bool f_lc=false,f_gu=false;bool lr_active=false;int lr_index=0,lr_length=0;V16 lr_frame{};
bool req_held=false,lr_held=false;uint64_t req_address=0;uint32_t req_tag=0;int req_channel=0,req_beats=0;V4 held_lr{};bool held_sop=false,held_eop=false;
struct Ack{bool live=false;V16 ticket{};int word=0,due=0;}ack;
bool fence_live=false;uint32_t fence_cookie=0;int fence_epoch=0,fence_due=0;
void need(bool b,const std::string&m){if(!b)throw std::runtime_error(m+" cycle="+std::to_string(cycle));}
template<size_t N>std::array<uint32_t,N>hex(const std::string&s){std::array<uint32_t,N>v{};for(size_t n=0;n<N;++n){size_t end=s.size()>n*8?s.size()-n*8:0,begin=end>8?end-8:0;if(end)v[n]=uint32_t(std::stoul(s.substr(begin,end-begin),nullptr,16));}return v;}
template<class P,size_t N>void put(P&p,const std::array<uint32_t,N>&v){for(size_t i=0;i<N;++i)p[i]=v[i];}
template<class P,size_t N>bool eq(const P&p,const std::array<uint32_t,N>&v){for(size_t i=0;i<N;++i)if(p[i]!=v[i])return false;return true;}
V4 key(){return {0x101,1,0x250,1};}V4 owner(int id){return {uint32_t(id),1,0x250,2};}
template<size_t N>void bits(std::array<uint32_t,N>&v,int at,int count,uint64_t x){for(int b=0;b<count;++b)if((x>>b)&1U)v[size_t((at+b)/32)]|=1U<<((at+b)%32);}
uint64_t field(const V16&v,int at,int count){uint64_t x=0;for(int b=0;b<count;++b)if((v[size_t((at+b)/32)]>>((at+b)%32))&1U)x|=uint64_t(1)<<b;return x;}
V16 guard_ticket(const E&e){V16 v{};bits(v,0,3,e.kind);bits(v,3,4,e.scope);bits(v,7,32,e.record);bits(v,39,32,e.ticket);auto k=key(),o=owner(e.owner);for(int i=0;i<4;++i){bits(v,71+i*32,32,e.record?k[size_t(i)]:0);bits(v,199+i*32,32,o[size_t(i)]);}return v;}
R*find_record(uint32_t id){for(auto*r:records)if(uint32_t(r->id)==id)return r;return nullptr;}
void check_RF(const V16&frame){int status=int(field(frame,40,8));uint32_t session=uint32_t(field(frame,48,32));auto it=rf_expected.find(session);need(it!=rf_expected.end(),"unknown RF session");auto e=it->second;
 need(uint32_t(field(frame,80,32))==e.record&&bool(status)==e.error,"RF record/error identity");need(int(field(frame,128,4))==e.scope,"RF context");
 need(int(field(frame,144,16))==(e.error?0:e.next)&&int(field(frame,160,16))==(e.error?0:e.full)&&int(field(frame,136,8))==(e.error?0:e.group)&&int(field(frame,132,4))==(e.error?0:e.n),"owned RF cursor/shape");
 need(uint32_t(field(frame,176,32))==e.ticket&&bool(field(frame,112,1))==e.snapshot,"RF ticket/snapshot policy");
 if(e.snapshot){for(int i=0;i<8;++i)need(frame[size_t(8+i)]==e.data[size_t(i)],"public actual-scaled result payload");}
 if(e.record){auto*r=find_record(e.record);need(r!=nullptr,"missing W owner");need(int(field(frame,208,2))==r->bank&&int(field(frame,210,16))==r->gen,"early W reuse corrupted RF result");r->complete=true;}
 rf_expected.erase(it);++RFcomplete;
}
void receive(const V16&frame){int event=int(field(frame,32,8)),status=int(field(frame,40,8));uint32_t session=uint32_t(field(frame,48,32)),record=uint32_t(field(frame,80,32));need(field(frame,0,32)==0x02504d02,"response ABI");
 received[{session,event}]=frame;++responses;trace<<"RESPONSE,"<<cycle<<","<<event<<","<<session<<","<<record<<","<<status<<","<<lr_length<<"\n";
 if(event==7){if(status>=13&&status<=15){need(session==0&&record==0,"unowned transport fault blamed a live job");for(int i=8;i<12;++i)need(frame[size_t(i)]==0,"unowned transport fault borrowed current key");}++faults;return;}need(status==0||event==4,"unexpected source error");
 if(event==1){auto*r=find_record(record);need(r&&r->alloc_session==session,"ALLOC session");r->bank=int(field(frame,128,2));r->gen=int(field(frame,130,16));}
 if(event==2){auto*r=find_record(record);need(r&&r->alloc_session==session,"FILL session");r->fill=true;}
 if(event==3){auto*r=find_record(record);need(r&&r->exec_session==session&&r->read==8,"real input lease release");r->input=true;}
 if(event==4)check_RF(frame);
 if(event==6){auto*r=find_record(record);need(r&&!r->descriptor_live&&r->descriptor_closed,"DRAIN before actual global CLOSE/return");for(size_t i=0;i<r->dma.size();++i)need(r->issued[i]==r->returned[i],"DRAIN before true return");}
}
void tick(){
 t.clk=0;t.a_valid=reading&&reading->read<8&&!force_A&&(ideal||cycle%7!=0);if(t.a_valid){put(t.a_data,reading->a[size_t(reading->read)]);t.a_session=reading->exec_session+(inject_bad_A?1:0);t.a_beat=reading->read;}
 t.mc_req_ready=!force_MC&&(ideal||cycle%5!=0)&&outstanding[0]<32&&outstanding[1]<32;
 if(!pause_returns&&!return_live&&!pending.empty()){std::vector<size_t>due;for(size_t i=0;i<pending.size();++i)if(pending[i].due<=cycle)due.push_back(i);if(!due.empty()){size_t i=due[rng()%due.size()];returning=pending[i];pending.erase(pending.begin()+long(i));return_live=true;}}
 t.mc_rsp_valid=return_live;if(return_live){t.mc_rsp_tag=returning.tag;put(t.mc_rsp_data,returning.r->dma[size_t(returning.beat)]);}
 t.mc_close_ready=!pause_CLOSE;t.mc_fence_req_ready=1;t.mc_fence_done_valid=fence_live&&cycle>=fence_due;t.mc_fence_done_cookie=fence_cookie;t.mc_fence_done_epoch=fence_epoch;
 t.gu_native_ready=1;t.gu_s_ready=!pause_S&&(ideal||cycle%5!=0);t.gu_terminal_ready=ideal||cycle%11<8;t.gu_ack_valid=ack.live&&!pause_S&&cycle>=ack.due;put(t.gu_ack_ticket,ack.ticket);t.gu_ack_word=ack.word;t.gu_ack_error=0;
 t.gu_result_valid=0;t.lr_ready=ideal||cycle%7!=0;t.eval();
 int event=lr_active?int(field(lr_frame,32,8)):(t.lr_valid?int((t.lr_data[1])&255U):0);
 if(pause_RF&&event==4)t.lr_ready=0;
 V16 candidate=lr_frame;if(t.lr_valid){for(int i=0;i<4;++i)candidate[size_t(lr_index*4+i)]=t.lr_data[i];}
 if(t.lr_valid&&t.lr_eop&&event==4){uint32_t session=uint32_t(field(candidate,48,32));auto it=rf_expected.find(session);need(it!=rf_expected.end(),"RF EOP session not registered");auto&e=it->second;put(t.gu_result_ticket,guard_ticket(e));V8 data{};if(e.snapshot)for(int i=0;i<8;++i)data[size_t(i)]=candidate[size_t(8+i)];put(t.gu_result_data,data);t.gu_result_error=field(candidate,40,8)!=0;t.gu_result_valid=t.lr_ready;t.lr_ready=t.lr_ready&&t.gu_result_ready;}
 t.eval();f_lc=t.lc_valid&&t.lc_ready;f_gu=t.gu_cmd_valid&&t.gu_cmd_ready;
 if(!t.reset){
  if(close_held){need(t.mc_close_valid&&t.mc_close_tag_base==close_tag,"CLOSE changed under backpressure");}close_held=t.mc_close_valid&&!t.mc_close_ready;close_tag=t.mc_close_tag_base;
  if(req_held){need(t.mc_req_valid&&uint64_t(t.mc_req_address)==req_address&&t.mc_req_tag==req_tag&&t.mc_req_channel==req_channel&&t.mc_req_record_beats==req_beats,"MC request changed under backpressure");}req_held=t.mc_req_valid&&!t.mc_req_ready;req_address=t.mc_req_address;req_tag=t.mc_req_tag;req_channel=t.mc_req_channel;req_beats=t.mc_req_record_beats;
  if(lr_held){need(t.lr_valid&&eq(t.lr_data,held_lr)&&bool(t.lr_sop)==held_sop&&bool(t.lr_eop)==held_eop,"response flit changed under backpressure");}lr_held=t.lr_valid&&!t.lr_ready;for(int i=0;i<4;++i)held_lr[size_t(i)]=t.lr_data[i];held_sop=t.lr_sop;held_eop=t.lr_eop;
  if(f_lc)trace<<"LC,"<<cycle<<","<<int(t.lc_sop)<<","<<int(t.lc_eop)<<","<<((t.lc_data[0]>>16)&15U)<<","<<t.lc_data[1]<<"\n";
  if(t.dbg_exec_fire)trace<<"CORE_EXEC,"<<cycle<<","<<t.dbg_exec_session<<"\n";
  if(t.dbg_control_fire)trace<<"CORE_CONTROL,"<<cycle<<","<<t.dbg_control_session<<","<<int(t.dbg_control_kind)<<"\n";
  if(t.dbg_input_valid&&last_input_session!=t.dbg_input_session){last_input_session=t.dbg_input_session;trace<<"CORE_INPUT,"<<cycle<<","<<t.dbg_input_session<<"\n";}
  if(t.dbg_rf_valid&&last_rf_ticket!=t.dbg_rf_ticket){last_rf_ticket=t.dbg_rf_ticket;trace<<"CORE_RF,"<<cycle<<","<<t.dbg_rf_ticket<<","<<t.dbg_rf_record<<"\n";}
  if(t.a_valid&&t.a_ready&&!inject_bad_A){++reading->read;++Aaccepted;trace<<"A,"<<cycle<<","<<reading->id<<","<<reading->exec_session<<","<<reading->read-1<<"\n";}
  if(t.mc_req_valid&&t.mc_req_ready){uint64_t address=t.mc_req_address;R*r=nullptr;for(auto*p:records)if(address>=p->base&&address<p->base+p->dma.size()*64){r=p;break;}need(r!=nullptr,"DMA address not in exact deployed record");int beat=int((address-r->base)/64),ch=int((r->base/2048)%2);need(beat>=0&&beat<int(r->dma.size())&&!r->issued[size_t(beat)],"DMA duplicate/beat");need(int(t.mc_req_channel)==ch&&t.mc_req_record_beats==r->dma.size(),"record stripe/burst length");need((t.mc_req_tag&31U)==uint32_t(beat),"DMA tag beat");
   if(beat==0){need(!r->descriptor_live,"duplicate descriptor");r->descriptor_live=true;r->descriptor_closed=false;++descriptors[size_t(ch)];r->epoch=int(t.mc_req_tag>>23);r->observed_bank=int((t.mc_req_tag>>21)&3U);r->observed_generation=int((t.mc_req_tag>>5)&65535U);}r->issued[size_t(beat)]=true;if(beat==int(r->dma.size())-1)r->descriptor_closed=true;++outstanding[size_t(ch)];need(outstanding[size_t(ch)]<=32&&descriptors[size_t(ch)]<=32,"real channel credit overflow");peak_credit=std::max(peak_credit,outstanding[0]+outstanding[1]);pending.push_back({r,beat,t.mc_req_tag,cycle+9});++mc_accepted;trace<<"MC_REQ,"<<cycle<<","<<r->id<<","<<beat<<","<<ch<<","<<t.mc_req_tag<<"\n";}
  if(t.mc_rsp_valid&&t.mc_rsp_ready){if(!duplicate_return){auto&r=*returning.r;r.returned[size_t(returning.beat)]=true;int ch=int((r.base/2048)%2);--outstanding[size_t(ch)];if(r.descriptor_closed&&std::equal(r.issued.begin(),r.issued.end(),r.returned.begin())){--descriptors[size_t(ch)];r.descriptor_live=false;}++mc_returned;}trace<<"MC_RETURN,"<<cycle<<","<<returning.r->id<<","<<returning.beat<<","<<int(duplicate_return)<<"\n";return_live=false;duplicate_return=false;}
  if(t.mc_close_valid&&t.mc_close_ready){R*r=nullptr;for(auto*p:records)if(p->descriptor_live&&p->observed_bank==int((t.mc_close_tag_base>>21)&3U)&&p->observed_generation==int((t.mc_close_tag_base>>5)&65535U)&&p->epoch==int(t.mc_close_tag_base>>23)){need(r==nullptr,"ambiguous global descriptor");r=p;}need(r&&!(t.mc_close_tag_base&31U)&&!r->descriptor_closed,"CLOSE owner/duplicate");r->descriptor_closed=true;if(std::equal(r->issued.begin(),r->issued.end(),r->returned.begin())){--descriptors[size_t((r->base/2048)%2)];r->descriptor_live=false;}trace<<"MC_CLOSE,"<<cycle<<","<<r->id<<","<<t.mc_close_tag_base<<"\n";}
  if(t.lr_valid&&t.lr_ready){if(t.lr_sop){need(!lr_active&&lr_index==0,"response SOP nesting");lr_length=int((t.lr_data[3]>>28)&15U);need(lr_length>=2&&lr_length<=4,"bounded response length");lr_active=true;}need(lr_active&&bool(t.lr_eop)==(lr_index==lr_length-1),"response exact EOP");lr_frame=candidate;trace<<"LR,"<<cycle<<","<<event<<","<<lr_index<<","<<lr_length<<"\n";if(t.lr_eop){receive(lr_frame);lr_frame={};lr_index=0;lr_active=false;}else ++lr_index;}
  if(t.gu_native_valid&&t.gu_native_ready)++native_issues;
  if(t.gu_s_valid&&t.gu_s_ready){need(!ack.live,"more than one actual S word outstanding");V16 id{};for(int i=0;i<16;++i)id[size_t(i)]=t.gu_s_ticket[i];uint32_t tid=uint32_t((uint64_t(id[1])>>7)|(uint64_t(id[2])<<25));auto it=guard_commands.find(tid);need(it!=guard_commands.end()&&it->second.snapshot,"partial RF write escaped to S");auto&e=it->second;need(eq(t.gu_s_ticket,guard_ticket(e)),"actual S request identity");int word=t.gu_s_word;for(int i=0;i<4;++i)need(t.gu_s_data[i]==e.data[size_t(word*4+i)],"actual S word data");ack={true,id,word,cycle+(ideal?2:3+int(rng()%7))};trace<<"S_REQ,"<<cycle<<","<<e.ticket<<","<<word<<"\n";}
  if(t.gu_ack_valid&&t.gu_ack_ready){ack.live=false;++Sacks;trace<<"S_ACK,"<<cycle<<","<<ack.word<<"\n";}
  if(t.gu_terminal_valid&&t.gu_terminal_ready){need(!terminals.empty(),"unexpected guard terminal");auto e=terminals.front();terminals.pop_front();V8 expected=e.snapshot?e.data:V8{};need(eq(t.gu_terminal_ticket,guard_ticket(e))&&eq(t.gu_terminal_data,expected),"guard terminal identity/data");need(bool(t.gu_terminal_stored)==e.snapshot&&bool(t.gu_terminal_error)==e.error,"guard actual ACK/error policy");if(e.snapshot)committed[e.ticket]=e;trace<<"TERMINAL,"<<cycle<<","<<e.ticket<<","<<int(e.snapshot)<<"\n";}
  peak_results=std::max(peak_results,int(t.gu_result_count));need(t.gu_count<=2&&t.gu_result_count<=2,"unbounded guard queue");
  if(t.mc_fence_req_valid&&t.mc_fence_req_ready){need(!fence_live&&pending.empty()&&!return_live&&outstanding[0]==0&&outstanding[1]==0,"fence before true MC drain");fence_live=true;fence_cookie=t.mc_fence_req_cookie;fence_epoch=t.mc_fence_req_epoch;fence_due=cycle+4;}
  if(t.mc_fence_done_valid&&t.mc_fence_done_ready)fence_live=false;
 }
 t.clk=1;t.eval();t.clk=0;t.eval();++cycle;
}
template<class X>void wait(X x,const std::string&m){for(int k=0;k<100000;++k){if(x())return;tick();}throw std::runtime_error(m+" cycle="+std::to_string(cycle));}
F frame(int op,int words,int scope,int generation,uint32_t session,uint32_t record=0,int bank=0,int high=0){F f{};f[0]={uint32_t(0x4d02|(op<<16)|(words<<20)|(scope<<24)|(bank<<28)),session,record,uint32_t(generation|(high<<16))};return f;}
void send(const F&f,int words){for(int word=0;word<words;++word){t.lc_valid=1;t.lc_sop=word==0;t.lc_eop=word==words-1;put(t.lc_data,f[size_t(word)]);do{tick();}while(!f_lc);}t.lc_valid=0;t.lc_sop=t.lc_eop=0;}
void wait_event(uint32_t session,int event){wait([&]{return received.count({session,event})!=0;},"response event "+std::to_string(event));}
void begin_scope(R&r,int scope,int owner_id,int full=128){r.scope=scope;r.sg=++scope_gen[size_t(scope)];uint32_t sid=sequence++;auto f=frame(1,8,scope,r.sg,sid);f[1]=key();f[2]=owner(owner_id);f[3][0]=uint32_t(full|(r.n<<16)|(int(r.head)<<20));for(int i=0;i<8;++i)f[size_t(5+i/4)][size_t(i%4)]=r.bias[size_t(i)];f[7][0]=0x53333251;f[7][1]=0x4b313633;send(f,8);wait_event(sid,10);}
void guard_command(const E&e){rf_expected[e.session]=e;guard_commands[e.ticket]=e;put(t.gu_cmd_ticket,guard_ticket(e));put(t.gu_cmd_key,key());t.gu_cmd_stored=e.snapshot;t.gu_cmd_destination=(e.ticket%400)*2;t.gu_cmd_valid=1;int goal=native_issues+1;do{tick();}while(!f_gu);t.gu_cmd_valid=0;terminals.push_back(e);wait([&]{return native_issues>=goal;},"actual guard command acceptance");}
void context(R&r,int owner_id,int kind,int full=128,int offset=0,const V8&value={},bool error=false,const E*proof=nullptr){uint32_t sid=sequence++;E e;e.kind=kind;e.scope=r.scope;e.owner=owner_id;e.session=sid;e.ticket=sid;e.full=full;e.next=offset;e.group=r.head?16:128;e.n=r.n;e.snapshot=kind==3&&!error;e.error=error;e.data=value;guard_command(e);
 auto f=frame(kind==1?5:4,kind==1?8:1,r.scope,r.sg,sid,0,0,kind==1?0:kind);
 if(kind==1){f[1]=owner(owner_id);f[2]=owner(owner_id);f[3][0]=uint32_t(offset|(full<<16));f[3][1]=uint32_t((r.head?16:128)|(r.n<<8));for(int i=0;i<8;++i)f[size_t(5+i/4)][size_t(i%4)]=value[size_t(i)];if(proof){f[4][0]=proof->ticket;bits(f[7],0,32,proof->ticket);bits(f[7],32,1,1);bits(f[7],33,4,r.scope);bits(f[7],37,16,offset);bits(f[7],53,16,full);bits(f[7],69,8,r.head?16:128);bits(f[7],77,4,r.n);}}
 send(f,kind==1?8:1);wait_event(sid,4);
}
void allocate(R&r){r.alloc_session=sequence++;r.base=0x100000ULL+uint64_t(r.id)*4096+(r.id%2?1984:2048);records.push_back(&r);auto f=frame(2,2,r.scope,r.sg,r.alloc_session,r.id);f[1][0]=uint32_t(r.base);f[1][1]=uint32_t(r.base>>32);send(f,2);}
void execute(R&r,int owner_id,int full=128,int offset=0,const V8*expected=nullptr){r.exec_session=sequence++;r.ticket=r.exec_session;r.read=0;r.input=r.complete=false;E e;e.kind=2;e.scope=r.scope;e.owner=owner_id;e.full=full;e.next=offset+128;e.group=r.head?16:128;e.n=r.n;e.session=r.exec_session;e.record=r.id;e.ticket=r.ticket;e.snapshot=offset+128==full;e.data=expected?*expected:r.final;guard_command(e);auto f=frame(3,2,r.scope,r.sg,r.exec_session,r.id);bits(f[1],0,2,r.bank);bits(f[1],2,16,r.gen);bits(f[1],18,16,r.id+17);bits(f[1],34,16,offset);bits(f[1],50,16,offset/128);bits(f[1],66,1,r.id&1);bits(f[1],67,16,r.id+3);bits(f[1],83,6,8);bits(f[1],89,32,r.ticket);send(f,2);reading=&r;}
void done(R&r){wait([&]{return r.complete&&r.input;},"product real record completion");reading=nullptr;}
int main(int argc,char**argv){try{need(argc==6,"usage records leaf seed initial trace");rng.seed(uint32_t(std::stoul(argv[3])));Verilated::randReset(std::stoi(argv[4]));Verilated::randSeed(int(std::stoul(argv[3])));top=std::make_unique<Vm_leaf_test_top>();trace.open(argv[5]);
 std::ifstream f(argv[1]),g(argv[2]);int count,other;f>>count;g>>other;need(count==34&&other==34,"public fixture count");std::vector<R>rs(size_t(count),R{});std::string s;
 for(auto&r:rs){int h,id;f>>h>>r.n>>r.id;r.head=h;for(int b=0;b<(r.head?18:17);++b){f>>s;r.dma.push_back(hex<16>(s));}for(auto&a:r.a){f>>s;a=hex<8>(s);}for(int k=0;k<16+(r.head?8:1);++k)f>>s;g>>id;need(id==r.id,"leaf oracle record");g>>s;r.bias=hex<8>(s);for(int k=0;k<(r.head?8:1);++k){g>>s;r.prefix.push_back(hex<8>(s));}g>>s;r.final=hex<8>(s);}
 V8 cross_o{},cross_h{};g>>s;cross_o=hex<8>(s);g>>s;cross_h=hex<8>(s);need(bool(f)&&bool(g),"fixture parse");t.lc_valid=0;t.gu_cmd_valid=0;t.reset=1;for(int k=0;k<4;++k)tick();t.reset=0;
 for(int i=0;i<6;++i){begin_scope(rs[size_t(i)],i,100+i);context(rs[size_t(i)],100+i,0);}wait([]{return t.gu_count==0;},"initial CREATE drain");
 pause_returns=true;for(int i=0;i<4;++i){allocate(rs[size_t(i)]);}wait([]{return outstanding[0]+outstanding[1]==32;},"private MC credit cap exercised");int issued_at_cap=mc_accepted;for(int k=0;k<4;++k){tick();need(mc_accepted==issued_at_cap,"native private credit cap ignored");}pause_returns=false;
 for(int i=0;i<4;++i){wait([&]{return rs[size_t(i)].fill;},"initial actual DMA fill");}pause_S=true;
 for(int i=0;i<count;++i){auto&r=rs[size_t(i)];if(i>=6&&r.sg==0){begin_scope(r,i%16,100+i);context(r,100+i,0);}
  if(i==1){pause_RF=true;}execute(r,100+i);
  if(i==1){wait([&]{return r.input;},"serialized input ACK");wait([]{return t.lr_valid&&((t.lr_data[1]&255U)==4);},"held product RF header");allocate(rs[5]);wait([&]{return std::all_of(rs[5].returned.begin(),rs[5].returned.begin()+long(rs[5].dma.size()),[](bool x){return x;});},"same bank overwrite behind blocked response");need(rs[5].gen==0||rs[5].bank==-1,"unreported allocation should not have fake ACK");need(rs[5].observed_bank==r.bank&&rs[5].observed_generation!=r.gen,"held RF did not survive actual same-bank refill");pause_RF=false;pause_S=false;}
  done(r);
  if(i==0){allocate(rs[4]);wait([&]{return rs[4].fill;},"prefill bank0");int prior=faults;auto&old=rs[0];need(rs[4].bank==old.bank&&rs[4].gen!=old.gen,"stale owner case requires actual same-bank reuse");returning={&old,0,uint32_t((old.epoch<<23)|(old.observed_bank<<21)|(old.observed_generation<<5)),cycle};return_live=true;duplicate_return=true;wait([&]{return faults==prior+1;},"old return while new owner READY");}
  if(i>=2&&i+4<count&&rs[size_t(i+4)].alloc_session==0){auto&future=rs[size_t(i+4)];if(i+4>=6){begin_scope(future,(i+4)%16,100+i+4);context(future,100+i+4,0);}allocate(future);wait([&]{return future.fill;},"future real fill");}
  if(i+1<count&&rs[size_t(i+1)].alloc_session!=0)wait([&]{return rs[size_t(i+1)].fill;},"next record ready");
 }
 wait([]{return t.gu_count==0&&!ack.live;},"all real S ACKs");need(peak_results==2,"actual two-result guard did not fill");
 // Scope reuse across two explicit source-slice records, not a claim of
 // adjacent K coordinates in the public model. Actual state and scale math.
 for(int h=0;h<2;++h){extras.push_back(rs[size_t(h?24:0)]);auto&first=extras.back();first.id=3000+h*10;first.issued.fill(false);first.returned.fill(false);first.fill=false;first.alloc_session=0;first.read=0;extras.push_back(rs[size_t(h?25:1)]);auto&second=extras.back();second.id=3001+h*10;second.issued.fill(false);second.returned.fill(false);second.fill=false;second.alloc_session=0;second.read=0;
  begin_scope(first,8+h,700+h,256);second.scope=first.scope;second.sg=first.sg;context(first,700+h,0,256);allocate(first);allocate(second);wait([&]{return first.fill&&second.fill;},"cross real DMA");execute(first,700+h,256,0,&first.prefix.back());done(first);wait([]{return t.gu_count==0;},"continue terminal");pause_S=true;context(first,700+h,3,256,128,first.prefix.back());uint32_t spill=sequence-1;
  context(first,700+h,1,256,128,V8{},true);need(committed.count(spill)==0,"snapshot restored before real S ACK");pause_S=false;wait([&]{return committed.count(spill)!=0;},"snapshot actual S ACK proof");auto proof=committed[spill];context(first,700+h,1,256,128,proof.data,false,&proof);execute(second,700+h,256,128,h?&cross_h:&cross_o);done(second);
 }
 // Product aperture timings use real command and response flits, not the
 // internal twelve-cycle arithmetic number. One ordinary and one head scope.
 ideal=true;
 for(int h=0;h<2;++h){extras.push_back(rs[size_t(h?24:0)]);auto&r=extras.back();r.id=5000+h;r.issued.fill(false);r.returned.fill(false);r.fill=false;r.descriptor_live=false;r.alloc_session=0;r.read=0;begin_scope(r,12+h,900+h);context(r,900+h,0);allocate(r);wait([&]{return r.fill;},"ideal product fill");trace<<"IDEAL_RECORD,"<<cycle<<","<<r.id<<"\n";execute(r,900+h);done(r);wait([]{return t.gu_count==0;},"ideal real S ACK drain");}
 // Isolate actual CONTINUE, SPILL and true-ACK RESTORE framing as well.
 extras.push_back(rs[0]);auto&ip=extras.back();ip.id=5010;ip.issued.fill(false);ip.returned.fill(false);ip.fill=false;ip.descriptor_live=false;ip.alloc_session=0;ip.read=0;
 extras.push_back(rs[1]);auto&iq=extras.back();iq.id=5011;iq.issued.fill(false);iq.returned.fill(false);iq.fill=false;iq.descriptor_live=false;iq.alloc_session=0;iq.read=0;
 begin_scope(ip,14,920,256);iq.scope=ip.scope;iq.sg=ip.sg;context(ip,920,0,256);allocate(ip);allocate(iq);wait([&]{return ip.fill&&iq.fill;},"ideal split DMA");execute(ip,920,256,0,&ip.prefix.back());done(ip);wait([]{return t.gu_count==0;},"ideal RF-only completion");context(ip,920,3,256,128,ip.prefix.back());uint32_t ips=sequence-1;wait([&]{return committed.count(ips)!=0;},"ideal snapshot real ACK");auto ipp=committed[ips];context(ip,920,1,256,128,ipp.data,false,&ipp);execute(iq,920,256,128,&cross_o);done(iq);wait([]{return t.gu_count==0;},"ideal restore final ACK");
 // Head continuation and real queued next-EXEC: eight independent RNEs
 // per K128 record, one finite pending command, no result or A FIFO added.
 extras.push_back(rs[24]);auto&hp=extras.back();hp.id=5020;hp.issued.fill(false);hp.returned.fill(false);hp.fill=false;hp.descriptor_live=false;hp.alloc_session=0;hp.read=0;
 extras.push_back(rs[25]);auto&hq=extras.back();hq.id=5021;hq.issued.fill(false);hq.returned.fill(false);hq.fill=false;hq.descriptor_live=false;hq.alloc_session=0;hq.read=0;
 begin_scope(hp,11,930,256);hq.scope=hp.scope;hq.sg=hp.sg;context(hp,930,0,256);allocate(hp);allocate(hq);wait([&]{return hp.fill&&hq.fill;},"ideal head continuation DMA");execute(hp,930,256,0,&hp.prefix.back());wait([&]{return hp.input;},"head first true input ACK");execute(hq,930,256,128,&cross_h);done(hq);need(hp.complete,"queued head EXEC lost first RF commit");wait([]{return t.gu_count==0;},"queued head final true S ACK");
 // A duplicate and an old-epoch DMA return must consume neither a data bank
 // nor a real MC credit. Unknown A cannot enter M. Invalid frames recover.
 int fault_goal=faults;
 auto&old=rs[0];returning={&old,0,uint32_t((old.epoch<<23)|(old.observed_bank<<21)|(old.observed_generation<<5)),cycle};return_live=true;duplicate_return=true;wait([&]{return faults==fault_goal+1;},"duplicate DMA fault");++fault_goal;
 returning={&old,0,uint32_t(((old.epoch^1)<<23)|(old.observed_bank<<21)|(old.observed_generation<<5)),cycle};return_live=true;duplicate_return=true;wait([&]{return faults==fault_goal+1;},"stale epoch DMA fault");++fault_goal;
 old.read=0;reading=&old;inject_bad_A=true;tick();reading=nullptr;inject_bad_A=false;wait([&]{return faults==fault_goal+1;},"unknown A session fault");++fault_goal;
 // Two malformed transports share one diagnostic slot: bad A wins,
 // bad MC remains VALID until its own real acceptance and response.
 returning={&old,0,uint32_t((old.epoch<<23)|(old.observed_bank<<21)|(old.observed_generation<<5)),cycle};return_live=true;duplicate_return=true;
 old.read=0;reading=&old;inject_bad_A=true;tick();need(return_live,"bad MC consumed alongside the sole A diagnostic");reading=nullptr;inject_bad_A=false;
 wait([&]{return faults==fault_goal+2;},"concurrent bad A and MC bounded diagnostics");fault_goal+=2;
 // A complete stale command and a bad MC return can each own their separate
 // finite reply slot without overwriting either frame or stalling dispatch.
 uint32_t both=sequence++;send(frame(3,2,12,scope_gen[12]-1,both,5000),2);
 returning={&old,0,uint32_t((old.epoch<<23)|(old.observed_bank<<21)|(old.observed_generation<<5)),cycle};return_live=true;duplicate_return=true;
 wait([&]{return faults==fault_goal+2;},"command reply and transport diagnostic coexist");wait_event(both,7);fault_goal+=2;
 uint32_t bad=sequence++;send(frame(15,1,0,0,bad),1);wait_event(bad,7);need(faults==fault_goal+1,"bad opcode frame fault");++fault_goal;
 bad=sequence++;send(frame(3,2,12,scope_gen[12]-1,bad,5000),2);wait_event(bad,7);need(faults==fault_goal+1,"stale scope generation fault");
 // Cancellation cannot withdraw a held MC request. Its one already offered
 // beat still returns; DRAIN completes only after this true return.
 extras.push_back(rs[0]);auto&cancel=extras.back();cancel.id=6000;cancel.issued.fill(false);cancel.returned.fill(false);cancel.fill=false;cancel.descriptor_live=false;cancel.alloc_session=0;cancel.read=0;begin_scope(cancel,15,950);pause_CLOSE=true;force_MC=true;allocate(cancel);wait_event(cancel.alloc_session,1);wait([]{return bool(t.mc_req_valid);},"held cancellation DMA");tick();uint32_t cs=sequence++;send(frame(6,1,cancel.scope,cancel.sg,cs,cancel.id,cancel.bank,cancel.gen),1);for(int k=0;k<3;++k)tick();need(received.count({cs,9})==0,"cancel withdrew offered DMA");force_MC=false;wait_event(cs,9);wait([]{return pending.empty()&&!return_live;},"canceled offered beat returned");need(std::count(cancel.issued.begin(),cancel.issued.end(),true)==1,"cancel issued unoffered suffix");uint32_t ds=sequence++;send(frame(7,1,cancel.scope,cancel.sg,ds,cancel.id,cancel.bank,cancel.gen),1);for(int k=0;k<5;++k)tick();need(received.count({ds,6})==0&&cancel.descriptor_live,"last return falsely implied global CLOSE");pause_CLOSE=false;wait_event(ds,6);
 // Product cancellation after three real head K16 operands. This EXEC
 // is an abort control service, not a normal RF4 guard command. ABORT5
 // returns its actual prefix cursor; a later ordinary SPILL uses the real
 // guard and two true S ACKs to verify the independent third RNE prefix.
 extras.push_back(rs[24]);auto&partial=extras.back();partial.id=7000;partial.issued.fill(false);partial.returned.fill(false);partial.fill=false;partial.descriptor_live=false;partial.alloc_session=0;partial.read=0;partial.input=false;partial.complete=false;
 begin_scope(partial,6,970);context(partial,970,0);wait([]{return t.gu_count==0;},"partial CREATE guard drain");allocate(partial);wait([&]{return partial.fill;},"partial real W fill");
 partial.exec_session=sequence++;partial.ticket=partial.exec_session;
 auto pf=frame(3,2,partial.scope,partial.sg,partial.exec_session,partial.id);bits(pf[1],0,2,partial.bank);bits(pf[1],2,16,partial.gen);bits(pf[1],18,16,partial.id+17);bits(pf[1],67,16,partial.id+3);bits(pf[1],83,6,8);bits(pf[1],89,32,partial.ticket);send(pf,2);reading=&partial;
 wait([&]{return partial.read==3;},"three real partial operands");force_A=true;
 uint32_t pcs=sequence++;send(frame(6,1,partial.scope,partial.sg,pcs,partial.id,partial.bank,partial.gen),1);wait_event(pcs,9);wait_event(partial.exec_session,5);
 auto abort_frame=received.at({partial.exec_session,5});need(field(abort_frame,128,4)==uint64_t(partial.scope)&&field(abort_frame,144,16)==48,"actual abort prefix cursor/context");auto pk=key(),po=owner(970);for(int i=0;i<4;++i)need(abort_frame[size_t(8+i)]==pk[size_t(i)]&&abort_frame[size_t(12+i)]==po[size_t(i)],"actual abort full key/owner");
 need(partial.read==3&&!partial.input&&!partial.complete,"partial cancellation fabricated full input/result completion");trace<<"ABORT_PARTIAL,"<<cycle<<","<<partial.id<<",3,48\n";reading=nullptr;force_A=false;
 uint32_t pds=sequence++;send(frame(7,1,partial.scope,partial.sg,pds,partial.id,partial.bank,partial.gen),1);wait_event(pds,6);
 context(partial,970,3,128,48,partial.prefix[2]);uint32_t pspill=sequence-1;wait([&]{return committed.count(pspill)!=0&&t.gu_count==0;},"partial exact prefix SPILL true S ACK");
 wait([]{return t.gu_count==0&&pending.empty()&&!return_live&&!ack.live;},"fence preconditions");uint32_t sid=sequence++;send(frame(8,1,0,0,sid),1);wait_event(sid,8);
 need(mc_accepted==mc_returned&&outstanding[0]==0&&outstanding[1]==0&&descriptors[0]==0&&descriptors[1]==0,"real DDR conservation");need(t.gu_rejected==0&&rf_expected.empty(),"guard/response ownership leak");
 std::cout<<"PASS leaf public_records=34 MC64requests="<<mc_accepted<<" MC64returns="<<mc_returned<<" Abeats="<<Aaccepted<<" RFcompletions="<<RFcomplete<<" responses="<<responses<<" S128ACKs="<<Sacks<<" peak_guard_results="<<peak_results<<" peak_private_credit="<<peak_credit<<" faults="<<faults<<" cycles="<<cycle<<"\n";t.final();top.reset();return 0;
}catch(const std::exception&e){std::cerr<<"FAIL "<<e.what()<<"\n";top.reset();return 1;}}
