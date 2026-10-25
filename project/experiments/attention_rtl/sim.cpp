#include "Vchain102.h"
#include "verilated.h"
#include <array>
#include <vector>
#include <deque>
#include <fstream>
#include <iostream>
#include <sstream>
#include <iomanip>
#include <stdexcept>
using W=std::array<uint32_t,4>;static Vchain102 d;static uint64_t ticks=0;static int stall=0;static unsigned serial=0,mserial=0,eserial=0;static int swait=0,mwait=0;static bool sseen=false,mseen=false,hold_external=false;static unsigned high_water=0,accepted=0,accepted_reads=0;
struct Reply{uint32_t epoch;int delay;W data;};static std::deque<Reply> fifo;
struct Case{std::string name,q,k,v,lut;unsigned length;int ke,ve;uint64_t qe;unsigned version;};static Case current;
static std::vector<uint8_t> qbytes,kbytes,vbytes,lut;static std::vector<int32_t> qk,score,exp1,exp_again,prob;static std::vector<uint64_t> sums;static std::ofstream out;
static void need(bool b,const char*s){if(!b)throw std::runtime_error(s);}
static W memory(uint32_t a){const std::vector<uint8_t>*p=nullptr;uint32_t off=0;
 if(a>=0x04000000&&uint64_t(a)<0x04000000ull+current.length*256){p=&kbytes;off=a-0x04000000;}
 else if(a>=0x04100000&&uint64_t(a)<0x04100000ull+current.length*256){p=&vbytes;off=a-0x04100000;}
 else if(a>=0x02012010&&a<0x02014020){p=&lut;off=a-0x02000000;}
 need(p&&a%16==0&&off+16<=p->size(),"bounded immutable external read");W w{};for(int j=0;j<16;j++)w[j/4]|=uint32_t((*p)[off+j])<<(8*(j%4));return w;
}
struct E{bool command,cfg_req,cfg_rsp;W data;};
static E step(){d.clk=0;d.ext_ready=fifo.size()<2;d.ext_valid=!fifo.empty()&&!hold_external&&fifo.front().delay==0;d.ext_response_epoch=fifo.empty()?0:fifo.front().epoch;for(int j=0;j<4;j++)d.ext_data[j]=fifo.empty()?0:fifo.front().data[j];d.eval();
 if(d.mem_request&&!sseen){sseen=true;swait=stall?serial++%3:0;}if(d.mul_request&&!mseen){mseen=true;mwait=stall?mserial++%3:0;}d.mem_hold=swait>0;d.mul_hold=mwait>0;d.eval();
 bool ext_accept=d.ext_req&&d.ext_ready,ext_retire=d.ext_valid&&d.ext_take;auto address=d.ext_addr,ep=d.ext_epoch;
 if(d.reset||d.soft_abort)need(!d.ext_req&&!d.ext_take&&!d.cmd_accept&&!d.cfg_ready&&!d.cfg_valid&&!d.done,"reset masks all public handshakes");
 if(d.obs_valid){unsigned index=unsigned(d.obs_head)*current.length+d.obs_key;
  if(d.obs_kind==0){need(index==qk.size(),"QK sequence");qk.push_back(d.obs_x);score.push_back(d.obs_y);}
  else if(d.obs_kind==1){need(index==exp1.size(),"SUM sequence");exp1.push_back(d.obs_x);if(d.obs_key+1==current.length)sums.push_back(d.obs_sum);}
  else if(d.obs_kind==2){need(index==prob.size(),"P sequence");prob.push_back(d.obs_x);exp_again.push_back(d.obs_y);}
  else need(false,"unexpected observer kind");
 }
 if(d.swrite_event)need(d.swrite_addr>=80&&d.swrite_addr<988,"runtime bounded SRAM write lease");
 E e{bool(d.cmd_accept),bool(d.cfg&&d.cfg_ready),bool(d.cfg_valid&&d.cfg_take),{d.cfg_dout[0],d.cfg_dout[1],d.cfg_dout[2],d.cfg_dout[3]}};
 d.clk=1;d.eval();d.clk=0;d.eval();ticks++;
 if(d.reset){fifo.clear();eserial=0;}else{for(auto&f:fifo)if(f.delay>0)f.delay--;if(ext_retire)fifo.pop_front();if(ext_accept){accepted_reads++;fifo.push_back({ep,stall?1+int(eserial++%5):1,memory(address)});if(fifo.size()>high_water)high_water=fifo.size();}}
 if(d.soft_abort){sseen=mseen=false;swait=mwait=0;}if(swait>0)swait--;if(mwait>0)mwait--;if(!d.mem_request)sseen=false;if(!d.mul_request)mseen=false;return e;
}
static W config(bool wr,int addr,W w={}){d.cfg=1;d.cfg_wr=wr;d.cfg_addr=addr;d.cfg_take=1;for(int i=0;i<4;i++)d.cfg_din[i]=w[i];int n=0;while(!step().cfg_req)need(++n<100,"cfg ready");d.cfg=0;for(n=0;n<100;n++){auto e=step();if(e.cfg_rsp)return e.data;}throw std::runtime_error("cfg response");}
static void readfile(std::string p,std::vector<uint8_t>&v){std::ifstream f(p,std::ios::binary);need(bool(f),"source file");v.assign(std::istreambuf_iterator<char>(f),{});}
static uint32_t b0,t0,g0;static uint64_t before;
static void prepare(const Case&c){current=c;readfile(c.q,qbytes);readfile(c.k,kbytes);readfile(c.v,vbytes);readfile(c.lut,lut);need(qbytes.size()==1024&&kbytes.size()>=c.length*256&&vbytes.size()==kbytes.size()&&lut.size()==131072,"physical input sizes");
 for(int i=0;i<64;i++){W w{};for(int j=0;j<16;j++)w[j/4]|=uint32_t(qbytes[16*i+j])<<(8*(j%4));config(true,i,w);}
 for(int i=1020;i<1024;i++)config(true,i,{0xa5a5a5a5,0x12345678,0xdeadbeef,0x87654321});
 qk.clear();score.clear();exp1.clear();exp_again.clear();prob.clear();sums.clear();serial=mserial=eserial=0;sseen=mseen=false;swait=mwait=0;
 d.key_address=0x04000000;d.value_address=0x04100000;d.owner=0x1234;d.input_version=c.version;d.score_multiplier=94906266;d.length=c.length;d.position=c.length-1;d.window=0;d.key_unit=c.ke;d.value_unit=c.ve;d.query_units=c.qe;b0=d.wire_beats;t0=d.transactions;g0=d.mul_grants;before=ticks;
}
static void start(){auto epoch=d.epoch;d.cmd=1;int n=0;while(!step().command)need(++n<20,"command handshake");need(d.epoch==epoch+1,"epoch per command");accepted++;d.cmd=0;
 d.key_address=d.value_address=0xffffffff;d.owner=0;d.input_version=0;d.score_multiplier=0;d.length=0;d.position=0;d.window=65535;d.key_unit=127;d.value_unit=-128;d.query_units=0;
}
static void wait_done(){auto begin=ticks;while(!d.done){step();need(ticks-begin<30000000,"complete chain watchdog");need(!d.cfg_ready&&!d.cmd_ready,"busy protects resources");}}
static void ack(){unsigned status=d.status,epoch=d.epoch;for(int j=0;j<4;j++){need(d.done&&d.status==status&&d.epoch==epoch&&!d.cmd_ready,"done held until ack");step();}d.ack=1;step();d.ack=0;need(!d.busy,"ack idle");}
template<class T>static void array(std::ostream&o,const std::vector<T>&v){o<<'[';for(size_t i=0;i<v.size();i++){if(i)o<<',';o<<v[i];}o<<']';}
static void finish(const Case&c,const std::string&role){wait_done();need(d.status==0,"complete chain status");need(qk.size()==8*c.length&&score.size()==qk.size()&&exp1.size()==qk.size()&&exp_again.size()==qk.size()&&prob.size()==qk.size()&&sums.size()==8,"all8 complete integer attention");need(exp1==exp_again,"readonly LUT consistent across passes");need(d.cache_owner==0x1234&&d.cache_version==c.version&&d.cache_length==c.length&&int8_t(d.cache_key_unit)==c.ke&&int8_t(d.cache_value_unit)==c.ve,"actual locked cache metadata");
 auto cy=d.cycles;auto macs=d.macs,sr=d.sreads,sw=d.swrites,kl=d.kloads,vl=d.vloads,ll=d.lut_reads,di=d.divides,sp=d.score_products,beats=d.wire_beats-b0,tx=d.transactions-t0,mg=d.mul_grants-g0,ep=d.epoch;ack();std::vector<int32_t> output;
 for(int i=0;i<256;i++){auto w=config(false,732+i);for(int j=0;j<4;j++)output.push_back(int32_t(w[j]));}
 for(int i=1020;i<1024;i++)need(config(false,i)==W{0xa5a5a5a5,0x12345678,0xdeadbeef,0x87654321},"64B canary retained");
 out<<"{\"name\":\""<<c.name<<"\",\"role\":\""<<role<<"\",\"epoch\":"<<ep<<",\"status\":0,\"length\":"<<c.length<<",\"cycles\":"<<cy<<",\"macs\":"<<macs<<",\"sreads\":"<<sr<<",\"swrites\":"<<sw<<",\"kloads\":"<<kl<<",\"vloads\":"<<vl<<",\"lut_reads\":"<<ll<<",\"divides\":"<<di<<",\"score_products\":"<<sp<<",\"wire_beats\":"<<beats<<",\"transactions\":"<<tx<<",\"mul_grants\":"<<mg<<",\"qk\":";array(out,qk);out<<",\"score\":";array(out,score);out<<",\"exp\":";array(out,exp1);out<<",\"sum\":";array(out,sums);out<<",\"P\":";array(out,prob);out<<",\"out\":";array(out,output);out<<"}\n";
}
int main(int argc,char**argv){try{Verilated::commandArgs(argc,argv);need(argc==5,"vectors output stall pilot");stall=std::stoi(argv[3]);int pilot=std::stoi(argv[4]);d.reset=1;step();d.reset=0;step();std::ifstream f(argv[1]);out.open(argv[2]);need(bool(f)&&bool(out),"files");std::vector<Case>cases;Case c;while(f>>c.name>>c.q>>c.k>>c.v>>c.lut>>c.length>>c.ke>>c.ve>>c.qe>>c.version)cases.push_back(c);need(cases.size()==79,"76real3synthetic");
 if(pilot){std::vector<unsigned> pick=pilot==1?std::vector<unsigned>{0,7,8,39,76,78}:std::vector<unsigned>{72,75,77};for(auto i:pick){prepare(cases[i]);start();finish(cases[i],"pilot");}}
 else for(auto&x:cases){prepare(x);start();finish(x,"complete");}
 std::ofstream p(std::string(argv[2])+".protocol.json");p<<"{\"schema\":\"a102-protocol/1\",\"accepted\":"<<accepted<<",\"same_core_no_per_case_reset\":true,\"held_done\":true,\"latched_parameters\":true,\"canary_bytes\":64,\"fabric_high_water\":"<<high_water<<",\"external_accepted\":"<<accepted_reads<<"}\n";std::cout<<"PASS_ACTUAL_INTEGER_GQA_EXECUTION\n";return 0;
 }catch(const std::exception&e){std::cerr<<e.what()<<" state="<<unsigned(d.debug_state)<<" A="<<unsigned(d.adebug)<<" status="<<unsigned(d.status)<<" ticks="<<ticks<<" qk="<<qk.size()<<" P="<<prob.size()<<"\n";return 1;}}
