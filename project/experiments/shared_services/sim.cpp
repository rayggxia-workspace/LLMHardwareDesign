#include "Vshared106.h"
#include "verilated.h"
#include <array>
#include <vector>
#include <deque>
#include <fstream>
#include <iostream>
#include <sstream>
#include <iomanip>
#include <filesystem>
#include <stdexcept>
using W=std::array<uint32_t,4>;
static Vshared106 d;static uint64_t ticks=0;static int stall=0;static unsigned accepted=0,highwater=0,external_accepted=0,root_writes=0;static bool hold_reply=false,hold_result=false;
struct Reply{uint32_t epoch;int delay;W data;};static std::deque<Reply> fifo;
struct MC{std::string name,g,w,gamma;uint32_t coef;};struct AC{std::string name,q,k,v;unsigned len;int ke,ve;uint64_t qe;unsigned version;};
static std::vector<MC> mc;static std::vector<AC> ac;static std::string rpath,lutpath;static int initial_unit;
static std::vector<uint8_t> gu,records,gamma_bytes,qbytes,kbytes,vbytes,lut,rimage;static std::ofstream out;
static std::vector<int32_t> mids,codes,accs,downs,joins,qk,score,exp1,probs,outputs;static std::vector<uint64_t>sums;static unsigned current_length=0;static uint32_t start_sread,start_swrite,start_m0,start_m1,start_f,start_tx,start_beats,start_lines,start_roots;static uint64_t before;
static void need(bool b,const char*s){if(!b)throw std::runtime_error(s);}
static void readfile(const std::string&p,std::vector<uint8_t>&v){std::ifstream f(p,std::ios::binary);need(bool(f),"input file");v.assign(std::istreambuf_iterator<char>(f),{});}
static W word(const std::vector<uint8_t>&v,uint32_t offset){need(offset+16<=v.size(),"finite payload");W w{};for(int j=0;j<16;j++)w[j/4]|=uint32_t(v[offset+j])<<(8*(j%4));return w;}
static W memory(uint32_t a,bool wr,W w){need(a%16==0,"external alignment");if(a>=0x06000000&&a<0x06100000){unsigned off=a-0x06000000;if(wr){for(int j=0;j<16;j++)rimage[off+j]=uint8_t(w[j/4]>>(8*(j%4)));if(off==0xa0400)root_writes++;return {};}return word(rimage,off);}
 need(!wr,"readonly M/A/LUT");if(a>=0x04000000&&uint64_t(a)<0x04000000ull+gu.size())return word(gu,a-0x04000000);
 if(a>=0x04100000&&uint64_t(a)<0x04100000ull+records.size())return word(records,a-0x04100000);
 if(a>=0x04800000&&uint64_t(a)<0x04800000ull+gamma_bytes.size())return word(gamma_bytes,a-0x04800000);
 if(a>=0x05000000&&uint64_t(a)<0x05000000ull+current_length*256)return word(kbytes,a-0x05000000);
 if(a>=0x05100000&&uint64_t(a)<0x05100000ull+current_length*256)return word(vbytes,a-0x05100000);
 if(a>=0x02000000&&a<0x02020000)return word(lut,a-0x02000000);
 throw std::runtime_error("unallocated external address "+std::to_string(a));}
