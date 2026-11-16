// A deliberately serial but executable schedule for the measured exact
// 15-partial provider. One raw K128 tile, one A row, one full-K output owner.
// All local reads/MC returns/native command flits are embedded in the actual
// atomic RTL service calendar. There is no DDR credit returned by LOCAL_S.
U ns_dynamic_calls=0,ns_dynamic_partials=0,ns_dynamic_S_read_B=0;
U ns_dynamic_staging_B=0,ns_dynamic_local_return_B=0,ns_dynamic_service_cycles=0;
bool ns_dynamic_target(const Op& o)const{
 return nv_int("NS_DYNAMIC",0)&&o.layout!=0&&o.k%128==0&&o.cols%8==0&&
  tensors[o.in[0]].bits==32&&tensors[o.in[1]].bits==32;
}
void ns_dynamic_worker(const Op& o,int worker,sc_event& done){
 const U started=now();auto& stats=detail::data.p[worker];++ns_dynamic_calls;
 const auto& a=tensors[o.in[0]];const auto& b=tensors[o.in[1]];
 const int active=nv_int("NS_DYNAMIC_PCOUNT",3);
 const auto columns=worker<active?detail::columns(o.cols,worker,active,cfg.paircols):std::vector<int>{};
 // One64B returned beat is held while its two/four true S128 writes ACK.
 // Larger DDR transfers must not accumulate a free full-tile payload FIFO.
 auto load64=[&](U address,U useful,detail::Flow flow){
  require(useful==32||useful==64,"dynamic raw source beat size");
  mem.transfer(worker,address,useful,false,flow,-2);
  ns_dynamic_staging_B+=useful;
 };
 for(int batch=0;batch<o.batches;++batch)for(int row=0;row<o.rows;++row)for(int col:columns){
  for(int kk=0;kk<o.k;kk+=128){
   for(int off=0;off<128;off+=16)load64(a.base+((U(batch)*o.rows+row)*o.k+kk+off)*4,64,detail::A);
   if(o.layout==1){
    for(int n=0;n<8;++n)for(int off=0;off<128;off+=16)
     load64(b.base+(U(batch)*o.cols*o.k+U(col+n)*o.k+kk+off)*4,64,detail::DYNAMIC_B);
   }else{
    for(int k=0;k<128;++k)
     load64(b.base+(U(batch)*o.k*o.cols+U(kk+k)*o.cols+col)*4,32,detail::DYNAMIC_B);
   }
   // Measured BEGIN first flit -> raw capture. Before/after fixture overhead
   // is charged separately. Concurrent reuse of this whole S interval is
   // forbidden; three P instances each have their own ordinary S port.
   const U fee=U(nv_int("NS_DYNAMIC_RECORD_CYCLES",1256));
   for(int partial=0;partial<15;++partial){
    pause_until(store[worker].reserve(now(),fee*C));
    cycles(6); // observed owner bind2 + nonfinal merge accept/apply/take4
    ++ns_dynamic_partials;++m_commands;ns_dynamic_service_cycles+=fee+6;
    ns_dynamic_S_read_B+=288*16;ns_dynamic_local_return_B+=17*64;
   }
   ++m_tiles;++stats.tiles;
  }
  // Full-K RNE, held final result and two true S128 result acknowledgements.
  cycles(2);
  for(int word=0;word<2;++word){auto reply=ns_S_request(worker,now());pause_until(reply.ack);cycles(1);}
  mem.transfer(worker,tensors[o.out].base+((U(batch)*o.rows+row)*o.cols+col)*4,32,true,detail::DOT_OUTPUT);
 }
 stats.service+=now()-started;stats.elapsed+=now()-started;done.notify(SC_ZERO_TIME);
}
