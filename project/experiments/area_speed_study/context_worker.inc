 // Extra accumulator register contexts; all P S data reservations remain 16KiB.
 bool context_target(const Op& o) const {
  if(cfg.contexts<=1||!cfg.stream||cfg.m_mode!=2||o.rows!=1||o.layout!=0)return false;
  const U full_a=U(o.k)*(tensors[o.in[0]].bits/8);
  const U workspace=1024+(cfg.combine?512:0);
  const U minimum_b=2*ceildiv(U(8)*8*cfg.weight_bits/8,cfg.beat)*cfg.beat;
  return full_a+minimum_b+96+workspace>16384;
 }
 void context_matrix_worker(const Op& o,int worker,sc_event& done){
  auto& buffer=*context_buffers[worker];auto& stats=detail::data.p[worker];
  auto& extra=context_detail::data[worker];++extra.enabled_calls;U worker_start=now();
  require(cfg.buffer_count==2,"context candidate requires two B tokens");
  require(cfg.contexts>=2&&cfg.contexts<=16,"context limit");
  require(buffer.ready.num_available()==0,"context FIFO not drained");
  for(const auto& v:buffer.A)require(!v.live&&v.remaining==0,"A bank not drained");
  for(const auto& v:buffer.B)require(!v.live,"B bank not drained");
  std::array<detail::WriteBuffer,8> wb;
  auto flush_one=[&](detail::WriteBuffer& line){if(line.valid){
   mem.transfer(worker,line.base+line.lo,line.bytes,true,detail::DOT_OUTPUT);line.valid=false;
  }};
  auto output=[&](int row,U address,U bytes){
   if(!cfg.combine){mem.transfer(worker,address,bytes,true,detail::DOT_OUTPUT);return;}
   while(bytes){auto& line=wb[row];U base=address/64*64,offset=address%64,take=std::min<U>(bytes,64-offset);
    require(address<(U(1)<<40),"write combine address width");cycles(cfg.book_cycles);
    if(line.valid&&(line.base!=base||line.lo+line.bytes!=offset))flush_one(line);
    if(!line.valid){line.valid=true;line.base=base;line.lo=offset;line.bytes=0;}
    line.bytes+=take;U live=0;for(const auto& v:wb)if(v.valid)live+=64;
    stats.write_buffer_peak=std::max(stats.write_buffer_peak,live);
    if(line.lo==0&&line.bytes==64)flush_one(line);
    address+=take;bytes-=take;
   }
  };
  auto wait_free=[&]{U before=now();buffer.free.wait();stats.producer_free_wait+=now()-before;};
  const auto selected=detail::columns(o.cols,worker,cfg.mcount,cfg.paircols);
  auto producer=sc_spawn([&,this]{U sequence=0,A_sequence=0,group_sequence=0;
   for(int batch=0;batch<o.batches;++batch){
    const auto& a=tensors[o.in[0]];const auto& b=tensors[o.in[1]];const int bbits=cfg.weight_bits;
    const U workspace=1024+(cfg.combine?512:0);
    int cap=(16384-U(8)*12-workspace)/(2*((a.bits/8)+8*(bbits/8)));
    int limit=std::min(cfg.k,std::max(8,(cap/8)*8));
    const U full_a=U(o.k)*(a.bits/8);
    require(full_a+2*ceildiv(U(8)*8*bbits/8,cfg.beat)*cfg.beat+96+workspace>16384,
            "full A can reside; use original worker");
    int cache_k=0;U prefix_bytes=0;
    if(cfg.prefix_cache&&!selected.empty()){
     const U fixed=2*(ceildiv(U(limit)*a.bits/8,cfg.beat)*cfg.beat+
                     ceildiv(U(8)*limit*bbits/8,cfg.beat)*cfg.beat)+ceildiv(U(8)*12,64)*64+workspace;
     if(fixed<16384){U available=(16384-fixed)/(a.bits/8);
      cache_k=std::min(o.k,int(available/limit)*limit);prefix_bytes=U(cache_k)*(a.bits/8);
     }
    }
    if(cfg.resident){for(int j=0;j<2;++j)wait_free();for(int j=0;j<2;++j)buffer.free.post();}
    if(prefix_bytes){
     mem.transfer(worker,a.base+U(batch)*o.k*(a.bits/8),prefix_bytes,false,detail::A);
     stats.prefix_loaded+=prefix_bytes;stats.prefix_saved+=prefix_bytes*(selected.size()-1);
     stats.prefix_peak=std::max(stats.prefix_peak,prefix_bytes);extra.A_loaded_bytes+=prefix_bytes;
    }
    for(size_t start=0;start<selected.size();start+=static_cast<size_t>(cfg.contexts)){
     const int count=static_cast<int>(std::min<size_t>(cfg.contexts,selected.size()-start));
     const U group=++group_sequence;++extra.groups;
     extra.psum_register_bytes_peak=std::max(extra.psum_register_bytes_peak,U(count)*8*12);
     for(int kk=0;kk<o.k;kk+=limit){const int k=std::min(limit,o.k-kk);
      int shared_bank=-1;U shared_generation=0;
      const U abytes=ceildiv(U(k)*a.bits,8);const bool prefix=kk<cache_k;
      if(prefix)require(kk+k<=cache_k,"prefix cache block boundary");
      for(int slot=0;slot<count;++slot){
       wait_free();const int bbank=static_cast<int>(sequence%2);auto& bs=buffer.B[bbank];
       require(!bs.live,"B bank overwritten before output ACK");bs.live=true;++bs.generation;
       U live_b=0;for(const auto& v:buffer.B)live_b+=v.live?1:0;
       require(live_b<=2,"B bank capacity");extra.B_bank_peak=std::max(extra.B_bank_peak,live_b);
       const int col=selected[start+slot],n=std::min(8,o.cols-col);
       const U bbytes=ceildiv(U(n)*k*bbits,8);
       U scratch=2*(ceildiv(abytes,cfg.beat)*cfg.beat+ceildiv(bbytes,cfg.beat)*cfg.beat)+U(n)*12+workspace;
       if(prefix_bytes)scratch=2*(ceildiv(abytes,cfg.beat)*cfg.beat+ceildiv(bbytes,cfg.beat)*cfg.beat)+ceildiv(U(8)*12,64)*64+workspace+prefix_bytes;
       scratch_peak=std::max(scratch_peak,scratch);require(scratch<=16384,"P private S overflow");
       if(prefix_bytes)cycles(cfg.book_cycles); // Same per-Mtile lookup charge as the reference.
       int abank=shared_bank;U ageneration=shared_generation;
       if(!cfg.reuse_A||slot==0){
        abank=cfg.reuse_A?static_cast<int>(A_sequence++%2):bbank;auto& as=buffer.A[abank];
        while(as.live)wait(as.released);
        require(as.remaining==0&&as.pending.empty(),"A bank live references");
        as.live=true;++as.generation;as.remaining=cfg.reuse_A?static_cast<U>(count):1;
        as.group=group;as.batch=batch;as.kk=kk;as.bytes=abytes;as.prefix=prefix;ageneration=as.generation;
        ++extra.A_groups;U live_a=0;for(const auto& v:buffer.A)live_a+=v.live?1:0;
        require(live_a<=2,"A bank capacity");extra.A_bank_peak=std::max(extra.A_bank_peak,live_a);
        if(!prefix){
         const U address=a.base+(U(batch)*o.k+kk)*(a.bits/8);
         if(cfg.queued)as.pending.push_back(mem.submit(worker,address,abytes,false,detail::A));
         else mem.transfer(worker,address,abytes,false,detail::A);
         extra.A_loaded_bytes+=abytes;
         if(cfg.reuse_A)extra.A_saved_bytes+=abytes*U(count-1);
        }
        if(cfg.reuse_A){shared_bank=abank;shared_generation=ageneration;}
       }
       require(abank>=0&&abank<2,"A bank tag");
       std::vector<std::shared_ptr<Burst>> pending;
       const U address=b.base+(U(batch)*o.cols*o.k+U(col)*o.k+U(kk)*n)*bbits/8;
       if(cfg.queued)pending.push_back(mem.submit(worker,address,bbytes,false,detail::WEIGHT));
       else mem.transfer(worker,address,bbytes,false,detail::WEIGHT);
       auto* task=new ContextTile;
       task->tile=Tile{1,n,k,batch,0,col,kk,bbank,kk+k==o.k,abytes,bbytes,std::move(pending)};
       task->slot=slot;task->abank=abank;task->bbank=bbank;
       task->ageneration=ageneration;task->bgeneration=bs.generation;task->group=group;
       ++sequence;buffer.ready.write(task);
      }
     }
    }
   }
   buffer.ready.write(nullptr);
  });
  std::array<int,16> next_k{},context_col{},context_batch{};
  std::array<U,16> context_group{};std::array<bool,16> active{};
  while(true){U before=now();ContextTile* task=buffer.ready.read();stats.ready+=now()-before;if(!task)break;
   Tile* p=&task->tile;require(task->slot>=0&&task->slot<cfg.contexts,"context slot range");
   auto& as=buffer.A[task->abank];auto& bs=buffer.B[task->bbank];
   require(as.live&&as.remaining>0&&as.generation==task->ageneration,"A bank generation mismatch");
   require(as.group==task->group&&as.batch==p->batch&&as.kk==p->ki&&as.bytes==p->abytes,"A identity mismatch");
   require(bs.live&&bs.generation==task->bgeneration,"B bank generation mismatch");
   before=now();for(auto& request:as.pending)mem.await(request);for(auto& request:p->pending)mem.await(request);
   stats.ack+=now()-before;
   const int slot=task->slot;
   if(p->ki==0){require(!active[slot],"context reinitialized before final output ACK");
    active[slot]=true;next_k[slot]=0;context_col[slot]=p->col;context_batch[slot]=p->batch;context_group[slot]=task->group;
   }
   require(active[slot]&&next_k[slot]==p->ki&&context_col[slot]==p->col&&
           context_batch[slot]==p->batch&&context_group[slot]==task->group,"context K order or tag mismatch");
   before=now();++extra.context_switches;extra.switch_subcycles+=U(cfg.context_switch_cycles)*C;
   cycles(cfg.context_switch_cycles);
   // Native S32/96-bit full-K arithmetic, streaming work and local S reads are
   // identical to the original worker. Selection is additional service above.
   U start=now(),send=store[worker].reserve(start,ceildiv(p->abytes+p->bbytes,cfg.swidth)*cfg.slat*C);
   U adapt=std::max(ceildiv(p->abytes,32),ceildiv(p->bbytes,64));
   U compute=U(p->r)*ceildiv(p->k,8);
   U tail=4+(p->ki==0?14:0)+(p->last?8+ceildiv(U(p->r)*p->n,4)*2:0);
   adapter_work+=adapt*C;m_work+=(compute+tail)*C;++m_tiles;++m_commands;
   pause_until(std::max(send,start+std::max(adapt,compute)*C)+tail*C);
   next_k[slot]+=p->k;require(next_k[slot]<=o.k,"context K overflow");
   stats.service+=now()-before;++stats.tiles;before=now();
   if(p->last){require(next_k[slot]==o.k,"context incomplete K at final RNE");
    U bytes=U(p->r)*p->n*4;sio(worker,bytes);
    for(int row=0;row<p->r;++row)output(row,tensors[o.out].base+((U(p->batch)*o.rows+p->row+row)*o.cols+p->col)*4,U(p->n)*4);
    active[slot]=false;++extra.completed_contexts;
   }
   stats.output+=now()-before;
   // The B token and A reference include the output path (including each real
   // write ACK); a write-combine entry owns bytes accepted for later flush.
   require(as.live&&as.generation==task->ageneration&&as.remaining>0,"A release tag mismatch");
   if(--as.remaining==0){as.live=false;as.pending.clear();as.released.notify(SC_ZERO_TIME);}
   require(bs.live&&bs.generation==task->bgeneration,"B release tag mismatch");
   bs.live=false;buffer.free.post();delete task;
  }
  U before=now();for(auto& line:wb)flush_one(line);stats.output+=now()-before;
  stats.elapsed+=now()-worker_start;
  for(bool v:active)require(!v,"unfinished accumulator context");
  for(const auto& v:buffer.A)require(!v.live&&v.remaining==0,"unfinished A bank users");
  for(const auto& v:buffer.B)require(!v.live,"unfinished B bank users");
  require(producer.terminated(),"context producer unfinished");done.notify(SC_ZERO_TIME);
 }
