// Real leaf commands; numerical oracles are the pinned PR198 integer engines.
// Timing is this serialized driver boundary, not a measured product schedule.
#include "native_engines.hpp"
#include "Vblock_v2_e_compact.h"
#include "Vtransaction6k.h"
#include "t.hpp"
#include <iostream>
#include <random>

using namespace blocks;
static uint32_t random_word = 219;
static uint32_t rng() { random_word ^= random_word << 13; random_word ^= random_word >> 17; random_word ^= random_word << 5; return random_word; }

class Compact : public layer::Clocked<Vblock_v2_e_compact> {
public:
 Compact(){dut.reset=1;dut.in_valid=0;dut.out_ready=0;tick();tick();dut.reset=0;tick();}
 Reply execute(unsigned op, unsigned shift, const std::array<int16_t,8>& a,
               const std::array<int16_t,8>& b={},const std::array<int16_t,8>& c={}) {
  ECommand command; command.op=ECommand::Op(op);command.shift=shift;command.a=a;command.b=b;command.c=c;
  Reply expected;
  if(op==13) {
   expected.count=4;
   for(unsigned i=0;i<4;++i){
    const int32_t v=int32_t(uint16_t(a[2*i])|(uint32_t(uint16_t(a[2*i+1]))<<16));
    auto rounded=rne(Wide(v),shift);
    expected.lane[i]=int64_t(std::max(Wide(-32768),std::min(Wide(32767),rounded)));
    expected.saturated|=rounded < -32768 || rounded > 32767;
   }
  } else expected=EEngine{}.execute(command);
  unsigned count=op==3||op==6?3:(op==7||op==8||op>=10?1:2);
  for(unsigned i=0;i<count;++i){
   wait([&]{return dut.in_ready;});dut.in_op=op;dut.in_shift=shift;
   layer::pack16(dut.in_data,i==0?a:i==1?b:c);dut.in_valid=1;tick();dut.in_valid=0;
  }
  wait([&]{return dut.out_valid;});Reply actual=expected;actual.error=dut.out_error;actual.saturated=dut.out_saturated;
  for(unsigned i=0;i<expected.count;++i)actual.lane[i]=int16_t(dut.out_data[i/2]>>(16*(i%2)));
  layer::compare(actual,expected,"compact E");
  if(op==13)layer::require(dut.out_data[2]==0&&dut.out_data[3]==0,"E narrow upper lanes");
  dut.out_ready=1;tick();dut.out_ready=0;return actual;
 }
};

