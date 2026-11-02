#include "Vblock_v2_m.h"
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
static Vblock_v2_m* dut_ptr;
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
static uint64_t measured_cycles[4]{};
static void check_raw(unsigned row,const Full& full){
 for(unsigned pair=0;pair<4;++pair){auto data=cmd(3,row*8+pair,0).data;
  ck(int64_t(data)==full[2*pair]&&int64_t(data>>64)==full[2*pair+1],"S64 complete result");}
}
static void numeric(){
 for(unsigned test=0;test<96;++test){
  cmd(6,0,0);Inputs a{};Weights b{};Partial part{};fill(a,b,test);
  unsigned rows=1+test%8,tiles=1+(test/8)%4,k=1+rng()%8,n=1+rng()%8,bank=test%2;
  bool wa=test&1,wb=test&2;int16_t factor=test%7?int16_t(rng()):INT16_MIN;unsigned shift=test%9;
  cmd(4,0,uint16_t(factor)|(uint64_t(shift)<<16));
  for(unsigned t=0;t<tiles;++t){put_b(bank,t,b,wb);for(unsigned r=0;r<rows;++r)put_a(bank,r,t,a[r][t],wa);}
  cmd(10,bank*32,descriptor(wa,wb,true,k,n,tiles,rows));reference(part,a,b,wa,wb,rows,tiles,k,n,true);
  std::array<Full,8> full{};
  for(unsigned r=0;r<rows;++r){for(unsigned j=0;j<8;++j)full[r][j]=I128(part[r][j])*factor*(I128(1)<<shift);check_raw(r,full[r]);check_final(r,full[r],test%64,test%3);}
  // Replacing A preserves B. A fresh K32 segment accumulates at full precision.
  for(unsigned r=0;r<rows;++r)for(unsigned t=0;t<tiles;++t){for(auto&v:a[r][t])v=int16_t(rng());put_a(bank,r,t,a[r][t],wa);}
  reference(part,a,b,wa,wb,rows,tiles,k,n,true);cmd(10,bank*32,descriptor(wa,wb,false,k,n,tiles,rows));
  for(unsigned r=0;r<rows;++r){for(unsigned j=0;j<8;++j)full[r][j]+=I128(part[r][j])*factor*(I128(1)<<shift);check_raw(r,full[r]);check_final(r,full[r],(test+13)%64,(test+1)%3);}
  ++cases;
 }
}
static void long_k(){
 reset();Inputs a{};Weights b{};std::array<Full,8> full{};unsigned loads_b=0;
 for(unsigned segment=0;segment<8;++segment){
  fill(a,b,segment);int16_t factor=-16381;unsigned shift=3;cmd(4,0,uint16_t(factor)|(uint64_t(shift)<<16));
  for(unsigned t=0;t<4;++t){put_b(0,t,b,true);++loads_b;for(unsigned r=0;r<8;++r)put_a(0,r,t,a[r][t],true);}
  Partial p{};reference(p,a,b,true,true,8,4,8,8,true);
  auto reply=cmd(10,0,descriptor(true,true,segment==0,8,8,4,8));ck(!reply.sat,"unexpected result saturation");
  for(unsigned r=0;r<8;++r){for(unsigned j=0;j<8;++j)full[r][j]+=I128(p[r][j])*factor*(I128(1)<<shift);check_raw(r,full[r]);}
 }
 ck(loads_b==32,"K256 B reuse: one load per segment tile, not per output row");
}
static void safeguards(){
 reset();cmd(3,0,0,true);cmd(12,0,0,true);cmd(10,0,descriptor(0,0,1,8,8,1,1),true);
 cmd(4,0,uint64_t(1)<<21,true);cmd(4,1,1,true);
 Inputs a{};Weights b{};for(auto&row:a)for(auto&tile:row)tile.fill(-32768);for(auto&tile:b)for(auto&row:tile)row.fill(-32768);
 for(unsigned t=0;t<4;++t){put_b(0,t,b,true);for(unsigned r=0;r<8;++r)put_a(0,r,t,a[r][t],true);}
 cmd(4,0,1);cmd(10,0,descriptor(1,1,1,8,8,4,8));Full base{};base.fill(I128(1)<<35);
 for(unsigned r=0;r<8;++r)check_raw(r,base);
 cmd(4,0,32767|(uint64_t(31)<<16));auto rejected=cmd(10,0,descriptor(1,1,1,8,8,4,8),true);
 ck(uint8_t(rejected.data)==255,"overflow row mask");for(unsigned r=0;r<8;++r)check_raw(r,base);
 // Only the final two rows retain S40 partials; other rows reject explicitly.
 for(unsigned r=0;r<6;++r)cmd(12,r*8,0,true);
 for(unsigned r=6;r<8;++r)for(unsigned g=0;g<4;++g){auto v=cmd(12,r*8+g,0).data;ck(int64_t(v)==(int64_t(1)<<35)&&int64_t(v>>64)==(int64_t(1)<<35),"S40 sign-extended partial read");}
 cmd(10,0,descriptor(1,1,0,8,7,4,8),true);
 d.cmd_valid=1;d.cmd_op=10;d.cmd_index=0;d.cmd_data=descriptor(1,1,1,8,8,4,8);tick();d.cmd_valid=0;
 d.a_valid=1;d.a_bank=0;d.b_valid=1;d.b_bank=0;d.eval();ck(!d.a_ready&&!d.b_ready,"active operand bank lock");
 d.a_bank=1;prepare_b(1,0,b,false,0);d.eval();ck(d.a_ready&&d.b_ready,"other operand bank overlap");tick();d.a_valid=0;d.b_valid=0;
 reset();cmd(3,0,0,true);cmd(12,6*8,0,true);cmd(10,0,descriptor(1,1,1,8,8,4,8),true);
}
static void measure(){
 timed=true;
 for(unsigned format=0;format<4;++format){reset();Inputs a{};Weights b{};fill(a,b,2);
  for(unsigned t=0;t<4;++t){put_b(0,t,b,format&2);for(unsigned r=0;r<8;++r)put_a(0,r,t,a[r][t],format&1);}
  auto reply=cmd(10,0,descriptor(format&1,format&2,1,8,8,4,8));measured_cycles[format]=reply.latency;
 }
 timed=false;
}
int main(int argc,char**argv){try{
 Verilated::commandArgs(argc,argv);dut_ptr=new Vblock_v2_m;reset();numeric();long_k();safeguards();measure();
 std::cout<<"{\"passed\":true,\"checks\":"<<checks<<",\"cycles\":"<<cycles<<",\"cases\":"<<cases<<",\"partial_slots\":16,\"partial_bits\":40,\"result_bits\":64,\"K32_N8_M8_compute_command_latency\":[";
 for(unsigned i=0;i<4;++i)std::cout<<(i?",":"")<<measured_cycles[i];std::cout<<"]}\n";delete dut_ptr;return 0;
 }catch(const std::exception&e){std::cerr<<"FAIL "<<cycles<<" "<<e.what()<<"\n";delete dut_ptr;return 1;}}
