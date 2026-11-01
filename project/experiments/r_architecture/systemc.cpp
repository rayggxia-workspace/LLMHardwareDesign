// Clocked, deliberately serialized first scheduler. No claim of optimal overlap.
#include <systemc>
#include <array>
#include <vector>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <cstdint>
#include <algorithm>
using namespace sc_core;
using I=__int128_t; using V=std::vector<int32_t>;
static void require(bool b,const char*s){if(!b)throw std::runtime_error(s);}
template<class T>std::vector<T> readv(std::ifstream&f,size_t n){std::vector<T>v(n);f.read(reinterpret_cast<char*>(v.data()),n*sizeof(T));require(bool(f),"truncated corpus");return v;}
static I round_even(I a,unsigned s){I q=a>>s;I rem=a-q*(I(1)<<s),half=I(1)<<(s-1);return q+(rem>half||(rem==half&&(q&1)));}
struct Numbers{
 bool good=true;V result,out;
 int32_t ck(I a){good&=a>=INT32_MIN&&a<=INT32_MAX;return int32_t(uint32_t(a));}
 Numbers(const V&s,const std::vector<int16_t>&k,const std::vector<int16_t>&q,const V&v,const std::vector<uint32_t>&f,unsigned mode,uint32_t decay,uint32_t beta,const std::vector<int16_t>&t){
  out.resize(8);result.resize(s.size());
  if(mode==2){for(int l=0;l<8;++l){I z=I(v[l])*t[l];for(int j=0;j<3;++j)z+=I(s[j*8+l])*t[(j+1)*8+l];out[l]=ck(round_even(z,14));}std::copy(v.begin(),v.begin()+8,result.begin());std::copy(s.begin(),s.begin()+16,result.begin()+8);return;}
  size_t rows=s.size()/8;for(size_t i=0;i<s.size();++i)result[i]=ck(round_even(I(s[i])*(mode?f[i]:decay),31));
  std::array<int32_t,8>err{};
  if(!mode)for(int l=0;l<8;++l){I z=0;for(size_t r=0;r<rows;++r)z+=I(result[r*8+l])*k[r];int32_t pred=ck(round_even(z,14)),e=ck(I(v[l])-pred);err[l]=ck(round_even(I(e)*beta,31));}
  for(size_t i=0;i<s.size();++i)result[i]=ck(I(result[i])+round_even(I(mode?v[8+i%8]:err[i%8])*k[i/8],14));
  for(int l=0;l<8;++l){I z=0;for(size_t r=0;r<rows;++r)z+=I(result[r*8+l])*q[r];int32_t a=ck(round_even(z,14));out[l]=mode?ck(I(a)+round_even(I(v[l])*v[16+l],16)):a;}
 }
};
struct Request{unsigned bytes=0,latency=0,beat=0;};
std::ostream&operator<<(std::ostream&o,const Request&r){return o<<r.bytes;}
// One pending descriptor and one completion register: explicit backpressure.
struct Link:sc_module{
 sc_in<bool>clk;sc_fifo<Request>requests{1};sc_fifo<bool>done{1};uint64_t bytes=0,busy=0,transactions=0;unsigned max_fifo=0;
 SC_HAS_PROCESS(Link);Link(sc_module_name n):sc_module(n){SC_THREAD(service);sensitive<<clk.pos();}
 void service(){while(true){Request r=requests.read();max_fifo=std::max(max_fifo,1u);++transactions;bytes+=r.bytes;unsigned cycles=r.latency+(r.bytes+r.beat-1)/r.beat;for(unsigned i=0;i<cycles;++i){wait();++busy;}done.write(true);}}
 void transfer(unsigned n,unsigned beat,unsigned latency=0){if(!n)return;requests.write({n,latency,beat});done.read();}
};
// S has ONE shared narrow request (16 B/cycle), not four independent ports.
// Wide reads (64 B/cycle) exclude narrow access. This policy uses narrow DMA.
struct Storage:Link{uint64_t reads=0,writes=0,peak=0;Storage(sc_module_name n):Link(n){}
 void access(unsigned n,bool wr){if(wr)writes+=n;else reads+=n;transfer(n,16);}
 void reserve(unsigned n){require(n<=16384,"S capacity exceeded");peak=std::max(peak,uint64_t(n));}
};
struct System:sc_module{
 sc_clock clk{"clk",sc_time(1,SC_NS)};Link interconnect{"interconnect"},dram{"dram"};Storage s{"S16K"};
 unsigned cap,dram_latency,dram_beat;std::string path,arch;std::ofstream csv;bool passed=false;
 uint64_t compute=0,slots=0,utilized=0,state_read=0,state_write=0,coeff=0,intermediate=0,chunks=0,swaps=0,commands=0,checks=0;
 SC_HAS_PROCESS(System);
 System(sc_module_name n,std::string p,std::string a,unsigned c,unsigned latency,unsigned bw,std::string result):sc_module(n),cap(c),dram_latency(latency),dram_beat(bw),path(p),arch(a),csv(result){
  interconnect.clk(clk);dram.clk(clk);s.clk(clk);SC_THREAD(run);sensitive<<clk.posedge_event();
 }
 uint64_t now(){return uint64_t(sc_time_stamp()/sc_time(1,SC_NS));}
 void cycles(unsigned n,bool arithmetic=true){for(unsigned j=0;j<n;++j){wait();if(arithmetic){++compute;slots+=8;}}}
 void operation(unsigned rows){utilized+=8*rows;cycles(rows+2);}
 void transfer(unsigned bytes,bool from_dram,const char*kind){
  if(std::string(kind)=="state"){if(from_dram)state_read+=bytes;else state_write+=bytes;}
  else if(std::string(kind)=="coefficient")coeff+=bytes;else intermediate+=bytes;
  // Serialized DMA through bounded S tile: independent link and S service cycles.
  for(unsigned pos=0;pos<bytes;pos+=1024){unsigned n=std::min(1024u,bytes-pos);s.reserve(512+std::min(n,1024u));
   // Local R banks are NOT S allocations; only DMA double buffer + metadata.
   if(from_dram){dram.transfer(n,dram_beat,dram_latency);interconnect.transfer(n,16);s.access(n,true);s.access(n,false);interconnect.transfer(n,16);}
   else{interconnect.transfer(n,16);s.access(n,true);s.access(n,false);interconnect.transfer(n,16);dram.transfer(n,dram_beat,dram_latency);}
  }
 }
 void execute(unsigned mode,unsigned n,bool resident,bool cold){
  unsigned rows=n/8,tiles=(n+cap-1)/cap;
  if(mode==2){if(cold)transfer(96,true,"state");transfer(32+64,true,"coefficient");utilized+=32;cycles(14);return;}
  transfer(96,true,"coefficient");
  if(n<=cap){transfer(rows*4+(mode?n*4:0),true,"coefficient");if(cold||!resident)transfer(n*4,true,"state");for(unsigned p=0;p<(mode?3u:4u);++p)operation(rows);cycles(mode?5:7);utilized+=8;if(!resident)transfer(n*4,false,"state");return;}
  // Global GDN predict then ONE error broadcast; no per-tile EXEC/COMMIT.
  for(unsigned t=0;t<tiles;++t){unsigned words=std::min(cap,n-t*cap);++chunks;transfer(mode?words*4:words/4,true,"coefficient");transfer(words*4,true,"state");operation(words/8);if(!mode)operation(words/8);transfer(words*4,false,"intermediate");}
  if(!mode){cycles(5);utilized+=8;}
  for(unsigned t=0;t<tiles;++t){unsigned words=std::min(cap,n-t*cap);++chunks;transfer(words/2,true,"coefficient");transfer(words*4,true,"intermediate");operation(words/8);operation(words/8);transfer(words*4,false,"state");}
  cycles(mode?5:2);if(mode)utilized+=8;
 }
 void run(){try{
  std::ifstream f(path,std::ios::binary);require(bool(f),"missing corpus");auto h=readv<uint32_t>(f,8);unsigned mode=h[0],n=h[1],layers=h[2],tokens=h[3],flags=h[5];
  csv<<"architecture,capacity,workload,status,cycles,compute_cycles,multiply_ops,lane_slots,utilization,dram_read_state,dram_write_state,coefficient_bytes,intermediate_bytes,S_reads,S_writes,S_peak,link_bytes,link_busy,dram_bytes,dram_busy,tile_visits,context_loads,numeric_checks,policy,dram_latency,dram_bytes_per_cycle\n";
  if(arch=="C"||(arch=="A0"&&mode!=2&&n>2048)){csv<<arch<<','<<cap<<','<<path<<",UNSUPPORTED_CURRENT_MODEL\n";passed=true;sc_stop();return;}
  bool resident=layers==1&&n<=cap;std::vector<V>state;for(unsigned l=0;l<layers;++l)state.push_back(readv<int32_t>(f,n));
  uint64_t start=now();
  for(unsigned token=0;token<tokens;++token)for(unsigned layer=0;layer<layers;++layer){
   auto k=readv<int16_t>(f,n/8),q=readv<int16_t>(f,n/8);auto v=readv<int32_t>(f,24);auto factors=readv<uint32_t>(f,mode==1?n:0);auto taps=readv<int16_t>(f,mode==2?32:0);auto expected=readv<uint32_t>(f,2);auto out=readv<int32_t>(f,8),next=readv<int32_t>(f,n);
   if(flags&32)std::fill(state[layer].begin(),state[layer].end(),0);
   auto before=state[layer];Numbers value(state[layer],k,q,v,factors,mode,h[6],h[7],taps);
   execute(mode,n,resident,token==0);if(!resident)++swaps;
   require(value.good==bool(expected[0]),"overflow mismatch");require(value.out==out,"full output mismatch");checks+=9;
   // A bad owner/epoch commit is rejected, but a valid pending transaction remains.
   bool commit=value.good&&!(flags&(2|4|16));if(commit)state[layer]=value.result;
   require(commit==bool(expected[1]),"commit mismatch");require(state[layer]==next,"full state mismatch");checks+=n+1;
   if(!commit)require(state[layer]==before,"rollback changed old state");
   cycles(1,false);++commands; // single global publication; does not copy old state
   if(flags&8)cycles(7,false);if(flags&4)cycles(2,false);
  }
  // Publish only final resident version to DRAM; retain all old versions until commit.
  if(resident)transfer(n*4,false,"state");
  require(f.peek()==std::char_traits<char>::eof(),"trailing corpus data");
  uint64_t total=now()-start;
  csv<<arch<<','<<cap<<','<<path<<",PASS,"<<total<<','<<compute<<','<<utilized<<','<<slots<<','<<(slots?double(utilized)/slots:0)<<','<<state_read<<','<<state_write<<','<<coeff<<','<<intermediate<<','<<s.reads<<','<<s.writes<<','<<s.peak<<','<<interconnect.bytes<<','<<interconnect.busy<<','<<dram.bytes<<','<<dram.busy<<','<<chunks<<','<<swaps<<','<<checks<<",serialized_narrow_dma,"<<dram_latency<<','<<dram_beat<<'\n';passed=true;sc_stop();
 }catch(const std::exception&e){std::cerr<<"FAIL "<<e.what()<<'\n';sc_stop();}}
};
int sc_main(int argc,char**argv){try{require(argc==8,"usage corpus architecture capacity dram_latency dram_bytes_per_cycle output_csv seed_unused");System model("model",argv[1],argv[2],std::stoul(argv[3]),std::stoul(argv[4]),std::stoul(argv[5]),argv[6]);sc_start();return model.passed?0:1;}catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 2;}}