class Handoff : public layer::Clocked<Vtransaction6k> {
public:
 using Buffer=std::vector<std::array<uint32_t,4>>;
 Handoff(){dut.reset=1;dut.begin_valid=0;dut.write_valid=0;dut.commit_valid=0;dut.revoke_valid=0;dut.read_take=0;dut.release_valid=0;tick();tick();dut.reset=0;tick();}
 void boundaries(){
  for(unsigned n: {0u,385u,1023u}){
   dut.reset=1;tick();dut.reset=0;dut.begin_words=n;dut.eval();
   layer::require(!dut.begin_ready,"T accepted an invalid lease extent");
   dut.begin_valid=1;tick();dut.begin_valid=0;layer::require(!dut.busy&&dut.protocol_error,"T invalid begin diagnostic");
  }
  dut.reset=1;tick();dut.reset=0;tick();
 }
 Buffer transfer(const Buffer& input){
  const unsigned words=input.size();Buffer output;
  dut.begin_words=words;dut.begin_owner=2;dut.begin_generation=17;
  wait([&]{return dut.begin_ready;});dut.begin_valid=1;tick();dut.begin_valid=0;
  for(unsigned i=0;i<words;++i){dut.write_index=i;wait([&]{return dut.write_ready;});
   for(unsigned k=0;k<4;++k)dut.write_data[k]=input[i][k];
   dut.write_valid=1;tick();dut.write_valid=0;
  }
  wait([&]{return dut.commit_ready;});dut.commit_valid=1;tick();dut.commit_valid=0;
  for(unsigned i=0;i<words;++i){wait([&]{return dut.read_valid;});
   layer::require(dut.read_index==i&&bool(dut.read_last)==(i+1==words),"generated T tags");
   std::array<uint32_t,4> word{};for(unsigned k=0;k<4;++k)word[k]=dut.read_data[k];output.push_back(word);
   dut.read_take=1;tick();dut.read_take=0;
  }
  wait([&]{return dut.release_ready;});dut.release_valid=1;tick();dut.release_valid=0;
  layer::require(!dut.protocol_error&&!dut.busy,"generated T release");return output;
 }
 uint64_t batch(unsigned words,unsigned stall){
  TEngine ref;TCommand c;c.op=TCommand::Op::Begin;c.words=words;c.owner=2;c.generation=17;
  layer::require(!ref.execute(c).error,"T oracle begin");
  auto began=cycles;dut.begin_words=words;dut.begin_owner=2;dut.begin_generation=17;
  wait([&]{return dut.begin_ready;});dut.begin_valid=1;tick();dut.begin_valid=0;
  for(unsigned i=0;i<words;++i){
   c.op=TCommand::Op::Write;c.index=i;c.data={uint64_t(i)*1234567+89,~uint64_t(i)};
   layer::require(!ref.execute(c).error,"T oracle write");
   dut.write_index=i;wait([&]{return dut.write_ready;});
   dut.write_data[0]=uint32_t(c.data[0]);dut.write_data[1]=uint32_t(c.data[0]>>32);
   dut.write_data[2]=uint32_t(c.data[1]);dut.write_data[3]=uint32_t(c.data[1]>>32);
   dut.write_valid=1;tick();dut.write_valid=0;
  }
  c.op=TCommand::Op::Commit;layer::require(!ref.execute(c).error,"T oracle commit");
  wait([&]{return dut.commit_ready;});dut.commit_valid=1;tick();dut.commit_valid=0;
  for(unsigned i=0;i<words;++i){
   wait([&]{return dut.read_valid;});c.op=TCommand::Op::Peek;auto expected=ref.execute(c);
   for(unsigned j=0;j<stall;++j)tick();
   layer::require(dut.read_valid && dut.read_index==i && bool(dut.read_last)==(i+1==words),"T tags/order/backpressure");
   for(unsigned k=0;k<4;++k)layer::require(dut.read_data[k]==uint32_t(expected.bits[k/2]>>(32*(k%2))),"T payload");
   layer::require(!dut.begin_ready,"T lease overwritten before release");
   c.op=TCommand::Op::Take;layer::require(!ref.execute(c).error,"T oracle take");
   dut.read_take=1;tick();dut.read_take=0;
  }
  wait([&]{return dut.release_ready;});c.op=TCommand::Op::Release;layer::require(!ref.execute(c).error,"T oracle release");
  dut.release_valid=1;tick();dut.release_valid=0;layer::require(!dut.busy&&!dut.protocol_error,"T release");
  return cycles-began;
 }
};

// PR198's pass sequence, tiled to the accepted R256 rather than R1024.
// Each stored tile is read back and reloaded; global dot/update are retained.
class TiledRecurrent : public layer::Clocked<Vr_stream_local> {
public:
 TiledRecurrent(){dut.reset=1;dut.load_valid=0;dut.rd_valid=0;dut.rd_index=0;
  dut.rd_rsp_ready=0;dut.cmd_valid=0;dut.rsp_ready=0;tick();tick();dut.reset=0;tick();}
 void load(unsigned target,unsigned index,const std::array<uint32_t,4>& data){
  wait([&]{return dut.load_ready;});dut.load_target=target;dut.load_index=index;
  for(unsigned i=0;i<4;++i)dut.load_data[i]=data[i];
  dut.load_valid=1;tick();dut.load_valid=0;
 }
 std::array<int32_t,8> read(unsigned row){
  std::array<int32_t,8> result{};
  for(unsigned half=0;half<2;++half){
   dut.rd_index=row*2+half;dut.rd_bank=1;
   wait([&]{return dut.rd_ready;});dut.rd_valid=1;tick();dut.rd_valid=0;
   wait([&]{return dut.rd_rsp_valid;});
   for(unsigned i=0;i<4;++i)result[half*4+i]=int32_t(dut.rd_data[i]);
   dut.rd_rsp_ready=1;tick();dut.rd_rsp_ready=0;
  }
  return result;
 }
 std::array<int32_t,8> pass(unsigned op,unsigned rows=0,bool clear=false){
  wait([&]{return dut.cmd_ready;});dut.cmd_op=op;dut.cmd_rows=rows;
  dut.cmd_role=0;dut.cmd_mode=0;dut.cmd_clear=clear;dut.cmd_valid=1;tick();dut.cmd_valid=0;
  wait([&]{return dut.rsp_valid;});layer::require(!dut.rsp_error,"R256 tiled pass error");
  std::array<int32_t,8> result{};
  for(unsigned i=0;i<8;++i)result[i]=int32_t(dut.rsp_data[i*2]);
  dut.rsp_ready=1;tick();dut.rsp_ready=0;return result;
 }
 using State=std::vector<std::array<int32_t,8>>;
 void state(unsigned bank,const State& state){
  for(unsigned row=0;row<state.size();++row)for(unsigned half=0;half<2;++half){
   std::array<uint32_t,4> data{};for(unsigned i=0;i<4;++i)data[i]=uint32_t(state[row][half*4+i]);
   load(bank,row*2+half,data);
  }
 }
 void coefficients(unsigned target,const std::vector<int16_t>& values){
  for(unsigned i=0;i<values.size();i+=8){
   std::array<uint32_t,4> data{};
   for(unsigned j=0;j<8&&i+j<values.size();++j)data[j/2]|=uint32_t(uint16_t(values[i+j]))<<(16*(j%2));
   load(target,i/8,data);
  }
 }
 State predict(const State& old,const std::vector<int16_t>& key,uint32_t decay,bool first){
  state(0,old);coefficients(2,key);load(5,0,{decay,0,0,0});
  pass(0,old.size());pass(1,old.size(),first);
  State result;for(unsigned row=0;row<old.size();++row)result.push_back(read(row));return result;
 }
 void error(const std::array<int32_t,8>& x,uint32_t beta){
  for(unsigned half=0;half<2;++half){std::array<uint32_t,4> data{};
   for(unsigned i=0;i<4;++i)data[i]=uint32_t(x[half*4+i]);
   load(4,half,data);}
  load(5,0,{0,beta,0,0});pass(4);
 }
 State update(const State& decayed,const std::vector<int16_t>& key,const std::vector<int16_t>& query,bool first){
  state(1,decayed);coefficients(2,key);coefficients(3,query);
  pass(2,decayed.size());pass(3,decayed.size(),first);
  State result;for(unsigned row=0;row<decayed.size();++row)result.push_back(read(row));return result;
 }
};

