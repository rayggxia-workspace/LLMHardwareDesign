// End-to-end cycle driver. Arithmetic and global transaction logic are actual
// frozen/new RTL via Verilator. S is a signal-level, RTL-cross-checked model.
#include "Vresearch_top.h"
#include "verilated.h"
#include "s_port.hpp"
#include <fstream>
#include <vector>
#include <array>
#include <map>
#include <string>
#include <iostream>
#include <stdexcept>
#include <algorithm>
#include <cstdint>
#include <functional>
using U=__uint128_t;using Words=std::vector<uint32_t>;using Lanes=std::array<int64_t,8>;
static void need(bool b,const char*s){if(!b)throw std::runtime_error(s);}
template<class T>static std::vector<T>readv(std::ifstream&f,size_t n){std::vector<T>a(n);f.read(reinterpret_cast<char*>(a.data()),n*sizeof(T));need(bool(f),"truncated corpus");return a;}
template<class W>static void put128(W&to,U v){for(unsigned i=0;i<4;++i){to[i]=uint32_t(v);v>>=32;}}
template<class W>static U get128(const W&v){U a=0;for(int i=3;i>=0;--i)a=a<<32|v[i];return a;}
static U packet(const Words&v,unsigned start,unsigned count){U p=0;for(unsigned i=0;i<4&&i<count;++i)p|=U(v[start+i])<<(32*i);return p;}
static Lanes from32(const Words&v,unsigned start=0){Lanes a{};for(unsigned i=0;i<8;++i)a[i]=int32_t(v[start+i]);return a;}
static Words to32(const Lanes&v){Words a;for(auto x:v)a.push_back(uint32_t(x));return a;}
static Words packed16(const std::vector<int16_t>&v){Words a((v.size()+1)/2);for(unsigned i=0;i<v.size();++i)a[i/2]|=uint32_t(uint16_t(v[i]))<<(16*(i%2));return a;}

