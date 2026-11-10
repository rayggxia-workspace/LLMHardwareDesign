"""Extend the pinned finite-fabric oracle with runtime native P admission."""
from pathlib import Path
import subprocess
base='0b60b134e'
dest=Path('project/experiments/mother_control_native/typed_dma/typed.cpp')
s=subprocess.check_output(['git','show',f'{base}:project/experiments/w8a16_dma/dma.cpp']).decode()
s=s.replace('Vmc_dma_fabric','Vmc_dma_fabric_typed_p')
s=s.replace('bool boot_purged=false,forced_bad_fence=false;', '''bool boot_purged=false,forced_bad_fence=false;
uint8_t mode_pending=0,mode_choice=0,client_drained=7;
int mode_accepts=0,native_legal=0,native_bad=0;''')
s=s.replace(' t.clk=0;t.c_req_valid=0;', ''' t.clk=0;t.p_mode_valid=mode_pending;t.p_mode_native64=mode_choice;t.p_mode_client_drained=client_drained;
 t.c_req_valid=0;''')
s=s.replace('  std::array<int,2>now{};', '''  uint8_t mfire=t.p_mode_valid&t.p_mode_ready;
  if(mfire){need(boot_purged,"mode admitted before actual startup purge");
   for(int c=0;c<3;++c)if(mfire&(1<<c)){++mode_accepts;trace<<"MODE,"<<cycle<<","<<c<<","<<((mode_choice>>c)&1)<<"\\n";}
   mode_pending&=~mfire;
  }
  std::array<int,2>now{};''')
s=s.replace('queues[size_t(c)].pop_front();if(!p.bad)', '''queues[size_t(c)].pop_front();
    if(c<3){need(bool((t.p_req_rejected>>c)&1U)==p.bad,"typed source false allocation or missing rejection");
      if((t.p_mode_active>>c)&1U){if(p.bad)++native_bad;else ++native_legal;}}
    if(!p.bad)''')
a=s.index('int main(')
s=s[:a]+'''void set_modes(uint8_t mask,uint8_t bits){
 mode_pending=mask;mode_choice=bits;
 wait([]{return mode_pending==0;},"actual mode acceptance");
 need((t.p_mode_active&mask)==(bits&mask),"mode selection didn't bind");
}
Packet one(int client,int serial,int channel){
 auto p=packet(client,serial,0,1,channel);
 p.address+=64;return p; // legally not 128B-aligned
}
void submit_bad(Packet p){
 int old=faults,oa=accepted,oi=issued;p.bad=true;
 queues[size_t(p.client)].push_back(p);
 wait([&]{return source_empty()&&faults==old+1;},"bounded typed rejection");
 for(int i=0;i<4;++i)tick();
 need(accepted==oa&&issued==oi,"bad typed request reserved/issued data");
}
'''+s[a:]
s=s.replace('t.reset=0;\n // All twelve', '''t.reset=0;
 need(t.p_mode_active==0,"startup default must remain legacy");
 // All twelve''')
a=s.index(' need(expected.empty()&&accepted==returned+cancelled')
s=s[:a]+''' // Old scope mode still rejects native64 and protects one local descriptor
 // identity across both DDR channels while its other half is outstanding.
 submit_bad(one(0,10000,1));
 add_record(0,10100,2,0,0,1);
 int pre=returned;wait([&]{return returned==pre+1&&source_empty();},"legacy prefix returned");
 auto cross=packet(0,10100,0,2,1);submit_bad(cross);
 mode_pending=1;mode_choice=1;
 for(int i=0;i<8;++i){tick();need(mode_pending==1&&t.p_mode_active==0,"mode switched with open legacy descriptor");}
 add_record(0,10100,2,0,1,2);
 wait([]{return mode_pending==0;},"prefix descriptor drain then typed mode");
 need(t.p_mode_active==1,"native mode after true legacy drain");
 // A held return occupies a real skid, and a local DONE must drain even
 // after transport credits disappear. Neither state permits a mode change.
 block_clients=true;queues[0].push_back(one(0,11000,0));
 wait([]{return (t.c_rsp_valid&1)!=0;},"held native result");
 mode_pending=1;mode_choice=0;client_drained=6;
 for(int i=0;i<8;++i){tick();need(mode_pending==1&&t.p_mode_active==1,"undrained native return changed mode");}
 block_clients=false;quiet();
 for(int i=0;i<8;++i){tick();need(mode_pending==1&&t.p_mode_active==1,"local DONE owner did not block mode transition");}
 client_drained=7;wait([]{return mode_pending==0;},"transport+client drained");need(t.p_mode_active==0,"back to scope");
 set_modes(7,7);
 submit_bad(one(0,11000,1)); // replay even after mode switch/other channel
 auto odd=one(1,11001,0);odd.tag|=1;submit_bad(odd);
 auto mis=one(1,11001,0);mis.address+=16;submit_bad(mis);
 auto wrong=one(2,11001,0);wrong.channel=1;submit_bad(wrong);
 submit_bad(packet(2,11001,0,2,0));
 // A rejected tag never advances its monotonic cursor. Three new request
 // owners contend with ordinary W and unmodified scope sources.
 ideal=false;
 for(int row=0;row<144;++row){
  for(int c=0;c<3;++c)queues[size_t(c)].push_back(one(c,11100+row,(row+c)&1));
  if(row%8==0){
   add_record(3,13000+row,2,1);
   add_record(9,14000+row,17,0);
   add_record(11,15000+row,18,1);
  }
 }
 quiet();need(native_legal==433&&native_bad==5,"native64 valid/reject coverage");
 // Only this client's accepted FENCE DONE resets its local replay cursor;
 // global serial auto-purge is independent of a local namespace reset.
 fence_client=0;fence_cookie=0x25000bc1;fence_epoch=21;fence_request=true;
 oldf=fences;wait([&]{return !fence_request&&fences>oldf&&!backend_fence&&!t.c_fence_done_valid;},
                 "real typed-client FENCE");
 queues[0].push_back(one(0,7,0));quiet();
 submit_bad(one(1,7,0));
 need(native_legal==434&&native_bad==6,"typed client FENCE namespace");
 set_modes(7,0);
 add_record(0,10100,2,0);add_record(2,15100,2,1);quiet();
 need(mode_accepts==8&&t.p_mode_active==0,"runtime mode transition count");
'''+s[a:]
s=s.replace('<<" rolling3_bound=4 cycles="<<cycle', '<<" rolling3_bound=4 native64="<<native_legal<<" native64_rejects="<<native_bad<<" mode_accepts="<<mode_accepts<<" cycles="<<cycle')
dest.write_text(s,encoding='utf-8')

