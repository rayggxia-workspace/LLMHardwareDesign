#pragma once
#include "m.hpp"
#include "n.hpp"
#include "e.hpp"
#include "g.hpp"
#include "r.hpp"
#include "s.hpp"
#include "Vblock_v2_m.h"
#include "Vblock_v2_n.h"
#include "Vblock_v2_e.h"
#include "Vblock_v2_g.h"
#include "Vr_stream_local.h"
#include "native_memory.hpp"
#include <sstream>

namespace layer {
template<class D> class Clocked {
public:
 D dut;
 uint64_t cycles=0,commands=0;
 void tick(){dut.clk=0;dut.eval();dut.clk=1;dut.eval();++cycles;dut.clk=0;dut.eval();}
 template<class F>void wait(F ready){unsigned guard=0;dut.eval();while(!ready()){tick();require(++guard<100000,"macro timeout");}}
};
template<class D>inline void pack16(D &data,const std::array<int16_t,8>&values) {
 for(unsigned i=0;i<4;++i)data[i]=uint16_t(values[2*i])|(uint32_t(uint16_t(values[2*i+1]))<<16);
}
inline void compare(const blocks::Reply &actual,const blocks::Reply &expected,const char *name) {
 if(actual.error!=expected.error||actual.saturated!=expected.saturated)
   throw std::runtime_error(std::string(name)+" status differs");
 for(unsigned i=0;i<expected.count;++i)
   if(actual.lane[i]!=expected.lane[i]) {
     std::ostringstream out;out<<name<<" lane "<<i<<" RTL "<<actual.lane[i]<<" SystemC "<<expected.lane[i];
     throw std::runtime_error(out.str());
   }
}
class Matrix : public Clocked<Vblock_v2_m> {
 blocks::MEngine oracle;
 std::array<uint32_t,4> command(unsigned op,unsigned index,uint64_t data,bool &error,bool &sat) {
  wait([&]{return dut.cmd_ready;});dut.cmd_valid=1;dut.cmd_op=op;dut.cmd_index=index;dut.cmd_data=data;
  tick();dut.cmd_valid=0;wait([&]{return dut.rsp_valid;});
  std::array<uint32_t,4> out{};for(unsigned i=0;i<4;++i)out[i]=dut.rsp_data[i];
  error=dut.rsp_error;sat=dut.rsp_saturated;dut.rsp_ready=1;tick();dut.rsp_ready=0;return out;
 }
public:
 Matrix(){dut.reset=1;dut.cmd_valid=0;dut.a_valid=0;dut.b_valid=0;dut.rsp_ready=0;tick();tick();dut.reset=0;tick();}
 blocks::Reply execute(const blocks::MCommand &c) {
  using Op=blocks::MCommand::Op;
  auto expected=oracle.execute(c);auto actual=blocks::reply(c);actual.count=expected.count;++commands;
  bool error=false,sat=false;std::array<uint32_t,4> data{};
  if(c.op==Op::LoadA) {
   wait([&]{return dut.a_ready;});dut.a_valid=1;dut.a_bank=c.bank;dut.a_row=c.row;dut.a_tile=c.tile;dut.a_wide=c.wide_a;
   for(unsigned i=0;i<4;++i)dut.a_data[i]=uint32_t(c.data[i/2]>>(32*(i%2)));
   tick();dut.a_valid=0;
  }else if(c.op==Op::LoadB) {
   dut.b_bank=c.bank;dut.b_tile=c.tile;dut.b_half=c.half;dut.b_wide=c.wide_b;dut.eval();
   wait([&]{return dut.b_ready;});dut.b_valid=1;
   for(unsigned i=0;i<16;++i)dut.b_data[i]=uint32_t(c.data[i/2]>>(32*(i%2)));
   tick();dut.b_valid=0;
  }else {
   unsigned op=0,index=0;uint64_t value=0;
   switch(c.op) {
    case Op::Reset:case Op::InvalidateAll:op=6;break;
    case Op::InvalidateBank:op=11;index=c.bank;break;
    case Op::Scale:op=4;value=uint16_t(c.coefficient)|(uint64_t(c.shift)<<16);break;
    case Op::Execute:op=10;index=c.bank<<5;value=unsigned(c.wide_a)|(unsigned(c.wide_b)<<1)|
      (unsigned(c.clear)<<2)|(c.last_k<<4)|(c.columns<<8)|(c.tiles<<12)|(c.rows<<15);break;
    case Op::ReadFull:op=3;index=c.row*8+c.pair;break;
    case Op::ReadPartial:op=12;index=c.row*8+c.pair;break;
    case Op::ReadFinal:op=5;index=c.row*8+c.half;value=c.shift|((c.width==8?0:c.width==16?1:2)<<8);break;
    default:throw std::runtime_error("unmapped M command");
   }
   data=command(op,index,value,error,sat);
   if(c.op==Op::ReadFull||c.op==Op::ReadPartial)
     for(unsigned i=0;i<2;++i)actual.lane[i]=int64_t(uint64_t(data[2*i])|(uint64_t(data[2*i+1])<<32));
   if(c.op==Op::ReadFinal)for(unsigned i=0;i<4;++i)actual.lane[i]=int32_t(data[i]);
  }
  actual.error=error;actual.saturated=sat;compare(actual,expected,"M");return actual;
 }
};
class Vector : public Clocked<Vblock_v2_e> {
 blocks::EEngine oracle;
public:
 Vector(){dut.reset=1;dut.in_valid=0;dut.out_ready=0;tick();tick();dut.reset=0;tick();}
 blocks::Reply execute(const blocks::ECommand &c) {
  auto expected=oracle.execute(c);auto actual=blocks::reply(c);actual.count=expected.count;++commands;
  if(c.op==blocks::ECommand::Op::Reset)return actual;
  wait([&]{return dut.in_ready;});dut.in_op=unsigned(c.op);dut.in_shift=c.shift;
  pack16(dut.in_a,c.a);pack16(dut.in_b,c.b);pack16(dut.in_c,c.c);dut.in_valid=1;tick();dut.in_valid=0;
  wait([&]{return dut.out_valid;});actual.error=dut.out_error;actual.saturated=dut.out_saturated;
  for(unsigned i=0;i<8;++i)actual.lane[i]=int16_t(dut.out_data[i/2]>>(16*(i%2)));
  if(c.op==blocks::ECommand::Op::Pack8)throw std::runtime_error("Pack8 needs explicit compact response ABI");
  dut.out_ready=1;tick();dut.out_ready=0;compare(actual,expected,"E");return actual;
 }
};
class Normalizer : public Clocked<Vblock_v2_n> {
 blocks::NEngine oracle;
public:
 Normalizer(){dut.reset=1;dut.cmd_valid=0;dut.rsp_ready=0;tick();tick();dut.reset=0;tick();}
 blocks::Reply execute(const blocks::NCommand &c) {
  using Op=blocks::NCommand::Op;
  auto expected=oracle.execute(c);auto actual=blocks::reply(c);actual.count=expected.count;++commands;
  if(c.op==Op::Reset){dut.reset=1;tick();dut.reset=0;tick();return actual;}
  wait([&]{return dut.cmd_ready;});dut.cmd_op=unsigned(c.op);dut.cmd_count=c.count;dut.cmd_param=0;
  for(unsigned i=0;i<4;++i){dut.cmd_data[i]=uint16_t(c.data[2*i])|(uint32_t(uint16_t(c.data[2*i+1]))<<16);dut.cmd_aux[i]=uint16_t(c.gamma[2*i])|(uint32_t(uint16_t(c.gamma[2*i+1]))<<16);}
  if(c.op==Op::Begin){dut.cmd_param=unsigned(c.mode);dut.cmd_data[0]=c.epsilon;for(unsigned i=1;i<4;++i)dut.cmd_data[i]=0;}
  if(c.op==Op::TopBegin)dut.cmd_param=c.k;
  if(c.op==Op::TopLoad)for(unsigned i=0;i<4;++i)dut.cmd_data[i]=uint16_t(c.data[i])|(uint32_t(c.ids[i])<<16);
  dut.cmd_valid=1;tick();dut.cmd_valid=0;wait([&]{return dut.rsp_valid;});
  actual.error=dut.rsp_error;actual.saturated=dut.rsp_saturated;
  if(c.op==Op::ReadStats) {
   actual.lane[0]=uint16_t(dut.rsp_data[0]);actual.lane[1]=int16_t(dut.rsp_data[0]>>16);
   actual.lane[2]=int16_t(dut.rsp_data[1]);actual.lane[3]=int32_t((dut.rsp_data[1]>>16)|(dut.rsp_data[2]<<16));
   actual.lane[4]=uint64_t(dut.rsp_data[2]>>16)|(uint64_t(dut.rsp_data[3])<<16);
   for(unsigned i=5;i<8;++i)actual.lane[i]=expected.lane[i]; // Extended observer counters have no native response lanes.
  }else if(c.op==Op::ReadFactor)actual.lane[0]=dut.rsp_data[0];
  else for(unsigned i=0;i<actual.count;++i)actual.lane[i]=(c.op==Op::NormReplay)?
    int64_t(int16_t(dut.rsp_data[i/2]>>(16*(i%2)))):int64_t(uint16_t(dut.rsp_data[i/2]>>(16*(i%2))));
  dut.rsp_ready=1;tick();dut.rsp_ready=0;compare(actual,expected,"N");return actual;
 }
};
class Activation : public Clocked<Vblock_v2_g> {
 blocks::GEngine oracle;
public:
 Activation(){dut.reset=1;dut.in_valid=0;dut.out_ready=0;tick();tick();dut.reset=0;tick();}
 blocks::Reply execute(const blocks::GCommand &c){
  auto expected=oracle.execute(c);auto actual=blocks::reply(c);actual.count=expected.count;++commands;
  if(c.function==blocks::GCommand::Function::Reset)return actual;
  wait([&]{return dut.in_ready;});dut.in_fn=unsigned(c.function);dut.in_gated=c.gated;
  dut.in_x=uint16_t(c.x[0])|(uint32_t(uint16_t(c.x[1]))<<16);
  dut.in_gate=uint16_t(c.gate[0])|(uint32_t(uint16_t(c.gate[1]))<<16);
  dut.in_valid=1;tick();dut.in_valid=0;wait([&]{return dut.out_valid;});
  actual.error=dut.out_error;actual.saturated=dut.out_saturated;
  actual.lane[0]=int16_t(dut.out_data);actual.lane[1]=int16_t(dut.out_data>>16);
  dut.out_ready=1;tick();dut.out_ready=0;compare(actual,expected,"G");return actual;
 }
};
class Recurrent : public Clocked<Vr_stream_local> {
 blocks::REngine oracle;
 unsigned active=0,length=0;
 std::array<int16_t,128> key{},query{};
 std::array<int32_t,8> saved_output{};
 void load(unsigned target,unsigned index,const uint32_t *data) {
  wait([&]{return dut.load_ready;});dut.load_target=target;dut.load_index=index;
  for(unsigned i=0;i<4;++i)dut.load_data[i]=data[i];
  dut.load_valid=1;tick();dut.load_valid=0;
 }
 void load32(unsigned target,unsigned index,const int32_t *data){load(target,index,reinterpret_cast<const uint32_t*>(data));}
 std::array<uint32_t,16> pass(unsigned op,unsigned rows,unsigned role,unsigned mode,bool clear) {
  wait([&]{return dut.cmd_ready;});dut.cmd_op=op;dut.cmd_rows=rows;dut.cmd_role=role;dut.cmd_mode=mode;dut.cmd_clear=clear;
  dut.cmd_valid=1;tick();dut.cmd_valid=0;wait([&]{return dut.rsp_valid;});
  require(!dut.rsp_error,"R RTL pass failed");std::array<uint32_t,16> result{};
  for(unsigned i=0;i<16;++i)result[i]=dut.rsp_data[i];
  dut.rsp_ready=1;tick();dut.rsp_ready=0;return result;
 }
public:
 Recurrent(){dut.reset=1;dut.load_valid=0;dut.rd_valid=0;dut.rd_rsp_ready=0;dut.cmd_valid=0;dut.rsp_ready=0;tick();tick();dut.reset=0;tick();}
 blocks::Reply execute(const blocks::RCommand &c) {
  using Op=blocks::RCommand::Op;
  auto expected=oracle.execute(c);auto actual=blocks::reply(c);actual.count=expected.count;++commands;
  switch(c.op) {
   case Op::Open:length=c.length;require(length<=128,"R1024 rows");active=0;pass(7,0,0,0,false);break;
   case Op::StateRow:for(unsigned half=0;half<2;++half)load32(active,c.index*2+half,c.values.data()+half*4);break;
   case Op::Key:key[c.index]=c.coefficients[0];break;
   case Op::Query:query[c.index]=c.coefficients[0];break;
   case Op::X:for(unsigned half=0;half<2;++half)load32(4,half,c.values.data()+half*4);break;
   case Op::Parameters:{uint32_t data[4]={c.decay,c.beta,0,0};load(5,0,data);break;}
   case Op::History:for(unsigned half=0;half<2;++half)load32(6,c.index*2+half,c.values.data()+half*4);break;
   case Op::Taps:load(7,c.index,reinterpret_cast<const uint32_t*>(c.coefficients.data()));break;
   case Op::Execute:{
    std::array<uint32_t,16> output{};
    if(c.mode==blocks::RCommand::Mode::Conv4){pass(6,0,0,2,true);output=pass(5,0,0,2,false);}
    else {
     require(c.mode==blocks::RCommand::Mode::GDN,"only selected GDN mode");
     for(unsigned index=0;index<(length+7)/8;++index){
      load(2,index,reinterpret_cast<const uint32_t*>(key.data()+index*8));
      load(3,index,reinterpret_cast<const uint32_t*>(query.data()+index*8));
     }
     pass(0,length,active,0,false);pass(1,length,active,0,true);pass(4,0,active,0,false);
     pass(2,length,active,0,false);pass(3,length,active,0,true);
     output=pass(5,0,active,0,false);
    }
    for(unsigned i=0;i<8;++i)saved_output[i]=int32_t(output[i*2]);
    break;}
   case Op::ReadOutput:for(unsigned i=0;i<8;++i)actual.lane[i]=saved_output[i];break;
   case Op::Commit:active^=1;break;
   case Op::ReadState:
    for(unsigned half=0;half<2;++half){
     wait([&]{return dut.rd_ready;});dut.rd_valid=1;dut.rd_bank=active;dut.rd_index=c.index*2+half;
     tick();dut.rd_valid=0;wait([&]{return dut.rd_rsp_valid;});
     for(unsigned i=0;i<4;++i)actual.lane[half*4+i]=int32_t(dut.rd_data[i]);
     dut.rd_rsp_ready=1;tick();dut.rd_rsp_ready=0;
    }break;
   default:throw std::runtime_error("unsupported selected-layer R command");
  }
  compare(actual,expected,"R");return actual;
 }
};
} // namespace layer

namespace blocks {
template<class Engine>struct NativeEngine { using type=Engine; };
template<>struct NativeEngine<MEngine> {using type=layer::Matrix;};
template<>struct NativeEngine<NEngine> {using type=layer::Normalizer;};
template<>struct NativeEngine<EEngine> {using type=layer::Vector;};
template<>struct NativeEngine<GEngine> {using type=layer::Activation;};
template<>struct NativeEngine<REngine> {using type=layer::Recurrent;};
}
