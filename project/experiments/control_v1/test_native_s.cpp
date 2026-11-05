// Independent public-port oracle for the actual finite S storage and feeder.
// No hierarchy access, internal RAM preload, or expected power-up contents.
#include "Vblock_feed_s_macro.h"
#include "verilated.h"
#include <array>
#include <vector>
#include <random>
#include <iostream>
#include <cstdlib>
using Word=std::array<uint32_t,4>;
static unsigned checks=0,cycles=0;
static void need(bool b,const char*m){++checks;if(!b){std::cerr<<m<<" cycle "<<cycles<<"\n";std::exit(1);}}
template<class V>static Word word(const V&v){return {{v[0],v[1],v[2],v[3]}};}
struct A {Word data;unsigned row,tile,bank,wide;};
struct B {std::array<uint32_t,16> data;unsigned tile,bank,wide,half;};
struct Test {
 Vblock_feed_s_macro v;std::mt19937 rng{162};std::array<Word,1024> memory{};
 std::vector<A> aa;std::vector<B> bb;unsigned ai=0,bi=0,requests=0,responses=0,loads=0;
 bool pending=false;Word expected{};
 Test(){v.clk=0;v.reset=0;v.req=0;v.wr=0;v.addr=0;for(unsigned i=0;i<4;++i)v.din[i]=0;
  v.take=0;v.load_valid=0;v.load_bank=0;v.load_rows=0;v.load_tiles=0;v.load_a_wide=0;v.load_b_wide=0;
  v.load_reuse_b=0;v.load_a_base=0;v.load_b_base=0;v.done_take=0;v.a_ready=0;v.b_ready=0;}
 bool tick(){
  v.clk=0;v.eval();bool accept=v.req&&v.ready;
  if(!v.reset){
   if(v.valid){need(pending,"no unsolicited narrow response");need(word(v.dout)==expected,"narrow read/write acknowledgement payload");}
   if(v.valid&&v.take){pending=false;++responses;}
   if(accept){need(!pending,"finite single narrow response slot");expected=v.wr?word(v.din):memory[v.addr];
    if(v.wr)memory[v.addr]=word(v.din);pending=true;++requests;}
   if(v.a_valid){need(ai<aa.size(),"no extra A container");const auto&a=aa[ai];
    need(word(v.a_data)==a.data&&v.a_row==a.row&&v.a_tile==a.tile&&v.a_bank==a.bank&&v.a_wide==a.wide,"A payload and all metadata, including stalled cycles");if(v.a_ready)++ai;}
   if(v.b_valid){need(bi<bb.size(),"no extra B container");const auto&b=bb[bi];bool equal=true;
    for(unsigned i=0;i<16;++i)equal&=v.b_data[i]==b.data[i];
    need(equal&&v.b_tile==b.tile&&v.b_bank==b.bank&&v.b_wide==b.wide&&v.b_half==b.half,"B payload and all metadata, including stalled cycles");if(v.b_ready)++bi;}
   if(v.done_valid)need(ai==aa.size()&&bi==bb.size()&&!v.busy,"completion follows all actual feeder consumption");
  }
  v.clk=1;v.eval();++cycles;return accept;
 }
 void reset(){v.req=0;v.load_valid=0;v.take=0;v.done_take=0;v.reset=1;
  for(unsigned i=0;i<4;++i)tick();v.clk=0;v.eval();need(!v.ready&&!v.valid&&!v.load_ready&&!v.a_valid&&!v.b_valid&&!v.done_valid&&!v.busy,"reset flushes protocol state");
  pending=false;aa.clear();bb.clear();ai=bi=0;v.reset=0;tick();}
 void access(unsigned address,bool write,Word value={}){
  v.req=1;v.wr=write;v.addr=address;for(unsigned i=0;i<4;++i)v.din[i]=value[i];v.take=0;
  bool accepted=false;for(unsigned guard=0;guard<100&&!accepted;++guard)accepted=tick();need(accepted,"bounded narrow acceptance");v.req=0;
  for(unsigned i=0;i<3+(rng()%5);++i)tick();v.take=1;tick();v.take=0;need(!pending,"narrow response consumed exactly once");
 }
 void configure(unsigned rows,unsigned tiles,unsigned aw,unsigned bw,unsigned reuse,unsigned bank,unsigned abase,unsigned bbase){
  aa.clear();bb.clear();ai=bi=0;
  for(unsigned t=0;t<tiles;++t){
   for(unsigned r=0;r<rows;++r)aa.push_back({memory[abase+t*(rows>4?8:4)+r],r,t,bank,aw});
   if(!reuse)for(unsigned half=0;half<(bw?2u:1u);++half){B b{};b.tile=t;b.bank=bank;b.wide=bw;b.half=half;
    for(unsigned w=0;w<4;++w)for(unsigned k=0;k<4;++k)b.data[w*4+k]=memory[bbase+t*(bw?8:4)+half*4+w][k];bb.push_back(b);}
  }
 }
 void command(unsigned rows,unsigned tiles,unsigned aw,unsigned bw,unsigned reuse,unsigned bank,unsigned abase,unsigned bbase,bool legal=true){
  if(legal)configure(rows,tiles,aw,bw,reuse,bank,abase,bbase);else{aa.clear();bb.clear();ai=bi=0;}
  v.load_rows=rows;v.load_tiles=tiles;v.load_a_wide=aw;v.load_b_wide=bw;v.load_reuse_b=reuse;v.load_bank=bank;
  v.load_a_base=abase;v.load_b_base=bbase;v.load_valid=1;v.done_take=0;v.a_ready=0;v.b_ready=0;
  v.clk=0;v.eval();need(v.load_ready,"idle feeder accepts descriptor");tick();v.load_valid=0;++loads;
  bool completed=false;unsigned guard=0;
  // Concurrent narrow reads contend with the same real bank ports. A/B are
  // independently stalled; the first 19 cycles fill their finite buffers.
  for(;guard<20000;++guard){
   v.a_ready=guard>19&&rng()%4!=0;v.b_ready=guard>29&&rng()%3!=0;v.take=rng()%4!=0;
   if(!v.req&&rng()%3==0){v.req=1;v.wr=0;v.addr=rng()%1024;}
   v.clk=0;v.eval();bool done=v.done_valid;
   if(tick())v.req=0;
   if(done){completed=true;break;}
  }
  need(completed,"bounded feeder completion under independent backpressure and bank contention");
  need(bool(v.done_error)==!legal,"descriptor error status");
  v.req=0;v.take=1;for(unsigned i=0;i<7;++i){tick();need(v.done_valid&&bool(v.done_error)==!legal&&!v.load_ready,"done/status held until explicit acknowledgement");}
  v.done_take=1;tick();v.done_take=0;v.clk=0;v.eval();need(!v.done_valid&&v.load_ready,"completion release");
  need(ai==aa.size()&&bi==bb.size()&&!pending,"all finite outputs consumed");
 }
};
int main(int argc,char**argv){Verilated::commandArgs(argc,argv);Test t;t.reset();
 for(unsigned address=0;address<1024;++address){Word x{};for(auto&w:x)w=t.rng();t.access(address,true,x);}
 for(unsigned address=0;address<1024;++address)t.access((address*509)%1024,false);
 for(unsigned rows=1;rows<=8;++rows)for(unsigned tiles=1;tiles<=4;++tiles)
  for(unsigned aw=0;aw<2;++aw)for(unsigned bw=0;bw<2;++bw)for(unsigned reuse=0;reuse<2;++reuse)for(unsigned bank=0;bank<2;++bank)
   t.command(rows,tiles,aw,bw,reuse,bank,bank?984:16,bank?952:512);
 // Exact high-address endpoints, invalid dimensions/alignment/range, and
 // ignored B extent when reusing weights. Alignment remains mandatory.
 t.command(8,4,1,1,0,1,992,992);
 t.command(4,4,0,1,1,0,1008,1020);
 for(const auto&x:std::vector<std::array<unsigned,5>>{{{0,1,0,0,512}},{{9,1,0,0,512}},{{1,0,0,0,512}},{{1,5,0,0,512}},{{8,4,0,996,512}},{{8,4,0,0,996}},{{4,1,0,1,512}},{{4,1,1,0,513}}})
  t.command(x[0],x[1],0,1,x[2],0,x[3],x[4],false);
 // Abort with blocked feeder entries and pending narrow response; reset
 // flushes control while preserving the initialized standard-cell memory.
 t.configure(8,4,0,1,0,1,0,512);t.v.load_rows=8;t.v.load_tiles=4;t.v.load_a_base=0;t.v.load_b_base=512;
 t.v.load_reuse_b=0;t.v.load_bank=1;t.v.load_a_wide=0;t.v.load_b_wide=1;t.v.a_ready=0;t.v.b_ready=0;t.v.load_valid=1;
 t.tick();t.v.load_valid=0;for(unsigned i=0;i<40;++i)t.tick();need(t.v.busy,"abort exercised active finite feeder");t.reset();
 for(unsigned address=0;address<1024;++address)t.access(address,false);
 t.command(8,4,1,1,0,1,0,512);
 need(t.requests==t.responses&&t.loads==523,"all issued narrow requests and descriptors accounted");
 std::cout<<"{\"passed\":true,\"checks\":"<<checks<<",\"cycles\":"<<cycles<<",\"descriptors\":"<<t.loads<<",\"narrow_requests\":"<<t.requests<<",\"cpu_internal_ram_access\":0}\n";
}
