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
 unsigned ar_count=0,aw_count=0;
 Sim(){v.clk=0;v.axil_awaddr=0;v.axil_awprot=0;v.axil_awvalid=0;v.axil_wdata=0;v.axil_wstrb=15;v.axil_wvalid=0;v.axil_bready=1;
  v.axil_araddr=0;v.axil_arprot=0;v.axil_arvalid=0;v.axil_rready=1;v.arready=0;v.awready=0;v.wready=0;v.rvalid=0;v.rid=0;v.rresp=0;v.rlast=0;
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
  v.clk=1;v.eval();++cycles;need(!v.protocol_error,"real endpoint protocol");need(!v.fault,"controller fault");
 }
 void cfg(unsigned address,uint32_t data){v.axil_awaddr=address;v.axil_awvalid=1;v.axil_wdata=data;v.axil_wvalid=1;v.clk=0;v.eval();bool aw=false,w=false;
  unsigned guard=0;while(!aw||!w){const bool a=v.axil_awvalid&&v.axil_awready,b=v.axil_wvalid&&v.axil_wready;tick();if(a){aw=true;v.axil_awvalid=0;}if(b){w=true;v.axil_wvalid=0;}v.clk=0;v.eval();need(++guard<1000,"AXIL independent channels");}
  while(!v.axil_bvalid){tick();need(++guard<1000,"AXIL write response");}need(v.axil_bresp==0,"AXIL write accepted");tick();}
 void run(const std::vector<Desc>&ds,const std::vector<unsigned>&order){need(ds.size()<=16,"descriptor capacity");
  for(unsigned d=0;d<ds.size();++d)for(unsigned w=0;w<8;++w)cfg(0x2000+d*32+w*4,ds[d][w]);
  std::vector<uint64_t>program;for(auto d:order){program.push_back(ins(13,1,d,0,1,0));program.push_back(ins(14,2,1));}program.push_back(ins(18));need(program.size()<=256,"program capacity");
  for(unsigned n=0;n<program.size();++n){cfg(0x1000+n*8,uint32_t(program[n]));cfg(0x1004+n*8,program[n]>>32);}cfg(4,1);
  unsigned guard=0;while(!v.ended){tick();need(++guard<2000000,"finite system program");}for(unsigned n=0;n<10;++n)tick();need(!v.busy && writes.empty() && !reads[0].valid && !reads[1].valid && !pending[0] && !pending[1],"all real transactions drained");
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
 std::cout<<"{\"passed\":true,\"checks\":"<<checks<<",\"cycles\":"<<cycles<<",\"real_compositions\":3,\"cpu_tensor_moves\":0}\n";
}
