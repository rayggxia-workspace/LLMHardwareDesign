// Public-port scheduling only. Reuse the independent integer references,
// never internal RTL signals or the regression's random-stall command driver.
#define main included_numeric_regression_main
#ifdef BENCH_RECURRENT
#include "test_recurrent_macro.cpp"
#else
#include "test_vector_macro.cpp"
#endif
#undef main
#include <map>
#include <string>

struct Command {
 unsigned op,index;U data,expected;unsigned request_bytes=0,response_bytes=0;
};
struct Phase {
 uint64_t cycles=0,accepted=0,responses=0,request_bytes=0,response_bytes=0;
 std::map<std::string,uint64_t> reasons;
};
static std::map<std::string,Phase> phases;
static unsigned profile=0;
static void restart() {
 dut.cmd_valid=0;dut.rsp_ready=0;dut.reset=1;tick();tick();dut.reset=0;tick();
 phases.clear();
}
static void stream(const std::vector<Command>&commands,const std::string&phase) {
 auto&result=phases[phase];unsigned sent=0,received=0,elapsed=0,gap=0;
 bool held=false;U held_data=0;bool held_error=false;
 while(received<commands.size()) {
  dut.clk=0;dut.cmd_valid=sent<commands.size()&&!gap;
  if(sent<commands.size()) {auto c=commands[sent];dut.cmd_op=c.op;dut.cmd_index=c.index;put(c.data);}
  dut.rsp_ready=profile!=2||elapsed%5>=2;dut.eval();
  if(held)need(dut.rsp_valid&&get()==held_data&&bool(dut.rsp_error)==held_error,"held benchmark response changed");
  bool accept=dut.cmd_valid&&dut.cmd_ready,consume=dut.rsp_valid&&dut.rsp_ready;
  std::string reason;
  if(dut.rsp_valid&&!dut.rsp_ready)reason="response_backpressure";
  else if(dut.cmd_valid&&!dut.cmd_ready)reason="command_blocked";
  else if(accept)reason="command_accepted";
  else if(gap)reason="producer_gap";
  else if(consume)reason="response_drain";
  else reason="operation_or_pipeline_wait";
  ++result.reasons[reason];++result.cycles;
  held=dut.rsp_valid&&!dut.rsp_ready;held_data=get();held_error=dut.rsp_error;
  if(consume) {
   need(received<sent,"response preceded accepted command");
   need(!dut.rsp_error&&get()==commands[received].expected,"public-port numeric/ack mismatch");
   result.response_bytes+=commands[received].response_bytes;++result.responses;++received;
  }
  if(gap)--gap;
  if(accept) {
   result.request_bytes+=commands[sent].request_bytes;++result.accepted;++sent;
   if(profile==1&&sent%4==0&&sent<commands.size())gap=3;
  }
  tick();need(++elapsed<200000,"benchmark command timeout");
 }
 need(sent==commands.size()&&!held,"incomplete benchmark transfer");
 dut.cmd_valid=0;dut.rsp_ready=0;dut.eval();
}
static void one(unsigned op,unsigned index,U data,const std::string&phase,U expected=0,unsigned request=0,unsigned response=0) {
 stream({{op,index,data,expected,request,response}},phase);
}
static void report(const std::string&workload,unsigned size) {
 static bool first=true;if(!first)std::cout<<",";first=false;
 std::cout<<"{\"workload\":\""<<workload<<"\",\"size\":"<<size<<",\"profile\":"<<profile;
#ifdef BENCH_RECURRENT
 std::cout<<",\"semantic_output_bytes\":32,\"active_state_bytes\":"<<32*size;
#else
 std::cout<<",\"semantic_output_bytes\":"<<4*size;
#endif
 std::cout<<",\"phases\":{";
 bool first_phase=true;uint64_t total=0;
 for(const auto&entry:phases) {
  if(!first_phase)std::cout<<",";first_phase=false;const auto&p=entry.second;total+=p.cycles;
  uint64_t sum=0;for(auto r:p.reasons)sum+=r.second;need(sum==p.cycles,"cycle attribution incomplete");
  need(p.accepted==p.responses,"ack count mismatch");
  std::cout<<"\""<<entry.first<<"\":{\"cycles\":"<<p.cycles<<",\"accepted_commands\":"<<p.accepted
   <<",\"responses\":"<<p.responses<<",\"request_data_valid_bytes\":"<<p.request_bytes
   <<",\"response_data_valid_bytes\":"<<p.response_bytes<<",\"request_container_bytes\":"<<16*p.accepted
   <<",\"response_container_bytes\":"<<16*p.responses<<",\"cycle_attribution\":{";
  bool f=true;for(auto r:p.reasons){if(!f)std::cout<<",";f=false;std::cout<<"\""<<r.first<<"\":"<<r.second;}std::cout<<"}}";
 }
 std::cout<<"},\"total_cycles\":"<<total<<"}";
}

