// Optimistic native command-rate probe. Inputs stay resident, rsp_ready=1,
// next Execute is already asserted. No DMA/LC/S stalls, no output readout.
// S8 truncation is a timing fixture; it is NOT Qwen quantization evidence.
#define main activity_driver_main
#include "m_activity.cpp"
#undef main

int main(int argc,char** argv) {
 try {
  Verilated::commandArgs(argc,argv);
  if(argc<2)throw std::runtime_error("usage: M-saturation tile.tsv [+verilator options]");
  std::ifstream file(argv[1]);std::vector<Operand> v;Operand x;
  while(file>>x.a>>x.b>>x.shift)v.push_back(x);
  if(v.size()!=768)throw std::runtime_error("real tile required");
  Bench b;b.reset();b.command(6,0,0);b.command(4,0,1);
  auto& d=b.dut;d.a_bank=0;d.a_wide=0;d.a_row=0;
  for(unsigned t=0;t<4;++t){
   for(unsigned i=0;i<4;++i)d.a_data[i]=0;
   for(unsigned k=0;k<8;++k)d.a_data[k/4]|=uint32_t(uint8_t(v[((t*8+k)*8)*3].a))<<(8*(k%4));
   d.a_tile=t;d.a_valid=1;d.eval();
   if(!d.a_ready)throw std::runtime_error("A stalled");b.tick();
  }
  d.a_valid=0;d.b_bank=0;d.b_wide=0;d.b_half=0;
  for(unsigned t=0;t<4;++t){
   for(unsigned i=0;i<16;++i)d.b_data[i]=0;
   for(unsigned n=0;n<8;++n)for(unsigned k=0;k<8;++k){
    unsigned j=n*8+k;
    d.b_data[j/4]|=uint32_t(uint8_t(v[((t*8+k)*8+n)*3].b))<<(8*(j%4));
   }
   d.b_tile=t;d.b_valid=1;d.eval();
   if(!d.b_ready)throw std::runtime_error("B stalled");b.tick();
  }
  d.b_valid=0;d.cmd_op=10;d.cmd_index=0;
  d.cmd_data=4|(8<<4)|(8<<8)|(4<<12)|(1<<15);
  d.rsp_ready=1;d.cmd_valid=1;d.eval();
  std::vector<uint64_t> accepts,responses;
  const unsigned count=1024;
  for(unsigned watchdog=0;responses.size()<count;++watchdog){
   if(watchdog>count*100)throw std::runtime_error("saturation timeout");
   if(d.cmd_valid&&d.cmd_ready){accepts.push_back(b.cycles);if(accepts.size()>count)throw std::runtime_error("extra command");}
   if(d.rsp_valid){
    if(d.rsp_error||d.rsp_saturated||d.rsp_data[0]||d.rsp_data[1]||d.rsp_data[2]||d.rsp_data[3])
     throw std::runtime_error("Execute failed");
    responses.push_back(b.cycles);
   }
   b.tick();
   if(accepts.size()==count)d.cmd_valid=0;
   d.eval();
  }
  if(accepts.size()!=count)throw std::runtime_error("command/response count mismatch");
  uint64_t interval=accepts[1]-accepts[0];
  for(unsigned i=1;i<count;++i)
   if(accepts[i]-accepts[i-1]!=interval||responses[i]-responses[i-1]!=interval)
    throw std::runtime_error("nonuniform command interval");
  d.rsp_ready=0;d.eval();
  std::array<int64_t,8> expected{};
  for(unsigned k=0;k<32;++k)for(unsigned n=0;n<8;++n)
   expected[n]+=int64_t(int8_t(v[(k*8)*3].a))*int64_t(int8_t(v[(k*8+n)*3].b));
  for(unsigned p=0;p<4;++p){
   auto value=b.command(3,p,0);
   if(int64_t(value)!=expected[2*p]||int64_t(value>>64)!=expected[2*p+1])
    throw std::runtime_error("final S64 result mismatch");
  }
  std::cout<<"SATURATION {\"commands\":"<<count<<",\"accept_to_accept_cycles\":"<<interval
   <<",\"first_response_cycles\":"<<responses[0]-accepts[0]
   <<",\"macs_per_command\":256,\"exact_s64_passed\":true,\"full_model_qualified\":false}\n";
  return 0;
 }catch(const std::exception& e){std::cerr<<e.what()<<"\n";return 1;}
}
