#include "Vmul84.h"
#include "verilated.h"
#include <cstdint>
#include <fstream>
#include <iostream>
#include <stdexcept>
static Vmul84 d;static void need(bool b,const char*s){if(!b)throw std::runtime_error(s);}
static void edge(){d.clk=0;d.eval();d.clk=1;d.eval();d.clk=0;d.eval();}
int main(int argc,char**argv){try{Verilated::commandArgs(argc,argv);d.reset=1;edge();d.reset=0;
 int sent[2]={},retired[2]={};bool outstanding[2]={};int64_t answer[2]={};int both=0,denied=0,held=0;uint32_t rnd=0x91537;
 for(int t=0;t<50000&&(retired[0]<2048||retired[1]<2048);t++){
  d.r0=!outstanding[0]&&sent[0]<2048;d.r1=!outstanding[1]&&sent[1]<2048;d.take0=t%7==0;d.take1=t%11==0;d.hold=t%13==0;
  auto val=[&](int k){if(sent[k]%4==0)return INT32_MIN;if(sent[k]%4==1)return INT32_MAX;return int32_t(uint32_t(sent[k])*1664525u+1013904223u+uint32_t(k)*7919u);};
  d.a0=val(0);d.b0=(sent[0]%3)?-2147483647:-1;d.a1=val(1);d.b1=(sent[1]%3)?INT32_MIN:1;d.eval();
  if(d.r0&&d.r1)both++;if((d.r0&&!d.ready0)||(d.r1&&!d.ready1))denied++;
  bool req[2]={bool(d.r0&&d.ready0),bool(d.r1&&d.ready1)},v[2]={bool(d.v0),bool(d.v1)},take[2]={bool(d.take0),bool(d.take1)};
  int64_t y[2]={int64_t(d.y0),int64_t(d.y1)},expected[2]={int64_t(int32_t(d.a0))*int64_t(int32_t(d.b0)),int64_t(int32_t(d.a1))*int64_t(int32_t(d.b1))};
  for(int k=0;k<2;k++){if(v[k]){need(outstanding[k]&&y[k]==answer[k],"signed multiply/held response");if(take[k]){outstanding[k]=false;retired[k]++;}else held++;}if(req[k]){need(!outstanding[k],"no overwrite");outstanding[k]=true;answer[k]=expected[k];sent[k]++;}}
  edge();
 }
 need(retired[0]==2048&&retired[1]==2048&&both>0&&denied>0&&held>0,"both clients finish under hold and arbitration");
 // Explicit bounded fairness when neither client response is blocked.
 d.reset=1;edge();d.reset=0;d.hold=0;d.take0=1;d.take1=1;d.r0=1;d.r1=1;
 for(int t=0;t<20;t++)edge();need(d.grants0>=5&&d.grants1>=5,"round robin bounded service");
 d.take0=0;d.take1=0;for(int t=0;t<4;t++)edge();need(d.v0&&d.v1,"two finite response slots");d.reset=1;edge();d.reset=0;d.r0=0;d.r1=0;edge();need(!d.v0&&!d.v1,"reset drops pending values");
 std::ofstream o(argv[1]);o<<"{\"status\":\"PASS_MUL_ARBITRATION\",\"accepted\":4096,\"both_request_edges\":"<<both<<",\"denied_edges\":"<<denied<<",\"held_response_edges\":"<<held<<",\"fairness\":true,\"active_reset\":true}\n";std::cout<<"PASS_MUL_ARBITRATION\n";return 0;
 }catch(const std::exception&e){std::cerr<<e.what()<<"\n";return 1;}}
