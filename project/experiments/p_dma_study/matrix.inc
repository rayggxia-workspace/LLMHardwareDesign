 // Included inside Study. Observe preserves the frozen worker's waits/order.
 void matrix_worker(const Op& o,int worker,sc_event& done){
  auto& buffer=*buffers[worker];auto& stats=detail::data.p[worker];U worker_start=now();
  std::array<detail::WriteBuffer,8> wb;
  auto flush_one=[&](detail::WriteBuffer& line){if(line.valid){
   mem.transfer(worker,line.base+line.lo,line.bytes,true,detail::DOT_OUTPUT);line.valid=false;
  }};
  auto output=[&](int row,U address,U bytes){
   if(!cfg.combine){mem.transfer(worker,address,bytes,true,detail::DOT_OUTPUT);return;}
   while(bytes){auto& line=wb[row];U base=address/64*64,offset=address%64,take=std::min<U>(bytes,64-offset);
    require(address<(U(1)<<40),"write combine address width");
    cycles(cfg.book_cycles);
    if(line.valid&&(line.base!=base||line.lo+line.bytes!=offset))flush_one(line);
    if(!line.valid){line.valid=true;line.base=base;line.lo=offset;line.bytes=0;}
    line.bytes+=take;U live=0;for(const auto& v:wb)if(v.valid)live+=64;
    stats.write_buffer_peak=std::max(stats.write_buffer_peak,live);
    if(line.lo==0&&line.bytes==64)flush_one(line);
    address+=take;bytes-=take;
   }
  };
  auto wait_free=[&]{U before=now();buffer.free.wait();stats.producer_free_wait+=now()-before;};
  const auto selected_columns=detail::columns(o.cols,worker,cfg.mcount,cfg.paircols);
  auto producer=sc_spawn([&,this]{int seq=0;
   for(int batch=0;batch<o.batches;++batch)for(int rr=0;rr<o.rows;rr+=8){
    int r=std::min(8,o.rows-rr);
    const auto& a=tensors[o.in[0]];const auto& b=tensors[o.in[1]];int bbits=o.layout==0?cfg.weight_bits:b.bits;
    const U workspace=1024+(cfg.combine?512:0);
    int cap=(16384-U(r)*8*12-workspace)/(2*(r*(a.bits/8)+8*(bbits/8)));
    int limit=std::min(cfg.k,std::max(8,(cap/8)*8));
    const U full_a=U(r)*o.k*(a.bits/8);
    if(cfg.resident&&full_a+U(r)*8*12+workspace<16384){
     int resident_cap=(16384-full_a-U(r)*8*12-workspace)/(2*8*(bbits/8));
     if(resident_cap>=8)limit=std::min(limit,(resident_cap/8)*8);
    }
    bool resident=cfg.resident&&!selected_columns.empty()&&full_a+2*ceildiv(U(8)*limit*bbits/8,cfg.beat)*cfg.beat+U(r)*8*12+workspace<=16384;
    int cache_k=0;U prefix_bytes=0;
    if(cfg.prefix_cache&&!resident&&!selected_columns.empty()){
     U fixed=2*(ceildiv(U(r)*limit*a.bits/8,cfg.beat)*cfg.beat+
                ceildiv(U(8)*limit*bbits/8,cfg.beat)*cfg.beat)+ceildiv(U(r)*8*12,64)*64+workspace;
     if(fixed<16384){U available=(16384-fixed)/(U(r)*(a.bits/8));
      cache_k=std::min(o.k,int(available/limit)*limit);prefix_bytes=U(r)*cache_k*(a.bits/8);
     }
    }
    if(cfg.resident){for(int j=0;j<cfg.buffer_count;++j)wait_free();for(int j=0;j<cfg.buffer_count;++j)buffer.free.post();}
    if(resident){
     mem.transfer(worker,a.base+(U(batch)*o.rows+rr)*o.k*(a.bits/8),full_a,false,detail::A);
     resident_saved+=full_a*(selected_columns.size()-1);
    }else if(prefix_bytes){
     for(int row=0;row<r;++row)mem.transfer(worker,
      a.base+(U(batch)*o.rows+rr+row)*o.k*(a.bits/8),U(cache_k)*(a.bits/8),false,detail::A);
     stats.prefix_loaded+=prefix_bytes;stats.prefix_saved+=prefix_bytes*(selected_columns.size()-1);
     stats.prefix_peak=std::max(stats.prefix_peak,prefix_bytes);
    }
    for(int col:selected_columns){int n=std::min(8,o.cols-col);
    for(int kk=0;kk<o.k;kk+=limit){wait_free();int k=std::min(limit,o.k-kk);
     std::vector<std::shared_ptr<Burst>> pending;
     auto load=[&](U address,U bytes,detail::Flow flow){
      if(cfg.queued)pending.push_back(mem.submit(worker,address,bytes,false,flow));
      else mem.transfer(worker,address,bytes,false,flow);
     };
     U abytes=ceildiv(U(r)*k*a.bits,8),bbytes=ceildiv(U(n)*k*bbits,8);
     U scratch=2*(ceildiv(abytes,cfg.beat)*cfg.beat+ceildiv(bbytes,cfg.beat)*cfg.beat)+U(r)*n*12+workspace;
     if(resident)scratch=full_a+2*ceildiv(bbytes,cfg.beat)*cfg.beat+U(r)*n*12+workspace;
     if(prefix_bytes)scratch=2*(ceildiv(abytes,cfg.beat)*cfg.beat+ceildiv(bbytes,cfg.beat)*cfg.beat)+ceildiv(U(r)*8*12,64)*64+workspace+prefix_bytes;
     scratch_peak=std::max(scratch_peak,scratch);require(scratch<=16384,"P private S overflow");
     if(prefix_bytes)cycles(cfg.book_cycles);
     if(!resident&&kk>=cache_k)for(int row=0;row<r;++row)load(
      a.base+(U(batch)*o.rows+rr+row)*o.k*(a.bits/8)+U(kk)*(a.bits/8),U(k)*(a.bits/8),detail::A);
     else if(!resident)require(kk+k<=cache_k,"prefix cache block boundary");
     if(o.layout==0){
      U addr=b.base+(U(batch)*o.cols*o.k+U(col)*o.k+U(kk)*n)*bbits/8;
      load(addr,bbytes,detail::WEIGHT);
     }else if(o.layout==1){
      for(int c=0;c<n;++c)load(b.base+(U(batch)*o.cols*o.k+U(col+c)*o.k+kk)*(bbits/8),U(k)*(bbits/8),detail::DYNAMIC_B);
     }else{
      for(int row=0;row<k;++row)load(b.base+(U(batch)*o.k*o.cols+U(kk+row)*o.cols+col)*(bbits/8),U(n)*(bbits/8),detail::DYNAMIC_B);
     }
     buffer.ready.write(new Tile{r,n,k,batch,rr,col,kk,seq++%2,kk+k==o.k,abytes,bbytes,std::move(pending)});
    }
   }}buffer.ready.write(nullptr);
  });
  while(true){U before=now();Tile* p=buffer.ready.read();stats.ready+=now()-before;if(!p)break;
   before=now();for(auto& request:p->pending)mem.await(request);stats.ack+=now()-before;
   before=now();
   const int abits=tensors[o.in[0]].bits,bbits=o.layout==0?cfg.weight_bits:tensors[o.in[1]].bits;
   int ac=abits==32?3:1,bc=bbits==32?3:1;
   if(cfg.m_mode==2)ac=bc=1;
   if(cfg.stream){
    U start=now(),send=store[worker].reserve(start,ceildiv(p->abytes+p->bbytes,cfg.swidth)*cfg.slat*C);
    U adapt=std::max(ceildiv(p->abytes,32),ceildiv(p->bbytes,64));
    U compute=U(p->r)*ceildiv(p->k,8);
    U tail=4+(p->ki==0?14:0)+(p->last?8+ceildiv(U(p->r)*p->n,4)*2:0);
    adapter_work+=adapt*C;m_work+=(compute+tail)*C;++m_tiles;++m_commands;
    pause_until(std::max(send,start+std::max(adapt,compute)*C)+tail*C);
   }else{
    sio(worker,p->abytes+p->bbytes);
    U adapt=ceildiv(p->abytes+p->bbytes,16);adapter_work+=adapt*C;cycles(adapt);
    int kt=p->k<=1?1:p->k<=8?8:32;
    int native=m_ticks.count({p->r,kt})?m_ticks.at({p->r,kt}):p->r*((kt+7)/8)*9+14+p->r;
    int issue_groups=((abits==8?1:3)*(bbits==8?1:3));
    if(cfg.m_mode==1)issue_groups=1;
    if(cfg.m_mode==2)native=14+p->r*((p->k+7)/8)+p->r;
    else if(issue_groups!=9)native=14+p->r*((p->k+7)/8)*issue_groups+p->r;
    U ticks=U(ac)*bc*(native+1+ceildiv(U(p->r)*p->k,8)+ceildiv(U(p->r)*p->n,2)*2);
    m_commands+=U(ac)*bc;m_work+=ticks*C;++m_tiles;cycles(ticks);
    U merge=U(ac)*bc*ceildiv(U(p->r)*p->n,4)*3;
    adapter_work+=merge*C;cycles(merge);sio(worker,U(p->r)*p->n*12*2);
   }
   stats.service+=now()-before;++stats.tiles;before=now();
   if(p->last){U bytes=U(p->r)*p->n*4;sio(worker,bytes);
    for(int row=0;row<p->r;++row)output(row,tensors[o.out].base+((U(p->batch)*o.rows+p->row+row)*o.cols+p->col)*4,U(p->n)*4);
   }
   stats.output+=now()-before;buffer.free.post();delete p;
  }
  U before=now();for(auto& line:wb)flush_one(line);stats.output+=now()-before;
  stats.elapsed+=now()-worker_start;
  require(producer.terminated(),"matrix producer unfinished");done.notify(SC_ZERO_TIME);
 }
 void matrix(const Op& o){
  U before=now(),tiles=m_tiles,commands=m_commands;auto previous=detail::flow_totals();
  for(int t:o.in)flush(t);
  std::vector<std::unique_ptr<sc_event>> done;std::vector<sc_process_handle> workers;
  for(int w=0;w<cfg.mcount;++w){done.emplace_back(new sc_event);workers.push_back(sc_spawn([&,w,this]{matrix_worker(o,w,*done[w]);}));}
  for(auto& w:workers)if(!w.terminated())wait(w.terminated_event());
  matrix_backed.insert(o.out);
  std::string key=std::to_string(o.rows)+"x"+std::to_string(o.cols)+"x"+std::to_string(o.k)+"b"+std::to_string(o.batches)+"l"+std::to_string(o.layout);
  auto& sh=detail::data.shapes[key];++sh.calls;sh.wall+=now()-before;sh.tiles+=m_tiles-tiles;sh.commands+=m_commands-commands;
  auto current=detail::flow_totals();for(int f=0;f<detail::FLOWS;++f)detail::accumulate(sh.flows[f],detail::difference(current[f],previous[f]));
 }
