#include "Vchain93.h"
#include "verilated.h"
#include <array>
#include <vector>
#include <deque>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
using W=std::array<uint32_t,4>;static Vchain93 d;static uint64_t ticks=0;static int stall=0,waits=0,mulwait=0;static bool seen=false,mulseen=false;static uint64_t serial=0,mulserial=0,extserial=0;static bool hold_external=false;
static void need(bool b,const char*s){if(!b)throw std::runtime_error(s);}
static constexpr uint32_t GBASE=0x01000000;
struct Reply{uint32_t epoch;int delay;W words;};static unsigned fabric_high_water=0;static std::deque<Reply> fifo;static std::vector<uint8_t> payload,gamma_payload;
static std::vector<int32_t> accs,downs,joins,gamma_words;static std::vector<uint32_t> gamma_addresses,external_gamma_addresses;
static bool track=false;static int active_h=0,active_kind=0,active_stream=0,gamma_fault=0;static unsigned sum_barrier_checks=0,canary_checks=0;
struct E{bool cfg_req,cfg_rsp,command;W data;};
static E step(){
 d.clk=0;d.ext_ready=fifo.size()<2;d.ext_valid=!fifo.empty()&&!hold_external&&fifo.front().delay==0;d.ext_response_epoch=fifo.empty()?0:fifo.front().epoch;for(int j=0;j<4;j++)d.ext_data[j]=fifo.empty()?0:fifo.front().words[j];d.eval();
 bool accept=d.ext_req&&d.ext_ready,retire=d.ext_valid&&d.ext_take;auto address=d.ext_addr,epoch=d.ext_epoch;
 if(track&&d.obs_valid){accs.push_back(d.obs_acc);downs.push_back(d.obs_down);}
 if(d.mem_request&&!seen){seen=true;waits=stall?serial%3:0;serial++;}d.mem_hold=waits>0;
 if(d.mul_request&&!mulseen){mulseen=true;mulwait=stall?mulserial%3:0;mulserial++;}d.mul_hold=mulwait>0;d.eval();
 if(track&&d.mwrite)for(int j=0;j<4;j++)joins.push_back(d.mdata[j]);
 if(track&&d.swrite_event){unsigned a=d.swrite_addr;
  if(d.debug_state==1)need(a<384||(a>=768&&a<1024),"M writes only XY/A");
  else{unsigned base=active_h/4;need(d.den_events==1,"wholeH single denominator precedes all norm writes");sum_barrier_checks++;
   if(active_stream&&a>=base&&a<base+64){gamma_addresses.push_back(a);for(int j=0;j<4;j++)gamma_words.push_back(d.swrite_data[j]);}
   else need(a<unsigned(active_h/4),"norm cannot write frame/gap/A or stale full-gamma area");}
 }
 E e{bool(d.cfg&&d.cfg_ready),bool(d.cfg_valid&&d.cfg_take),bool(d.cmd_accept),{d.cfg_dout[0],d.cfg_dout[1],d.cfg_dout[2],d.cfg_dout[3]}};
 d.clk=1;d.eval();d.clk=0;d.eval();ticks++;
 if(d.reset){fifo.clear();extserial=0;}else{for(auto&f:fifo)if(f.delay>0)f.delay--;if(retire)fifo.pop_front();if(accept){W w{};need(address%16==0,"external alignment");if(address>=GBASE){uint32_t off=address-GBASE;need(off+16<=gamma_payload.size(),"gamma external bounds");if(track)external_gamma_addresses.push_back(address);if(gamma_fault==1)off=(off+1024)%gamma_payload.size();if(gamma_fault==2)off%=1024;for(int j=0;j<16;j++)w[j/4]|=uint32_t(gamma_payload[off+j])<<(8*(j%4));}else{need(address+16<=payload.size(),"M external bounds");for(int j=0;j<16;j++)w[j/4]|=uint32_t(payload[address+j])<<(8*(j%4));}fifo.push_back({epoch,stall?1+int(extserial++%5):1,w});if(fifo.size()>fabric_high_water)fabric_high_water=fifo.size();}}
 if(d.soft_abort){seen=mulseen=false;waits=mulwait=0;serial=mulserial=0;}if(mulwait>0)mulwait--;if(!d.mul_request)mulseen=false;if(waits>0)waits--;if(!d.mem_request)seen=false;return e;
}
static W cfg(bool wr,int addr,W w={}){d.cfg=1;d.cfg_wr=wr;d.cfg_addr=addr;d.cfg_take=1;for(int i=0;i<4;i++)d.cfg_din[i]=w[i];int n=0;while(!step().cfg_req)need(++n<100,"cfg ready");d.cfg=0;for(n=0;n<100;n++){auto e=step();if(e.cfg_rsp)return e.data;}throw std::runtime_error("cfg response");}
static std::vector<uint8_t> unhex(std::string s){std::vector<uint8_t>r;for(size_t i=0;i<s.size();i+=2)r.push_back(std::stoul(s.substr(i,2),nullptr,16));return r;}
static W bytes_word(const std::vector<uint8_t>&a,size_t j){W w{};for(int i=0;i<16;i++)w[i/4]|=uint32_t(a[j+i])<<(8*(i%4));return w;}
static void load_at(const std::vector<uint8_t>&a,int base){need(a.size()%16==0,"full lines");for(size_t j=0;j<a.size();j+=16)cfg(true,base+j/16,bytes_word(a,j));}
struct Case{std::string name,p0,p1,g,x;uint32_t epsilon,coefficient;int kind,h;};static std::ofstream out;static unsigned commands=0,blocked_edges=0,held_done=0,aborts_tested=0,errors=0,parameter_mutations=0,control_conflicts=0,terminal_rejects=0,negative_runs=0,records_written=0;
static uint32_t b0,t0,g0,g1;static uint64_t setup,guard_setup,command_edges,accepted_tick;static std::vector<unsigned>guard_lines;
static W canary(unsigned i){return{0x91c00000u+i,0x91c10000u+i,0x91c20000u+i,0x91c30000u+i};}
static void prepare(const Case&c,int cache,int stream,int fault=0){track=false;gamma_fault=fault;active_h=c.h;active_kind=c.kind;active_stream=stream;payload.clear();if(!c.kind){std::ifstream f(cache?c.p1:c.p0,std::ios::binary);payload.assign(std::istreambuf_iterator<char>(f),{});need(payload.size()==size_t(cache?6492160:12779520),"original fullM payload");}gamma_payload=unhex(c.g);need(gamma_payload.size()==size_t(c.h*4),"complete gamma");
 auto st=ticks;guard_lines.clear();if(stream)for(unsigned i=c.h/4+64;i<768;i++)guard_lines.push_back(i);if(c.kind||!cache)for(unsigned i=768;i<1024;i++)guard_lines.push_back(i);for(auto i:guard_lines)cfg(true,i,canary(i));guard_setup=ticks-st;
 st=ticks;if(c.kind)load_at(unhex(c.x),0);if(!stream)load_at(gamma_payload,384);setup=ticks-st;
 accs.clear();downs.clear();joins.clear();gamma_words.clear();gamma_addresses.clear();external_gamma_addresses.clear();serial=mulserial=extserial=0;seen=mulseen=false;waits=mulwait=0;b0=d.wire_beats;t0=d.transactions;g0=d.mul_grants0;g1=d.mul_grants1;
 d.cache_mode=cache;d.norm_only=c.kind;d.h=c.h;d.gamma_stream=stream;d.gamma_address=GBASE;d.epsilon=c.epsilon;d.coefficient=c.coefficient;track=true;
}
static void start(bool collision=false){auto before=ticks;auto epoch=d.epoch;d.cmd=1;
 if(collision){d.cfg=1;d.cfg_wr=0;d.cfg_addr=740;d.cfg_take=0;need(step().cfg_req,"cfg priority");d.cfg=0;for(int j=0;j<3;j++){need(!step().command&&!d.cmd_ready&&d.cfg_valid,"pending cfg blocks cmd");blocked_edges++;}d.cfg_take=1;need(step().cfg_rsp,"held cfg response");}
 int n=0;while(!step().command)need(++n<20,"command handshake");need(d.epoch==epoch+1,"epoch increments");commands++;d.cmd=0;command_edges=ticks-before;accepted_tick=ticks;
 d.cache_mode^=1;d.norm_only^=1;d.h=7;d.gamma_stream^=1;d.gamma_address=3;d.epsilon=0;d.coefficient=0;parameter_mutations++;
}
static void wait_done(){auto st=ticks;while(!d.done){d.cmd=(ticks-st==20);need(!step().command,"busy command rejected");d.cmd=0;need(ticks-st<30000000,"complete command watchdog");need(!d.cfg_ready,"busy cfg blocked");}}
static void ack(){unsigned status=d.status;auto epoch=d.epoch;for(int j=0;j<4;j++){need(d.done&&!d.cmd_ready&&d.status==status&&d.epoch==epoch,"held done");step();held_done++;}d.ack=1;step();d.ack=0;need(!d.busy,"ack idle");}
template<class T>static void array_json(const T&v){out<<"[";for(size_t i=0;i<v.size();i++){if(i)out<<",";out<<v[i];}out<<"]";}
static void finish(const Case&c,int cache,int stream,const std::string&role){wait_done();records_written++;auto active_edges=ticks-accepted_tick;unsigned status=d.status;need(status==(c.epsilon==0?2u:0u),"expected numeric status");if(!c.kind)need(accs.size()==12288&&downs.size()==12288&&joins.size()==1536,"all full M observations");else need(accs.empty()&&downs.empty()&&joins.empty(),"no hidden M in norm-only");
 auto cy=d.cycles,ncy=d.norm_cycles;auto epoch=d.epoch;auto reads=d.reads,writes=d.writes,packets=d.packets,macs=d.macs,mw=d.mwrites,cr=d.cache_reads,cw=d.cache_writes;auto beats=d.wire_beats-b0,tx=d.transactions-t0,mg0=d.mul_grants0-g0,mg1=d.mul_grants1-g1,gl=d.gamma_loads,gs=d.gamma_stores,de=d.den_events,pm=d.port_wait_m,pn=d.port_wait_n;
 W sum={d.observed_sum[0],d.observed_sum[1],d.observed_sum[2],d.observed_sum[3]},den={d.observed_den[0],d.observed_den[1],d.observed_den[2],d.observed_den[3]};ack();track=false;auto begin=ticks;std::vector<int32_t>result;if(status==0)for(int j=0;j<c.h/4;j++){auto ws=cfg(false,j);for(int k=0;k<4;k++)result.push_back(int32_t(ws[k]));}auto result_edges=ticks-begin;
 begin=ticks;for(auto i:guard_lines){need(cfg(false,i)==canary(i),"frame/gap/A canary unchanged");canary_checks++;}if(!c.kind&&cache)for(int i=0;i<256;i++){need(cfg(false,768+i)==bytes_word(payload,i*16),"A cache matches source throughout norm");canary_checks++;}auto guard_result=ticks-begin;
 out<<"{\"name\":\""<<c.name<<"\",\"role\":\""<<role<<"\",\"kind\":"<<c.kind<<",\"h\":"<<c.h<<",\"cache\":"<<cache<<",\"gamma_stream\":"<<stream<<",\"gamma_fault\":"<<gamma_fault<<",\"epoch\":"<<epoch<<",\"status\":"<<status<<",\"cycles\":"<<cy<<",\"active_edges\":"<<active_edges<<",\"norm_cycles\":"<<ncy<<",\"reads\":"<<reads<<",\"writes\":"<<writes<<",\"M_packets\":"<<(c.kind?0:packets)<<",\"M_MACs\":"<<(c.kind?0:macs)<<",\"M_store_lines\":"<<(c.kind?0:mw)<<",\"wire_beats\":"<<beats<<",\"transactions\":"<<tx<<",\"cache_reads\":"<<(c.kind?0:cr)<<",\"cache_writes\":"<<(c.kind?0:cw)<<",\"mul_grants0\":"<<mg0<<",\"mul_grants1\":"<<mg1<<",\"gamma_loads\":"<<gl<<",\"gamma_stores\":"<<gs<<",\"den_events\":"<<de<<",\"port_wait_m\":"<<pm<<",\"port_wait_n\":"<<pn<<",\"setup_edges\":"<<setup<<",\"command_edges\":"<<command_edges<<",\"completion_edges\":5,\"result_edges\":"<<result_edges<<",\"total_edges\":"<<setup+command_edges+active_edges+5+result_edges<<",\"guard_setup_edges\":"<<guard_setup<<",\"guard_result_edges\":"<<guard_result<<",\"acc\":";array_json(accs);out<<",\"down\":";array_json(downs);out<<",\"joined\":";array_json(joins);out<<",\"out\":";array_json(result);out<<",\"sum_words\":";array_json(sum);out<<",\"den_words\":";array_json(den);out<<",\"gamma_addresses\":";array_json(gamma_addresses);out<<",\"gamma_words\":";array_json(gamma_words);out<<",\"external_gamma_addresses\":";array_json(external_gamma_addresses);out<<"}\n";
}
static void abort_now(){auto e=d.epoch;d.soft_abort=1;step();d.soft_abort=0;track=false;need(!d.busy&&!d.done&&d.epoch==(e==0xffffffffu?e:e+1),"abort drains control/no wrap");d.cmd=0;}
static void hard_reset(){d.cmd=0;d.cfg=0;d.ack=0;d.soft_abort=0;hold_external=false;track=false;d.reset=1;step();d.reset=0;step();need(d.epoch==0&&!d.busy&&!d.done&&fifo.empty(),"coordinated reset");}
static void control_priority(){for(bool hard:{false,true}){hard_reset();cfg(true,740,canary(740));d.cfg=1;d.cfg_wr=1;d.cfg_addr=740;d.cfg_take=1;d.cfg_din[0]=0xdeadbeef;d.reset=hard;d.soft_abort=!hard;d.eval();need(!d.cfg_ready&&!d.cfg_valid&&!d.done,"reset masks cfg outputs");auto e=step();need(!e.cfg_req&&!e.cfg_rsp&&!e.command,"reset/cfg priority");d.cfg=0;d.reset=d.soft_abort=0;step();need(cfg(false,740)==canary(740),"cancelled cfg write");control_conflicts++;
 d.cfg=1;d.cfg_wr=0;d.cfg_take=0;need(step().cfg_req,"pending cfg accepted");d.cfg=0;step();need(d.cfg_valid,"cfg held");d.reset=hard;d.soft_abort=!hard;d.cfg_take=1;d.eval();need(!d.cfg_valid&&!d.cfg_ready&&!d.done,"reset masks pending");e=step();need(!e.cfg_rsp,"no reset response");d.reset=d.soft_abort=0;step();need(!d.cfg_valid,"no ghost cfg");control_conflicts++;}}
