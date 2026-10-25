#include "Vr99.h"
#include "verilated.h"
#include <array>
#include <vector>
#include <fstream>
#include <string>
#include <stdexcept>
#include <iostream>
#include <cstring>
#include <filesystem>
using Line=std::array<uint32_t,4>;
static void need(bool v,const std::string&s){if(!v)throw std::runtime_error(s);}
struct Sim {
 Vr99 d;std::vector<uint8_t> mem;std::ofstream rows,raw,events;uint64_t t=0;bool stall=false,init=false,pending=false,applied=false;uint32_t pa=0,pg=0;bool pw=false;Line pdata{},result{};uint64_t due=0;bool peer_pending=false;int64_t peer_expected=0;uint64_t peer_checks=0,holds=0;bool inject_stale=false;unsigned stale_injected=0;unsigned record=0;int head=0;std::string out;
 Sim(const char* image,const char* dir,bool hold,int h):mem(1<<20),stall(hold),head(h),out(dir){std::ifstream f(image,std::ios::binary);f.read((char*)mem.data(),mem.size());need(f.gcount()==(long)mem.size(),"image size");rows.open(out+"/actual.jsonl");raw.open(out+"/actual.bin",std::ios::binary);events.open(out+"/protocol.jsonl");d.clk=0;d.reset=0;d.cmd=0;d.ack=0;d.abort_request=0;d.accept_candidate=0;d.reject_candidate=0;d.cfg=0;d.cfg_take=0;d.peer_req=0;d.peer_take=1;d.ext_valid=0;d.ext_ready=0;d.response_generation=0;}
 Line get(uint32_t a){need(a>=0x04000000&&a<0x04100000&&!(a&15),"external address");Line x;memcpy(x.data(),mem.data()+a-0x04000000,16);return x;}
 void set(uint32_t a,Line x){get(a);memcpy(mem.data()+a-0x04000000,x.data(),16);}
 void apply(){if(pw&&!applied){need(pa<0x040a0410,"write outside declared mutable region");auto desc=get(0x040a0400);bool valid=(desc[3]>>22)&1;int bank=(desc[3]>>16)&1;if(valid&&!init){uint32_t st=0x04000000+bank*0x20000,ys=0x040a0000+bank*512;need(!(pa>=st&&pa<st+0x20000)&&!(pa>=ys&&pa<ys+512),"published data overwritten");}set(pa,pdata);applied=true;}}
 void tick(){
 d.mem_hold=stall&&(t%11==3||t%11==4);d.mul_hold=stall&&t%13==5;
 d.ext_ready=!pending&&(!stall||t%7!=2);d.ext_valid=pending&&t>=due;bool badtag=inject_stale&&d.ext_valid&&stale_injected==0;d.response_generation=badtag?(pg^0x80000000u):pg;
 if(d.ext_valid){apply();auto x=pw?Line{}:get(pa);for(int j=0;j<4;j++)d.ext_rdata[j]=x[j];}
 d.peer_take=!stall||t%17<9;d.peer_req=!d.reset&&stall&&!peer_pending&&t%31==4;d.peer_a=(int32_t)(t%2003)-1001;d.peer_b=(int32_t)(t%307)-153;
 d.clk=0;d.eval();if(d.reset)need(!d.ext_req&&!d.cmd_ready&&!d.abort_ready&&!d.cfg_ready&&!d.offer&&!d.done&&!d.peer_ready&&!d.peer_valid,"reset phantom handshake");bool req=d.ext_req&&d.ext_ready,resp=d.ext_valid&&d.ext_take;bool pr=d.peer_req&&d.peer_ready,pv=d.peer_valid&&d.peer_take;
 if(pv){need(peer_pending&&(int64_t)d.peer_y==peer_expected,"shared multiply peer");peer_pending=false;peer_checks++;}
 if(pr){need(!peer_pending,"peer overwrite");peer_pending=true;peer_expected=(int64_t)(int32_t)d.peer_a*(int32_t)d.peer_b;}
 uint32_t ra=d.ext_addr,rg=d.ext_generation;bool rw=d.ext_wr;Line data{};for(int j=0;j<4;j++)data[j]=d.ext_wdata[j];
 d.clk=1;d.eval();t++;
 if(resp){need(pending,"response without credit");if(badtag)stale_injected++;else pending=false;}
 if(req){need(!pending,"external credit >1");get(ra);pending=true;pa=ra;pg=rg;pw=rw;pdata=data;applied=false;due=t+(stall?1+t%9:1);}
 }
 void reset(){need(!pending,"reset requires fabric barrier");d.cmd=0;d.ack=0;d.abort_request=0;d.accept_candidate=0;d.reject_candidate=0;d.reset=1;for(int i=0;i<3;i++)tick();d.reset=0;peer_pending=false;tick();}
 void scratch(){for(unsigned i=0;i<1024;i++){while(!d.cfg_ready)tick();d.cfg=1;d.cfg_wr=1;d.cfg_addr=i;for(int j=0;j<4;j++)d.cfg_din[j]=0x9e370000u+i*4+j;tick();d.cfg=0;while(!d.cfg_valid)tick();d.cfg_take=1;tick();d.cfg_take=0;}}
 void canary(){for(unsigned i=514;i<1024;i++){while(!d.cfg_ready)tick();d.cfg=1;d.cfg_wr=0;d.cfg_addr=i;tick();d.cfg=0;while(!d.cfg_valid)tick();for(int j=0;j<4;j++)need(d.cfg_dout[j]==0x9e370000u+i*4+j,"unused scratch changed");d.cfg_take=1;tick();d.cfg_take=0;}}
 void begin(int op,int un=0){while(!d.cmd_ready)tick();d.command=op;d.head=head;d.initial_unit=un;d.expected_position=d.position;d.cmd=1;tick();d.cmd=0;}
 void finish(const std::string&label,int op,int un,bool reject=false,int abort_phase=-1){
 uint32_t b0=d.beats,tx0=d.transactions,mg=d.mul_grants,pg0=d.peer_grants,ct=d.contested;uint64_t pc=peer_checks;begin(op,un);bool aborted=false,late=false;int held=0;uint32_t cu=0,ce=0;uint64_t lim=t+40000000;
 while(!d.done){need(t<lim,"command timeout phase "+std::to_string(d.debug_state));
 // Change all configuration pins while busy: accepted values must remain latched.
 d.initial_unit=(int16_t)(t%255-127);d.head=(head+1+t)%32;d.expected_position=0xf0000000u+(uint32_t)t;d.command=t%4;
 if(d.offer){if(!held){cu=d.candidate_unit;ce=d.candidate_epoch;}need(cu==d.candidate_unit&&ce==d.candidate_epoch,"offer changed while held");held++;if(held>7){d.reject_candidate=reject;d.accept_candidate=1;}}
 if(!aborted&&abort_phase>=0&&abort_phase<1000&&d.debug_state==abort_phase&&d.abort_ready){d.abort_request=1;aborted=true;}
 if(abort_phase==1000&&!late&&pending&&pw&&pa>=0x04040000&&pa<0x04060000&&d.debug_state==3){apply();due=t+17;d.abort_request=1;aborted=true;late=true;}
 if(abort_phase==1002&&!late&&pending&&pw&&pa>=0x04040000&&pa<0x04060000&&t>=due&&d.debug_state==3){d.abort_request=1;aborted=true;late=true;}
 if(abort_phase==1001&&pending&&pw&&pa==0x040a0400){if(!late){apply();due=t+13;late=true;}need(!d.abort_ready,"descriptor publication cannot accept abort");d.abort_request=1;}

 tick();d.abort_request=0;
 }
 d.accept_candidate=0;d.reject_candidate=0;need(!pending,"done with external credit");auto ds=get(0x040a0400);int bank=(ds[3]>>16)&1;
 raw.write((char*)ds.data(),16);raw.write((char*)mem.data()+bank*0x20000,0x20000);raw.write((char*)mem.data()+0xa0000+bank*512,512);
 rows<<"{\"schema\":\"r99-row-v1\",\"index\":"<<record++<<",\"label\":\""<<label<<"\",\"op\":"<<op<<",\"status\":"<<(unsigned)d.status<<",\"position\":"<<d.position<<",\"unit\":"<<(int16_t)d.unit<<",\"epoch\":"<<d.numeric_epoch<<",\"bank\":"<<(unsigned)d.bank<<",\"generation\":"<<d.generation<<",\"aborts\":"<<d.aborts<<",\"stale\":"<<d.stale<<",\"retries\":"<<(unsigned)d.retries<<",\"cycles\":"<<d.cycles<<",\"reads\":"<<d.ext_reads<<",\"writes\":"<<d.ext_writes<<",\"s_reads\":"<<d.s_reads<<",\"s_writes\":"<<d.s_writes<<",\"beats\":"<<d.beats-b0<<",\"transactions\":"<<d.transactions-tx0<<",\"mul\":"<<d.mul_grants-mg<<",\"peer_grants\":"<<d.peer_grants-pg0<<",\"peer_checked\":"<<peer_checks-pc<<",\"contested\":"<<d.contested-ct<<",\"alpha_bypass\":"<<d.alpha_bypass<<",\"offer_hold\":"<<held<<",\"abort_injected\":"<<(aborted?"true":"false")<<"}\n";rows.flush();raw.flush();d.ack=1;tick();d.ack=0;tick();
 if(abort_phase>=1000){need(late,"late write test not reached");events<<"{\"test\":\""<<label<<"\",\"write_applied_before_ack\":true,\"abort_was_accepted\":"<<(aborted?"true":"false")<<"}\n";events.flush();}
 }
 void config_conflict(){while(!d.cfg_ready)tick();d.cfg=1;d.cfg_wr=0;d.cfg_addr=600;d.cmd=1;d.command=1;d.expected_position=d.position;d.head=head;d.clk=0;d.eval();need(!d.cmd_ready&&!d.cmd_accept,"cfg command arbitration");tick();d.cfg=0;for(int i=0;i<9;i++){need(d.cfg_valid&&!d.cmd_ready&&!d.cmd_accept&&!d.busy,"pending config swallowed command");tick();}d.cmd=0;d.cfg_take=1;tick();d.cfg_take=0;tick();events<<"{\"test\":\"cfg_pending\",\"held_cycles\":9}\n";}
 void hardwrite(bool commit){begin(1);uint64_t limit=t+40000000;while(true){need(t<limit,"hardreset target timeout");if(d.offer)d.accept_candidate=1;tick();if(pending&&pw&&(commit?pa==0x040a0400:(pa>=0x04040000&&pa<0x04060000))){apply();break;}}d.accept_candidate=0;auto before=get(0x040a0400);
 events<<"{\"test\":\"hardreset-"<<(commit?"commit":"private")<<"\",\"applied_address\":"<<pa<<",\"cycles\":"<<d.cycles<<",\"reads\":"<<d.ext_reads<<",\"writes\":"<<d.ext_writes<<",\"generation\":"<<d.generation<<",\"descriptor_position_after_apply\":"<<before[1]<<",\"write_ack_not_delivered\":true,\"fabric_barrier_drained\":true}\n";events.flush();
 // Coordinated fabric barrier: accepted write has actually applied; stale ACK is discarded before reset release.
 pending=false;reset();finish(commit?"restore-hardcommit":"restore-hardprivate",2,0);
 }
 void terminal(){need(!pending,"terminal pending");d.generation=0xfffffffe;finish("terminal-restore",2,0);need(d.generation==0xffffffff&&!d.cmd_ready,"generation terminal wrap");d.cmd=1;d.command=2;for(int i=0;i<11;i++){need(!d.cmd_ready&&!d.cmd_accept,"terminal accepted command");tick();}d.cmd=0;need(!pending,"terminal fabric pending");pending=true;pw=false;pa=0x040a0400;pg=0xffffffff;due=t;applied=false;tick();need(!pending&&d.stale==1,"terminal matching stale response blocked");events<<"{\"test\":\"generation_terminal_RTL_register_injection\",\"injected\":4294967294,\"observed\":4294967295,\"rejected_cycles\":11,\"terminal_stale_drained\":1}\n";}

};
int main(int argc,char**argv){try{need(argc==7,"args image out stall head unit mode");bool stall=std::stoi(argv[3]);int head=std::stoi(argv[4]),unit=std::stoi(argv[5]);Sim s(argv[1],argv[2],stall,head);std::string mode=argv[6];
 if(mode=="boundary"){
  auto dir=std::filesystem::path(argv[1]).parent_path();std::ifstream cases(dir/"fixtures.tsv");std::string name;int runstep;
  while(cases>>name>>runstep){need(!s.pending,"fixture barrier");std::ifstream f(dir/(name+".bin"),std::ios::binary);f.read((char*)s.mem.data(),s.mem.size());need(f.gcount()==(long)s.mem.size(),"fixture bytes");s.reset();s.scratch();s.finish(name+"/restore",2,0);if(runstep){need(s.d.status==0,"valid fixture restore");if(name=="whole_head_range"){s.finish(name+"/abort-reencode",1,0,false,50);need(s.d.status==2,"full-head reencode abort");s.finish(name+"/restore-again",2,0);}s.finish(name+"/step",1,0);}s.canary();}
 }else{
 s.reset();s.scratch();s.init=true;s.finish("init",0,unit);s.init=false;
 if(mode=="real"){
 for(int t=0;t<72;t++){s.finish("token"+std::to_string(t),1,0);need(s.d.status==0,"real numeric rejection");if((t+1)%8==0)s.finish("restore"+std::to_string(t+1),2,0);}
 s.canary();
 }else{
 s.config_conflict();s.inject_stale=true;s.finish("restore-stale",2,0);s.inject_stale=false;need(s.stale_injected==1&&s.d.stale==1,"stale response not drained");s.events<<"{\"test\":\"stale_response\",\"injected\":1,\"observed\":1}\n";s.finish("reject",1,0,true);need(s.d.status==3&&s.d.position==0,"reject changed publication");
 for(int phase:{16,20,25,36,45,55,60,66,79,1000,1002}){s.finish("abort"+std::to_string(phase),1,0,false,phase);need(s.d.status==2&&s.d.position==0,"abort failed");s.finish("restore-abort"+std::to_string(phase),2,0);}
 s.hardwrite(false);need(s.d.position==0,"private reset publication");s.hardwrite(true);need(s.d.position==1,"commit reset publication");
 s.finish("commit-drain",1,0,false,1001);need(s.d.status==0&&s.d.position==2,"irreversible commit cancelled");s.canary();s.terminal();
 }}
 std::cout<<"PASS_DRIVER commands="<<s.record<<" peer_checked="<<s.peer_checks<<"\n";return 0;
 }catch(const std::exception&e){std::cerr<<e.what()<<"\n";return 1;}}
