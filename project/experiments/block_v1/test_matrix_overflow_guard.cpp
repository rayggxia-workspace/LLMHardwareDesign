// Fault injection checks the defensive S64 overflow guard outside legal input
// magnitudes. The public API must reject the whole result; no injected state
// is accepted as evidence of a legal numeric workload.
#include "Vblock_v1_m.h"
#include "Vblock_v1_m___024root.h"
#include "verilated.h"
#include <cstdint>
#include <iostream>
#include <stdexcept>
using U128=__uint128_t;
static Vblock_v1_m d;
static unsigned cycles=0,checks=0;
static void ck(bool p,const char*s){++checks;if(!p)throw std::runtime_error(s);}
static void tick(){d.clk=0;d.eval();d.clk=1;d.eval();++cycles;}
static void put(U128 x){for(unsigned i=0;i<4;++i){d.cmd_data[i]=uint32_t(x);x>>=32;}}
static U128 get(){U128 x=0;for(int i=3;i>=0;--i)x=x<<32|d.rsp_data[i];return x;}
static U128 command(unsigned op,unsigned index,U128 payload,bool error=false){
 d.clk=0;d.eval();ck(d.cmd_ready,"input not ready");d.cmd_valid=1;d.cmd_op=op;d.cmd_index=index;put(payload);d.rsp_ready=0;tick();d.cmd_valid=0;
 unsigned elapsed=0;while(!d.rsp_valid){tick();ck(++elapsed<100,"response timeout");}
 ck(bool(d.rsp_error)==error,error?"expected signed overflow rejection":"unexpected error");
 U128 data=get();ck(!d.rsp_saturated,"unexpected saturation");
 for(unsigned i=0;i<4;++i){d.cmd_valid=1;d.cmd_op=3;put(0);d.clk=0;d.eval();ck(!d.cmd_ready,"error response did not block reads");tick();ck(d.rsp_valid&&get()==data&&bool(d.rsp_error)==error,"held result changed");}
 d.cmd_valid=0;d.rsp_ready=1;tick();d.rsp_ready=0;return data;
}
int main(int argc,char**argv){try{
 Verilated::commandArgs(argc,argv);d.reset=1;d.cmd_valid=0;d.rsp_ready=0;tick();d.reset=0;tick();
 for(unsigned burst=0;burst<2;++burst)for(unsigned negative=0;negative<2;++negative){
  command(6,0,0);
  command(0,0,1);for(unsigned r=0;r<8;++r)command(1,r,1);
  command(2,0,U128(4)|(U128(1)<<4)|(U128(8)<<8));
  command(4,0,U128(1)|(U128(1)<<39));
  U128 saved=command(5,0,U128(2)<<8);
  ck(saved==(U128(1)|(U128(1)<<32)|(U128(1)<<64)|(U128(1)<<96)),"bad initial result");
  if(burst){
   command(7,32,negative?U128(255):U128(1));
   for(unsigned pair=0;pair<4;++pair)command(8,32+pair,U128(1)|(U128(1)<<64));
  }else command(0,0,negative?U128(65535):U128(1));
  d.rootp->block_v1_m__DOT__accumulator[7]=negative?UINT64_C(0x8000000000000000):UINT64_C(0x7fffffffffffffff);
  d.eval();
  auto tag=command(burst?10:2,burst?32:0,(U128(1)<<4)|(U128(8)<<8)|(burst?U128(1)<<12:0),true);
  ck(tag==(burst?U128(1)<<127:0),"wrong completion tag");
  command(3,0,0,true);command(3,3,0,true);
  ck(command(5,0,U128(2)<<8)==saved,"overflow changed previous complete result");
  command(4,0,U128(1)|(U128(1)<<39),true);
 }
 std::cout<<"{\"passed\":true,\"fault_injections\":4,\"checks\":"<<checks<<",\"cycles\":"<<cycles<<"}\n";return 0;
}catch(const std::exception&e){std::cerr<<e.what()<<" at cycle "<<cycles<<"\n";return 1;}}

