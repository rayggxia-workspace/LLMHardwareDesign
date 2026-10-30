#include "Vblock_v2_e.h"
#include "verilated.h"
#include <array>
#include <cstdint>
#include <iostream>
#include <memory>
#include <random>
#include <stdexcept>
static std::unique_ptr<Vblock_v2_e> p;
#define d (*p)
static uint64_t checks=0,cycles=0;
static std::mt19937 rng(143);
static void ck(bool x,const char* s){++checks;if(!x)throw std::runtime_error(s);}
static void tick(){d.clk=0;d.eval();d.clk=1;d.eval();++cycles;d.clk=0;d.eval();}
using Vec=std::array<int16_t,8>;
static int64_t rne(int64_t x,unsigned s){if(!s)return x;uint64_t r=uint64_t(x)&((uint64_t(1)<<s)-1),h=uint64_t(1)<<(s-1);int64_t q=x>>s;return q+int64_t(r>h||(r==h&&(q&1)));}
static void pack(VlWide<4>& x,const Vec& a){for(unsigned i=0;i<4;++i)x[i]=uint16_t(a[2*i])|(uint32_t(uint16_t(a[2*i+1]))<<16);}
static void reset(){d.reset=1;d.in_valid=0;d.out_ready=0;tick();tick();d.reset=0;tick();ck(d.in_ready&&!d.out_valid,"reset");}
static void run(unsigned op,unsigned shift,const Vec& a,const Vec& b,const Vec& c,bool pressure){
 ck(d.in_ready,"admission");d.in_valid=1;d.in_op=op;d.in_shift=shift;pack(d.in_a,a);pack(d.in_b,b);pack(d.in_c,c);tick();d.in_valid=0;
 unsigned wait=0;while(!d.out_valid){ck(++wait<12,"timeout");tick();}
 ck(bool(d.out_error)==(op>12),"error");std::array<uint32_t,4> expected{};bool sat=false;
 if(op<=12)for(unsigned i=0;i<8;++i){int64_t x=a[i],y=b[i],z=c[i],v=0;
  switch(op){case 0:v=x+y;break;case 1:v=x-y;break;case 2:v=x*y;break;case 3:v=x*y+z;break;
   case 4:v=x>y?x:y;break;case 5:v=x<y?x:y;break;case 6:v=z?x:y;break;
   case 7:v=x*(int64_t(1)<<shift);break;case 8:v=x>>shift;break;
   case 9:v=x*int64_t(b[i&6])+((i&1)?1:-1)*int64_t(a[i^1])*b[i|1];break;
   case 10:v=x;break;case 11:v=x<0?-x:x;break;default:v=x;}
  if(op==2||op==3||op==9||op==10)v=rne(v,shift);
  int64_t lo=op==12?-128:-32768,hi=op==12?127:32767;
  if(v<lo){v=lo;sat=true;}if(v>hi){v=hi;sat=true;}
  if(op==12)expected[i/4]|=uint32_t(uint8_t(v))<<(8*(i%4));
  else expected[i/2]|=uint32_t(uint16_t(v))<<(16*(i%2));
 }
 for(unsigned i=0;i<4;++i)ck(d.out_data[i]==expected[i],"numeric mismatch");
 ck(bool(d.out_saturated)==sat,"saturation");
 if(pressure)for(unsigned n=0;n<5;++n){tick();ck(d.out_valid&&!d.in_ready,"hold valid");for(unsigned i=0;i<4;++i)ck(d.out_data[i]==expected[i],"hold payload");}
 d.out_ready=1;tick();d.out_ready=0;
}
int main(int argc,char** argv){try{Verilated::commandArgs(argc,argv);p=std::make_unique<Vblock_v2_e>();reset();
 Vec a{},b{},c{};const int v[]={-32768,-32767,-1024,-1,0,1,1024,32767};
 for(unsigned op=0;op<16;++op)for(unsigned s=0;s<32;++s){for(unsigned i=0;i<8;++i){a[i]=v[i];b[i]=v[(i+s)%8];c[i]=v[(i+op)%8];}run(op,s,a,b,c,true);}
 for(unsigned n=0;n<4000;++n){for(unsigned i=0;i<8;++i){a[i]=int16_t(rng());b[i]=int16_t(rng());c[i]=int16_t(rng());}run(rng()%13,rng()%32,a,b,c,n%7==0);}
 d.in_valid=1;d.in_op=9;tick();reset();
 std::cout<<"{\"passed\":true,\"checks\":"<<checks<<",\"cycles\":"<<cycles<<"}\n";return 0;
 }catch(const std::exception& e){std::cerr<<"FAIL "<<cycles<<" "<<e.what()<<"\n";return 1;}}
