#include "Vwide_block.h"
#include "verilated.h"
#include <array>
#include <vector>
#include <fstream>
#include <sstream>
#include <iostream>
#include <stdexcept>
#include <cstdint>
using W=std::array<uint32_t,4>;
static Vwide_block d; static std::vector<uint8_t> code;static uint64_t tickno=0;static int stall=0;
static bool pending=false;static int delay=0;static W response{};
static bool old_blocked=false;static uint32_t old_addr=0;static bool old_wr=false;static W old_wdata{};
static void require(bool b,const char*s){if(!b)throw std::runtime_error(s);}
template<class T>static W get(const T&v){return {v[0],v[1],v[2],v[3]};}
template<class T>static void set(T&v,const W&a){for(int i=0;i<4;i++)v[i]=a[i];}
struct Event{bool cfg=false,cfg_rsp=false;W cfgdata{};};
static Event step(){
 d.clk=0;d.ext_ready=!pending&&(!stall||tickno%7!=0);d.ext_valid=pending&&delay==0;set(d.ext_rdata,response);d.eval();
 Event e{bool(d.cfg_valid&&d.cfg_ready),bool(d.cfg_response&&d.cfg_take),get(d.cfg_result)};
 bool accept=d.ext_req&&d.ext_ready, retire=d.ext_valid&&d.ext_take;uint32_t addr=d.ext_addr;bool wr=d.ext_write;W wd=get(d.ext_wdata);
 if(old_blocked)require(d.ext_req&&addr==old_addr&&wr==old_wr&&wd==old_wdata,"unstable external request under backpressure");
 old_blocked=d.ext_req&&!d.ext_ready;old_addr=addr;old_wr=wr;old_wdata=wd;
 d.clk=1;d.eval();d.clk=0;d.eval();tickno++;
 if(d.reset){pending=false;delay=0;old_blocked=false;}
 else {if(pending&&delay>0)delay--;if(retire)pending=false;if(accept){require(!wr,"program memory is read-only");require((addr&15)==0&&addr<code.size(),"external program read bounds");require(!pending,"one outstanding external read");response={};for(int j=0;j<16;j++)if(addr+j<code.size())response[j/4]|=uint32_t(code[addr+j])<<(8*(j%4));pending=true;delay=stall?1+int(tickno%5):1;}}
 return e;
}
static W cfg(bool wr,int addr,const W&data={}){
 d.cfg_valid=1;d.cfg_write=wr;d.cfg_addr=addr;set(d.cfg_data,data);d.cfg_take=1;
 int n=0;while(!step().cfg){require(++n<100,"cfg request timeout");}d.cfg_valid=0;
 for(n=0;n<100;n++){auto e=step();if(e.cfg_rsp)return e.cfgdata;}throw std::runtime_error("cfg response timeout");
}
static std::vector<uint8_t> unhex(const std::string&s){std::vector<uint8_t>x;for(size_t i=0;i<s.size();i+=2)x.push_back(uint8_t(std::stoul(s.substr(i,2),nullptr,16)));return x;}
static std::string hex(const std::vector<uint8_t>&x){const char*h="0123456789abcdef";std::string r;for(auto b:x){r+=h[b>>4];r+=h[b&15];}return r;}
static void load(const std::vector<uint8_t>&x){require(x.size()==512,"bounded frame input");for(int a=0;a<32;a++){W w{};for(int j=0;j<16;j++)w[j/4]|=uint32_t(x[16*a+j])<<(8*(j%4));cfg(true,a,w);}}
static std::vector<uint8_t> dump(){std::vector<uint8_t>x(512);for(int a=0;a<32;a++){auto w=cfg(false,a);for(int j=0;j<16;j++)x[16*a+j]=w[j/4]>>(8*(j%4));}return x;}
static void command(uint32_t pc,int lane,int tag){d.cmd_pc=pc;d.cmd_limit=code.size()/8;d.cmd_lane=lane;d.cmd_tag=tag;d.cmd_valid=1;d.eval();require(d.cmd_ready,"command accepted only idle");step();d.cmd_valid=0;}
int main(int argc,char**argv){
 try{
 Verilated::commandArgs(argc,argv);require(argc>=5,"program vectors output stall [limit]");stall=std::stoi(argv[4]);
 std::ifstream binary(argv[1],std::ios::binary);code.assign(std::istreambuf_iterator<char>(binary),{});require(!code.empty()&&code.size()%8==0,"program image");
 std::ifstream vectors(argv[2]);std::ofstream out(argv[3]);require(bool(vectors)&&bool(out),"files");
 d.cmd_valid=0;d.done_ready=0;d.cfg_valid=0;d.cfg_take=0;d.reset=1;step();step();d.reset=0;step();
 std::string name,in;uint32_t pc;int lane,status;unsigned count=0;int limit=argc>5?std::stoi(argv[5]):100000;
 while(vectors>>name>>pc>>lane>>status>>in){if(int(count)>=limit)break;auto input=unhex(in);load(input);
 uint64_t begin=tickno;uint32_t b0=d.wire_beats,t0=d.transactions;command(pc,lane,100+count);unsigned n=0;
 while(!d.done){step();require(++n<64000100,"execution timeout");require(!d.cfg_ready,"busy cfg forbidden");}
 uint64_t elapsed=tickno-begin;auto status0=d.status;auto tag0=d.tag;require(status0==status,"expected command status");require(tag0==100+count,"completion tag");
 uint64_t cycles=d.cycles;uint32_t actions=d.actions,fetches=d.fetches,reads=d.frame_reads,writes=d.frame_writes,rom=d.rom_reads,beats=d.wire_beats-b0,transactions=d.transactions-t0;
 d.cfg_valid=1;for(int h=0;h<3;h++){step();require(d.done&&d.status==status0&&d.tag==tag0&&!d.cfg_ready,"completion/status stable under backpressure");}d.cfg_valid=0;
 d.done_ready=1;step();d.done_ready=0;auto actual=dump();
 require(beats==5*transactions,"all serialized requests and responses charged five128bit beats");
 out<<"{\"name\":\""<<name<<"\",\"status\":"<<unsigned(status0)<<",\"tag\":"<<tag0<<",\"cycles\":"<<cycles<<",\"observed_active_edges\":"<<elapsed<<",\"actions\":"<<actions<<",\"fetch_lines\":"<<fetches<<",\"frame_read_lines\":"<<reads<<",\"frame_write_lines\":"<<writes<<",\"rom_requests\":"<<rom<<",\"link_transactions\":"<<transactions<<",\"wire_beats\":"<<beats<<",\"caller_setup_write_lines\":32,\"caller_result_read_lines\":32,\"frame\":\""<<hex(actual)<<"\"}\n";
 count++;
 }
 // Interrupt a real executing program: no stale completion; untouched SRAM marker retained.
 if(count){std::vector<uint8_t> x(512);for(int i=480;i<496;i++)x[i]=0xa5;load(x);command(pc,0,65000);for(int i=0;i<20&&!d.done;i++)step();d.reset=1;step();d.reset=0;for(int i=0;i<20;i++){step();require(!d.done,"no completion after reset abort");}auto line=cfg(false,30);for(int i=0;i<4;i++)require(line[i]==0xa5a5a5a5,"reset preserves SRAM data");}
 std::cout<<"PASS_WIDE_RTL cases="<<count<<" wall_edges="<<tickno<<" backpressure="<<stall<<" reset_preservation=PASS\n";
 return 0;
 }catch(const std::exception&e){std::cerr<<"FAIL: "<<e.what()<<" edge="<<tickno<<" state="<<unsigned(d.debug_state)<<" status="<<unsigned(d.status)<<"\n";return 1;}
}
