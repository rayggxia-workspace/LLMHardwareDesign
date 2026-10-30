#include "Vblock_v1_r.h"
#include "verilated.h"
#include <array>
#include <vector>
#include <random>
#include <cstdint>
#include <iostream>
#include <stdexcept>
using I=__int128_t;using U=__uint128_t;using Row=std::array<int32_t,8>;
static Vblock_v1_r dut;static std::mt19937_64 rng(12120261027ULL);
static uint64_t checks=0,cycles=0;static uint32_t owner=0x12345678,epoch=0,position=0;
static void need(bool v,const char*s){++checks;if(!v)throw std::runtime_error(s);}
static void tick(){dut.clk=0;dut.eval();dut.clk=1;dut.eval();++cycles;}
static void put(U v){for(int i=0;i<4;++i){dut.cmd_data[i]=uint32_t(v);v>>=32;}}
static U get(){U v=0;for(int i=3;i>=0;--i)v=v<<32|dut.rsp_data[i];return v;}
struct Reply{U data;unsigned latency;};
static Reply cmd(unsigned op,unsigned index,U data,bool error=false){
 need(dut.cmd_ready,"input unavailable");dut.rsp_ready=0;dut.cmd_valid=1;dut.cmd_op=op;dut.cmd_index=index;put(data);tick();dut.cmd_valid=0;
 unsigned latency=0;while(!dut.rsp_valid){tick();need(++latency<5000,"timeout");}
 need(bool(dut.rsp_error)==error,"error flag mismatch");Reply result{get(),latency};
 for(unsigned j=0,n=rng()%4;j<n;++j){need(!dut.cmd_ready,"backpressure missing");dut.cmd_valid=1;dut.cmd_op=8;put(U(rng())<<64|rng());tick();need(dut.rsp_valid&&get()==result.data&&bool(dut.rsp_error)==error,"held response changed");}
 dut.cmd_valid=0;dut.rsp_ready=1;tick();dut.rsp_ready=0;need(dut.cmd_ready,"response release failed");return result;
}
static U half(const Row&r,int p){U v=0;for(int j=0;j<4;++j)v|=U(uint32_t(r[p*4+j]))<<(32*j);return v;}
static I rne(I v,unsigned s){I q=v>>s;U r=U(v)&((U(1)<<s)-1),h=U(1)<<(s-1);return q+(r>h||(r==h&&(q&1)));}
static bool fits(I v){return v>=INT32_MIN&&v<=INT32_MAX;}
static void open(unsigned n,uint32_t initial_epoch=0){epoch=initial_epoch;position=17;cmd(0,0,U(n)|(U(owner)<<9)|(U(epoch)<<41)|(U(position)<<73));}
static void state_load(const std::vector<Row>&a){for(unsigned j=0;j<a.size();++j)for(int p=0;p<2;++p)cmd(1,2*j+p,half(a[j],p));}
static void state_matches(const std::vector<Row>&a){for(unsigned j=0;j<a.size();++j)for(int p=0;p<2;++p){auto v=cmd(11,2*j+p,0).data;for(int l=0;l<4;++l)need(int32_t(v>>(32*l))==a[j][4*p+l],"active state mismatch");}}
static void load_vector(unsigned op,const std::vector<int16_t>&a){for(unsigned c=0;c<(a.size()+7)/8;++c){U v=0;for(unsigned j=0;j<8;++j)if(8*c+j<a.size())v|=U(uint16_t(a[8*c+j]))<<(16*j);cmd(op,c,v);}}
static void values(unsigned base,const Row&x){for(int p=0;p<2;++p)cmd(4,base+p,half(x,p));}
static void output_matches(const Row&x){for(int p=0;p<2;++p){auto v=cmd(12,p,0).data;for(int j=0;j<4;++j)need(int32_t(v>>(32*j))==x[p*4+j],"readout mismatch");}}
static Reply execute(unsigned mode,bool error=false){return cmd(6,0,U(mode)|(U(owner)<<2)|(U(epoch)<<34)|(U(position)<<66),error);}
static void commit(uint32_t next,bool error=false){auto r=cmd(7,0,U(owner)|(U(epoch)<<32)|(U(position)<<64)|(U(next)<<96),error);if(!error){++epoch;position=next;} (void)r;}
static Row random_row(int magnitude){Row a;for(auto&v:a)v=int(rng()%(2*magnitude+1))-magnitude;return a;}
static void reset(){dut.cmd_valid=0;dut.rsp_ready=0;dut.reset=1;tick();tick();dut.reset=0;tick();}
static bool reference(std::vector<Row>&a,const std::vector<int16_t>&k,const std::vector<int16_t>&q,const Row&x,const Row&inject,const Row&skip,uint32_t decay,uint32_t beta,const std::vector<Row>&factors,unsigned mode,Row&out){
 bool okay=true;std::vector<Row>b(a.size());std::array<I,8>dot{};Row error{};
 for(unsigned r=0;r<a.size();++r)for(int l=0;l<8;++l){I y=rne(I(a[r][l])*(mode?uint32_t(factors[r][l]):decay),31);okay&=fits(y);b[r][l]=int32_t(y);}
 if(mode==0){
  for(unsigned r=0;r<a.size();++r)for(int l=0;l<8;++l)dot[l]+=I(b[r][l])*k[r];
  for(int l=0;l<8;++l){I pred=rne(dot[l],14);okay&=fits(pred);I e=I(x[l])-int32_t(pred);okay&=fits(e);I y=rne(I(int32_t(e))*beta,31);okay&=fits(y);error[l]=int32_t(y);}
 }
 for(unsigned r=0;r<a.size();++r)for(int l=0;l<8;++l){I y=I(b[r][l])+rne(I(mode?inject[l]:error[l])*k[r],14);okay&=fits(y);b[r][l]=int32_t(y);}
 dot.fill(0);for(unsigned r=0;r<a.size();++r)for(int l=0;l<8;++l)dot[l]+=I(b[r][l])*q[r];
 for(int l=0;l<8;++l){I y=rne(dot[l],14);okay&=fits(y);int32_t z=int32_t(y);if(mode){y=I(z)+rne(I(x[l])*skip[l],16);okay&=fits(y);}out[l]=int32_t(y);}
 if(okay)a=b;return okay;
}
int main(int argc,char**argv){try{Verilated::commandArgs(argc,argv);reset();
 // Invalid/reset/incomplete context is never silently consumed.
 cmd(11,0,0,true);cmd(12,0,0,true);cmd(0,0,0,true);cmd(0,0,257,true);open(1);execute(0,true);commit(18,true);
 unsigned random_cases=0;
 for(unsigned mode=0;mode<2;++mode)for(unsigned trial=0;trial<120;++trial){
  unsigned n=trial==0?256:trial==1?128:1+rng()%37;
  std::vector<Row>a(n),factor(n);std::vector<int16_t>k(n),q(n);
  for(unsigned j=0;j<n;++j){a[j]=random_row(30000);k[j]=int(rng()%8193)-4096;q[j]=int(rng()%8193)-4096;for(auto&v:factor[j])v=int32_t(trial%4==0?0x80000000U:uint32_t(rng()&0x7fffffff));}
  auto original=a;Row x=random_row(20000),injection=random_row(10000),skip=random_row(65536),out{};
  uint32_t decay=trial%4==0?0x80000000U:uint32_t(rng()&0x7fffffff),beta=trial%4==1?0x80000000U:uint32_t(rng()&0x7fffffff);
  open(n);state_load(a);load_vector(2,k);load_vector(3,q);values(0,x);values(2,injection);cmd(5,0,U(decay)|(U(beta)<<32));
  cmd(5,1,half(skip,0));cmd(5,2,half(skip,1));
  if(mode)for(unsigned j=0;j<n;++j)for(int p=0;p<2;++p)cmd(15,2*j+p,half(factor[j],p));
  need(reference(a,k,q,x,injection,skip,decay,beta,factor,mode,out),"random domain unexpectedly overflowed");
  auto r=execute(mode);need(r.latency==(mode==0?4*n+15:3*n+11),"execution latency mismatch");
  output_matches(out);state_matches(original);
  // Wrong owner/epoch cannot consume a valid candidate.
  cmd(7,0,U(owner+1)|(U(epoch)<<32)|(U(position)<<64)|(U(position+1)<<96),true);
  if(trial%5==0){cmd(8,0,0);state_matches(original);cmd(12,0,0,true);commit(position+1,true);}
  else {commit(position+1);state_matches(a);cmd(12,0,0,true);}
  ++random_cases;
 }
 // Repeated GDN/SSM transitions exercise both physical bank roles without
 // reopening or reloading state. Aborting a candidate cannot swap roles.
 {unsigned n=3;open(n);std::vector<Row>a(n),factor(n);for(auto&v:a)v=random_row(10000);state_load(a);
  std::vector<int16_t>k{1024,-2048,4096},q{-1024,2048,512};load_vector(2,k);load_vector(3,q);
  Row x=random_row(5000),in=random_row(2000),skip=random_row(1000),out{};
  for(unsigned step=0;step<6;++step){unsigned mode=step%2;auto before=a;
   values(0,x);values(2,in);cmd(5,0,U(0x70000000U)|(U(0x50000000U)<<32));cmd(5,1,half(skip,0));cmd(5,2,half(skip,1));
   if(mode)for(unsigned r=0;r<n;++r){factor[r].fill(0x60000000);for(int p=0;p<2;++p)cmd(15,2*r+p,half(factor[r],p));}
   need(reference(a,k,q,x,in,skip,0x70000000U,0x50000000U,factor,mode,out),"repeat-mode numeric domain");
   execute(mode);output_matches(out);state_matches(before);auto c=cmd(7,0,U(owner)|(U(epoch)<<32)|(U(position)<<64)|(U(position+1)<<96));
   need(c.latency==1,"bank role commit must be constant-time");++epoch;++position;state_matches(a);
  }
 }
 // Rounded negative ties and beta=one: all-key prediction precedes update.
 {open(2);std::vector<Row>a(2);a[0].fill(-3);a[1].fill(5);state_load(a);std::vector<int16_t>k{8192,8192},q{16384,-16384};load_vector(2,k);load_vector(3,q);Row x{};x.fill(-7);values(0,x);cmd(5,0,U(0x40000000U)|(U(0x80000000U)<<32));Row out{},z{};std::vector<Row>f;need(reference(a,k,q,x,z,z,0x40000000U,0x80000000U,f,0,out),"tie reference");execute(0);output_matches(out);commit(position);state_matches(a);}
 // Overflow rejects the entire candidate, preserving every old row.
 {open(1);std::vector<Row>a(1);a[0].fill(INT32_MAX);state_load(a);load_vector(2,{32767});load_vector(3,{32767});Row x{};x.fill(INT32_MIN);values(0,x);cmd(5,0,U(0x80000000U)|(U(0x80000000U)<<32));execute(0,true);state_matches(a);commit(position+1,true);cmd(12,0,0,true);}
 // Exact four-tap depthwise convolution; no history changes before commit.
 for(unsigned trial=0;trial<100;++trial){open(1);Row x=random_row(20000);std::array<Row,3>h;std::array<std::array<int16_t,8>,4>t;values(0,x);
  for(int j=0;j<3;++j){h[j]=random_row(20000);for(int p=0;p<2;++p)cmd(9,2*j+p,half(h[j],p));}
  for(int j=0;j<4;++j){U v=0;for(int l=0;l<8;++l){t[j][l]=int(rng()%32768)-16384;v|=U(uint16_t(t[j][l]))<<(16*l);}cmd(10,j,v);}
  Row out{};for(int l=0;l<8;++l){I v=I(x[l])*t[0][l];for(int j=0;j<3;++j)v+=I(h[j][l])*t[j+1][l];out[l]=int32_t(rne(v,14));}
  need(execute(2).latency==14,"convolution latency");output_matches(out);
  auto matches_history=[&](const std::array<Row,3>&expect){for(int j=0;j<3;++j)for(int p=0;p<2;++p){U v=cmd(14,2*j+p,0).data;for(int l=0;l<4;++l)need(int32_t(v>>(32*l))==expect[j][p*4+l],"history changed incorrectly");}};
  matches_history(h);if(trial%3==0){cmd(8,0,0);matches_history(h);}else {commit(position+1);matches_history({x,h[0],h[1]});}
 }
 // Epoch exhaustion cannot wrap or partially commit.
 {open(1,0xffffffffU);std::vector<Row>a(1);a[0].fill(1);state_load(a);load_vector(2,{0});load_vector(3,{16384});Row x{};values(0,x);cmd(5,0,U(0x80000000U));execute(0);commit(position,true);state_matches(a);cmd(8,0,0);}
 // Reset in-flight invalidates context; arbitrary RAM is not a valid state.
 {open(256);std::vector<Row>a(256);for(auto&r:a)r.fill(5);state_load(a);load_vector(2,std::vector<int16_t>(256,1));load_vector(3,std::vector<int16_t>(256,1));Row x{};values(0,x);cmd(5,0,U(0x80000000U));dut.cmd_valid=1;dut.cmd_op=6;put(U(owner)<<2|U(epoch)<<34|U(position)<<66);tick();dut.cmd_valid=0;for(int i=0;i<19;++i)tick();reset();cmd(11,0,0,true);execute(0,true);}
 std::cout<<"{\"passed\":true,\"random_recurrent_cases\":"<<random_cases<<",\"conv_cases\":100,\"checks\":"<<checks<<",\"cycles\":"<<cycles<<"}\n";
 return 0;
}catch(const std::exception&e){std::cerr<<e.what()<<"\n";return 1;}}
