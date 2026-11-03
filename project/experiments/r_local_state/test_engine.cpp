#include "Vr_stream_local.h"
#include "verilated.h"
#include <array>
#include <vector>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <algorithm>
using U=__uint128_t;
static void ck(bool b,const char*s){if(!b)throw std::runtime_error(s);}
template<class T>std::vector<T> readv(std::ifstream&f,size_t n){std::vector<T>a(n);f.read(reinterpret_cast<char*>(a.data()),n*sizeof(T));ck(bool(f),"truncated corpus");return a;}
int main(int argc,char**argv){try{Verilated::commandArgs(argc,argv);ck(argc>=2,"usage r_stream corpus");std::ifstream f(argv[1],std::ios::binary);auto h=readv<uint32_t>(f,8);unsigned mode=h[0],n=h[1],layers=h[2],tokens=h[3],flags=h[5];Vr_stream_local d;uint64_t checks=0,cycles=0;
 auto tick=[&](){d.clk=0;d.eval();d.clk=1;d.eval();d.clk=0;d.eval();++cycles;};d.reset=1;d.load_valid=0;d.cmd_valid=0;d.rsp_ready=0;d.rd_index=0;d.rd_bank=0;d.rd_valid=0;d.rd_rsp_ready=0;tick();tick();d.reset=0;tick();
 auto load=[&](unsigned target,unsigned index,U data){for(unsigned w=0;!d.load_ready;++w){ck(w<100,"load wait");tick();}d.load_valid=1;d.load_target=target;d.load_index=index;for(unsigned j=0;j<4;++j){d.load_data[j]=uint32_t(data);data>>=32;}tick();d.load_valid=0;};
 auto vec32=[&](unsigned target,unsigned index,const std::vector<int32_t>&a,unsigned start,unsigned count){for(unsigned i=0;i<count;i+=4){U v=0;for(unsigned j=0;j<4&&i+j<count;++j)v|=U(uint32_t(a[start+i+j]))<<(32*j);load(target,index+i/4,v);}};
 auto vec16=[&](unsigned target,const std::vector<int16_t>&a,unsigned start,unsigned count){for(unsigned i=0;i<count;i+=8){U v=0;for(unsigned j=0;j<8&&i+j<count;++j)v|=U(uint16_t(a[start+i+j]))<<(16*j);load(target,i/8,v);}};
 auto command=[&](unsigned op,unsigned rows,unsigned role,bool clear){d.cmd_valid=1;d.cmd_op=op;d.cmd_rows=rows;d.cmd_role=role;d.cmd_clear=clear;d.cmd_mode=mode;for(unsigned w=0;!d.cmd_ready;++w){ck(w<100,"command wait");tick();}tick();d.cmd_valid=0;unsigned latency=0;while(!d.rsp_valid){tick();ck(++latency<1000,"pass timeout");}unsigned expected=op<=3?rows+2:op==4?4:op==5?(mode==1?5:2):op==6?6:0;ck(latency>=expected,"response before original minimal latency");bool error=d.rsp_error;d.rsp_ready=1;tick();d.rsp_ready=0;return error;};
 auto readbank=[&](unsigned bank,std::vector<int32_t>&v,unsigned start,unsigned count){
  d.rd_bank=bank;
  for(unsigned i=0;i<count;i+=4){
   d.rd_index=i/4;d.rd_valid=1;d.eval();
   for(unsigned w=0;!d.rd_ready;++w){ck(w<100,"read request wait");tick();}
   tick();d.rd_valid=0;d.eval();
   for(unsigned w=0;!d.rd_rsp_valid;++w){ck(w<100,"read response wait");tick();}
   std::array<uint32_t,4> hold;for(unsigned j=0;j<4;++j)hold[j]=d.rd_data[j];
   for(unsigned w=0;w<(i/4)%3;++w){tick();ck(d.rd_rsp_valid,"response lost under backpressure");for(unsigned j=0;j<4;++j)ck(hold[j]==d.rd_data[j],"response changed under backpressure");}
   for(unsigned j=0;j<4&&i+j<count;++j)v[start+i+j]=int32_t(d.rd_data[j]);checks+=4;
   d.rd_rsp_ready=1;tick();d.rd_rsp_ready=0;d.eval();
  }
 };
 std::vector<std::vector<int32_t>>states;for(unsigned l=0;l<layers;++l)states.push_back(readv<int32_t>(f,n));
 bool resident=layers==1&&n<=TEST_WORDS;unsigned role=0;
 for(unsigned t=0;t<tokens;++t)for(unsigned layer=0;layer<layers;++layer){
  auto k=readv<int16_t>(f,n/8),q=readv<int16_t>(f,n/8);auto v=readv<int32_t>(f,24);auto factors=readv<uint32_t>(f,mode==1?n:0);auto taps=readv<int16_t>(f,mode==2?32:0);auto status=readv<uint32_t>(f,2);auto out=readv<int32_t>(f,8),next=readv<int32_t>(f,n);
  if(flags&32)std::fill(states[layer].begin(),states[layer].end(),0);
  if(!resident)role=0;command(7,0,role,false);vec32(4,0,v,0,24);load(5,0,U(h[6])|(U(h[7])<<32));
  std::vector<int32_t>candidate(n);
  if(mode==2){vec32(6,0,states[layer],0,24);vec16(7,taps,0,32);command(6,0,role,true);}
  else{
   for(unsigned start=0;start<n;start+=TEST_WORDS){unsigned words=std::min(unsigned(TEST_WORDS),n-start),rows=words/8;
    if(!resident||!t||flags&32)vec32(role,0,states[layer],start,words);
    if(mode==1){std::vector<int32_t>factors32(factors.begin(),factors.end());vec32(1-role,0,factors32,start,words);}
    vec16(2,k,start/8,rows);command(0,rows,role,false);if(mode==0)command(1,rows,role,start==0);readbank(1-role,candidate,start,words);
   }
   if(mode==0)command(4,0,role,false);
   for(unsigned start=0;start<n;start+=TEST_WORDS){unsigned words=std::min(unsigned(TEST_WORDS),n-start),rows=words/8;
    if(!resident)vec32(1-role,0,candidate,start,words);
    vec16(2,k,start/8,rows);vec16(3,q,start/8,rows);command(2,rows,role,false);command(3,rows,role,start==0);readbank(1-role,candidate,start,words);
   }
  }
  bool error=command(5,0,role,false);ck(error==!bool(status[0]),"stream overflow mismatch");
  if(status[0])for(unsigned l=0;l<8;++l){uint64_t got=uint64_t(d.rsp_data[2*l])|(uint64_t(d.rsp_data[2*l+1])<<32);ck(int32_t(got)==out[l],"stream output mismatch");++checks;}
  if(status[1]){if(mode==2){candidate=states[layer];std::copy(v.begin(),v.begin()+8,candidate.begin());std::copy(states[layer].begin(),states[layer].begin()+16,candidate.begin()+8);}ck(candidate==next,"stream candidate state mismatch");states[layer]=candidate;if(resident)role=1-role;}
  else{ck(states[layer]==next,"rollback changed old state");if(resident&&mode!=2){std::vector<int32_t>observed(n);readbank(role,observed,0,n);ck(observed==states[layer],"physical old bank changed");}}
 }
 ck(f.peek()==std::char_traits<char>::eof(),"trailing input");std::cout<<"{\"passed\":true,\"words\":"<<TEST_WORDS<<",\"checks\":"<<checks<<",\"cycles\":"<<cycles<<"}\n";return 0;
}catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}}
