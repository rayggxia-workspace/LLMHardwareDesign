 // Issue250 executable service model, NOT qualified 3P shared-pool RTL.
 // X only: Mid and down A retain the historical finite 256B staging path.
 struct SXRequest { int worker,kk,local_slot=-1;U epoch,issued=0,arrived=0,consumed=0,accept_at=0,local_generation=0,planned_uses=1,issued_uses=1,completed_uses=0;bool active=false,closed=false;sc_event arrival; };
 struct SXLocalBuffer {sc_semaphore free;std::array<bool,2> live{};std::array<U,2> generation{};U peak=0;SXLocalBuffer():free(nv_int("SX_A_SLOTS",2)){}};
 std::array<SXLocalBuffer,3> sx_local_buffers;
 std::array<std::deque<std::shared_ptr<SXRequest>>,3> sx_local_pending;
 std::array<std::shared_ptr<SXRequest>,3> sx_local_last;
 std::array<std::map<int,U>,3> sx_local_use_plan;
 U sx_local_reuse=0,sx_local_loads=0,sx_local_prepare_cycles=0;
 std::array<bool,16> sx_x_valid{};sc_event sx_x_valid_event;
 std::vector<sc_process_handle> sx_copy_workers;U sx_copy_source_B=0,sx_copy_dest_B=0;
 struct SXPort { U reserved=0,live=0,peak=0,issued=0,arrived=0,consumed=0; };
 std::array<SXPort,3> sx_ports;
 std::array<std::deque<std::shared_ptr<SXRequest>>,3> sx_pending;
 Calendar sx_lc_prepare[3];U sx_retired_at[3]={0,0,0};
 sc_event sx_activity;
 bool sx_sealed=false;U sx_epoch=0,sx_objects=0,sx_fill_B=0,sx_read_B=0,sx_local_reads=0,sx_wait=0,sx_stalls=0;
 U sx_descriptor_count=0,sx_adapter_cycles=0;int sx_owner=0;
 int sx_mode()const{return nv_int("SX_MODE",0);} // 0 reg,1 pool,2 S serial,3 S2slot prefetch,4 tilelease
 int sx_desc_cycles()const{return nv_int("SX_DESC_CYCLES",1);}
 int sx_slots()const{return nv_int("SX_SLOTS",2);}
 int sx_retire_cycles()const{return nv_int("SX_RETIRE_CYCLES",1);}
 int sx_latency()const{return nv_int("SX_LATENCY",2);}
 int sx_local_width()const{return nv_int("SX_LOCAL_WIDTH",16);}
 int sx_local_latency()const{return nv_int("SX_LOCAL_LATENCY",1);}
 int sx_phase_cycles()const{return nv_int("SX_PHASE_CYCLES",2);}
 int sx_a_slots()const{return nv_int("SX_A_SLOTS",2);}
 bool sx_early()const{return nv_int("SX_EARLY",0)!=0;}
 int sx_copy_latency()const{return nv_int("SX_COPY_LATENCY",1);}
 void sx_early_begin(){
  sx_x_valid.fill(false);sx_copy_workers.clear();
  for(int worker=0;worker<3;++worker){sx_copy_workers.push_back(sc_spawn([this,worker]{
   // Exactly one16B holding register/FSM per unicast destination. Each read
   // waits its source response and destination ACK before another is issued.
   // No broadcast, hidden full-X copy or unbounded return queue.
   cycles(sx_desc_cycles()); // finite copy descriptor acceptance
   for(int chunk=0;chunk<16;++chunk){
    while(!sx_x_valid[chunk])wait(sx_x_valid_event);
    for(int word=0;word<16;++word){
     pause_until(store[3].reserve(now(),U(1+sx_copy_latency())*C));sx_copy_source_B+=16;
     pause_until(cl_links[worker].reserve(now(),C));cl_link_bytes+=16;
     U written=store[worker].reserve(now(),C);pause_until(written+U(sx_copy_latency())*C);sx_copy_dest_B+=16;
    }
   }
  }));}
 }
 void sx_early_valid(U chunk){require(chunk<16&&!sx_x_valid[chunk],"X chunk write ACK/order");sx_x_valid[chunk]=true;sx_x_valid_event.notify(SC_ZERO_TIME);}
 void sx_early_join(){for(auto& w:sx_copy_workers)if(!w.terminated())wait(w.terminated_event());}
 U sx_s_duration(U bytes)const{return (ceildiv(bytes,U(16))+sx_local_latency())*C;}
 void sx_local_begin(){
  ++sx_epoch;
  for(int p=0;p<3;++p){require(sx_local_pending[p].empty(),"local X BEGIN before queue drain");for(bool live:sx_local_buffers[p].live)require(!live,"local X BEGIN before lease drain");}
 }
 void sx_local_free(const std::shared_ptr<SXRequest>& r,int worker){
  auto& b=sx_local_buffers[worker];require(r->active&&r->local_slot>=0&&b.live[r->local_slot]&&b.generation[r->local_slot]==r->local_generation,"local A free identity");
  b.live[r->local_slot]=false;b.free.post();
 }
 void sx_local_close(int worker){
  auto r=sx_local_last[worker];if(!r)return;
  require(r->issued_uses==r->planned_uses,"tile CLOSE before planned consumers issued");
  r->closed=true;if(r->completed_uses==r->planned_uses)sx_local_free(r,worker);
  sx_local_last[worker].reset();
 }
 std::shared_ptr<SXRequest> sx_local_request(int worker,int kk){
  require(kk>=0&&kk+128<=2048&&kk%128==0,"local X address");
  if(sx_mode()==4){
   auto last=sx_local_last[worker];
   if(last&&last->epoch==sx_epoch&&last->kk==kk){
    require(!last->closed&&last->issued_uses<last->planned_uses,"tile reuse plan overrun");
    ++last->issued_uses;++sx_local_reuse;return last;
   }
   sx_local_close(worker);
  }
  require(sx_local_pending[worker].size()<4,"local X pending exceeds W-bank ownership");
  auto r=std::make_shared<SXRequest>();r->worker=worker;r->kk=kk;r->epoch=sx_epoch;
  if(sx_mode()==4){r->planned_uses=sx_local_use_plan[worker].at(kk);sx_local_last[worker]=r;}
  sx_local_pending[worker].push_back(r);sx_activity.notify(SC_ZERO_TIME);return r;
 }
 void sx_local_serve(int worker){
  while(true){
   while(sx_local_pending[worker].empty())wait(sx_activity);
   auto r=sx_local_pending[worker].front();sx_local_pending[worker].pop_front();
   auto& b=sx_local_buffers[worker];b.free.wait();
   ++sx_local_loads;sx_local_prepare_cycles+=sx_desc_cycles();cycles(sx_desc_cycles());
   int slot=0;while(slot<2&&b.live[slot])++slot;require(slot<2,"local A slot overflow");
   b.live[slot]=true;r->local_slot=slot;r->local_generation=++b.generation[slot];
   U live=0;for(bool v:b.live)live+=v;b.peak=std::max(b.peak,live);
   // Real128b source reads; one unified calendar excludes normal S accesses.
   // Explicit normal->feeder->normal phase cost, SRAM response and slot ACK.
   U ready=store[worker].reserve(now(),(ceildiv(U(256),U(sx_local_width()))+sx_local_latency()+sx_phase_cycles())*C);
   pause_until(ready);require(r->epoch==sx_epoch,"stale local X response");
   sx_local_reads+=256;r->active=true;r->arrival.notify(SC_ZERO_TIME);
  }
 }
 void sx_local_serve0(){sx_local_serve(0);}void sx_local_serve1(){sx_local_serve(1);}void sx_local_serve2(){sx_local_serve(2);}
 void sx_local_await(const std::shared_ptr<SXRequest>& r,int worker){
  require(bool(r)&&r->worker==worker&&r->epoch==sx_epoch,"local A JOIN identity");
  while(!r->active)wait(r->arrival);
  const auto& b=sx_local_buffers[worker];require(r->local_slot>=0&&b.live[r->local_slot]&&b.generation[r->local_slot]==r->local_generation,"local A generation");
 }
 void sx_local_release(const std::shared_ptr<SXRequest>& r,int worker){
  sx_local_await(r,worker);
  require(r->completed_uses<r->issued_uses,"duplicate tile consumer completion");++r->completed_uses;
  if(sx_mode()!=4||(r->closed&&r->completed_uses==r->planned_uses))sx_local_free(r,worker);
 }
 void sx_local_fill(int worker){
  // The existing external request interface is128b. Internal wide512 does
  // not grant an external64B/cycle client. Serialize writes + real ACK.
  sio(3,4096);
  pause_until(cl_links[worker].reserve(now(),ceildiv(U(4096),U(16))*C));
  cl_link_bytes+=4096;
  pause_until(store[worker].reserve(now(),(4096/16+sx_local_latency())*C));
 }
 void sx_begin_fill(){
  require(!sx_sealed,"pool BEGIN while SEALED");
  for(const auto& p:sx_ports)require(!p.reserved&&!p.live,"BEGIN before drain");
  ++sx_epoch;++sx_objects;cycles(1); // accepted BEGIN
  // Read normalized X from U's actual S port once; no DDR byte suppression.
  sio(3,4096);
  // Same explicit 16B/cycle inter-group transport as the frozen baseline.
  // The pool's eight1RW banks cannot be read while FILL is active.
  cycles(4096/16+sx_latency()+1);sx_fill_B+=4096;
  cycles(1);sx_sealed=true; // final write ACK + SEAL acceptance
 }
 std::shared_ptr<SXRequest> sx_request(int worker,int kk){
  require(sx_sealed&&worker>=0&&worker<3&&kk>=0&&kk+128<=2048&&kk%128==0,"shared X descriptor");
  require(sx_pending[worker].size()<4,"shared X metadata queue exceeds four weight banks");
  auto r=std::make_shared<SXRequest>();r->worker=worker;r->kk=kk;r->epoch=sx_epoch;
  sx_pending[worker].push_back(r);sx_activity.notify(SC_ZERO_TIME);return r;
 }
 void sx_serve(){
  while(true){
   int selected=-1;U next_accept=~U(0);
   for(int n=0;n<3;++n){int p=(sx_owner+n)%3;
    if(sx_pending[p].empty())continue;
    // Only active+prepared descriptors occupy the declared1/2 control slots.
    // Remaining weight-bank task metadata is not an accepted pool command.
    int prepared=0;
    for(auto r:sx_pending[p]){
     if(prepared++==sx_slots())break;
     if(!r->active){r->active=true;
      r->accept_at=sx_lc_prepare[p].reserve(now(),U(sx_desc_cycles())*C);
      ++sx_descriptor_count;sx_adapter_cycles+=sx_desc_cycles();}
    }
    auto r=sx_pending[p].front();
    // Proposed extended LOAD: one row,16 native128b containers=K128 A256B.
    // Each P prepares its own descriptor independently; those control cycles
    // cannot block unrelated P SRAM grants. Only one active descriptor/P.
    if(r->issued==4||sx_ports[p].reserved==4)continue;
    U accepted=std::max(r->accept_at,sx_retired_at[p]);
    if(accepted>now()){next_accept=std::min(next_accept,accepted);continue;}
    selected=p;break;
   }
   if(selected<0){
    if(next_accept!=~U(0))wait(sc_time::from_value(next_accept-now()),sx_activity);
    else wait(sx_activity);
    continue;
   }
   const int worker=selected;auto request=sx_pending[worker].front();auto& p=sx_ports[worker];
   require(sx_sealed&&request->epoch==sx_epoch,"stale/unsealed X read");
   // Exactly one64B global SRAM grant. K16 bridge pairs two adjacent native
   // S16x8 containers. The tiles16 descriptor is an explicit new RTL contract,
   // not a claim that PR243's tiles<=4 native descriptor already supports it.
   ++p.reserved;++p.issued;p.peak=std::max(p.peak,p.reserved);
   require(p.reserved<=4,"shared X FIFO credit includes in-flight");
   ++request->issued;sx_read_B+=64;
   const U due=now()+U(sx_latency())*C;
   sc_spawn([this,request,worker,due]{pause_until(due);auto& port=sx_ports[worker];
    ++request->arrived;++port.arrived;++port.live;require(port.live<=port.reserved,"unreserved X response");
    request->arrival.notify(SC_ZERO_TIME);
   });
   sx_owner=(worker+1)%3;cycles(1); // global64B/cycle, never per-P64B/cycle
  }
 }
 void sx_consume(const std::shared_ptr<SXRequest>& r,int worker){
  require(bool(r)&&r->worker==worker&&r->epoch==sx_epoch,"X consume identity");
  auto& p=sx_ports[worker];
  for(U beat=0;beat<4;++beat){
   const U before=now();while(r->arrived<=beat)wait(r->arrival);
   sx_wait+=now()-before;sx_stalls+=now()!=before;
   require(p.live&&p.reserved&&r->consumed==beat,"X FIFO underflow/order");
   // One64B FIFO entry supplies two successive32B K16 operand beats.
   // Hold credit until BOTH real32B handshakes; no fifth hidden FIFO entry.
   cycles(2);++r->consumed;--p.live;--p.reserved;++p.consumed;
   sx_activity.notify(SC_ZERO_TIME);
  }
  require(!sx_pending[worker].empty()&&sx_pending[worker].front()==r,"descriptor done order");
  sx_retired_at[worker]=now()+U(sx_retire_cycles())*C;
  sx_pending[worker].pop_front();sx_activity.notify(SC_ZERO_TIME);
 }
 void sx_release(){
  require(sx_sealed,"RELEASE before SEAL");
  for(int p=0;p<3;++p)require(sx_pending[p].empty()&&!sx_ports[p].live&&!sx_ports[p].reserved,"RELEASE before LOAD/done drain");
  for(U retired:sx_retired_at)pause_until(retired);
  cycles(1);sx_sealed=false;
 }
 void sx_check(){
  require(sx_mode()>=0&&sx_mode()<=4,"unknown shared X mode");
  require(sx_slots()==1||sx_slots()==2,"finite prepared control slots");
  require(sx_a_slots()==1||sx_a_slots()==2,"finite A data slots");
  require(!sx_sealed,"live X object at completion");
  for(int p=0;p<3;++p){const auto& s=sx_ports[p];require(sx_pending[p].empty()&&!s.live&&!s.reserved&&s.issued==s.arrived&&s.arrived==s.consumed&&s.peak<=4,"X completion conservation");}
  for(int p=0;p<3;++p){require(sx_local_pending[p].empty()&&!sx_local_last[p],"local X pending/lease leak");for(bool live:sx_local_buffers[p].live)require(!live,"local A slot leak");}
 }
 void sx_emit(){
  std::cout<<",\"shared_x\":{\"mode\":"<<sx_mode()<<",\"objects\":"<<sx_objects
   <<",\"pool_capacity_B\":"<<(sx_mode()==1?32768:0)<<",\"local_LVT\":false,\"new_local_SRAM_B\":0"
   <<",\"global_pool_B_cycle\":64,\"K16_A_B_cycle_per_P\":32,\"FIFO_B_per_P\":256"
   <<",\"fill_B\":"<<sx_fill_B<<",\"read_B\":"<<sx_read_B<<",\"local_S_X_read_B\":"<<sx_local_reads
   <<",\"descriptor_count\":"<<sx_descriptor_count<<",\"descriptor_cycles\":"<<sx_desc_cycles()
   <<",\"SRAM_response_cycles\":"<<sx_latency()<<",\"adapter_cycles\":"<<sx_adapter_cycles
   <<",\"descriptor_payload_B\":256,\"descriptor_slots_per_P\":"<<sx_slots()<<",\"active_descriptors_per_P\":1"
   <<",\"LOAD_retire_cycles\":"<<sx_retire_cycles()
   <<",\"local_A_port_B_cycle\":"<<sx_local_width()<<",\"local_write_port_B_cycle\":16"
   <<",\"local_phase_cycles\":"<<sx_phase_cycles()<<",\"local_A_slot_B\":256,\"local_A_slots\":"<<sx_a_slots()
   <<",\"local_tile_reused_M_commands\":"<<sx_local_reuse<<",\"new_A_slot_register_B_per_P\":"<<(sx_mode()>=3?256*sx_a_slots():0)
   <<",\"local_A_loads\":"<<sx_local_loads<<",\"local_A_load_prepare_cycles\":"<<sx_local_prepare_cycles
   <<",\"early_X_copy\":"<<(sx_early()?"true":"false")<<",\"early_copy_holding_B_per_P\":"<<(sx_early()?16:0)
   <<",\"early_copy_source_B\":"<<sx_copy_source_B<<",\"early_copy_dest_B\":"<<sx_copy_dest_B
   <<",\"A_starve_cycles\":"<<double(sx_wait)/C<<",\"A_starve_events\":"<<sx_stalls
   <<",\"packing\":\"B1 row1: pair two consecutiveS16x8 containers into same-rowK16; proposed tag bridge\""
   <<",\"RTL_qualified\":false,\"physical_qualified\":false,\"ports\":[";
  for(int worker=0;worker<3;++worker){const auto& p=sx_ports[worker];if(worker)std::cout<<",";
   std::cout<<"{\"P\":"<<worker<<",\"peak_reserved_B\":"<<p.peak*64<<",\"issued\":"<<p.issued<<",\"arrived\":"<<p.arrived<<",\"consumed\":"<<p.consumed<<"}";}
  std::cout<<"]}";
 }
