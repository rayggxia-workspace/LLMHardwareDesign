// Candidate RTL probe, not physical or full-model acceptance.
// Build with the frozen systemc_benchmark/m_activity.cpp copied beside this file.
#define main activity_driver_main
#include "m_activity.cpp"
#undef main

int main(int argc,char**argv){
 try{
  Verilated::commandArgs(argc,argv);
  Bench b;unsigned checked=0;std::array<uint64_t,4> periods{};
  for(unsigned format=0;format<4;++format)for(unsigned tiles:{1u,4u,8u,16u,32u})
  for(unsigned tail:{1u,8u})for(unsigned columns:{1u,8u})for(unsigned bank=0;bank<2;++bank){
   b.reset();b.command(6,0,0);b.command(4,0,1);
   auto& d=b.dut;bool wa=format&1,wb=format&2;
   std::array<int64_t,8> expected{};
   auto aval=[&](unsigned k)->int {return wa?int(int16_t(k*739+format*1021+bank*3907)):int(int8_t(k*23+format*19+bank*37));};
   auto bval=[&](unsigned k,unsigned n)->int {return wb?int(int16_t(k*313+n*1711+bank*919)):int(int8_t(k*17+n*31+bank*19));};
   d.a_bank=bank;d.a_wide=wa;
   for(unsigned t=0;t<tiles;++t){
    for(unsigned i=0;i<4;++i)d.a_data[i]=0;
    for(unsigned k=0;k<8;++k){
     auto a=aval(t*8+k);
     if(wa)d.a_data[k/2]|=uint32_t(uint16_t(a))<<(16*(k%2));
     else d.a_data[k/4]|=uint32_t(uint8_t(a))<<(8*(k%4));
    }
    d.a_row=t/4;d.a_tile=t%4;d.a_valid=1;d.eval();
    if(!d.a_ready)throw std::runtime_error("A load stalled");b.tick();
   }
   d.a_valid=0;d.b_bank=bank;d.b_wide=wb;
   for(unsigned t=0;t<tiles;++t)for(unsigned half=0;half<(wb?2u:1u);++half){
    for(unsigned i=0;i<16;++i)d.b_data[i]=0;
    for(unsigned j=0;j<(wb?32u:64u);++j){
     unsigned n=wb?half*4+j/8:j/8,k=j%8;int v=bval(t*8+k,n);
     if(wb)d.b_data[j/2]|=uint32_t(uint16_t(v))<<(16*(j%2));
     else d.b_data[j/4]|=uint32_t(uint8_t(v))<<(8*(j%4));
    }
    d.b_tile=t;d.b_half=half;d.b_valid=1;d.eval();
    if(!d.b_ready)throw std::runtime_error("B load stalled");b.tick();
   }
   d.b_valid=0;d.eval();auto begin=b.cycles;
   b.command(13,bank*32,format|4|(tail<<4)|(columns<<8)|(tiles<<12)|(1<<18));
   auto duration=b.cycles-begin;
   if(format==0&&tiles==32&&tail==8&&columns==8&&duration!=45)
    throw std::runtime_error("unexpected K256 timing");
   for(unsigned t=0;t<tiles;++t)for(unsigned k=0;k<(t+1==tiles?tail:8);++k)
    for(unsigned n=0;n<columns;++n)expected[n]+=int64_t(aval(t*8+k))*bval(t*8+k,n);
   for(unsigned pair=0;pair<4;++pair){
    auto actual=b.command(3,pair,0);
    if(int64_t(actual)!=expected[2*pair]||int64_t(actual>>64)!=expected[2*pair+1])
     throw std::runtime_error("long K S64 mismatch");
   }
   if(tiles==32&&tail==8&&columns==8&&bank==0){
    d.cmd_op=13;d.cmd_index=0;d.cmd_data=format|4|(8<<4)|(8<<8)|(32<<12)|(1<<18);
    d.rsp_ready=1;d.cmd_valid=1;d.eval();
    std::vector<uint64_t> accepts,responses;
    for(unsigned guard=0;responses.size()<1024;++guard){
     if(guard>1024*1000)throw std::runtime_error("saturation timeout");
     if(d.cmd_valid&&d.cmd_ready)accepts.push_back(b.cycles);
     if(d.rsp_valid){
      if(d.rsp_error||d.rsp_saturated)throw std::runtime_error("saturation command error");
      responses.push_back(b.cycles);
     }
     b.tick();if(accepts.size()==1024)d.cmd_valid=0;d.eval();
    }
    if(accepts.size()!=1024)throw std::runtime_error("saturation count mismatch");
    auto period256=accepts[1]-accepts[0];periods[format]=period256;
    for(unsigned j=1;j<1024;++j)
     if(accepts[j]-accepts[j-1]!=period256||responses[j]-responses[j-1]!=period256)
      throw std::runtime_error("saturation interval mismatch");
    d.rsp_ready=0;d.eval();
    for(unsigned pair=0;pair<4;++pair){
     auto actual=b.command(3,pair,0);
     if(int64_t(actual)!=expected[2*pair]||int64_t(actual>>64)!=expected[2*pair+1])
      throw std::runtime_error("saturation S64 mismatch");
    }
   }
   ++checked;
  }
  // Invalid long rows must reject before modifying architectural state.
  auto& d=b.dut;d.cmd_op=13;d.cmd_index=0;d.cmd_data=4|(8<<4)|(8<<8)|(4<<12)|(2<<18);
  d.cmd_valid=1;b.tick();d.cmd_valid=0;
  unsigned watchdog=0;while(!d.rsp_valid){if(++watchdog>1000)throw std::runtime_error("reject timeout");b.tick();}
  if(!d.rsp_error)throw std::runtime_error("unsupported multirow long K accepted");
  std::cout<<"LONGK {\"descriptors_checked\":"<<checked
   <<",\"k256_s8_execute_with_response_cycles\":"<<periods[0]+1
   <<",\"k256_s8_measured_accept_interval_1024_commands\":"<<periods[0]
   <<",\"k256_measured_intervals_by_format\":{\"S8_S8\":"<<periods[0]
   <<",\"S16_S8\":"<<periods[1]<<",\"S8_S16\":"<<periods[2]
   <<",\"S16_S16\":"<<periods[3]<<"}"
   <<",\"invalid_rows_rejected\":true,\"exact_s64_passed\":true,\"physical_qualified\":false}\n";
  return 0;
 }catch(const std::exception&e){std::cerr<<e.what()<<"\n";return 1;}
}