#ifndef BENCH_RECURRENT
static U vector_word(const std::vector<int32_t>&a,unsigned begin) {
 U word=0;for(unsigned j=0;j<4&&begin+j<a.size();++j)word|=U(uint32_t(a[begin+j]))<<(32*j);return word;
}
static void vector_load(const std::vector<int32_t>&a,unsigned op,const std::string&phase) {
 std::vector<Command> commands;
 for(unsigned p=0;p<(a.size()+3)/4;++p)commands.push_back({op,p,vector_word(a,4*p),0,std::min(4u,unsigned(a.size())-4*p)*4,0});
 stream(commands,phase);
}
static void vector_read(const std::vector<int32_t>&expected,const std::string&phase) {
 std::vector<Command> commands;
 for(unsigned p=0;p<(expected.size()+3)/4;++p)commands.push_back({9,p,0,vector_word(expected,4*p),0,std::min(4u,unsigned(expected.size())-4*p)*4});
 stream(commands,phase);
}
static void vector_cases() {
 for(profile=0;profile<3;++profile) {
  // Same finite vector and numeric results, baseline schedules eight-element
  // function invocations; revised uses its actual finite replay operation.
  for(unsigned fn=0;fn<5;++fn)for(unsigned n:{17u,256u}) {
   restart();std::vector<int32_t>a(n),y(n);
   for(unsigned i=0;i<n;++i){a[i]=fn==0?-int32_t((i*997)%1048577):int32_t((i*997)%524289)-262144;y[i]=lut(fn,a[i]);}
#ifdef BASELINE_VR
   for(unsigned begin=0;begin<n;begin+=8) {
    std::vector<int32_t>part(8),expected(8);unsigned valid=std::min(8u,n-begin);
    for(unsigned j=0;j<8;++j){part[j]=j<valid?a[begin+j]:0;expected[j]=lut(fn,part[j]);}
    vector_load(part,0,"input");one(5,0,fn,"compute");vector_read(expected,"output");
   }
#else
   vector_load(a,7,"input");one(14,fn,n,"compute");vector_read(y,"output");
#endif
   report("function-"+std::to_string(fn),n);
  }
  // Shared local-composition protocol permits a direct old/new comparison.
  for(unsigned kind:{0u,2u})for(unsigned n:{17u,256u}) {
   restart();std::vector<int32_t>a(n),y(n);for(unsigned i=0;i<n;++i)a[i]=int32_t((i*997)%2097153)-1048576;
   U denominator=0,factor=0;
   if(kind==0) {for(auto v:a)denominator+=U(I(v)*v);factor=root_rne(U(n)<<96,denominator+U(4295)*n);for(unsigned i=0;i<n;++i)y[i]=sat(rne(I(a[i])*factor,32));}
   else {int32_t maximum=*std::max_element(a.begin(),a.end());for(unsigned i=0;i<n;++i){y[i]=lut(0,int32_t(std::max(int64_t(a[i])-maximum,int64_t(-1048576))));denominator+=uint32_t(y[i]);}factor=quotient_rne(U(1)<<48,denominator);for(auto&v:y)v=sat(rne(I(v)*factor,32));}
   vector_load(a,7,"input");one(8,kind,U(n)|(U(kind==0?4295:0)<<9),"compute");vector_read(y,"output");
   report(kind==0?"local-rmsnorm":"local-softmax",n);
  }
 }
}
#else
static void recurrent_cases() {
 for(profile=0;profile<3;++profile)for(unsigned mode=0;mode<2;++mode)for(unsigned n:{1u,17u,128u,256u}) {
  restart();owner=0x12345678;epoch=0;position=17;
  std::vector<Row>a(n),factor(n);std::vector<int16_t>k(n),q(n);
  for(unsigned r=0;r<n;++r){k[r]=int(r%13)*97-500;q[r]=int(r%17)*53-400;for(unsigned l=0;l<8;++l){a[r][l]=int(r*13+l*41)%6000-3000;factor[r][l]=0x60000000;}}
  Row x{},injection{},skip{},expected{};for(unsigned l=0;l<8;++l){x[l]=int(l)*13-40;injection[l]=int(l)*19-70;skip[l]=32768;}
  one(0,0,U(n)|(U(owner)<<9)|(U(epoch)<<41)|(U(position)<<73),"control",0,16);
  std::vector<Command> words;
  for(unsigned r=0;r<n;++r)for(unsigned p=0;p<2;++p)words.push_back({1,2*r+p,half(a[r],p),0,16,0});
  stream(words,"state_load");words.clear();
  for(unsigned op=2;op<=3;++op)for(unsigned begin=0;begin<n;begin+=8){U word=0;unsigned valid=std::min(8u,n-begin);for(unsigned j=0;j<valid;++j)word|=U(uint16_t((op==2?k:q)[begin+j]))<<(16*j);words.push_back({op,begin/8,word,0,valid*2,0});}
  for(unsigned p=0;p<2;++p){words.push_back({4,p,half(x,p),0,16,0});words.push_back({4,2+p,half(injection,p),0,16,0});}
  stream(words,"input");words.clear();
  one(5,0,U(0x70000000U)|(U(0x50000000U)<<32),"control",0,8);
  for(unsigned p=0;p<2;++p)one(5,1+p,half(skip,p),"control",0,16);
  if(mode){for(unsigned r=0;r<n;++r)for(unsigned p=0;p<2;++p)words.push_back({15,2*r+p,half(factor[r],p),0,16,0});stream(words,"coefficients");words.clear();}
  need(reference(a,k,q,x,injection,skip,0x70000000U,0x50000000U,factor,mode,expected),"benchmark reference overflow");
  one(6,0,U(mode)|(U(owner)<<2)|(U(epoch)<<34)|(U(position)<<66),"compute",0,16);
  for(unsigned p=0;p<2;++p)words.push_back({12,p,0,half(expected,p),0,16});stream(words,"output");words.clear();
  one(7,0,U(owner)|(U(epoch)<<32)|(U(position)<<64)|(U(position+1)<<96),"control",0,16);
  // Export is explicit, separately priced. It is not free validation or an
  // implicit normal per-token requirement when state remains resident.
  for(unsigned r=0;r<n;++r)for(unsigned p=0;p<2;++p)words.push_back({11,2*r+p,0,half(a[r],p),0,16});
  stream(words,"state_export");report(mode?"ssm-update":"gdn-update",n);
 }
}
#endif
int main(int argc,char**argv) {
 try {Verilated::commandArgs(argc,argv);std::cout<<"{\"cases\":[";
#ifdef BENCH_RECURRENT
 recurrent_cases();
#else
 vector_cases();
#endif
 std::cout<<"],\"passed\":true,\"checks\":"<<checks<<"}\n";return 0;
 }catch(const std::exception&e){std::cerr<<e.what()<<"\n";return 1;}
}
