// Reuse the qualified public-port clock and assertions, not its old fixtures.
#define main legacy_activity_main
#include "n_activity.cpp"
#undef main

int main(int argc,char**argv) {
 Verilated::commandArgs(argc,argv);
 try {
  if(argc<2)throw std::runtime_error("usage: n-command-profile fixtures.tsv [Verilator options]");
  std::ifstream input(argv[1]);if(!input)throw std::runtime_error("missing fixtures");
  NBench bench;bench.reset();
  unsigned mode,pack,length,expected,id=0;
  while(input>>mode>>pack>>length>>expected) {
   if(mode>3||pack<1||pack>8||length<1||length>65535||((mode==0||mode==3)&&length!=1))
    throw std::runtime_error("unsupported N service descriptor");
   std::vector<int16_t> values;
   for(unsigned i=0;i<length;++i){int x;if(!(input>>x)||x< -32768||x>32767)throw std::runtime_error("invalid S16 payload");values.push_back(x);}
   const auto start=bench.cycles;
   // The old activity helper's timing key omits current mode. Each fixture
   // is one mode; do not compare RMS Finalize with L2 Finalize as one key.
   bench.commands.clear();
   const unsigned native_mode=mode==3?0:mode;
   bench.command(0,0,native_mode,{1,0,0,0});
   if(native_mode==0) {
    bench.command(1,mode==3?1:2,0,{uint16_t(values[0]),0,0,0});
    bench.command(2,0,0,{});
    bench.command(3,1,0,{uint16_t(values[0]),0,0,0},expected);
   } else {
    for(unsigned offset=0;offset<length;offset+=pack) {
     const unsigned count=std::min(pack,length-offset);
     std::array<uint32_t,4> word{};
     for(unsigned i=0;i<count;++i)word[i/2]|=uint32_t(uint16_t(values[offset+i]))<<(16*(i%2));
     bench.command(1,count,0,word);
    }
    bench.command(2,0,0,{});bench.command(11,0,0,{},expected);
   }
   std::cout<<"ROW "<<id++<<' '<<bench.cycles-start<<' '<<expected<<'\n';
  }
  if(!id)throw std::runtime_error("empty fixtures");
  std::cout<<"RESULT {\"services\":"<<id<<",\"exact_response_checks_passed\":true,\"full_model_qualified\":false}\n";
  return 0;
 }catch(const std::exception& error){std::cerr<<error.what()<<'\n';return 1;}
}
