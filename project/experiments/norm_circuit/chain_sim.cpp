#include "Vchain82.h"
#include "verilated.h"
#include <array>
#include <vector>
#include <fstream>
#include <iostream>
#include <stdexcept>
using W=std::array<uint32_t,4>;static Vchain82 d;static uint64_t ticks=0;static int stall=0,waits=0;static bool seen=false;static uint64_t serial=0;
static void need(bool b,const char*s){if(!b)throw std::runtime_error(s);}
struct E{bool req,rsp;W data;};
static std::vector<uint8_t> payload;static bool pending_ext=false;static int response_wait=0;static W response_data{};static uint64_t ext_serial=0;
static std::vector<int32_t> accs,downs,joins;
static E step(){
 d.clk=0;d.ext_ready=!pending_ext;d.ext_valid=pending_ext&&response_wait==0;for(int j=0;j<4;j++)d.ext_data[j]=response_data[j];d.eval();
 bool accept=d.ext_req&&d.ext_ready,retire=d.ext_valid&&d.ext_take;auto address=d.ext_addr;
 if(d.obs_valid){accs.push_back(d.obs_acc);downs.push_back(d.obs_down);}
 if(d.mem_request&&!seen){seen=true;waits=stall?serial%3:0;serial++;}d.mem_hold=waits>0;d.eval();
 if(d.mwrite)for(int j=0;j<4;j++)joins.push_back(d.mdata[j]);
 E e{bool(d.cfg&&d.cfg_ready),bool(d.cfg_valid&&d.cfg_take),{d.cfg_dout[0],d.cfg_dout[1],d.cfg_dout[2],d.cfg_dout[3]}};
 d.clk=1;d.eval();d.clk=0;d.eval();ticks++;
 if(d.reset){pending_ext=false;response_wait=0;ext_serial=0;}
 else {if(response_wait>0)response_wait--;if(retire)pending_ext=false;if(accept){need(address%16==0&&address+16<=payload.size(),"actual M input address");response_data={};for(int j=0;j<16;j++)response_data[j/4]|=uint32_t(payload[address+j])<<(8*(j%4));pending_ext=true;response_wait=stall?1+(ext_serial++%5):1;}}
 if(waits>0)waits--;if(!d.mem_request)seen=false;return e;
}
static W cfg(bool wr,int addr,W w={}){d.cfg=1;d.cfg_wr=wr;d.cfg_addr=addr;d.cfg_take=1;for(int i=0;i<4;i++)d.cfg_din[i]=w[i];int n=0;while(!step().req)need(++n<100,"cfg ready");d.cfg=0;for(n=0;n<100;n++){auto e=step();if(e.rsp)return e.data;}throw std::runtime_error("cfg response");}
static std::vector<uint8_t> unhex(std::string s){std::vector<uint8_t>r;if(s=="-")return r;for(size_t i=0;i<s.size();i+=2)r.push_back(std::stoul(s.substr(i,2),nullptr,16));return r;}
static void load(std::string s,int base){auto a=unhex(s);for(size_t j=0;j<a.size();j+=16){W w{};for(int i=0;i<16;i++)w[i/4]|=uint32_t(a[j+i])<<(8*(i%4));cfg(true,base+j/16,w);}}
int main(int argc,char**argv){try{Verilated::commandArgs(argc,argv);need(argc==4,"vectors output stall");stall=std::stoi(argv[3]);d.reset=1;step();step();d.reset=0;step();
 std::ifstream in(argv[1]);std::ofstream out(argv[2]);need(bool(in)&&bool(out),"files");std::string name,file,g;unsigned coefficient;int count=0;
 auto array=[&](const std::vector<int32_t>&v){out<<"[";for(size_t i=0;i<v.size();i++){if(i)out<<",";out<<v[i];}out<<"]";};
 while(in>>name>>file>>g>>coefficient){std::ifstream bin(file,std::ios::binary);payload.assign(std::istreambuf_iterator<char>(bin),{});need(payload.size()==12779520,"finite actual M payload");accs.clear();downs.clear();joins.clear();serial=0;seen=false;waits=0;ext_serial=0;auto start=ticks;load(g,384);auto setup=ticks-start;auto b0=d.wire_beats,t0=d.transactions;d.epsilon=17;d.coefficient=coefficient;d.cmd=1;step();d.cmd=0;d.epsilon=0;d.coefficient=0;start=ticks;
 while(!d.done){step();need(ticks-start<30000000,"chain watchdog");need(!d.cfg_ready,"busy blocks cfg");}
 auto cy=d.cycles,ncy=d.norm_cycles;auto r=d.reads,w=d.writes;auto packets=d.packets,macs=d.macs,mw=d.mwrites;auto beats=d.wire_beats-b0,transactions=d.transactions-t0;unsigned st=d.status;
 need(st==0,"M/full norm status");need(accs.size()==12288&&downs.size()==12288&&joins.size()==1536,"full M observation counts");need(beats==transactions*5,"all serialized link beats");
 for(int j=0;j<3;j++){step();need(d.done&&d.status==st,"held done/status");}d.ack=1;step();d.ack=0;auto begin=ticks;std::vector<int32_t> result;
 for(int j=0;j<384;j++){auto words=cfg(false,j);for(int k=0;k<4;k++)result.push_back(int32_t(words[k]));}
 out<<"{\"name\":\""<<name<<"\",\"status\":"<<st<<",\"cycles\":"<<cy<<",\"norm_cycles\":"<<ncy<<",\"reads\":"<<r<<",\"writes\":"<<w<<",\"M_packets\":"<<packets<<",\"M_MACs\":"<<macs<<",\"M_store_lines\":"<<mw<<",\"wire_beats\":"<<beats<<",\"transactions\":"<<transactions<<",\"setup_edges\":"<<setup<<",\"result_edges\":"<<ticks-begin<<",\"acc\":";array(accs);out<<",\"down\":";array(downs);out<<",\"joined\":";array(joins);out<<",\"out\":";array(result);out<<"}\n";count++;
 }
 cfg(true,900,{0xa5a5a5a5,0xa5a5a5a5,0xa5a5a5a5,0xa5a5a5a5});d.cmd=1;step();d.cmd=0;int abort_wait=0;while(d.macs<64){step();need(++abort_wait<10000,"active M reset reached");}d.reset=1;step();d.reset=0;for(int j=0;j<20;j++){step();need(!d.done,"no stale M completion");}need(cfg(false,900)[0]==0xa5a5a5a5,"M reset SRAM retention");
 std::ofstream proto(std::string(argv[2])+".protocol.json");proto<<"{\"actual_M_active_reset\":true,\"no_stale_completion\":true,\"SRAM_retained\":true}\n";
 std::cout<<"FULL_M_CONSUMER_RTL_EXECUTED "<<count<<"\n";return 0;
 }catch(const std::exception&e){std::cerr<<e.what()<<" state="<<unsigned(d.debug_state)<<" status="<<unsigned(d.status)<<"\n";return 1;}}
