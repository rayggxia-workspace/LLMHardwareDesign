#include "Vcontrol_adapter_r.h"
#include "verilated.h"
#include <array>
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <random>
using Word=std::array<uint32_t,4>;
using Desc=std::array<uint32_t,8>;
static uint64_t checks=0,cycles=0;
static void need(bool ok,const char*why){++checks;if(!ok){std::cerr<<why<<" cycle "<<cycles<<"\n";std::exit(1);}}
int main(int argc,char**argv){
 Verilated::commandArgs(argc,argv);Vcontrol_adapter_r v;std::mt19937 rng(162);
 std::array<Word,1024> memory{};std::array<std::array<Word,256>,8> loaded{};
 for(auto&w:memory)for(auto&x:w)x=rng();
 bool sp=false,rp=false,cp=false,command_error=false;unsigned sd=0,rd=0,cd=0,load_busy=0;
 Word s_reply{},r_reply{};std::array<uint32_t,16> command_reply{};
 uint64_t completions=0,completion=0,loads=0,reads=0,commands=0,sreads=0,swrites=0;
 Desc expected{};unsigned packet=0;bool checking=false;
 bool held_complete=false,held_s=false,held_load=false,held_read=false,held_cmd=false;
 uint64_t old_complete=0;std::array<uint32_t,6>old_s{},old_load{};uint32_t old_read=0,old_cmd=0;
 auto reset=[&](){
  v.reset=1;v.task_valid=0;v.complete_ready=0;v.s_ready=0;v.s_valid=0;v.load_ready=0;
  v.rd_ready=0;v.rd_rsp_valid=0;v.cmd_ready=0;v.rsp_valid=0;v.rsp_error=0;
  for(unsigned i=0;i<8;++i)v.task_data[i]=0;
  for(unsigned i=0;i<4;++i){v.s_dout[i]=0;v.rd_data[i]=0;}for(unsigned i=0;i<16;++i)v.rsp_data[i]=0;
  for(unsigned i=0;i<4;++i){v.clk=0;v.eval();v.clk=1;v.eval();++cycles;}
  v.reset=0;sp=rp=cp=false;sd=rd=cd=load_busy=0;
  held_complete=held_s=held_load=held_read=held_cmd=false;checking=false;
 };
 reset();
 auto tick=[&](){
  v.clk=0;v.complete_ready=rng()%4!=0;v.s_ready=!sp&&rng()%3!=0;v.s_valid=sp&&sd==0;
  v.load_ready=load_busy==0&&rng()%3!=0;v.rd_ready=!rp&&rng()%3!=0;v.rd_rsp_valid=rp&&rd==0;
  v.cmd_ready=!cp&&rng()%3!=0;v.rsp_valid=cp&&cd==0;v.rsp_error=command_error;
  for(unsigned i=0;i<4;++i){v.s_dout[i]=s_reply[i];v.rd_data[i]=r_reply[i];}
  for(unsigned i=0;i<16;++i)v.rsp_data[i]=command_reply[i];v.eval();
  const std::array<uint32_t,6>ss{{v.s_wr,v.s_addr,v.s_din[0],v.s_din[1],v.s_din[2],v.s_din[3]}};
  const std::array<uint32_t,6>ls{{v.load_target,v.load_index,v.load_data[0],v.load_data[1],v.load_data[2],v.load_data[3]}};
  const uint32_t rs=v.rd_bank|(uint32_t(v.rd_index)<<1);
  const uint32_t cs=v.cmd_op|(uint32_t(v.cmd_rows)<<3)|(uint32_t(v.cmd_role)<<12)|(uint32_t(v.cmd_clear)<<13)|(uint32_t(v.cmd_mode)<<14);
  if(held_complete)need(v.complete_valid&&v.complete_data==old_complete,"completion stable under backpressure");
  if(held_s)need(v.s_req&&ss==old_s,"S request stable under backpressure");
  if(held_load)need(v.load_valid&&ls==old_load,"R load stable under backpressure");
  if(held_read)need(v.rd_valid&&rs==old_read,"R read stable under backpressure");
  if(held_cmd)need(v.cmd_valid&&cs==old_cmd,"R command stable under backpressure");
  held_complete=v.complete_valid&&!v.complete_ready;old_complete=v.complete_data;
  held_s=v.s_req&&!v.s_ready;old_s=ss;held_load=v.load_valid&&!v.load_ready;old_load=ls;
  held_read=v.rd_valid&&!v.rd_ready;old_read=rs;held_cmd=v.cmd_valid&&!v.cmd_ready;old_cmd=cs;
  if(v.complete_valid&&v.complete_ready){
   need(!sp&&!rp&&!cp&&!load_busy,"completion drains accepted transactions");completion=v.complete_data;++completions;
  }
  if(sp&&sd)--sd;if(v.s_valid&&v.s_take)sp=false;
  if(rp&&rd)--rd;if(v.rd_rsp_valid&&v.rd_rsp_ready)rp=false;
  if(cp&&cd)--cd;if(v.rsp_valid&&v.rsp_ready)cp=false;
  if(load_busy)--load_busy;
  if(v.s_req&&v.s_ready){
   need(!sp&&checking,"finite S ownership");need(v.s_addr==(expected[4]/16+packet),"S packet address exact");
   if(v.s_wr){
    need((expected[0]&255)!=0,"load must read S");
    for(unsigned i=0;i<4;++i){
     const uint32_t value=(expected[0]&255)==2?command_reply[4*packet+i]:loaded[expected[1]][expected[2]+packet][i];
     need(v.s_din[i]==value,"all128 output bits retained");memory[v.s_addr][i]=v.s_din[i];
    }
    ++swrites;++packet;
   }else{need((expected[0]&255)==0,"only load reads S");s_reply=memory[v.s_addr];++sreads;}
   sp=true;sd=1+rng()%7;
  }
  if(v.load_valid&&v.load_ready){
   need(checking&&(expected[0]&255)==0,"only load task issues R load");need(v.load_target==expected[1]&&v.load_index==expected[2]+packet,"R load index exact");
   for(unsigned i=0;i<4;++i){need(v.load_data[i]==memory[expected[4]/16+packet][i],"all128 load bits retained");loaded[v.load_target][v.load_index][i]=v.load_data[i];}
   ++packet;++loads;load_busy=1+rng()%4;
  }
  if(v.rd_valid&&v.rd_ready){
   need(!rp&&checking&&(expected[0]&255)==1,"one R read credit");need(v.rd_bank==expected[1]&&v.rd_index==expected[2]+packet,"R read bank/index exact");
   r_reply=loaded[v.rd_bank][v.rd_index];rp=true;rd=4+rng()%6;++reads;
  }
  if(v.cmd_valid&&v.cmd_ready){
   need(!cp&&checking&&(expected[0]&255)==2,"one R command");
   need(v.cmd_op==expected[1]&&v.cmd_rows==expected[2]&&v.cmd_role==(expected[3]&1)&&v.cmd_clear==((expected[3]>>1)&1)&&v.cmd_mode==(expected[3]>>2),"R command fields exact");
   for(unsigned i=0;i<16;++i)command_reply[i]=0x139ac781u*(i+1)^expected[1]^(expected[2]<<8)^(expected[3]<<24);
   cp=true;cd=1+rng()%9;++commands;
  }
  v.clk=1;v.eval();++cycles;
 };
 auto task=[&](Desc d,unsigned status,unsigned words){
  expected=d;packet=0;checking=true;const uint64_t before=completions;const auto oldloads=loads,oldreads=reads,oldcommands=commands,oldsr=sreads,oldsw=swrites;
  for(unsigned i=0;i<8;++i)v.task_data[i]=d[i];v.task_valid=1;v.clk=0;v.eval();unsigned guard=0;
  while(!v.task_ready){tick();need(++guard<100000,"task ready bounded");}tick();v.task_valid=0;
  while(completions==before){tick();need(++guard<100000,"completion bounded");}
  need(((completion>>16)&15)==7&&uint16_t(completion)==uint16_t(d[0]>>16),"completion endpoint and tag exact");
  need(((completion>>20)&15)==status&&(completion>>32)==words,"completion status and count exact");
  if(status==2)need(loads==oldloads&&reads==oldreads&&commands==oldcommands&&sreads==oldsr&&swrites==oldsw,"invalid descriptor has no side effects");
  if(status==4)need(swrites==oldsw,"R command error never writes result");
  checking=false;return completion;
 };
 unsigned tag=1,descriptors=0;
 auto desc=[&](unsigned op,unsigned a,unsigned b,unsigned n,unsigned address){++descriptors;return Desc{{((tag++&65535)<<16)|0x700|op,a,b,n,address,0,0,0}};};
 const std::array<unsigned,8>capacity{{256,256,16,16,6,1,6,4}};
 for(unsigned target=0;target<8;++target){
  const auto count=capacity[target];task(desc(0,target,0,count,0),0,count);
  task(desc(0,target,count-1,1,16368),0,1);
  task(desc(0,target,count,1,0),2,0);task(desc(0,target,count-1,2,0),2,0);
 }
 for(unsigned bank=0;bank<2;++bank){task(desc(1,bank,0,256,4096),0,256);task(desc(1,bank,255,1,16368),0,1);}
 for(unsigned op=0;op<8;++op)for(unsigned flags=0;flags<16;++flags)task(desc(2,op,1+rng()%128,flags,16320),0,4);
 command_error=true;task(desc(2,5,128,15,0),4,0);command_error=false;
 for(unsigned op=0;op<3;++op){
  auto d=desc(op,0,0,op==2?0:1,0);d[0]|=0x1000;task(d,2,0);
  d=desc(op,0,0,op==2?0:1,0);d[7]=1;task(d,2,0);
  for(unsigned address:{1u,16384u,0xfffffff0u})task(desc(op,0,0,op==2?0:1,address),2,0);
 }
 for(unsigned bad:{0u,257u,0x80000000u,0xffffffffu}){task(desc(0,0,0,bad,0),2,0);task(desc(1,0,0,bad,0),2,0);}
 for(unsigned bad:{256u,0x80000000u,0xffffffffu}){task(desc(0,0,bad,1,0),2,0);task(desc(1,0,bad,1,0),2,0);}
 task(desc(0,8,0,1,0),2,0);task(desc(1,2,0,1,0),2,0);task(desc(2,8,1,0,0),2,0);
 task(desc(2,0,129,0,0),2,0);task(desc(2,0,1,16,0),2,0);task(desc(2,0,1,0,16336),2,0);
 for(unsigned op=3;op<8;++op)task(desc(op,0,0,0,0),2,0);
 // Cancel real in-flight activity at several different handshake offsets.
 for(unsigned op=0;op<3;++op)for(unsigned delay=1;delay<20;++delay){
  auto d=desc(op,0,op==2?8:0,op==2?0:8,0);expected=d;packet=0;checking=true;
  for(unsigned i=0;i<8;++i)v.task_data[i]=d[i];v.task_valid=1;v.clk=0;v.eval();
  need(v.task_ready,"reset trial starts idle");tick();v.task_valid=0;for(unsigned i=0;i<delay;++i)tick();
  reset();const auto before=completions;for(unsigned i=0;i<20;++i)tick();need(completions==before,"reset cancels stale completion");
  task(desc(2,7,0,0,0),0,4);
 }
 for(unsigned i=0;i<30;++i)tick();need(!sp&&!rp&&!cp&&!load_busy,"final protocol drain");
 std::cout<<"{\"passed\":true,\"checks\":"<<checks<<",\"cycles\":"<<cycles<<",\"descriptors\":"<<descriptors<<",\"R_loads\":"<<loads<<",\"R_reads\":"<<reads<<",\"R_commands\":"<<commands<<",\"S_reads\":"<<sreads<<",\"S_writes\":"<<swrites<<",\"scope\":\"independent interface oracle; actual R arithmetic pairing separate\"}\n";
}
