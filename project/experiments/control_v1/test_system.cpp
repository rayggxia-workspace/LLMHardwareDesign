#include "Vcontrol_system.h"
#include "verilated.h"
#include <array>
#include <vector>
#include <deque>
#include <random>
#include <iostream>
#include <cstdlib>
using Desc=std::array<uint32_t,8>;
constexpr uint64_t ExtBase=0x1200000000ULL;
static uint64_t checks=0,cycles=0;
static void need(bool b,const char*m){++checks;if(!b){std::cerr<<m<<" cycle="<<cycles<<"\n";std::exit(1);}}
static uint64_t ins(unsigned op,unsigned rd=0,unsigned ra=0,unsigned rb=0,unsigned flags=0,unsigned aux=0,uint32_t imm=0){return uint64_t(op)<<56|uint64_t(rd)<<52|uint64_t(ra)<<48|uint64_t(rb)<<44|uint64_t(flags)<<40|uint64_t(aux)<<32|imm;}
static Desc dma(bool write,unsigned ext,unsigned local,unsigned bytes){uint64_t addr=ExtBase+ext;return {{write?1u:0u,uint32_t(addr),uint32_t(addr>>32)|(local<<12),bytes,1,0,0,0}};}
static Desc vec(unsigned role,unsigned op,unsigned count,unsigned flags=0,unsigned a=0,unsigned b=0,unsigned dst=0,unsigned param=0){return {{(role<<8)|(flags<<12)|op,count,a,b,0,dst,param,0}};}
struct Sim{
 Vcontrol_system v;std::mt19937 rng{162};std::vector<uint8_t> ext=std::vector<uint8_t>(262144,0xa5);
 struct Read{bool valid=false;uint64_t addr=0;unsigned count=0,index=0;};std::array<Read,2> reads{};
 struct Write{uint64_t addr;unsigned count,index,id;};std::deque<Write>writes;std::array<bool,2>pending{{false,false}};
 unsigned ar_count=0,aw_count=0;bool allow_fault=false;
 Sim(){if(const char* seed=std::getenv("CONTROL_TEST_SEED"))rng.seed(std::stoul(seed));v.clk=0;v.axil_awaddr=0;v.axil_awvalid=0;v.axil_wdata=0;v.axil_wstrb=15;v.axil_wvalid=0;v.axil_bready=1;
  v.axil_araddr=0;v.axil_arvalid=0;v.axil_rready=1;v.arready=0;v.awready=0;v.wready=0;v.rvalid=0;v.rid=0;v.rresp=0;v.rlast=0;
  for(unsigned n=0;n<4;++n)v.rdata[n]=0;v.bvalid=0;v.bid=0;v.bresp=0;
  v.reset=1;for(unsigned n=0;n<4;++n){v.clk=0;v.eval();v.clk=1;v.eval();}v.reset=0;v.clk=0;v.eval();}
 unsigned offset(uint64_t a){need(a>=ExtBase && a+16<=ExtBase+ext.size(),"finite external range");return unsigned(a-ExtBase);}
 void tick(){v.clk=0;v.arready=rng()%4!=0;v.awready=rng()%4!=0;v.wready=rng()%3!=0;
  unsigned r=rng()%2;if(!reads[r].valid)r^=1;v.rvalid=reads[r].valid && rng()%3!=0;v.rid=r;v.rresp=0;
  if(v.rvalid){const auto&x=reads[r];v.rlast=x.index+1==x.count;unsigned a=offset(x.addr+x.index*16);for(unsigned n=0;n<4;++n){uint32_t z=0;for(unsigned b=0;b<4;++b)z|=uint32_t(ext[a+n*4+b])<<(b*8);v.rdata[n]=z;}}
  unsigned b=rng()%2;if(!pending[b])b^=1;v.bvalid=pending[b] && rng()%3!=0;v.bid=b;v.bresp=0;v.eval();
  if(v.rvalid && v.rready){auto&x=reads[r];if(++x.index==x.count)x.valid=false;}
  if(v.bvalid && v.bready)pending[b]=false;
  if(v.arvalid && v.arready){need(v.arid<2 && !reads[v.arid].valid,"finite read slots");need(v.arsize==4 && v.arburst==1 && v.arlen<16,"AR fields");reads[v.arid]={true,v.araddr,unsigned(v.arlen+1),0};++ar_count;}
  if(v.awvalid && v.awready){need(v.awid<2 && !pending[v.awid],"finite write slots");writes.push_back({v.awaddr,unsigned(v.awlen+1),0,v.awid});++aw_count;}
  if(v.wvalid && v.wready){need(!writes.empty(),"W has accepted AW");auto&x=writes.front();need(v.wlast==(x.index+1==x.count),"W tail");unsigned a=offset(x.addr+x.index*16);
   for(unsigned n=0;n<16;++n)if(v.wstrb&(1u<<n))ext[a+n]=v.wdata[n/4]>>(8*(n%4));if(++x.index==x.count){pending[x.id]=true;writes.pop_front();}}
  v.clk=1;v.eval();++cycles;need(!v.protocol_error,"real endpoint protocol");need(allow_fault||!v.fault,"controller fault");
 }
 void cfg(unsigned address,uint32_t data){v.axil_awaddr=address;v.axil_awvalid=1;v.axil_wdata=data;v.axil_wvalid=1;v.clk=0;v.eval();bool aw=false,w=false;
  unsigned guard=0;while(!aw||!w){const bool a=v.axil_awvalid&&v.axil_awready,b=v.axil_wvalid&&v.axil_wready;tick();if(a){aw=true;v.axil_awvalid=0;}if(b){w=true;v.axil_wvalid=0;}v.clk=0;v.eval();need(++guard<1000,"AXIL independent channels");}
  while(!v.axil_bvalid){tick();need(++guard<1000,"AXIL write response");}need(v.axil_bresp==0,"AXIL write accepted");tick();}
 void run(const std::vector<Desc>&ds,const std::vector<unsigned>&order){need(ds.size()<=16,"descriptor capacity");
  for(unsigned d=0;d<ds.size();++d)for(unsigned w=0;w<8;++w)cfg(0x2000+d*32+w*4,ds[d][w]);
  std::vector<uint64_t>program;for(auto d:order){program.push_back(ins(13,1,d,0,1,0));program.push_back(ins(14,2,1));}program.push_back(ins(18));need(program.size()<=256,"program capacity");
  for(unsigned n=0;n<program.size();++n){cfg(0x1000+n*8,uint32_t(program[n]));cfg(0x1004+n*8,program[n]>>32);}cfg(4,1);
  unsigned guard=0;while(!v.ended && !(allow_fault&&v.fault)){tick();need(++guard<2000000,"finite system program");}for(unsigned n=0;n<10;++n)tick();need(!v.busy && writes.empty() && !reads[0].valid && !reads[1].valid && !pending[0] && !pending[1],"all real transactions drained");
 }
 void s16(unsigned address,unsigned count,unsigned value){for(unsigned n=0;n<count;++n){ext[address+n*2]=value;ext[address+n*2+1]=value>>8;}}
 void check16(unsigned address,unsigned count,unsigned value){for(unsigned n=0;n<count;++n)need((unsigned(ext[address+n*2])|(unsigned(ext[address+n*2+1])<<8))==value,"external S16 numerical result");}
};
int main(int argc,char**argv){Verilated::commandArgs(argc,argv);
 {Sim x;for(unsigned n=0;n<192;++n)x.ext[n]=0;for(unsigned row=0;row<8;++row)for(unsigned k=0;k<8;++k)x.ext[row*16+k]=1;for(unsigned n=128;n<192;++n)x.ext[n]=1;
  Desc feed{{0x500,8|(1<<4),0,128,0,0,0,0}};
  Desc execute{{0x100,(8<<4)|(8<<8)|(1<<12)|(8<<15)|4,0,1,0,0,0,0}};
  Desc drain{{0x102,8,0,0,0,512,2<<8,0}};
  x.run({dma(false,0,0,192),feed,execute,drain,dma(true,4096,512,256)},{0,1,2,3,4});
  for(unsigned n=0;n<64;++n){unsigned a=4096+n*4;uint32_t value=uint32_t(x.ext[a])|uint32_t(x.ext[a+1])<<8|uint32_t(x.ext[a+2])<<16|uint32_t(x.ext[a+3])<<24;need(value==8,"M real feeder GEMM output");}
  need(x.v.s_read_count==16 && x.v.s_write_count==12,"D only performs real S accesses");}
 {Sim x;constexpr unsigned chunk=4096,bytes=chunk*2,source=16384,scratch=65536;
  x.s16(source,chunk*3,0);std::vector<Desc> d{vec(2,0,0)};
  for(unsigned n=0;n<3;++n)d.push_back(dma(false,source+n*bytes,0,bytes));
  d.push_back(vec(2,1,chunk));d.push_back(vec(2,2,0));d.push_back(vec(2,3,chunk,4,0,0,8192));
  for(unsigned n=0;n<3;++n)d.push_back(dma(true,scratch+n*bytes,8192,bytes));
  d.push_back(vec(2,4,0));for(unsigned n=0;n<3;++n)d.push_back(dma(false,scratch+n*bytes,0,bytes));
  d.push_back(vec(2,6,chunk,4,0,0,8192));std::vector<unsigned> order{0,1,4,2,4,3,4,5,1,6,7,2,6,8,3,6,9,10,11,14,7,12,14,8,13,14,9};
  x.run(d,order);x.check16(scratch,chunk*3,1);}
 {Sim x;x.s16(0,257,16384);
  Desc begin{{0x600,33,0,0,0,0,1,42}},fill{{0x601,33,4096,0,0,0,0,0}},commit{{0x602,0,0,0,0,0,0,0}},drain{{0x603,33,8192,0,0,0,0,0}},release{{0x604,0,0,0,0,0,0,0}};
  x.run({dma(false,0,0,514),vec(3,0,257,5,0,0x40000000,1024),vec(4,0,257,5,1024,0x40000200,4096,1),begin,fill,commit,drain,release,dma(true,4096,8192,514)},{0,1,2,3,4,5,6,7,8});x.check16(4096,257,8192);}

 // R native pass ABI. All state/data movement below is performed by D/S/R RTL.
 auto rload=[](unsigned target,unsigned count,unsigned src,unsigned index=0){return Desc{{0x700,count,src,index,target,0,0,0}};};
 auto rread=[](unsigned bank,unsigned count,unsigned dst,unsigned index=0){return Desc{{0x701,count,dst,index,bank,0,0,0}};};
 auto rcmd=[](unsigned op,unsigned rows=0,unsigned role=0,unsigned mode=0,bool clear=false,unsigned dst=0,unsigned flags=0){return Desc{{0x702|(flags<<12),op|(rows<<3)|(role<<12)|(unsigned(clear)<<13)|(mode<<14),dst,0,0,0,0,0}};};
 auto put32=[](Sim&x,unsigned a,uint32_t value){for(unsigned b=0;b<4;++b)x.ext[a+b]=value>>(b*8);};
 auto check32=[](Sim&x,unsigned a,uint32_t expected){uint32_t got=0;for(unsigned b=0;b<4;++b)got|=uint32_t(x.ext[a+b])<<(b*8);need(got==expected,"R hardware-chain S32 result");};
 // Both complete banks, all legal state packet addresses, real S arbitration.
 {Sim x;for(unsigned i=0;i<512;++i)put32(x,i*4,0x12345678u+i*0x9e3779b9u);
  x.run({dma(false,0,0,2048),rload(0,64,0),rload(1,64,1024),rread(0,64,4096),rread(1,64,5120),dma(true,8192,4096,2048)},{0,1,2,3,4,5});
  for(unsigned i=0;i<512;++i)check32(x,8192+i*4,0x12345678u+i*0x9e3779b9u);
 }
 // Full GDN passes -> packed final output -> E conversion -> G -> T -> external.
 {Sim x;for(unsigned i=0;i<256;++i)put32(x,i*4,1024);
  x.s16(1024,64,16384);for(unsigned i=0;i<24;++i)put32(x,1152+i*4,i<8?65536:0);
  put32(x,1248,0x80000000u);put32(x,1252,0);
  x.run({dma(false,0,0,1264),rcmd(7),rload(0,64,0),rload(2,4,1024),rload(3,4,1088),rload(4,6,1152),rload(5,1,1248)},{0,1,2,3,4,5,6});
  Desc begin{{0x600,2,0,0,0,0,1,123}},fill{{0x601,2,4096,0,0,0,0,0}},commit{{0x602,0,0,0,0,0,0,0}},drain{{0x603,2,8192,0,0,0,0,0}},release{{0x604,0,0,0,0,0,0,0}};
  x.run({rcmd(0,32),rcmd(1,32,0,0,true),rcmd(4),rcmd(2,32),rcmd(3,32,0,0,true),rcmd(5,0,0,0,false,2048,3),vec(3,13,8,4,2048,0,3072,6),vec(4,1,16,4,3072,0,4096),begin,fill,commit,drain,release,dma(true,16384,8192,32)}, {0,1,2,3,4,5,6,7,8,9,10,11,12,13});
  for(unsigned packet=0;packet<2;++packet)for(unsigned lane=0;lane<8;++lane){unsigned a=16384+packet*16+lane*2,value=unsigned(x.ext[a])|(unsigned(x.ext[a+1])<<8);need(value==(lane<4?10198u:8192u),"R-E-G-T real numerical chain");}
 }
 // SSM per-element decay, injected update, final C dot and skip branch.
 {Sim x;for(unsigned i=0;i<256;++i){put32(x,i*4,1024);put32(x,1024+i*4,0x40000000u);}
  x.s16(2048,64,16384);for(unsigned i=0;i<24;++i)put32(x,2176+i*4,i<8?8192:i<16?1024:65536);put32(x,2272,0);put32(x,2276,0);
  x.run({dma(false,0,0,2288),rcmd(7),rload(0,64,0),rload(1,64,1024),rload(2,4,2048),rload(3,4,2112),rload(4,6,2176),rload(5,1,2272)},{0,1,2,3,4,5,6,7});
  x.run({rcmd(0,32,0,1),rcmd(2,32,0,1),rcmd(3,32,0,1,true),rcmd(5,0,0,1,false,3072,3),dma(true,12288,3072,32)},{0,1,2,3,4});
  for(unsigned i=0;i<8;++i)check32(x,12288+i*4,57344);
 }
 // Four-tap convolution through the same R endpoint and finite output store.
 {Sim x;for(unsigned i=0;i<8;++i)put32(x,i*4,1024);for(unsigned i=0;i<24;++i)put32(x,32+i*4,(i/8+2)*1024);x.s16(128,32,16384);
  x.run({dma(false,0,0,192),rcmd(7),rload(4,2,0),rload(6,6,32),rload(7,4,128),rcmd(6,0,0,2,true),rcmd(5,0,0,2,false,2048,3),dma(true,8192,2048,32)},{0,1,2,3,4,5,6,7});
  for(unsigned i=0;i<8;++i)check32(x,8192+i*4,10240);
 }


 // M formatted S32 results become R state; N Softmax Q1.14 becomes R query.
 {Sim x;for(unsigned i=0;i<336;++i)x.ext[i]=0;
  for(unsigned row=0;row<8;++row)for(unsigned k=0;k<8;++k)x.ext[row*16+k]=1;
  for(unsigned i=128;i<192;++i)x.ext[i]=1;x.s16(192,8,16384);put32(x,224,0x80000000u);put32(x,228,0);
  Desc feed{{0x500,8|(1<<4),0,128,0,0,0,0}},execute{{0x100,(8<<4)|(8<<8)|(1<<12)|(8<<15)|4,0,1,0,0,0,0}},drain{{0x102,8,0,0,0,512,2<<8,0}};
  x.run({dma(false,0,0,336),feed,execute,drain},{0,1,2,3});
  x.run({vec(2,0,0),vec(2,1,8,0,240),vec(2,2,0),vec(2,3,8,4,240,0,3072),vec(2,4,0),vec(2,6,8,4,3072,0,3088)},{0,1,2,3,4,5});
  x.run({rcmd(7),rload(0,16,512),rload(2,1,192),rload(3,1,3088),rload(4,6,240),rload(5,1,224),rcmd(0,8),rcmd(1,8,0,0,true),rcmd(4),rcmd(2,8),rcmd(3,8,0,0,true),rcmd(5,0,0,0,false,1024,3),dma(true,8192,1024,32)}, {0,1,2,3,4,5,6,7,8,9,10,11,12});
  for(unsigned i=0;i<8;++i)check32(x,8192+i*4,8);
 }
 // Rejected descriptors must complete as errors instead of hanging R or S.
 for(unsigned which=0;which<5;++which){Sim x;x.allow_fault=true;
  Desc bad=which==0?rload(0,65,0):which==1?rload(2,5,0):which==2?rread(0,2,0,63):which==3?rcmd(0,33):rcmd(5,0,0,0,false,16368,3);
  x.run({bad},{0});need(x.v.fault==4,"R descriptor error reaches C");need(x.ar_count==0&&x.aw_count==0,"invalid R task performs no external transfer");
 }
 {Sim x;x.allow_fault=true;Desc bad{{0x800,0,0,0,0,0,0,0}};x.run({bad},{0});need(x.v.fault==5,"endpoint8 rejected by eight-endpoint C");}
 std::cout<<"{\"passed\":true,\"checks\":"<<checks<<",\"cycles\":"<<cycles<<",\"real_compositions\":8,\"cpu_tensor_moves\":0}\n";
}
