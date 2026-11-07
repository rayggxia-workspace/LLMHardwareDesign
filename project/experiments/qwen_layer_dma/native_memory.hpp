#pragma once
#include "Vlayer_dma.h"
#include "verilated.h"
#include <algorithm>
#include <array>
#include <cstdint>
#include <cstring>
#include <deque>
#include <fstream>
#include <stdexcept>

namespace layer {
inline void require(bool condition, const char *message) {
  if (!condition) throw std::runtime_error(message);
}
struct Counts { uint64_t reads=0,writes=0,read_bytes=0,write_bytes=0; };
class Memory {
  Vlayer_dma dut;
  struct Request { uint64_t address, due; uint16_t id; bool write; std::array<uint32_t,4> data; };
  std::deque<Request> pending;
  uint64_t base=0, extent=0;
  unsigned char *backing=nullptr;
  unsigned category=0;
  uint16_t tag=0;
public:
  uint64_t cycles=0,descriptors=0,held_requests=0;
  std::array<Counts,4> completed{};
  Memory() {
    dut.reset=1;
    dut.desc_valid=0;dut.complete_ready=0;dut.host_select=0;dut.host_req=0;dut.host_take=0;
    dut.mem_ready=0;dut.response_valid=0;
    for(unsigned i=0;i<4;++i) tick();
    dut.reset=0; tick();
  }
  void tick() {
    dut.clk=0;dut.mem_ready=pending.size()<8 && cycles%7!=0;
    dut.response_valid=!pending.empty()&&pending.front().due<=cycles&&cycles%5!=0;
    if(dut.response_valid) {
      const auto &q=pending.front();
      for(unsigned k=0;k<4;++k) dut.response_data[k]=q.data[k];
      dut.response_data[4]=q.id;dut.response_data[4+1-1]&=0xffffu;
    }
    dut.eval();
    const bool accepted=dut.mem_valid&&dut.mem_ready;
    const bool returned=dut.response_valid&&dut.response_ready;
    Request q{};
    if(accepted) {
      q.address=uint64_t(dut.mem_data[4])|(uint64_t(dut.mem_data[5]&255)<<32);
      q.id=uint16_t(dut.mem_data[5]>>8);q.write=bool(dut.mem_data[5]&(1u<<24));q.due=cycles+3;
      require(q.address>=base&&q.address+16<=base+extent,"DMA request outside supplied region");
      for(unsigned k=0;k<4;++k) q.data[k]=dut.mem_data[k];
    }
    if(dut.mem_valid&&!dut.mem_ready) ++held_requests;
    if(returned) {
      auto &done=pending.front();auto &count=completed[category];
      if(done.write) {++count.writes;count.write_bytes+=16;}
      else {++count.reads;count.read_bytes+=16;}
      pending.pop_front();
    }
    if(accepted) {
      const auto offset=q.address-base;
      if(q.write) std::memcpy(backing+offset,q.data.data(),16);
      else std::memcpy(q.data.data(),backing+offset,16);
      pending.push_back(q);
    }
    dut.clk=1;dut.eval();++cycles;
    require(!dut.protocol_error,"DMA protocol error");
    dut.clk=0;dut.eval();
  }
  void local(unsigned word, void *bytes, bool write) {
    dut.host_select=1;dut.host_write=write;dut.host_address=word;dut.host_req=1;dut.host_take=0;
    if(write)std::memcpy(dut.host_data.data(),bytes,16);
    dut.eval();unsigned guard=0;
    while(!dut.host_ready) {tick();require(++guard<100,"S request timed out");}
    tick();dut.host_req=0;dut.eval();
    while(!dut.host_valid) {tick();require(++guard<100,"S response timed out");}
    if(!write)std::memcpy(bytes,dut.host_result.data(),16);
    dut.host_take=1;tick();dut.host_take=0;dut.host_select=0;
  }
  void transfer(unsigned kind,uint64_t address,unsigned char *storage,uint64_t storage_bytes,
                void *payload,size_t count,bool write) {
    require(kind<4&&count>0,"invalid native memory request");
    const uint64_t first=address&~uint64_t(15);
    const size_t skip=size_t(address-first);
    const unsigned words=unsigned((skip+count+15)/16);
    require(words<=17&&(!write||(skip==0&&count%16==0)),"native write requires full aligned words");
    base=kind==0?0:(15+kind)*(1ULL<<30);
    backing=storage;extent=storage_bytes;category=kind;
    require(first>=base&&first+uint64_t(words)*16<=base+extent,"native transfer extent");
    std::array<unsigned char,17*16> scratch{};
    if(write) {
      std::memcpy(scratch.data(),payload,count);
      for(unsigned i=0;i<words;++i) local(i,scratch.data()+i*16,true);
    }
    dut.desc_valid=1;dut.desc_write=write;dut.desc_address=first;
    dut.desc_local=0;dut.desc_words=words;dut.desc_tag=++tag;dut.complete_ready=0;
    dut.eval();unsigned guard=0;
    while(!dut.desc_ready){tick();require(++guard<100000,"DMA descriptor blocked");}
    tick();dut.desc_valid=0;dut.eval();
    while(!dut.complete_valid){tick();require(++guard<100000,"DMA completion blocked");}
    require(dut.complete_status==0&&dut.complete_tag==tag&&dut.completed_words==words,"DMA completion mismatch");
    require(pending.empty(),"DMA completed with memory response pending");
    dut.complete_ready=1;tick();dut.complete_ready=0;++descriptors;
    if(!write) {
      for(unsigned i=0;i<words;++i) local(i,scratch.data()+i*16,false);
      std::memcpy(payload,scratch.data()+skip,count);
    }
  }
  void report(std::ostream &out,unsigned position,unsigned layer) const {
    for(unsigned kind=0;kind<4;++kind) {
      const auto &c=completed[kind];
      out<<position<<','<<layer<<','<<kind<<','<<c.reads<<','<<c.writes<<','
         <<c.read_bytes<<','<<c.write_bytes<<','<<cycles<<','<<descriptors<<'\n';
    }
  }
};
inline Memory &memory() { static Memory device; return device; }
} // namespace layer
