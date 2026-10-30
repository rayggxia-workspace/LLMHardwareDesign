#include "Vblock_v2_n.h"
#include "verilated.h"
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <iostream>
#include <memory>
#include <numeric>
#include <random>
#include <stdexcept>
#include <vector>
static std::unique_ptr<Vblock_v2_n> p;
#define d (*p)
using Vec=std::array<uint16_t,8>;
static uint64_t cycles=0,checks=0,commands=0;static std::mt19937 rng(143);
static void ck(bool v,const char*s){++checks;if(!v)throw std::runtime_error(s);}
static void tick(){d.clk=0;d.eval();d.clk=1;d.eval();++cycles;d.clk=0;d.eval();}
static void reset(){d.reset=1;d.cmd_valid=0;d.rsp_ready=0;tick();tick();d.reset=0;tick();ck(d.cmd_ready&&!d.rsp_valid,"reset");}
static void pack(VlWide<4>& x,const Vec& v){for(unsigned i=0;i<4;++i)x[i]=uint32_t(v[2*i])|(uint32_t(v[2*i+1])<<16);}
static Vec transaction(unsigned op,unsigned n=0,unsigned param=0,Vec a={},Vec b={},bool error=false){
 ck(d.cmd_ready,"admission");d.cmd_valid=1;d.cmd_op=op;d.cmd_count=n;d.cmd_param=param;pack(d.cmd_data,a);pack(d.cmd_aux,b);tick();d.cmd_valid=0;
 unsigned wait=0;while(!d.rsp_valid){ck(++wait<1000,"command timeout");tick();}
 ck(bool(d.rsp_error)==error,"command error mismatch");Vec out{};for(unsigned i=0;i<8;++i)out[i]=uint16_t(d.rsp_data[i/2]>>(16*(i%2)));
 bool sat=d.rsp_saturated;for(unsigned j=0;j<commands%4;++j){tick();ck(d.rsp_valid&&!d.cmd_ready,"held response");ck(bool(d.rsp_saturated)==sat,"held sat");for(unsigned i=0;i<8;++i)ck(uint16_t(d.rsp_data[i/2]>>(16*(i%2)))==out[i],"held data");}
 d.rsp_ready=1;tick();d.rsp_ready=0;++commands;return out;
}
static uint64_t root(uint64_t v){uint64_t x=uint64_t(std::sqrt((long double)v));while((__uint128_t(x)+1)*(x+1)<=v)++x;while(__uint128_t(x)*x>v)--x;return x;}
static int64_t rne(int64_t v,unsigned n){if(!n)return v;int64_t q=v>>n;uint64_t r=uint64_t(v)&((uint64_t(1)<<n)-1),h=uint64_t(1)<<(n-1);return q+int64_t(r>h||(r==h&&(q&1)));}
static uint16_t expraw(int difference){if(difference< -16384)return 0;if(difference>=0)return 32768;
 unsigned t=difference+16384,i=t/16,f=t%16;int lo=std::llrint(std::exp(-16.+i/64.)*32768),hi=std::llrint(std::exp(-16.+(i+1)/64.)*32768);
 return lo+rne((hi-lo)*f,4);
}
static Vec chunk(const std::vector<int16_t>& v,unsigned i){Vec a{};for(unsigned j=0;j<8&&i+j<v.size();++j)a[j]=uint16_t(v[i+j]);return a;}
static void normalization(unsigned mode,const std::vector<int16_t>& x,unsigned eps){
 Vec e{};e[0]=eps;e[1]=eps>>16;transaction(0,0,mode,e);int64_t sum=0;uint64_t sq=0;int ma=-32768,mi=32767;
 for(unsigned i=0;i<x.size();i+=8){transaction(1,std::min<unsigned>(8,x.size()-i),0,chunk(x,i));}
 for(auto v:x){sum+=v;sq+=int64_t(v)*v;ma=std::max(ma,int(v));mi=std::min(mi,int(v));}
 auto stats=transaction(7);uint64_t got_sq=uint64_t(stats[5])|(uint64_t(stats[6])<<16)|(uint64_t(stats[7])<<32);
 ck(stats[0]==x.size()&&int16_t(stats[1])==ma&&int16_t(stats[2])==mi,"statistics extrema/count");
 ck(int32_t(uint32_t(stats[3])|(uint32_t(stats[4])<<16))==sum&&got_sq==sq,"statistics wide sums");
 transaction(2);
 uint64_t denom=(sq<<16);if(mode==1)denom/=x.size();denom+=uint64_t(eps)<<16;
 uint64_t factor=(uint64_t(1)<<38)/root(denom);auto f=transaction(11);ck((uint32_t(f[0])|(uint32_t(f[1])<<16))==factor,"norm factor");
 for(unsigned i=0;i<x.size();i+=8){Vec gamma{};for(auto&g:gamma)g=uint16_t(int16_t(rng()));auto y=transaction(5,std::min<unsigned>(8,x.size()-i),0,chunk(x,i),gamma);
  for(unsigned j=0;j<8&&i+j<x.size();++j){int64_t z=rne(int64_t(x[i+j])*factor*int16_t(gamma[j]),30);z=std::max<int64_t>(-32768,std::min<int64_t>(32767,z));ck(int16_t(y[j])==z,"norm replay");}
 }
 transaction(5,1,0,{}, {},true);transaction(1,1,0,{}, {},true);
}
static double soft_error=0;
static void softmax(const std::vector<int16_t>& x){
 transaction(0);for(unsigned i=0;i<x.size();i+=8)transaction(1,std::min<unsigned>(8,x.size()-i),0,chunk(x,i));transaction(2);
 int ma=*std::max_element(x.begin(),x.end());uint64_t sum=0;std::vector<uint16_t> ex(x.size());double ref_sum=0;
 for(auto v:x)ref_sum+=std::exp((double(v)-ma)/1024.);
 for(unsigned i=0;i<x.size();i+=8){auto r=transaction(3,std::min<unsigned>(8,x.size()-i),0,chunk(x,i));for(unsigned j=0;j<8&&i+j<x.size();++j){ex[i+j]=expraw(int(x[i+j])-ma);ck(r[j]==ex[i+j],"EXP interpolation");sum+=ex[i+j];}}
 transaction(4);uint64_t factor=(uint64_t(1)<<46)/sum;
 for(unsigned i=0;i<x.size();i+=8){Vec a{};for(unsigned j=0;j<8&&i+j<x.size();++j)a[j]=ex[i+j];auto y=transaction(6,std::min<unsigned>(8,x.size()-i),0,a);
  for(unsigned j=0;j<8&&i+j<x.size();++j){uint64_t z=rne(int64_t(ex[i+j])*factor,30);z=std::min<uint64_t>(65535,z);ck(y[j]==z,"probability normalization");soft_error=std::max(soft_error,std::abs(y[j]/65536.-std::exp((double(x[i+j])-ma)/1024.)/ref_sum));}}
 transaction(6,1,0,{}, {},true);
}
static void topk(){for(unsigned trial=0;trial<80;++trial){unsigned k=1+trial%8;transaction(8,0,k);std::vector<std::pair<int,int>> entries;
 for(unsigned i=0;i<40;i+=4){Vec v{};for(unsigned j=0;j<4;++j){int score=trial%3?int16_t(rng()):i%7;int id=1000+int(39-i-j);entries.emplace_back(score,id);v[2*j]=uint16_t(score);v[2*j+1]=id;}transaction(9,4,0,v);}
 transaction(9,1,0,{}, {},true);auto r=transaction(10);std::stable_sort(entries.begin(),entries.end(),[](auto a,auto b){return a.first!=b.first?a.first>b.first:a.second<b.second;});
 for(unsigned i=0;i<k;++i)ck(r[i]==entries[i].second,"topK selection/ID");}}
