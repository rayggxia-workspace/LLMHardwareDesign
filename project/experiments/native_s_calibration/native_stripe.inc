 // Candidate loop interchange: keep all normalized MidA16 distributed in the
 // existing three private S memories; no additional SRAM or free broadcast.
 struct NSStripe {std::array<bool,3> requested{},loaded{};bool copied=false;int leader=0;sc_event change;};
 std::map<std::pair<int,int>,std::shared_ptr<NSStripe>> ns_stripes;
 std::unique_ptr<sc_semaphore> ns_copy_lock;
 U ns_stripe_copy_B=0,ns_stripe_S_read_B=0,ns_stripe_S_write_B=0;
 U ns_stripe_sequence=0;sc_event ns_stripe_advance;
 std::unique_ptr<sc_fifo<int>> ns_G_jobs;
 std::array<int,32> ns_ring_owner;bool ns_ring_active=false;U ns_ring_peak=0;sc_event ns_ring_released;
 void ns_ring_claim(int col){
  const int group=col/8,slot=group%32;
  while(ns_ring_owner[slot]!=-1&&ns_ring_owner[slot]!=group)wait(ns_ring_released);
  ns_ring_owner[slot]=group;U live=0;for(int owner:ns_ring_owner)live+=owner!=-1;
  ns_ring_peak=std::max(ns_ring_peak,live);require(live<=32,"G gate/up ring capacity");
 }
 void ns_ring_release(int first){
  for(int col=first;col<first+128;col+=8){const int group=col/8,slot=group%32;
   require(ns_ring_owner[slot]==group,"G consumed wrong ring epoch");ns_ring_owner[slot]=-1;
  }
  ns_ring_released.notify(SC_ZERO_TIME);
 }
 void ns_stripe_load(int worker,int wave,int kk){
  const auto key=std::make_pair(wave,kk);auto& entry=ns_stripes[key];
  if(!entry){entry=std::make_shared<NSStripe>();entry->leader=nv_int("NS_EARLY_STRIPE",0)?worker:0;}
  auto r=entry;
  require(!r->requested[worker],"stripe duplicate A copy request");
  r->requested[worker]=true;r->change.notify(SC_ZERO_TIME);
  if(worker==r->leader){
   if(nv_int("NS_EARLY_STRIPE",0)){
    const U ordinal=U(wave)*86+U(kk/128);
    while(ns_stripe_sequence!=ordinal)wait(ns_stripe_advance);
   }else{while(!std::all_of(r->requested.begin(),r->requested.end(),[](bool b){return b;}))wait(r->change);}
   ns_copy_lock->wait();
   const int source=(kk/128)%3;
   ns_copy_words(source,{0,1,2},nv_int("NS_DIR_REG",0)?16:17,true);
   if(nv_int("NS_DIR_REG",0))cycles(U(nv_int("NS_SCALE_META_CYCLES",4))); // real twoflit metadata/ACK candidate, not extra dataword
   r->copied=true;r->change.notify(SC_ZERO_TIME);
  }else{while(!r->copied)wait(r->change);}
  // Same real single-inflight A loader as the calibrated existing candidate.
  cycles(2);
  for(int word=0;word<16;++word){auto reply=ns_S_request(worker,now());pause_until(reply.ack);if(word!=15)cycles(2);}
  cycles(2);
  // Explicit S metadata read plus scale association/accept; root's bridge
  // will replace this sensitivity with its measured object/kk/ACK trace.
  if(!nv_int("NS_DIR_REG",0)){pause_until(store[worker].reserve(now(),C)+C);cycles(2);}
  r->loaded[worker]=true;r->change.notify(SC_ZERO_TIME);
  if(worker==r->leader){
   while(!std::all_of(r->loaded.begin(),r->loaded.end(),[](bool b){return b;}))wait(r->change);
   ns_copy_lock->post();ns_stripes.erase(key);++ns_stripe_sequence;ns_stripe_advance.notify(SC_ZERO_TIME);
  }
 }
 void ns_G_consume(int mid_first,bool spill,const Op& down){
  pause_until(store[0].reserve(now(),108*C));cl_G_values+=128;cl_G_cycles+=68;
  if(ns_ring_active)ns_ring_release(mid_first); // actual G input consumed, conservative finalACK boundary
  if(nv_int("NS_QUANT",0)){ns_quantize(0,nv_int("NS_G_KNOWN_SHIFT",1)!=0);}
  else{sio(0,768);cycles(66);}
  if(spill){
   sio(0,16);cycles(2);
   for(int p=0;p<3;++p)cl_link(p,256,0,true);
   std::vector<CLJob> consume[3];
   for(int col=0;col<2048;col+=8)
    consume[(col/8)%3].push_back(CLJob{down.in[1],col,mid_first,11008,true,mid_first+128==11008});
   cl_wave(consume);
  }else{
   const int owner=(mid_first/128)%3;
   if(nv_int("NS_PRODUCT",0))ns_copy_words(0,{owner},16);
   else{sio(0,256);pause_until(cl_links[owner].reserve(now(),16*C));sio(owner,256);cl_link_bytes+=256;}
   if(!nv_int("NS_DIR_REG",0))sio(owner,16);
   cycles(2); // source directory publish after dataACK; metadata profile remains conditional
  }
 }
 void ns_ffn_striped(size_t i){
  const Op gate=ops[i],up=ops[i+1],down=ops[i+4];++cl_ffns;cl_active=true;
  require(ns_stripes.empty(),"prior FFN stripe still live");ns_stripe_sequence=0;
  while(cache.size()>128)remove_line(cache.begin());
  if(sx_early())sx_early_begin();
  for(U off=0;off<2048;off+=128){
   if(nv_int("NS_QUANT",0)){touch(gate.in[0],off*4,512,false);ns_quantize(3,false);}
   else{read_range(gate.in[0],off*4,512);cycles(66);sio(3,256);}
   if(sx_early())sx_early_valid(off/128);
  }
  if(last_use[gate.in[0]]<=int(i+1))discard_range(gate.in[0],0,size(gate.in[0]));
  if(sx_early())sx_early_join();else for(int p=0;p<3;++p)sx_local_fill(p);
  sx_local_begin();
  const bool spill=nv_int("NS_SPILL",0)!=0;
  ns_ring_active=nv_int("NS_G_OVERLAP",0)!=0;
  require(!ns_ring_active||(!spill&&nv_int("NS_PRODUCT",0)),"G overlap requires product stripe provider");
  ns_ring_owner.fill(-1);require(ns_G_jobs->num_available()==0,"prior G jobs live");
  sc_process_handle G_worker;
  if(ns_ring_active)G_worker=sc_spawn([&,this]{while(true){int first=ns_G_jobs->read();if(first<0)break;ns_G_consume(first,false,down);}});
  const int projection_columns=nv_int("NS_PROJECT_COLS",128);
  require(projection_columns==128||projection_columns==192,"native projection tile");
  //29/29/28 normalized Mid tiles; X remains live during the entire phase1.
  //Per-P conservative phase1: Mid + X + gate/up1KiB + G/Mid512 +
  //quant256 + control512 + scale-directory32. W/RF/A registers are separate.
  const U directory_S=nv_int("NS_DIR_REG",0)?0:512;
  const U phase1_peak=(spill?86*32:29*256)+4096+2048+512+256+512+directory_S;
  const U phase2_peak=29*256+86*32+(nv_int("NS_DIR_REG",0)?256:272)+512+directory_S;
  cl_peak_s=std::max(cl_peak_s,std::max(phase1_peak,phase2_peak));
  require(phase1_peak<=16384&&phase2_peak<=16384,"stripe private S lifetime capacity");
  int pending=0,mid_first=0;
  for(int first=0;first<11008;first+=projection_columns){
   const int chunk=std::min(projection_columns,11008-first);
   std::vector<CLJob> project[3];
   for(int k=0;k<2048;k+=128)for(int w:{gate.in[1],up.in[1]})for(int col=first;col<first+chunk;col+=8)
    project[(col/8)%3].push_back(CLJob{w,col,k,2048,false,k+128==2048});
   cl_wave(project);
   for(int p=0;p<3;++p){
    require(cl_contexts[p].empty(),"stripe projection RF not committed");
    U columns=0;for(int col=first;col<first+chunk;col+=8)if((col/8)%3==p)columns+=8;
    const U bytes=columns*8;
    if(nv_int("NS_PRODUCT",0)){
     // P0 FINAL has already written its canonical ring. Each remote plane
     // uses the real single-source held16B route; strided addresses remain
     // a separately qualified frontend, not a free shared global array.
     if(p){ns_copy_words(p,{0},int(bytes/32));ns_copy_words(p,{0},int(bytes/32));}
    }else{sio(p,bytes);
     if(p){pause_until(cl_links[p].reserve(now(),ceildiv(bytes,16)*C));sio(0,bytes);cl_link_bytes+=bytes;}}
   }
   pending+=chunk;
   require(pending<=256,"gate/up carry exceeds finite2KiB window");
   while(pending>=128){
    if(ns_ring_active)ns_G_jobs->write(mid_first);else ns_G_consume(mid_first,spill,down);
    pending-=128;mid_first+=128;
   }
  }
  require(pending==0&&mid_first==11008,"gate/up carry or normalization group lost");
  if(ns_ring_active){ns_G_jobs->write(-1);if(!G_worker.terminated())wait(G_worker.terminated_event());
   for(int owner:ns_ring_owner){require(owner==-1,"unconsumed G ring epoch");}
   ns_ring_active=false;
  }
  // X, gate/up and G scratch may now be released. The normalized MidA16
  // remains22,016B across3 S; eachP has <=7,424B plus32B directory.
  if(!spill){
   std::vector<sc_process_handle> workers;
   for(int p=0;p<3;++p)workers.push_back(sc_spawn([&,p,this]{sc_event unused;ns_matrix_worker(down,p,unused,true);}));
   for(auto& w:workers)if(!w.terminated())wait(w.terminated_event());
  }
  require(ns_stripes.empty(),"stripe pending transport or source hold");
  for(int col=0;col<2048;col+=8){int p=(col/8)%3;sio(p,32);
   pause_until(cl_links[p].reserve(now(),2*C));write_range(down.out,U(col)*4,32);cl_link_bytes+=32;
  }
  matrix_backed.insert(down.out);cl_active=false;
 }
