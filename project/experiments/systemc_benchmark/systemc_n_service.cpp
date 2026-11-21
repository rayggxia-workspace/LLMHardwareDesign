// Clocked native-N service timing: paired statistics and shared exact group.
// Payload answers are checked separately against actual RTL/final gate netlist.
#include <systemc>
#include <algorithm>
#include <fstream>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <vector>

struct Descriptor {unsigned mode,pack,length;};
struct Model:sc_core::sc_module {
 std::vector<Descriptor> input;
 sc_core::sc_event request,complete;
 unsigned group_bits=0;uint64_t cycle=0;
 Model(sc_core::sc_module_name name,std::vector<Descriptor> values):sc_module(name),input(std::move(values)) {
  SC_THREAD(run);SC_THREAD(group);
 }
 void tick(unsigned count=1) {
  cycle+=count;const uint64_t target=(cycle*10000+2)/3;
  const uint64_t now=sc_core::sc_time_stamp().value();
  if(target<now)throw std::runtime_error("nonmonotone N clock");
  if(target>now)wait(sc_core::sc_time::from_value(target-now));
 }
 void group() {
  while(true) {
   wait(request);
   // Accept at the next edge, then shift one divisor bit or two root bits
   // per edge. The parent observes out_valid on its next edge.
   tick();tick(group_bits);complete.notify(sc_core::SC_ZERO_TIME);
  }
 }
 void calculate(unsigned bits) {
  group_bits=bits;request.notify(sc_core::SC_ZERO_TIME);wait(complete);tick();
 }
 void simple(unsigned stages=0) {tick();tick(stages);tick();}
 void run() {
  for(size_t id=0;id<input.size();++id) {
   const auto d=input[id];const auto start=cycle;
   simple(); // Begin: command acceptance and response consumption
   if(d.mode==0||d.mode==3) {
    simple(2); // Stats [x,0] or legacy [x]: both use one pair
    simple();simple(2); // Finalize softmax; Exp one lane
   } else {
    for(unsigned offset=0;offset<d.length;offset+=d.pack) {
     const unsigned n=std::min(d.pack,d.length-offset);
     simple(2*((n+1)/2)); // CALC and ACCUM for each two-lane group
    }
    tick(); // Finalize acceptance
    if(d.mode==1)calculate(64); // mean divider for RMS only
    calculate(32);calculate(64); // square root and factor divider
    tick(); // consume response
    simple(); // ReadFactor
   }
   std::cout<<"ROW "<<id<<' '<<cycle-start<<'\n';
  }
  std::cout<<"RESULT {\"services\":"<<input.size()<<",\"full_model_qualified\":false}\n";
  sc_core::sc_stop();
 }
};
int sc_main(int argc,char**argv) {
 try {
  if(argc!=2)throw std::runtime_error("usage: systemc-n-service descriptors.tsv");
  std::ifstream file(argv[1]);if(!file)throw std::runtime_error("missing descriptors");
  std::vector<Descriptor> values;std::string line;
  while(std::getline(file,line)) {
   if(line.empty()||line[0]=='#')continue;
   Descriptor d{};std::string extra;std::istringstream row(line);
   if(!(row>>d.mode>>d.pack>>d.length)||(row>>extra)||d.mode>3||d.pack<1||d.pack>8||!d.length||d.length>65535||((d.mode==0||d.mode==3)&&d.length!=1))
    throw std::runtime_error("unsupported N service descriptor");
   values.push_back(d);
  }
  if(values.empty())throw std::runtime_error("malformed or empty N descriptors");
  sc_core::sc_set_time_resolution(1,sc_core::SC_PS);
  Model model("N",values);sc_core::sc_start();return 0;
 }catch(const std::exception& error){std::cerr<<error.what()<<'\n';return 1;}
}
