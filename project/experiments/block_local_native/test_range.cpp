#include "Vrecord_range_iterator.h"
#include "verilated.h"
#include <algorithm>
#include <array>
#include <cstdint>
#include <iostream>
#include <memory>
#include <random>
#include <stdexcept>
#include <vector>

static void check(bool condition, const char* why) { if (!condition) throw std::runtime_error(why); }
struct Ticket { uint32_t seq, ctx, next; unsigned ready; };
struct Job { uint32_t n, col, stride, groups, ctx, full, begin, end, seq; bool head; uint32_t ways; };
struct Record {
 uint32_t seq, k, col, ctx, n, flags, uses, bytes, way; uint64_t address;
 bool operator==(const Record& b) const {
  return seq==b.seq && k==b.k && col==b.col && ctx==b.ctx && n==b.n &&
         flags==b.flags && uses==b.uses && bytes==b.bytes && way==b.way && address==b.address;
 }
};
int main(int argc, char** argv) {
 try {
  check(argc==3,"seed and initial required");
  const unsigned seed=unsigned(std::stoul(argv[1])),initial=unsigned(std::stoul(argv[2]));
  std::mt19937 rng(seed);auto context=std::make_unique<VerilatedContext>();
  context->commandArgs(argc,argv);context->randReset(int(initial));context->randSeed(int(seed));
  auto model=std::make_unique<Vrecord_range_iterator>(context.get());auto& d=*model;
  auto rise=[&]{d.clk=1;d.eval();context->timeInc(1);d.clk=0;d.eval();context->timeInc(1);};
  d.reset=1;d.job_valid=0;d.record_ready=0;d.complete_valid=0;d.cancel_valid=0;d.done_ready=0;
  for(int i=0;i<3;++i)rise();d.reset=0;d.eval();
  unsigned cases=0,records=0,complete=0,rejected=0,max_live=0,total_cycles=0;
  unsigned tail_mask=0,invalid_cases=0;
  for(unsigned test=0;test<144;++test) {
   Job j{137,0,24,6,2,512,0,512,1000+test*10000,bool(test%3==0),1};
   if(test%4==1) {j.n=128;j.groups=16;j.stride=8;j.ctx=0;}
   if(test%4==2) {j.n=11008;j.col=10400;j.groups=9;j.stride=24;j.ctx=3;j.full=11008;j.begin=128;j.end=384;}
   if(test%4==3) {j.n=151936;j.groups=12;j.ctx=0;j.full=2048;j.end=2048;}
   if(test%4==0 || test%4==2) {j.ways=2;j.groups=6;}
   if(test%4==0) {j.col=16;j.n=137+(test/4)%7;}
   const bool invalid=test%12==0,cancel=test%12==5,error=test%12==7;
   uint64_t base0=0x100000000ULL,base1=0x300000000ULL;
   if(invalid) {
    ++invalid_cases;
    switch(test/12) {
     case 0:j.groups=17;break;
     case 1:j.begin=1;break;
     case 2:j.col=j.n;break;
     case 3:j.ctx=15;j.groups=2;break;
     case 4:j.groups=0;break;
     case 5:j.ways=0;break;
     case 6:j.ways=3;break;
     case 7:j.stride=7;break;
     case 8:j.seq=0xfffffff8U;break;
     case 9:base0+=1;break;
     case 10:base0=0xfffffffffffffc00ULL;break;
     default:base1=0xffffffffffc0ULL;break;
    }
   }
   const std::array<uint32_t,4> owner={0x42000000U+test,17U+test,300U+seed,0x80000000U+test};
   for(unsigned w=0;w<4;++w)d.job_owner[w]=owner[w];
   d.job_sequence_base=j.seq;d.job_weight_base=base0;d.job_weight_base1=base1;
   d.job_ways=j.ways;d.job_columns=j.n;d.job_first_col=j.col;
   d.job_col_stride=j.stride;d.job_groups=j.groups;d.job_first_context=j.ctx;
   d.job_full_k=j.full;d.job_k_begin=j.begin;d.job_k_end=j.end;d.job_head16=j.head;
   check(d.job_ready,"job did not drain");d.job_valid=1;d.eval();rise();d.job_valid=0;
   std::vector<Record> expected;
   if(!invalid) for(uint32_t k=j.begin;k<j.end;k+=128) for(uint32_t way=0;way<j.ways;++way) for(uint32_t c=0;c<j.groups;++c) {
    const uint32_t col=j.col+c*j.stride,bytes=j.head?1152:1088;
    const uint32_t flags=(k==0)|((k==j.begin&&k!=0)<<1)|((k+128==j.full)<<2)|
          ((k+128==j.end&&j.end!=j.full)<<3)|((c==0&&way==0)<<4)|((c+1==j.groups&&way+1==j.ways)<<5)|(uint32_t(j.head)<<6);
    expected.push_back(Record{j.seq+uint32_t(expected.size()),k,col,j.ctx+c+way*j.groups,std::min(8U,j.n-col),flags,j.groups*j.ways,bytes,way,
      (way?base1:base0)+(uint64_t(col/8)*(j.full/128)+k/128)*bytes});
   }
   std::vector<Ticket> pending;unsigned sent=0,retired=0;bool cancelled=false,faulted=false,finished=false;
   uint32_t failed_sequence=0xffffffffU,failed_next=0;
   bool held=false;Record previous{};
   for(unsigned cycle=0;cycle<20000 && !finished;++cycle) {
    d.record_ready=(rng()%5)!=0;d.complete_valid=0;d.cancel_valid=0;d.done_ready=(rng()%4)!=0;
    if(cancel && sent>=4 && !cancelled) {for(unsigned w=0;w<4;++w)d.cancel_owner[w]=owner[w];d.cancel_valid=1;cancelled=true;}
    int selected=-1;bool bad=false;
    if(!pending.empty() && (rng()%3)!=0) {
     std::vector<unsigned> eligible;for(unsigned i=0;i<pending.size();++i)if(pending[i].ready<=cycle)eligible.push_back(i);
     if(!eligible.empty()) {
      selected=int(eligible[rng()%eligible.size()]);const auto& t=pending[unsigned(selected)];
      d.complete_valid=1;for(unsigned w=0;w<4;++w)d.complete_owner[w]=owner[w];
      d.complete_sequence=t.seq;d.complete_context=t.ctx;d.complete_next_k=t.next;d.complete_error=0;
      // Wrong epoch and wrong context must not steal live tickets.
      if(cycle%11==0) {d.complete_owner[2]^=1;bad=true;}
      else if(cycle%13==0) {d.complete_context^=1;bad=true;}
      else if(error && !faulted) {d.complete_next_k=t.next+1;faulted=true;failed_sequence=t.seq;failed_next=t.next+1;}
     }
    }
    d.eval();
    Record actual{d.record_sequence,d.record_k,d.record_col,d.record_context,d.record_n,
     uint32_t(d.record_create)|(uint32_t(d.record_restore)<<1)|(uint32_t(d.record_final)<<2)|
     (uint32_t(d.record_spill)<<3)|(uint32_t(d.record_A_first)<<4)|(uint32_t(d.record_A_last)<<5)|
     (uint32_t(d.record_head16)<<6),d.record_A_uses,d.record_bytes,d.record_way,d.record_address};
    if(held)check(d.record_valid && actual==previous,"offered record changed under backpressure/cancel");
    held=d.record_valid&&!d.record_ready;previous=actual;
    if(d.complete_valid) {check(bool(d.complete_ready)!=bad,"completion ownership mismatch");if(bad)++rejected;}
    if(d.record_valid&&d.record_ready) {
     check(sent<expected.size() && actual==expected[sent],"range address/order/metadata mismatch");
     for(unsigned w=0;w<4;++w)check(d.record_owner[w]==owner[w],"record owner mismatch");
     check(d.record_full_k==j.full,"record fullK mismatch");
     if(actual.n<8)tail_mask|=1U<<actual.n;
     pending.push_back(Ticket{actual.seq,actual.ctx,actual.k+128,cycle+8+unsigned(rng()%11)});++sent;++records;
    }
    if(d.complete_valid&&d.complete_ready) {check(selected>=0,"unselected completion");pending.erase(pending.begin()+selected);++retired;++complete;}
    max_live=std::max(max_live,unsigned(pending.size()));check(pending.size()<=6,"ticket credit exceeded");
    if(d.done_valid&&d.done_ready) {
     check(pending.empty()&&sent==retired,"job finished before drain");
     check(d.done_issued==sent&&d.done_completed==retired,"terminal accounting mismatch");
     check(bool(d.done_error)==(invalid||error),"terminal error mismatch");
     check(bool(d.done_cancelled)==cancel,"terminal cancel mismatch");
     check(d.done_failed_sequence==failed_sequence&&d.done_failed_next_k==failed_next,"first failure identity lost");
     if(!cancel&&!error)check(sent==expected.size(),"normal job lost records");
     if(cancel||error)check(sent<expected.size(),"stop did not stop issuing");
     finished=true;
    }
    rise();++total_cycles;
   }
   check(finished,"range timeout");++cases;
  }
  check(max_live==6&&rejected>0&&tail_mask==0xfe&&invalid_cases==12,"missing credit, tail, or negative coverage");
  std::cout<<"PASS range cases="<<cases<<" records="<<records<<" completed="<<complete<<" rejected="<<rejected
           <<" peak_tickets="<<max_live<<" tails="<<tail_mask<<" invalid="<<invalid_cases
           <<" cycles="<<total_cycles<<" initial="<<initial<<"\n";
  model.reset();return 0;
 } catch(const std::exception& error) {std::cerr<<error.what()<<"\n";return 1;}
}