#ifdef GENERATED_PLAN
#include "generated_plan.hpp"
#endif

int main(int argc,char**argv){
 Verilated::commandArgs(argc,argv);
 try {
  layer::Activation g;Compact e;
  for(unsigned fn=0;fn<4;++fn)for(unsigned gated=0;gated<2;++gated){
   uint64_t duration=0;
   for(unsigned trial=0;trial<97;++trial){GCommand c;c.function=GCommand::Function(fn);c.gated=gated;
    for(unsigned i=0;i<2;++i){c.x[i]=int16_t(rng());c.gate[i]=int16_t(rng());}
    auto start=g.cycles;g.execute(c);auto ticks=g.cycles-start;
    layer::require(trial==0||ticks==duration,"G nonconstant profile");duration=ticks;}
   std::cout<<"LEAF kind=G function="<<fn<<" gated="<<gated<<" ticks="<<duration<<"\n";
  }
  for(unsigned op: {0u,1u,2u,3u,4u,5u,6u,7u,8u,9u,10u,11u,13u})for(unsigned shift=0;shift<=31;++shift){
   uint64_t duration=0;
   for(unsigned trial=0;trial<37;++trial){std::array<int16_t,8>a{},b{},c{};
    for(unsigned i=0;i<8;++i){a[i]=int16_t(rng());b[i]=int16_t(rng());c[i]=int16_t(rng());}
    auto start=e.cycles;e.execute(op,shift,a,b,c);auto ticks=e.cycles-start;
    layer::require(trial==0||ticks==duration,"E nonconstant profile");duration=ticks;}
   std::cout<<"LEAF kind=E op="<<op<<" shift="<<shift<<" ticks="<<duration<<"\n";
  }
  layer::Matrix m;
  {MCommand c;c.op=MCommand::Op::Scale;auto start=m.cycles;m.execute(c);
   std::cout<<"LEAF kind=M_SCALE ticks="<<m.cycles-start<<"\n";}
  for(unsigned columns: {1u,2u,4u,8u})for(unsigned k=1;k<=32;++k){
   MCommand c;c.op=MCommand::Op::InvalidateAll;m.execute(c);
   for(unsigned tile=0;tile<(k+7)/8;++tile){
    MCommand a;a.op=MCommand::Op::LoadA;a.tile=tile;a.wide_a=true;
    for(unsigned i=0;i<8;++i)a.data[i/4]|=uint64_t(uint16_t(int16_t(rng()%257)-128))<<(16*(i%4));
    auto start=m.cycles;m.execute(a);layer::require(m.cycles-start==1,"M A profile");
    for(unsigned half=0;half<2;++half){MCommand b;b.op=MCommand::Op::LoadB;b.tile=tile;b.half=half;b.wide_b=true;
     for(unsigned i=0;i<32;++i)b.data[i/4]|=uint64_t(uint16_t(int16_t(rng()%257)-128))<<(16*(i%4));
     start=m.cycles;m.execute(b);layer::require(m.cycles-start==1,"M B profile");}
   }
   c=MCommand{};c.op=MCommand::Op::Execute;c.tiles=(k+7)/8;c.last_k=(k-1)%8+1;c.columns=columns;c.wide_a=c.wide_b=true;
   auto start=m.cycles;m.execute(c);auto ticks=m.cycles-start;
   c.clear=false;start=m.cycles;m.execute(c);layer::require(m.cycles-start==ticks,"M clear/accumulate time");
   std::cout<<"LEAF kind=M columns="<<columns<<" k="<<k<<" execute_ticks="<<ticks<<"\n";
   for(unsigned half=0;half<(columns+3)/4;++half)for(unsigned shift=0;shift<64;++shift){
    MCommand read;read.op=MCommand::Op::ReadFinal;read.half=half;read.width=16;read.shift=shift;
    start=m.cycles;m.execute(read);layer::require(m.cycles-start==5,"M ReadFinal timing differs");
    if(shift==5)std::cout<<"LEAF kind=M_READ ticks="<<m.cycles-start<<"\n";
   }
  }
  layer::Recurrent r;
  // rd_ready is address-qualified even while rd_valid is low. Set a legal
  // idle address before the PR198 driver's initial ready poll.
  r.dut.rd_index=0;
  for(unsigned rows=1;rows<=32;++rows){
   auto start=r.cycles;RCommand c;c.op=RCommand::Op::Open;c.length=rows;r.execute(c);
   for(unsigned row=0;row<rows;++row){c=RCommand{};c.op=RCommand::Op::StateRow;c.index=row;
    for(unsigned i=0;i<8;++i)c.values[i]=int32_t((row+1)*(i+1)*13)-500;
    r.execute(c);}
   for(unsigned row=0;row<rows;++row){c=RCommand{};c.op=RCommand::Op::Key;c.index=row;c.coefficients[0]=int16_t(row*7+1);r.execute(c);
    c.op=RCommand::Op::Query;c.coefficients[0]=int16_t(row*3+2);r.execute(c);}
   c=RCommand{};c.op=RCommand::Op::X;
   for(unsigned i=0;i<8;++i)c.values[i]=int32_t(i+1)*200;
   r.execute(c);
   c=RCommand{};c.op=RCommand::Op::Parameters;c.decay=0x70000000;c.beta=0x40000000;r.execute(c);
   c=RCommand{};c.op=RCommand::Op::Execute;c.mode=RCommand::Mode::GDN;r.execute(c);
   c.op=RCommand::Op::ReadOutput;r.execute(c);c.op=RCommand::Op::Commit;r.execute(c);
   for(unsigned row=0;row<rows;++row){c=RCommand{};c.op=RCommand::Op::ReadState;c.index=row;r.execute(c);}
   std::cout<<"LEAF kind=R_GDN rows="<<rows<<" ticks="<<r.cycles-start<<"\n";
  }
  TiledRecurrent tiled;
  std::vector<unsigned> sizes;for(unsigned n=1;n<=32;++n)sizes.push_back(n);
  for(unsigned n: {33u,64u,127u,128u,256u})sizes.push_back(n);
  for(unsigned total: sizes){
   REngine reference;RCommand c;c.op=RCommand::Op::Open;c.length=total;reference.execute(c);
   TiledRecurrent::State old;
   std::vector<int16_t> key,query;
   for(unsigned row=0;row<total;++row){
    c=RCommand{};c.op=RCommand::Op::StateRow;c.index=row;
    for(unsigned i=0;i<8;++i)c.values[i]=int32_t(rng()%1025)-512;
    old.push_back(c.values);reference.execute(c);
    key.push_back(int16_t(rng()%129)-64);query.push_back(int16_t(rng()%129)-64);
    c.op=RCommand::Op::Key;c.coefficients[0]=key.back();reference.execute(c);
    c.op=RCommand::Op::Query;c.coefficients[0]=query.back();reference.execute(c);
   }
   std::array<int32_t,8> x{};for(auto& v:x)v=int32_t(rng()%2049)-1024;
   c=RCommand{};c.op=RCommand::Op::X;c.values=x;reference.execute(c);
   c=RCommand{};c.op=RCommand::Op::Parameters;c.decay=0x80000000;c.beta=0x50000000;reference.execute(c);
   c=RCommand{};c.op=RCommand::Op::Execute;layer::require(!reference.execute(c).error,"R tiled oracle execute");
   c.op=RCommand::Op::ReadOutput;auto expected=reference.execute(c);
   c.op=RCommand::Op::Commit;reference.execute(c);
   auto clear_start=tiled.cycles;tiled.pass(7);
   std::cout<<"LEAF kind=R_BEGIN ticks="<<tiled.cycles-clear_start<<"\n";
   std::vector<TiledRecurrent::State> decayed;
   for(unsigned offset=0;offset<total;offset+=32){unsigned n=std::min(32u,total-offset);
    auto start=tiled.cycles;decayed.push_back(tiled.predict({old.begin()+offset,old.begin()+offset+n},
      {key.begin()+offset,key.begin()+offset+n},0x80000000,offset==0));
    std::cout<<"LEAF kind=R_PREDICT rows="<<n<<" ticks="<<tiled.cycles-start<<"\n";
   }
   auto began=tiled.cycles;tiled.error(x,0x50000000);
   std::cout<<"LEAF kind=R_ERROR ticks="<<tiled.cycles-began<<"\n";
   for(unsigned offset=0;offset<total;offset+=32){unsigned n=std::min(32u,total-offset);
    auto start=tiled.cycles;auto next=tiled.update(decayed[offset/32],{key.begin()+offset,key.begin()+offset+n},
      {query.begin()+offset,query.begin()+offset+n},offset==0);
    std::cout<<"LEAF kind=R_UPDATE rows="<<n<<" ticks="<<tiled.cycles-start<<"\n";
    for(unsigned row=0;row<n;++row){c=RCommand{};c.op=RCommand::Op::ReadState;c.index=offset+row;
     auto state=reference.execute(c);for(unsigned i=0;i<8;++i)layer::require(next[row][i]==state.lane[i],"R256 tiled next state differs");}
   }
   began=tiled.cycles;auto actual=tiled.pass(5);
   std::cout<<"LEAF kind=R_FINISH ticks="<<tiled.cycles-began<<"\n";
   for(unsigned i=0;i<8;++i)layer::require(actual[i]==expected.lane[i],"R256 tiled output differs");
  }
  layer::Normalizer norm;
  for(unsigned mode=0;mode<3;++mode){
   auto call=[&](NCommand c){auto start=norm.cycles;auto result=norm.execute(c);
    std::cout<<"LEAF kind=N mode="<<mode<<" op="<<unsigned(c.op)<<" count="<<c.count<<" ticks="<<norm.cycles-start<<"\n";return result;};
   NCommand c;c.op=NCommand::Op::Begin;c.mode=NCommand::Mode(mode);c.count=0;call(c);
   std::array<std::array<uint16_t,8>,8> data{},exp{};
   for(unsigned n=1;n<=8;++n){c=NCommand{};c.op=NCommand::Op::Stats;c.count=n;
    for(unsigned i=0;i<n;++i)data[n-1][i]=c.data[i]=int16_t(int(rng()%4097)-2048);
    call(c);}
   c=NCommand{};c.op=NCommand::Op::Finalize;c.count=0;call(c);
   if(mode==0){
    for(unsigned n=1;n<=8;++n){c=NCommand{};c.op=NCommand::Op::Exp;c.count=n;c.data=data[n-1];auto out=call(c);
     for(unsigned i=0;i<n;++i)exp[n-1][i]=int16_t(out.lane[i]);}
    c=NCommand{};c.op=NCommand::Op::FinishExp;c.count=0;call(c);
   }
   for(unsigned n=1;n<=8;++n){c=NCommand{};c.op=mode==0?NCommand::Op::SoftReplay:NCommand::Op::NormReplay;
    c.count=n;c.data=mode==0?exp[n-1]:data[n-1];c.gamma.fill(1024);call(c);}
  }
  Handoff t;t.boundaries();for(unsigned words: {1u,2u,8u,32u,384u})for(unsigned stall: {0u,3u})
   std::cout<<"LEAF kind=T words="<<words<<" stall="<<stall<<" ticks="<<t.batch(words,stall)<<"\n";
#ifdef GENERATED_PLAN
  replay_generated_plan();
#endif
  std::cout<<"NATIVE_LEAF_PROBE_PASS seed=219\n";
 }catch(const std::exception& error){std::cerr<<error.what()<<"\n";return 1;}
}
