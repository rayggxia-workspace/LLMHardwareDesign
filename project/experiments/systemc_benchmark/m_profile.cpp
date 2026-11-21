// Complete native descriptor timing grid with direct S64 arithmetic checks.
// Prepared A is the captured first real row, replicated across rows for a
// data-independent shape/handshake test; this is not full-model numeric evidence.
#define main activity_driver_main
#include "m_activity.cpp"
#undef main
#include <map>

int main(int argc,char**argv){
 try{
  Verilated::commandArgs(argc,argv);
  if(argc<3)throw std::runtime_error("usage: M-profile real-tile.tsv output.jsonl [+verilator options]");
  std::ifstream f(argv[1]);std::vector<Operand> input;Operand x;
  while(f>>x.a>>x.b>>x.shift)input.push_back(x);
  if(input.size()!=768)throw std::runtime_error("expected full real tile");
  std::ofstream output(argv[2]);if(!output)throw std::runtime_error("cannot write profile");
  Bench bench;unsigned count=0;
  for(unsigned fmt=0;fmt<4;++fmt)for(unsigned rows=1;rows<=8;++rows)
  for(unsigned tiles=1;tiles<=4;++tiles)for(unsigned tail=1;tail<=8;++tail)
  for(unsigned n=1;n<=8;++n){
   bench.reset();bench.command(6,0,0);bench.command(4,0,1);
   auto& d=bench.dut;bool wa=fmt&1,wb=fmt&2;unsigned bank=count%2;
   const auto load_begin=bench.cycles;
   d.b_bank=bank;d.b_wide=wb;
   for(unsigned t=0;t<tiles;++t)for(unsigned h=0;h<(wb?2:1);++h){
    for(unsigned j=0;j<16;++j)d.b_data[j]=0;
    const unsigned lanes=wb?32:64;
    for(unsigned j=0;j<lanes;++j){
     unsigned col=wb?h*4+j/8:j/8,k=j%8;
     const auto v=input[((t*8+k)*8+col)*3].b;
     if(wb)d.b_data[j/2]|=uint32_t(uint16_t(v))<<(16*(j%2));
     else d.b_data[j/4]|=uint32_t(uint8_t(v))<<(8*(j%4));
    }
    d.b_tile=t;d.b_half=h;d.b_valid=1;d.eval();
    if(!d.b_ready)throw std::runtime_error("grid B unexpectedly stalled");bench.tick();
   }
   d.b_valid=0;d.a_bank=bank;d.a_wide=wa;
   for(unsigned row=0;row<rows;++row)for(unsigned t=0;t<tiles;++t){
    for(unsigned j=0;j<4;++j)d.a_data[j]=0;
    for(unsigned k=0;k<8;++k){
     const auto v=input[((t*8+k)*8)*3].a;
     if(wa)d.a_data[k/2]|=uint32_t(uint16_t(v))<<(16*(k%2));
     else d.a_data[k/4]|=uint32_t(uint8_t(v))<<(8*(k%4));
    }
    d.a_row=row;d.a_tile=t;d.a_valid=1;d.eval();
    if(!d.a_ready)throw std::runtime_error("grid A unexpectedly stalled");bench.tick();
   }
   d.a_valid=0;d.eval();const auto loaded=bench.cycles;
   bench.command(10,bank*32,unsigned(wa)|(unsigned(wb)<<1)|4|(tail<<4)|(n<<8)|(tiles<<12)|(rows<<15));
   const auto executed=bench.cycles;
   std::array<int64_t,8> expected{};
   for(unsigned t=0;t<tiles;++t)for(unsigned k=0;k<(t+1==tiles?tail:8);++k)
   for(unsigned col=0;col<n;++col){
    const auto av=input[((t*8+k)*8)*3].a,bv=input[((t*8+k)*8+col)*3].b;
    expected[col]+=int64_t(wa?int16_t(av):int8_t(av))*int64_t(wb?int16_t(bv):int8_t(bv));
   }
   for(unsigned row=0;row<rows;++row)for(unsigned pair=0;pair<4;++pair){
    auto actual=bench.command(3,row*8+pair,0);
    if(int64_t(actual)!=expected[2*pair]||int64_t(actual>>64)!=expected[2*pair+1])
     throw std::runtime_error("descriptor-grid S64 mismatch");
   }
   output<<"{\"wide_a\":"<<unsigned(wa)<<",\"wide_b\":"<<unsigned(wb)
    <<",\"rows\":"<<rows<<",\"tiles\":"<<tiles<<",\"last_k\":"<<tail
    <<",\"columns\":"<<n<<",\"load_cycles\":"<<loaded-load_begin
    <<",\"execute_with_response_cycles\":"<<executed-loaded
    <<",\"read_all_s64_cycles\":"<<bench.cycles-executed<<"}\n";
   ++count;
   if(count%512==0)std::cout<<"CHECKED "<<count<<std::endl;
  }
  std::cout<<"PROFILE {\"descriptors_checked\":"<<count<<",\"cycles\":"<<bench.cycles
   <<",\"exact_s64_passed\":true,\"full_model_qualified\":false}\n";
  return 0;
 }catch(const std::exception& e){std::cerr<<e.what()<<"\n";return 1;}
}
