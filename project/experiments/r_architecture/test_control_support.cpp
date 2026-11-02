#include "Vcontrol_support.h"
#include "verilated.h"
#include <random>
#include <iostream>
#include <stdexcept>
static void ck(bool x,const char*s){if(!x)throw std::runtime_error(s);}
int main(int argc,char**argv){try{Verilated::commandArgs(argc,argv);Vcontrol_support d;std::mt19937 rng(1572026);unsigned checks=0;auto tick=[&](){d.clk=0;d.eval();d.clk=1;d.eval();d.clk=0;d.eval();};d.reset=1;tick();d.reset=0;
for(unsigned trial=0;trial<400;++trial){
 auto put=[&](bool code,unsigned idx,uint64_t x){d.config_valid=1;d.config_code=code;d.config_index=idx;for(int j=0;j<4;++j)d.config_data[j]=j<2?uint32_t(x>>(32*j)):0;tick();d.config_valid=0;};
 uint32_t value=rng(),n=1+rng()%16;put(false,5,value);
 put(true,0,(3ull<<60)|n);put(true,1,(1ull<<60)|(5ull<<55)|(3ull<<52));put(true,2,(2ull<<60)|(8ull<<55));put(true,3,(5ull<<60)|16);put(true,4,(4ull<<60)|1);put(true,5,0);
 d.start=1;tick();d.start=0;unsigned sent=0,received=0;uint32_t last[16]={};
 for(unsigned t=0;d.busy;++t){ck(t<2000,"controller timeout");d.command_ready=(rng()%3)!=0;d.feedback_valid=received<sent&&(rng()%3)!=0;d.feedback_wide=1;d.feedback_error=trial%7==0;for(int j=0;j<16;++j)d.feedback_data[j]=rng();d.eval();
  if(d.command_valid&&d.command_ready){ck(d.command_channel==3&&d.command_data[0]==value&&d.command_address==sent*16,"dispatch mismatch");++sent;++checks;}
  if(d.feedback_valid&&d.feedback_ready){++received;for(int j=0;j<16;++j)last[j]=d.feedback_data[j];}tick();
 }
 ck(sent==n&&received==n,"lost command");ck(bool(d.failed)==(trial%7==0),"sticky failure mismatch");for(int j=0;j<16;++j){ck(d.register_words[8*4+j]==last[j],"response register mismatch");++checks;}
 d.reset=1;tick();d.reset=0;d.eval();ck(d.ready&&!d.busy&&!d.failed,"reset mismatch");
}
std::cout<<"{\"passed\":true,\"trials\":400,\"checks\":"<<checks<<"}\n";return 0;
}catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}}
