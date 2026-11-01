#pragma once
#include <systemc>
#include <array>
using namespace sc_core;using namespace sc_dt;
// Exact signal-level contract of frozen block_feed_s16k, including arbitration
// and independent finite response registers. Memory is four 256x128 1RW banks.
struct SPort:sc_module{
 sc_in<bool>clk;sc_signal<bool>reset,req,wr,ready,valid,take,wide_req,wide_ready,wide_valid,wide_take;
 sc_signal<sc_uint<10>>addr;sc_signal<sc_uint<8>>wide_addr;
 sc_signal<sc_biguint<128>>din,dout;sc_signal<sc_biguint<512>>wide_dout;
 std::array<sc_biguint<128>,1024>mem{};
 uint64_t narrow_reads=0,narrow_writes=0,wide_reads=0,conflicts=0,held_narrow=0,held_wide=0;
 SC_HAS_PROCESS(SPort);
 SPort(sc_module_name n):sc_module(n){SC_METHOD(comb);sensitive<<reset<<valid<<take<<wide_valid<<wide_take<<wide_req;SC_METHOD(seq);sensitive<<clk.pos();dont_initialize();}
 void comb(){bool wready=!reset.read()&&(!wide_valid.read()||wide_take.read());wide_ready=wready;ready=!reset.read()&&(!valid.read()||take.read())&&!(wide_req.read()&&wready);}
 void seq(){
  if(reset.read()){valid=false;wide_valid=false;dout=0;wide_dout=0;return;}
  bool wf=wide_req.read()&&wide_ready.read();
  if(valid.read()&&!take.read())++held_narrow;if(wide_valid.read()&&!wide_take.read())++held_wide;
  if(valid.read()&&take.read())valid=false;if(wide_valid.read()&&wide_take.read())wide_valid=false;
  if(wf){sc_biguint<512>v;for(unsigned b=0;b<4;++b)v.range(b*128+127,b*128)=mem[wide_addr.read().to_uint()*4+b];wide_valid=true;wide_dout=v;++wide_reads;if(req.read())++conflicts;}
  else if(req.read()&&ready.read()){unsigned index=addr.read().to_uint();valid=true;if(wr.read()){mem[index]=din.read();dout=din.read();++narrow_writes;}else{dout=mem[index];++narrow_reads;}}
 }
};
