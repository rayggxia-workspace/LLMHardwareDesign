#include "verilated.h"
#if ROLE==3
#include "Vcontrol_pair_e.h"
using Model=Vcontrol_pair_e;
#elif ROLE==4
#include "Vcontrol_pair_g.h"
using Model=Vcontrol_pair_g;
#else
#include "Vcontrol_pair_n.h"
using Model=Vcontrol_pair_n;
#endif
#include <array>
#include <vector>
#include <random>
#include <iostream>
#include <cstdlib>
using Word=std::array<uint32_t,4>;
static uint64_t checks=0,cycles=0;
static void need(bool b,const char*m){++checks;if(!b){std::cerr<<m<<" at "<<cycles<<"\n";std::exit(1);}}
struct Sim {
 Model v;std::mt19937 rng{162};std::vector<uint64_t> results;
 Sim(){v.clk=0;v.task_valid=0;v.complete_ready=0;v.init_mode=0;v.init_valid=0;v.init_write=0;v.init_address=0;v.init_take=1;
  for(unsigned n=0;n<4;++n)v.init_data[n]=0;for(unsigned n=0;n<8;++n)v.task_data[n]=0;
  v.reset=1;for(unsigned n=0;n<4;++n){v.clk=0;v.eval();v.clk=1;v.eval();}v.reset=0;v.clk=0;v.eval();}
 void tick(){v.clk=0;v.complete_ready=rng()%4!=0;v.eval();if(v.complete_valid&&v.complete_ready)results.push_back(v.complete_data);
  v.clk=1;v.eval();++cycles;}
 Word memory(bool write,unsigned address,Word data={}){
  v.init_mode=1;v.init_write=write;v.init_address=address;for(unsigned n=0;n<4;++n)v.init_data[n]=data[n];v.init_valid=1;v.eval();
  unsigned guard=0;while(!v.init_ready){tick();need(++guard<100,"S init ready");}tick();v.init_valid=0;
  while(!v.init_response){tick();need(++guard<100,"S init response");}Word result{};for(unsigned n=0;n<4;++n)result[n]=v.init_rdata[n];tick();v.init_mode=0;tick();return result;
 }
 void fill(unsigned base,unsigned count,int value){for(unsigned w=0;w<(count+7)/8;++w){Word x{};for(unsigned lane=0;lane<8;++lane)x[lane/2]|=uint32_t(uint16_t(value))<<(16*(lane%2));memory(true,base/16+w,x);}}
 uint64_t task(unsigned op,unsigned count,unsigned flags,unsigned a=0,unsigned b=0,unsigned c=0,unsigned dst=0,unsigned param=0,unsigned epsilon=0,unsigned tag=55){
  const std::array<uint32_t,8> d{{(tag<<16)|(flags<<12)|(ROLE<<8)|op,count,a,b,c,dst,param,epsilon}};
  const unsigned target=unsigned(results.size())+1;for(unsigned n=0;n<8;++n)v.task_data[n]=d[n];v.task_valid=1;v.eval();
  unsigned guard=0;while(!v.task_ready){tick();need(++guard<500000,"task queue");}tick();v.task_valid=0;
  while(results.size()<target){tick();need(++guard<500000,"adapter response");}
  need((results.back()&65535)==tag,"completion tag");return results.back();
 }
 void values(unsigned base,unsigned count,unsigned expected){for(unsigned w=0;w<(count+7)/8;++w){const auto x=memory(false,base/16+w);
  for(unsigned l=0;l<8;++l)need(((x[l/2]>>(16*(l%2)))&65535)==(w*8+l<count?expected:0),"actual S output/tail");}}
};
int main(int argc,char**argv){Verilated::commandArgs(argc,argv);Sim x;
#if ROLE==3
 x.fill(0,257,123);x.fill(1024,257,456);
 need(((x.task(0,257,5,0,1024,0,4096)>>20)&15)==0,"E task success");x.values(4096,257,579);
 // Scalar broadcast and exact in-place operation use finite local holds.
 need(((x.task(2,257,5,0,0x40000400,0,0,10)>>20)&15)==0,"E scalar multiply");x.values(0,257,123);
#elif ROLE==4
 x.fill(0,17,16384);
 need(((x.task(0,17,5,0,0x40000200,0,4096,1)>>20)&15)==0,"G task success");x.values(4096,17,8192);
#else
 x.fill(0,257,1024);
 need(((x.task(0,0,0,0,0,0,0,1,1)>>20)&15)==0,"N RMS begin");
 need(((x.task(1,257,0)>>20)&15)==0,"N stats");need(((x.task(2,0,0)>>20)&15)==0,"N finalize");
 need(((x.task(5,257,5,0,0x40000400,0,4096)>>20)&15)==0,"N replay");x.values(4096,257,1024);
 x.fill(0,257,0);need(((x.task(0,0,0)>>20)&15)==0,"Softmax begin");
 need(((x.task(1,257,0)>>20)&15)==0,"Softmax max statistics");need(((x.task(2,0,0)>>20)&15)==0,"Softmax stats finish");
 need(((x.task(3,257,4,0,0,0,2048)>>20)&15)==0,"Softmax EXP actual S write");
 need(((x.task(4,0,0)>>20)&15)==0,"Softmax factor");
 need(((x.task(6,257,4,2048,0,0,4096)>>20)&15)==0,"Softmax EXP replay");x.values(4096,257,64);
 // Native small TopK uses S32 score/id pairs, not eight S16 data lanes.
 for(unsigned w=0;w<10;++w){Word data{};for(unsigned n=0;n<4;++n){unsigned id=w*4+n;data[n]=id|(id<<16);}x.memory(true,w,data);}
 need(((x.task(8,0,0,0,0,0,0,8)>>20)&15)==0,"TopK begin");need(((x.task(9,40,0)>>20)&15)==0,"TopK load");
 need(((x.task(10,0,4,0,0,0,4096)>>20)&15)==0,"TopK select");const auto top=x.memory(false,4096/16);
 for(unsigned n=0;n<8;++n)need(((top[n/2]>>(16*(n%2)))&65535)==39-n,"TopK indices");
#endif
 need(((x.task(ROLE==2?1:0,16,4,0,0,0,16)>>20)&15)==2,"unsafe shifted overlap rejected");
 need(((x.task(ROLE==2?1:0,9,4,16368,0,0,4096)>>20)&15)==2,"capacity rejected");
 std::cout<<"{\"passed\":true,\"checks\":"<<checks<<",\"cycles\":"<<cycles<<",\"role\":"<<ROLE<<"}\n";
}