struct Event{bool command,cfg_req,cfg_rsp,abort;W data;};
static Event step(){d.clk=0;d.ext_ready=fifo.size()<2&&(!stall||ticks%7!=0);d.ext_valid=!fifo.empty()&&!hold_reply&&fifo.front().delay==0;d.response_epoch=fifo.empty()?0:fifo.front().epoch;for(int j=0;j<4;j++)d.ext_data[j]=fifo.empty()?0:fifo.front().data[j];d.mem_hold=stall&&ticks%5<2;d.mul_hold=stall&&ticks%7<2;d.result_take=!hold_result&&(!stall||ticks%5>=2);d.eval();
 bool ext_ac=d.ext_req&&d.ext_ready,ext_re=d.ext_valid&&d.ext_take;auto addr=d.ext_addr,epoch=d.ext_epoch;bool wr=d.ext_wr;W wd{d.ext_wdata[0],d.ext_wdata[1],d.ext_wdata[2],d.ext_wdata[3]};
 if(d.reset)need(!d.ext_req&&!d.ext_take&&!d.cmd_accept&&!d.cfg_ready&&!d.cfg_valid&&!d.done&&!d.result_valid,"hard reset handshakes");
 if(d.owner==0&&d.busy){if(d.obs_mid_valid){need(d.obs_index==mids.size(),"MID order");mids.push_back(d.obs_mid);}if(d.obs_a_valid){need(d.obs_index==codes.size(),"A8 order");codes.push_back(int8_t(d.obs_a));}if(d.m_obs_valid){need(unsigned(d.m_obs_row)*8+d.m_obs_rank==accs.size(),"M order");accs.push_back(d.m_obs_acc);downs.push_back(d.m_obs_down);}if(d.swrite_event&&d.mdebug==5&&d.swrite_addr<384)for(int j=0;j<4;j++)joins.push_back(d.swrite_data[j]);}
 if(d.owner==1&&d.busy&&d.a_obs_valid){unsigned ix=d.a_obs_head*current_length+d.a_obs_key;if(d.a_obs_kind==0){need(ix==qk.size(),"QK order");qk.push_back(d.a_obs_x);score.push_back(d.a_obs_y);}else if(d.a_obs_kind==1){need(ix==exp1.size(),"exp order");exp1.push_back(d.a_obs_x);if(d.a_obs_key+1==current_length)sums.push_back(d.a_obs_sum);}else if(d.a_obs_kind==2){need(ix==probs.size(),"P order");probs.push_back(d.a_obs_x);need(d.a_obs_y==exp1[ix],"exp repeated words");}else need(false,"observer type");}
 if(d.result_valid&&d.result_take){need(d.result_index*4==outputs.size(),"actual export order");need(d.result_candidate==(d.owner==2),"candidate result type");for(int j=0;j<4;j++)outputs.push_back(d.result_data[j]);}
 Event e{bool(d.cmd_accept),bool(d.cfg&&d.cfg_ready),bool(d.cfg_valid&&d.cfg_take),bool(d.abort_accept),{d.cfg_dout[0],d.cfg_dout[1],d.cfg_dout[2],d.cfg_dout[3]}};
 d.clk=1;d.eval();d.clk=0;d.eval();ticks++;
 if(d.reset)fifo.clear();else{for(auto&f:fifo)if(f.delay)f.delay--;if(ext_re)fifo.pop_front();if(ext_ac){auto data=memory(addr,wr,wd);fifo.push_back({epoch,stall?1+int(external_accepted%5):1,data});external_accepted++;if(fifo.size()>highwater)highwater=fifo.size();}}
 return e;}
