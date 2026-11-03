#include "Vdram_m_fifo_tb.h"
#include "verilated.h"
#include <array>
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <map>
#include <memory>
#include <random>
#include <stdexcept>
#include <string>
#include <vector>
using Word=std::array<uint32_t,4>;
using Big=std::array<uint32_t,16>;
using I128=__int128_t;
using U128=__uint128_t;
static uint64_t checks=0;
static void ck(bool x,const std::string&s){++checks;if(!x)throw std::runtime_error(s);}
template<class T> static Word word(const T&x){return {x[0],x[1],x[2],x[3]};}
template<class T> static Big big(const T&x){Big b{};for(int i=0;i<16;++i)b[i]=x[i];return b;}
static U128 wide(const Word&w){U128 v=0;for(int j=3;j>=0;--j)v=(v<<32)|w[j];return v;}
struct Matrix {
 unsigned rows=8,tiles=4,k=8,n=8,bank=0;bool wa=false,wb=false;
 int16_t a[8][4][8]{},b[4][8][8]{};
};
struct Rig {
 std::unique_ptr<Vdram_m_fifo_tb> d=std::make_unique<Vdram_m_fifo_tb>();
 std::mt19937_64 rng;
 uint64_t t=0,core=0,mem=0,reqs=0,rsps=0,req_full=0,rsp_full=0,stall_until=0;
 uint64_t request_stall_until=0;
 unsigned mh,phase;
 bool pending=false;
 unsigned delay=0;
 Word response{};bool response_error=false;
 int64_t error_at=-1;
 std::map<uint64_t,Word> memory;
 std::vector<uint64_t> expected_addresses;
 unsigned issued=0,got_a=0,got_b=0;
 Matrix current;
 bool watch=false,corrupt=false;
 bool holda=false,holdb=false,holdq=false,holddone=false,holdrsp=false;
 Word olda{},oldrsp{};Big oldb{};
 uint64_t oldameta=0,oldbmeta=0,oldq=0;bool olddoneerr=false,oldrsperr=false;
 bool cmd_fire=false,load_fire=false;
 Rig(uint64_t seed,unsigned memhalf,unsigned p):rng(seed),mh(memhalf),phase(p){
  d->core_clk=0;d->mem_clk=0;d->reset=0;d->load_valid=0;d->done_ready=0;
  d->cmd_valid=0;d->rsp_ready=0;d->mem_rsp_valid=0;d->mem_req_ready=0;
  d->allow_a=0;d->allow_b=0;
 }
 void step(){
  ++t;bool ce=t%20==10,cf=t%20==0;
  bool me=t>=phase&&(t-phase)%(2*mh)==mh;
  bool mf=t>=phase&&(t-phase)%(2*mh)==0;
  cmd_fire=load_fire=false;
  if(cf)d->core_clk=0;if(mf)d->mem_clk=0;
  if(ce){
   d->allow_a=core>=stall_until&&rng()%5!=0;
   d->allow_b=core>=stall_until&&rng()%5!=0;
  }
  if(me){
   d->mem_req_ready=!d->reset&&!pending&&core>=request_stall_until&&rng()%4!=0;
   d->mem_rsp_valid=!d->reset&&pending&&delay==0;
   d->mem_rsp_error=response_error;
   for(int j=0;j<4;++j)d->mem_rsp_data[j]=response[j];
  }
  d->eval();
  bool qfire=me&&d->mem_req_valid&&d->mem_req_ready;
  bool rfire=me&&d->mem_rsp_valid&&d->mem_rsp_ready;
  uint64_t addr=d->mem_req_address;
  if(me&&!d->reset){
   ++mem;rsp_full+=d->response_fifo_full;
   if(holdq)ck(d->mem_req_valid&&addr==oldq,"memory request changed while blocked");
   holdq=d->mem_req_valid&&!d->mem_req_ready;oldq=addr;
  }
  if(ce&&!d->reset){
   ++core;req_full+=d->request_fifo_full;
   cmd_fire=d->cmd_valid&&d->cmd_ready;
   load_fire=d->load_valid&&d->load_ready;
   uint64_t am=d->a_bank|(d->a_row<<1)|(d->a_tile<<4)|(d->a_wide<<6);
   uint64_t bm=d->b_bank|(d->b_tile<<1)|(d->b_wide<<3)|(d->b_half<<4);
   if(holda)ck(d->a_valid&&word(d->a_data)==olda&&am==oldameta,"A changed under backpressure");
   if(holdb)ck(d->b_valid&&big(d->b_data)==oldb&&bm==oldbmeta,"B changed under backpressure");
   holda=d->a_valid&&!d->a_ready;olda=word(d->a_data);oldameta=am;
   holdb=d->b_valid&&!d->b_ready;oldb=big(d->b_data);oldbmeta=bm;
   if(holddone)ck(d->done_valid&&bool(d->done_error)==olddoneerr&&!d->load_ready,"completion unstable");
   holddone=d->done_valid&&!d->done_ready;olddoneerr=d->done_error;
   if(holdrsp)ck(d->rsp_valid&&word(d->rsp_data)==oldrsp&&bool(d->rsp_error)==oldrsperr,"M response unstable");
   holdrsp=d->rsp_valid&&!d->rsp_ready;oldrsp=word(d->rsp_data);oldrsperr=d->rsp_error;
   if(watch&&d->a_valid&&d->a_ready){
    ck(d->a_bank==current.bank&&bool(d->a_wide)==current.wa,"A bank/format");
    ck(d->a_row<current.rows&&d->a_tile<current.tiles,"A tag range");
    ck(d->a_row==got_a/current.tiles&&d->a_tile==got_a%current.tiles,"A order");
    Word expect{};
    for(unsigned k=0;k<8;++k){
     unsigned v=current.wa?uint16_t(current.a[d->a_row][d->a_tile][k]):uint8_t(current.a[d->a_row][d->a_tile][k]);
     unsigned bit=k*(current.wa?16:8);expect[bit/32]|=uint32_t(v)<<(bit%32);
    }
    ck(word(d->a_data)==expect,"A payload");++got_a;
   }
   if(watch&&d->b_valid&&d->b_ready){
    ck(d->b_bank==current.bank&&bool(d->b_wide)==current.wb,"B bank/format");
    ck(d->b_tile==got_b/(current.wb?2:1)&&d->b_half==(current.wb?got_b%2:0),"B order");
    Big expect{};
    for(unsigned j=0;j<(current.wb?32u:64u);++j){
     unsigned ix=j+(current.wb?32*d->b_half:0);
     int16_t v=current.b[d->b_tile][ix/8][ix%8];
     unsigned bit=j*(current.wb?16:8);
     expect[bit/32]|=uint32_t(current.wb?uint16_t(v):uint8_t(v))<<(bit%32);
    }
    ck(big(d->b_data)==expect,"B payload");++got_b;
   }
  }
  if(ce)d->core_clk=1;if(me)d->mem_clk=1;
  d->eval();
  if(me&&!d->reset){
   if(pending&&delay)--delay;
   if(rfire){ck(pending,"orphan response");pending=false;++rsps;}
   if(qfire){
    ck(!pending,"external outstanding >1");
    ck(issued<expected_addresses.size()&&addr==expected_addresses[issued],"request address/order");
    auto it=memory.find(addr);ck(it!=memory.end(),"unmapped read");
    response=it->second;response_error=int64_t(issued)==error_at;
    if(corrupt&&issued==0)response[0]^=1;
    ++issued;++reqs;pending=true;delay=1+rng()%9;
   }
  }
  ck(core<2000000,"watchdog");
 }
 void cores(unsigned n){uint64_t end=core+n;while(core<end)step();}
 template<class P>void until(P p,const std::string&s,unsigned limit=30000){
  auto start=core;while(!p()){step();ck(core-start<limit,s);}
 }
 void reset(bool abandon=false){
  d->reset=1;d->load_valid=0;d->cmd_valid=0;d->done_ready=0;d->rsp_ready=0;
  pending=false;watch=false;
  holda=holdb=holdq=holddone=holdrsp=false;
  for(unsigned i=0;i<300;++i)step();
  d->reset=0;stall_until=request_stall_until=0;
  cores(12);
  ck(!d->done_valid&&!d->rsp_valid&&!d->a_valid&&!d->b_valid,"reset leaves old publication");
  if(abandon)ck(!d->loading,"aborted load still active");
 }
 Word cmd(unsigned op,unsigned index,uint64_t data,bool error=false){
  until([&]{return bool(d->cmd_ready);},"cmd ready timeout");
  d->cmd_op=op;d->cmd_index=index;d->cmd_data=data;d->cmd_valid=1;
  until([&]{return cmd_fire;},"cmd handshake");
  d->cmd_valid=0;
  until([&]{return bool(d->rsp_valid);},"M compute timeout");
  auto v=word(d->rsp_data);
  ck(bool(d->rsp_error)==error,"M error flag");
  cores(rng()%4+1);
  d->rsp_ready=1;cores(1);d->rsp_ready=0;return v;
 }
 void prepare(const Matrix&m){
  current=m;memory.clear();expected_addresses.clear();issued=got_a=got_b=0;error_at=-1;watch=true;
  constexpr uint64_t abase=0x100001000ULL,bbase=0x200002000ULL;
  for(unsigned t0=0;t0<m.tiles;++t0){
   std::vector<uint8_t> bytes;
   for(unsigned n=0;n<8;++n)for(unsigned k=0;k<8;++k){
    uint16_t v=m.b[t0][n][k];bytes.push_back(uint8_t(v));if(m.wb)bytes.push_back(uint8_t(v>>8));
   }
   for(unsigned p=0;p<bytes.size()/16;++p){
    Word w{};for(unsigned j=0;j<16;++j)w[j/4]|=uint32_t(bytes[p*16+j])<<(8*(j%4));
    auto addr=bbase+t0*(m.wb?128:64)+p*16;memory[addr]=w;expected_addresses.push_back(addr);
   }
  }
  for(unsigned r=0;r<m.rows;++r)for(unsigned ti=0;ti<m.tiles;++ti){
   Word w{};
   for(unsigned k=0;k<8;++k){
    unsigned v=m.wa?uint16_t(m.a[r][ti][k]):uint8_t(m.a[r][ti][k]);
    unsigned bit=k*(m.wa?16:8);w[bit/32]|=uint32_t(v)<<(bit%32);
   }
   auto addr=abase+(r*m.tiles+ti)*16;memory[addr]=w;expected_addresses.push_back(addr);
  }
  d->load_bank=m.bank;d->load_rows=m.rows;d->load_tiles=m.tiles;
  d->load_a_wide=m.wa;d->load_b_wide=m.wb;d->load_a_base=abase;d->load_b_base=bbase;
 }
 uint64_t load(bool error=false){
  auto start=core;until([&]{return bool(d->load_ready);},"load ready");
  d->load_valid=1;until([&]{return load_fire;},"load accept");d->load_valid=0;
  until([&]{return bool(d->done_valid);},"load completion timeout");
  ck(bool(d->done_error)==error,"load error completion");
  ck(issued==expected_addresses.size()&&!pending,"load done before all returns");
  if(!error){
   ck(got_a==current.rows*current.tiles,"missing A packets");
   ck(got_b==current.tiles*(current.wb?2:1),"missing B packets");
  }
  cores(4);d->done_ready=1;cores(1);d->done_ready=0;watch=false;return core-start;
 }
 void invalid(unsigned rows,unsigned tiles,uint64_t a,uint64_t b){
  until([&]{return bool(d->load_ready);},"invalid ready");
  auto before=reqs;watch=false;expected_addresses.clear();issued=0;
  d->load_rows=rows;d->load_tiles=tiles;d->load_a_base=a;d->load_b_base=b;
  d->load_valid=1;until([&]{return load_fire;},"invalid accept");d->load_valid=0;
  until([&]{return bool(d->done_valid);},"invalid reject");
  ck(d->done_error,"bad descriptor accepted");cores(8);ck(reqs==before,"bad descriptor did memory IO");
  d->done_ready=1;cores(1);d->done_ready=0;
 }
};
static Matrix matrix(Rig&r,unsigned i){
 Matrix m;m.rows=1+i%8;m.tiles=1+(i/8)%4;m.k=1+(i*3)%8;m.n=1+(i*5)%8;
 m.bank=i%2;m.wa=i&1;m.wb=i&2;
 for(auto&row:m.a)for(auto&tile:row)for(auto&v:tile)v=m.wa?int16_t(r.rng()):int8_t(r.rng());
 for(auto&tile:m.b)for(auto&row:tile)for(auto&v:row)v=m.wb?int16_t(r.rng()):int8_t(r.rng());
 return m;
}
static void compute(Rig&r,const Matrix&m){
 int16_t factor=-3;unsigned shift=2;
 r.cmd(4,0,uint16_t(factor)|(uint64_t(shift)<<16));
 uint64_t desc=unsigned(m.wa)|(unsigned(m.wb)<<1)|4|(m.k<<4)|(m.n<<8)|(m.tiles<<12)|(m.rows<<15);
 r.cmd(10,m.bank*32,desc);
 for(unsigned row=0;row<m.rows;++row)for(unsigned pair=0;pair<4;++pair){
  auto data=wide(r.cmd(3,row*8+pair,0));
  for(unsigned lane=0;lane<2;++lane){
   unsigned n=2*pair+lane;int64_t sum=0;
   if(n<m.n)for(unsigned tile=0;tile<m.tiles;++tile)
    for(unsigned k=0;k<(tile+1==m.tiles?m.k:8);++k)
     sum+=int64_t(m.a[row][tile][k])*m.b[tile][n][k];
   int64_t expected=sum*factor*(int64_t(1)<<shift);
   ck(int64_t(data>>(64*lane))==expected,"independent matrix oracle mismatch");
  }
 }
}
int main(int argc,char**argv){try{
 Verilated::commandArgs(argc,argv);
 uint64_t seed=argc>1?std::strtoull(argv[1],nullptr,10):173;
 unsigned mh=argc>2?std::atoi(argv[2]):6,phase=argc>3?std::atoi(argv[3]):3;
 Rig r(seed,mh,phase);r.corrupt=argc>4&&std::string(argv[4])=="corrupt";
 r.reset();unsigned cases=0;uint64_t load_cycles=0;
 for(unsigned i=0;i<128;++i){
  r.cmd(6,0,0);auto m=matrix(r,i);r.prepare(m);
  if(i==31){r.stall_until=r.core+700;r.request_stall_until=r.core+25;}
  load_cycles+=r.load();compute(r,m);++cases;
 }
 // Invalid lengths, alignment and 40-bit overflow issue no memory reads.
 r.invalid(0,1,0x1000,0x2000);r.invalid(9,1,0x1000,0x2000);
 r.invalid(1,0,0x1000,0x2000);r.invalid(1,5,0x1000,0x2000);
 r.invalid(1,1,0x1001,0x2000);r.invalid(1,1,0x1000,0x2001);
 r.invalid(8,4,(1ULL<<40)-16,0x2000);r.invalid(1,4,0x1000,(1ULL<<40)-16);
 // Read failure drains outstanding work; caller invalidates the destination bank.
 auto e=matrix(r,31);r.cmd(6,0,0);r.prepare(e);r.error_at=5;r.load(true);
 r.cmd(11,e.bank,0);
 uint64_t desc=unsigned(e.wa)|(unsigned(e.wb)<<1)|4|(8<<4)|(8<<8)|(e.tiles<<12)|(e.rows<<15);
 r.cmd(10,e.bank*32,desc,true);
 auto good=matrix(r,19);r.prepare(good);r.load();compute(r,good);++cases;
 // Reset with accepted external request and queued transfers; reset model too.
 auto a=matrix(r,31);r.cmd(6,0,0);r.prepare(a);r.stall_until=r.core+10000;
 r.d->load_valid=1;r.until([&]{return r.load_fire;},"reset load accept");r.d->load_valid=0;
 r.until([&]{return r.pending;},"no in-flight reset coverage");
 r.reset(true);r.cmd(6,0,0);r.prepare(a);r.load();compute(r,a);++cases;
 ck(r.req_full>0&&r.rsp_full>0,"full boundary not covered");
 ck(r.reqs==r.rsps+1,"reset must account for exactly one abandoned request");
 std::cout<<"{\"passed\":true,\"seed\":"<<seed<<",\"mem_half_quanta\":"<<mh<<",\"core_half_quanta\":10,\"phase_quanta\":"<<phase
 <<",\"checks\":"<<checks<<",\"core_cycles\":"<<r.core<<",\"mem_cycles\":"<<r.mem<<",\"matrix_cases\":"<<cases
 <<",\"read_requests\":"<<r.reqs<<",\"read_responses\":"<<r.rsps<<",\"request_full_cycles\":"<<r.req_full
 <<",\"response_full_cycles\":"<<r.rsp_full<<",\"sum_128_load_cycles\":"<<load_cycles<<"}\n";
 return 0;
}catch(const std::exception&e){std::cerr<<"FAIL "<<e.what()<<"\n";return 1;}}
