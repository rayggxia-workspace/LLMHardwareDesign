#include "Vlocal_s_pool.h"
#include "verilated.h"
#include <array>
#include <cstdint>
#include <iostream>
#include <random>
#include <stdexcept>
#include <string>
#include <type_traits>

using Word=std::array<uint32_t,4>;
template<class T> void put(T& a,int bit,int width,uint32_t v){
 for(int i=0;i<width;i++){
  if constexpr(std::is_integral_v<T>){T m=T(1)<<(bit+i);if((v>>i)&1)a|=m;else a&=~m;}
  else {uint32_t m=uint32_t(1)<<((bit+i)%32);if((v>>i)&1)a[(bit+i)/32]|=m;else a[(bit+i)/32]&=~m;}
 }
}
template<class T> uint32_t get(const T& a,int bit,int width){
 uint32_t v=0;for(int i=0;i<width;i++){
  if constexpr(std::is_integral_v<T>)v|=uint32_t((a>>(bit+i))&1U)<<i;
  else v|=((a[(bit+i)/32]>>((bit+i)%32))&1U)<<i;
 }return v;
}
template<class T> Word word(const T& a,int bit){Word w{};for(int i=0;i<4;i++)w[i]=get(a,bit+32*i,32);return w;}
struct Request {bool valid=false,write=false;int addr=0;Word data{};};
struct Pending {bool valid=false,write=false,seen=false;int client=0,addr=0;Word expected{};};
struct Load {bool active=false,accepted=false;int rows=0,tiles=0,abase=0,bbase=0;
 bool aw=false,bw=false,reuse=false,bank=false;int acount=0,bcount=0;
 bool ahold=false,bhold=false;Word helda{};std::array<uint32_t,16> heldb{};
 uint32_t atag=0,btag=0;};
