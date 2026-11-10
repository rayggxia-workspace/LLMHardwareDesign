#include "Vcopy_scale_header_joint.h"
#include "verilated.h"
#include <array>
#include <cstdint>
#include <iostream>
#include <memory>
#include <random>
#include <stdexcept>
static void check(bool b,const char* why){if(!b)throw std::runtime_error(why);}
int main(int argc,char** argv){
 try{
  check(argc==3,"seed/initial");unsigned seed=unsigned(std::stoul(argv[1])),initial=unsigned(std::stoul(argv[2]));
  auto c=std::make_unique<VerilatedContext>();c->commandArgs(argc,argv);c->randReset(int(initial));c->randSeed(int(seed));
  auto m=std::make_unique<Vcopy_scale_header_joint>(c.get());auto& d=*m;std::mt19937 rng(seed);
  auto rise=[&]{d.clk=1;d.eval();c->timeInc(1);d.clk=0;d.eval();c->timeInc(1);};
  d.reset=1;d.halt=0;d.start_valid=0;d.lease_valid=0;d.frame_stall=0;d.ack_stall=0;
  d.metadata_ready=0;d.inject_ack_valid=0;d.release_valid=0;d.release_cancel=0;
  d.inject_ack_error=0;for(unsigned w=0;w<4;++w)d.header_xor[w]=0;
  d.data_drained=0;d.consumer_drained=0;d.done_ready=0;
  for(int i=0;i<3;++i)rise();d.reset=0;d.eval();
  unsigned frames=0,meta=0,normal=0,failed=0,held_halt=0,deferred=0,expected_meta=0;
  for(unsigned test=0;test<144;++test){
   unsigned mode=test%8,mask=1+rng()%7,gen=test+1,shift=test%18;
   bool expect_error=mode>=1&&mode<=4;
   unsigned destinations=0;for(unsigned p=0;p<3;++p)destinations+=(mask>>p)&1U;
   if(!expect_error)expected_meta+=destinations;
   std::array<uint32_t,4> key={uint32_t(rng()),uint32_t(rng()),uint32_t(rng()),uint32_t(rng())};
   for(unsigned w=0;w<4;++w)d.start_key[w]=d.lease_key[w]=key[w];
   for(unsigned w=0;w<4;++w)d.header_xor[w]=0;
   if(mode==3){
    if((test/8)%2==0)d.start_key[2]^=1;
    else {
     const std::array<unsigned,7> bits={112,96,80,79,64,32,0};
     unsigned bit=bits[(test/8)%7];d.header_xor[bit/32]=1U<<(bit%32);
    }
   }
   d.start_generation=gen;d.start_kk=uint16_t((test%86)*128);
   d.start_session=0x12340000U+test;d.start_ticket=0x87650000U+test;
   d.start_shift=mode==2?18:shift;d.start_mask=mask;
   d.start_written_mask=mode==1&&(test/8)%2==0?0xfffe:0xffff;
   d.start_producer_error=mode==1&&(test/8)%2!=0;
   d.halt=0;d.frame_stall=0;d.ack_stall=0;d.metadata_ready=0;d.inject_ack_valid=0;
   d.data_drained=0;d.consumer_drained=0;d.release_cancel=0;d.release_valid=0;
   check((d.lease_ready&mask)==mask && d.start_ready,"previous lease not drained");
   d.lease_valid=mask;d.start_valid=1;d.eval();rise();d.lease_valid=0;d.start_valid=0;
   unsigned takes=0,held=0,cycles=0,ack_before=d.rejected_ack;
   std::array<std::array<uint32_t,5>,3> old{};
   std::array<unsigned,3> sent_frames{};
   bool ended=false;
   for(;cycles<600;++cycles){
    d.frame_stall=unsigned(rng()%8);d.ack_stall=unsigned(rng()%8);
    if(mode==4&&cycles<3)d.frame_stall=mask;
    d.halt=mode==4&&cycles>=1;
    d.metadata_ready=mode==6?0:unsigned(rng()%8);
    d.inject_ack_valid=mode==5&&cycles==2?7:0;
    d.inject_ack_error=7;
    for(unsigned p=0;p<3;++p)d.inject_ack_tag[p]=0xdeadbeefU;
    d.eval();
    for(unsigned p=0;p<3;++p){
     unsigned bit=1U<<p;
     if(held&bit){
      check(d.frame_valid&bit,"halt withdrew held frame");
      check(d.frame_tag[p]==old[p][0],"held tag changed");
      for(unsigned w=0;w<4;++w)check(d.frame_data[p*4+w]==old[p][w+1],"held payload changed");
      if(d.halt)++held_halt;
     }
     if((d.frame_valid&~d.frame_ready)&bit){
      held|=bit;old[p][0]=d.frame_tag[p];
      for(unsigned w=0;w<4;++w)old[p][w+1]=d.frame_data[p*4+w];
     }else held&=~bit;
     if((d.frame_valid&d.frame_ready)&bit){++frames;++sent_frames[p];}
     if(d.metadata_valid&bit){
      check((d.data_enabled&bit)&&!expect_error,"uncommitted/invalid scale published");
      for(unsigned w=0;w<4;++w)check(d.metadata_key[p*4+w]==key[w],"scale key");
      check(((d.metadata_generation>>(p*16))&65535)==gen,"scale generation");
      check(((d.metadata_kk>>(p*16))&65535)==d.start_kk,"scale K");
      check(((d.metadata_shift>>(p*6))&63)==shift,"scale value");
      check(d.metadata_session[p]==d.start_session && d.metadata_ticket[p]==d.start_ticket,"scale session");
      if(d.metadata_ready&bit){check(!(takes&bit),"scale consumed twice");takes|=bit;++meta;}
     }
    }
    check(d.release_ready==0,"released without true drain");
    if(d.done_valid){ended=true;break;}
    rise();
   }
   check(ended && bool(d.done_error)==expect_error,"prelude completion/error");
   check(d.frame_valid==0,"completion before offered frames drained");
   for(unsigned p=0;p<3;++p){
    if(!(mask&(1U<<p)))check(sent_frames[p]==0,"unselected destination received a frame");
    else if(mode==1||mode==2)check(sent_frames[p]==0,"invalid producer issued metadata");
    else if(mode==4||(mode==3&&(test/8)%2==0))check(sent_frames[p]==1,"partial prelude drain");
    else if(mode==3)check(sent_frames[p]>=1&&sent_frames[p]<=2,"fault duplicated/lost proffered frame");
    else check(sent_frames[p]==2,"successful prelude did not send exactly two frames");
   }
   if(mode==5)check(d.rejected_ack-ack_before==3,"unowned ACK accounting/ownership");
   // Prelude completion certifies receiver capture, not A-load consumption.
   // Commit the last observed ready/valid edge before testing deferred use.
   rise();
   if(!expect_error){
    check((d.data_enabled&mask)==mask,"header ACK before capture");
    if(mode==6){
     check(takes==0&&(d.metadata_valid&mask)==mask,"deferred receiver lost scale");
     d.metadata_ready=mask;d.eval();
     for(unsigned p=0;p<3;++p)if(d.metadata_valid&(1U<<p))++meta;
     rise();takes=mask;++deferred;
    }
    if(takes!=mask){
     d.metadata_ready=mask;d.eval();
     for(unsigned p=0;p<3;++p)if(d.metadata_valid&(1U<<p)){
      check(!(takes&(1U<<p)),"duplicate delayed metadata");takes|=1U<<p;++meta;
     }
     rise();
    }
    check(takes==mask,"missing metadata consumer");++normal;
   }else ++failed;
   d.done_ready=1;d.eval();rise();d.done_ready=0;d.halt=0;d.inject_ack_valid=0;
   d.release_cancel=expect_error;d.release_valid=mask;
   d.data_drained=1;d.consumer_drained=0;d.eval();
   check(d.release_ready==0,"released before consumer drain");rise();
   d.consumer_drained=1;d.eval();
   check((d.release_ready&mask)==mask,"drained lease did not release");
   rise();d.release_valid=0;d.eval();
   check(d.rx_quiescent==7&&d.quiescent,"lease state leaked");
  }
  check(normal==72&&failed==72&&held_halt>0&&deferred==18,"coverage");
  check(meta==expected_meta,"metadata consumption conservation");
  std::cout<<"PASS copy-scale-header cases=144 normal="<<normal<<" failed="<<failed
   <<" frames="<<frames<<" metadata_takes="<<meta<<" held_halt="<<held_halt
   <<" deferred="<<deferred<<" rejected_ACK="<<d.rejected_ack<<" initial="<<initial<<"\n";
  return 0;
 }catch(const std::exception& e){std::cerr<<e.what()<<"\n";return 1;}
}
