// Command-level RoPE composition and statistics boundary tests on unchanged V.
// Reuse only transport/backpressure helpers; the oracle composes declared
// fixed-point commands, with supplied cos/sin parameters and stagewise RNE.
#define main vector_regression_main
#include "test_vector_macro.cpp"
#undef main

int main(int argc,char**argv){try{
 Verilated::commandArgs(argc,argv);dut.cmd_valid=0;dut.rsp_ready=0;
 dut.reset=1;tick();tick();dut.reset=0;tick();
 unsigned rope_cases=0;double max_rope_abs=0;
 auto point=[&](const Row&a,const Row&b,unsigned n,unsigned op,unsigned shift,bool paired){
  load(0,a);load(1,b);
  auto r=cmd(2,0,U(op)|(U(shift)<<4)|(U(n)<<11)|(U(2)<<16)|(U(paired)<<18));
  need(r.latency==5,"composed point latency");auto values=read(n);Row result{};
  std::copy(values.begin(),values.end(),result.begin());return result;
 };
 for(unsigned test=0;test<320;++test){
  unsigned n=2*(1+test%4);Row x{},cosine{},sine{};
  for(unsigned j=0;j<n;j+=2){
   double angle=test<4?double(test)*std::acos(-1.)/2:
       (double(int64_t(rng()%2000001)-1000000)/1000000)*std::acos(-1.);
   int32_t c=int32_t(std::llrint(std::cos(angle)*65536));
   int32_t s=int32_t(std::llrint(std::sin(angle)*65536));
   cosine[j]=cosine[j+1]=c;sine[j]=-s;sine[j+1]=s;
   x[j]=int32_t(rng()%524289)-262144;x[j+1]=int32_t(rng()%524289)-262144;
   if(test<4){x[j]=65536;x[j+1]=-131072;}
   if(test==4){x[j]=INT32_MIN;x[j+1]=INT32_MAX;}
  }
  Row direct=point(x,cosine,n,2,16,false);
  // Finite paired B access supplies x[j^1]; no general gather is implied.
  Row crossed=point(sine,x,n,2,16,true);
  Row actual=point(direct,crossed,n,0,0,false);
  for(unsigned j=0;j<n;++j){
   int32_t a=sat(rne(I(x[j])*cosine[j],16));
   int32_t b=sat(rne(I(x[j^1])*sine[j],16));
   need(actual[j]==sat(I(a)+b),"RoPE command composition mismatch");
   if(test!=4){
    double reference=(double(x[j])*cosine[j]+double(x[j^1])*sine[j])/4294967296.;
    max_rope_abs=std::max(max_rope_abs,std::abs(double(actual[j])/65536-reference));
   }
  }
  ++rope_cases;
 }
 // Fill the declared 65535-element statistics domain across commands.
 cmd(13,0,0);Row ones{};ones.fill(1);load(0,ones);unsigned total=0;
 while(total<65535){unsigned n=std::min(8U,65535-total);
  cmd(3,0,U(total==0)|(U(total+n==65535)<<1)|(U(n)<<2)|(U(total)<<16));total+=n;
 }
 U sum=cmd(4,0,0).data,square=cmd(4,1,0).data,meta=cmd(4,2,0).data;
 need(sum==65535&&square==65535&&uint16_t(meta>>96)==65535,"full statistics count/sum");
 need(uint16_t(meta>>32)==0&&uint16_t(meta>>80)==0&&bool((meta>>112)&1),"statistics stable tied IDs/final");
 unsigned norm_boundary_cases=0;
 const U max_epsilon=(U(1)<<64)-1;
 // Exercise the full sixteen-bit count and all sixty-four epsilon bits.
 replay(std::vector<int32_t>{1});
 for(unsigned kind=0;kind<2;++kind){
  cmd(8,4+kind,U(1)|(max_epsilon<<9));auto y=read(1);
  U f=root_rne(U(kind==0?65535:1)<<96,U(65535)+max_epsilon*(kind==0?65535:1));
  need(y[0]==sat(rne(I(f),32)),"full count/max epsilon denominator");++norm_boundary_cases;
 }
 std::vector<int32_t>edge(256,INT32_MIN);
 for(U eps:{U(0),U(1),max_epsilon})for(unsigned kind=0;kind<2;++kind){
  replay(edge);cmd(8,kind,U(256)|(eps<<9));auto y=read(256);
  U squares=U(256)*(U(1)<<62);
  U f=root_rne(U(kind==0?256:1)<<96,squares+eps*(kind==0?256:1));
  for(auto value:y)need(value==sat(rne(I(INT32_MIN)*f,32)),"local max magnitude/epsilon denominator");
  ++norm_boundary_cases;
 }
 cmd(3,0,U(1)<<2|(U(65535)<<16),true); // count would exceed its domain
 need(cmd(4,0,0).data==sum&&cmd(4,1,0).data==square&&cmd(4,2,0).data==meta,"overflow changed statistics");
 cmd(3,0,U(1)|(U(2)<<2)|(U(65535)<<16),true); // isolated ID-domain error on start
 need(cmd(4,0,0).data==sum&&cmd(4,1,0).data==square&&cmd(4,2,0).data==meta,"bad ID changed statistics");
 cmd(3,0,U(3)|(U(1)<<2)|(U(65535)<<16)); // maximum legal ID, final
 auto last=cmd(4,2,0).data;
 need(uint16_t(last>>32)==65535&&uint16_t(last>>80)==65535&&uint16_t(last>>96)==1&&bool((last>>112)&1),"maximum ID/final boundary");
 cmd(3,0,U(1)<<2,true);
 std::cout<<"{\"passed\":true,\"rope_cases\":"<<rope_cases
          <<",\"statistics_elements\":"<<total<<",\"norm_boundary_cases\":"<<norm_boundary_cases<<",\"rejected_boundary_cases\":3,\"checks\":"<<checks
          <<",\"cycles\":"<<cycles<<",\"max_rope_abs_against_quantized_parameters\":"<<max_rope_abs<<"}\n";
 return 0;
}catch(const std::exception&e){std::cerr<<e.what()<<"\n";return 1;}}
