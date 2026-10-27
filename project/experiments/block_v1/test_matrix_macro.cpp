#include "Vblock_v1_m.h"
#include "verilated.h"
#include <array>
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <random>
#include <stdexcept>
using I128=__int128_t;
using U128=__uint128_t;
using Vec=std::array<int16_t,8>;
using Mat=std::array<Vec,8>;
struct Reply{U128 data;bool error,saturated;unsigned latency;};
static Vblock_v1_m dut;
static std::mt19937_64 rng(12120261027ULL);
static uint64_t checks=0,cycles=0;
static void require(bool ok,const char*why){++checks;if(!ok)throw std::runtime_error(why);}
static void tick(){dut.clk=0;dut.eval();dut.clk=1;dut.eval();++cycles;}
static U128 get_data(){U128 v=0;for(int n=3;n>=0;--n)v=(v<<32)|dut.rsp_data[n];return v;}
static void put_data(U128 v){for(int n=0;n<4;++n){dut.cmd_data[n]=uint32_t(v);v>>=32;}}
static Reply command(unsigned op,unsigned index,U128 data,bool error=false){
 require(dut.cmd_ready,"command input must be available");
 dut.rsp_ready=0;dut.cmd_valid=1;dut.cmd_op=op;dut.cmd_index=index;put_data(data);tick();dut.cmd_valid=0;
 unsigned latency=0;
 while(!dut.rsp_valid){tick();if(++latency>1000)throw std::runtime_error("response timeout");}
 Reply r{get_data(),bool(dut.rsp_error),bool(dut.rsp_saturated),latency};
 require(r.error==error,"wrong error response");
 unsigned hold=rng()%5;
 for(unsigned n=0;n<hold;++n){
  // A different command may be presented under backpressure; never accepted.
  dut.cmd_valid=1;dut.cmd_op=6;put_data(U128(rng())<<64|rng());
  require(!dut.cmd_ready,"response did not block new command");tick();
  require(dut.rsp_valid&&get_data()==r.data&&dut.rsp_error==r.error&&dut.rsp_saturated==r.saturated,
          "response changed while stalled");
 }
 dut.cmd_valid=0;dut.rsp_ready=1;tick();dut.rsp_ready=0;
 require(dut.cmd_ready,"did not release response");return r;
}
static U128 pack(const Vec&v){U128 r=0;for(int j=0;j<8;++j)r|=U128(uint16_t(v[j]))<<(16*j);return r;}
static std::array<int64_t,8> partial(){
 std::array<int64_t,8>r{};
 for(unsigned p=0;p<4;++p){auto x=command(3,p,0);r[2*p]=int64_t(x.data);r[2*p+1]=int64_t(x.data>>64);}
 return r;
}
static void load(const Vec&a,const Mat&b){command(0,0,pack(a));for(int i=0;i<8;++i)command(1,i,pack(b[i]));}
static void mac(bool wa,bool wb,bool clear,unsigned k,unsigned n){
 auto r=command(2,0,U128(wa)|(U128(wb)<<1)|(U128(clear)<<2)|(U128(k)<<4)|(U128(n)<<8));
 require(r.latency==3*(wa?3:1)*(wb?3:1)+1,"wrong MAC cycle count");
}
static I128 rne(I128 x,unsigned sh){
 if(!sh)return x;
 I128 q=x>>sh;U128 mask=(U128(1)<<sh)-1,rem=U128(x)&mask,half=U128(1)<<(sh-1);
 return q+(rem>half||(rem==half&&(q&1)));
}
static void final_matches(const std::array<I128,8>&x,unsigned sh,unsigned mode){
 int bits=mode==0?8:mode==1?16:32;
 I128 lo=-(I128(1)<<(bits-1)),hi=(I128(1)<<(bits-1))-1;
 for(int group=0;group<2;++group){auto r=command(5,group,U128(sh)|(U128(mode)<<8));bool sat=false;
  for(int j=0;j<4;++j){I128 y=rne(x[4*group+j],sh);if(y<lo){y=lo;sat=true;}if(y>hi){y=hi;sat=true;}
   require(int32_t(r.data>>(32*j))==int32_t(y),"final RNE/saturation mismatch");}
  require(r.saturated==sat,"wrong saturation flag");
 }
}
int main(int argc,char**argv){try{
 Verilated::commandArgs(argc,argv);dut.reset=1;dut.cmd_valid=0;dut.rsp_ready=0;tick();dut.reset=0;tick();
 command(3,0,0,true);command(4,0,0,true);command(5,0,0,true);command(15,0,0,true);
 command(2,0,(U128(1)<<4)|(U128(1)<<8)|4,true); // Uninitialized operands.
 command(1,8,0,true);
 const int16_t corners[]={-32768,-32767,-16385,-16384,-129,-128,-127,-1,0,1,127,128,16383,16384,32766,32767};
 std::array<int64_t,8> expected{};std::array<I128,8> merged{};
 for(unsigned test=0;test<1200;++test){
  bool wa=test&1,wb=test&2,clear=test%5==0||test==0;
  unsigned k=1+rng()%8,n=1+rng()%8;Vec a;Mat b;
  for(int j=0;j<8;++j){a[j]=test<128?corners[(test+j)%16]:int16_t(rng());
   for(int i=0;i<8;++i)b[i][j]=test<128?corners[(test/8+3*i+j)%16]:int16_t(rng());}
  // Include valid positive P15 probability codes as well as arbitrary S16.
  if(test%17==0){wa=true;wb=true;for(auto&v:a)v=int16_t(rng()&32767);}
  load(a,b);if(clear)expected.fill(0);
  for(unsigned i=0;i<n;++i)for(unsigned j=0;j<k;++j)
   expected[i]+=int64_t(wa?a[j]:int16_t(int8_t(a[j])))*(wb?b[i][j]:int16_t(int8_t(b[i][j])));
  mac(wa,wb,clear,k,n);require(partial()==expected,"matrix/tail/multi-tile integer mismatch");
  int32_t factor=int32_t(rng());unsigned shift=rng()%13;bool cm=test%7==0||test==0;
  auto r=command(4,0,U128(uint32_t(factor))|(U128(shift)<<32)|(U128(cm)<<39));
  require(r.latency==17,"wrong merge latency");if(cm)merged.fill(0);
  for(int i=0;i<8;++i)merged[i]+=I128(expected[i])*factor*(I128(1)<<shift);
  for(unsigned mode=0;mode<3;++mode)final_matches(merged,rng()%100,mode);
 }
 // Positive and negative exact half ties, plus shift 127.
 Vec a{};Mat b{};a[0]=1;for(int i=0;i<8;++i)b[i][0]=int16_t(i-4);
 load(a,b);mac(true,true,true,1,8);command(4,0,U128(1)|(U128(1)<<39));
 for(int i=0;i<8;++i)merged[i]=i-4;
 for(unsigned sh:{0U,1U,2U,3U,63U,126U,127U})for(unsigned mode=0;mode<3;++mode)final_matches(merged,sh,mode);
 command(5,2,0,true);command(5,0,U128(3)<<8,true);command(4,0,U128(64)<<32,true);
 command(2,0,(U128(9)<<4)|(U128(8)<<8),true); // Invalid K must preserve old state.
 require(partial()[0]==-4,"invalid command modified accumulation");
 // Overflow in a late lane must reject the whole merge, keeping all old lanes.
 a.fill(-32768);for(auto&row:b)row.fill(-32768);load(a,b);mac(true,true,true,8,8);
 for(unsigned j=0;j<5;++j)mac(true,true,false,8,8); // 48*2^30
 command(4,0,U128(0x7fffffffU)|(U128(63)<<32)|(U128(1)<<39),true);
 for(unsigned mode=0;mode<3;++mode)final_matches(merged,0,mode);
 // K<=65535 guard: zero data makes every accepted tile easy to compare.
 a.fill(0);for(auto&row:b)row.fill(0);load(a,b);mac(false,false,true,7,8);
 for(unsigned j=0;j<8191;++j)mac(false,false,false,8,8);
 require(partial()==std::array<int64_t,8>{},"zero long-K result");
 command(2,0,(U128(1)<<4)|(U128(8)<<8),true);
 require(partial()==std::array<int64_t,8>{},"K overflow modified state");
 command(6,0,0);command(3,0,0,true);command(5,0,0,true);
 dut.reset=1;tick();dut.reset=0;tick();command(3,0,0,true);command(5,0,0,true);
 std::cout<<"{\"passed\":true,\"random_and_corner_tiles\":1200,\"checks\":"<<checks
          <<",\"cycles\":"<<cycles<<",\"scope\":\"RTL integer/rounding/protocol/guard simulation; no PPA or model quality claim\"}\n";
 return 0;
}catch(const std::exception&e){std::cerr<<e.what()<<" at cycle "<<cycles<<"\n";return 1;}}