int main(int argc,char**argv){try{Verilated::commandArgs(argc,argv);need(argc==4,"vectors output stall");stall=std::stoi(argv[3]);hard_reset();std::ifstream in(argv[1]);out.open(argv[2]);need(bool(in)&&bool(out),"files");std::vector<Case>cases;Case c;while(in>>c.name>>c.kind>>c.h>>c.epsilon>>c.coefficient>>c.p0>>c.p1>>c.g>>c.x)cases.push_back(c);need(cases.size()==12,"six Granite/two Gemma/four synthetic cases");
 for(auto&v:cases){if(!v.kind)for(int cache=0;cache<2;cache++)for(int stream=0;stream<2;stream++){prepare(v,cache,stream);start();finish(v,cache,stream,"primary");}else{prepare(v,1,1);start();finish(v,1,1,"primary");}}
 c=cases[6];for(int state:{4,8,20,21,22,23,11,15,17}){prepare(c,1,1);start();auto begin=ticks;while(!(d.debug_state==3&&d.ndebug==state)){step();need(ticks-begin<1000000,"reach norm abort stage");}abort_now();for(int j=0;j<10;j++){step();need(!d.done,"no ghost completion");}aborts_tested++;prepare(c,1,1);start(state==20);finish(c,1,1,"restart-stage-"+std::to_string(state));}
 for(int fault=0;fault<5;fault++){prepare(c,1,1);if(fault==0)d.h=1537;if(fault==1)d.norm_only=0;if(fault==2)d.gamma_address=GBASE+1;if(fault==3)d.gamma_address=0;if(fault==4)d.gamma_stream=0;start();wait_done();need(d.status==((fault==2||fault==3)?17:16),"rejected shape/address/alias");need(external_gamma_addresses.empty(),"invalid descriptor no DMA");ack();errors++;prepare(c,1,1);start();finish(c,1,1,"restart-error-"+std::to_string(fault));}
 // Accepted old gamma response may overlap a new request only in this explicit two-slot external test fabric.
 prepare(c,1,1);start();while(!(d.debug_state==3&&d.ndebug==20))step();hold_external=true;auto begin=ticks;while(fifo.empty()){step();need(ticks-begin<100,"old gamma read");}abort_now();prepare(c,1,1);start();begin=ticks;while(fifo.size()<2){step();need(ticks-begin<1000000,"old/new gamma replies finite FIFO");}hold_external=false;finish(c,1,1,"restart-stale-gamma");need(d.stale_responses>=1&&fifo.empty(),"old epoch discarded");
 auto old_aborts=d.aborts,old_stale=d.stale_responses;control_priority();prepare(c,1,1);start();while(!(d.debug_state==3&&d.ndebug==22))step();d.reset=1;step();d.reset=0;track=false;step();prepare(c,1,1);start();finish(c,1,1,"restart-hard-reset");
 // Real epoch register injection in quiescent DUT; then legal final gamma command and terminal drain.
 need(!d.busy&&fifo.empty(),"idle epoch injection");d.epoch=0xfffffffeu;d.eval();step();need(d.epoch==0xfffffffeu,"actual terminal seed");prepare(c,1,1);start();finish(c,1,1,"last-legal-epoch");d.cmd=1;for(int i=0;i<5;i++){need(!step().command&&!d.cmd_ready&&d.epoch==0xffffffffu,"terminal commands blocked");terminal_rejects++;}d.cmd=0;auto st=d.stale_responses;fifo.push_back({0xffffffffu,0,{1,2,3,4}});step();need(fifo.empty()&&d.stale_responses==st+1&&!d.done,"terminal matching response discarded");hard_reset();
 c=cases[9];for(int fault=1;fault<=2;fault++){prepare(c,1,1,fault);start();finish(c,1,1,fault==1?"negative-shifted-gamma":"negative-stale-gamma");negative_runs++;}
 std::ofstream p(std::string(argv[2])+".protocol.json");p<<"{\"schema\":\"gamma93-protocol-v1\",\"commands_accepted\":"<<commands<<",\"abort_stages\":"<<aborts_tested<<",\"invalid_commands\":"<<errors<<",\"blocked_command_edges\":"<<blocked_edges<<",\"held_done_edges\":"<<held_done<<",\"parameter_mutations\":"<<parameter_mutations<<",\"soft_aborts_before_reset\":"<<old_aborts<<",\"stale_before_reset\":"<<old_stale<<",\"control_reset_conflicts\":"<<control_conflicts<<",\"terminal_rejected_edges\":"<<terminal_rejects<<",\"negative_RTL_runs\":"<<negative_runs<<",\"sum_barrier_checks\":"<<sum_barrier_checks<<",\"canary_line_checks\":"<<canary_checks<<",\"fabric_response_high_water\":"<<fabric_high_water<<",\"records_written\":"<<records_written<<"}\n";
 std::cout<<"PASS_GAMMA_RTL_EXECUTION records=49\n";return 0;
 }catch(const std::exception&e){std::cerr<<e.what()<<" state="<<unsigned(d.debug_state)<<" M="<<unsigned(d.mdebug)<<" N="<<unsigned(d.ndebug)<<" status="<<unsigned(d.status)<<" epoch="<<d.epoch<<"\n";return 1;}}
