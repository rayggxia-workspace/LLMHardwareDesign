#include "Vblock_v1_m.h"
#include "verilated.h"
#include <array>
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <random>
#include <stdexcept>
#include <vector>
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
struct Transfer{unsigned op,index;U128 data;};
static std::vector<Transfer> packed(unsigned bank,const std::vector<Vec>&aa,const std::vector<Mat>&bb,bool wa,bool wb){
 std::vector<Transfer> q;
 for(unsigned t=0;t<aa.size();++t){
  unsigned base=bank*32+t*8;U128 a=0;
  for(unsigned j=0;j<8;++j)a|=wa?U128(uint16_t(aa[t][j]))<<(16*j):U128(uint8_t(aa[t][j]))<<(8*j);
  q.push_back({7,base+unsigned(wa),a});
  for(unsigned c=0;c<(wb?8:4);++c){U128 b=0;
   if(wb)b=pack(bb[t][c]);
   else for(unsigned j=0;j<16;++j)b|=U128(uint8_t(bb[t][2*c+j/8][j%8]))<<(8*j);
   q.push_back({wb?9u:8u,base+c,b});
  }
 }
 return q;
}
static U128 descriptor(bool wa,bool wb,bool clear,unsigned k,unsigned n,unsigned tiles){return U128(wa)|(U128(wb)<<1)|(U128(clear)<<2)|(U128(k)<<4)|(U128(n)<<8)|(U128(tiles)<<12);}
static void packed_cases(){
 for(unsigned test=0;test<240;++test){
  unsigned bank=test%2,tiles=1+rng()%4,k=1+rng()%8,n=1+rng()%8;bool wa=test&1,wb=test&2;
  std::vector<Vec> aa(tiles);std::vector<Mat> bb(tiles);std::array<int64_t,8> expected{};
  for(unsigned t=0;t<tiles;++t)for(unsigned j=0;j<8;++j){
   aa[t][j]=int16_t(rng());for(auto&row:bb[t])row[j]=int16_t(rng());
  }
  for(auto w:packed(bank,aa,bb,wa,wb))command(w.op,w.index,w.data);
  for(unsigned t=0;t<tiles;++t)for(unsigned row=0;row<n;++row)for(unsigned j=0;j<(t+1==tiles?k:8);++j)
   expected[row]+=int64_t(wa?aa[t][j]:int16_t(int8_t(aa[t][j])))*(wb?bb[t][row][j]:int16_t(int8_t(bb[t][row][j])));
  auto r=command(10,bank*32,descriptor(wa,wb,true,k,n,tiles));
  require(r.data==(U128(1)<<127),"tagged descriptor completion");
  require(r.latency==tiles*(wa?3:1)*(wb?3:1)+3,"resident tile pipeline fill/drain latency");
  require(partial()==expected,"packed multi-tile wide/tail mismatch");
 }
 // Existing active bank runs while twenty tightly packed next-bank transfers
 // are offered continuously. Finite response holding is randomly stalled.
 std::vector<Vec> aa(4);std::vector<Mat> bb(4);std::array<int64_t,8> e{};
 for(unsigned t=0;t<4;++t)for(unsigned j=0;j<8;++j){aa[t][j]=j+1;for(unsigned r=0;r<8;++r){bb[t][r][j]=r+1;e[r]+=int64_t(j+1)*(r+1);}}
 for(auto w:packed(0,aa,bb,true,true))command(w.op,w.index,w.data);
 auto q=packed(1,aa,bb,false,false);dut.cmd_valid=1;dut.cmd_op=10;dut.cmd_index=0;put_data(descriptor(true,true,true,8,8,4));dut.rsp_ready=1;tick();
 unsigned sent=0,acks=0,overlap=0,elapsed=0;bool completed=false,held=false;U128 last=0;
 while(sent<q.size()||acks<q.size()||!completed){
  require(elapsed++<2000,"overlapped descriptor timeout");
  dut.clk=0;dut.cmd_valid=sent<q.size();
  if(dut.cmd_valid){auto w=q[sent];dut.cmd_op=w.op;dut.cmd_index=w.index;put_data(w.data);}
  dut.rsp_ready=rng()%4!=0;dut.eval();
  if(held)require(dut.rsp_valid&&get_data()==last&&!dut.rsp_error,"overlapped response must hold");
  bool push=dut.cmd_valid&&dut.cmd_ready,pop=dut.rsp_valid&&dut.rsp_ready;
  if(push){++sent;if(!completed)++overlap;}
  if(pop){require(!dut.rsp_error,"unexpected overlap error");if(get_data()==(U128(1)<<127))completed=true;else{require(get_data()==0,"loader acknowledgement tag");++acks;}}
  held=dut.rsp_valid&&!dut.rsp_ready;last=get_data();tick();
 }
 dut.cmd_valid=0;dut.rsp_ready=0;dut.eval();
 require(overlap>=16,"finite preload must overlap core execution");require(partial()==e,"overlap changed active operands");
 command(10,32,descriptor(false,false,false,8,8,4));for(auto&v:e)v*=2;require(partial()==e,"preloaded bank accumulation");
 command(6,0,0);command(10,0,descriptor(false,false,true,8,8,4),true);
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
  require(r.latency==33,"wrong staged merge latency");if(cm)merged.fill(0);
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
 packed_cases();
 std::cout<<"{\"packed_descriptor_cases\":240,\"overlapped_preload_words\":20,\"passed\":true,\"random_and_corner_tiles\":1200,\"checks\":"<<checks
          <<",\"cycles\":"<<cycles<<",\"scope\":\"RTL integer/rounding/protocol/guard simulation; no PPA or model quality claim\"}\n";
 return 0;
}catch(const std::exception&e){std::cerr<<e.what()<<" at cycle "<<cycles<<"\n";return 1;}}