int main(int argc,char**argv){try{
 Verilated::commandArgs(argc,argv);p=std::make_unique<Vblock_v2_n>();reset();transaction(2,0,0,{}, {},true);transaction(0,0,3,{}, {},true);transaction(0,0,1,{}, {},true);
 for(unsigned n:{1,2,7,8,9,40,257,1024,65535}){std::vector<int16_t>x(n);for(auto&v:x)v=int16_t(rng());if(n>=2){x[0]=-32768;x[1]=32767;}normalization(1,x,1);normalization(2,x,7);softmax(x);}
 normalization(1,std::vector<int16_t>(17,0),1);normalization(2,std::vector<int16_t>(33,-32768),1);softmax(std::vector<int16_t>(40,0));
 topk();ck(soft_error<.0005,"softmax float error budget");
 transaction(0);d.cmd_valid=1;d.cmd_op=1;d.cmd_count=8;tick();reset();
 std::cout<<"{\"passed\":true,\"checks\":"<<checks<<",\"cycles\":"<<cycles<<",\"commands\":"<<commands<<",\"softmax_max_abs_error\":"<<soft_error<<"}\n";p.reset();return 0;
 }catch(const std::exception&e){std::cerr<<"FAIL cycle "<<cycles<<": "<<e.what()<<"\n";p.reset();return 1;}}
