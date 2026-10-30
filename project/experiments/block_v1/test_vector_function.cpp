#include "Vblock_v1_v_function.h"
#include "verilated.h"
#include <vector>
#include <deque>
#include <cmath>
#include <iostream>
#include <stdexcept>
#include <cstdint>
static Vblock_v1_v_function d;static uint64_t checks=0,pairs=0;
static void need(bool v){++checks;if(!v)throw std::runtime_error("function II/latency/numeric mismatch");}
static void tick(){d.clk=0;d.eval();d.clk=1;d.eval();}
static double ref(unsigned fn,double x){switch(fn){case 0:return std::exp(x);case 1:return 1/(1+std::exp(-x));case 2:return x/(1+std::exp(-x));case 3:return .5*x*(1+std::tanh(std::sqrt(2/std::acos(-1.0))*(x+.044715*x*x*x)));default:return std::log1p(std::exp(x));}}
static int64_t rne(int64_t v,unsigned shift){int64_t q=v>>shift,r=v&((int64_t(1)<<shift)-1),h=int64_t(1)<<(shift-1);return q+(r>h||(r==h&&(q&1)));}
struct Expected{int32_t a,b;double ra,rb;bool valid;unsigned fn;};
int main(int argc,char**argv){try{Verilated::commandArgs(argc,argv);d.reset=1;d.in_valid=0;tick();tick();d.reset=0;std::deque<Expected>fifo;double worst_abs[5]={},worst_rel[5]={};uint64_t values[5]={};
 auto step=[&](Expected e,int32_t x,int32_t y){d.in_valid=e.valid;d.fn=e.fn;d.x0=x;d.x1=y;fifo.push_back(e);tick();if(fifo.size()>=3){auto a=fifo.front();fifo.pop_front();need(bool(d.out_valid)==a.valid);if(a.valid){need(!d.error&&int32_t(d.y0)==a.a&&int32_t(d.y1)==a.b);for(int j=0;j<2;++j){double reference=j?a.rb:a.ra,actual=double(j?int32_t(d.y1):int32_t(d.y0))/65536,err=std::abs(actual-reference);worst_abs[a.fn]=std::max(worst_abs[a.fn],err);if(std::abs(reference)>=1.0/256)worst_rel[a.fn]=std::max(worst_rel[a.fn],err/std::abs(reference));++values[a.fn];}++pairs;}}};
 for(unsigned fn=0;fn<5;++fn){int lo=fn==0||fn==4?-16:-8,hi=fn==0?0:fn==4?16:8,shift=fn==0?9:11,stepn=fn==0?128:32;std::vector<int64_t>table((hi-lo)*stepn+1);for(unsigned i=0;i<table.size();++i)table[i]=std::llrint(ref(fn,lo+double(i)/stepn)*65536);
  auto expected=[&](int32_t raw){unsigned offset=raw-lo*65536,index=offset>>shift,f=offset&((1U<<shift)-1);return int32_t(index==table.size()-1?table[index]:table[index]+rne((table[index+1]-table[index])*f,shift));};
  for(int raw=lo*65536;raw<=hi*65536;raw+=2){int other=std::min(raw+1,hi*65536);step({expected(raw),expected(other),ref(fn,double(raw)/65536),ref(fn,double(other)/65536),true,fn},raw,other);}
  // Bubble between domains tests the valid pipeline; no wave reset.
  step({0,0,0,0,false,fn},0,0);
 }
 for(int i=0;i<3;++i)step({0,0,0,0,false,0},0,0);
 std::cout<<"{\"passed\":true,\"actual_rtl_exhaustive_domain_grid\":true,\"pipeline_latency\":3,\"initiation_interval\":1,\"parallel_lanes\":2,\"pairs\":"<<pairs<<",\"checks\":"<<checks<<",\"functions\":[";
 for(int fn=0;fn<5;++fn)std::cout<<(fn?",":"")<<"{\"id\":"<<fn<<",\"tested_values_including_padded_endpoint\":"<<values[fn]<<",\"maximum_absolute_error\":"<<worst_abs[fn]<<",\"maximum_relative_error_where_abs_reference_ge_1_over_256\":"<<worst_rel[fn]<<"}";
 std::cout<<"]}\n";return 0;
}catch(const std::exception&e){std::cerr<<e.what()<<"\n";return 1;}}
