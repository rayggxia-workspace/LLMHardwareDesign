 // Experimental finite FFN protocol. Independent P macros remain independent.
 struct CLJob{int weight,col,kk,full_k;bool down,final;};
 struct CLTask{CLJob job;int bank;U generation,prior;std::vector<std::shared_ptr<Burst>> dma;};
 struct CLBuffer{
  sc_semaphore free;sc_fifo<CLTask*> ready;sc_event released;
  std::array<bool,2> live{};std::array<U,2> generation{};
  CLBuffer():free(2),ready(2){}
 };
 std::vector<std::unique_ptr<CLBuffer>> cl_buffers;
 Calendar cl_links[3];
 std::map<std::pair<int,int>,int> cl_contexts[3];
 U cl_ffns=0,cl_metadata=0,cl_partial_read=0,cl_partial_write=0,cl_link_bytes=0,cl_G_values=0;
 U cl_G_cycles=0,cl_peak_b=0,cl_peak_s=0,cl_wave_count=0;
 bool cl_active=false;
 U cl_packed_address(int weight,int col,int kk,int full_k)const{
  require(col%8==0&&kk%128==0&&full_k%128==0,"packed W8 tile alignment");
  // A deployment image packs 1024 W8 bytes + 16 FP16 scale bytes + 48 pad
  // bytes. A single DMA owns the whole 1088B record in the same finite bank.
  return (U(1)<<42)+U(weight)*(U(1)<<31)+(U(col/8)*(full_k/128)+U(kk/128))*1088;
 }
 U cl_meta_address(const CLJob& j)const{
  return (U(1)<<37)+U(j.weight)*(U(1)<<26)+(U(j.col)*(j.full_k/128)+U(j.kk/128)*8)*2;
 }
 void cl_link(int worker,U bytes,int source=3,bool to_register=false){
  // Explicit unicast with source read, finite link and destination write ACK.
  sio(source,bytes);
  if(source!=worker){pause_until(cl_links[worker].reserve(now(),ceildiv(bytes,16)*C));cl_link_bytes+=bytes;}
  if(to_register){cycles(ceildiv(bytes,32));}else{sio(worker,bytes);}
 }
 void cl_wave_worker(const std::vector<CLJob>& jobs,int worker){
  auto& b=*cl_buffers[worker];++cl_wave_count;
  require(b.ready.num_available()==0&&!b.live[0]&&!b.live[1],"CL wave not drained");
  auto producer=sc_spawn([&,this]{
   for(const auto& j:jobs){
    b.free.wait();int bank=!b.live[0]?0:1;require(!b.live[bank],"CL input overwrite");
    b.live[bank]=true;++b.generation[bank];cl_peak_b=std::max<U>(cl_peak_b,U(b.live[0])+U(b.live[1]));
    auto* t=new CLTask{j,bank,b.generation[bank],now(),{}};
    U address=tensors[j.weight].base+U(j.col)*j.full_k+U(j.kk)*8;
    if(cfg.cl_mode>=4){t->dma.push_back(mem.submit(worker,cl_packed_address(j.weight,j.col,j.kk,j.full_k),1088,false,detail::WEIGHT,bank));}
    else{
     t->dma.push_back(mem.submit(worker,address,1024,false,detail::WEIGHT,bank));
     t->dma.push_back(mem.submit(worker,cl_meta_address(j),16,false,detail::WEIGHT,bank));
    }
    cl_metadata+=16;
    if((j.down||(cfg.cl_mode>=3&&cfg.cl_mode<4))&&j.kk){t->prior=store[worker].reserve(now(),s_port_duration(cfg,worker,128));cl_partial_read+=128;}
    b.ready.write(t);
   }
   b.ready.write(nullptr);
  });
  while(true){
   CLTask* t=b.ready.read();if(!t)break;
   require(b.live[t->bank]&&b.generation[t->bank]==t->generation,"CL generation mismatch");
   for(auto& d:t->dma){mem.await(d);}pause_until(t->prior);
   if(cfg.cl_mode>=4&&!t->job.down){
    auto key=std::make_pair(t->job.weight,t->job.col);auto& contexts=cl_contexts[worker];
    if(!t->job.kk){require(contexts.count(key)==0&&contexts.size()<16,"CL RF context capacity/overwrite");contexts[key]=0;}
    require(contexts.count(key)&&contexts.at(key)==t->job.kk,"CL RF context identity/K order");
    contexts[key]+=128;if(t->job.final){require(contexts[key]==t->job.full_k,"CL RF incomplete final");contexts.erase(key);}
   }
   // A comes from U's finite source window or a declared 256B feeder register.
   if(cfg.cl_mode<3){cl_link(worker,256,t->job.down?0:3);}
   const U start=now();U consumed=mem.weight_store[2*worker+t->bank].reserve(start,8*C);
   consumed=std::max(consumed,start+8*C);pause_until(consumed+3*C);
   ++m_tiles;++m_commands;m_work+=11*C;adapter_work+=2*C;cycles(2);
   if(t->job.final){cycles(3);adapter_work+=3*C;}
   U ack=now();
   if(t->job.down||(cfg.cl_mode>=3&&cfg.cl_mode<4)){
    const U bytes=t->job.final?32:128;
    ack=store[worker].reserve(now(),s_port_duration(cfg,worker,bytes));
    if(!t->job.final){cl_partial_write+=128;}
   }else if(t->job.final){ack=store[worker].reserve(now(),s_port_duration(cfg,worker,32));}
   // Two actual result slots; SRAM write ACK releases ownership, not compute end.
   sc_spawn([&,t,ack,this]{pause_until(ack);require(b.live[t->bank]&&b.generation[t->bank]==t->generation,"CL output ownership");
    b.live[t->bank]=false;b.free.post();b.released.notify(SC_ZERO_TIME);delete t;});
  }
  while(b.live[0]||b.live[1]){wait(b.released);}
  require(producer.terminated(),"CL producer incomplete");
 }
 void cl_wave(const std::vector<CLJob> jobs[3]){
  std::vector<sc_process_handle> workers;
  for(int p=0;p<3;++p){workers.push_back(sc_spawn([&,p,this]{cl_wave_worker(jobs[p],p);}));}
  for(auto& w:workers){if(!w.terminated()){wait(w.terminated_event());}}
 }
 bool cl_ffn_match(size_t i)const{
  if(cfg.cl_mode<2||i+4>=ops.size()||cfg.mcount!=3)return false;
  const auto& a=ops[i];const auto& b=ops[i+1];const auto& g=ops[i+2];const auto& u=ops[i+3];const auto& d=ops[i+4];
  if(a.kind!="Dot"||b.kind!="Dot"||g.kind!="SiLU"||u.kind!="Product"||d.kind!="Dot")return false;
  return a.rows==1&&a.batches==1&&a.k==2048&&a.cols==11008&&a.layout==0&&b.k==a.k&&b.cols==a.cols&&
   b.in[0]==a.in[0]&&g.in[0]==a.out&&u.in[0]==g.out&&u.in[1]==b.out&&d.in[0]==u.out&&
   d.rows==1&&d.batches==1&&d.layout==0&&d.k==11008&&d.cols==2048&&
   last_use[a.out]==int(i+2)&&last_use[b.out]==int(i+3)&&last_use[g.out]==int(i+3)&&last_use[u.out]==int(i+4);
 }
 void cl_ffn(size_t i){
  const Op gate=ops[i],up=ops[i+1],down=ops[i+4];++cl_ffns;cl_active=true;
  // Reserve U: <=8KiB cache + 4KiB normalized X + existing 4KiB workspace.
  while(cache.size()>128){remove_line(cache.begin());}
  for(U off=0;off<2048;off+=128){read_range(gate.in[0],off*4,512);cycles(66);sio(3,256);}
  if(last_use[gate.in[0]]<=int(i+1)){discard_range(gate.in[0],0,size(gate.in[0]));}
  // S128 output state + two padded B/scale slots + double A + gate/up + Mid + control.
  cl_peak_s=std::max<U>(cl_peak_s,11008+2176+512+1024+1024+512);
  require(cl_peak_s<=16384,"CL complete S lifetime reservation");
  for(int first=0;first<11008;first+=128){
   if(cfg.cl_mode>=3){
    // Gate/up partials alias the not-yet-live Mid workspace. X's K tile is
    // broadcast once, then reused across this chunk's output groups.
    for(int k=0;k<2048;k+=128){
     for(int p=0;p<3;++p){cl_link(p,256,3,true);}
     std::vector<CLJob> project[3];
     for(int w:{gate.in[1],up.in[1]})for(int col=first;col<first+128;col+=8){
      project[(col/8)%3].push_back(CLJob{w,col,k,2048,false,k+128==2048});
     }
     cl_wave(project);
    }
   }else{
    std::vector<CLJob> project[3];
    for(int w:{gate.in[1],up.in[1]})for(int col=first;col<first+128;col+=8){
     for(int k=0;k<2048;k+=128){project[(col/8)%3].push_back(CLJob{w,col,k,2048,false,k+128==2048});}
    }
    cl_wave(project);
   }
   // Gather two projections to G beside P0, retaining a finite 128-value tile.
   for(int p=0;p<3;++p){require(cl_contexts[p].empty(),"CL projection contexts not committed");}
   for(int p=0;p<3;++p){
    U columns=0;for(int col=first;col<first+128;col+=8){if((col/8)%3==p)columns+=8;}
    const U bytes=columns*8;sio(p,bytes);
    if(p){pause_until(cl_links[p].reserve(now(),ceildiv(bytes,16)*C));sio(0,bytes);cl_link_bytes+=bytes;}
   }
   // Same P0 S port services G input and full wide output; no free overlap.
   sio(0,2048);cycles(67);cl_G_values+=128;cl_G_cycles+=67;
   // Max/shift, RNE normalization, and a one-tile scale descriptor.
   sio(0,1280);cycles(66);
   if(cfg.cl_mode>=3){for(int p=0;p<3;++p){cl_link(p,256,0,true);}}
   std::vector<CLJob> consume[3];
   for(int col=0;col<2048;col+=8){consume[(col/8)%3].push_back(CLJob{down.in[1],col,first,11008,true,first+128==11008});}
   cl_wave(consume);
  }
  // Final RNE results travel from private P S to the U-visible output window.
  for(int col=0;col<2048;col+=8){int p=(col/8)%3;sio(p,32);
   pause_until(cl_links[p].reserve(now(),2*C));write_range(down.out,U(col)*4,32);cl_link_bytes+=32;
  }
  matrix_backed.insert(down.out);cl_active=false;
 }
