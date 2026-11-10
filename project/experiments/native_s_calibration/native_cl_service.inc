 // Product128 M framing, isolated from the frozen historical CL worker.
 // The raw/RF arithmetic is unchanged. This model uses102172 EOP offsets;
 // root's complete scope/MC/metadata framing is still an explicit gap.
 void ns_cl_wave_worker(const std::vector<CLJob>& jobs,int worker){
  auto& b=*cl_buffers[worker];++cl_wave_count;
  require(b.ready.num_available()==0,"product CL ready queue leak");
  for(bool v:b.live)require(!v,"product CL W bank leak");
  sx_local_use_plan[worker].clear();
  for(const auto& j:jobs)if(!j.down)++sx_local_use_plan[worker][j.kk];
  U results=0;sc_event terminal;
  std::vector<sc_process_handle> children;
  auto keep=[&](sc_process_handle child){
   children.erase(std::remove_if(children.begin(),children.end(),[](const sc_process_handle& p){return p.terminated();}),children.end());
   children.push_back(child);
  };
  auto producer=sc_spawn([&,this]{
   for(const auto& j:jobs){
    ns_buffers[worker]->record_free.wait();++ns_record_live[worker];
    ns_record_peak=std::max(ns_record_peak,ns_record_live[worker]);
    b.free.wait();int bank=0;while(bank<cfg.cl_banks&&b.live[bank])++bank;
    require(bank<cfg.cl_banks,"product CL W overwrite");b.live[bank]=true;++b.generation[bank];
    U live=0;for(bool v:b.live)live+=v;cl_peak_b=std::max(cl_peak_b,live);
    auto* t=new CLTask{j,bank,b.generation[bank],now(),{}, {}};
    if(!j.down)t->sx=sx_local_request(worker,j.kk);
    t->dma.push_back(mem.submit(worker,cl_packed_address(j.weight,j.col,j.kk,j.full_k),1088,false,detail::WEIGHT,bank));
    cl_metadata+=16;b.ready.write(t);
   }
   sx_local_close(worker);b.ready.write(nullptr);
  });
  while(true){
   auto* t=b.ready.read();if(!t)break;
   for(auto& d:t->dma)mem.await(d);
   if(!t->job.down)sx_local_await(t->sx,worker);
   ns_buffers[worker]->command_free.wait();++results;
   ns_result_peak=std::max(ns_result_peak,results);require(results<=2,"product CL result ownership");
   ns_scope_ensure(worker,t->job.weight,t->job.col);
   auto key=std::make_pair(t->job.weight,t->job.col);auto& contexts=cl_contexts[worker];
   if(!t->job.down){
    if(!t->job.kk){require(contexts.count(key)==0&&contexts.size()<16,"product CL RF CREATE");cycles(5);contexts[key]=0;}
    require(contexts.at(key)==t->job.kk,"product CL RF K order");
   }else if(!t->job.kk){cycles(5);} // CREATE, LC->EOP4 and next accept+1
   else{
    // RESTORE snapshot is two actual ordinary S128 reads, not part of12raw.
    for(int word=0;word<2;++word){auto reply=ns_S_request(worker,now());pause_until(reply.ack);if(!word)cycles(1);}
    cl_partial_read+=32;cycles(14); //8flit RESTORE LC->terminal13, next accept+1
   }
   cycles(U(nv_int("NS_EXEC_GAP",1))); //+1 candidate preparse versus current realguard+EXEC +5
   const U start=now();pause_until(mem.weight_store[8*worker+t->bank].reserve(start,8*C));cycles(1);
   if(!t->job.down)sx_local_release(t->sx,worker);
   keep(sc_spawn([&,t,this]{cycles(2); // actual INPUT EOP, coreexec+11
    require(b.live[t->bank]&&b.generation[t->bank]==t->generation,"product CL INPUT EOP identity");
    b.live[t->bank]=false;b.free.post();b.released.notify(SC_ZERO_TIME);
   }));
   cycles(3); // core RF result at exec+12
   cycles(U(nv_int("NS_ORDINARY_PIPE_EXTRA",0))); // explicit prospective3stage scale sensitivity
   cycles(t->job.final?4:2); // product RF FINAL4flit/CONTINUE2flit EOP16/14
   ++m_tiles;++m_commands;m_work+=12*C;
   if(!t->job.down)contexts[key]+=128;
   if(t->job.down&&!t->job.final)cycles(7); // nextaccept1 + independentSPILL LC->RF EOP6
   const bool writes=t->job.down||t->job.final;
   if(t->job.down&&!t->job.final)cl_partial_write+=32;
   keep(sc_spawn([&,t,key,writes,this]{
    if(writes&&!t->job.down&&ns_ring_active)ns_ring_claim(t->job.col);
    cycles(2); // RF EOP->guard C_REQUEST; CONTINUE zeroS terminal+2
    if(writes){
     for(int word=0;word<2;++word){auto reply=ns_S_request(worker,now());pause_until(reply.ack);if(!word)cycles(1);}
     cycles(1); // second realACK->terminal
    }
    if(!t->job.down&&t->job.final){
     require(cl_contexts[worker].at(key)==t->job.full_k,"product CL FINAL prefix");cl_contexts[worker].erase(key);
    }
    require(ns_record_live[worker]>0&&results>0,"product CL orphan terminal");
    --ns_record_live[worker];ns_buffers[worker]->record_free.post();--results;
    ns_buffers[worker]->command_free.post();terminal.notify(SC_ZERO_TIME);delete t;
   }));
  }
  while(results)wait(terminal);
  for(auto& c:children)if(!c.terminated())wait(c.terminated_event());
  require(producer.terminated()&&ns_record_live[worker]==0,"product CL undrained ownership");
  for(bool v:b.live)require(!v,"product CL W leak");
 }
