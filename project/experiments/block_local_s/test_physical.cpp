#include "Vlocal_s_physical.h"
#include "verilated.h"
#include <algorithm>
#include <array>
#include <cstdint>
#include <iostream>
#include <random>
#include <stdexcept>
#include <string>
#ifndef CLIENT_COUNT
#define CLIENT_COUNT 4
#endif
#ifndef WITH_FEEDER
#define WITH_FEEDER 0
#endif
using Word=std::array<uint32_t,4>;
struct Req{bool valid=false,wr=false;unsigned addr=0;Word data{};};
struct Pending{bool valid=false,wr=false,seen=false;unsigned owner=0,addr=0;Word expected{};};
struct Bench{
 Vlocal_s_physical d;
 std::mt19937 rng;
 std::array<Word,1024> memory{};
 std::array<Req,CLIENT_COUNT> req{};
 Pending pending;
 uint64_t checks=0,cycles=0,requests=0,responses=0;
 std::array<unsigned,CLIENT_COUNT> grants{};
 unsigned ready=(1U<<CLIENT_COUNT)-1;
 bool reset=false;
#if WITH_FEEDER
 bool load=false,started=false,active=false,bank=false,aw=false,bw=false,reuse=false;
 unsigned rows=0,tiles=0,ar=1,br=1,dt=1,ac=0,bc=0;
 bool ahold=false,bhold=false;Word held_a{};std::array<uint32_t,16> held_b{};unsigned a_tag=0,b_tag=0;
#endif
 explicit Bench(unsigned seed):rng(seed){}
 void check(bool ok,const char* message){checks++;if(!ok)throw std::runtime_error(std::string(message)+" cycle="+std::to_string(cycles));}
 Word random_word(){return{uint32_t(rng()),uint32_t(rng()),uint32_t(rng()),uint32_t(rng())};}
 bool quiet(){if(pending.valid)return false;for(auto&r:req)if(r.valid)return false;return true;}
 void tick(){
  d.clk=0;d.reset=reset;d.req_valid=0;d.req_write=0;d.req_addr=0;d.rsp_ready=ready;
  for(unsigned c=0;c<CLIENT_COUNT;c++){
   if(req[c].valid)d.req_valid|=1U<<c;if(req[c].wr)d.req_write|=1U<<c;
   d.req_addr|=uint64_t(req[c].addr)<<(10*c);for(unsigned q=0;q<4;q++)d.req_data[c*4+q]=req[c].data[q];
  }
#if WITH_FEEDER
  d.load_valid=load;d.load_bank=bank;d.load_rows=rows;d.load_tiles=tiles;
  d.load_a_wide=aw;d.load_b_wide=bw;d.load_reuse_b=reuse;d.load_a_base=0;d.load_b_base=128;
  d.a_ready=ar;d.b_ready=br;d.done_take=dt;
#endif
  d.eval();
  if(reset){check(d.req_ready==0&&d.rsp_valid==0,"reset handshake");pending={};for(auto&r:req)r={};
#if WITH_FEEDER
   check(!d.a_valid&&!d.b_valid&&!d.done_valid,"reset feeder completion");load=started=active=ahold=bhold=false;
#endif
  }else{
   unsigned accepted=0,returned=0;
   for(unsigned c=0;c<CLIENT_COUNT;c++){
    if((d.rsp_valid>>c)&1){returned++;check(pending.valid&&pending.owner==c,"response owner");
     Word value{};for(unsigned q=0;q<4;q++)value[q]=d.rsp_data[c*4+q];check(value==pending.expected,"response data");
     if(pending.wr&&!pending.seen)memory[pending.addr]=pending.expected;pending.seen=true;
     if((ready>>c)&1){pending.valid=false;responses++;}
    }
    if((d.req_valid&d.req_ready)>>c&1){accepted++;check(!pending.valid,"inflight overwrite");
     auto&r=req[c];pending={true,r.wr,false,c,r.addr,r.wr?r.data:memory[r.addr]};r.valid=false;requests++;grants[c]++;
    }
   }check(accepted<=1&&returned<=1,"multiple local owners");
#if WITH_FEEDER
   if(d.load_valid&&d.load_ready){check(active&&!started,"load acceptance");load=false;started=true;}
   if(d.a_valid){check(active&&started,"unexpected A");check(d.a_row<rows&&d.a_tile<tiles,"A tag range");
    Word value{};for(unsigned q=0;q<4;q++)value[q]=d.a_data[q];
    unsigned tag=d.a_row|(d.a_tile<<3)|(d.a_bank<<5)|(d.a_wide<<6);
    check(value==memory[d.a_tile*(rows>4?8:4)+d.a_row],"A payload");check(d.a_bank==bank&&d.a_wide==aw,"A format");
    if(ahold)check(value==held_a&&tag==a_tag,"A hold");ahold=!ar;held_a=value;a_tag=tag;
    if(ar){check(d.a_row==ac%rows&&d.a_tile==ac/rows,"A order");ac++;}
   }else check(!ahold,"A valid under stall");
   if(d.b_valid){check(active&&started&&!reuse,"unexpected B");std::array<uint32_t,16> value{};
    for(unsigned q=0;q<16;q++)value[q]=d.b_data[q];
    unsigned tag=d.b_tile|(d.b_half<<2)|(d.b_bank<<3)|(d.b_wide<<4);
    for(unsigned q=0;q<4;q++){Word w{};for(unsigned j=0;j<4;j++)w[j]=value[q*4+j];
     check(w==memory[128+d.b_tile*(bw?8:4)+d.b_half*4+q],"B payload");}
    check(d.b_bank==bank&&d.b_wide==bw,"B format");
    if(bhold)check(value==held_b&&tag==b_tag,"B hold");bhold=!br;held_b=value;b_tag=tag;
    if(br){unsigned parts=bw?2:1;check(d.b_tile==bc/parts&&d.b_half==bc%parts,"B order");bc++;}
   }else check(!bhold,"B valid under stall");
   if(d.done_valid){check(active&&started&&!d.done_error,"load completion");
    check(ac==rows*tiles&&bc==(reuse?0:tiles*(bw?2:1)),"premature completion");if(dt)active=false;}
#endif
  }d.clk=1;d.eval();cycles++;
 }
 void drain(){ready=(1U<<CLIENT_COUNT)-1;for(unsigned i=0;i<1000&&!quiet();i++)tick();check(quiet(),"drain timeout");}
 void enqueue(unsigned c,bool wr,unsigned addr,Word data={}){check(!req[c].valid,"source overwrite");req[c]={true,wr,addr,data};}
 void resetting(){reset=true;tick();tick();reset=false;tick();}
 void run(){
  resetting();
  for(unsigned addr=0;addr<1024;addr++){enqueue(addr%CLIENT_COUNT,true,addr,random_word());drain();}
  for(unsigned addr=0;addr<1024;addr++){enqueue((addr+1)%CLIENT_COUNT,false,addr);drain();}
  auto before=grants;
  for(unsigned i=0;i<500;i++){for(unsigned c=0;c<CLIENT_COUNT;c++)if(!req[c].valid)enqueue(c,false,rng()%1024);tick();}drain();
  unsigned lo=~0U,hi=0;for(unsigned c=0;c<CLIENT_COUNT;c++){unsigned n=grants[c]-before[c];lo=std::min(lo,n);hi=std::max(hi,n);}
  check(lo>10&&hi-lo<=1,"fairness");
  for(unsigned i=0;i<1000;i++){ready=rng()&((1U<<CLIENT_COUNT)-1);for(unsigned c=0;c<CLIENT_COUNT;c++)if(!req[c].valid&&rng()%3==0)enqueue(c,rng()%2,rng()%1024,random_word());tick();}drain();
  ready&=~1U;enqueue(0,true,511,random_word());for(unsigned i=0;i<6;i++)tick();check(pending.seen,"held write fixture");
  enqueue(1,false,511);unsigned old_requests=requests;for(unsigned i=0;i<40;i++)tick();check(requests==old_requests,"owner overwritten during hold");drain();
  enqueue(0,true,850,random_word());tick();resetting();enqueue(1,false,850);drain();
  ready&=~1U;enqueue(0,true,851,random_word());for(unsigned i=0;i<6;i++)tick();check(pending.seen,"retained write fixture");resetting();enqueue(1,false,851);drain();
#if WITH_FEEDER
  for(unsigned pass=0;pass<5;pass++){
   active=load=true;started=false;rows=pass==0?1:pass==1?5:8;tiles=pass==0?1:4;
   aw=pass&1;bw=pass&2;reuse=pass==4;bank=pass&1;ac=bc=0;dt=0;unsigned initial=requests;
   for(unsigned i=0;i<1500;i++){
    ar=i<100?0:rng()%2;br=i<100?0:rng()%2;if(i==1300)dt=1;
    for(unsigned c=0;c<CLIENT_COUNT;c++)if(!req[c].valid&&rng()%3==0)enqueue(c,rng()%2,512+rng()%512,random_word());
    tick();if(i==99)check(requests-initial>=10&&ac==0&&bc==0,"ordinary progress under feeder stall");
   }ar=br=dt=1;for(unsigned i=0;i<1000&&active;i++)tick();check(!active,"feeder progress");drain();
  }
#endif
  check(quiet(),"final outstanding");
 }
};
int main(int argc,char**argv){Verilated::commandArgs(argc,argv);try{Bench b(177);b.run();std::cout<<"{\"passed\":true,\"checks\":"<<b.checks<<",\"cycles\":"<<b.cycles<<",\"requests\":"<<b.requests<<",\"responses\":"<<b.responses<<",\"clients\":"<<CLIENT_COUNT<<",\"feeder\":"<<WITH_FEEDER<<"}"<<std::endl;}catch(const std::exception&e){std::cerr<<"FAIL "<<e.what()<<std::endl;return 1;}return 0;}