struct Experiment:sc_module{
 sc_clock clk{"clk",sc_time(1,SC_NS)};SPort s{"S"};Vresearch_top d;
 std::string file,output,policy;unsigned arch,cap,latency,bw;bool passed=false,bad=false;
 uint64_t cycle=0,checks=0,dram_read=0,dram_write=0,dram_peak=0,s_alloc_peak=0,local_read=0,local_write=0;
 uint64_t wide_unsigned=0,wide_signed=0,wide_short=0,m_s8_physical=0,m_s8_useful=0,merge96=0,finish65=0,r_mul=0;
 uint64_t tiles=0,loads=0,commits=0,aborts=0,control_packets=0,max_write_outstanding=0;
 std::map<std::string,uint64_t>stages,traffic,ports;Words dram;
 unsigned ctx=0,mode=0,elements=0,contexts=0,tokens=0,flags=0,role=0,current_tile=0;
 uint32_t decay=0,beta=0;std::vector<uint32_t>epochs,positions;std::vector<bool>versions,ddr_versions;
 bool keep=false,cache=false;unsigned tile_words=0,cache_words=0;
 std::vector<int>slot;
 SC_HAS_PROCESS(Experiment);
 Experiment(sc_module_name n,std::string input,std::string dest,unsigned a,unsigned c,unsigned l,unsigned b,std::string pol):sc_module(n),file(input),output(dest),policy(pol),arch(a),cap(c),latency(l),bw(b){s.clk(clk);SC_THREAD(run);}
 void settle(){d.clk=0;d.eval();}
 void step(const char*stage="control"){settle();wait(clk.posedge_event());wait(SC_ZERO_TIME);wait(SC_ZERO_TIME);d.clk=1;d.eval();++cycle;++stages[stage];}
 void waitn(unsigned n,const char*stage){for(unsigned i=0;i<n;++i)step(stage);}
 U s_access(unsigned address,bool write,U data=0){
  need(address<1024,"S address overflow");s.req=true;s.wr=write;s.addr=address;sc_biguint<128>v;for(unsigned i=0;i<4;++i)v.range(i*32+31,i*32)=uint32_t(data>>(32*i));s.din=v;s.take=true;
  wait(SC_ZERO_TIME);wait(SC_ZERO_TIME);while(!s.ready.read())step("S_port_wait");step("S_write_read");need(s.valid.read(),"S missing response");U result=0;for(int i=3;i>=0;--i)result=result<<32|s.dout.read().range(i*32+31,i*32).to_uint();s.req=false;ports[write?"S_narrow_write":"S_narrow_read"]+=16;return result;
 }
 void reserve(unsigned bytes){need(bytes<=16384,"S capacity exceeded");s_alloc_peak=std::max(s_alloc_peak,uint64_t(bytes));}
 void r_load(unsigned target,unsigned index,U p){
  d.r_load_target=target;d.r_load_index=index;put128(d.r_load_data,p);d.r_load_valid=1;settle();while(!d.r_load_ready)step("R_input_wait");step("R_load");d.r_load_valid=0;ports["R_load128"]+=16;
 }
 bool r_command(unsigned op,unsigned rows=0,bool clear=false){
  d.r_cmd_op=op;d.r_cmd_rows=rows;d.r_cmd_role=role;d.r_cmd_clear=clear;d.r_cmd_mode=mode;d.r_cmd_valid=1;settle();while(!d.r_cmd_ready)step("R_command_wait");step("R_command");d.r_cmd_valid=0;unsigned n=0;while(!d.r_rsp_valid){step("R_execute");need(++n<2000,"R command timeout");}
  unsigned expected=op<=3?rows+2:op==4?4:op==5?(mode==1?5:2):op==6?6:0;need(n==expected,"uncalibrated R latency");
  bool error=d.r_rsp_error;d.r_rsp_ready=1;step("R_response");d.r_rsp_ready=0;ports["R_command"]+=16;ports["R_response512"]+=64;++control_packets;return error;
 }
 U r_read(unsigned bank,unsigned index){d.r_rd_bank=bank;d.r_rd_index=index;settle();U v=get128(d.r_rd_data);step("R_read");ports["R_read128"]+=16;return v;}
 U a_command(unsigned op,unsigned index,U data,bool*error=nullptr){
  d.a_cmd_valid=1;d.a_cmd_op=op;d.a_cmd_index=index;put128(d.a_cmd_data,data);settle();while(!d.a_cmd_ready)step("A0_command_wait");step("A0_command");d.a_cmd_valid=0;unsigned n=0;while(!d.a_rsp_valid){step("A0_execute");need(++n<10000,"A0 timeout");}if(error)*error=d.a_rsp_error;else need(!d.a_rsp_error,"unexpected A0 protocol error");U v=get128(d.a_rsp_data);d.a_rsp_ready=1;step("A0_response");d.a_rsp_ready=0;ports["A0_command128"]+=16;ports["A0_response128"]+=16;++control_packets;return v;
 }
 bool txn(unsigned op,uint32_t next=0,bool wrong=false){
  d.t_cmd_valid=1;d.t_cmd_op=op;d.t_cmd_context=ctx;d.t_cmd_owner=ctx+1+unsigned(wrong);d.t_cmd_epoch=epochs[ctx];d.t_cmd_position=positions[ctx];d.t_cmd_next=next;d.t_dma_idle=d.t_outstanding==0;settle();while(!d.t_cmd_ready)step("transaction_wait");step("transaction");d.t_cmd_valid=0;need(d.t_rsp_valid,"missing transaction response");bool error=d.t_rsp_error;d.t_rsp_ready=1;step("transaction");d.t_rsp_ready=0;ports["transaction128"]+=32;++control_packets;max_write_outstanding=std::max(max_write_outstanding,uint64_t(d.t_outstanding));return error;
 }
 Lanes wide(const Lanes&a,const Lanes&b,unsigned kind){
  for(unsigned i=0;i<8;++i){d.c_in_a[i]=uint32_t(a[i]);d.c_in_b[i]=uint32_t(b[i]);}d.c_in_kind=kind;d.c_in_valid=1;settle();while(!d.c_in_ready)step("M_busy_wait");step("M_dispatch");d.c_in_valid=0;unsigned n=0;while(!d.c_out_valid){step("M_wide");need(++n<2000,"wide timeout");}need(n==(kind==0?481:801),"uncalibrated M latency");need(!d.c_out_error,"wide reconstruction overflow");Lanes out;for(unsigned i=0;i<8;++i)out[i]=int64_t(uint64_t(d.c_out_data[2*i])|(uint64_t(d.c_out_data[2*i+1])<<32));unsigned terms=kind==0?15:25;need(d.c_commands==terms,"M count mismatch");m_s8_physical+=64*terms;m_s8_useful+=8*terms;merge96+=8*terms;ports["M_A128"]+=16*terms;ports["M_B512"]+=64*terms;ports["M_commands64"]+=40*terms;ports["M_responses128"]+=80*terms;ports["wide256_input"]+=64;ports["wide512_output"]+=64;
  d.c_out_ready=1;step("M_response");d.c_out_ready=0;if(kind==0)wide_short+=8;else if(kind==1)wide_signed+=8;else wide_unsigned+=8;return out;
 }
 Lanes finish(const Lanes&a,const Lanes&b,unsigned op,unsigned shift){
  for(unsigned i=0;i<8;++i){d.f_in_a[2*i]=uint32_t(a[i]);d.f_in_a[2*i+1]=uint64_t(a[i])>>32;d.f_in_b[2*i]=uint32_t(b[i]);d.f_in_b[2*i+1]=uint64_t(b[i])>>32;}d.f_in_op=op;d.f_in_shift=shift;d.f_in_valid=1;settle();while(!d.f_in_ready)step("finish_wait");step("finish_dispatch");d.f_in_valid=0;unsigned n=0;while(!d.f_out_valid){step("finish");need(++n<20,"finish timeout");}need(n==8,"uncalibrated finish latency");bad|=bool(d.f_out_error);Lanes out;for(unsigned i=0;i<8;++i)out[i]=int64_t(uint64_t(d.f_out_data[2*i])|(uint64_t(d.f_out_data[2*i+1])<<32));d.f_out_ready=1;step("finish_response");d.f_out_ready=0;finish65+=8;ports["finish512_input"]+=128;ports["finish512_output"]+=64;return out;
 }
 // Explicit DDR bursts, one 128-bit response buffer, backpressure to source.
 Words dma_read(unsigned address,unsigned count,const char*kind,std::function<void(unsigned,U,unsigned)>consume={}){
  need(bool(consume)||count<=24,"unbounded controller read buffer");
  need(address+count<=dram.size(),"DRAM read bounds");Words result;result.reserve(count);traffic[std::string(kind)+"_read"]+=count*4;dram_read+=count*4;
  for(unsigned base=0;base<count;base+=256){unsigned length=std::min(256u,count-base);step("DMA_command");waitn(latency,"DRAM_latency");
   for(unsigned p=0;p<length;p+=4){unsigned n=std::min(4u,length-p);waitn((n*4+bw-1)/bw,"DRAM_data");U v=packet(dram,address+base+p,n);ports["DRAM128"]+=16;s_access(928,true,v);U held=s_access(928,false);if(consume)consume(base+p,held,n);else for(unsigned j=0;j<n;++j)result.push_back(uint32_t(held>>(32*j)));}
   step("DMA_response");
  }return result;
 }
 void dma_write_stream(unsigned address,unsigned count,const char*kind,std::function<U(unsigned,unsigned)>produce){
  need(address+count<=dram.size(),"DRAM streaming write bounds");traffic[std::string(kind)+"_write"]+=count*4;dram_write+=count*4;
  for(unsigned base=0;base<count;base+=256){unsigned length=std::min(256u,count-base);need(!txn(2),"stream write issue denied");step("DMA_command");waitn(latency,"DRAM_latency");
   for(unsigned p=0;p<length;p+=4){unsigned n=std::min(4u,length-p);U v=produce(base+p,n);s_access(928,true,v);U held=s_access(928,false);waitn((n*4+bw-1)/bw,"DRAM_data");ports["DRAM128"]+=16;for(unsigned j=0;j<n;++j)dram[address+base+p+j]=uint32_t(held>>(32*j));}
   step("DMA_response");need(!txn(3),"stream write ack denied");
  }
 }
 void dma_to_r(unsigned address,unsigned count,const char*kind,unsigned target){dma_read(address,count,kind,[&](unsigned p,U v,unsigned){r_load(target,p/4,v);});}
 void dma_to_s(unsigned address,unsigned count,const char*kind,unsigned offset){dma_read(address,count,kind,[&](unsigned p,U v,unsigned){s_access((offset+p)/4,true,v);});}
 void dma_write(unsigned address,const Words&v,const char*kind){
  need(address+v.size()<=dram.size(),"DRAM write bounds");traffic[std::string(kind)+"_write"]+=v.size()*4;dram_write+=v.size()*4;
  for(unsigned base=0;base<v.size();base+=256){unsigned length=std::min(256u,unsigned(v.size())-base);need(!txn(2),"write issue denied");step("DMA_command");waitn(latency,"DRAM_latency");
   for(unsigned p=0;p<length;p+=4){unsigned n=std::min(4u,length-p);s_access(928,true,packet(v,base+p,n));U held=s_access(928,false);waitn((n*4+bw-1)/bw,"DRAM_data");ports["DRAM128"]+=16;for(unsigned j=0;j<n;++j)dram[address+base+p+j]=uint32_t(held>>(32*j));}
   step("DMA_response");need(!txn(3),"write ack denied");
  }
 }
 unsigned address(bool candidate)const{return(ctx*2+unsigned(ddr_versions[ctx]^candidate))*elements;}
 void send_r(unsigned target,const Words&v){for(unsigned i=0;i<v.size();i+=4)r_load(target,i/4,packet(v,i,std::min(4u,unsigned(v.size())-i)));}
 Words read_r(unsigned bank,unsigned n){Words result;for(unsigned i=0;i<n;i+=4){U p=r_read(bank,i/4);for(unsigned j=0;j<4&&i+j<n;++j)result.push_back(uint32_t(p>>(32*j)));}return result;}
 Words s_words(unsigned offset,unsigned n){Words v;for(unsigned i=0;i<n;i+=4){U p=s_access((offset+i)/4,false);for(unsigned j=0;j<4&&i+j<n;++j)v.push_back(uint32_t(p>>(32*j)));}return v;}
 void put_s_words(unsigned offset,const Words&v){need(offset+v.size()<=3712,"S state overlaps bounded DMA/control workspace");for(unsigned i=0;i<v.size();i+=4)s_access((offset+i)/4,true,packet(v,i,std::min(4u,unsigned(v.size())-i)));}
 // Physical cache page exchange carries BOTH versions, never loses old state.
 void exchange(unsigned tile){
  if(tile==current_tile)return;need(cache&&arch==1&&slot[tile]>=0,"invalid cache page");unsigned where=slot[tile];
  for(unsigned bank=0;bank<2;++bank)for(unsigned i=0;i<tile_words;i+=4){unsigned loc=where+bank*tile_words+i;U incoming=s_access(loc/4,false);U outgoing=r_read(bank,i/4);r_load(bank,i/4,incoming);s_access(loc/4,true,outgoing);}
  slot[current_tile]=where;slot[tile]=-1;current_tile=tile;
 }
 void initialize_cache(){
  reserve(cache_words*4+1536);unsigned chunks=(elements+tile_words-1)/tile_words;slot.assign(chunks,-1);current_tile=0;
  for(unsigned t=0;t<chunks;++t){if(arch==1&&mode!=2&&t==0)dma_to_r(address(false)+t*tile_words,tile_words,"state",role);else{unsigned offset=arch==1&&mode!=2?(t-1)*2*tile_words:t*tile_words;slot[t]=offset;dma_to_s(address(false)+t*tile_words,tile_words,"state",offset+role*(arch==1&&mode!=2?tile_words:elements));}}
  ++loads;
 }
 void run();
};

