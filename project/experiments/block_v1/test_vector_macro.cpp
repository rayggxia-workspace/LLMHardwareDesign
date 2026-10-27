#include "Vblock_v1_v.h"
#include "verilated.h"
#include <array>
#include <vector>
#include <random>
#include <cstdint>
#include <cmath>
#include <algorithm>
#include <iostream>
#include <stdexcept>
using I=__int128_t;using U=__uint128_t;using Row=std::array<int32_t,8>;
static Vblock_v1_v dut;static std::mt19937_64 rng(12120261027ULL);static uint64_t checks=0,cycles=0;
static void need(bool v,const char*s){++checks;if(!v)throw std::runtime_error(s);}
static void tick(){dut.clk=0;dut.eval();dut.clk=1;dut.eval();++cycles;}
static void put(U v){for(int j=0;j<4;++j){dut.cmd_data[j]=uint32_t(v);v>>=32;}}
static U get(){U v=0;for(int j=3;j>=0;--j)v=v<<32|dut.rsp_data[j];return v;}
struct Reply{U data;unsigned latency;bool saturated;};
static Reply cmd(unsigned op,unsigned index,U data,bool error=false){
 need(dut.cmd_ready,"input unavailable");dut.cmd_valid=1;dut.cmd_op=op;dut.cmd_index=index;put(data);dut.rsp_ready=0;tick();dut.cmd_valid=0;
 unsigned latency=0;while(!dut.rsp_valid){tick();need(++latency<5000,"operation timeout");}
 if(bool(dut.rsp_error)!=error){std::cerr<<"op "<<op<<" index "<<index<<" latency "<<latency<<" expected error "<<error<<"\n";need(false,"error mismatch");}
 Reply r{get(),latency,bool(dut.rsp_saturated)};
 for(unsigned j=0,n=rng()%4;j<n;++j){need(!dut.cmd_ready,"held response accepted command");dut.cmd_valid=1;dut.cmd_op=13;put(U(rng())<<64|rng());tick();need(dut.rsp_valid&&get()==r.data&&bool(dut.rsp_error)==error&&bool(dut.rsp_saturated)==r.saturated,"held response changed");}
 dut.cmd_valid=0;dut.rsp_ready=1;tick();dut.rsp_ready=0;need(dut.cmd_ready,"response release failed");return r;
}
static U pack(const Row&a,int p){U v=0;for(int j=0;j<4;++j)v|=U(uint32_t(a[4*p+j]))<<(32*j);return v;}
static void load(unsigned op,const Row&a){for(int p=0;p<2;++p)cmd(op,p,pack(a,p));}
static I rne(I v,unsigned s){if(!s)return v;I q=v>>s;U r=U(v)&((U(1)<<s)-1),h=U(1)<<(s-1);return q+(r>h||(r==h&&(q&1)));}
static int32_t sat(I v,int bits=32){I lo=-(I(1)<<(bits-1)),hi=(I(1)<<(bits-1))-1;return int32_t(std::max(lo,std::min(hi,v)));}
static std::vector<int32_t> read(unsigned n){std::vector<int32_t>v;for(unsigned p=0;p<(n+3)/4;++p){U x=cmd(9,p,0).data;for(unsigned j=0;j<4&&v.size()<n;++j)v.push_back(int32_t(x>>(32*j)));}return v;}
static void replay(const std::vector<int32_t>&a){for(unsigned p=0;p<(a.size()+3)/4;++p){U v=0;for(unsigned j=0;j<4;++j)if(4*p+j<a.size())v|=U(uint32_t(a[4*p+j]))<<(32*j);cmd(7,p,v);}}
static double function_reference(unsigned fn,double x){switch(fn){case 0:return std::exp(x);case 1:return 1/(1+std::exp(-x));case 2:return x/(1+std::exp(-x));case 3:return .5*x*(1+std::tanh(std::sqrt(2/std::acos(-1.0))*(x+.044715*x*x*x)));default:return std::log1p(std::exp(x));}}
static int64_t coefficient(unsigned fn,unsigned index){int step=fn==0?128:32,lo=fn==0||fn==4?-16:-8;return std::llrint(function_reference(fn,lo+double(index)/step)*65536);}
static int32_t lut(unsigned fn,int32_t x){
 int lo=fn==0||fn==4?-16:-8,hi=fn==0?0:fn==4?16:8,shift=fn==0?9:11;
 if(x<lo*65536)return 0;
 if(x>hi*65536)return fn==1?65536:x;
 unsigned off=unsigned(int64_t(x)-int64_t(lo)*65536),index=off>>shift,f=off&((1U<<shift)-1);
 if(x==hi*65536)return int32_t(coefficient(fn,index));
 auto a=coefficient(fn,index),b=coefficient(fn,index+1);return int32_t(a+rne(I(b-a)*f,shift));
}
static U isqrt(U n){U lo=0,hi=U(1)<<64;while(lo+1<hi){U m=(lo+hi)/2;if(m*m<=n)lo=m;else hi=m;}return lo;}
static U quotient_rne(U n,U d){U q=n/d,r=n%d;return q+(r>d-r||(r==d-r&&(q&1)));}
static U root_rne(U n,U d){U q=n/d,rem=n%d,r=isqrt(q),s=q-r*r;return r+(s>r||(s==r&&(rem>d/4||(rem==d/4&&d%4==0&&(r&1)))));}
int main(int argc,char**argv){try{Verilated::commandArgs(argc,argv);dut.cmd_valid=0;dut.reset=1;tick();tick();dut.reset=0;tick();
 cmd(9,0,0,true);cmd(6,0,0,true);cmd(8,0,1,true);cmd(11,0,40|(8<<6),true);
 unsigned point_cases=0,function_cases=0,compose_cases=0;double max_function_abs[5]={};
 for(unsigned op=0;op<10;++op)for(unsigned t=0;t<80;++t){Row a,b;for(int j=0;j<8;++j){a[j]=int32_t(rng());b[j]=int32_t(rng());}load(0,a);load(1,b);
  bool broadcast=t&1,swap=t&2;int32_t sb=int32_t(rng()),sc=int32_t(rng());unsigned shift=op==7?rng()%97:rng()%128,width=t%3,n=1+rng()%8;int bits=width==0?8:width==1?16:32;
  U data=U(op)|(U(shift)<<4)|(U(n)<<11)|(U(broadcast)<<15)|(U(width)<<16)|(U(swap)<<18)|(U(uint32_t(sb))<<32)|(U(uint32_t(sc))<<64);
  auto response=cmd(2,0,data);need(response.latency==2,"point cycle count");auto actual=read(n);bool saturated=false;
  for(unsigned j=0;j<n;++j){I bv=broadcast?sb:b[j^unsigned(swap)];I y=0;switch(op){case 0:y=I(a[j])+bv;break;case 1:y=I(a[j])-bv;break;case 2:y=I(a[j])*bv;break;case 3:y=I(a[j])*bv+sc;break;case 4:y=std::max(I(a[j]),bv);break;case 5:y=std::min(I(a[j]),bv);break;case 6:y=I(a[j])>=bv?-1:0;break;case 7:y=I(a[j])*(I(1)<<shift);break;case 8:y=a[j];break;case 9:y=a[j]<0?bv:sc;break;}if(op!=7)y=rne(y,shift);int32_t expected=sat(y,bits);saturated|=I(expected)!=y;need(actual[j]==expected,"point arithmetic mismatch");}
  need(response.saturated==saturated,"point saturation flag");++point_cases;
 }
 // Cross-cycle exact statistics and indexed ties, including signed extremes.
 for(unsigned t=0;t<90;++t){I sum=0;U sq=0;int32_t mx=INT32_MIN,mn=INT32_MAX;unsigned imx=0,imn=0,count=0;
  for(unsigned chunk=0;chunk<9;++chunk){Row a;for(int j=0;j<8;++j)a[j]=t==0?INT32_MIN:t==1?INT32_MAX:int32_t(rng());load(0,a);unsigned n=1+rng()%8,base=500+chunk*8;
   cmd(3,0,U(chunk==0)|(U(chunk==8)<<1)|(U(n)<<2)|(U(base)<<16));
   for(unsigned j=0;j<n;++j){sum+=a[j];sq+=U(I(a[j])*a[j]);if(count==0||a[j]>mx){mx=a[j];imx=base+j;}if(count==0||a[j]<mn){mn=a[j];imn=base+j;}++count;}
  }
  need(I(cmd(4,0,0).data)==sum,"stat sum");need(cmd(4,1,0).data==sq,"stat square sum");auto r=cmd(4,2,0).data;
  need(int32_t(r)==mx&&uint16_t(r>>32)==imx&&int32_t(r>>48)==mn&&uint16_t(r>>80)==imn&&uint16_t(r>>96)==count&&bool((r>>112)&1),"stat extrema/count/final");cmd(3,0,4,true);
 }
 // Function path: exact independent coefficient/interpolation oracle plus analytic error.
 for(unsigned fn=0;fn<5;++fn)for(unsigned t=0;t<250;++t){Row a;int lo=fn==0||fn==4?-16:-8,hi=fn==0?0:fn==4?16:8;
  for(int j=0;j<8;++j)a[j]=lo*65536+int(rng()%uint64_t((hi-lo)*65536+1));if(t==0){a[0]=lo*65536;a[1]=hi*65536;a[2]=0;}
  load(0,a);cmd(5,0,fn);auto actual=read(8);for(int j=0;j<8;++j){need(actual[j]==lut(fn,a[j]),"function interpolation mismatch");double ref=function_reference(fn,double(a[j])/65536);max_function_abs[fn]=std::max(max_function_abs[fn],std::abs(double(actual[j])/65536-ref));}++function_cases;
 }
 {Row a{};a.fill(1);load(0,a);cmd(5,0,0,true);cmd(9,0,0,true);}
 // Exact U128 group quotient/sqrt rounding, not an approximate host substitute.
 for(unsigned t=0;t<250;++t){U d=t<4?U(t+1):U(rng())<<32|rng();for(unsigned op=0;op<2;++op){U expected=op?root_rne(U(1)<<48,d):quotient_rne(U(1)<<32,d);auto r=cmd(6,op,d);need(r.data==std::min(expected,U(INT32_MAX))&&r.saturated==(expected>INT32_MAX),"group fixed-point result");}}
 for(unsigned kind=0;kind<3;++kind)for(unsigned t=0;t<90;++t){unsigned n=t==0?256:t==1?1:1+rng()%256;std::vector<int32_t>a(n);for(auto&v:a)v=kind==2?int(rng()%2097153)-1048576:int(rng()%200000001)-100000000;
  if(t==2)for(auto&v:a)v=1;uint64_t eps=kind==2?0:4295;replay(a);cmd(8,kind,U(n)|(U(eps)<<9));auto actual=read(n);U d=0,num=0,f=0;
  if(kind==2){int32_t mx=*std::max_element(a.begin(),a.end());std::vector<int32_t>e(n);for(unsigned j=0;j<n;++j){int64_t delta=int64_t(a[j])-mx;e[j]=lut(0,int32_t(std::max(delta,int64_t(-1048576))));d+=uint32_t(e[j]);}f=quotient_rne(U(1)<<48,d);for(unsigned j=0;j<n;++j)need(actual[j]==sat(rne(I(e[j])*f,32)),"softmax internal replay");}
  else {for(auto v:a)d+=U(I(v)*v);d+=U(eps)*(kind==0?n:1);num=U(kind==0?n:1)<<96;f=root_rne(num,d);for(unsigned j=0;j<n;++j)need(actual[j]==sat(rne(I(a[j])*f,32)),"norm internal replay");}
  ++compose_cases;
 }
 // Forty arbitrary runtime IDs, score ties, deterministic eight-round selection.
 for(unsigned t=0;t<100;++t){unsigned n=t==0?40:1+rng()%40,k=std::min(8U,n);std::vector<int32_t>a(n);std::vector<uint16_t>ids(n);std::vector<unsigned>order(n);
  for(unsigned j=0;j<n;++j){a[j]=int(rng()%21)-10;ids[j]=uint16_t(60000-j*17);order[j]=j;}replay(a);
  for(unsigned p=0;p<(n+7)/8;++p){U v=0;for(unsigned j=0;j<8;++j)if(8*p+j<n)v|=U(ids[8*p+j])<<(16*j);cmd(10,p,v);}
  std::stable_sort(order.begin(),order.end(),[&](unsigned l,unsigned r){return a[l]>a[r]||(a[l]==a[r]&&ids[l]<ids[r]);});auto r=cmd(11,0,n|(k<<6));need(r.latency==k*(n+1),"TopK cycle count");
  for(unsigned j=0;j<k;++j){U v=cmd(12,j,0).data;need(int32_t(v)==a[order[j]]&&uint16_t(v>>32)==ids[order[j]],"TopK dynamic ID/tie mismatch");}
 }
 std::cout<<"{\"passed\":true,\"point_cases\":"<<point_cases<<",\"function_cases\":"<<function_cases<<",\"compose_cases\":"<<compose_cases<<",\"topk_cases\":100,\"checks\":"<<checks<<",\"cycles\":"<<cycles<<",\"sampled_function_max_abs\":[";for(int f=0;f<5;++f)std::cout<<(f?",":"")<<max_function_abs[f];std::cout<<"]}\n";return 0;
}catch(const std::exception&e){std::cerr<<e.what()<<"\n";return 1;}}
