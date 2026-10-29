#include "Vlinkclose_mts_bench.h"
#include "verilated.h"
#include <array>
#include <vector>
#include <cstdint>
#include <iostream>
#include <stdexcept>
using Word=std::array<uint32_t,4>;
struct Test {
 Vlinkclose_mts_bench d;
 uint64_t cycles=0,checks=0,full=0,mstalls=0,tstalls=0,swrites=0;
 unsigned written=0,read=0,profile=0;uint64_t start=0;
 bool active=false,heldm=false,heldt=false,verify=false;
 Word oldm{},oldt{};unsigned oldti=0;
 std::vector<Word> expected;
 void need(bool b,const char*m){++checks;if(!b)throw std::runtime_error(std::to_string(cycles)+": "+m);}
 template<class T>Word word(T&v){return {v[0],v[1],v[2],v[3]};}
 void idle(){d.cmd_valid=0;d.command_capture=0;d.begin_valid=0;d.commit_valid=0;d.release_valid=0;d.verify_req=0;d.read_enable=0;d.write_enable=1;d.s_take=1;}
 void tick(){
  if(active&&!verify){
   uint64_t age=cycles-start;
   d.write_enable=profile==0?1:(age>=80&&age%11>=4);
   d.s_take=profile==0?1:age%17>=9;
  }
  d.clk=0;d.eval();
  if(!d.reset){
   need(d.occupancy<=2,"finite queue overflow");full+=d.occupancy==2;
   if(heldm)need(d.m_valid&&word(d.m_data)==oldm,"producer changed held response");
   heldm=d.m_valid&&!d.m_ready;if(heldm){oldm=word(d.m_data);++mstalls;}
   if(heldt)need(d.t_read_valid&&word(d.t_read_data)==oldt&&d.t_read_index==oldti,"T changed held result");
   heldt=d.t_read_valid&&!d.t_read_take;if(heldt){oldt=word(d.t_read_data);oldti=d.t_read_index;++tstalls;}
   need(!d.t_error&&!d.bridge_error&&!d.bridge_saturated,"macro/bridge error");
   if(d.t_write_valid&&d.t_write_ready){
    need(active&&written<expected.size(),"unexpected command acknowledgement entered T");
    need(d.t_write_index==written&&word(d.t_write_data)==expected[written],"T write order/payload");++written;
   }
   if(d.t_read_valid&&d.t_read_take){
    need(read<expected.size()&&d.t_read_index==read&&word(d.t_read_data)==expected[read],"T/S transfer");++read;++swrites;
   }
  }else{heldm=heldt=false;}
  d.clk=1;d.eval();++cycles;
 }
 void command(unsigned op,unsigned index,Word data,bool capture=false){
  d.cmd_op=op;d.cmd_index=index;d.command_capture=capture;
  for(int i=0;i<4;++i)d.cmd_data[i]=data[i];d.cmd_valid=1;
  for(unsigned n=0;;++n){need(n<20000,"command timeout");d.clk=0;d.eval();bool fire=d.cmd_ready;tick();if(fire)break;}
  d.cmd_valid=0;
 }
 template<class F>void until(F f){for(unsigned n=0;!f();++n){need(n<20000,"phase timeout");tick();}}
 void reset(){idle();d.reset=1;tick();tick();d.reset=0;tick();active=false;}
 void setup(unsigned seed){
  command(6,0,{});Word a{};int av[8];
  for(unsigned k=0;k<8;++k){av[k]=int((k+seed)%13)-6;a[k/2]|=uint32_t(uint16_t(av[k]))<<(16*(k%2));}command(0,0,a);
  for(unsigned j=0;j<8;++j){Word b{};for(unsigned k=0;k<8;++k)b[k/2]|=uint32_t(uint16_t(int((3*j+k+seed)%17)-8))<<(16*(k%2));command(1,j,b);}
  command(2,0,{0x887,0,0,0});until([&]{return !d.m_valid&&d.occupancy==0&&d.cmd_ready;});
 }
 Word reference(unsigned seed,unsigned pair){Word v{};for(unsigned l=0;l<2;++l){int64_t acc=0;unsigned j=2*pair+l;for(unsigned k=0;k<8;++k)acc+=(int((k+seed)%13)-6)*(int((3*j+k+seed)%17)-8);v[2*l]=uint32_t(acc);v[2*l+1]=uint32_t(uint64_t(acc)>>32);}return v;}
 void lease(unsigned size,unsigned p,unsigned seed){
  profile=p;setup(seed);written=read=0;expected.clear();for(unsigned i=0;i<size;++i)expected.push_back(reference(seed,i%4));
  d.begin_words=size;d.begin_valid=1;d.clk=0;d.eval();need(d.begin_ready,"begin admission");tick();d.begin_valid=0;
  active=true;start=cycles;
  for(unsigned i=0;i<size;++i){
   command(3,i%4,{},true);
   if(p&&i%5==0){d.cmd_valid=0;for(unsigned n=0;n<7;++n)tick();}
  }
  until([&]{return d.t_sealed;});need(written==size,"complete lease only");
  d.commit_valid=1;d.clk=0;d.eval();need(d.commit_ready,"commit admission");tick();d.commit_valid=0;d.read_enable=1;
  until([&]{return d.release_ready;});need(read==size,"complete S transfer");
  d.read_enable=0;d.release_valid=1;tick();d.release_valid=0;
  d.s_take=1;verify=true;
  until([&]{return !d.s_valid;});
  for(unsigned i=0;i<size;++i){
   d.verify_req=1;d.verify_addr=i;d.clk=0;d.eval();need(d.verify_ready,"S read admission");tick();d.verify_req=0;
   d.clk=0;d.eval();need(d.s_valid&&word(d.s_dout)==expected[i],"S final readback");tick();
  }
  verify=false;active=false;need(!d.t_busy,"lease released");
 }
 void run(){reset();unsigned cases=0;for(unsigned size:{1u,2u,3u,7u,16u,383u,384u})for(unsigned p=0;p<2;++p){lease(size,p,3+cases);++cases;}
  // Reset with queued/in-flight data: old bytes must not become a new lease.
  setup(91);d.begin_words=3;d.begin_valid=1;tick();d.begin_valid=0;active=true;profile=1;start=cycles;written=read=0;expected={reference(91,0),reference(91,1),reference(91,2)};
  command(3,0,{},true);command(3,1,{},true);until([&]{return d.occupancy==2;});reset();need(d.occupancy==0&&!d.t_busy,"coordinated reset discards in-flight lease");
  lease(7,1,92);++cases;
  need(full>0&&mstalls>0&&tstalls>0,"stall scenarios actually exercised");
  std::cout<<"{\"passed\":true,\"cases\":"<<cases<<",\"cycles\":"<<cycles<<",\"checks\":"<<checks<<",\"queue_full_cycles\":"<<full<<",\"producer_stall_cycles\":"<<mstalls<<",\"consumer_stall_cycles\":"<<tstalls<<",\"s_writes\":"<<swrites<<"}\n";
 }
};
int main(int argc,char**argv){Verilated::commandArgs(argc,argv);try{Test t;t.run();}catch(const std::exception&e){std::cerr<<e.what()<<"\n";return 1;}return 0;}