void Experiment::run(){try{
 std::ifstream input(file,std::ios::binary);need(bool(input),"input absent");auto h=readv<uint32_t>(input,8);mode=h[0];elements=h[1];contexts=h[2];tokens=h[3];flags=h[5];decay=h[6];beta=h[7];need(mode<=2&&contexts<=24&&elements%8==0,"descriptor rejected");
 if(arch==0&&mode!=2&&elements>2048){std::ofstream out(output);out<<"{\"status\":\"UNSUPPORTED_ORIGINAL_CAPACITY\"}\n";passed=true;sc_stop();return;}
 unsigned cursor=2*contexts*elements;auto alloc=[&](unsigned n){unsigned base=cursor;cursor=(cursor+n+3)&~3u;return base;};
 unsigned k_addr=alloc((elements/8+1)/2),q_addr=alloc((elements/8+1)/2),factor_addr=alloc(mode==1?elements:0),v_addr=alloc(28),tap_addr=alloc(16);dram.resize(cursor);dram_peak=dram.size()*4;
 for(unsigned c=0;c<contexts;++c){auto state=readv<int32_t>(input,elements);for(unsigned i=0;i<elements;++i)dram[c*2*elements+i]=flags&32?0:uint32_t(state[i]);}
 epochs.assign(contexts,0);positions.assign(contexts,17);versions.assign(contexts,false);ddr_versions.assign(contexts,false);
 s.reset=true;d.reset=1;d.t_dma_idle=1;s.take=true;s.wide_take=true;step("reset");step("reset");s.reset=false;d.reset=0;
 for(ctx=0;ctx<contexts;++ctx){need(!txn(0),"context creation failed");s_access(992+ctx,true,U(ctx+1)|(U(17)<<64));}ctx=0;
 tile_words=arch==2?std::min(256u,elements):std::min(cap,elements);
 if(mode==2)tile_words=elements;
 cache=policy=="cache"&&arch!=0&&((arch==1?2*(elements-tile_words):2*elements+(mode==1?elements:0)+elements/8)*4+1536<=16384);
 if(arch==1&&elements<=cap&&mode!=2)cache=false;
 if(mode==2)cache=policy=="cache"&&arch!=0;
 cache_words=arch==1?2*(elements-tile_words):2*elements+(mode==1?elements:0)+elements/8;
 if(mode==2)cache_words=2*elements+32;
 reserve(cache?cache_words*4+1536:arch==2?(2*tile_words+tile_words/8)*4+1536:1536);
 keep=contexts==1&&(cache||(mode!=2&&arch!=2&&elements<=cap)||mode==2&&arch==0);
 bool initialized=false;uint64_t start=cycle;std::ofstream trace(output+".trace.csv");trace<<"token,context,start_cycle,end_cycle,mathematical_ok,committed\n";
 auto install=[&](unsigned base,const Words&v){need(base+v.size()<=dram.size(),"fixture installation bounds");std::copy(v.begin(),v.end(),dram.begin()+base);};
 auto load_a=[&](unsigned op,unsigned index,unsigned base,unsigned count,const char*kind){dma_read(base,count,kind,[&](unsigned p,U data,unsigned){a_command(op,index+p/4,data);});};
 auto c_operand=[&](unsigned offset){return from32(s_words(offset,8));};
 auto c_store=[&](unsigned offset,const Lanes&data){put_s_words(offset,to32(data));};
 auto scalar_coeff=[&](unsigned offset,unsigned row){U p=s_access((offset+row/2)/4,false);unsigned half=(row%8);return int16_t(p>>(16*half));};
 auto peek=[&](){Words observed(elements);
  if(arch==0){d.probe_history=mode==2;d.probe_bank=d.probe_role;for(unsigned i=0;i<elements;i+=4){d.probe_index=i/4;settle();U p=get128(d.probe_data);for(unsigned j=0;j<4;++j)observed[i+j]=uint32_t(p>>(32*j));}}
  else if(cache&&arch==2||cache&&mode==2){for(unsigned i=0;i<elements;++i)observed[i]=s.mem[(role*elements+i)/4].range((i%4)*32+31,(i%4)*32).to_uint();}
  else if(arch==1&&mode!=2&&(elements<=cap||cache)){
   for(unsigned i=0;i<elements;i+=4){unsigned tile=i/tile_words,index=i%tile_words;U p;if(elements<=cap||tile==current_tile){d.r_rd_bank=role;d.r_rd_index=index/4;settle();p=get128(d.r_rd_data);}else p=0;
    for(unsigned j=0;j<4;++j){if(elements<=cap||tile==current_tile)observed[i+j]=uint32_t(p>>(32*j));else{unsigned word=slot[tile]+role*tile_words+index+j;observed[i+j]=s.mem[word/4].range((word%4)*32+31,(word%4)*32).to_uint();}}
   }
  }else for(unsigned i=0;i<elements;++i)observed[i]=dram[address(false)+i];return observed;
 };
 for(unsigned token=0;token<tokens;++token)for(ctx=0;ctx<contexts;++ctx){
  uint64_t begin=cycle;bad=false;auto k=readv<int16_t>(input,elements/8),q=readv<int16_t>(input,elements/8);auto signed_v=readv<int32_t>(input,24);Words values(signed_v.begin(),signed_v.end());auto factors=readv<uint32_t>(input,mode==1?elements:0);auto taps=readv<int16_t>(input,mode==2?32:0);auto status=readv<uint32_t>(input,2);auto expected_out=readv<int32_t>(input,8),expected_state=readv<int32_t>(input,elements);
  install(k_addr,packed16(k));install(q_addr,packed16(q));install(v_addr,values);install(v_addr+24,{decay,beta,0,0});if(mode==1)install(factor_addr,factors);if(mode==2)install(tap_addr,packed16(taps));
  need(!txn(1),"global begin failed");
  if(!initialized||!keep){role=0;
   if(arch==0){a_command(0,0,U(mode==2?1:elements/8)|(U(ctx+1)<<9)|(U(epochs[ctx])<<41)|(U(positions[ctx])<<73));role=d.probe_role;if(mode!=2)load_a(1,0,address(false),elements,"state");else load_a(9,0,address(false),24,"history");++loads;}
   else if(cache){initialize_cache();}
   else if(arch==1&&elements<=cap&&mode!=2){dma_to_r(address(false),elements,"state",role);++loads;}
   initialized=true;
  }
  Lanes result{},zero{},input_x{},inject{},skip{};
  if(arch==0){
   load_a(4,0,v_addr,16,"coefficient");load_a(5,0,v_addr+24,4,"coefficient");
   // Skip registers use the separate op5 indices, not op4 scalar slots.
   load_a(5,1,v_addr+16,8,"coefficient");
   if(mode==2)load_a(10,0,tap_addr,16,"coefficient");
   else{load_a(2,0,k_addr,(elements/8+1)/2,"coefficient");load_a(3,0,q_addr,(elements/8+1)/2,"coefficient");if(mode==1)load_a(15,0,factor_addr,elements,"coefficient");}
   bool error=false;a_command(6,0,U(mode)|(U(ctx+1)<<2)|(U(epochs[ctx])<<34)|(U(positions[ctx])<<66),&error);bad=error;
   if(!bad)for(unsigned p=0;p<2;++p){U data=a_command(12,p,0);for(unsigned l=0;l<4;++l)result[p*4+l]=int32_t(data>>(32*l));}
   r_mul+=mode==2?32:(mode==0?4*elements+8:3*elements+8);
  }else if(arch==1){
   r_command(7);dma_to_r(v_addr,24,"coefficient",4);dma_to_r(v_addr+24,4,"coefficient",5);
   if(mode==2){
    if(cache){for(unsigned p=0;p<24;p+=4)r_load(6,p/4,s_access((role*elements+p)/4,false));}
    else dma_to_r(address(false),24,"history",6);
    dma_to_r(tap_addr,16,"coefficient",7);r_command(6);bad=r_command(5);r_mul+=32;
   }else{
    for(unsigned pos=0;pos<elements;pos+=tile_words){unsigned words=std::min(tile_words,elements-pos),rows=words/8;++tiles;
     if(cache)exchange(pos/tile_words);else if(elements>cap)dma_to_r(address(false)+pos,words,"state",role);
     if(mode==1)dma_to_r(factor_addr+pos,words,"coefficient",1-role);
     if(mode==0)dma_to_r(k_addr+pos/16,(rows+1)/2,"coefficient",2);
     r_command(0,rows);if(mode==0)r_command(1,rows,pos==0);
     if(!cache&&elements>cap)dma_write_stream(address(true)+pos,words,"intermediate",[&](unsigned p,unsigned){return r_read(1-role,p/4);});
    }
    if(mode==0)r_command(4);
    for(unsigned pos=0;pos<elements;pos+=tile_words){unsigned words=std::min(tile_words,elements-pos),rows=words/8;++tiles;
     if(cache)exchange(pos/tile_words);else if(elements>cap)dma_to_r(address(true)+pos,words,"intermediate",1-role);
     dma_to_r(k_addr+pos/16,(rows+1)/2,"coefficient",2);dma_to_r(q_addr+pos/16,(rows+1)/2,"coefficient",3);
     r_command(2,rows);r_command(3,rows,pos==0);
     if(!cache&&elements>cap)dma_write_stream(address(true)+pos,words,"state",[&](unsigned p,unsigned){return r_read(1-role,p/4);});
    }
    bad=r_command(5);r_mul+=mode==0?4*elements+8:3*elements+8;
   }
   for(unsigned l=0;l<8;++l)result[l]=int32_t(d.r_rsp_data[2*l]);
  }else{
   Words scv=dma_read(v_addr,24,"coefficient");input_x=from32(scv,0);inject=from32(scv,8);skip=from32(scv,16);dma_read(v_addr+24,4,"coefficient");
   if(mode==2){
    if(!cache)dma_to_s(address(false),24,"history",0);unsigned tap_base=2*elements;dma_to_s(tap_addr,16,"coefficient",tap_base);Lanes dot{};
    for(unsigned j=0;j<4;++j){Lanes a=j==0?input_x:c_operand((cache?role*elements:0)+(j-1)*8),b{};Words tv=s_words(tap_base+j*4,4);for(unsigned l=0;l<8;++l)b[l]=int16_t(tv[l/2]>>(16*(l%2)));dot=finish(wide(a,b,0),dot,2,0);}
    result=finish(dot,zero,0,14);
   }else{
    unsigned span=cache?elements:tile_words,coef=cache?2*elements:tile_words,factor_offset=coef,key_offset=coef+(mode==1?span:0),query_offset=key_offset+span/16;reserve((query_offset+span/16)*4+1536);
    Lanes dot{};for(unsigned pos=0;pos<elements;pos+=span){unsigned words=std::min(span,elements-pos),rows=words/8;++tiles;
     if(!cache)dma_to_s(address(false)+pos,words,"state",0);
     if(mode==1)dma_to_s(factor_addr+pos,words,"coefficient",factor_offset);
     if(mode==0)dma_to_s(k_addr+pos/16,(rows+1)/2,"coefficient",key_offset);
     for(unsigned r=0;r<rows;++r){unsigned old=(cache?role*elements:0)+r*8,shadow=(cache?(1-role)*elements:0)+r*8;Lanes a=c_operand(old),b{};if(mode==1)b=c_operand(factor_offset+r*8);else b.fill(decay);Lanes decayed=finish(wide(a,b,2),zero,0,31);c_store(shadow,decayed);if(mode==0){b.fill(scalar_coeff(key_offset,r));dot=finish(wide(decayed,b,0),dot,2,0);}}
     if(!cache)dma_write_stream(address(true)+pos,words,"intermediate",[&](unsigned p,unsigned){return s_access(p/4,false);});
    }
    Lanes error{};if(mode==0){Lanes pred=finish(dot,zero,0,14),minus=pred;for(auto&x:minus)x=-x;error=finish(input_x,minus,1,0);Lanes b;b.fill(beta);error=finish(wide(error,b,2),zero,0,31);}dot={};
    for(unsigned pos=0;pos<elements;pos+=span){unsigned words=std::min(span,elements-pos),rows=words/8;++tiles;
     if(!cache)dma_to_s(address(true)+pos,words,"intermediate",0);
     dma_to_s(k_addr+pos/16,(rows+1)/2,"coefficient",key_offset);dma_to_s(q_addr+pos/16,(rows+1)/2,"coefficient",query_offset);
     for(unsigned r=0;r<rows;++r){unsigned where=(cache?(1-role)*elements:0)+r*8;Lanes state=c_operand(where),b;b.fill(scalar_coeff(key_offset,r));state=finish(wide(mode==0?error:inject,b,0),state,1,14);c_store(where,state);b.fill(scalar_coeff(query_offset,r));dot=finish(wide(state,b,0),dot,2,0);}
     if(!cache)dma_write_stream(address(true)+pos,words,"state",[&](unsigned p,unsigned){return s_access(p/4,false);});
    }
    result=finish(dot,zero,0,14);if(mode==1)result=finish(wide(input_x,skip,1),result,1,16);
   }
  }
  need(bad==!bool(status[0]),"mathematical error flag mismatch");if(!bad)for(unsigned l=0;l<8;++l){need(int32_t(result[l])==expected_out[l],"end-to-end output mismatch");++checks;}
  // Output payload crosses a bounded 128-bit result link to the consumer.
  if(!bad){ports["result128"]+=32;step("result_link");step("result_link");}
  need(!txn(4,bad?1:0),"compute completion denied");bool want_commit=!bad&&!(flags&(2|4|16));
  if(flags&16)need(txn(15),"invalid command accepted");
  if(flags&2){need(txn(6,positions[ctx]+1,true),"wrong-owner commit accepted");if(arch==0&&!bad){bool error=false;a_command(7,0,U(ctx+2)|(U(epochs[ctx])<<32)|(U(positions[ctx])<<64)|(U(positions[ctx]+1)<<96),&error);need(error,"A0 bad owner commit accepted");}}
  if(want_commit&&arch==0)a_command(7,0,U(ctx+1)|(U(epochs[ctx])<<32)|(U(positions[ctx])<<64)|(U(positions[ctx]+1)<<96));
  // Convolution history is one candidate, published only with the global txn.
  if(mode==2&&arch!=0){
   unsigned src=cache?role*elements:0,dst=cache?(1-role)*elements:0;Words history=cache?s_words(src,24):dma_read(address(false),24,"history");Words candidate(values.begin(),values.begin()+8);candidate.insert(candidate.end(),history.begin(),history.begin()+16);put_s_words(dst,candidate);
  }
  bool writeback=!keep||token+1==tokens;
  if(want_commit&&writeback){
   if(arch==0)dma_write_stream(address(true),elements,mode==2?"history":"state",[&](unsigned p,unsigned){return a_command(mode==2?14:11,p/4,0);});
   else if(mode==2||arch==2&&cache)dma_write_stream(address(true),elements,mode==2?"history":"state",[&](unsigned p,unsigned){return s_access(((cache?(1-role)*elements:0)+p)/4,false);});
   else if(arch==1&&(cache||elements<=cap)){
    for(unsigned pos=0;pos<elements;pos+=tile_words){if(cache)exchange(pos/tile_words);unsigned n=std::min(tile_words,elements-pos);dma_write_stream(address(true)+pos,n,"state",[&](unsigned p,unsigned){return r_read(1-role,p/4);});}
   }
  }
  bool committed=false;
  if(flags&4){need(std::none_of(versions.begin(),versions.end(),[](bool x){return x;}),"reset case requires explicit reload fixture");s.reset=true;d.reset=1;step("reset");step("reset");s.reset=false;d.reset=0;unsigned saved=ctx;for(ctx=0;ctx<contexts;++ctx)need(!txn(0),"reset reopen denied");ctx=saved;initialized=false;++aborts;}
  else if(want_commit){need(!txn(6,positions[ctx]+1),"valid global commit denied");versions[ctx]=!versions[ctx];if(writeback)ddr_versions[ctx]=!ddr_versions[ctx];++epochs[ctx];++positions[ctx];if(arch!=0)role=1-role;committed=true;++commits;}
  else{if(bad)need(txn(6,positions[ctx]+1),"failed computation committed");need(!txn(5),"global abort denied");if(arch==0)a_command(8,0,0);++aborts;}
  need(committed==bool(status[1]),"global publication mismatch");
  Words observed;
  if(flags&4){for(unsigned i=0;i<elements;++i)observed.push_back(dram[address(false)+i]);}
  else observed=peek();
  for(unsigned i=0;i<elements;++i){need(int32_t(observed[i])==expected_state[i],"published state mismatch");++checks;}
  s_access(992+ctx,true,U(ctx+1)|(U(epochs[ctx])<<32)|(U(positions[ctx])<<64)|(U(versions[ctx])<<96));
  trace<<token<<','<<ctx<<','<<begin<<','<<cycle<<','<<!bad<<','<<committed<<'\n';
 }
 need(input.peek()==std::char_traits<char>::eof(),"trailing input");uint64_t total=cycle-start;std::ofstream out(output);
 out<<"{\"status\":\"PASS\",\"architecture\":"<<arch<<",\"capacity\":"<<cap<<",\"elements\":"<<elements<<",\"layers\":"<<contexts<<",\"tokens\":"<<tokens<<",\"mode\":"<<mode<<",\"cycles\":"<<total<<",\"checks\":"<<checks<<",\"DRAM_read_bytes\":"<<dram_read<<",\"DRAM_write_bytes\":"<<dram_write<<",\"DRAM_peak_bytes\":"<<dram_peak<<",\"S_allocated_peak\":"<<s_alloc_peak<<",\"S_narrow_reads\":"<<s.narrow_reads<<",\"S_narrow_writes\":"<<s.narrow_writes<<",\"S_wide_reads\":"<<s.wide_reads<<",\"S_conflicts\":"<<s.conflicts<<",\"state_tile_visits\":"<<tiles<<",\"context_loads\":"<<loads<<",\"commits\":"<<commits<<",\"aborts\":"<<aborts<<",\"max_outstanding_writes\":"<<max_write_outstanding<<",\"R_wide_mul_events\":"<<r_mul<<",\"M_S8_physical_mul_events\":"<<m_s8_physical<<",\"M_S8_useful_mul_events\":"<<m_s8_useful<<",\"merge96_events\":"<<merge96<<",\"finish65_events\":"<<finish65<<",\"policy\":\""<<policy<<"\",\"latency\":"<<latency<<",\"bandwidth\":"<<bw;
 auto mapjson=[&](const char*name,const auto&m){out<<",\""<<name<<"\":{";bool first=true;for(const auto&kv:m){if(!first)out<<',';first=false;out<<'\"'<<kv.first<<"\":"<<kv.second;}out<<'}';};mapjson("stages",stages);mapjson("traffic",traffic);mapjson("ports",ports);out<<"}\n";passed=true;sc_stop();
}catch(const std::exception&e){std::cerr<<"FAIL "<<e.what()<<" cycle="<<cycle<<" ctx="<<ctx<<" mode="<<mode<<'\n';sc_stop();}}

int sc_main(int argc,char**argv){try{Verilated::commandArgs(argc,argv);need(argc==6,"usage input output DRAM_latency DRAM_B_per_cycle cache_or_dram");Experiment task("experiment",argv[1],argv[2],MODEL_ARCH,MODEL_WORDS,std::stoul(argv[3]),std::stoul(argv[4]),argv[5]);sc_start();return task.passed?0:1;}catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 2;}}
