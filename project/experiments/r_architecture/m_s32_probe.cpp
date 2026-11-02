// Measure a feasible exact decomposition on the frozen, unmodified M.
#define main frozen_m_regression_main
#include "../../../work/YUZE-LU/157/inputs/test_m.cpp"
#undef main
static int8_t component(uint32_t value,unsigned part,bool is_signed){if(part==4)return is_signed?int32_t(value)>>28:(value>>28)&15;return(value>>(7*part))&127;}
int main(int argc,char**argv){try{
 Verilated::commandArgs(argc,argv);dut_ptr=new Vblock_v2_m;reset();timed=true;cmd(4,0,1);
 uint64_t execute_cycles=0,total_begin=cycles,products=0;
 for(unsigned test=0;test<24;++test){
  std::array<int32_t,8>a;std::array<uint32_t,8>b;std::array<I128,8>merged{};
  bool signed_b=test%2;
  for(unsigned l=0;l<8;++l){a[l]=test<2?(l%2?INT32_MIN:INT32_MAX):int32_t(rng());b[l]=test<2?(l%2?0xffffffffu:0x80000000u):uint32_t(rng());}
  for(unsigned i=0;i<5;++i)for(unsigned j=0;j<5;++j){
   Vec aa{};Weights bb{};
   for(unsigned l=0;l<8;++l){aa[l]=component(uint32_t(a[l]),i,true);bb[0][l][l]=component(b[l],j,signed_b);}
   put_a(0,0,0,aa,false);put_b(0,0,bb,false);auto reply=cmd(10,0,descriptor(false,false,true,8,8,1,1));execute_cycles+=reply.latency;
   for(unsigned pair=0;pair<4;++pair){auto v=cmd(3,pair,0).data;for(unsigned t=0;t<2;++t){unsigned l=2*pair+t;int64_t product=int64_t(v>>(64*t));int64_t expect=int64_t(aa[l])*bb[0][l][l];ck(product==expect,"S8 M diagonal product mismatch");merged[l]+=I128(product)*(I128(1)<<(7*(i+j)));++products;}}
  }
  for(unsigned l=0;l<8;++l){I128 expect=I128(a[l])*(signed_b?I128(int32_t(b[l])):I128(b[l]));ck(merged[l]==expect,"exact S32 reconstruction mismatch");}
 }
 std::cout<<"{\"passed\":true,\"vectors\":24,\"S8_pairs_per_S32_pair\":25,\"M_commands\":600,\"multiply_results_checked\":"<<products<<",\"execute_latency_sum\":"<<execute_cycles<<",\"total_load_execute_read_handshake_cycles\":"<<cycles-total_begin<<",\"wide_merge_hardware\":\"NOT_IMPLEMENTED_SOFTWARE_ORACLE_ONLY\"}\n";delete dut_ptr;return 0;
}catch(const std::exception&e){std::cerr<<e.what()<<'\n';delete dut_ptr;return 1;}}
