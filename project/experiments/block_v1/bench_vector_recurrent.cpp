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
 std::cout<<",\"semantic_output_bytes\":"<<(workload=="conv4"?32*size:32)<<",\"active_state_bytes\":"<<(workload=="conv4"?0:32*size);
 if(workload=="conv4")std::cout<<",\"history_bytes\":96,\"coefficient_bytes\":64";
#else
 std::cout<<",\"semantic_output_bytes\":"<<(workload=="topk40-to8"?48:4*size);
 if(workload.rfind("global-",0)==0)std::cout<<",\"scheduled_external_workspace_bytes\":"<<4*size
  <<",\"scheduled_external_workspace_access_bytes\":"<<(workload=="global-softmax"?24:12)*size;
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
static void vector_extended_cases() {
 for(profile=0;profile<3;++profile) {
  for(unsigned kind=0;kind<3;++kind)for(unsigned n:{257u,769u,3072u}) {
   restart();std::vector<int32_t>a(n),y(n);for(unsigned i=0;i<n;++i)a[i]=int32_t((i*997)%2097153)-1048576;
   need(n*4<=16384,"global workspace exceeded S16K");
   one(13,0,0,"control");
   auto statistics=[&](const std::vector<int32_t>&values,unsigned context,const std::string&phase) {
    for(unsigned begin=0;begin<n;begin+=8) {
     unsigned valid=std::min(8u,n-begin);std::vector<int32_t>row(8);
     for(unsigned j=0;j<valid;++j)row[j]=values[begin+j];
     vector_load(row,0,phase);
     one(3,context,U(begin==0)|(U(begin+valid==n)<<1)|(U(valid)<<2)|(U(begin)<<16),phase);
    }
   };
   statistics(a,0,"global_statistics");
   if(kind<2) {
    U squares=0;for(auto v:a)squares+=U(I(v)*v);
    U factor=root_rne(U(kind==0?n:1)<<96,squares+U(4295)*(kind==0?n:1));
    for(unsigned i=0;i<n;++i)y[i]=sat(rne(I(a[i])*factor,32));
    for(unsigned begin=0;begin<n;begin+=256) {
     unsigned valid=std::min(256u,n-begin);
     vector_load(std::vector<int32_t>(a.begin()+begin,a.begin()+begin+valid),7,"replay_input");
     one(8,4+kind,U(valid)|(U(4295)<<9),"compute");
     vector_read(std::vector<int32_t>(y.begin()+begin,y.begin()+begin+valid),"output");
    }
   }else {
    int32_t maximum=*std::max_element(a.begin(),a.end());U total=0;
    for(unsigned i=0;i<n;++i){y[i]=lut(0,int32_t(std::max(int64_t(a[i])-maximum,int64_t(-1048576))));total+=uint32_t(y[i]);}
    for(unsigned begin=0;begin<n;begin+=256) {
     unsigned valid=std::min(256u,n-begin);
     vector_load(std::vector<int32_t>(a.begin()+begin,a.begin()+begin+valid),7,"max_subtract_input");
     one(14,8,valid,"exponentiation");
     vector_read(std::vector<int32_t>(y.begin()+begin,y.begin()+begin+valid),"exponentials_writeback");
    }
    statistics(y,1,"denominator_statistics");U factor=quotient_rne(U(1)<<48,total);
    for(unsigned i=0;i<n;++i)y[i]=sat(rne(I(y[i])*factor,32));
    for(unsigned begin=0;begin<n;begin+=256) {
     unsigned valid=std::min(256u,n-begin);std::vector<int32_t>exponentials(valid);
     for(unsigned j=0;j<valid;++j)exponentials[j]=lut(0,int32_t(std::max(int64_t(a[begin+j])-maximum,int64_t(-1048576))));
     vector_load(exponentials,7,"normalization_input");one(8,6,valid,"compute");
     vector_read(std::vector<int32_t>(y.begin()+begin,y.begin()+begin+valid),"output");
    }
   }
   report(kind==0?"global-rmsnorm":kind==1?"global-l2norm":"global-softmax",n);
  }
  // Full8-lane arithmetic and paired internal RoPE, finite40-to8 TopK.
  for(unsigned operation=0;operation<2;++operation) {
   restart();std::vector<int32_t>a(8),b(8),y(8);
   for(unsigned j=0;j<8;++j){a[j]=int(j)*1009-3000;b[j]=int(j)*137-400;}
   if(operation==0) {
    vector_load(a,0,"input");vector_load(b,1,"input");one(2,0,U(8)<<11|U(2)<<16,"compute");
    for(unsigned j=0;j<8;++j)y[j]=sat(I(a[j])+b[j]);
   }else {
    vector_load(a,7,"input");vector_load(b,1,"input");one(15,0,0,"compute");
    for(unsigned j=0;j<8;++j){I p=rne(I(a[j])*b[j&6],16),q=rne(I(a[j^1])*b[j|1],16);y[j]=sat(j&1?I(sat(p))+sat(q):I(sat(p))-sat(q));}
   }
   vector_read(y,"output");report(operation==0?"residual-add":"paired-rope",8);
  }
  restart();std::vector<int32_t>a(40);std::vector<unsigned>order(40);std::vector<uint16_t>ids(40);
  for(unsigned j=0;j<40;++j){a[j]=int(j%11)-5;ids[j]=60000-j*17;order[j]=j;}
  vector_load(a,7,"input");std::vector<Command>words;
  for(unsigned p=0;p<5;++p){U word=0;for(unsigned j=0;j<8;++j)word|=U(ids[8*p+j])<<(16*j);words.push_back({10,p,word,0,16,0});}
  stream(words,"ids");words.clear();one(11,0,40|(8<<6),"compute");
  std::stable_sort(order.begin(),order.end(),[&](unsigned l,unsigned r){return a[l]>a[r]||(a[l]==a[r]&&ids[l]<ids[r]);});
  for(unsigned j=0;j<8;++j)words.push_back({12,j,0,U(uint32_t(a[order[j]]))|(U(ids[order[j]])<<32),0,6});
  stream(words,"output");report("topk40-to8",40);
 }
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
static void recurrent_extended_cases() {
 for(profile=0;profile<3;++profile)for(unsigned tokens:{1u,17u,256u}) {
  restart();owner=0x12345678;epoch=0;position=17;
  one(0,0,U(1)|(U(owner)<<9)|(U(epoch)<<41)|(U(position)<<73),"control",0,16);
  std::array<Row,3>history;std::array<std::array<int16_t,8>,4>taps;
  for(unsigned j=0;j<3;++j)for(unsigned l=0;l<8;++l)history[j][l]=int(j*17+l*31)-300;
  std::vector<Command>words;
  for(unsigned j=0;j<3;++j)for(unsigned p=0;p<2;++p)words.push_back({9,2*j+p,half(history[j],p),0,16,0});
  stream(words,"history_load");words.clear();
  for(unsigned j=0;j<4;++j){U data=0;for(unsigned l=0;l<8;++l){taps[j][l]=int(j*997+l*41)-1300;data|=U(uint16_t(taps[j][l]))<<(16*l);}words.push_back({10,j,data,0,16,0});}
  stream(words,"coefficients");words.clear();
  for(unsigned token=0;token<tokens;++token) {
   Row x{},expected{};for(unsigned l=0;l<8;++l)x[l]=int(token*19+l*31)%2000-1000;
   for(unsigned l=0;l<8;++l){I sum=I(x[l])*taps[0][l];for(unsigned j=0;j<3;++j)sum+=I(history[j][l])*taps[j+1][l];expected[l]=int32_t(rne(sum,14));}
   for(unsigned p=0;p<2;++p)words.push_back({4,p,half(x,p),0,16,0});stream(words,"input");words.clear();
   one(6,0,U(2)|(U(owner)<<2)|(U(epoch)<<34)|(U(position)<<66),"compute",0,16);
   for(unsigned p=0;p<2;++p)words.push_back({12,p,0,half(expected,p),0,16});stream(words,"output");words.clear();
   one(7,0,U(owner)|(U(epoch)<<32)|(U(position)<<64)|(U(position+1)<<96),"control",0,16);
   ++epoch;++position;history={x,history[0],history[1]};
  }
  for(unsigned j=0;j<3;++j)for(unsigned p=0;p<2;++p)words.push_back({14,2*j+p,0,half(history[j],p),0,16});
  stream(words,"history_export");report("conv4",tokens);
 }
}
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
#ifdef EXTENDED_VR
 recurrent_extended_cases();
#else
 recurrent_cases();
#endif
#else
#ifdef EXTENDED_VR
 vector_extended_cases();
#else
 vector_cases();
#endif
#endif
 std::cout<<"],\"passed\":true,\"checks\":"<<checks<<"}\n";return 0;
 }catch(const std::exception&e){std::cerr<<e.what()<<"\n";return 1;}
}
