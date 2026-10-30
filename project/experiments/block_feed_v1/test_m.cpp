#include "Vblock_feed_m.h"
#include "verilated.h"
#include <array>
#include <cstdint>
#include <iostream>
#include <random>
#include <stdexcept>
#include <string>
#include <vector>
using I128=__int128_t;
using U128=__uint128_t;
using Vec=std::array<int16_t,8>;
using Inputs=std::array<std::array<Vec,4>,8>;
using Weights=std::array<std::array<Vec,8>,4>;
using Partial=std::array<std::array<int64_t,8>,8>;
using Full=std::array<I128,8>;
static Vblock_feed_m* dut_ptr;
#define d (*dut_ptr)
static std::mt19937_64 rng(13020261029ULL);
static uint64_t checks=0,cycles=0,cases=0;
static bool timed=false;
static void ck(bool ok,const std::string& msg){++checks;if(!ok)throw std::runtime_error(msg);}
static void tick(){d.clk=0;d.eval();d.clk=1;d.eval();++cycles;d.clk=0;d.eval();}
static U128 response(){U128 x=0;for(int i=3;i>=0;--i)x=(x<<32)|d.rsp_data[i];return x;}
static void reset(){
 d.reset=1;d.cmd_valid=0;d.a_valid=0;d.b_valid=0;d.rsp_ready=0;tick();tick();d.reset=0;d.eval();
}
struct Reply{U128 data;bool sat;unsigned latency;};
static Reply cmd(unsigned op,unsigned index,uint64_t data,bool error=false){
 ck(d.cmd_ready,"command not ready");d.cmd_valid=1;d.cmd_op=op;d.cmd_index=index;d.cmd_data=data;
 d.rsp_ready=0;tick();d.cmd_valid=0;
 unsigned latency=0;while(!d.rsp_valid){ck(++latency<5000,"command timeout");tick();}
 Reply r{response(),bool(d.rsp_saturated),latency};ck(bool(d.rsp_error)==error,"response error flag");
 for(unsigned i=0,n=timed?0:rng()%4;i<n;++i){
  d.cmd_valid=1;d.cmd_op=6;d.cmd_index=0;d.cmd_data=0;d.eval();ck(!d.cmd_ready,"held response admits command");
  tick();ck(d.rsp_valid&&response()==r.data&&bool(d.rsp_error)==error&&bool(d.rsp_saturated)==r.sat,"unstable response");
 }
 d.cmd_valid=0;d.rsp_ready=1;tick();d.rsp_ready=0;d.eval();return r;
}
static void put_a(unsigned bank,unsigned row,unsigned tile,const Vec& a,bool wide){
 U128 data=0;for(unsigned j=0;j<8;++j)data|=wide?U128(uint16_t(a[j]))<<(16*j):U128(uint8_t(a[j]))<<(8*j);
 d.a_valid=1;d.a_bank=bank;d.a_row=row;d.a_tile=tile;d.a_wide=wide;
 for(unsigned j=0;j<4;++j){d.a_data[j]=uint32_t(data);data>>=32;}
 d.eval();ck(d.a_ready,"A not accepted in free bank");tick();d.a_valid=0;d.eval();
}
static void prepare_b(unsigned bank,unsigned tile,const Weights& b,bool wide,unsigned half){
 d.b_bank=bank;d.b_tile=tile;d.b_wide=wide;d.b_half=half;
 for(unsigned j=0;j<16;++j)d.b_data[j]=0;
 for(unsigned j=0;j<(wide?32u:64u);++j){
  unsigned index=j+(wide?32*half:0),n=index/8,k=index%8;
  if(wide)d.b_data[j/2]|=uint32_t(uint16_t(b[tile][n][k]))<<(16*(j%2));
  else d.b_data[j/4]|=uint32_t(uint8_t(b[tile][n][k]))<<(8*(j%4));
 }
}
static void put_b(unsigned bank,unsigned tile,const Weights& b,bool wide){
 for(unsigned h=0;h<(wide?2u:1u);++h){prepare_b(bank,tile,b,wide,h);d.b_valid=1;d.eval();ck(d.b_ready,"B not ready");tick();}
 d.b_valid=0;d.eval();
}
static uint64_t descriptor(bool wa,bool wb,bool clear,unsigned k,unsigned n,unsigned tiles,unsigned rows){
 return unsigned(wa)|(unsigned(wb)<<1)|(unsigned(clear)<<2)|(k<<4)|(n<<8)|(tiles<<12)|(rows<<15);
}
static void reference(Partial& p,const Inputs& a,const Weights& b,bool wa,bool wb,unsigned rows,unsigned tiles,unsigned k,unsigned n,bool clear){
 for(unsigned r=0;r<rows;++r){
  if(clear)p[r].fill(0);
  for(unsigned t=0;t<tiles;++t)for(unsigned j=0;j<(t+1==tiles?k:8);++j)for(unsigned o=0;o<n;++o){
   int64_t av=wa?a[r][t][j]:int8_t(a[r][t][j]);
   int64_t bv=wb?b[t][o][j]:int8_t(b[t][o][j]);p[r][o]+=av*bv;
  }
 }
}
static void check_partial(const Partial& p,unsigned rows){
 for(unsigned r=0;r<rows;++r)for(unsigned g=0;g<4;++g){
  auto v=cmd(3,r*8+g,0).data;
  ck(int64_t(v)==p[r][2*g]&&int64_t(v>>64)==p[r][2*g+1],"partial/reference mismatch row="+std::to_string(r));
 }
}
static I128 rne(I128 x,unsigned shift){
 if(!shift)return x;I128 q=x>>shift;U128 rem=U128(x)&((U128(1)<<shift)-1),half=U128(1)<<(shift-1);
 return q+(rem>half||(rem==half&&(q&1)));
}
static void check_final(unsigned row,const Full& full,unsigned shift,unsigned mode){
 unsigned bits=mode==0?8:mode==1?16:32;I128 lo=-(I128(1)<<(bits-1)),hi=(I128(1)<<(bits-1))-1;
 for(unsigned g=0;g<2;++g){auto reply=cmd(5,row*8+g,shift|(mode<<8));bool sat=false;
  ck(reply.latency==3,"final stages latency");
  for(unsigned j=0;j<4;++j){I128 v=rne(full[4*g+j],shift);if(v<lo){v=lo;sat=true;}if(v>hi){v=hi;sat=true;}
   ck(int32_t(reply.data>>(32*j))==int32_t(v),"final RNE/saturation mismatch");}
  ck(reply.sat==sat,"saturation flag");
 }
}
static void fill(Inputs& a,Weights& b,unsigned test){
 for(auto& row:a)for(auto& tile:row)for(auto& v:tile)v=int16_t(rng());
 for(auto& tile:b)for(auto& row:tile)for(auto& v:row)v=int16_t(rng());
 if(test%7==0){
  constexpr int16_t edge[]={-32768,-32767,-16384,-129,-128,-1,0,1,2,127,128,16383,32767};
  for(unsigned r=0;r<8;++r)for(unsigned t=0;t<4;++t)for(unsigned k=0;k<8;++k)a[r][t][k]=edge[(r+t+k)%13];
  for(unsigned t=0;t<4;++t)for(unsigned n=0;n<8;++n)for(unsigned k=0;k<8;++k)b[t][n][k]=edge[(t+3*n+k)%13];
 }
}
static void numerical_cases(){
 for(unsigned test=0;test<128;++test){
  cmd(6,0,0);Inputs a{};Weights b{};Partial p{};fill(a,b,test);
  bool wa=test&1,wb=test&2;unsigned bank=(test/4)%2,rows=1+(test/4)%8,tiles=1+test/32,k=1+rng()%8,n=1+rng()%8;
  for(unsigned t=0;t<tiles;++t){put_b(bank,t,b,wb);for(unsigned r=0;r<rows;++r)put_a(bank,r,t,a[r][t],wa);}
  auto v=cmd(10,bank*32,descriptor(wa,wb,true,k,n,tiles,rows));
  ck(v.data==(U128(1)<<127),"completion tag");
  ck(v.latency==rows*tiles*(wa?3:1)*(wb?3:1)+4,"multirow issue/drain cycles");
  reference(p,a,b,wa,wb,rows,tiles,k,n,true);check_partial(p,rows);
  // Replace A only. B must remain valid and be reused by all input rows.
  for(unsigned r=0;r<rows;++r)for(unsigned t=0;t<tiles;++t){for(auto& x:a[r][t])x=int16_t(rng());put_a(bank,r,t,a[r][t],wa);}
  cmd(10,bank*32,descriptor(wa,wb,false,k,n,tiles,rows));
  reference(p,a,b,wa,wb,rows,tiles,k,n,false);check_partial(p,rows);
  for(unsigned r=0;r<rows;++r){
   int32_t factor=test%3==0?INT32_MIN:int32_t(rng());unsigned shift=test%9;
   ck(cmd(4,r*8,uint32_t(factor)|(uint64_t(shift)<<32)|(uint64_t(1)<<39)).latency==49,"merge latency");
   Full full{};for(unsigned j=0;j<8;++j)full[j]=I128(p[r][j])*factor*(I128(1)<<shift);
   check_final(r,full,test%64,test%3);
   cmd(4,r*8,uint32_t(-3));for(unsigned j=0;j<8;++j)full[j]+=I128(p[r][j])*-3;
   check_final(r,full,1+test%63,(test+1)%3);
  }
  ++cases;
 }
}
static void protections(){
 reset();cmd(3,0,0,true);cmd(5,0,0,true);cmd(4,0,uint64_t(1)<<39,true);
 cmd(10,0,descriptor(false,false,true,8,8,1,1),true);
 Inputs a{};Weights b{};Partial p{};fill(a,b,0);
 put_a(0,0,0,a[0][0],true);prepare_b(0,0,b,true,1);d.b_valid=1;d.eval();ck(!d.b_ready,"orphan high B half");tick();d.b_valid=0;
 prepare_b(0,0,b,true,0);d.b_valid=1;tick();d.b_valid=0;
 cmd(10,0,descriptor(true,true,true,8,8,1,1),true);
 put_b(0,0,b,true);cmd(10,0,descriptor(true,true,true,8,8,1,1));
 reference(p,a,b,true,true,1,1,8,8,true);check_partial(p,1);
 cmd(10,0,descriptor(true,true,false,8,7,1,1),true); // incompatible append width
 cmd(10,1,descriptor(true,true,true,8,8,1,1),true); // reserved index
 cmd(10,0,descriptor(true,true,true,8,8,1,0),true);
 cmd(10,0,descriptor(true,true,true,8,8,1,9),true);
 cmd(10,0,descriptor(true,true,true,8,8,1,1)|(uint64_t(1)<<63),true);
 cmd(11,0,0);cmd(10,0,descriptor(true,true,true,8,8,1,1),true);
 // Reset must revoke prior operands/results, including incomplete B halves.
 reset();cmd(3,0,0,true);cmd(10,0,descriptor(true,true,true,8,8,1,1),true);
}
static void overlap(){
 reset();Inputs a{};Weights b{};Partial p{};fill(a,b,7);
 for(unsigned t=0;t<4;++t){put_b(0,t,b,true);for(unsigned r=0;r<8;++r)put_a(0,r,t,a[r][t],true);}
 ck(d.cmd_ready,"overlap start");d.cmd_valid=1;d.cmd_op=10;d.cmd_index=0;d.cmd_data=descriptor(true,true,true,8,8,4,8);tick();d.cmd_valid=0;
 // The executing bank must reject both input channels. The other bank accepts
 // A and a whole64B B tile on the very same edge.
 d.a_valid=1;d.a_bank=0;prepare_b(0,0,b,false,0);d.b_valid=1;d.eval();
 ck(!d.a_ready&&!d.b_ready,"executing bank overwritten");
 d.a_bank=1;d.a_row=0;d.a_tile=0;d.a_wide=false;
 for(unsigned j=0;j<4;++j)d.a_data[j]=0;d.a_data[0]=0x01010101;d.a_data[1]=0x01010101;
 prepare_b(1,0,b,false,0);d.eval();ck(d.a_ready&&d.b_ready,"independent A/B channel concurrency");tick();
 d.a_valid=0;d.b_valid=0;
 unsigned wait=0;while(!d.rsp_valid){ck(++wait<1000,"overlap timeout");tick();}
 ck(!d.rsp_error&&response()==(U128(1)<<127),"overlap completion");d.rsp_ready=1;tick();d.rsp_ready=0;
 reference(p,a,b,true,true,8,4,8,8,true);check_partial(p,8);
 // Check every B lane written by the single512-bit transfer, not only low128.
 for(unsigned j=0;j<8;++j)a[0][0][j]=1;
 cmd(10,32,descriptor(false,false,true,8,8,1,1));
 reference(p,a,b,false,false,1,1,8,8,true);check_partial(p,1);
}
static void boundary_cases(){
 reset();Inputs a{};Weights b{};Partial p{};
 for(auto& row:a)for(auto& tile:row)tile.fill(-32768);
 for(auto& tile:b)for(auto& row:tile)row.fill(-32768);
 for(unsigned t=0;t<4;++t){put_b(0,t,b,true);put_a(0,0,t,a[0][t],true);}
 cmd(10,0,descriptor(true,true,true,8,8,4,1));
 reference(p,a,b,true,true,1,4,8,8,true);
 Full full{};for(auto& v:full)v=-(I128(1)<<126);
 cmd(4,0,uint32_t(INT32_MIN)|(uint64_t(60)<<32)|(uint64_t(1)<<39));check_final(0,full,127,2);
 cmd(4,0,uint32_t(INT32_MIN)|(uint64_t(60)<<32));for(auto& v:full)v*=2;check_final(0,full,127,2);
 cmd(4,0,uint32_t(INT32_MIN)|(uint64_t(60)<<32),true);check_final(0,full,127,2);
 cmd(4,0,uint32_t(INT32_MIN)|(uint64_t(63)<<32)|(uint64_t(1)<<39),true);check_final(0,full,127,2);
 // Reach the legal complete-K limit without a DUT state force, then reject
 // the next descriptor and retain the exact prior partial sum.
 reset();for(auto& row:a)for(auto& tile:row)tile.fill(1);
 for(auto& tile:b)for(auto& row:tile)row.fill(1);
 for(unsigned t=0;t<4;++t){put_b(0,t,b,false);put_a(0,0,t,a[0][t],false);}
 for(unsigned i=0;i<2047;++i)cmd(10,0,descriptor(false,false,i==0,8,8,4,1));
 cmd(10,0,descriptor(false,false,false,7,8,4,1)); // 65504+31=65535
 p[0].fill(65535);check_partial(p,1);
 cmd(10,0,descriptor(false,false,false,1,8,1,1),true);check_partial(p,1);
 // Signed ties, including negative odd/even quotients.
 cmd(6,0,0);for(unsigned j=0;j<8;++j)b[0][j][0]=int16_t(2*int(j)-7);
 put_b(0,0,b,false);put_a(0,0,0,a[0][0],false);
 cmd(10,0,descriptor(false,false,true,1,8,1,1));cmd(4,0,uint64_t(1)|(uint64_t(1)<<39));
 for(unsigned j=0;j<8;++j)full[j]=2*int(j)-7;check_final(0,full,1,2);
}
struct Measurement {unsigned rows,format;uint64_t load_compute,finish,total,macs,a_bytes,b_bytes;};
static std::vector<Measurement> bench(){
 timed=true;std::vector<Measurement> result;
 for(unsigned rows:{1u,8u})for(unsigned format=0;format<4;++format){
  reset();Inputs a{};Weights b{};Partial p{};bool wa=format&1,wb=format&2;
  for(unsigned r=0;r<8;++r)for(auto& tile:a[r])for(unsigned j=0;j<8;++j)tile[j]=(j%2?-1:1)*int(j+1)*(wa?1234:1);
  for(auto& tile:b)for(unsigned n=0;n<8;++n)for(unsigned j=0;j<8;++j)tile[n][j]=int(n+1)*(int(j%3)-1)*(wb?257:1);
  auto start=cycles;
  for(unsigned group=0;group<32;++group){
   unsigned bank=group%2;
   // This cold benchmark includes every A/B load; channels run independently
   // on the same clock edges. It deliberately does NOT assume a free DMA.
   unsigned a_sent=0,b_sent=0,total_a=rows*4,total_b=4*(wb?2:1);
   while(a_sent<total_a||b_sent<total_b){
    d.a_valid=a_sent<total_a;d.a_bank=bank;d.a_row=a_sent/4;d.a_tile=a_sent%4;d.a_wide=wa;
    U128 av=0;for(unsigned j=0;j<8;++j)av|=wa?U128(uint16_t(a[0][0][j]))<<(16*j):U128(uint8_t(a[0][0][j]))<<(8*j);
    for(unsigned j=0;j<4;++j){d.a_data[j]=uint32_t(av);av>>=32;}
    d.b_valid=b_sent<total_b;if(d.b_valid)prepare_b(bank,b_sent/(wb?2:1),b,wb,wb?b_sent%2:0);d.eval();
    bool af=d.a_valid&&d.a_ready,bf=d.b_valid&&d.b_ready;tick();a_sent+=af;b_sent+=bf;
   }
   d.a_valid=d.b_valid=0;
   cmd(10,bank*32,descriptor(wa,wb,group==0,8,8,4,rows));
   reference(p,a,b,wa,wb,rows,4,8,8,group==0);
  }
  auto finish_start=cycles;
  check_partial(p,rows);
  for(unsigned r=0;r<rows;++r){cmd(4,r*8,uint64_t(1)|(uint64_t(1)<<39));
   Full full{};for(unsigned n=0;n<8;++n)full[n]=p[r][n];check_final(r,full,8,2);
  }
  result.push_back({rows,format,finish_start-start,cycles-finish_start,cycles-start,uint64_t(rows)*1024*8,
                    uint64_t(rows)*1024*(wa?2u:1u),uint64_t(1024)*8*(wb?2u:1u)});
 }
 timed=false;return result;
}
int main(int argc,char** argv){
 Verilated::commandArgs(argc,argv);dut_ptr=new Vblock_feed_m;
 try{reset();protections();numerical_cases();overlap();boundary_cases();auto measurements=bench();
  std::cout<<"{\"passed\":true,\"cases\":"<<cases<<",\"checks\":"<<checks<<",\"cycles\":"<<cycles<<",\"cold_benchmarks\":[";
  for(unsigned i=0;i<measurements.size();++i){auto m=measurements[i];if(i)std::cout<<",";
   std::cout<<"{\"rows\":"<<m.rows<<",\"format\":"<<m.format<<",\"k\":1024,\"n\":8,\"macs\":"<<m.macs
    <<",\"load_compute_cycles\":"<<m.load_compute<<",\"finalization_readback_cycles\":"<<m.finish
    <<",\"total_cycles\":"<<m.total<<",\"a_effective_bytes\":"<<m.a_bytes<<",\"b_effective_bytes\":"<<m.b_bytes
    <<",\"a_container_bytes\":"<<uint64_t(m.rows)*128*16<<",\"b_container_bytes\":"<<m.b_bytes
    <<",\"s_initialization_included\":false,\"cross_batch_load_overlap\":false}";
  }
  std::cout<<"]}\n";
 }catch(const std::exception& e){std::cerr<<"FAIL cycle="<<cycles<<": "<<e.what()<<"\n";return 1;}
}
