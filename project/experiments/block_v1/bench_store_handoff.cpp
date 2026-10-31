// Public-port traffic and independent payload scoreboard. Resets are outside
// measurements; every write, response, publication and release is charged.
#include "verilated.h"
#ifdef HANDOFF_T
#include "Vtransaction6k.h"
using Device=Vtransaction6k;
#else
#include "Vblock_v1_s16k.h"
using Device=Vblock_v1_s16k;
#endif
#include <array>
#include <cstdint>
#include <iostream>
#include <stdexcept>
#include <string>
using Word=std::array<uint32_t,4>;
static Device d;
static unsigned checks=0,scenario=0;
static void ck(bool good,const char*why){++checks;if(!good)throw std::runtime_error(why);}
static Word pattern(unsigned batch,unsigned index){return {0x71ac0000u+batch,index,index^0xa5a55a5au,~index+batch};}
static void edge(){d.clk=1;d.eval();d.clk=0;d.eval();}
struct Count {
 uint64_t cycles=0,accepted_write=0,accepted_read=0,retired=0,control=0,overlap=0,storage_access=0;
 uint64_t output_backpressure=0,producer_gap=0,transfer=0,dependency=0,drain=0;
 void print()const{
  ck(cycles==output_backpressure+producer_gap+transfer+dependency+drain,"exclusive cycle accounting");
  std::cout<<"{\"cycles\":"<<cycles<<",\"accepted_writes\":"<<accepted_write<<",\"accepted_reads\":"<<accepted_read
   <<",\"retired_data_or_ack_beats\":"<<retired<<",\"control_transfers\":"<<control<<",\"overlap_edges\":"<<overlap
   <<",\"storage_access_cycles\":"<<storage_access<<",\"cycle_attribution\":{\"output_backpressure\":"<<output_backpressure
   <<",\"producer_gap\":"<<producer_gap<<",\"transfer\":"<<transfer<<",\"dependency_wait\":"<<dependency<<",\"drain\":"<<drain<<"}}";
 }
};
static uint64_t serial=0;
static bool offer(){return scenario!=2||serial%7<4;}
static bool take(){return scenario!=3||serial%5!=2;}
static void count(Count&c,bool wr,bool rd,bool retire,bool control,bool blocked,bool gap,bool draining,bool access){
 ++c.cycles;c.accepted_write+=wr;c.accepted_read+=rd;c.retired+=retire;c.control+=control;c.overlap+=((wr||rd)&&retire);c.storage_access+=access;
 if(blocked)++c.output_backpressure;else if(gap)++c.producer_gap;else if(wr||rd||retire||control)++c.transfer;else if(draining)++c.drain;else ++c.dependency;
 ++serial;edge();
}
static void reset(){
 d.clk=0;d.reset=1;
#ifdef HANDOFF_T
 d.begin_valid=0;d.write_valid=0;d.commit_valid=0;d.revoke_valid=0;d.read_take=0;d.release_valid=0;
#else
 d.req=0;d.take=0;
#endif
 d.eval();edge();d.reset=0;d.eval();serial=0;
}
#ifdef HANDOFF_T
static void run(unsigned words,unsigned batches,Count&load,Count&read,Count&control){
 for(unsigned batch=0;batch<batches;++batch){
  d.begin_words=words;d.begin_owner=1;d.begin_generation=batch+1;d.begin_valid=1;d.eval();ck(d.begin_ready,"T begin refused");
  count(control,0,0,0,1,0,0,0,0);d.begin_valid=0;
  unsigned sent=0,got=0,watchdog=0;
  while(sent<words){
   ck(++watchdog<100000,"T write timeout");bool available=offer();d.write_valid=available;d.write_index=sent;
   Word w=pattern(batch,sent);for(unsigned j=0;j<4;++j)d.write_data[j]=w[j];d.eval();ck(!d.read_valid,"T provisional data visible");
   bool accepted=d.write_valid&&d.write_ready;bool gap=!available&&d.write_ready;
   count(load,accepted,0,0,0,0,gap,0,accepted);sent+=accepted;
  }
  d.write_valid=0;d.commit_valid=1;d.eval();ck(d.sealed&&d.commit_ready,"T commit before complete");
  count(control,0,0,0,1,0,0,0,0);d.commit_valid=0;
  bool held=false;Word held_word{};unsigned held_index=0;watchdog=0;
  while(got<words){
   ck(++watchdog<100000,"T read timeout");d.read_take=take();d.eval();
   Word w{};for(unsigned j=0;j<4;++j)w[j]=d.read_data[j];
   if(held)ck(d.read_valid&&w==held_word&&d.read_index==held_index,"T held data changed");
   if(d.read_valid)ck(w==pattern(batch,got)&&d.read_index==got&&bool(d.read_last)==(got+1==words),"T ordered payload mismatch");
   bool pop=d.read_valid&&d.read_take;bool blocked=d.read_valid&&!d.read_take;
   bool access=d.debug_state==3;
#ifdef REVISED_ST
   access=access||(d.debug_state==4&&pop&&!d.read_last);
#endif
   held=blocked;held_word=w;held_index=d.read_index;
   count(read,0,pop,pop,0,blocked,0,!d.read_valid,access);got+=pop;
  }
  d.read_take=0;d.release_valid=1;d.eval();ck(d.release_ready&&!d.protocol_error,"T release/error");
  count(control,0,0,0,1,0,0,0,0);d.release_valid=0;d.eval();ck(!d.busy,"T lease leaked");
 }
}
#else
static void phase(unsigned words,unsigned batches,bool writing,Count&c){
 unsigned sent=0,received=0,watchdog=0,total=words*batches;bool pending=false;Word expected{};bool held=false;Word held_word{};
 while(received<total){
  ck(++watchdog<100000,"S transfer timeout");bool available=sent<total&&offer();d.req=available;d.wr=writing;d.addr=sent%words;d.take=take();
  // Repeating batches use the same payload, so an entire write pass can be
  // followed by an independently checked read pass without host rereads.
  Word input=pattern(0,sent%words);for(unsigned j=0;j<4;++j)d.din[j]=input[j];d.eval();
  ck(bool(d.valid)==pending,"S response count mismatch");Word value{};for(unsigned j=0;j<4;++j)value[j]=d.dout[j];
  if(d.valid)ck(value==expected,"S payload or write ack mismatch");
  if(held)ck(d.valid&&value==held_word,"S held response changed");
  bool pop=d.valid&&d.take,push=d.req&&d.ready;bool blocked=d.valid&&!d.take;
  held=blocked;held_word=value;
  if(pop){pending=false;++received;}
  if(push){ck(!pending,"S multiple outstanding");pending=true;expected=writing?Word{}:pattern(0,sent%words);++sent;}
  bool gap=sent<total&&!available&&d.ready;
  count(c,push&&writing,push&&!writing,pop,0,blocked,gap,!available&&sent==total,push);
 }
 d.req=0;d.take=0;d.eval();ck(!d.valid,"S response not drained");
}
static void run(unsigned words,unsigned batches,Count&load,Count&read,Count&control){(void)control;phase(words,batches,true,load);phase(words,batches,false,read);}
#endif
int main(int argc,char**argv){try{
 Verilated::commandArgs(argc,argv);std::cout<<"{\"passed\":true,\"cases\":[";bool comma=false;
 const char*names[]={"continuous","repeated_batches","producer_gap","output_backpressure"};
 for(unsigned n:{1u,17u,384u
#ifndef HANDOFF_T
 ,1024u
#endif
 })for(scenario=0;scenario<4;++scenario){
  reset();unsigned batches=scenario==1?4:1;Count load,read,control;run(n,batches,load,read,control);
  ck(load.accepted_write==uint64_t(n)*batches&&read.accepted_read==uint64_t(n)*batches,"work count");
  ck(load.storage_access==uint64_t(n)*batches&&read.storage_access==uint64_t(n)*batches,"one actual storage access per payload word");
  if(comma)std::cout<<",";comma=true;
  std::cout<<"{\"words_per_batch\":"<<n<<",\"batches\":"<<batches<<",\"scenario\":\""<<names[scenario]<<"\",\"total_cycles\":"<<load.cycles+read.cycles+control.cycles
   <<",\"effective_payload_bytes_each_direction\":"<<uint64_t(n)*batches*16<<",\"write\":";load.print();std::cout<<",\"read\":";read.print();std::cout<<",\"control\":";control.print();std::cout<<"}";
 }
 std::cout<<"],\"checks\":"<<checks<<"}\n";return 0;
}catch(const std::exception&e){std::cerr<<e.what()<<"\n";return 1;}}
