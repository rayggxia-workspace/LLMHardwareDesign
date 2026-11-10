#include "Vp_scope_range_joint.h"
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
  auto model=std::make_unique<Vp_scope_range_joint>(context.get());auto& d=*model;
  auto rise=[&]{d.clk=1;d.eval();context->timeInc(1);d.clk=0;d.eval();context->timeInc(1);};
  d.reset=1;d.scope_valid=0;d.record_ready=0;d.complete_valid=0;d.cancel_valid=0;d.done_ready=0;
  for(int i=0;i<3;++i)rise();d.reset=0;d.eval();
  unsigned cases=0,records=0,complete=0,rejected=0,max_live=0,total_cycles=0;
  unsigned tail_mask=0,invalid_cases=0;
  for(unsigned test=0;test<144;++test) {
   Job j{137,0,24,6,2,512,0,512,1000+test*10000,bool(test%3==0),1};
   if(test%4==1) {j.n=128;j.groups=16;j.stride=8;j.ctx=0;}
   if(test%4==2) {j.n=11008;j.col=10400;j.groups=9;j.stride=24;j.ctx=3;j.full=2048;j.begin=128;j.end=384;}
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
   std::array<uint8_t,128> raw{};
   auto put=[&](unsigned at,unsigned len,uint64_t v) {
    for(unsigned i=0;i<len;++i)raw[at+i]=uint8_t(v>>(8*i));
   };
   put(0,4,0x02505001U);put(4,2,128);put(6,2,1);
   put(8,4,0x02504d02U);put(12,4,0x01020304U);
   put(32,4,0x10000000U);put(36,4,0x20000000U);
   put(40,4,9);put(44,4,j.seq);put(48,8,base0);put(56,8,base1);
   put(64,4,j.n);put(68,4,j.col);put(72,2,j.stride);
   put(74,1,j.groups);put(75,1,j.ctx);put(76,2,j.full);put(78,2,j.begin);
   put(80,2,j.end);put(82,1,j.ways);put(83,1,j.head);
   put(84,2,0);put(86,2,512);put(88,2,576);put(90,2,800);put(92,2,640);
   for(unsigned w=0;w<32;++w) {
    uint32_t v=0;for(unsigned b=0;b<4;++b)v|=uint32_t(raw[w*4+b])<<(8*b);
    d.scope_data[w]=v;
   }
   d.scope_crc_ok=1;d.expected_topology=0x01020304U;d.reject_ready=0;
   d.scope_valid=1;d.eval();
   if(invalid) {
    check(d.reject_valid && !d.scope_ready && d.reject_code!=0,"bad scope was not held as rejection");
    for(unsigned hold=0;hold<3;++hold) {rise();check(!d.record_valid && d.reject_valid,"rejected scope issued record");}
    d.reject_ready=1;d.eval();check(d.scope_ready,"reject acceptance missing");
    rise();d.scope_valid=0;d.reject_ready=0;d.eval();
    continue;
   }
   check(d.scope_ready && !d.reject_valid,"legal typed scope did not admit");
   rise();d.scope_valid=0;
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
  // Type-level failures are separate from legal range exhaustion/errors.
  for(unsigned test=0;test<17;++test) {
   std::array<uint8_t,128> raw{};
   auto put=[&](unsigned at,unsigned len,uint64_t v) {
    for(unsigned i=0;i<len;++i)raw[at+i]=uint8_t(v>>(8*i));
   };
   put(0,4,0x02505001U);put(4,2,128);put(6,2,1);put(8,4,0x02504d02U);
   put(12,4,0x01020304U);put(32,4,0x10000000U);put(36,4,0x20000000U);
   put(48,8,0x100000000ULL);put(56,8,0x300000000ULL);
   put(64,4,128);put(72,2,8);put(74,1,8);put(76,2,256);put(80,2,256);
   put(82,1,2);put(86,2,128);put(88,2,192);put(90,2,256);put(92,2,320);
   d.scope_crc_ok=1;d.expected_topology=0x01020304U;
   unsigned code=2;
   switch(test) {
    case 0:put(0,4,0x02505002U);break;
    case 1:put(4,2,127);break;
    case 2:put(6,2,2);code=4;break;
    case 3:put(6,2,3);code=4;break;
    case 4:put(8,4,0x02504d01U);break;
    case 5:d.expected_topology^=1;code=3;break;
    case 6:put(112,1,1);break;
    case 7:d.scope_crc_ok=0;code=1;break;
    case 8:put(36,4,0x10000000U);code=6;break;
    case 9:put(32,4,0xfffffffcU);code=6;break;
    case 10:put(86,2,1024);code=7;break;
    case 11:put(86,2,8);code=7;break;
    case 12:put(80,2,128);put(92,2,128);code=7;break;
    case 13:put(48,8,0xffffffffffc0ULL);code=5;break;
    case 14:put(96,8,3);code=5;break;
    case 15:put(74,1,0x28);break;
    default:put(75,1,0x10);break;
   }
   for(unsigned w=0;w<32;++w) {
    uint32_t v=0;for(unsigned b=0;b<4;++b)v|=uint32_t(raw[w*4+b])<<(8*b);
    d.scope_data[w]=v;
   }
   d.scope_valid=1;d.reject_ready=0;d.eval();
   check(d.reject_valid && d.reject_code==code && !d.scope_ready,"typed reject reason mismatch");
   for(unsigned hold=0;hold<4;++hold) {rise();check(!d.record_valid&&d.reject_valid,"typed reject issued traffic");}
   d.reject_ready=1;d.eval();check(d.scope_ready,"typed reject could not retire");
   rise();d.scope_valid=0;d.reject_ready=0;d.eval();++invalid_cases;
  }
  check(max_live==6&&rejected>0&&tail_mask==0xfe&&invalid_cases==29,"missing credit, tail, or negative coverage");
  std::cout<<"PASS typed-range cases="<<cases<<" records="<<records<<" completed="<<complete<<" rejected="<<rejected
           <<" peak_tickets="<<max_live<<" tails="<<tail_mask<<" invalid="<<invalid_cases
           <<" cycles="<<total_cycles<<" initial="<<initial<<"\n";
  model.reset();return 0;
 } catch(const std::exception& error) {std::cerr<<error.what()<<"\n";return 1;}
}
