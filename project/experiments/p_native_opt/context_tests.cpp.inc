// Native S16 A/B arithmetic uses the unchanged signed integer helper above.
// Golden values below use a direct __int128 dot product, never digit decomposition.
#ifndef TEST_CONTEXTS
#define TEST_CONTEXTS 8
#endif
static_assert(TEST_CONTEXTS==1||TEST_CONTEXTS==2||TEST_CONTEXTS==8,"invalid test context count");
static constexpr unsigned context_count=TEST_CONTEXTS;
struct Traffic {
 uint64_t wall=0,a_beats=0,b_beats=0,a_logical=0,b_logical=0,commands=0;
};
static uint64_t context_descriptor(bool wa,bool wb,bool first,bool final,unsigned k,unsigned n,
                                   unsigned tiles,unsigned arow,unsigned offset,unsigned tag){
 return unsigned(wa)|(uint64_t(wb)<<1)|(uint64_t(first)<<2)|(uint64_t(final)<<3)|
        (uint64_t(k)<<4)|(uint64_t(n)<<8)|(uint64_t(tiles)<<12)|(uint64_t(arow)<<15)|
        (uint64_t(offset)<<18)|(uint64_t(tag)<<34);
}
static uint64_t release_descriptor(unsigned tag,bool abort=false){return (uint64_t(tag)<<1)|unsigned(abort);}
static unsigned segment_len(unsigned total,unsigned segment){
 unsigned left=total-32*segment;return left<32?left:32;
}
static void fill_constant(Inputs& a,Weights& b,int16_t value){
 for(auto&row:a){for(auto&tile:row){tile.fill(value);}}
 for(auto&tile:b){for(auto&row:tile){row.fill(value);}}
}
static void context_numeric(){
 const unsigned lengths[]={1,7,8,9,31,32,33,65,255,256,257};
 uint64_t total_a[3]{},total_b[3]{},total_wall[3]{},total_commands[3]{};
 for(unsigned test=0;test<44;++test){
  const unsigned total=lengths[test%11],segments=(total+31)/32,arow=(test+3)%8;
  const bool wa=(test/11)&1,wb=(test/11)&2;
  const unsigned tag=100+test;
  std::vector<Inputs> a(segments);
  std::vector<std::vector<Weights>> b(context_count,std::vector<Weights>(segments));
  std::vector<Full> full(context_count);std::vector<unsigned> n(context_count);
  for(unsigned c=0;c<context_count;++c)n[c]=1+(test+3*c)%8;
  for(unsigned s=0;s<segments;++s){
   Weights unused{};fill(a[s],unused,test+s);
   for(unsigned c=0;c<context_count;++c){Inputs unused_a{};fill(unused_a,b[c][s],test+s+c);}
   const int16_t factor=s%3==0?-17:s%3==1?32767:13;const unsigned shift=(test+s)%9;
   const unsigned count=segment_len(total,s);
   for(unsigned c=0;c<context_count;++c)for(unsigned o=0;o<n[c];++o){
    I128 sum=0;
    for(unsigned k=0;k<count;++k){
     int64_t av=wa?a[s][arow][k/8][k%8]:int8_t(a[s][arow][k/8][k%8]);
     int64_t bv=wb?b[c][s][k/8][o][k%8]:int8_t(b[c][s][k/8][o][k%8]);
     sum+=I128(av)*bv;
    }
    full[c][o]+=sum*factor*(I128(1)<<shift);
   }
  }
  // 0=original Ngroup->allK; 1=new context loop but reload A; 2=new loop + real A reuse.
  // Every route counts configuration, execution, output and release command cycles.
  Traffic traffic[3];
  for(unsigned route=0;route<3;++route){
   reset();timed=true;const auto begin=cycles;
   auto run_segment=[&](unsigned c,unsigned s,bool load_a){
    const unsigned count=segment_len(total,s),tiles=(count+7)/8,last=(count-1)%8+1,bank=s%2;
    if(load_a)for(unsigned t=0;t<tiles;++t){put_a(bank,route==0?0:arow,t,a[s][arow][t],wa);
     ++traffic[route].a_beats;traffic[route].a_logical+=wa?16:8;}
    for(unsigned t=0;t<tiles;++t){put_b(bank,t,b[c][s],wb);
     traffic[route].b_beats+=wb?2:1;traffic[route].b_logical+=wb?128:64;}
    const int16_t factor=s%3==0?-17:s%3==1?32767:13;const unsigned shift=(test+s)%9;
    cmd(4,0,uint16_t(factor)|(uint64_t(shift)<<16));++traffic[route].commands;
    if(route==0)cmd(10,bank*32,descriptor(wa,wb,s==0,last,n[c],tiles,1));
    else cmd(13,bank*32+c,context_descriptor(wa,wb,s==0,s+1==segments,last,n[c],tiles,arow,32*s,tag));
    ++traffic[route].commands;
   };
   if(route==0){
    for(unsigned c=0;c<context_count;++c){
     for(unsigned s=0;s<segments;++s)run_segment(c,s,true);
     check_raw(0,full[c]);check_final(0,full[c],test%64,test%3);traffic[route].commands+=6;
    }
   }else{
    for(unsigned s=0;s<segments;++s)for(unsigned c=0;c<context_count;++c)run_segment(c,s,route==1||c==0);
    for(unsigned c=0;c<context_count;++c){
     check_raw(c,full[c]);check_final(c,full[c],test%64,test%3);traffic[route].commands+=6;
     cmd(14,c,release_descriptor(tag));++traffic[route].commands;
    }
   }
   traffic[route].wall=cycles-begin;timed=false;
   total_a[route]+=traffic[route].a_beats;total_b[route]+=traffic[route].b_beats;
   total_wall[route]+=traffic[route].wall;total_commands[route]+=traffic[route].commands;
  }
  ck(traffic[0].a_beats==traffic[1].a_beats,"reordering control must not silently reuse A");
  ck(traffic[1].a_beats==traffic[2].a_beats*context_count,"actual A handshake reuse ratio");
  ck(traffic[0].b_beats==traffic[1].b_beats&&traffic[1].b_beats==traffic[2].b_beats,"B loads changed");
  ck(traffic[1].commands==traffic[2].commands,"A reuse changed context command work");
  std::cout<<"{\"type\":\"case\",\"test\":"<<test<<",\"contexts\":"<<context_count
    <<",\"K\":"<<total<<",\"Awide\":"<<wa<<",\"Bwide\":"<<wb<<",\"routes\":[";
  for(unsigned r=0;r<3;++r){if(r)std::cout<<",";const auto&t=traffic[r];
   std::cout<<"{\"cycles\":"<<t.wall<<",\"A_handshakes\":"<<t.a_beats
    <<",\"A_logical_bytes\":"<<t.a_logical<<",\"A_wire_bytes\":"<<16*t.a_beats
    <<",\"B_handshakes\":"<<t.b_beats<<",\"B_logical_bytes\":"<<t.b_logical
    <<",\"B_wire_bytes\":"<<64*t.b_beats<<",\"commands\":"<<t.commands<<"}";
  }
  std::cout<<"]}\n";++cases;
 }
 std::cout<<"{\"type\":\"totals\",\"contexts\":"<<context_count<<",\"routes\":[";
 for(unsigned r=0;r<3;++r){if(r)std::cout<<",";
  std::cout<<"{\"cycles\":"<<total_wall[r]<<",\"A_handshakes\":"<<total_a[r]
   <<",\"B_handshakes\":"<<total_b[r]<<",\"commands\":"<<total_commands[r]<<"}";}
 std::cout<<"]}\n";
}
static void context_safeguards(){
 reset();timed=false;const unsigned row=5,tag=77;
 auto desc=[&](bool first,bool final,unsigned offset){return context_descriptor(false,false,first,final,3,5,1,row,offset,tag);};
 cmd(13,0,desc(true,false,0),true);cmd(14,0,release_descriptor(tag),true);
 Inputs a{};Weights b{};
 fill_constant(a,b,1);
 put_a(0,row,0,a[row][0],false);put_b(0,0,b,false);
 cmd(13,8,desc(true,false,0),true); // reserved index bits, also outside all limits
 if(context_count<8)cmd(13,context_count,desc(true,false,0),true);
 cmd(13,0,desc(true,false,0)|(uint64_t(1)<<50),true);
 for(unsigned field=0;field<3;++field){
  const unsigned shift=field==0?4:field==1?8:12;
  const uint64_t mask=field==2?7:15;
  const uint64_t base=desc(true,false,0)&~(mask<<shift);
  cmd(13,0,base,true);
  cmd(13,0,base|(uint64_t(field==2?5:9)<<shift),true);
 }
 cmd(13,0,desc(true,false,0)^(uint64_t(1)<<15),true); // different, unloaded A row
 cmd(13,0,desc(true,false,0)|1,true); // mismatched A format
 cmd(13,0,desc(true,false,0)|2,true); // mismatched B format
 cmd(13,0,desc(true,false,1),true); // first must start at K zero
 cmd(13,0,desc(false,false,0),true); // cannot append free context
 cmd(13,0,desc(true,false,0));
 cmd(3,0,0,true);cmd(5,0,0,true); // only final context is readable
 cmd(10,0,descriptor(0,0,1,3,5,1,1),true); // original mode may not alias live context slots
 cmd(13,0,desc(true,false,0),true);cmd(13,0,desc(false,true,4),true);
 cmd(13,0,desc(false,true,3)^(uint64_t(1)<<34),true); // stale group tag
 cmd(13,0,desc(false,true,3)^(uint64_t(1)<<8),true); // N changes
 cmd(14,0,release_descriptor(tag),true);cmd(14,0,release_descriptor(tag+1,true),true);
 cmd(13,0,desc(false,true,3));Full six{};for(unsigned n=0;n<5;++n)six[n]=6;check_raw(0,six);
 cmd(13,0,desc(false,true,6),true);cmd(13,0,desc(true,true,0),true);
 cmd(14,0,release_descriptor(tag+1),true);cmd(14,0,release_descriptor(tag));
 // Explicit abort discards an active result, then the slot can host a new generation.
 cmd(13,0,desc(true,false,0));cmd(14,0,release_descriptor(tag,true));cmd(3,0,0,true);
 cmd(13,0,desc(true,true,0));cmd(6,0,0);cmd(3,0,0,true);
 // Reset an executing command; no stale completion or context may reappear.
 put_a(0,row,0,a[row][0],false);put_b(0,0,b,false);
 d.cmd_valid=1;d.cmd_op=13;d.cmd_index=0;d.cmd_data=desc(true,true,0);tick();d.cmd_valid=0;
 tick();reset();for(unsigned i=0;i<30;++i){tick();ck(!d.rsp_valid,"ghost context completion after reset");}
 cmd(13,0,desc(false,true,0),true);cmd(3,0,0,true);
 // Start-cycle and in-flight operand locks, independent other-bank progress and held response.
 put_a(0,row,0,a[row][0],false);put_b(0,0,b,false);
 d.cmd_valid=1;d.cmd_op=13;d.cmd_index=0;d.cmd_data=desc(true,true,0);
 d.a_valid=1;d.a_bank=0;d.b_valid=1;d.b_bank=0;d.eval();ck(!d.a_ready&&!d.b_ready,"context start bank lock");
 tick();d.cmd_valid=0;d.eval();ck(!d.a_ready&&!d.b_ready,"context execution bank lock");
 d.a_bank=1;prepare_b(1,0,b,false,0);d.eval();ck(d.a_ready&&d.b_ready,"free operand bank blocked");
 tick();d.a_valid=0;d.b_valid=0;unsigned wait_cycles=0;
 while(!d.rsp_valid){ck(++wait_cycles<5000,"manual context completion timeout");tick();}
 ck(!d.rsp_error,"context completion failed");
 const auto held=response();
 for(unsigned i=0;i<7;++i){tick();ck(!d.cmd_ready&&d.rsp_valid&&response()==held,"context response backpressure");}
 d.rsp_ready=1;tick();d.rsp_ready=0;Full three{};for(unsigned n=0;n<5;++n)three[n]=3;check_raw(0,three);
 cmd(14,0,release_descriptor(tag));
}
static void context_overflow(){
 reset();const unsigned tag=333,row=7,target=context_count-1;
 Inputs a{};Weights b{};
 fill_constant(a,b,1);
 put_a(0,row,0,a[row][0],true);put_b(0,0,b,true);
 cmd(13,target,context_descriptor(1,1,1,0,1,8,1,row,0,tag));
 fill_constant(a,b,-32768);
 for(unsigned t=0;t<4;++t){put_a(0,row,t,a[row][t],true);put_b(0,t,b,true);}
 cmd(4,0,32767|(uint64_t(31)<<16));
 auto rejected=cmd(13,target,context_descriptor(1,1,0,1,8,8,4,row,1,tag),true);
 ck(uint8_t(rejected.data)==(1u<<target),"context atomic overflow mask");
 // Retry the exact old K offset after failure: both payload and nextK must be unchanged.
 fill_constant(a,b,1);
 put_a(0,row,0,a[row][0],true);put_b(0,0,b,true);cmd(4,0,1);
 cmd(13,target,context_descriptor(1,1,0,1,1,8,1,row,1,tag));Full two{};two.fill(2);check_raw(target,two);
 cmd(14,target,release_descriptor(tag));
 // A failed FIRST must not allocate or poison a free context.
 fill_constant(a,b,-32768);
 for(unsigned t=0;t<4;++t){put_a(0,row,t,a[row][t],true);put_b(0,t,b,true);}
 cmd(4,0,32767|(uint64_t(31)<<16));cmd(13,target,context_descriptor(1,1,1,1,8,8,4,row,0,tag),true);
 cmd(14,target,release_descriptor(tag,true),true);
 cmd(4,0,0);cmd(13,target,context_descriptor(1,1,1,1,8,8,4,row,0,tag));Full zero{};check_raw(target,zero);
 cmd(14,target,release_descriptor(tag));
 // Independently cover S64 ADD overflow, with an aligned segment that itself fits.
 cmd(4,0,32767|(uint64_t(13)<<16));
 cmd(13,target,context_descriptor(1,1,1,0,8,8,4,row,0,tag));
 auto add_rejected=cmd(13,target,context_descriptor(1,1,0,1,8,8,4,row,32,tag),true);
 ck(uint8_t(add_rejected.data)==(1u<<target),"context S64 addition overflow mask");
 cmd(4,0,0);cmd(13,target,context_descriptor(1,1,0,1,1,8,1,row,32,tag));
 Full preserved{};preserved.fill((I128(1)<<63)-(I128(1)<<48));
 check_raw(target,preserved);check_final(target,preserved,48,2);cmd(14,target,release_descriptor(tag));
}
static void context_k_bound(){
 reset();timed=true;Inputs a{};Weights b{};
 fill_constant(a,b,1);
 for(unsigned t=0;t<4;++t){put_a(0,0,t,a[0][t],false);put_b(0,t,b,false);}
 for(unsigned s=0;s<2047;++s)cmd(13,0,context_descriptor(0,0,s==0,0,8,1,4,0,32*s,9));
 cmd(13,0,context_descriptor(0,0,0,0,7,1,4,0,65504,9)); // nextK=65535
 cmd(13,0,context_descriptor(0,0,0,1,1,1,1,0,65535,9),true); // no silent 16-bit wrap
 cmd(14,0,release_descriptor(9,true));timed=false;
}
int main(int argc,char**argv){try{
 Verilated::commandArgs(argc,argv);dut_ptr=new Vblock_v2_m_context;reset();
 context_numeric();context_safeguards();context_overflow();context_k_bound();
 std::cout<<"{\"passed\":true,\"contexts\":"<<context_count<<",\"checks\":"<<checks
   <<",\"cycles\":"<<cycles<<",\"cases\":"<<cases
   <<",\"partial_bits\":40,\"result_bits\":64,\"added_psum_payload_bits\":0"
   <<",\"context_metadata_bits\":288,\"execute_metadata_bits\":37,\"physical_qualified\":false}\n";
 delete dut_ptr;return 0;
 }catch(const std::exception&e){std::cerr<<"FAIL "<<cycles<<" "<<e.what()<<"\n";delete dut_ptr;return 1;}}
