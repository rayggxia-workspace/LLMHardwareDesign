// The independent integer functions remain in the existing V regression.
// A generated header aliases its DUT class to the test-only two-leaf top.
#define main included_numeric_regression_main
#include "test_vector_macro.cpp"
#undef main
#include <map>
#include <string>

struct Counts {
 uint64_t cycles=0,s_reads=0,s_writes=0,s_acks=0,v_commands=0,v_responses=0;
 uint64_t stalled_s=0,stalled_v=0,simultaneous=0;
};
static std::map<std::string,Counts> measured;
static unsigned profile=0;
static U sget(){U v=0;for(int i=3;i>=0;--i)v=v<<32|dut.s_dout[i];return v;}
static void sput(U v){for(int i=0;i<4;++i){dut.s_din[i]=uint32_t(v);v>>=32;}}
static bool sink(unsigned elapsed){return profile!=2||elapsed%5>=2;}
static bool producer(unsigned elapsed){return profile!=1||elapsed%7<4;}
static void idle(){dut.cmd_valid=0;dut.rsp_ready=0;dut.s_req=0;dut.s_take=0;dut.eval();}
static void start(){
 idle();dut.reset=1;tick();tick();dut.reset=0;tick();measured.clear();
}
// All counters use preedge actual handshakes, once per shared S/V clock.
static void edge(const std::string&phase){
 dut.clk=0;dut.eval();auto&c=measured[phase];++c.cycles;
 if(dut.s_req&&dut.s_ready){if(dut.s_wr)++c.s_writes;else ++c.s_reads;}
 if(dut.s_valid&&dut.s_take)++c.s_acks;
 if(dut.cmd_valid&&dut.cmd_ready)++c.v_commands;
 if(dut.rsp_valid&&dut.rsp_ready){need(!dut.rsp_error,"V workspace error");++c.v_responses;}
 if(dut.s_req&&!dut.s_ready)++c.stalled_s;
 if(dut.cmd_valid&&!dut.cmd_ready)++c.stalled_v;
 if((dut.s_req&&dut.s_ready)&&(dut.cmd_valid&&dut.cmd_ready))++c.simultaneous;
 dut.clk=1;dut.eval();++cycles;
}
static U packed(const std::vector<int32_t>&a,unsigned base){
 U w=0;for(unsigned j=0;j<4&&base+j<a.size();++j)w|=U(uint32_t(a[base+j]))<<(32*j);return w;
}
static void initialize(const std::vector<int32_t>&a){
 unsigned words=(a.size()+3)/4,sent=0,done=0,e=0;
 while(done<words){
  dut.clk=0;dut.s_req=sent<words&&producer(e);dut.s_wr=1;dut.s_addr=sent;sput(packed(a,4*sent));
  dut.s_take=sink(e);dut.eval();
  bool push=dut.s_req&&dut.s_ready,pop=dut.s_valid&&dut.s_take;
  if(pop)need(sget()==0,"S write acknowledgement");
  edge("workspace_initialize");sent+=push;done+=pop;need(++e<20000,"S initialize timeout");
 }
 idle();need(sent==words,"S initialize incomplete");
}
static void vcommand(unsigned op,unsigned index,U data,const std::string&phase){
 unsigned e=0;bool sent=false,done=false;
 while(!done){
  dut.clk=0;dut.cmd_valid=!sent&&producer(e);dut.cmd_op=op;dut.cmd_index=index;put(data);dut.rsp_ready=sink(e);dut.eval();
  bool push=dut.cmd_valid&&dut.cmd_ready,pop=dut.rsp_valid&&dut.rsp_ready;
  if(pop)need(get()==0,"Unexpected V control payload");
  edge(phase);sent|=push;done|=pop;need(++e<10000,"V control timeout");
 }
 idle();need(sent,"V control response without request");
}
// At most one pending S response holds the operand. The driver copies that
// combinational value to V and consumes S only when V accepts it. No vector
// array or external payload queue sits between the two real macros.
static void from_s(unsigned begin,unsigned count,unsigned op,const std::string&phase){
 need(begin%4==0&&count>0&&count<=256,"S/V window");
 unsigned words=(count+3)/4,sent=0,taken=0,acked=0,e=0;
 bool held=false;U held_value=0;
 while(acked<words){
  dut.clk=0;dut.s_req=sent<words&&producer(e);dut.s_wr=0;dut.s_addr=begin/4+sent;
  dut.rsp_ready=sink(e);dut.cmd_op=op;dut.cmd_index=taken;dut.cmd_valid=0;dut.s_take=0;dut.eval();
  dut.cmd_valid=dut.s_valid;put(sget());dut.eval();dut.s_take=dut.cmd_ready;dut.eval();
  if(held)need(dut.s_valid&&sget()==held_value,"S operand changed while V blocked");
  bool push=dut.s_req&&dut.s_ready,take=dut.s_valid&&dut.s_take,ack=dut.rsp_valid&&dut.rsp_ready;
  need(bool(take)==bool(dut.cmd_valid&&dut.cmd_ready),"S/V bridge handshake");
  if(ack)need(get()==0,"V load acknowledgement");
  held=dut.s_valid&&!dut.s_take;held_value=sget();
  edge(phase);sent+=push;taken+=take;acked+=ack;need(++e<20000,"S/V load timeout");
 }
 idle();need(sent==words&&taken==words,"S/V load incomplete");
}
// V results either reach the external checker or overwrite the same finite
// S workspace. Expected data is a checker only, never a later operand source.
static void consume(unsigned begin,const std::vector<int32_t>&expected,bool write_s,const std::string&phase){
 unsigned words=(expected.size()+3)/4,sent=0,got=0,sacks=0,e=0;
 bool held=false;U held_value=0;
 while(got<words||(write_s&&sacks<words)){
  dut.clk=0;dut.cmd_valid=sent<words&&producer(e);dut.cmd_op=9;dut.cmd_index=sent;put(0);
  dut.s_take=write_s&&sink(e);dut.s_req=0;dut.eval();
  dut.rsp_ready=write_s?dut.s_ready:sink(e);dut.eval();
  if(write_s){dut.s_req=dut.rsp_valid;dut.s_wr=1;dut.s_addr=begin/4+got;sput(get());dut.eval();}
  if(held)need(dut.rsp_valid&&get()==held_value,"V result changed during S backpressure");
  bool push=dut.cmd_valid&&dut.cmd_ready,pop=dut.rsp_valid&&dut.rsp_ready;
  bool spush=dut.s_req&&dut.s_ready,sack=dut.s_valid&&dut.s_take;
  if(pop){need(got<words&&get()==packed(expected,4*got),"Global integer result mismatch");}
  if(write_s){need(spush==pop,"V/S bridge handshake");if(sack)need(sget()==0,"S EXP write acknowledgement");}
  held=dut.rsp_valid&&!dut.rsp_ready;held_value=get();
  edge(phase);sent+=push;got+=pop;sacks+=sack;need(++e<20000,"V/S consume timeout");
 }
 idle();need(sent==words,"V result requests incomplete");
}
static void statistics(unsigned n,unsigned context,const std::string&phase){
 for(unsigned begin=0;begin<n;begin+=8){
  unsigned valid=std::min(8u,n-begin);from_s(begin,valid,0,phase);
  vcommand(3,context,U(begin==0)|(U(begin+valid==n)<<1)|(U(valid)<<2)|(U(begin)<<16),phase);
 }
}
static void report(unsigned kind,unsigned n){
 static bool first=true;if(!first)std::cout<<",";first=false;
 std::cout<<"{\"operation\":"<<kind<<",\"size\":"<<n<<",\"profile\":"<<profile<<",\"phases\":{";
 bool f=true;Counts total;
 for(auto entry:measured){auto c=entry.second;if(!f)std::cout<<",";f=false;
  std::cout<<"\""<<entry.first<<"\":{\"cycles\":"<<c.cycles<<",\"s_reads\":"<<c.s_reads<<",\"s_writes\":"<<c.s_writes
   <<",\"s_acks\":"<<c.s_acks<<",\"v_commands\":"<<c.v_commands<<",\"v_responses\":"<<c.v_responses
   <<",\"s_stalled_request_cycles\":"<<c.stalled_s<<",\"v_stalled_command_cycles\":"<<c.stalled_v
   <<",\"simultaneous_s_v_requests\":"<<c.simultaneous<<"}";
  total.cycles+=c.cycles;total.s_reads+=c.s_reads;total.s_writes+=c.s_writes;total.s_acks+=c.s_acks;
  total.v_commands+=c.v_commands;total.v_responses+=c.v_responses;
 }
 need(total.s_reads+total.s_writes==total.s_acks&&total.v_commands==total.v_responses,"S/V lost transactions");
 unsigned words=(n+3)/4;
 need(total.s_reads==words*(kind==2?4:2)&&total.s_writes==words*(kind==2?2:1),"S/V traffic count");
 std::cout<<"},\"total_cycles\":"<<total.cycles<<",\"workspace_payload_bytes\":"<<16*words
  <<",\"s_payload_access_bytes\":"<<16*(total.s_reads+total.s_writes)<<"}";
}
int main(int argc,char**argv){
 try{Verilated::commandArgs(argc,argv);std::cout<<"{\"cases\":[";
 for(profile=0;profile<3;++profile)for(unsigned kind=0;kind<3;++kind)for(unsigned n:{257u,769u,3072u}){
  start();std::vector<int32_t>a(n),exp(n),y(n);for(unsigned i=0;i<n;++i)a[i]=int((i*997)%2097153)-1048576;
  need(4*((n+3)/4)<=4096,"S16KiB capacity");initialize(a);vcommand(13,0,0,"control");statistics(n,0,"global_statistics");
  if(kind<2){
   U squares=0;for(auto x:a)squares+=U(I(x)*x);
   U factor=root_rne(U(kind==0?n:1)<<96,squares+U(4295)*(kind==0?n:1));
   for(unsigned i=0;i<n;++i)y[i]=sat(rne(I(a[i])*factor,32));
  }else{
   auto maximum=*std::max_element(a.begin(),a.end());U sum=0;
   for(unsigned i=0;i<n;++i){exp[i]=lut(0,int32_t(std::max(int64_t(a[i])-maximum,int64_t(-1048576))));sum+=uint32_t(exp[i]);}
   for(unsigned begin=0;begin<n;begin+=256){
    unsigned valid=std::min(256u,n-begin);from_s(begin,valid,7,"exp_input");vcommand(14,8,valid,"exponentiation");
    consume(begin,std::vector<int32_t>(exp.begin()+begin,exp.begin()+begin+valid),true,"exp_workspace_writeback");
   }
   statistics(n,1,"denominator_statistics");U factor=quotient_rne(U(1)<<48,sum);
   for(unsigned i=0;i<n;++i)y[i]=sat(rne(I(exp[i])*factor,32));
  }
  for(unsigned begin=0;begin<n;begin+=256){
   unsigned valid=std::min(256u,n-begin);from_s(begin,valid,7,"normalization_input");
   vcommand(8,kind==2?6:4+kind,U(valid)|(U(kind==2?0:4295)<<9),"normalization");
   consume(begin,std::vector<int32_t>(y.begin()+begin,y.begin()+begin+valid),false,"output");
  }
  report(kind,n);
 }
 std::cout<<"],\"passed\":true,\"checks\":"<<checks<<"}\n";return 0;
 }catch(const std::exception&e){std::cerr<<e.what()<<"\n";return 1;}
}
