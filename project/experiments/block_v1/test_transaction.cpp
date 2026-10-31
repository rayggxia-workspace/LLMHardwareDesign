#include "Vtransaction6k.h"
#include "verilated.h"
#include <array>
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <random>
#include <stdexcept>
#include <string>
#include <vector>

// Functional queue scoreboard: payload visibility/ownership/lifetime are checked
// without inspecting DUT internal state or predicting its read microarchitecture.
struct Test {
 Vtransaction6k d;
 std::mt19937 rng{1212026102};
 enum Phase { EMPTY, WRITING, FULL, PUBLISHED, RELEASE } phase = EMPTY;
 using Word = std::array<uint32_t,4>;
 std::vector<Word> expected;
 unsigned count=0, written=0, next=0, owner=0, cycles=0, checks=0;
 uint32_t generation=0;
 bool error=false, was_held=false;
 Word held{};
 unsigned held_index=0, silent=0;
 void require(bool good, const std::string& message) {
  ++checks;
  if (!good) throw std::runtime_error("cycle "+std::to_string(cycles)+": "+message);
 }
 void clear() {
  d.begin_valid=0; d.write_valid=0; d.commit_valid=0; d.revoke_valid=0;
  d.read_take=0; d.release_valid=0;
 }
 Word random_word() { Word w; for (auto &x:w) x=rng(); return w; }
 Word value() { return {d.read_data[0], d.read_data[1], d.read_data[2], d.read_data[3]}; }
 void tick() {
  d.clk=0; d.eval();
  if (d.reset) {
   require(!d.read_valid && !d.write_ready && !d.begin_ready && !d.commit_ready && !d.revoke_ready && !d.release_ready,"reset handshake");
   phase=EMPTY; error=false; was_held=false; silent=0;
  } else {
   require(bool(d.busy)==(phase!=EMPTY),"busy and reference lease");
   require(bool(d.begin_ready)==(phase==EMPTY && d.begin_words>0 && d.begin_words<=384),"capacity admission");
   require(bool(d.write_ready)==(phase==WRITING && !d.revoke_valid && d.write_index==written),"write/index admission");
   require(bool(d.revoke_ready)==(phase==WRITING || phase==FULL),"revoke boundary");
   require(bool(d.commit_ready)==(phase==FULL && !d.revoke_valid),"commit boundary");
   require(bool(d.sealed)==(phase==FULL),"whole payload required");
   require(bool(d.committed)==(phase==PUBLISHED || phase==RELEASE),"publication boundary");
   require(bool(d.release_ready)==(phase==RELEASE),"release after last take");
   require(bool(d.protocol_error)==error,"sticky malformed-input indication");
   if (phase!=EMPTY) {
    require(d.owner==owner && d.generation==generation && d.word_count==count,"stable owner/generation/length");
   }
   if (was_held) require(d.read_valid && value()==held && d.read_index==held_index,"backpressure payload hold");
   if (d.read_valid) {
    require(phase==PUBLISHED,"no provisional or revoked visibility");
    require(next<count && d.read_index==next,"exactly-once ordered read");
    require(value()==expected[next],"payload bytes/canary");
    require(bool(d.read_last)==(next+1==count),"last beat");
    silent=0;
   } else if (phase==PUBLISHED) {
    require(++silent<=3,"bounded synchronous read response");
   } else silent=0;
   was_held=d.read_valid && !d.read_take;
   held=value(); held_index=d.read_index;
   if (d.begin_valid && phase==EMPTY && !(d.begin_words>0 && d.begin_words<=384)) error=true;
   if (d.write_valid && phase==WRITING && !d.revoke_valid && d.write_index!=written) error=true;
   if (d.revoke_valid && d.revoke_ready) { phase=EMPTY; was_held=false; }
   else if (d.begin_valid && d.begin_ready) {
    phase=WRITING; count=d.begin_words; owner=d.begin_owner; generation=d.begin_generation;
    written=0; next=0; expected.clear();
   } else if (d.write_valid && d.write_ready) {
    expected.push_back({d.write_data[0],d.write_data[1],d.write_data[2],d.write_data[3]});
    if (++written==count) phase=FULL;
   } else if (d.commit_valid && d.commit_ready) { phase=PUBLISHED; silent=0; }
   else if (d.read_valid && d.read_take) { if (++next==count) phase=RELEASE; }
   else if (d.release_valid && d.release_ready) phase=EMPTY;
  }
  d.clk=1; d.eval(); ++cycles;
 }
 void reset() { clear(); d.reset=1; tick(); d.reset=0; tick(); }
 void begin(unsigned size, unsigned trial) {
  clear(); d.begin_words=size; d.begin_owner=trial%4;
  d.begin_generation=trial%2 ? 0xffffffffu : trial;
  d.begin_valid=1; tick(); clear();
 }
 void write(unsigned index) {
  d.write_index=index; Word w=random_word(); for(unsigned j=0;j<4;++j) d.write_data[j]=w[j];
  d.write_valid=1; tick(); d.write_valid=0;
 }
 void run() {
  reset();
  begin(0,0); begin(385,0); require(phase==EMPTY,"invalid sizes did not acquire lease");
  for (unsigned trial=0;trial<240;++trial) {
   unsigned size= trial%8==0 ? 384 : trial%8==1 ? 256 : trial%8==2 ? 128 : trial%8==3 ? 32 : 1+rng()%384;
   begin(size,trial);
   bool revoked=false;
   for (unsigned i=0;i<size;++i) {
    if (trial%7==0 && i==size/2) { write(i+1); require(written==i,"bad index not consumed"); }
    for (unsigned gap=0;gap<rng()%4;++gap) {
     d.commit_valid=1; d.release_valid=1; tick(); clear();
    }
    if (trial%5==0 && i==size/2) {
     d.revoke_valid=1; d.write_valid=1; d.write_index=i; tick(); clear(); revoked=true; break;
    }
    write(i);
   }
   if (revoked) { for(int i=0;i<3;++i) tick(); continue; }
   for(int i=0;i<3;++i) { d.release_valid=1; tick(); clear(); }
   if (trial%11==0) {
    d.revoke_valid=1; d.commit_valid=1; tick(); clear();
    require(phase==EMPTY,"revoke wins before irreversible commit"); continue;
   }
   if (trial%13==0) { reset(); continue; }
   d.commit_valid=1; tick(); clear();
   while(phase==PUBLISHED) {
    // Revoke and duplicate commit are ignored once published; release cannot
    // free storage while a reader still holds the final response.
    d.revoke_valid=1; d.commit_valid=1; d.release_valid=1; d.read_take=rng()%4==0;
    tick(); clear();
   }
   for(int i=0;i<7;++i) {
    d.begin_valid=1; d.revoke_valid=1; tick(); clear();
    require(phase==RELEASE,"old reference prevents bank reuse");
   }
   d.release_valid=1; tick(); clear();
  }
  // Coordinated hard reset clears a committed lease; payload is not reset and
  // must be overwritten before its next publication.
  begin(1,999); write(0); d.commit_valid=1; tick(); clear(); tick(); reset();
  begin(384,1000); for(unsigned i=0;i<384;++i) write(i);
  d.commit_valid=1; tick(); clear();
  unsigned burst_first=0,burst_last=0,burst_count=0;
  while(phase==PUBLISHED) {
   d.read_take=1; d.eval();
   if(d.read_valid){if(!burst_count)burst_first=cycles;burst_last=cycles;++burst_count;}
   tick();
  }
  require(burst_count==384 && burst_last-burst_first+1==384,"continuous committed burst: one word per cycle");
  clear(); d.release_valid=1; tick(); clear(); tick();
  std::cout << "{\"passed\":true,\"seed\":1212026102,\"transactions\":242,\"cycles\":" << cycles
            << ",\"continuous_burst_words\":" << burst_count << ",\"continuous_burst_cycles\":" << burst_last-burst_first+1
            << ",\"assertions\":" << checks << "}\n";
 }
};
int main(int argc,char**argv) {
 Verilated::commandArgs(argc,argv);
 try { Test test; test.run(); } catch(const std::exception& e) { std::cerr<<e.what()<<"\n"; return 1; }
}
