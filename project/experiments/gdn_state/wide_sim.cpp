#include "Vwide_test104.h"
#include "verilated.h"
#include <fstream>
#include <iostream>
#include <random>
#include <vector>
#include <utility>
#include <stdexcept>
static void need(bool v,const char*s){if(!v)throw std::runtime_error(s);}
int main(int argc,char**argv){try{need(argc==2,"output");Vwide_test104 d;std::ofstream f(argv[1]);uint64_t t=0;auto tick=[&](){d.hold=t%7==2;d.clk=0;d.eval();d.clk=1;d.eval();t++;};d.reset=1;d.req=0;d.cancel=0;d.take=0;tick();tick();d.reset=0;tick();std::vector<std::pair<int64_t,int32_t>> cases;
 for(int64_t a:{INT64_MIN,INT64_MAX,INT64_MIN+1,int64_t(0),int64_t(1),int64_t(-1),int64_t(1)<<31,-(int64_t(1)<<31),int64_t(1)<<62})for(int32_t b:{-32769,-32768,-32767,-1,0,1,32767,32768,32769})cases.push_back({a,b});
 std::mt19937_64 rng(104);for(int i=0;i<4096;i++){int64_t a=(int64_t)(rng()>>((i%5)*12));if(i&1)a=-a;int32_t b=(int32_t)(rng()%65537)-32768;cases.push_back({a,b});}
 for(auto [a,b]:cases){need(d.ready,"ready");auto start=d.grants;d.a=a;d.b=b;d.req=1;tick();d.req=0;unsigned lim=0;while(!d.valid){need(++lim<100,"timeout");tick();}auto val=d.value;auto err=d.error;for(int k=0;k<5;k++){tick();need(d.valid&&d.value==val&&d.error==err,"held response");}f<<a<<","<<b<<","<<(unsigned)err<<","<<(int64_t)val<<","<<d.grants-start<<"\n";d.take=1;tick();d.take=0;}
 for(int at=0;at<9;at++){d.a=1234567890123;d.b=32767;d.req=1;tick();d.req=0;for(int j=0;j<at&&!d.valid;j++)tick();d.cancel=1;tick();d.cancel=0;unsigned lim=0;while(!d.valid){need(++lim<100,"cancel timeout");tick();}need(d.error,"cancel error");d.take=1;tick();d.take=0;need(d.ready,"cancel restart");}
 std::cout<<"PASS_WIDE_DRIVER vectors="<<cases.size()<<" cancellations=9\n";return 0;}catch(const std::exception&e){std::cerr<<e.what()<<"\n";return 1;}}
