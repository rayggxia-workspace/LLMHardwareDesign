#include "Vblock82.h"
#include "verilated.h"
#include <array>
#include <vector>
#include <fstream>
#include <iostream>
#include <stdexcept>
using W=std::array<uint32_t,4>;static Vblock82 d;static uint64_t ticks=0;static int stall=0,waits=0;static bool seen=false;static uint64_t serial=0;
static void need(bool b,const char*s){if(!b)throw std::runtime_error(s);}
struct E{bool req,rsp;W data;};
static E step(){
 d.clk=0;d.eval();if(d.mem_request&&!seen){seen=true;waits=stall?serial%3:0;serial++;}d.mem_hold=waits>0;d.eval();
 E e{bool(d.cfg&&d.cfg_ready),bool(d.cfg_valid&&d.cfg_take),{d.cfg_dout[0],d.cfg_dout[1],d.cfg_dout[2],d.cfg_dout[3]}};
 d.clk=1;d.eval();d.clk=0;d.eval();ticks++;if(waits>0)waits--;if(!d.mem_request)seen=false;return e;
}
static W cfg(bool wr,int addr,W w={}){d.cfg=1;d.cfg_wr=wr;d.cfg_addr=addr;d.cfg_take=1;for(int i=0;i<4;i++)d.cfg_din[i]=w[i];int n=0;while(!step().req)need(++n<100,"cfg ready");d.cfg=0;for(n=0;n<100;n++){auto e=step();if(e.rsp)return e.data;}throw std::runtime_error("cfg response");}
static std::vector<uint8_t> unhex(std::string s){std::vector<uint8_t>r;if(s=="-")return r;for(size_t i=0;i<s.size();i+=2)r.push_back(std::stoul(s.substr(i,2),nullptr,16));return r;}
static void load(std::string s,int base){auto a=unhex(s);for(size_t j=0;j<a.size();j+=16){W w{};for(int i=0;i<16;i++)w[i/4]|=uint32_t(a[j+i])<<(8*(i%4));cfg(true,base+j/16,w);}}
int main(int argc,char**argv){try{Verilated::commandArgs(argc,argv);need(argc==4,"vectors output stall");stall=std::stoi(argv[3]);d.reset=1;step();step();d.reset=0;step();
 std::ifstream in(argv[1]);std::ofstream out(argv[2]);need(bool(in)&&bool(out),"files");std::string name,x,g;unsigned h,eps;int count=0;
 while(in>>name>>h>>eps>>x>>g){serial=0;seen=false;waits=0;auto start=ticks;load(x,0);load(g,384);auto setup=ticks-start;d.h=h;d.epsilon=eps;d.cmd=1;step();d.cmd=0;start=ticks;
 while(!d.done){step();need(ticks-start<2000000,"norm watchdog");need(!d.cfg_ready,"busy blocks cfg");}
 auto cy=d.cycles;auto r=d.reads,w=d.writes;unsigned st=d.status;for(int j=0;j<3;j++){step();need(d.done&&d.status==st,"held done/status");}d.ack=1;step();d.ack=0;auto begin=ticks;
 out<<"{\"name\":\""<<name<<"\",\"status\":"<<st<<",\"cycles\":"<<cy<<",\"reads\":"<<r<<",\"writes\":"<<w<<",\"setup_edges\":"<<setup<<",\"out\":[";
 int n=(h<=1536&&h>0)?h:0;for(int j=0;j<(n+3)/4;j++){auto words=cfg(false,j);for(int k=0;k<4&&4*j+k<n;k++){if(4*j+k)out<<",";out<<int32_t(words[k]);}}
 out<<"],\"result_edges\":"<<ticks-begin<<"}\n";count++;
 }
 // Actual active compute reset and SRAM retention, without clearing data.
 cfg(true,900,{0xa5a5a5a5,0xa5a5a5a5,0xa5a5a5a5,0xa5a5a5a5});d.h=8;d.epsilon=17;d.cmd=1;step();d.cmd=0;int n=0;while(d.debug_state!=4){step();need(++n<1000,"reset target");}d.reset=1;step();d.reset=0;for(int i=0;i<20;i++){step();need(!d.done,"no stale done");}auto mark=cfg(false,900);need(mark[0]==0xa5a5a5a5,"SRAM retention");
 std::ofstream p(std::string(argv[2])+".protocol.json");p<<"{\"actual_active_reset\":true,\"SRAM_retained\":true,\"no_stale_completion\":true}\n";std::cout<<"RTL_EXECUTED "<<count<<"\n";return 0;
 }catch(const std::exception&e){std::cerr<<e.what()<<" state="<<unsigned(d.debug_state)<<"\n";return 1;}}
