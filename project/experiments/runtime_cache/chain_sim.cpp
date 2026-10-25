#include "Vchain85.h"
#include "verilated.h"
#include <array>
#include <vector>
#include <deque>
#include <fstream>
#include <iostream>
#include <stdexcept>
using W=std::array<uint32_t,4>;static Vchain85 d;static uint64_t ticks=0;static int stall=0,waits=0,mulwait=0;static bool seen=false,mulseen=false;static uint64_t serial=0,mulserial=0,extserial=0;static bool hold_external=false;
static void need(bool b,const char*s){if(!b)throw std::runtime_error(s);}
struct Reply{uint32_t epoch;int delay;W words;};static unsigned fabric_high_water=0;static std::deque<Reply> fifo;static std::vector<uint8_t> payload;static std::vector<int32_t> accs,downs,joins;
struct E{bool cfg_req,cfg_rsp,command;W data;};
static E step(){
 d.clk=0;d.ext_ready=fifo.size()<2;d.ext_valid=!fifo.empty()&&!hold_external&&fifo.front().delay==0;d.ext_response_epoch=fifo.empty()?0:fifo.front().epoch;for(int j=0;j<4;j++)d.ext_data[j]=fifo.empty()?0:fifo.front().words[j];d.eval();
 bool accept=d.ext_req&&d.ext_ready,retire=d.ext_valid&&d.ext_take;auto address=d.ext_addr,epoch=d.ext_epoch;
 if(d.obs_valid){accs.push_back(d.obs_acc);downs.push_back(d.obs_down);}
 if(d.mem_request&&!seen){seen=true;waits=stall?serial%3:0;serial++;}d.mem_hold=waits>0;
 if(d.mul_request&&!mulseen){mulseen=true;mulwait=stall?mulserial%3:0;mulserial++;}d.mul_hold=mulwait>0;d.eval();
 if(d.mwrite)for(int j=0;j<4;j++)joins.push_back(d.mdata[j]);
 E e{bool(d.cfg&&d.cfg_ready),bool(d.cfg_valid&&d.cfg_take),bool(d.cmd_accept),{d.cfg_dout[0],d.cfg_dout[1],d.cfg_dout[2],d.cfg_dout[3]}};
 d.clk=1;d.eval();d.clk=0;d.eval();ticks++;
 if(d.reset){fifo.clear();extserial=0;}else{for(auto& f:fifo)if(f.delay>0)f.delay--;if(retire)fifo.pop_front();if(accept){need(address%16==0&&address+16<=payload.size(),"physical request address");W w{};for(int j=0;j<16;j++)w[j/4]|=uint32_t(payload[address+j])<<(8*(j%4));fifo.push_back({epoch,stall?1+int(extserial++%5):1,w});if(fifo.size()>fabric_high_water)fabric_high_water=fifo.size();}}
 if(d.soft_abort){seen=mulseen=false;waits=mulwait=0;serial=mulserial=0;}
 if(mulwait>0)mulwait--;if(!d.mul_request)mulseen=false;if(waits>0)waits--;if(!d.mem_request)seen=false;return e;
}
static W cfg(bool wr,int addr,W w={}){d.cfg=1;d.cfg_wr=wr;d.cfg_addr=addr;d.cfg_take=1;for(int i=0;i<4;i++)d.cfg_din[i]=w[i];int n=0;while(!step().cfg_req)need(++n<100,"cfg ready");d.cfg=0;for(n=0;n<100;n++){auto e=step();if(e.cfg_rsp)return e.data;}throw std::runtime_error("cfg response");}
static std::vector<uint8_t> unhex(std::string s){std::vector<uint8_t>r;for(size_t i=0;i<s.size();i+=2)r.push_back(std::stoul(s.substr(i,2),nullptr,16));return r;}
static void load(std::string s){auto a=unhex(s);for(size_t j=0;j<a.size();j+=16){W w{};for(int i=0;i<16;i++)w[i/4]|=uint32_t(a[j+i])<<(8*(i%4));cfg(true,384+j/16,w);}}
struct Case{std::string name,p0,p1,g;uint32_t coefficient;};static std::ofstream out;static unsigned command_count=0,blocked_edges=0,held_done=0;
static uint32_t b0,t0,g0,g1;static uint64_t setup;
static void prepare(const Case& c,int mode,int fault=0){std::ifstream f(mode?c.p1:c.p0,std::ios::binary);payload.assign(std::istreambuf_iterator<char>(f),{});need(payload.size()==size_t(mode?6492160:12779520),"physical format");
 if(fault){auto h=mode?4096:0;if(fault==1)payload[h+14]=1;if(fault==2){payload[h+4]=32;payload[h+5]=payload[h+6]=payload[h+7]=0;}if(fault==3){payload[h]=payload[h+1]=payload[h+2]=255;payload[h+3]=127;payload[h+4]=31;payload[h+5]=payload[h+6]=payload[h+7]=0;if(mode){for(int j=0;j<512;j++){payload[j]=127;payload[h+16+j]=127;}}else for(int j=h+16;j<h+16+1024;j++)payload[j]=127;}}
 auto st=ticks;load(c.g);setup=ticks-st;accs.clear();downs.clear();joins.clear();serial=mulserial=extserial=0;seen=mulseen=false;waits=mulwait=0;b0=d.wire_beats;t0=d.transactions;g0=d.mul_grants0;g1=d.mul_grants1;
 d.cache_mode=mode;d.epsilon=17;d.coefficient=c.coefficient;
}
static void start(bool collision=false){auto epoch=d.epoch;d.cmd=1;
 if(collision){d.cfg=1;d.cfg_wr=0;d.cfg_addr=400;d.cfg_take=0;need(step().cfg_req,"cfg priority accepted");d.cfg=0;for(int j=0;j<3;j++){need(!step().command&&!d.cmd_ready&&d.cfg_valid,"pending cfg blocks command");blocked_edges++;}d.cfg_take=1;need(step().cfg_rsp,"held cfg response");}
 int n=0;while(!step().command)need(++n<20,"command ready handshake");need(d.epoch==epoch+1,"epoch advances per accept");command_count++;d.cmd=0;d.cache_mode^=1;d.epsilon=0;d.coefficient=0;
}
static void wait_done(){auto st=ticks;bool bad_pulse=false;while(!d.done){if(ticks-st==20){d.cmd=1;bad_pulse=true;}auto e=step();need(!e.command,"busy command unaccepted");if(bad_pulse)d.cmd=0;need(ticks-st<30000000,"whole chain watchdog");need(!d.cfg_ready,"busy blocks cfg");}}
static void ack(){unsigned status=d.status;auto epoch=d.epoch;for(int j=0;j<4;j++){need(d.done&&!d.cmd_ready&&d.status==status&&d.epoch==epoch,"held done status");step();held_done++;}d.ack=1;step();d.ack=0;need(!d.busy,"ack idle");}
static void finish(const Case& c,int mode,const std::string& role){wait_done();need(d.status==0,"whole chain status");need(accs.size()==12288&&downs.size()==12288&&joins.size()==1536,"all internal observations");auto cy=d.cycles,ncy=d.norm_cycles;auto epoch=d.epoch;auto r=d.reads,w=d.writes,p=d.packets,mac=d.macs,mw=d.mwrites,cr=d.cache_reads,cw=d.cache_writes;auto beats=d.wire_beats-b0,tx=d.transactions-t0,mg0=d.mul_grants0-g0,mg1=d.mul_grants1-g1;ack();auto begin=ticks;std::vector<int32_t>result;for(int j=0;j<384;j++){auto ws=cfg(false,j);for(int k=0;k<4;k++)result.push_back(int32_t(ws[k]));}
 auto array=[&](auto&v){out<<"[";for(size_t i=0;i<v.size();i++){if(i)out<<",";out<<v[i];}out<<"]";};
 out<<"{\"name\":\""<<c.name<<"\",\"role\":\""<<role<<"\",\"cache\":"<<mode<<",\"epoch\":"<<epoch<<",\"status\":0,\"cycles\":"<<cy<<",\"norm_cycles\":"<<ncy<<",\"reads\":"<<r<<",\"writes\":"<<w<<",\"M_packets\":"<<p<<",\"M_MACs\":"<<mac<<",\"M_store_lines\":"<<mw<<",\"wire_beats\":"<<beats<<",\"transactions\":"<<tx<<",\"cache_reads\":"<<cr<<",\"cache_writes\":"<<cw<<",\"mul_grants0\":"<<mg0<<",\"mul_grants1\":"<<mg1<<",\"setup_edges\":"<<setup<<",\"result_edges\":"<<ticks-begin<<",\"acc\":";array(accs);out<<",\"down\":";array(downs);out<<",\"joined\":";array(joins);out<<",\"out\":";array(result);out<<"}\n";
}
static void abort_now(){auto e=d.epoch;d.soft_abort=1;step();d.soft_abort=0;need(!d.busy&&!d.done&&d.epoch==e+1,"abort clears pipeline and changes epoch");d.cmd=0;}
int main(int argc,char**argv){try{Verilated::commandArgs(argc,argv);need(argc==4,"vectors output stall");stall=std::stoi(argv[3]);d.reset=1;step();step();d.reset=0;step();std::ifstream in(argv[1]);out.open(argv[2]);need(bool(in)&&bool(out),"files");std::vector<Case> cases;Case c;while(in>>c.name>>c.p0>>c.p1>>c.g>>c.coefficient)cases.push_back(c);need(cases.size()==6,"six cases");
 for(int i=0;i<6;i++)for(int m=0;m<2;m++){int mode=(i%2)?1-m:m;prepare(cases[i],mode);start(true);finish(cases[i],mode,"mixed");}
 c=cases[0];unsigned aborttests=0,errors=0;std::vector<std::pair<int,int>> stages={{1,15},{1,17},{1,5},{1,6},{1,21},{0,5},{2,4},{2,6},{2,8},{2,16}};
 for(auto target:stages){int mode=target.first==0?0:1;prepare(c,mode);start();auto begin=ticks;while(!((target.first==2?d.ndebug:d.mdebug)==target.second&&(target.first!=2||d.debug_state==3))){step();need(ticks-begin<30000000,"reach abort phase");}
 abort_now();for(int j=0;j<10;j++){step();need(!d.done,"no ghost done");}aborttests++;prepare(c,1-mode);start();finish(c,1-mode,"restart-stage-"+std::to_string(aborttests));}
 for(int mode=0;mode<2;mode++)for(int fault=1;fault<=3;fault++){prepare(c,mode,fault);start();wait_done();need(d.status==(fault==3?2:1),"fault status exact");ack();errors++;prepare(c,mode);start();finish(c,mode,"restart-error-"+std::to_string(mode)+"-"+std::to_string(fault));}
 // Keep an accepted old response in an explicit finite two-slot fabric queue across soft abort.
 prepare(c,1);hold_external=true;start();auto begin=ticks;while(fifo.empty()){step();need(ticks-begin<100,"old external request issued");}auto old_epoch=d.epoch;abort_now();prepare(c,0);start();need(d.epoch!=old_epoch,"new generation");begin=ticks;while(fifo.size()<2){step();need(ticks-begin<100,"new request queued behind stale reply");}hold_external=false;finish(c,0,"restart-stale-epoch");need(d.stale_responses>=1&&fifo.empty(),"late old response discarded");
 unsigned actual_abort_count=d.aborts,actual_stale_count=d.stale_responses;auto before=d.epoch;cfg(true,400,{0xa5a5a5a5,0xa5a5a5a5,0xa5a5a5a5,0xa5a5a5a5});d.reset=1;step();d.reset=0;step();need(d.epoch==0&&!d.busy&&!d.done&&cfg(false,400)[0]==0xa5a5a5a5,"coordinated hard reset retains SRAM");prepare(c,1);start();finish(c,1,"restart-hard-reset");
 std::ofstream p(std::string(argv[2])+".protocol.json");p<<"{\"soft_aborts_actual\":"<<actual_abort_count<<",\"stale_responses_actual\":"<<actual_stale_count<<",\"fabric_response_high_water\":"<<fabric_high_water<<",\"schema\":\"runtime85-protocol-v1\",\"mode_parameter_latching\":true,\"cfg_command_competition\":true,\"held_done_response\":true,\"stage_abort_restart\":true,\"error_recovery\":true,\"stale_epoch_discard\":true,\"coordinated_reset_restart\":true,\"commands_accepted\":"<<command_count<<",\"abort_stages\":"<<aborttests<<",\"error_conditions\":"<<errors<<",\"blocked_command_edges\":"<<blocked_edges<<",\"held_done_edges\":"<<held_done<<",\"full_output_commands\":30}\n";
 std::cout<<"PASS_RUNTIME_EXECUTION 30 full commands plus abort/error cases\n";return 0;
 }catch(const std::exception&e){std::cerr<<e.what()<<" state="<<unsigned(d.debug_state)<<" M="<<unsigned(d.mdebug)<<" N="<<unsigned(d.ndebug)<<" status="<<unsigned(d.status)<<"\n";return 1;}}
