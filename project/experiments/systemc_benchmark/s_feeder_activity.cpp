// Exact packet/ownership checks on the accepted P-S feeder.
// Reuse the ordinary-port fixture verbatim; its command() is initialization only.
#define S_FEEDER
#define main ordinary_s_activity_main
#include "s_activity.cpp"
#undef main
#include <set>

struct PacketBench:SBench {
 uint64_t a_count=0,b_count=0;
 uint64_t load(unsigned rows,unsigned tiles,bool aw,bool bw,bool reuse,bool stalled) {
  auto& d=dut;const auto begin=cycles;
  d.load_bank=1;d.load_rows=rows;d.load_tiles=tiles;
  d.load_a_wide=aw;d.load_b_wide=bw;d.load_reuse_b=reuse;
  d.load_a_base=0;d.load_b_base=128;d.load_valid=1;d.eval();
  if(!d.load_ready)throw std::runtime_error("feeder not ready at serialized boundary");
  tick();d.load_valid=0;d.eval();
  std::set<unsigned> seen_a,seen_b;
  bool held_a=false,held_b=false;std::array<uint32_t,4> old_a{};
  std::array<uint32_t,16> old_b{};unsigned old_am=0,old_bm=0;
  unsigned guard=0;
  while(!d.done_valid) {
   if(++guard>1000)throw std::runtime_error("feeder completion timeout");
   const auto offset=cycles-begin;
   d.a_ready=!stalled||offset%7>=3;d.b_ready=!stalled||offset%11>=4;d.eval();
   if(d.req_ready)throw std::runtime_error("ordinary port enabled during feeder ownership");
   const unsigned am=(d.a_bank<<8)|(d.a_wide<<7)|(d.a_tile<<3)|d.a_row;
   const unsigned bm=(d.b_bank<<8)|(d.b_wide<<7)|(d.b_tile<<1)|d.b_half;
   if(held_a) {
    if(!d.a_valid||am!=old_am)throw std::runtime_error("stalled A metadata changed");
    for(unsigned j=0;j<4;++j)if(d.a_data[j]!=old_a[j])throw std::runtime_error("stalled A data changed");
   }
   if(held_b) {
    if(!d.b_valid||bm!=old_bm)throw std::runtime_error("stalled B metadata changed");
    for(unsigned j=0;j<16;++j)if(d.b_data[j]!=old_b[j])throw std::runtime_error("stalled B data changed");
   }
   if(d.a_valid) {
    if(d.a_bank!=1||d.a_wide!=aw||d.a_row>=rows||d.a_tile>=tiles)
     throw std::runtime_error("invalid A packet metadata");
    const unsigned address=d.a_tile*((rows+3)/4)*4+d.a_row;
    for(unsigned j=0;j<4;++j)if(d.a_data[j]!=memory[address][j])
     throw std::runtime_error("A packet differs from independent SRAM address/word oracle");
    if(d.a_ready){if(!seen_a.insert(d.a_tile*8+d.a_row).second)throw std::runtime_error("duplicate A packet");++a_count;}
   }
   if(d.b_valid) {
    if(reuse||d.b_bank!=1||d.b_wide!=bw||d.b_tile>=tiles||d.b_half>unsigned(bw))
     throw std::runtime_error("invalid B packet metadata");
    const unsigned address=128+d.b_tile*(bw?8:4)+d.b_half*4;
    for(unsigned j=0;j<16;++j)if(d.b_data[j]!=memory[address+j/4][j%4])
     throw std::runtime_error("B packet differs from independent SRAM address/word oracle");
    if(d.b_ready){if(!seen_b.insert(d.b_tile*2+d.b_half).second)throw std::runtime_error("duplicate B packet");++b_count;}
   }
   held_a=d.a_valid&&!d.a_ready;held_b=d.b_valid&&!d.b_ready;old_am=am;old_bm=bm;
   for(unsigned j=0;j<4;++j)old_a[j]=d.a_data[j];
   for(unsigned j=0;j<16;++j)old_b[j]=d.b_data[j];
   tick();
  }
  if(held_a||held_b||seen_a.size()!=rows*tiles||seen_b.size()!=(reuse?0:tiles*(bw?2:1)))
   throw std::runtime_error("done before every expected A/B packet retired");
  d.a_ready=1;d.b_ready=1;
  // Completion belongs to this operation until its consumer takes it.
  for(unsigned j=0;j<3;++j){
   if(!d.done_valid||d.done_error||d.req_ready||d.load_ready||d.a_valid||d.b_valid)
    throw std::runtime_error("done/phase ownership changed under completion backpressure");
   tick();
  }
  d.done_take=1;tick();d.done_take=0;d.eval();
  if(d.done_valid||!d.load_ready||!d.req_ready)throw std::runtime_error("completion did not release feeder phase");
  return cycles-begin;
 }
};
int main(int argc,char**argv) {
 Verilated::commandArgs(argc,argv);Verilated::traceEverOn(true);
 try {
  if(argc<9)throw std::runtime_error("usage: operands.tsv output.vcd active|idle rows tiles aw bw reuse [stalled]");
  std::ifstream file(argv[1]);std::vector<std::pair<int,int>> operands;int a,b,power;
  while(file>>a>>b>>power){
   if(a< -32768||a>32767||b< -32768||b>32767)throw std::runtime_error("not S16 captured operands");
   operands.emplace_back(a,b);
  }
  if(operands.empty())throw std::runtime_error("missing captured operands");
  const std::string mode=argv[3];const unsigned rows=std::stoul(argv[4]),tiles=std::stoul(argv[5]);
  const bool aw=std::stoul(argv[6]),bw=std::stoul(argv[7]),reuse=std::stoul(argv[8]);
  const bool stalled=argc>9&&std::stoul(argv[9]);
  if((mode!="active"&&mode!="idle")||!rows||rows>8||!tiles||tiles>4)
   throw std::runtime_error("invalid feeder case");
  PacketBench s;s.reset();
  for(unsigned i=0;i<1024;++i){
   Word w{};if(i)for(unsigned j=0;j<8;++j){
    auto x=operands[(i*8+j)%operands.size()];const int value=i<128?x.first:x.second;
    w[j/2]|=uint32_t(uint16_t(value))<<(16*(j%2));
   }
   s.command(true,i,w);
  }
  // Initialize both packet slots and weight holding registers before reuse-B cases.
  s.load(8,4,true,true,false,false);
  const auto period=s.load(rows,tiles,aw,bw,reuse,stalled);s.quiesce();
  const auto initial=s.memory;
  s.dut.trace(&s.trace,99);s.trace.open(argv[2]);s.tracing=true;
  const auto begin=s.cycles,start_ps=s.ps,a0=s.a_count,b0=s.b_count;
  constexpr unsigned repeats=32;
  if(mode=="active") {
   for(unsigned i=0;i<repeats;++i)if(s.load(rows,tiles,aw,bw,reuse,stalled)!=period)
    throw std::runtime_error("identical feeder jobs have different calibrated period");
   s.quiesce();
  }else for(uint64_t i=0;i<repeats*period+6*s.period;++i)s.tick();
  if(initial!=s.memory)throw std::runtime_error("read-only feeder activity changed SRAM contents");
  s.dut.eval();s.trace.dump(s.ps);s.trace.close();s.tracing=false;
  std::cout<<"FUNCTIONAL {\"timing\":{\"cycles\":"<<s.cycles-begin
   <<",\"window_ps\":"<<s.ps-start_ps<<",\"nominal_clock_hz\":300000000,\"passed\":true"
   <<",\"feeder_period_cycles_with_done_hold3\":"<<period
   <<",\"jobs\":"<<(mode=="active"?repeats:0)<<",\"A_packets\":"<<s.a_count-a0
   <<",\"B_packets\":"<<s.b_count-b0<<"},\"same_final_memory\":true"
   <<",\"rows\":"<<rows<<",\"tiles\":"<<tiles<<",\"wide_a\":"<<aw<<",\"wide_b\":"<<bw
   <<",\"reuse_b\":"<<reuse<<",\"backpressure_pattern\":"<<stalled
   <<",\"scope\":\"P S feeder exact packet/phase/held-response calibration only; M/LC and complete system energy separate\"}\n";
  return 0;
 }catch(const std::exception&e){std::cerr<<e.what()<<"\n";return 1;}
}
