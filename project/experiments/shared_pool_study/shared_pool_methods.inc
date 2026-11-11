// Included inside Study; original tile shapes, contexts and scratch budgets stay.
 void pool_begin(const Op& o){
  auto& p=shared_pool::pool;
  if(!p.capacity||!cfg.stream||cfg.m_mode!=2||o.layout!=0||o.batches!=1||o.rows<1||o.rows>8||tensors[o.in[0]].bits!=32)return;
  require(cfg.mcount==2,"shared pool model requires two P workers");
  const auto& a=tensors[o.in[0]];
  if(!p.begin(a.base,o.rows,o.k,a.bits/8,cfg.k))return;
  std::deque<std::shared_ptr<Burst>> pending;U sequence=0;
  for(U row=0;row<p.rows;++row)for(U offset=0;offset<p.prefix_k*p.element_bytes;offset+=1024){
   const U bytes=std::min<U>(1024,p.prefix_k*p.element_bytes-offset);
   // Two finite fill descriptors, at most one selected round-robin per DDR
   // channel. Existing channel credits, beat service and final ACK apply.
   if(pending.size()==2){mem.await(pending.front());pending.pop_front();}
   pending.push_back(mem.submit(int(sequence++%2),p.base+row*p.K*p.element_bytes+offset,bytes,false,detail::A,true,row*p.stride+offset));
   ++p.fill_descriptors;p.fill_payload_bytes+=bytes;p.fill_peak_descriptors=std::max<U>(p.fill_peak_descriptors,pending.size());
   p.fill_DDR_bus_bytes+=ceildiv((p.base+row*p.K*p.element_bytes+offset)%cfg.beat+bytes,cfg.beat)*cfg.beat;
  }
  for(auto& request:pending){mem.await(request);}
  p.filled();
 }
 U pool_local_bytes(U address,U bytes)const{return bytes-shared_pool::pool.covered(address,bytes);}
 void a_load(int worker,U address,U bytes,std::vector<std::shared_ptr<Burst>>* pending){
  auto& p=shared_pool::pool;
  if(!p.active){if(pending)pending->push_back(mem.submit(worker,address,bytes,false,detail::A));else mem.transfer(worker,address,bytes,false,detail::A);return;}
  const auto ranges=p.remaining(address,bytes);U actual=0,bus=0;
  for(const auto& part:ranges){actual+=part.second;bus+=ceildiv(part.first%cfg.beat+part.second,cfg.beat)*cfg.beat;
   if(pending)pending->push_back(mem.submit(worker,part.first,part.second,false,detail::A));else mem.transfer(worker,part.first,part.second,false,detail::A);}
  const U old_bus=ceildiv(address%cfg.beat+bytes,cfg.beat)*cfg.beat;
  require(bus<=old_bus,"A split increased bus service");auto& w=p.workers[worker];
  w.avoided_DDR_bytes+=bytes-actual;w.avoided_DDR_bus_bytes+=old_bus-bus;
  w.avoided_DDR_descriptors+=1-static_cast<long long>(ranges.size());
  w.avoided_local_write+=(old_bus-bus)/cfg.beat*s_port_duration(cfg,worker,cfg.beat);
 }
 U pool_tile_bytes(const Op& o,const Tile* t)const{
  if(!shared_pool::pool.active)return 0;
  U hit=0;
  const auto& a=tensors[o.in[0]];
  for(int row=0;row<t->r;++row)hit+=shared_pool::pool.covered(a.base+((U(t->batch)*o.rows+t->row+row)*o.k+t->ki)*(a.bits/8),U(t->k)*(a.bits/8));
  return hit;
 }
 U pool_input_service(const Op& o,int worker,const Tile* t){
  const U hit=pool_tile_bytes(o,t),bytes=t->abytes+t->bbytes-hit;
  if(shared_pool::pool.active){auto& w=shared_pool::pool.workers[worker];
   w.local_A_bytes+=t->abytes-hit;w.bypassed_local_A_bytes+=hit;
   w.local_read_saved+=s_port_duration(cfg,worker,t->abytes+t->bbytes)-s_port_duration(cfg,worker,bytes);}
  return store[worker].reserve(now(),s_port_duration(cfg,worker,bytes));
 }
 U pool_feed(const Op& o,int worker,const Tile* t,U local_ready_at){
  if(!shared_pool::pool.active)return now();
  const U hit=shared_pool::pool.feed(worker,t->row,t->r,t->ki,t->k,
    (U(t->col)<<40)|(U(t->row)<<32)|U(t->ki),local_ready_at);
  require(hit==pool_tile_bytes(o,t),"shared A consumption differs from bypass");return now();
 }
