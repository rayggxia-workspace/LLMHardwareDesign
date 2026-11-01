#ifdef REAL_S
#include "Vcontrol_d_s_pair.h"
using Vcontrol_d=Vcontrol_d_s_pair;
#else
#include "Vcontrol_d.h"
#endif
#include "verilated.h"
#include <array>
#include <vector>
#include <deque>
#include <random>
#include <iostream>
#include <cstdlib>
static uint64_t checks=0,cycles=0;
static void need(bool b,const char*m){++checks;if(!b){std::cerr<<m<<" cycle="<<cycles<<"\n";std::exit(1);}}
using Word=std::array<uint32_t,4>;
using Desc=std::array<uint32_t,8>;
constexpr uint64_t ExtBase=0x1200000000ULL;
static Desc descriptor(bool write,uint16_t tag,unsigned ext,unsigned loc,unsigned bytes,unsigned rows,unsigned estride,unsigned lstride){
 uint64_t addr=ExtBase+ext;return {{uint32_t(tag)<<16|(write?1u:0u),uint32_t(addr),uint32_t(addr>>32)|(loc<<12),bytes,rows|(lstride<<16),estride,0,0}};}
struct Sim {
 Vcontrol_d v;std::mt19937 rng{162};
 std::vector<uint8_t> ext=std::vector<uint8_t>(65536,0xa5),s=std::vector<uint8_t>(16384,0);
 struct Read {bool valid=false;uint64_t addr=0;unsigned count=0,index=0;};
 std::array<Read,2> reads{};
 struct Write {uint64_t addr;unsigned count,index,id;};
 std::deque<Write> writes;std::array<bool,2> b_pending{{false,false}};
 unsigned reads_live=0,writes_live=0,ar_count=0,aw_count=0;
 bool s_pending=false;unsigned s_delay=0,s_address=0;
 std::vector<uint64_t> completions;
 bool inject_r=false,inject_b=false,r_injected=false,b_injected=false;
 bool stalled_complete=false;uint64_t held_complete=0;
 Sim(){v.clk=0;v.task_valid=0;for(unsigned n=0;n<8;++n)v.task_data[n]=0;
  v.complete_ready=0;v.arready=0;v.awready=0;v.rvalid=0;v.rid=0;v.rresp=0;v.rlast=0;for(unsigned n=0;n<4;++n)v.rdata[n]=0;
  v.wready=0;v.bvalid=0;v.bid=0;v.bresp=0;
#ifdef REAL_S
  v.init_mode=0;v.init_valid=0;v.init_address=0;v.init_take=1;for(unsigned n=0;n<4;++n)v.init_data[n]=0;
#else
  v.s_ready=0;v.s_valid=0;for(unsigned n=0;n<4;++n)v.s_dout[n]=0;
#endif
  v.reset=1;for(unsigned n=0;n<4;++n){v.clk=0;v.eval();v.clk=1;v.eval();}v.reset=0;v.clk=0;v.eval();
  for(unsigned n=0;n<ext.size();++n)ext[n]=uint8_t(n*73+19);}
 unsigned offset(uint64_t addr){need(addr>=ExtBase && addr+16<=ExtBase+ext.size(),"finite external address");return unsigned(addr-ExtBase);}
 Word load(const std::vector<uint8_t>&m,unsigned a){need(a+16<=m.size(),"word read range");Word w{};for(unsigned n=0;n<16;++n)w[n/4]|=uint32_t(m[a+n])<<(8*(n%4));return w;}
 void store(std::vector<uint8_t>&m,unsigned a,const Word&w,unsigned mask){need(a+16<=m.size(),"word write range");for(unsigned n=0;n<16;++n)if(mask&(1u<<n))m[a+n]=w[n/4]>>(8*(n%4));}
 void tick(){
  v.clk=0;v.complete_ready=rng()%4!=0;v.arready=rng()%4!=0;v.awready=rng()%4!=0;v.wready=rng()%3!=0;
#ifndef REAL_S
  v.s_ready=!s_pending && rng()%4!=0;v.s_valid=s_pending && s_delay==0;
  if(v.s_valid){const auto w=load(s,s_address*16);for(unsigned n=0;n<4;++n)v.s_dout[n]=w[n];}
#endif
  unsigned rslot=rng()%2;if(!reads[rslot].valid)rslot^=1;
  v.rvalid=reads[rslot].valid && rng()%3!=0;v.rid=rslot;v.rresp=0;
  bool inject_now=false;
  if(v.rvalid){const auto&r=reads[rslot];v.rlast=r.index+1==r.count;const auto w=load(ext,offset(r.addr+r.index*16));for(unsigned n=0;n<4;++n)v.rdata[n]=w[n];
   inject_now=inject_r&&!r_injected;v.rresp=inject_now?2:0;}
  unsigned bslot=rng()%2;if(!b_pending[bslot])bslot^=1;
  v.bvalid=b_pending[bslot] && rng()%3!=0;v.bid=bslot;v.bresp=inject_b&&!b_injected?2:0;
  v.eval();
  if(stalled_complete)need(v.complete_valid && v.complete_data==held_complete,"completion stable under backpressure");
  stalled_complete=v.complete_valid&&!v.complete_ready;if(stalled_complete)held_complete=v.complete_data;
  if(v.complete_valid && v.complete_ready)completions.push_back(v.complete_data);
#ifndef REAL_S
  if(v.s_valid && v.s_take)s_pending=false;
  else if(s_pending && s_delay)--s_delay;
#endif
  if(v.s_req && v.s_ready){need(v.s_instance==0 && v.s_addr<1024,"finite S port address");
   if(v.s_wr){Word w{};for(unsigned n=0;n<4;++n)w[n]=v.s_din[n];store(s,v.s_addr*16,w,65535);}
#ifndef REAL_S
   need(!s_pending,"only one S transaction in flight");s_pending=true;s_delay=1+rng()%5;s_address=v.s_addr;
#endif
  }
  if(v.rvalid && v.rready){if(inject_now)r_injected=true;auto&r=reads[rslot];if(++r.index==r.count){r.valid=false;--reads_live;}}
  if(v.bvalid && v.bready){if(v.bresp)b_injected=true;b_pending[bslot]=false;--writes_live;}
  if(v.arvalid && v.arready){need(v.arid<2 && !reads[v.arid].valid,"read ID not reused");need(++reads_live<=2,"two AR outstanding");
   need(v.arsize==4 && v.arburst==1 && v.arlen<16 && (v.araddr&4095)+(v.arlen+1)*16<=4096,"AR fields");
   reads[v.arid]={true,v.araddr,unsigned(v.arlen+1),0};++ar_count;}
  if(v.awvalid && v.awready){need(v.awid<2 && !b_pending[v.awid],"write ID not reused");need(++writes_live<=2,"two AW outstanding");
   need(v.awsize==4 && v.awburst==1 && v.awlen<16 && (v.awaddr&4095)+(v.awlen+1)*16<=4096,"AW fields");
   writes.push_back({v.awaddr,unsigned(v.awlen+1),0,v.awid});++aw_count;}
  if(v.wvalid && v.wready){need(!writes.empty(),"W follows accepted AW order");auto&w=writes.front();
   need(v.wlast==(w.index+1==w.count),"WLAST");Word data{};for(unsigned n=0;n<4;++n)data[n]=v.wdata[n];
   store(ext,offset(w.addr+w.index*16),data,v.wstrb);if(++w.index==w.count){b_pending[w.id]=true;writes.pop_front();}}
  v.clk=1;v.eval();++cycles;need(!v.protocol_error,"legal AXI/S protocol");
 }
 void send(const Desc&d){for(unsigned n=0;n<8;++n)v.task_data[n]=d[n];v.task_valid=1;
  unsigned guard=0;v.eval();while(!v.task_ready){tick();need(++guard<10000,"task queue timeout");v.eval();}tick();v.task_valid=0;}
 uint64_t finish(unsigned number=1){const unsigned target=unsigned(completions.size())+number;
  for(unsigned n=0;n<50000 && completions.size()<target;++n)tick();need(completions.size()==target,"DMA completion timeout");return completions.back();}
 void drained(){for(unsigned n=0;n<20;++n)tick();need(reads_live==0&&writes_live==0&&writes.empty()&&!s_pending,"no implicit unfinished transactions");}
 void prime(unsigned begin,unsigned end){
#ifdef REAL_S
  v.init_mode=1;
  for(unsigned a=begin;a<end;a+=16){const auto data=load(s,a);for(unsigned n=0;n<4;++n)v.init_data[n]=data[n];v.init_address=a/16;v.init_valid=1;v.eval();
   unsigned guard=0;while(!v.init_ready){tick();need(++guard<100,"S init ready");}tick();v.init_valid=0;
   while(!v.init_response){tick();need(++guard<100,"S init acknowledgement");}tick();}
  v.init_mode=0;tick();
#else
  (void)begin;(void)end;
#endif
 }
};
int main(int argc,char**argv){Verilated::commandArgs(argc,argv);
 {Sim x;auto d=descriptor(false,91,0,0,16,1,0,0);d[2]|=1u<<8;x.send(d);auto c=x.finish();need(((c>>20)&15)==2 && !x.ar_count && !x.aw_count,"unwired S instance rejected before AXI/S access");}
 for(unsigned bytes:{1u,15u,16u,17u,255u,256u,257u,1024u}){
  Sim x;const unsigned stride=(bytes+15)&~15u;
  x.send(descriptor(false,33,4080,0,bytes,2,8192,stride));auto c=x.finish();need(c==(uint64_t(bytes*2)<<32|33),"load completion after S writes");
  for(unsigned row=0;row<2;++row)for(unsigned n=0;n<stride;++n)need(x.s[row*stride+n]==(n<bytes?x.ext[4080+row*8192+n]:0),"load bytes and zero padding");
  const auto before=x.ext;x.send(descriptor(true,34,32768,0,bytes,2,4096,stride));c=x.finish();need(c==(uint64_t(bytes*2)<<32|34),"store completion after B");
  for(unsigned row=0;row<2;++row)for(unsigned n=0;n<stride;++n)need(x.ext[32768+row*4096+n]==(n<bytes?x.s[row*stride+n]:before[32768+row*4096+n]),"WSTRB preserves external tail");
  x.drained();
 }
 {
  Sim x;for(unsigned n=8192;n<16384;++n)x.s[n]=uint8_t(n*17);
  x.prime(8192,10240);auto expect=x.s;x.send(descriptor(false,1,0,0,1024,1,0,0));x.send(descriptor(true,2,32768,8192,1024,1,0,0));
  x.send(descriptor(false,3,4096,1024,1024,1,0,0));x.send(descriptor(true,4,36864,9216,1024,1,0,0));
  x.finish(4);for(unsigned n=0;n<1024;++n){need(x.s[n]==x.ext[n],"concurrent load0");need(x.s[1024+n]==x.ext[4096+n],"concurrent load1");
   need(x.ext[32768+n]==expect[8192+n]&&x.ext[36864+n]==expect[9216+n],"concurrent store");}x.drained();
 }
 for(unsigned write=0;write<2;++write){Sim x;x.inject_r=!write;x.inject_b=write;x.send(descriptor(write,77,0,0,1024,1,0,0));
  const auto c=x.finish();need((c&65535)==77 && ((c>>20)&15)==4,"AXI error reported");x.drained();need(write?x.b_injected:x.r_injected,"error exercised");}
 {
  Sim x;auto d=descriptor(false,88,0,16368,17,1,0,0);x.send(d);const auto c=x.finish();
  need(((c>>20)&15)==2 && x.ar_count==0 && x.aw_count==0 && x.v.s_write_count==0,"invalid descriptor has no side effects");
 }
 std::cout<<"{\"passed\":true,\"checks\":"<<checks<<",\"cycles\":"<<cycles<<"}\n";
}
