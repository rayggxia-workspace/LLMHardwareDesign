#include "Vchain97.h"
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
using W=std::array<uint32_t,4>;static Vchain97 d;static uint64_t ticks=0;static int stall=0;static unsigned serial=0,mserial=0,eserial=0;static int swait=0,mwait=0;static bool sseen=false,mseen=false,hold_external=false;static unsigned high_water=0,accepted=0,aborted=0;
struct Reply{uint32_t epoch;int delay;W data;};static std::deque<Reply> fifo;
struct Case{std::string name,gu,records,gamma_bytes,lut;uint32_t coefficient;};static std::vector<uint8_t> gu,records,gamma_bytes,lut;static std::vector<int32_t> mids,acodes,accs,downs,joins;static std::ofstream out;
static void need(bool b,const char*s){if(!b)throw std::runtime_error(s);}
static W memory(uint32_t a){const std::vector<uint8_t>*p=nullptr;uint32_t off=0;
 if(a>=0x04000000&&uint64_t(a)<0x04000000ull+gu.size()){p=&gu;off=a-0x04000000;}
 else if(a>=0x04100000&&uint64_t(a)<0x04100000ull+records.size()){p=&records;off=a-0x04100000;}
 else if(a>=0x04800000&&uint64_t(a)<0x04800000ull+gamma_bytes.size()){p=&gamma_bytes;off=a-0x04800000;}
 else if(a>=0x02000000&&uint64_t(a)<0x02000000ull+lut.size()){p=&lut;off=a-0x02000000;}
 need(p&&a%16==0&&off+16<=p->size(),"legal external byte read");W w{};for(int j=0;j<16;j++)w[j/4]|=uint32_t((*p)[off+j])<<(8*(j%4));return w;
}
struct E{bool command,cfg_req,cfg_rsp;W data;};
static E step(){d.clk=0;d.ext_ready=fifo.size()<2;d.ext_valid=!fifo.empty()&&!hold_external&&fifo.front().delay==0;d.ext_response_epoch=fifo.empty()?0:fifo.front().epoch;for(int j=0;j<4;j++)d.ext_data[j]=fifo.empty()?0:fifo.front().data[j];d.eval();
 if(d.mem_request&&!sseen){sseen=true;swait=stall?serial++%3:0;}if(d.mul_request&&!mseen){mseen=true;mwait=stall?mserial++%3:0;}d.mem_hold=swait>0;d.mul_hold=mwait>0;d.eval();
 if(d.a_valid&&d.busy)need(acodes.size()==4096,"no premature A publication");
 bool ext_accept=d.ext_req&&d.ext_ready,ext_retire=d.ext_valid&&d.ext_take;auto address=d.ext_addr,ep=d.ext_epoch;
 if(d.obs_mid_valid){need(d.obs_index==mids.size(),"ordered actual MID");mids.push_back(d.obs_mid);}if(d.obs_a_valid){need(d.obs_index==acodes.size(),"ordered actual A8");acodes.push_back(int8_t(d.obs_a));}
 if(d.obs_valid){need(unsigned(d.obs_row)*8+d.obs_rank==accs.size(),"ordered actual fullK M");accs.push_back(d.obs_acc);downs.push_back(d.obs_down);}
 if(d.swrite_event){if(d.debug_state==5&&d.swrite_addr<384)for(int j=0;j<4;j++)joins.push_back(d.swrite_data[j]);need((d.debug_state==2&&(d.swrite_addr<128||d.swrite_addr>=768))||(d.debug_state==5&&d.swrite_addr<384)||(d.debug_state==8&&d.swrite_addr<448),"actual phase SRAM write lease");}
 E e{bool(d.cmd_accept),bool(d.cfg&&d.cfg_ready),bool(d.cfg_valid&&d.cfg_take),{d.cfg_dout[0],d.cfg_dout[1],d.cfg_dout[2],d.cfg_dout[3]}};
 d.clk=1;d.eval();d.clk=0;d.eval();ticks++;
 if(d.reset){fifo.clear();eserial=0;}else{for(auto&f:fifo)if(f.delay>0)f.delay--;if(ext_retire)fifo.pop_front();if(ext_accept){fifo.push_back({ep,stall?1+int(eserial++%5):1,memory(address)});if(fifo.size()>high_water)high_water=fifo.size();}}
 if(d.soft_abort){sseen=mseen=false;swait=mwait=0;serial=mserial=0;}if(swait>0)swait--;if(mwait>0)mwait--;if(!d.mem_request)sseen=false;if(!d.mul_request)mseen=false;return e;
}
static W config(bool wr,int addr,W w={}){d.cfg=1;d.cfg_wr=wr;d.cfg_addr=addr;d.cfg_take=1;for(int i=0;i<4;i++)d.cfg_din[i]=w[i];int n=0;while(!step().cfg_req)need(++n<100,"cfg ready");d.cfg=0;for(n=0;n<100;n++){auto e=step();if(e.cfg_rsp)return e.data;}throw std::runtime_error("cfg response");}
static void readfile(std::string p,std::vector<uint8_t>&v){std::ifstream f(p,std::ios::binary);need(bool(f),"source file");v.assign(std::istreambuf_iterator<char>(f),{});}
static uint32_t b0,t0,g0,g1;static uint64_t before;
static void prepare(const Case&c,bool only=false){readfile(c.gu,gu);readfile(c.records,records);readfile(c.gamma_bytes,gamma_bytes);readfile(c.lut,lut);need(gu.size()==32768&&records.size()==6488064&&gamma_bytes.size()==6144&&lut.size()==131072,"exact physical input sizes");
 config(true,512,{0xa5a5a5a5,0x12345678,0xdeadbeef,0x87654321});config(true,767,{0xa5a5a5a5,0,0,0});mids.clear();acodes.clear();accs.clear();downs.clear();joins.clear();serial=mserial=eserial=0;sseen=mseen=false;swait=mwait=0;
 d.gateup_address=0x04000000;d.records_address=0x04100000;d.gamma_address=0x04800000;d.owner=0x1234;d.input_version=100+accepted;d.epsilon=17;d.coefficient=c.coefficient;d.prep_only=only;b0=d.wire_beats;t0=d.transactions;g0=d.mul_grants0;g1=d.mul_grants1;before=ticks;
}
static void start(){auto epoch=d.epoch;d.cmd=1;int n=0;while(!step().command)need(++n<20,"command handshake");need(d.epoch==epoch+1,"epoch per command");accepted++;d.cmd=0;d.gateup_address=d.records_address=d.gamma_address=0xffffffff;d.owner=0;d.input_version=0;d.epsilon=0;d.coefficient=0;d.prep_only^=1;}
static void wait_done(){auto begin=ticks;while(!d.done){step();need(ticks-begin<30000000,"complete chain watchdog");need(!d.cfg_ready&&!d.cmd_ready,"busy protects resources");}}
static void ack(){unsigned status=d.status,epoch=d.epoch;for(int j=0;j<4;j++){need(d.done&&d.status==status&&d.epoch==epoch&&!d.cmd_ready,"done held until ack");step();}d.ack=1;step();d.ack=0;need(!d.busy,"ack idle");}
static std::string hex128(const VlWide<4>&v){std::ostringstream s;s<<std::hex<<std::setfill('0');for(int j=3;j>=0;j--)s<<std::setw(8)<<v[j];return s.str();}
static void array(std::ostream&o,const std::vector<int32_t>&v){o<<'[';for(size_t i=0;i<v.size();i++){if(i)o<<',';o<<v[i];}o<<']';}
static void finish(const Case&c,const std::string&role,bool only=false){wait_done();need(d.status==0,"complete chain status");need(mids.size()==4096&&acodes.size()==4096&&d.a_valid&&d.expert_valid==255,"all8 original V results published");need(only||(accs.size()==12288&&downs.size()==12288&&joins.size()==1536),"complete real M consumer");need(d.a_owner==0x1234&&d.a_version==99+accepted&&d.a_epoch==d.epoch,"owner/version/epoch latched");
 auto cy=d.cycles,vc=d.v_cycles,nc=d.norm_cycles;auto gr=d.gate_reads,ur=d.up_reads,ll=d.lut_reads,vsr=d.v_sreads,vsw=d.v_swrites;auto nr=d.reads,nw=d.writes,gl=d.gamma_loads,gs=d.gamma_stores,de=d.den_events;auto packets=d.packets,macs=d.macs,mwrites=d.mwrites,cr=d.cache_reads,cw=d.cache_writes,beats=d.wire_beats-b0,tx=d.transactions-t0,mg0=d.mul_grants0-g0,mg1=d.mul_grants1-g1,ep=d.epoch;std::string sum=hex128(d.observed_sum),den=hex128(d.observed_den);std::vector<int32_t> ds;for(int j=0;j<8;j++)ds.push_back(int16_t(d.deltas[j/2]>>(16*(j%2))));ack();std::vector<int32_t> codes,output;
 for(int i=0;i<256;i++){auto w=config(false,768+i);for(int j=0;j<16;j++)codes.push_back(int8_t(w[j/4]>>(8*(j%4))));}need(codes==acodes,"M/norm retains actual generated A");
 if(!only)for(int i=0;i<384;i++){auto w=config(false,i);for(int j=0;j<4;j++)output.push_back(int32_t(w[j]));}
 need(config(false,512)[0]==0xa5a5a5a5&&config(false,767)[0]==0xa5a5a5a5,"unleased SRAM canaries retained");
 out<<"{\"name\":\""<<c.name<<"\",\"role\":\""<<role<<"\",\"prep_only\":"<<(only?"true":"false")<<",\"epoch\":"<<ep<<",\"status\":0,\"cycles\":"<<cy<<",\"v_cycles\":"<<vc<<",\"norm_cycles\":"<<nc<<",\"gate_reads\":"<<gr<<",\"up_reads\":"<<ur<<",\"lut_reads\":"<<ll<<",\"v_sreads\":"<<vsr<<",\"v_swrites\":"<<vsw<<",\"norm_reads\":"<<nr<<",\"norm_writes\":"<<nw<<",\"gamma_loads\":"<<gl<<",\"gamma_stores\":"<<gs<<",\"den_events\":"<<de<<",\"M_packets\":"<<packets<<",\"M_MACs\":"<<macs<<",\"M_writes\":"<<mwrites<<",\"cache_reads\":"<<cr<<",\"cache_writes\":"<<cw<<",\"wire_beats\":"<<beats<<",\"transactions\":"<<tx<<",\"mul_grants0\":"<<mg0<<",\"mul_grants1\":"<<mg1<<",\"sum_hex\":\""<<sum<<"\",\"den_hex\":\""<<den<<"\",\"mid\":";array(out,mids);out<<",\"A8\":";array(out,codes);out<<",\"delta\":";array(out,ds);out<<",\"acc\":";array(out,accs);out<<",\"down\":";array(out,downs);out<<",\"joined\":";array(out,joins);out<<",\"out\":";array(out,output);out<<"}\n";
}
int main(int argc,char**argv){try{Verilated::commandArgs(argc,argv);need(argc==5,"vectors output stall pilot");stall=std::stoi(argv[3]);int pilot=std::stoi(argv[4]);d.reset=1;step();d.reset=0;step();std::ifstream f(argv[1]);out.open(argv[2]);need(bool(f)&&bool(out),"files");std::vector<Case>cases;Case c;while(f>>c.name>>c.gu>>c.records>>c.gamma_bytes>>c.lut>>c.coefficient)cases.push_back(c);need(cases.size()==6,"six bound inputs");
 if(pilot){auto c=cases[pilot==2?5:0];prepare(c,true);start();finish(c,"prep-pilot",true);prepare(c);start();finish(c,"chain-pilot");}else for(auto&x:cases){prepare(x);start();finish(x,"mixed");}
 std::ofstream p(std::string(argv[2])+".protocol.json");p<<"{\"schema\":\"v97-protocol-pilot-v1\",\"accepted\":"<<accepted<<",\"same_core_no_per_case_reset\":true,\"held_done\":true,\"latched_parameters\":true,\"fabric_high_water\":"<<high_water<<"}\n";std::cout<<"PASS_ACTUAL_V_M_NORM_EXECUTION\n";return 0;
 }catch(const std::exception&e){std::cerr<<e.what()<<" phase="<<unsigned(d.debug_state)<<" V="<<unsigned(d.vdebug)<<" M="<<unsigned(d.mdebug)<<" N="<<unsigned(d.ndebug)<<" status="<<unsigned(d.status)<<" ticks="<<ticks<<"\n";return 1;}}
