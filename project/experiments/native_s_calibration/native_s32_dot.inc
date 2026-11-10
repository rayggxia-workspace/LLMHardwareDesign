// Refs #252/#253. Conservative service calendars from actual four-bank
// RTL, including all K128 input groups and true result write acknowledgements.
// One provider and one ordinary S128 port per P. Tile count/precision/DDR
// channels do not change with hardware capacity or residence order.
U ns_dot_calls=0,ns_dot_begins=0,ns_dot_chunks=0,ns_dot_macs=0;
U ns_dot_A_staged=0,ns_dot_B_staged=0,ns_dot_bus_read=0,ns_dot_S_reads=0;
U ns_dot_S_result_writes=0,ns_dot_S_export_reads=0,ns_dot_service_cycles=0;
U ns_dot_s_peak=0,ns_dot_raw_live=0,ns_dot_raw_peak=0,ns_dot_qk_reuse=0;
U ns_dot_av_saves=0,ns_dot_av_restores=0,ns_dot_av_snapshot_S_words=0,ns_dot_av_pair_beats=0;
bool ns_dot_target(const Op& o) const{
 return nv_int("NS_NATIVE_DOT",0)&&(o.layout==1||o.layout==2)&&
  (o.k==128||o.k==512)&&o.cols%8==0&&o.shift>=0&&o.shift<=63&&
  tensors[o.in[0]].bits==32&&tensors[o.in[1]].bits==32&&tensors[o.out].bits==32;
}
void ns_dot_worker(const Op& o,int worker,sc_event& done){
 const U started=now();auto& stats=detail::data.p[worker];++ns_dot_calls;
 const int cap=nv_int("NS_DOT_ROWS",1),reuse=nv_int("NS_DOT_REUSE",0);
 const int depth=nv_int("NS_DOT_RAW_SLOTS",1),pressure=nv_int("NS_DOT_PRESSURE",0);
 const bool narrow=nv_int("NS_DOT_STAGE64",0);
 require((cap==1||cap==2||cap==4)&&o.rows%cap==0,"native S32 measured active-row group");
 require(reuse>=0&&reuse<=2&&depth>=1&&depth<=2&&pressure>=0&&pressure<=1,"native S32 schedule choices");
 const int ci=cap==1?0:cap==2?1:2;
 const auto& a=tensors[o.in[0]];const auto& b=tensors[o.in[1]];
 const auto& output=tensors[o.out];
 const int wave_pairs=o.layout==2&&cap==4&&o.rows==8&&o.k==512&&o.cols%16==0?
    nv_int("NS_DOT_AV_CKPT_PAIRS",0):0;
 const bool av_wave=wave_pairs!=0;
 require(!av_wave||(wave_pairs>=1&&wave_pairs<=2&&cap==4&&o.rows==8&&o.k==512&&o.cols%16==0&&narrow),
  "native AV checkpoint experiment is restricted to the measured R4 workload");
 const auto columns=detail::columns(o.cols,worker,cfg.mcount,av_wave||cfg.paircols);
 if(columns.empty()){done.notify(SC_ZERO_TIME);return;}
 const U fixed_reserved=2*U(cfg.cl_head_group==16?128:64);
 require(cfg.mcount==3&&cfg.pbytes+fixed_reserved==16384&&cfg.beat==64,"native S32 fixed three-P resource contract");
 require(a.base%64==0&&b.base%64==0&&output.base%64==0,"native S32 raw and output layout alignment");
 const bool reuse_B=reuse==2&&o.layout==1&&o.k==128;
 const U resident_A=reuse_B?U(o.rows)*512:U(cap)*(reuse?U(o.k)*4:512);
 const U checkpoint_words=U(cap)*5+2; // exact S80 state and two owner/format header words
 const U wave_columns=std::min<U>(columns.size(),2*wave_pairs);
 const U window=av_wave?U(o.rows)*512+8192+wave_columns*(o.rows/cap)*checkpoint_words*16+32*U(cap):
    resident_A+4096+32*U(cap);
 require(window<=cfg.pbytes,"native S32 fixed A/B/result windows exceed S");
 ns_dot_s_peak=std::max(ns_dot_s_peak,window+fixed_reserved);
 // Reuse the existing global six64B data slots, at most one or two raw
 // descriptors per P. Each slot remains owned through all true S write ACKs
 // in the existing -2 typed calendar. Two-slot DMA producer is a candidate,
 // not measured native source RTL; the model has no extra full-tile FIFO.
 std::deque<std::shared_ptr<Burst>> pending;
 auto pop_raw=[&](){mem.await(pending.front());pending.pop_front();require(ns_dot_raw_live>0,"native S32 raw owner underflow");--ns_dot_raw_live;};
 auto flush=[&](){while(!pending.empty())pop_raw();};
 auto stage=[&](U address,U bytes,detail::Flow flow){
  require((bytes==32||bytes==64)&&address%64+bytes<=64,"native S32 one physical source beat");
  if(pending.size()==size_t(depth))pop_raw();
  pending.push_back(mem.submit(worker,address,bytes,false,flow,-2));
  ++ns_dot_raw_live;ns_dot_raw_peak=std::max(ns_dot_raw_peak,ns_dot_raw_live);
  require(ns_dot_raw_live<=U(3*depth),"native S32 bounded raw return slots");
  ns_dot_bus_read+=64;
  if(flow==detail::A)ns_dot_A_staged+=bytes;else ns_dot_B_staged+=bytes;
 };
 auto stage_A=[&](int batch,int row,int rows,int kk){
  for(int r=0;r<rows;++r)for(int off=0;off<128;off+=16)
   stage(a.base+((U(batch)*o.rows+row+r)*o.k+kk+off)*4,64,detail::A);
 };
 auto stage_B=[&](int batch,int col,int kk){
  if(o.layout==1){
   for(int n=0;n<8;++n)for(int off=0;off<128;off+=16)
    stage(b.base+(U(batch)*o.cols*o.k+U(col+n)*o.k+kk+off)*4,64,detail::DYNAMIC_B);
  }else for(int k=0;k<128;++k)
   stage(b.base+(U(batch)*o.k*o.cols+U(kk+k)*o.cols+col)*4,32,detail::DYNAMIC_B);
 };
 auto begin_owner=[&](){
  const int begin=ns_dot_profile::begin[narrow][pressure][o.layout-1][ci];
  cycles(begin);++ns_dot_begins;ns_dot_service_cycles+=begin;
 };
 auto run_chunk=[&](int kk){
  flush(); // source committed before CHUNK; never overlap aliased S windows
  const int index=o.k==128?0:1+kk/128;
  const U fee=ns_dot_profile::chunks[narrow][pressure][o.layout-1][ci][index];
  pause_until(store[worker].reserve(now(),fee*C));
  ++ns_dot_chunks;++m_commands;m_tiles+=cap;stats.tiles+=cap;
  ns_dot_service_cycles+=fee;ns_dot_macs+=U(cap)*128*8;ns_dot_S_reads+=U(32)*(cap+8);
  if(kk+128==o.k)ns_dot_S_result_writes+=2*cap;
 };
 auto export_owner=[&](int batch,int row,int col){
  // Two true S128 reads pack each32B logical DDR write. Typed -3 replaces
  // generic prewrite port charge; no second reservation/zero-cost export.
  for(int r=0;r<cap;++r){
   mem.transfer(worker,output.base+((U(batch)*o.rows+row+r)*o.cols+col)*4,32,true,detail::DOT_OUTPUT,-3);
   ns_dot_S_export_reads+=2;
  }
 };
 auto run_owner=[&](int batch,int row,int col,bool A_ready,bool B_ready){
  begin_owner();
  for(int kk=0;kk<o.k;kk+=128){
   if(!A_ready)stage_A(batch,row,cap,kk);
   if(!B_ready)stage_B(batch,col,kk);
   run_chunk(kk);
  }
  export_owner(batch,row,col);
 };
 auto checkpoint=[&](bool load){
  // Sensitivity until the checked S80 import/export RTL exists. Includes
  // all header/data writes or reads, fixed CPA/control, and last true ACK.
  const U gap=U(nv_int("NS_DOT_CKPT_REQ_GAP",1));
  require(gap==1||gap==3,"snapshot one/two real S owner sensitivity");
  const U fee=checkpoint_words*gap+(load?10:8);
  pause_until(store[worker].reserve(now(),fee*C));
  ns_dot_service_cycles+=fee;
  ns_dot_av_snapshot_S_words+=checkpoint_words;
  if(load)++ns_dot_av_restores;else ++ns_dot_av_saves;
 };
 for(int batch=0;batch<o.batches;++batch){
  if(av_wave){
   // Each DDR line feeds both adjacent N8 column blocks, keeping its
   // natural 4-word stride in S. This needs an explicit B-stride4 provider.
   // Checkpoint exact unrounded S80, never split-K RNE. Keep at most one
   // arithmetic owner; released owner state lives in existing S.
   const size_t step=2*size_t(wave_pairs);
   for(size_t first=0;first<columns.size();first+=step){
    const size_t last=std::min(first+step,columns.size());
    require((last-first)%2==0,"native AV paired output ownership");
    std::map<std::pair<int,int>,int> spilled;
    for(int kk=0;kk<o.k;kk+=128){
     stage_A(batch,0,o.rows,kk);
     for(size_t i=first;i<last;i+=2){
      const int col=columns[i];
      require(col%16==0&&columns[i+1]==col+8,"native AV physical 64B pair alignment");
      for(int k=0;k<128;++k){
       stage(b.base+(U(batch)*o.k*o.cols+U(kk+k)*o.cols+col)*4,64,detail::DYNAMIC_B);
       ++ns_dot_av_pair_beats;
      }
      flush();
      for(int half=0;half<2;++half)for(int row=0;row<o.rows;row+=cap){
       const int cc=col+half*8;
       const auto key=std::make_pair(row,cc);
       if(kk==0){require(!spilled.count(key),"duplicate AV owner");begin_owner();}
       else{require(spilled.at(key)==kk,"AV restore must match owner and next K");checkpoint(true);spilled.erase(key);}
       run_chunk(kk);
       if(kk+128<o.k){checkpoint(false);spilled[key]=kk+128;}
       else export_owner(batch,row,cc);
      }
     }
    }
    require(spilled.empty(),"AV spilled owner leak");
   }
  }else if(reuse_B){
   // Each query group uses the same B for this N8. Two sequential owners
   // do not mean two arithmetic contexts. All A fits in this phase S.
   stage_A(batch,0,o.rows,0);flush();
   for(int col:columns){
    stage_B(batch,col,0);flush();
    for(int row=0;row<o.rows;row+=cap){run_owner(batch,row,col,true,true);if(row)++ns_dot_qk_reuse;}
   }
  }else for(int row=0;row<o.rows;row+=cap){
   if(reuse){for(int kk=0;kk<o.k;kk+=128)stage_A(batch,row,cap,kk);flush();}
   for(int col:columns)run_owner(batch,row,col,reuse!=0,false);
  }
 }
 require(pending.empty(),"native S32 raw owner leak");
 stats.service+=now()-started;stats.elapsed+=now()-started;done.notify(SC_ZERO_TIME);
}