struct Bench {
 Vlocal_s_pool d;
 std::mt19937 rng;
 std::array<std::array<Word,1024>,9> memory{};
 std::array<std::array<Request,5>,9> requests{};
 std::array<Pending,9> pending{};
 std::array<Load,9> loads{};
 uint64_t checks=0,cycles=0,accepted=0,returned=0,wide_a=0,wide_b=0;
 std::array<std::array<uint64_t,5>,9> grants{};
 uint64_t response_ready=(uint64_t(1)<<45)-1;
 unsigned resetting=0,ar=511,br=511,dt=511;
 explicit Bench(unsigned seed):rng(seed){}
 int clients(int b) const{return b==5?5:4;}
 void check(bool v,const std::string& m){checks++;if(!v)throw std::runtime_error(m+" at cycle "+std::to_string(cycles));}
 Word pattern(int b,int addr){return {uint32_t(0x10000000+b),uint32_t(addr),uint32_t(b*1024+addr),uint32_t(0x9e3779b9U^(b<<16)^addr)};}
 Word random_word(){return {uint32_t(rng()),uint32_t(rng()),uint32_t(rng()),uint32_t(rng())};}
 bool quiet()const{for(int b=0;b<9;b++){if(pending[b].valid)return false;for(auto&r:requests[b])if(r.valid)return false;}return true;}
 void drive(){
  d.clk=0;d.reset=resetting;d.req_valid=0;d.req_write=0;d.rsp_ready=response_ready;
  d.load_valid=0;d.load_bank=0;d.load_a_wide=0;d.load_b_wide=0;d.load_reuse_b=0;
  d.a_ready=ar;d.b_ready=br;d.done_take=dt;
  for(int b=0;b<9;b++){
   for(int c=0;c<5;c++){auto&r=requests[b][c];int k=b*5+c;
    if(r.valid)d.req_valid|=uint64_t(1)<<k;if(r.write)d.req_write|=uint64_t(1)<<k;
    put(d.req_addr,k*10,10,r.addr);for(int q=0;q<4;q++)put(d.req_data,k*128+32*q,32,r.data[q]);
   }
   auto&l=loads[b];if(l.active&&!l.accepted)d.load_valid|=1U<<b;
   if(l.bank)d.load_bank|=1U<<b;if(l.aw)d.load_a_wide|=1U<<b;
   if(l.bw)d.load_b_wide|=1U<<b;if(l.reuse)d.load_reuse_b|=1U<<b;
   put(d.load_rows,b*4,4,l.rows);put(d.load_tiles,b*3,3,l.tiles);
   put(d.load_a_base,b*10,10,l.abase);put(d.load_b_base,b*10,10,l.bbase);
  }d.eval();
 }
 void tick(){
  drive();
  for(int b=0;b<9;b++){
   if((resetting>>b)&1){
    check(((d.req_ready>>(b*5))&31)==0,"ready during reset");
    check(((d.rsp_valid>>(b*5))&31)==0,"response during reset");
    check(!((d.a_valid|d.b_valid|d.done_valid)>>b&1),"feeder visible during reset");
    pending[b]={};loads[b]={};for(auto&r:requests[b])r={};continue;
   }
   int n=clients(b);if(n==4){check(!((d.req_ready>>(b*5+4))&1),"inactive client accepted");check(!((d.rsp_valid>>(b*5+4))&1),"inactive response");}
   int nr=0,ns=0;
   for(int c=0;c<5;c++){
    int k=b*5+c;
    if((d.req_ready>>k)&1){nr++;check(requests[b][c].valid,"grant without request");check(c<n,"wrong local membership");}
    if((d.rsp_valid>>k)&1){ns++;auto&p=pending[b];
     check(p.valid&&p.client==c,"response routed to wrong local client");
     check(word(d.rsp_data,k*128)==p.expected,"data/write ACK mismatch block "+std::to_string(b));
     if(p.write&&!p.seen)memory[b][p.addr]=p.expected;p.seen=true;
     if((response_ready>>k)&1){p.valid=false;returned++;}
    }
   }
   check(nr<=1&&ns<=1,"multiple local grants/responses");
   for(int c=0;c<5;c++)if((d.req_valid&d.req_ready)>>(b*5+c)&1){
    auto&r=requests[b][c];check(!pending[b].valid,"local command overwritten");
    pending[b]={true,r.write,false,c,r.addr,r.write?r.data:memory[b][r.addr]};
    r.valid=false;accepted++;grants[b][c]++;
   }
   auto&l=loads[b];
   if(b>=3){check(!((d.load_ready|d.a_valid|d.b_valid|d.done_valid)>>b&1),"non-P feeder exposed");continue;}
   if((d.load_valid&d.load_ready)>>b&1){check(l.active&&!l.accepted,"bad load acceptance");l.accepted=true;}
   if((d.a_valid>>b)&1){
    check(l.active&&l.accepted,"unexpected A");int row=get(d.a_row,b*3,3),tile=get(d.a_tile,b*2,2);
    check(row<l.rows&&tile<l.tiles,"A metadata range");
    Word a=word(d.a_data,b*128);uint32_t tag=row|(tile<<3)|(((d.a_bank>>b)&1)<<5)|(((d.a_wide>>b)&1)<<6);
    check(a==memory[b][l.abase+tile*(l.rows>4?8:4)+row],"feeder A data");
    check(bool((d.a_bank>>b)&1)==l.bank&&bool((d.a_wide>>b)&1)==l.aw,"A format/bank");
    if(l.ahold)check(a==l.helda&&tag==l.atag,"A changed under backpressure");
    l.ahold=!((ar>>b)&1);l.helda=a;l.atag=tag;
    if((ar>>b)&1){check(row==l.acount%l.rows&&tile==l.acount/l.rows,"A order");l.acount++;wide_a++;}
   }else{check(!l.ahold,"A valid dropped under stall");}
   if((d.b_valid>>b)&1){
    check(l.active&&l.accepted&&!l.reuse,"unexpected B");int tile=get(d.b_tile,b*2,2),half=(d.b_half>>b)&1;
    std::array<uint32_t,16> data{};for(int q=0;q<16;q++)data[q]=get(d.b_data,b*512+q*32,32);
    uint32_t tag=tile|(half<<2)|(((d.b_bank>>b)&1)<<3)|(((d.b_wide>>b)&1)<<4);
    for(int q=0;q<4;q++)check(word(d.b_data,b*512+q*128)==memory[b][l.bbase+tile*(l.bw?8:4)+half*4+q],"feeder B data");
    check(bool((d.b_bank>>b)&1)==l.bank&&bool((d.b_wide>>b)&1)==l.bw,"B format/bank");
    if(l.bhold)check(data==l.heldb&&tag==l.btag,"B changed under backpressure");
    l.bhold=!((br>>b)&1);l.heldb=data;l.btag=tag;
    if((br>>b)&1){int parts=l.bw?2:1;check(tile==l.bcount/parts&&half==l.bcount%parts,"B order");l.bcount++;wide_b++;}
   }else{check(!l.bhold,"B valid dropped under stall");}
   if((d.done_valid>>b)&1){
    check(l.active&&l.accepted,"unexpected feeder completion");check(!((d.done_error>>b)&1),"legal load rejected");
    check(l.acount==l.rows*l.tiles&&l.bcount==(l.reuse?0:l.tiles*(l.bw?2:1)),"completion before actual A/B retirement");
    if((dt>>b)&1)l={};
   }
  }
  d.clk=1;d.eval();cycles++;
 }
 void drain(){response_ready=(uint64_t(1)<<45)-1;for(int i=0;i<1000&&!quiet();i++)tick();check(quiet(),"drain timeout");}
 void reset(unsigned mask){resetting=mask;tick();tick();resetting=0;tick();}
 void transaction(int b,int c,bool wr,int addr,Word data={}){check(!requests[b][c].valid,"source queue overwrite");requests[b][c]={true,wr,addr,data};}
 void fill_read_all(){
  for(int addr=0;addr<1024;addr++){for(int b=0;b<9;b++)transaction(b,0,true,addr,pattern(b,addr));drain();}
  for(int addr=0;addr<1024;addr++){for(int b=0;b<9;b++)transaction(b,addr%clients(b),false,addr);drain();}
 }
 void traffic(int rounds,bool random_stall,bool upper_only=false,unsigned block_mask=511){
  for(int i=0;i<rounds;i++){
   if(random_stall)response_ready=(uint64_t(rng())<<32)|rng();else response_ready=(uint64_t(1)<<45)-1;
   for(int b=0;b<9;b++)if((block_mask>>b)&1)for(int c=0;c<clients(b);c++)if(!requests[b][c].valid&&(!random_stall||rng()%3==0))
    transaction(b,c,rng()%2,(upper_only?512:0)+rng()%(upper_only?512:1024),random_word());
   tick();
  }drain();
 }
 void fairness(){
  auto before=grants;traffic(2000,false);
  for(int b=0;b<9;b++){uint64_t lo=~uint64_t(0),hi=0;for(int c=0;c<clients(b);c++){auto v=grants[b][c]-before[b][c];lo=std::min(lo,v);hi=std::max(hi,v);}check(lo>50&&hi-lo<=1,"round-robin fairness");}
 }
 void isolation(){
  transaction(0,0,false,42);response_ready&=~uint64_t(1);for(int i=0;i<5;i++)tick();check(pending[0].seen,"stall fixture not reached");
  auto before=grants;auto count=returned;
  for(int i=0;i<600;i++){for(int b=1;b<9;b++)if(!requests[b][0].valid)transaction(b,0,false,i%1024);tick();}
  check(pending[0].valid,"blocked response retired");check(returned-count>1000,"other Blocks blocked");
  for(int b=1;b<9;b++)check(grants[b][0]-before[b][0]>100,"independent block stopped");drain();
 }
 void feeders(){
  for(int pass=0;pass<5;pass++){
   for(int b=0;b<3;b++)loads[b]={true,false,pass==0?1:pass==1?5:8,pass==0?1:4,0,128,bool(pass&1),bool(pass&2),pass==4,bool(b&1)};
   dt=0;
   for(int i=0;i<1500;i++){
    ar=i<25?0:rng()%8;br=i<35?0:rng()%8;
    for(int b=0;b<9;b++)for(int c=0;c<clients(b);c++)if(!requests[b][c].valid&&rng()%4==0)transaction(b,c,rng()%2,512+rng()%512,random_word());
    if(i==1300)dt=511;tick();
   }
   ar=br=dt=511;for(int i=0;i<500&&(loads[0].active||loads[1].active||loads[2].active);i++)tick();
   for(int b=0;b<3;b++)check(!loads[b].active,"feeder progress timeout");drain();
  }
 }
 void resets(){
  // Accepted into command register, then canceled before any RAM write.
  Word old=memory[0][850];transaction(0,0,true,850,random_word());tick();check(pending[0].valid,"capture not reached");reset(1);
  check(memory[0][850]==old,"reference changed on unconfirmed write");transaction(0,1,false,850);drain();
  // Completed write held under backpressure: reset drops response, retains RAM.
  response_ready&=~uint64_t(1);transaction(0,0,true,851,random_word());for(int i=0;i<5;i++)tick();check(pending[0].seen,"confirmed write not reached");
  reset(1);transaction(0,1,false,851);drain();
  // Cancel actual in-flight feeder while another Block is making progress.
  loads[0]={true,false,8,4,0,128,false,true,false,false};ar=br=0;
  for(int i=0;i<10;i++){if(!requests[5][0].valid)transaction(5,0,false,20+i);tick();}
  reset(1);check(!loads[0].active,"feeder reset did not cancel");ar=br=511;drain();
  transaction(0,2,false,0);drain();
 }
 void run(){reset(511);fill_read_all();std::cout<<"CASE_PASS full_address_space_and_cross_block_isolation\n";
  fairness();std::cout<<"CASE_PASS persistent_local_contention_fairness\n";
  isolation();std::cout<<"CASE_PASS_stalled_block_independent_progress\n";
  traffic(7000,true);std::cout<<"CASE_PASS randomized_request_response_backpressure\n";
  feeders();std::cout<<"CASE_PASS real_feeder_all_formats_and_local_port_conflicts\n";
  resets();std::cout<<"CASE_PASS independent_reset_cancellation_and_retained_storage\n";
  traffic(1000,true);std::cout<<"CASE_PASS normal_reuse_after_reset\n";}
};
int main(int argc,char**argv){Verilated::commandArgs(argc,argv);unsigned seed=177;for(int i=1;i<argc;i++)if(std::string(argv[i]).rfind("--seed=",0)==0)seed=std::stoul(argv[i]+7);
 try{Bench b(seed);b.run();std::cout<<"{\"pass\":true,\"seed\":"<<seed<<",\"checks\":"<<b.checks<<",\"cycles\":"<<b.cycles<<",\"requests\":"<<b.accepted<<",\"responses\":"<<b.returned<<",\"feeder_a\":"<<b.wide_a<<",\"feeder_b\":"<<b.wide_b<<",\"blocks\":9,\"private_payload_bytes\":147456}"<<std::endl;}
 catch(const std::exception&e){std::cerr<<"FAIL "<<e.what()<<std::endl;return 1;}return 0;
}