static W config(bool wr,unsigned addr,W w={}){d.cfg=1;d.cfg_wr=wr;d.cfg_addr=addr;d.cfg_take=1;for(int j=0;j<4;j++)d.cfg_din[j]=w[j];unsigned n=0;while(!step().cfg_req)need(++n<100,"cfg request");d.cfg=0;for(n=0;n<100;n++){auto e=step();if(e.cfg_rsp)return e.data;}throw std::runtime_error("cfg reply");}
static void clear(){mids.clear();codes.clear();accs.clear();downs.clear();joins.clear();qk.clear();score.clear();exp1.clear();sums.clear();probs.clear();outputs.clear();start_sread=d.sreads;start_swrite=d.swrites;start_m0=d.mul_grants0;start_m1=d.mul_grants1;start_f=d.fgrants;start_tx=d.transactions;start_beats=d.wire_beats;start_lines=d.result_lines;start_roots=root_writes;before=ticks;}
static void prepare_m(unsigned i){auto&c=mc.at(i);readfile(c.g,gu);readfile(c.w,records);readfile(c.gamma,gamma_bytes);need(gu.size()==32768&&records.size()==6488064&&gamma_bytes.size()==6144,"M original sizes");d.command_kind=0;d.gateup_address=0x04000000;d.records_address=0x04100000;d.gamma_address=0x04800000;d.m_owner=0x1234;d.m_version=accepted+1;d.epsilon=17;d.coefficient=c.coef;clear();}
static void prepare_a(unsigned i){auto&c=ac.at(i);readfile(c.q,qbytes);readfile(c.k,kbytes);readfile(c.v,vbytes);need(qbytes.size()==1024&&kbytes.size()==vbytes.size(),"A original shape");current_length=c.len;for(int j=0;j<64;j++)config(true,j,word(qbytes,16*j));d.command_kind=1;d.length=c.len;d.position=c.len-1;d.window=0;d.query_units=c.qe;d.key_unit=c.ke;d.value_unit=c.ve;d.key_address=0x05000000;d.value_address=0x05100000;d.a_owner=0x1234;d.a_version=c.version;d.score_multiplier=94906266;clear();}
static void prepare_r(unsigned command){d.command_kind=2;d.r_command=command;d.r_head=0;d.r_initial_unit=initial_unit;d.r_expected_position=d.r_position;clear();}
static void start(){auto old=d.epoch;d.cmd=1;unsigned n=0;while(!step().command)need(++n<40,"command handshake");d.cmd=0;accepted++;need(d.epoch==old+1,"one lease one epoch");d.command_kind=3;d.gateup_address=d.records_address=d.gamma_address=0xffffffff;d.m_owner=d.m_version=d.epsilon=d.coefficient=0;d.length=d.position=0;d.window=65535;d.query_units=0;d.key_unit=127;d.value_unit=-128;d.key_address=d.value_address=0xffffffff;d.a_owner=d.a_version=d.score_multiplier=0;d.r_command=3;d.r_head=31;d.r_initial_unit=127;d.r_expected_position=0xffffffff;}
static void waitdone(bool reject=false){uint64_t begin=ticks;while(!d.done){if(d.candidate_ready){need(outputs.size()==128,"consumer sees full actual Y before commit");d.accept_candidate=!reject;d.reject_candidate=reject;}step();d.accept_candidate=d.reject_candidate=0;need(ticks-begin<40000000,"complete consumer watchdog");need(!d.cmd_ready&&!d.cfg_ready,"lease protects bank");}}
static void release(){unsigned st=d.status,ep=d.epoch;for(int j=0;j<4;j++){need(d.done&&d.status==st&&d.epoch==ep&&!d.cmd_ready,"held DONE");step();}need(d.services_drained&&fifo.empty(),"release fully drained");d.ack=1;step();d.ack=0;need(!d.busy,"lease released");}
template<class T>static void array(std::ostream&o,const std::vector<T>&v){o<<'[';for(size_t j=0;j<v.size();j++){if(j)o<<',';o<<v[j];}o<<']';}
static std::string hex128(const VlWide<4>&v){std::ostringstream s;s<<std::hex<<std::setfill('0');for(int j=3;j>=0;j--)s<<std::setw(8)<<v[j];return s.str();}
static void finish(const std::string&name,const std::string&role,unsigned expected=0,bool reject=false){waitdone(reject);need(d.status==expected,"expected command status");unsigned kind=d.owner;std::vector<int32_t>state,delta,committed_y;
 if(kind==2){unsigned off=d.r_bank?0x20000:0;for(unsigned i=0;i<8192;i++){auto w=word(rimage,off+16*i);for(auto x:w)state.push_back(int32_t(x));}for(unsigned i=0;i<32;i++){auto w=word(rimage,0xa0000+(d.r_bank?0x200:0)+16*i);for(auto x:w)committed_y.push_back(int32_t(x));}}
 if(kind==0)for(unsigned j=0;j<8;j++)delta.push_back(int16_t(d.deltas[j/2]>>(16*(j%2))));
 out<<"{\"kind\":"<<kind<<",\"name\":\""<<name<<"\",\"role\":\""<<role<<"\",\"status\":"<<unsigned(d.status)<<",\"epoch\":"<<d.epoch<<",\"cycles\":"<<d.cycles<<",\"elapsed\":"<<ticks-before<<",\"compute_cycles\":"<<(kind==0?d.m_cycles:kind==1?d.a_cycles:d.r_cycles)<<",\"export_cycles\":"<<d.export_cycles<<",\"drain_cycles\":"<<d.drain_cycles<<",\"sreads\":"<<d.sreads-start_sread<<",\"swrites\":"<<d.swrites-start_swrite<<",\"mul0\":"<<d.mul_grants0-start_m0<<",\"mul1\":"<<d.mul_grants1-start_m1<<",\"fgrants\":"<<d.fgrants-start_f<<",\"transactions\":"<<d.transactions-start_tx<<",\"wire_beats\":"<<d.wire_beats-start_beats<<",\"result_lines\":"<<d.result_lines-start_lines<<",\"root_writes\":"<<root_writes-start_roots<<",\"cache_owner\":"<<d.cache_owner<<",\"cache_version\":"<<d.cache_version<<",\"cache_length\":"<<d.cache_length<<",\"r_position\":"<<d.r_position<<",\"r_unit\":"<<int16_t(d.r_unit)<<",\"r_epoch\":"<<d.r_numeric_epoch<<",\"r_bank\":"<<unsigned(d.r_bank)<<",\"r_retries\":"<<unsigned(d.r_retries)<<",\"sum_hex\":\""<<hex128(d.observed_sum)<<"\",\"den_hex\":\""<<hex128(d.observed_den)<<"\"";
 #define ARR(n,v) out<<",\"" n "\":";array(out,v)
 ARR("mid",mids);ARR("A8",codes);ARR("delta",delta);ARR("acc",accs);ARR("down",downs);ARR("joined",joins);ARR("qk",qk);ARR("score",score);ARR("exp",exp1);ARR("sum",sums);ARR("P",probs);ARR("out",outputs);ARR("state",state);ARR("committed_y",committed_y);out<<"}\n";out.flush();release();}
