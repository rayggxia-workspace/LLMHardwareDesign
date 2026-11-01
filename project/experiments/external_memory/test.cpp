#include "Vexternal_memory_fixture.h"
#include "verilated.h"
#include <array>
#include <vector>
#include <deque>
#include <random>
#include <stdexcept>
#include <iostream>
#include <sstream>
#include <cmath>
#include <algorithm>
#include <cstdint>
#include <memory>
using U=__uint128_t;using I=__int128_t;using Row=std::array<int32_t,8>;
// Parse Verilator initial-state controls before constructing any DUT storage.
static std::unique_ptr<Vexternal_memory_fixture> dut;
#define d (*dut)
static std::mt19937 rng(156);
static std::mt19937 bus_rng(1561),hold_rng(1562);
static uint64_t cycles=0,checks=0,reads=0,writes=0,req_wait=0,rsp_wait=0,s_wait=0;
static unsigned latency=1,gap=0,interval=1,peak=0,reserve_peak=0,t_peak=0;
static bool inject_error=false;
static std::vector<U> memory(131072,U(0xa5a5a5a5a5a5a5a5ULL)<<64|0x5a5a5a5a5a5a5a5aULL);
struct Request{bool write,error;unsigned addr;U data;uint64_t due;};
static std::deque<Request> pending;
static void need(bool v,const char* message){++checks;if(!v)throw std::runtime_error(message);}
template<class T>static void put(T& port,U value){for(int i=0;i<4;++i){port[i]=uint32_t(value);value>>=32;}}
template<class T>static U get(const T&port){U value=0;for(int i=3;i>=0;--i)value=value<<32|port[i];return value;}
static I rne(I value,unsigned shift){I q=value>>shift;U r=U(value)&((U(1)<<shift)-1),h=U(1)<<(shift-1);return q+(r>h||(r==h&&(q&1)));}
static U random_word(){return U(rng())<<96|U(rng())<<64|U(rng())<<32|rng();}
static bool stalled=false,held_write=false;static unsigned held_addr;static U held_data;
static void tick(){
 d.clk=0;d.eval();
 d.dma_ext_ready=pending.size()<4&&cycles%interval==0&&(gap==0||bus_rng()%gap!=0);
 d.dma_ext_rsp_valid=!pending.empty()&&pending.front().due<=cycles;
 d.dma_ext_rsp_error=d.dma_ext_rsp_valid&&pending.front().error;
 put(d.dma_ext_rsp_data,d.dma_ext_rsp_valid?memory[pending.front().addr/16]:0);
 d.eval();
 if(stalled)need(d.dma_ext_valid&&bool(d.dma_ext_write)==held_write&&d.dma_ext_addr==held_addr&&get(d.dma_ext_data)==held_data,"external request changed under backpressure");
 stalled=d.dma_ext_valid&&!d.dma_ext_ready;
 held_write=d.dma_ext_write;held_addr=d.dma_ext_addr;held_data=get(d.dma_ext_data);
 bool accept=d.dma_ext_valid&&d.dma_ext_ready,retire=d.dma_ext_rsp_valid&&d.dma_ext_rsp_ready;
 Request request{bool(d.dma_ext_write),inject_error,unsigned(d.dma_ext_addr),get(d.dma_ext_data),cycles+latency};
 if(accept){need(request.addr%16==0&&request.addr/16<memory.size(),"external address bounds");inject_error=false;if(request.write)++writes;else ++reads;}
 req_wait+=d.dma_ext_valid&&!d.dma_ext_ready;rsp_wait+=d.dma_ext_rsp_valid&&!d.dma_ext_rsp_ready;s_wait+=d.monitor_s_wait;
 if(!d.reset){reserve_peak=std::max(reserve_peak,unsigned(d.dma_reserved_words));need(d.dma_reserved_words<=4,"DMA over-reserved");}
 if(!d.reset&&d.t_busy)t_peak=std::max(t_peak,unsigned(d.t_word_count));
 if(d.dma_busy&&!d.dma_done_ready)need(!d.dma_cmd_ready,"busy DMA admitted another descriptor");
 d.clk=1;d.eval();d.clk=0;d.eval();++cycles;
 if(retire){auto r=pending.front();pending.pop_front();if(r.write&&!r.error)memory[r.addr/16]=r.data;}
 if(accept)pending.push_back(request);
 peak=std::max(peak,unsigned(pending.size()));need(pending.size()<=4,"external BFM queue overflow");
 need(cycles<10000000,"global timeout");
}
static void reset(){
 pending.clear();stalled=false;inject_error=false;d.reset=1;
 d.dma_cmd_valid=0;d.dma_done_ready=0;d.cpu_req=0;d.cpu_take=0;
 d.s_load_valid=0;d.s_done_take=0;d.m_cmd_valid=0;d.n_cmd_valid=0;d.r_cmd_valid=0;
 d.m_rsp_ready=0;d.n_rsp_ready=0;d.r_rsp_ready=0;
 d.t_begin_valid=0;d.t_write_valid=0;d.t_commit_valid=0;d.t_revoke_valid=0;d.t_release_valid=0;
 tick();tick();d.reset=0;tick();
}
static U cpu(bool write,unsigned addr,U data=0){
 d.cpu_req=1;d.cpu_wr=write;d.cpu_addr=addr;put(d.cpu_din,data);d.cpu_take=0;d.eval();
 unsigned wait=0;while(!d.cpu_ready){tick();need(++wait<50000,"S request timeout");}tick();d.cpu_req=0;
 while(!d.cpu_valid){tick();need(++wait<50000,"S response timeout");}
 U result=get(d.cpu_dout);d.cpu_take=1;tick();d.cpu_take=0;return result;
}
static void dma_start(unsigned mode,unsigned ext,unsigned rows,unsigned cols,unsigned stride,unsigned base,unsigned ss){
 d.dma_cmd_mode=mode;d.dma_cmd_ext_base=ext;d.dma_cmd_ext_stride=stride;
 d.dma_cmd_rows=rows;d.dma_cmd_cols=cols;d.dma_cmd_s_base=base;d.dma_cmd_s_stride=ss;
 d.dma_cmd_valid=1;d.eval();need(d.dma_cmd_ready,"DMA command unavailable");tick();d.dma_cmd_valid=0;
}
static void dma_finish(bool error=false){
 unsigned n=0;while(!d.dma_done_valid){tick();need(++n<300000,"DMA completion timeout");}
 need(bool(d.dma_done_error)==error,"DMA error mismatch");need(pending.empty(),"completion before external acknowledgments");
 for(int i=0;i<3;++i){tick();need(d.dma_done_valid&&bool(d.dma_done_error)==error,"completion not held");}
 d.dma_done_ready=1;tick();d.dma_done_ready=0;need(!d.dma_busy,"DMA not released");
}
static void dma(unsigned mode,unsigned ext,unsigned rows,unsigned cols,unsigned stride,unsigned base,unsigned ss,bool error=false){dma_start(mode,ext,rows,cols,stride,base,ss);dma_finish(error);}
static U command(char unit,unsigned op,unsigned index,U data=0,U aux=0,bool error=false){
 if(unit=='m'){d.m_cmd_valid=1;d.m_cmd_op=op;d.m_cmd_index=index;d.m_cmd_data=uint64_t(data);d.eval();need(d.m_cmd_ready,"M command unavailable");}
 if(unit=='n'){d.n_cmd_valid=1;d.n_cmd_op=op;d.n_cmd_count=index;d.n_cmd_param=uint32_t(aux);put(d.n_cmd_data,data);put(d.n_cmd_aux,aux);d.eval();need(d.n_cmd_ready,"N command unavailable");}
 if(unit=='r'){d.r_cmd_valid=1;d.r_cmd_op=op;d.r_cmd_index=index;put(d.r_cmd_data,data);d.eval();need(d.r_cmd_ready,"R command unavailable");}
 tick();d.m_cmd_valid=d.n_cmd_valid=d.r_cmd_valid=0;
 auto valid=[&](){return unit=='m'?d.m_rsp_valid:unit=='n'?d.n_rsp_valid:d.r_rsp_valid;};
 auto bad=[&](){return unit=='m'?d.m_rsp_error:unit=='n'?d.n_rsp_error:d.r_rsp_error;};
 auto value=[&](){return unit=='m'?get(d.m_rsp_data):unit=='n'?get(d.n_rsp_data):get(d.r_rsp_data);};
 unsigned n=0;while(!valid()){tick();need(++n<50000,"compute response timeout");}
 need(bool(bad())==error,"compute response error");U result=value();
 for(unsigned i=0,count=hold_rng()%3;i<count;++i){tick();need(valid()&&value()==result&&bool(bad())==error,"compute response not held");}
 if(unit=='m')d.m_rsp_ready=1;if(unit=='n')d.n_rsp_ready=1;if(unit=='r')d.r_rsp_ready=1;
 tick();d.m_rsp_ready=d.n_rsp_ready=d.r_rsp_ready=0;return result;
}
static void begin_t(unsigned words){
 d.t_begin_valid=1;d.t_begin_owner=1;d.t_begin_generation=156;d.t_begin_words=words;d.eval();need(d.t_begin_ready,"T begin refused");tick();d.t_begin_valid=0;
}
static void write_t(unsigned index,U value){
 d.t_write_valid=1;d.t_write_index=index;put(d.t_write_data,value);d.eval();need(d.t_write_ready,"T write refused");tick();d.t_write_valid=0;
}
static void commit_t(){d.t_commit_valid=1;d.eval();need(d.t_commit_ready,"T commit refused");tick();d.t_commit_valid=0;}
static void release_t(){need(d.t_release_ready&&!d.dma_busy,"T release before DMA completion");d.t_release_valid=1;tick();d.t_release_valid=0;need(!d.t_busy&&!d.t_protocol_error,"T release failed");}
static std::vector<std::string> reports;
struct Measure{
 std::string name;uint64_t c=cycles,r=reads,w=writes,q=req_wait,s=s_wait;
 explicit Measure(std::string n):name(n){}
 void finish(uint64_t rb,uint64_t wb){need((reads-r)*16==rb&&(writes-w)*16==wb,"external byte accounting mismatch");std::ostringstream o;o<<"{\"name\":\""<<name<<"\",\"latency\":"<<latency<<",\"request_interval\":"<<interval<<",\"request_gap_divisor\":"<<gap<<",\"cycles\":"<<cycles-c<<",\"read_bytes\":"<<(reads-r)*16<<",\"write_bytes\":"<<(writes-w)*16<<",\"external_request_stall_cycles\":"<<req_wait-q<<",\"S_request_stall_cycles\":"<<s_wait-s<<"}";reports.push_back(o.str());}
};
static void transfers(){
 Measure measure("DMA_2D_and_bounds");
 std::vector<U> expect(21);for(auto&v:expect)v=random_word();
 U canary=random_word();for(unsigned w=0;w<27;++w)memory[0x9000/16+w]=canary;
 for(unsigned r=0;r<3;++r)for(unsigned c=0;c<7;++c)memory[0x1000/16+11*r+c]=expect[7*r+c];
 dma(0,0x1000,3,7,176,200,13);
 for(unsigned r=0;r<3;++r)for(unsigned c=0;c<7;++c)need(cpu(false,200+13*r+c)==expect[7*r+c],"2D load data mismatch");
 dma(1,0x9000,3,7,144,200,13);
 for(unsigned r=0;r<3;++r){for(unsigned c=0;c<7;++c)need(memory[0x9000/16+9*r+c]==expect[7*r+c],"2D store data mismatch");if(r<2)need(memory[0x9000/16+9*r+7]==canary,"external row gap overwritten");}
 uint64_t requests=reads+writes;
 dma(0,3,1,1,16,0,1,true);dma(0,0x1000,0,1,16,0,1,true);
 dma(0,0xfffffff0,2,2,32,0,2,true);dma(0,0x1000,2,8,128,1020,8,true);
 dma(3,0x1000,1,1,16,0,1,true);dma(2,0x1000,1,385,6160,0,385,true);
 need(reads+writes==requests,"invalid descriptor emitted traffic");
 for(unsigned w=0;w<21;++w)cpu(true,400+w,canary);
 inject_error=true;dma(0,0x1000,3,7,176,400,7,true);
 need(cpu(false,400)==canary,"errored read beat modified S");
 for(unsigned w=1;w<21;++w)need(cpu(false,400+w)==expect[w],"good read beat lost after fault");
 dma(0,0x1000,3,7,176,400,7); // Fault does not poison the following descriptor.
 memory[0xb000/16]=canary;
 inject_error=true;dma(1,0xb000,3,7,112,400,7,true);
 need(memory[0xb000/16]==canary,"failed write changed external destination");
 measure.finish(1008,672);
}
static void matrix(){
 Measure measure("M_8x29x7_S8");
 constexpr unsigned rows=8,k=29,n=7,tiles=4;
 int a[rows][32]{},b[32][8]{};
 for(unsigned r=0;r<rows;++r)for(unsigned j=0;j<k;++j)a[r][j]=int(rng()%127)-63;
 for(unsigned j=0;j<k;++j)for(unsigned c=0;c<n;++c)b[j][c]=int(rng()%127)-63;
 for(unsigned t=0;t<tiles;++t){
  for(unsigned r=0;r<rows;++r){U word=0;for(unsigned j=0;j<8;++j)word|=U(uint8_t(a[r][8*t+j]))<<(8*j);memory[0x10000/16+8*t+r]=word;}
  for(unsigned w=0;w<4;++w){U word=0;for(unsigned j=0;j<16;++j){unsigned pos=w*16+j;word|=U(uint8_t(b[t*8+pos%8][pos/8]))<<(8*j);}memory[0x11000/16+4*t+w]=word;}
 }
 dma(0,0x10000,4,8,128,0,8);dma(0,0x11000,4,4,64,64,4);
 d.s_load_valid=1;d.s_load_bank=0;d.s_load_rows=8;d.s_load_tiles=4;
 d.s_load_a_wide=0;d.s_load_b_wide=0;d.s_load_reuse_b=0;d.s_load_a_base=0;d.s_load_b_base=64;
 d.eval();need(d.s_load_ready,"feeder unavailable");tick();d.s_load_valid=0;
 // An independent ordinary-port refill competes with the real wide feeder.
 dma_start(0,0x10000,1,32,512,512,32);
 unsigned timeout=0;while(!d.s_done_valid){tick();need(++timeout<10000,"feeder timeout");}
 need(!d.s_done_error,"feeder descriptor rejected");d.s_done_take=1;tick();d.s_done_take=0;dma_finish();
 command('m',4,0,1);
 command('m',10,0,U(4)|(U(5)<<4)|(U(n)<<8)|(U(tiles)<<12)|(U(rows)<<15));
 begin_t(32);
 for(unsigned r=0;r<rows;++r)for(unsigned p=0;p<4;++p){
  U value=command('m',3,r*8+p);
  for(unsigned h=0;h<2;++h){unsigned c=p*2+h;int64_t expected=0;for(unsigned j=0;j<k;++j)expected+=int64_t(a[r][j])*b[j][c];need(int64_t(value>>(64*h))==expected,"M dot product mismatch");}
  write_t(4*r+p,value);
 }
 commit_t();dma(2,0x14000,8,4,80,0,4);release_t();
 for(unsigned r=0;r<8;++r){for(unsigned p=0;p<4;++p){U word=memory[0x14000/16+5*r+p];for(unsigned h=0;h<2;++h){unsigned c=2*p+h;int64_t expected=0;for(unsigned j=0;j<k;++j)expected+=int64_t(a[r][j])*b[j][c];need(int64_t(word>>(64*h))==expected,"T/external matrix result mismatch");}}}
 measure.finish(1280,512);
}
static uint16_t exp_reference(int diff){
 if(diff< -16384)return 0;if(diff>=0)return 32768;
 unsigned t=diff+16384,i=t/16,f=t%16;
 int lo=std::llrint(std::exp(-16.+i/64.)*32768.),hi=std::llrint(std::exp(-16.+(i+1)/64.)*32768.);
 return lo+int(rne(I(hi-lo)*f,4));
}
static void softmax(unsigned length){
 Measure measure("N_softmax_"+std::to_string(length));
 std::vector<int16_t> input(length);std::vector<uint16_t> ex(length);
 for(auto&x:input)x=int(rng()%8193)-4096;
 unsigned words=(length+7)/8;
 for(unsigned w=0;w<words;++w){U value=0;for(unsigned j=0;j<8&&8*w+j<length;++j)value|=U(uint16_t(input[8*w+j]))<<(16*j);memory[0x20000/16+w]=value;}
 command('n',0,0,0,0);
 constexpr unsigned window=256;
 for(unsigned offset=0;offset<words;offset+=window){unsigned count=std::min(window,words-offset);dma(0,0x20000+offset*16,1,count,count*16,0,count);
  for(unsigned w=0;w<count;++w){unsigned valid=std::min(8u,length-(offset+w)*8);command('n',1,valid,cpu(false,w));}}
 command('n',2,0);
 for(unsigned offset=0;offset<words;offset+=window){unsigned count=std::min(window,words-offset);dma(0,0x20000+offset*16,1,count,count*16,0,count);
  for(unsigned w=0;w<count;++w){unsigned valid=std::min(8u,length-(offset+w)*8);U result=command('n',3,valid,cpu(false,w));cpu(true,w,result);}
  dma(1,0x40000+offset*16,1,count,count*16,0,count);}
 command('n',4,0);
 int maximum=*std::max_element(input.begin(),input.end());uint64_t sum=0;
 for(unsigned j=0;j<length;++j){ex[j]=exp_reference(int(input[j])-maximum);sum+=ex[j];}
 uint64_t factor=(uint64_t(1)<<44)/sum;
 for(unsigned offset=0;offset<words;offset+=window){unsigned count=std::min(window,words-offset);dma(0,0x40000+offset*16,1,count,count*16,0,count);begin_t(count);
  for(unsigned w=0;w<count;++w){unsigned valid=std::min(8u,length-(offset+w)*8);U raw=cpu(false,w);for(unsigned j=0;j<valid;++j)need(uint16_t(raw>>(16*j))==ex[8*(offset+w)+j],"N exponential reference mismatch");U result=command('n',6,valid,raw);write_t(w,result);}
  commit_t();dma(2,0x60000+offset*16,1,count,count*16,0,count);release_t();}
 for(unsigned j=0;j<length;++j)need(uint16_t(memory[0x60000/16+j/8]>>(16*(j%8)))==uint16_t(rne(I(ex[j])*factor,30)),"external Softmax mismatch");
 measure.finish(words*48,words*32);
}
static U half(const Row&r,unsigned p){U value=0;for(unsigned j=0;j<4;++j)value|=U(uint32_t(r[4*p+j]))<<(32*j);return value;}
static void stress(){
 Measure measure("DMA_random_2D_and_full_S");uint64_t before=reads;
 for(unsigned trial=0;trial<25;++trial){
  unsigned rows=trial==24?1:1+rng()%7,cols=trial==24?1024:1+rng()%17;
  unsigned ss=trial==24?1024:cols+rng()%9,es=cols+(trial==24?0:rng()%11);
  unsigned base=trial==24?0:rng()%(1024-((rows-1)*ss+cols)+1);
  std::vector<U> expected(rows*cols);
  U guard=random_word();for(unsigned w=0;w<rows*es;++w)memory[0x100000/16+w]=guard;
  for(unsigned r=0;r<rows;++r)for(unsigned c=0;c<cols;++c){U value=random_word();expected[r*cols+c]=value;memory[0xe0000/16+r*es+c]=value;}
  dma(0,0xe0000,rows,cols,16*es,base,ss);
  dma(1,0x100000,rows,cols,16*es,base,ss);
  for(unsigned r=0;r<rows;++r){for(unsigned c=0;c<cols;++c)need(memory[0x100000/16+r*es+c]==expected[r*cols+c],"random/full S transfer mismatch");for(unsigned c=cols;c<es;++c)need(memory[0x100000/16+r*es+c]==guard,"random row gap overwritten");}
 }
 measure.finish((reads-before)*16,(reads-before)*16);
}
static void recurrent(unsigned mode,unsigned n){
 Measure measure(std::string(mode?"R_SSM_":"R_GDN_")+std::to_string(n));
 std::vector<Row> old(n),next(n);std::vector<int16_t> key(n),query(n);Row x{},inject{},skip{},error{},out{};
 const uint32_t decay=0x60000000,beta=0x50000000,owner=0x156,epoch=2,pos=17;
 for(auto&row:old)for(auto&value:row)value=int(rng()%20001)-10000;
 for(auto&v:key)v=int(rng()%2049)-1024;for(auto&v:query)v=int(rng()%2049)-1024;
 for(unsigned l=0;l<8;++l){x[l]=int(rng()%10001)-5000;inject[l]=int(rng()%4001)-2000;skip[l]=1024*int(l+1);}
 for(unsigned r=0;r<n;++r)for(unsigned p=0;p<2;++p)memory[0x80000/16+2*r+p]=half(old[r],p);
 dma(0,0x80000,1,2*n,32*n,0,2*n);
 command('r',0,0,U(n)|(U(owner)<<9)|(U(epoch)<<41)|(U(pos)<<73));
 for(unsigned r=0;r<n;++r)for(unsigned p=0;p<2;++p)command('r',1,2*r+p,cpu(false,2*r+p));
 for(unsigned chunk=0;chunk<(n+7)/8;++chunk){U k=0,q=0;for(unsigned j=0;j<8&&chunk*8+j<n;++j){k|=U(uint16_t(key[chunk*8+j]))<<(16*j);q|=U(uint16_t(query[chunk*8+j]))<<(16*j);}command('r',2,chunk,k);command('r',3,chunk,q);}
 for(unsigned p=0;p<2;++p){command('r',4,p,half(x,p));command('r',4,p+2,half(inject,p));command('r',5,p+1,half(skip,p));}
 command('r',5,0,U(decay)|(U(beta)<<32));
 if(mode){Row factor;factor.fill(decay);for(unsigned r=0;r<n;++r)for(unsigned p=0;p<2;++p)command('r',15,2*r+p,half(factor,p));}
 std::array<I,8> dot{};
 for(unsigned r=0;r<n;++r)for(unsigned l=0;l<8;++l){next[r][l]=int32_t(rne(I(old[r][l])*decay,31));dot[l]+=I(next[r][l])*key[r];}
 for(unsigned l=0;l<8;++l)error[l]=int32_t(rne((I(x[l])-rne(dot[l],14))*beta,31));
 dot.fill(0);
 for(unsigned r=0;r<n;++r)for(unsigned l=0;l<8;++l){next[r][l]+=int32_t(rne(I(mode?inject[l]:error[l])*key[r],14));dot[l]+=I(next[r][l])*query[r];}
 for(unsigned l=0;l<8;++l)out[l]=int32_t(rne(dot[l],14)+(mode?rne(I(x[l])*skip[l],16):0));
 command('r',6,0,U(mode)|(U(owner)<<2)|(U(epoch)<<34)|(U(pos)<<66));
 for(unsigned r=0;r<n;++r)for(unsigned p=0;p<2;++p)need(command('r',11,2*r+p)==half(old[r],p),"R old state modified before commit");
 begin_t(2);for(unsigned p=0;p<2;++p){U value=command('r',12,p);need(value==half(out,p),"R output reference mismatch");write_t(p,value);}commit_t();dma(2,0xc0000,1,2,32,0,2);release_t();
 command('r',7,0,U(owner+1)|(U(epoch)<<32)|(U(pos)<<64)|(U(pos+1)<<96),0,true);
 command('r',7,0,U(owner)|(U(epoch)<<32)|(U(pos)<<64)|(U(pos+1)<<96));
 for(unsigned r=0;r<n;++r)for(unsigned p=0;p<2;++p)cpu(true,2*r+p,command('r',11,2*r+p));
 dma(1,0xa0000,1,2*n,32*n,0,2*n);
 for(unsigned r=0;r<n;++r)for(unsigned p=0;p<2;++p)need(memory[0xa0000/16+2*r+p]==half(next[r],p),"external R state reference mismatch");
 for(unsigned p=0;p<2;++p)need(memory[0xc0000/16+p]==half(out,p),"external R output mismatch");
 measure.finish(n*32,n*32+32);
}
int main(int argc,char**argv){try{
 Verilated::commandArgs(argc,argv);dut=std::make_unique<Vexternal_memory_fixture>();reset();
 for(unsigned setting=0;setting<4;++setting){
  rng.seed(156);bus_rng.seed(1561);hold_rng.seed(1562);
  latency=setting==0||setting==3?1:setting==1?7:31;
  gap=setting==0||setting==3?0:setting==1?3:2;interval=setting==3?4:1;
  transfers();stress();matrix();softmax(257);softmax(8193);
  recurrent(0,17);recurrent(1,17);recurrent(0,256);recurrent(1,256);
 }
 // Coordinated reset explicitly flushes both DMA and platform outstanding state.
 dma_start(0,0x10000,1,32,512,0,32);for(unsigned i=0;i<4;++i)tick();reset();
 dma(0,0x10000,1,32,512,0,32);
 // Descriptor/T length mismatch is reported; the unreleased T lease requires
 // coordinated reset, since a committed T payload cannot be revoked.
 begin_t(3);for(unsigned i=0;i<3;++i)write_t(i,random_word());commit_t();
 dma(2,0x18000,1,2,32,0,2,true);need(d.t_busy&&!d.t_release_ready,"short descriptor silently released T");reset();
 need(!d.t_protocol_error&&pending.empty(),"final state not quiescent");
 std::cout<<"{\"passed\":true,\"initial_reset\":"<<Verilated::randReset()<<",\"initial_seed\":"<<Verilated::randSeed()<<",\"checks\":"<<checks<<",\"cycles\":"<<cycles<<",\"external_pending_peak\":"<<peak<<",\"DMA_reserved_peak\":"<<reserve_peak<<",\"T_payload_peak_words\":"<<t_peak<<",\"reports\":[";
 for(unsigned i=0;i<reports.size();++i){if(i)std::cout<<",";std::cout<<reports[i];}std::cout<<"]}\n";dut.reset();return 0;
}catch(const std::exception&e){std::cerr<<e.what()<<" at cycle "<<cycles<<"\n";dut.reset();return 1;}}
