// Measure the macro command boundary, separately from function-lane II=1.
// Reuse the exact existing handshake/backpressure driver; RTL is unchanged.
#define main vector_scoreboard_main
#include "test_vector_macro.cpp"
#undef main
#include <string>
int main(int argc,char**argv){try{
 Verilated::commandArgs(argc,argv);dut.cmd_valid=0;dut.reset=1;tick();tick();dut.reset=0;tick();
 struct Sample{std::string name;unsigned op,index,n,k,latency;};std::vector<Sample>samples;
 auto measure=[&](const char*name,unsigned op,unsigned index,U data,unsigned n=0,unsigned k=0){
  auto r=cmd(op,index,data);samples.push_back({name,op,index,n,k,r.latency});return r.latency;
 };
 Row a{},b{};for(unsigned j=0;j<8;++j){a[j]=-int32_t((j+1)*65536);b[j]=32768;}
 measure("load_a_half",0,0,pack(a,0),4);measure("load_a_half",0,1,pack(a,1),4);load(1,b);
 for(unsigned op=0;op<10;++op){auto t=measure("element",2,0,U(op)|(U(op==7?3:0)<<4)|(U(8)<<11)|(U(2)<<16),8);need(t==5,"element latency changed");}
 auto stat=measure("statistics_start_final",3,0,1|2|(8<<2),8);need(stat==4,"statistics latency changed");
 measure("read_statistics",4,0,0);
 for(unsigned fn=0;fn<5;++fn){auto t=measure("function_8_elements",5,0,fn,8);need(t==7,"function macro latency changed");}
 measure("reciprocal",6,0,65536);measure("rsqrt",6,1,65536);
 for(unsigned n:{1U,7U,8U,9U,64U,128U,256U}){
  std::vector<int32_t>x(n);for(unsigned j=0;j<n;++j)x[j]=(int(j%9)-4)*4096;replay(x);
  for(unsigned kind=0;kind<3;++kind){measure(kind==0?"RMSNorm":kind==1?"L2Norm":"Softmax",8,kind,U(n)|(U(kind==2?0:4295)<<9),n);read(n);}
 }
 cmd(13,0,0);std::vector<int32_t>x(40);for(unsigned j=0;j<40;++j)x[j]=int(j%7);replay(x);
 for(unsigned p=0;p<5;++p){U ids=0;for(unsigned j=0;j<8;++j)ids|=U(60000-(8*p+j)*13)<<(16*j);cmd(10,p,ids);}
 auto t=measure("TopK",11,0,40|(8<<6),40,8);need(t==328,"TopK latency changed");
 std::cout<<"{\"passed\":true,\"scope\":\"Acceptance edge to first held response; input load, output read, response consumption and stalls are additional\",\"samples\":[";
 for(unsigned j=0;j<samples.size();++j){const auto&s=samples[j];std::cout<<(j?",":"")<<"{\"name\":\""<<s.name<<"\",\"op\":"<<s.op<<",\"index\":"<<s.index<<",\"n\":"<<s.n<<",\"k\":"<<s.k<<",\"cycles\":"<<s.latency<<"}";}
 std::cout<<"],\"checks\":"<<checks<<",\"simulation_cycles\":"<<cycles<<"}\n";return 0;
}catch(const std::exception&e){std::cerr<<e.what()<<"\n";return 1;}}