static void load(const std::string&path){std::ifstream f(path);need(bool(f),"vectors");std::string type;while(f>>type){if(type=="M"){MC c;f>>c.name>>c.g>>c.w>>c.gamma>>c.coef;mc.push_back(c);}else if(type=="A"){AC c;f>>c.name>>c.q>>c.k>>c.v>>c.len>>c.ke>>c.ve>>c.qe>>c.version;ac.push_back(c);}else if(type=="R")f>>rpath>>initial_unit;else if(type=="L")f>>lutpath;else need(false,"vector type");}need(mc.size()==2&&ac.size()==2,"frozen mixed sequence");readfile(rpath,rimage);readfile(lutpath,lut);need(rimage.size()==1048576&&lut.size()==131072,"external finite inventories");}
static void reset(){d.reset=1;step();d.reset=0;step();}
int main(int argc,char**argv){try{Verilated::commandArgs(argc,argv);need(argc==5,"vectors output stall pilot");stall=std::stoi(argv[3]);int pilot=std::stoi(argv[4]);load(argv[1]);out.open(argv[2]);need(bool(out),"output");reset();prepare_r(0);start();finish("head0","init");
 prepare_m(0);start();finish(mc[0].name,"mixed-M0");prepare_a(0);start();finish(ac[0].name,"mixed-Afull");prepare_r(1);start();finish("head0","mixed-R0");
 if(!pilot){prepare_a(1);start();finish(ac[1].name,"mixed-Acached");prepare_m(1);start();finish(mc[1].name,"mixed-M5");prepare_r(1);start();finish("head0","mixed-R1");}
 std::ofstream p(std::string(argv[2])+".protocol.json");p<<"{\"schema\":\"shared106-mixed/1\",\"accepted\":"<<accepted<<",\"leases\":"<<d.leases<<",\"same_core_no_per_case_reset\":true,\"held_done\":true,\"latched_parameters\":true,\"fabric_high_water\":"<<highwater<<",\"external_accepted\":"<<external_accepted<<",\"root_writes\":"<<root_writes<<",\"aborts\":"<<d.aborts<<",\"stale\":"<<d.stale_responses<<"}\n";std::cout<<"EXECUTED_SHARED_M_A_R_NOT_YET_RECEIVED\n";return 0;
 }catch(const std::exception&e){std::cerr<<e.what()<<" D="<<unsigned(d.debug_state)<<" owner="<<unsigned(d.owner)<<" M="<<unsigned(d.mdebug)<<" A="<<unsigned(d.adebug)<<" R="<<unsigned(d.rdebug)<<" status="<<unsigned(d.status)<<" ticks="<<ticks<<"\n";return 1;}}
