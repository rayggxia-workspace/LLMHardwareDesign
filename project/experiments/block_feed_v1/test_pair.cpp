#include "Vblock_feed_pair.h"
#include "verilated.h"
#include <array>
#include <cstdint>
#include <iostream>
#include <random>
#include <stdexcept>
#include <string>
#include <vector>
using I128=__int128_t;using U128=__uint128_t;
using Vec=std::array<int16_t,8>;
using Inputs=std::array<std::array<Vec,4>,8>;
using Weights=std::array<std::array<Vec,8>,4>;
using Partial=std::array<std::array<int64_t,8>,8>;
static Vblock_feed_pair* ptr;
#define d (*ptr)
static std::mt19937_64 rng(13020261029ULL);
static uint64_t checks=0,cycles=0,ac=0,bc=0,mc=0,nc=0,tc=0,ab_concurrent=0;
static bool timed=false;
static void ck(bool ok,const std::string& msg){++checks;if(!ok)throw std::runtime_error(msg);}
static U128 get128(const WData* x){U128 v=0;for(int j=3;j>=0;--j)v=(v<<32)|x[j];return v;}
static void put128(WData* x,U128 v){for(unsigned j=0;j<4;++j){x[j]=uint32_t(v);v>>=32;}}
static void tick(){
 d.clk=0;d.eval();ac+=d.a_fire;bc+=d.b_fire;mc+=d.mem_fire;nc+=d.req&&d.ready;tc+=d.capture_fire;
 ab_concurrent+=d.a_fire&&d.b_fire;
 d.clk=1;d.eval();++cycles;d.clk=0;d.eval();ck(!d.t_error,"T protocol error");
}
static void reset(){
 d.reset=1;d.req=0;d.take=1;d.cmd_valid=0;d.rsp_ready=0;d.load_valid=0;d.done_take=0;
 d.a_allow=1;d.b_allow=1;d.capture_to_t=0;d.t_begin_valid=0;d.t_commit=0;d.t_read_take=0;d.t_release=0;
 tick();tick();d.reset=0;d.eval();
}
static void write(unsigned addr,U128 data){
 d.req=1;d.wr=1;d.addr=addr;put128(d.din,data);d.eval();
 unsigned timeout=0;while(!d.ready){ck(++timeout<1000,"store write timeout");tick();}
 tick();ck(d.valid&&get128(d.dout)==data,"legacy128 write acknowledgement");d.req=0;d.eval();
}
static U128 pack(const Vec& a,bool wide){
 U128 v=0;for(unsigned j=0;j<8;++j)v|=wide?U128(uint16_t(a[j]))<<(16*j):U128(uint8_t(a[j]))<<(8*j);return v;
}
static void stage(unsigned bank,const Inputs& a,const Weights& b,bool wa,bool wb,unsigned rows,unsigned tiles,bool weights=true){
 unsigned abase=bank*128,bbase=bank*128+64,groups=(rows+3)/4;
 for(unsigned t=0;t<tiles;++t){
  for(unsigned r=0;r<4*groups;++r)write(abase+t*4*groups+r,r<rows?pack(a[r][t],wa):0);
  if(weights)for(unsigned w=0;w<(wb?8u:4u);++w){
   U128 word=0;for(unsigned j=0;j<(wb?8u:16u);++j){unsigned index=w*(wb?8:16)+j;
    word|=wb?U128(uint16_t(b[t][index/8][index%8]))<<(16*j):U128(uint8_t(b[t][index/8][index%8]))<<(8*j);
   }
   write(bbase+t*(wb?8:4)+w,word);
  }
 }
}
static void start_load(unsigned bank,bool wa,bool wb,unsigned rows,unsigned tiles,bool reuse){
 ck(d.load_ready,"loader not ready");d.load_valid=1;d.load_bank=bank;d.load_rows=rows;d.load_tiles=tiles;
 d.load_a_wide=wa;d.load_b_wide=wb;d.load_reuse_b=reuse;
 d.load_a_base=bank*128;d.load_b_base=bank*128+64;tick();d.load_valid=0;d.eval();
}
static uint64_t finish_load(bool pressure=false,bool expect_error=false){
 uint64_t start=cycles;unsigned wait=0;
 while(!d.done_valid){
  ck(++wait<3000,"loader timeout");d.a_allow=!pressure||rng()%4!=0;d.b_allow=!pressure||rng()%3!=0;tick();
 }
 uint64_t elapsed=cycles-start;ck(bool(d.done_error)==expect_error,"loader error flag");
 if(pressure)for(unsigned j=0;j<3;++j){tick();ck(d.done_valid&&bool(d.done_error)==expect_error,"done response stability");}
 d.a_allow=d.b_allow=1;d.done_take=1;tick();d.done_take=0;return elapsed;
}
static uint64_t descriptor(bool wa,bool wb,bool clear,unsigned k,unsigned n,unsigned tiles,unsigned rows){
 return unsigned(wa)|(unsigned(wb)<<1)|(unsigned(clear)<<2)|(k<<4)|(n<<8)|(tiles<<12)|(rows<<15);
}
struct Reply{U128 data;bool sat;};
static Reply command(unsigned op,unsigned index,uint64_t data,bool capture=false,bool error=false){
 ck(d.cmd_ready,"M command not ready");d.cmd_op=op;d.cmd_index=index;d.cmd_data=data;d.cmd_valid=1;
 d.capture_to_t=capture;d.rsp_ready=0;tick();d.cmd_valid=0;
 unsigned wait=0;while(!(capture?d.capture_fire:d.rsp_valid)){ck(++wait<5000,"M response timeout");tick();}
 Reply v{get128(d.rsp_data),bool(d.rsp_saturated)};ck(bool(d.rsp_error)==error,"M response error");
 if(!capture){
  unsigned hold=timed?0:rng()%3;for(unsigned j=0;j<hold;++j){tick();ck(d.rsp_valid&&get128(d.rsp_data)==v.data,"M response stalled stability");}
  d.rsp_ready=1;
 }
 tick();d.rsp_ready=0;d.capture_to_t=0;return v;
}
static void ref(Partial& p,const Inputs& a,const Weights& b,bool wa,bool wb,unsigned rows,unsigned tiles,unsigned k,unsigned n,bool clear){
 for(unsigned r=0;r<rows;++r){if(clear)p[r].fill(0);
  for(unsigned t=0;t<tiles;++t)for(unsigned j=0;j<(t+1==tiles?k:8);++j)for(unsigned o=0;o<n;++o)
   p[r][o]+=int64_t(wa?a[r][t][j]:int8_t(a[r][t][j]))*(wb?b[t][o][j]:int8_t(b[t][o][j]));
 }
}
static void partial_matches(const Partial& p,unsigned rows){
 for(unsigned r=0;r<rows;++r)for(unsigned j=0;j<4;++j){auto v=command(3,r*8+j,0).data;
  ck(int64_t(v)==p[r][2*j]&&int64_t(v>>64)==p[r][2*j+1],"S/loader/M independent numeric mismatch");}
}
static void fill(Inputs& a,Weights& b,unsigned seed){
 for(unsigned r=0;r<8;++r)for(unsigned t=0;t<4;++t)for(unsigned j=0;j<8;++j)a[r][t][j]=int16_t(rng()^(seed+r));
 for(unsigned t=0;t<4;++t)for(unsigned n=0;n<8;++n)for(unsigned j=0;j<8;++j)b[t][n][j]=int16_t(rng());
}
static U128 final_word(const Partial& p,unsigned row,unsigned group){
 U128 word=0;for(unsigned j=0;j<4;++j){I128 x=p[row][4*group+j],q=x>>16;
  U128 rem=U128(x)&65535;q+=rem>32768||(rem==32768&&(q&1));
  if(q<INT32_MIN)q=INT32_MIN;if(q>INT32_MAX)q=INT32_MAX;word|=U128(uint32_t(q))<<(32*j);
 }return word;
}
static void handoff_t(const Partial& p,unsigned rows){
 d.t_words=rows*2;d.t_begin_valid=1;d.eval();ck(d.t_begin_ready,"T lease not available");tick();d.t_begin_valid=0;
 auto start=tc;
 for(unsigned r=0;r<rows;++r){command(4,r*8,uint64_t(1)|(uint64_t(1)<<39));
  for(unsigned g=0;g<2;++g)command(5,r*8+g,16|(uint64_t(2)<<8),true);
 }
 ck(tc-start==rows*2,"T did not accept complete M results");
 ck(d.t_commit_ready&&!d.t_read_valid,"T premature result visibility");d.t_commit=1;tick();d.t_commit=0;
 unsigned consumed=0,timeout=0;bool held=false;U128 previous=0;
 while(consumed<rows*2){
  ck(++timeout<1000,"T read timeout");d.t_read_take=timed||rng()%3!=0;d.eval();
  if(held)ck(d.t_read_valid&&get128(d.t_read_data)==previous,"T backpressure stability");
  if(d.t_read_valid){
   ck(get128(d.t_read_data)==final_word(p,consumed/2,consumed%2),"M->T format/value mismatch");
   ck(bool(d.t_read_last)==(consumed+1==rows*2),"T last marker");
  }
  held=d.t_read_valid&&!d.t_read_take;previous=get128(d.t_read_data);
  bool take=d.t_read_valid&&d.t_read_take;tick();if(take)++consumed;
 }
 d.t_read_take=0;ck(d.t_release_ready,"T release phase");d.t_release=1;tick();d.t_release=0;
}
static void random_cases(){
 for(unsigned test=0;test<32;++test){
  reset();Inputs a{};Weights b{};Partial p{};fill(a,b,test);
  bool wa=test&1,wb=test&2;unsigned rows=1+(test/4)%8,tiles=1+test%4,k=1+rng()%8,n=1+rng()%8,bank=test%2;
  stage(bank,a,b,wa,wb,rows,tiles);uint64_t a0=ac,b0=bc,m0=mc;
  start_load(bank,wa,wb,rows,tiles,false);finish_load(true);
  ck(ac-a0==rows*tiles&&bc-b0==tiles*(wb?2:1),"A128/B512 handshake counts");
  ck(mc-m0==tiles*((rows+3)/4+(wb?2:1)),"actual512-bit memory transaction count");
  command(10,bank*32,descriptor(wa,wb,true,k,n,tiles,rows));ref(p,a,b,wa,wb,rows,tiles,k,n,true);partial_matches(p,rows);
  fill(a,b,test+32); // Preserve old weights separately in the store and M.
  // Read B back from initialized S through legacy128 access, proving the
  // feeder did not consume or duplicate physical storage contents.
  Weights old{};
  for(unsigned t=0;t<tiles;++t)for(unsigned w=0;w<(wb?8u:4u);++w){
   d.req=1;d.wr=0;d.addr=bank*128+64+t*(wb?8:4)+w;d.eval();ck(d.ready,"legacy128 read availability");tick();d.req=0;
   U128 value=get128(d.dout);
   for(unsigned j=0;j<(wb?8u:16u);++j){unsigned at=w*(wb?8:16)+j;
    old[t][at/8][at%8]=wb?int16_t(value>>(16*j)):int8_t(value>>(8*j));}
  }
  stage(bank,a,old,wa,wb,rows,tiles,false);a0=ac;b0=bc;m0=mc;
  start_load(bank,wa,wb,rows,tiles,true);finish_load(true);
  ck(ac-a0==rows*tiles&&bc==b0&&mc-m0==tiles*((rows+3)/4),"reuse unexpectedly fetched B");
  command(10,bank*32,descriptor(wa,wb,false,k,n,tiles,rows));ref(p,a,old,wa,wb,rows,tiles,k,n,false);partial_matches(p,rows);
  handoff_t(p,rows);
 }
}
static void overlap_and_reset(){
 reset();Inputs a{};Weights b{};Partial p{};fill(a,b,123);
 stage(0,a,b,true,true,8,4);stage(1,a,b,true,true,8,4);
 start_load(0,true,true,8,4,false);finish_load();
 d.cmd_valid=1;d.cmd_op=10;d.cmd_index=0;d.cmd_data=descriptor(true,true,true,8,8,4,8);d.rsp_ready=0;tick();d.cmd_valid=0;
 start_load(1,true,true,8,4,false);auto elapsed=finish_load(true);
 ck(elapsed<288&&!d.rsp_valid,"next bank not loaded while current bank computes");
 unsigned timeout=0;while(!d.rsp_valid){ck(++timeout<500,"overlap response timeout");tick();}
 ck(!d.rsp_error,"overlap compute error");d.rsp_ready=1;tick();d.rsp_ready=0;
 ref(p,a,b,true,true,8,4,8,8,true);partial_matches(p,8);
 command(10,32,descriptor(true,true,true,8,8,4,8));partial_matches(p,8);
 start_load(0,true,true,8,4,false);tick();tick();reset();
 ck(!d.load_busy&&!d.done_valid,"reset left a live loader transaction");
 command(10,0,descriptor(true,true,true,8,8,4,8),false,true);
 // Invalid descriptors perform no memory access and return a held error.
 uint64_t before=mc;d.load_valid=1;d.load_rows=0;d.eval();ck(d.load_ready,"invalid descriptor admission");tick();d.load_valid=0;
 finish_load(true,true);ck(mc==before,"invalid load performed a read");
}
static std::string benchmark(){
 timed=true;std::string text="[";
 for(unsigned rows:{1u,8u})for(unsigned format=0;format<4;++format){
  reset();Inputs a{};Weights b{};Partial p{};bool wa=format&1,wb=format&2;
  for(auto& row:a)for(auto& tile:row)for(unsigned j=0;j<8;++j)tile[j]=(j%2?-1:1)*int(j+1)*(wa?1234:1);
  for(auto& tile:b)for(unsigned n=0;n<8;++n)for(unsigned j=0;j<8;++j)tile[n][j]=int(n+1)*(int(j%3)-1)*(wb?257:1);
  uint64_t refill=0,load=0,compute=0,start=cycles,n0=nc,m0=mc,a0=ac,b0=bc;
  for(unsigned group=0;group<32;++group){
   unsigned bank=group%2;auto before=cycles;stage(bank,a,b,wa,wb,rows,4);refill+=cycles-before;
   before=cycles;start_load(bank,wa,wb,rows,4,false);finish_load();load+=cycles-before;
   before=cycles;command(10,bank*32,descriptor(wa,wb,group==0,8,8,4,rows));compute+=cycles-before;
   ref(p,a,b,wa,wb,rows,4,8,8,group==0);
  }
  auto before=cycles;handoff_t(p,rows);auto finish=cycles-before,total=cycles-start;
  ck(total==refill+load+compute+finish,"end-to-end cycle attribution");
  if(text.size()>1)text+=",";
  text+="{\"rows\":"+std::to_string(rows)+",\"format\":"+std::to_string(format)+",\"k\":1024,\"n\":8";
  text+=",\"logical_macs\":"+std::to_string(uint64_t(rows)*1024*8);
  text+=",\"s_refill_cycles\":"+std::to_string(refill)+",\"s_to_m_load_cycles\":"+std::to_string(load);
  text+=",\"m_compute_cycles\":"+std::to_string(compute)+",\"finalize_t_consume_cycles\":"+std::to_string(finish);
  text+=",\"total_cycles\":"+std::to_string(total)+",\"s128_write_bytes\":"+std::to_string((nc-n0)*16);
  text+=",\"s512_read_bytes\":"+std::to_string((mc-m0)*64)+",\"a_container_bytes\":"+std::to_string((ac-a0)*16);
  text+=",\"b_container_bytes\":"+std::to_string((bc-b0)*64);
  text+=",\"a_effective_bytes\":"+std::to_string(uint64_t(rows)*1024*(wa?2u:1u));
  text+=",\"b_effective_bytes\":"+std::to_string(uint64_t(1024)*8*(wb?2u:1u));
  text+=",\"s_initialization_and_refill_included\":true,\"cross_batch_load_overlap\":false}";
 }
 timed=false;return text+"]";
}
int main(int argc,char** argv){
 Verilated::commandArgs(argc,argv);ptr=new Vblock_feed_pair;
 try{reset();random_cases();overlap_and_reset();auto benchmarks=benchmark();ck(ab_concurrent>0,"S feeder never transferred A/B concurrently");
  std::cout<<"{\"passed\":true,\"cases\":32,\"checks\":"<<checks<<",\"cycles\":"<<cycles
   <<",\"a_handshakes\":"<<ac<<",\"b_handshakes\":"<<bc<<",\"s_wide_reads\":"<<mc
   <<",\"s_narrow_accesses\":"<<nc<<",\"t_captured_words\":"<<tc
   <<",\"a_b_same_cycle_transfers\":"<<ab_concurrent<<",\"cold_benchmarks\":"<<benchmarks<<"}\n";
 }catch(const std::exception& e){std::cerr<<"FAIL cycle="<<cycles<<": "<<e.what()<<"\n";return 1;}
}
