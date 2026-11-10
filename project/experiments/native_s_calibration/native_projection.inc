 // Timing-only static W8A16 scheduling, conditional on registered native APIs.
 // Dynamic S32xS32 QK/AV deliberately stay outside this provider.
 struct NSATile {bool ready=false;int kk=0,remaining=0;U generation=0;sc_event arrived;};
 struct NSTask {int col,kk,bank;U generation;std::shared_ptr<NSATile> A;std::shared_ptr<Burst> W;};
 struct NSBuffer {
  sc_semaphore W_free,A_free,A_loader,command_free,record_free;
  sc_fifo<NSTask*> tasks;
  sc_fifo<std::shared_ptr<NSATile>> A_tasks;
  NSBuffer():W_free(4),A_free(2),A_loader(1),command_free(2),record_free(nv_int("NS_RECORD_CREDITS",6)),tasks(4),A_tasks(2){}
 };
 std::vector<std::unique_ptr<NSBuffer>> ns_buffers;
 void ns_initialize(){for(int p=0;p<cfg.mcount;++p)ns_buffers.emplace_back(new NSBuffer);ns_copy_lock.reset(new sc_semaphore(1));ns_G_jobs.reset(new sc_fifo<int>(2));}
 U ns_static_calls=0,ns_static_tiles=0,ns_A_load_B=0,ns_A_reuse=0;
 U ns_raw_groups=0,ns_RF_groups=0,ns_W_peak=0,ns_A_peak=0,ns_result_peak=0;
 std::array<U,3> ns_cl_results{};sc_event ns_cl_drain[3];
 std::array<U,3> ns_record_live{};U ns_record_peak=0;
 std::array<std::map<std::pair<int,int>,U>,3> ns_scope_cache;
 U ns_scope_clock=0,ns_scope_BEGINs=0,ns_scope_hits=0;
 void ns_scope_ensure(int worker,int weight,int col){
  if(!nv_int("NS_PRODUCT",0))return;
  auto& scopes=ns_scope_cache[worker];const auto key=std::make_pair(weight,col);
  if(scopes.count(key)){++ns_scope_hits;scopes[key]=++ns_scope_clock;return;}
  if(scopes.size()==16){auto victim=std::min_element(scopes.begin(),scopes.end(),[](const auto& a,const auto& b){return a.second<b.second;});scopes.erase(victim);}
  cycles(12); //8flit BEGIN through ACK EOP11, following native accept+1
  scopes[key]=++ns_scope_clock;++ns_scope_BEGINs;
 }
 bool ns_target(const Op& o)const{
  return nv_int("NS_NATIVE",0)>=3&&o.layout==0&&o.rows==1&&o.batches==1&&
      tensors[o.in[0]].bits==16&&o.k%128==0&&o.cols%8==0;
 }
 void ns_matrix_worker(const Op& o,int worker,sc_event& done,bool striped=false){
  ++ns_static_calls;auto& stats=detail::data.p[worker];const U worker_start=now();
  const U full_A=U(o.k)*2;
  require(striped||full_A+4096<=cfg.pbytes,"native full A private-S capacity");
  require(cfg.cl_banks==4,"native four W banks required");
  auto& W_free=ns_buffers[worker]->W_free;auto& A_free=ns_buffers[worker]->A_free;
  auto& A_loader=ns_buffers[worker]->A_loader;auto& command_free=ns_buffers[worker]->command_free;
  auto& tasks=ns_buffers[worker]->tasks;sc_event W_released,all_terminal;
  auto& A_tasks=ns_buffers[worker]->A_tasks;
  require(tasks.num_available()==0&&A_tasks.num_available()==0,"native task queue not drained");
  std::array<bool,4> W_live{};std::array<U,4> W_generation{};
  U live_A=0,live_command=0;
  std::vector<sc_process_handle> children;
  auto keep_child=[&](sc_process_handle child){
   children.erase(std::remove_if(children.begin(),children.end(),[](const sc_process_handle& p){return p.terminated();}),children.end());
   children.push_back(child);
  };
  const auto selected=detail::columns(o.cols,worker,cfg.mcount,striped?false:cfg.paircols);
  U before=now();
  if(!striped&&!selected.empty()&&!sq_A_skip(o,tensors[o.in[0]].base,full_A)){
   mem.transfer(worker,tensors[o.in[0]].base,full_A,false,detail::A);
  }
  stats.ack+=now()-before;
  U ageneration=0;
  const int rf_limit=nv_int("NS_RF_CONTEXTS",16);require(rf_limit==8||rf_limit==16,"native RF choice");
  std::vector<std::pair<size_t,int>> groups;
  for(size_t first=0;first<selected.size();){
   const U remaining=selected.size()-first;
   const int count=int(nv_int("NS_BALANCE",0)?ceildiv(remaining,ceildiv(remaining,U(rf_limit))):std::min<U>(rf_limit,remaining));
   groups.push_back({first,count});first+=size_t(count);
  }
  auto launch_A=[&,this](size_t wave,int kk,int count){
     A_free.wait();++live_A;ns_A_peak=std::max(ns_A_peak,live_A);require(live_A<=2,"native A overflow");
     auto A=std::make_shared<NSATile>();A->kk=kk;A->remaining=count;A->generation=++ageneration;
     keep_child(sc_spawn([&,A,wave,this]{
      A_loader.wait();cycles(2); // accepted command -> registered first request
      if(striped){ns_stripe_load(worker,int(wave),A->kk);}
      else for(int word=0;word<16;++word){
       auto reply=ns_S_request(worker,now());
       pause_until(reply.ack); // actual SRAM request -> response take is two clocks
       if(word!=15)cycles(2); // single-inflight frontend constructs its next request
      }
      if(!striped)cycles(2); // last data -> LOAD terminal capture/take
      A->ready=true;ns_A_load_B+=256;A->arrived.notify(SC_ZERO_TIME);A_loader.post();
     }));
     return A;
  };
  sc_process_handle A_producer;
  if(nv_int("NS_A_PREFETCH",0))A_producer=sc_spawn([&,this]{
   for(size_t wave=0;wave<groups.size();++wave)for(int kk=0;kk<o.k;kk+=128)
    A_tasks.write(launch_A(wave,kk,groups[wave].second));
   A_tasks.write({});
  });
  auto producer=sc_spawn([&,this]{
   for(size_t wave=0;wave<groups.size();++wave){
    const size_t first=groups[wave].first;const int count=groups[wave].second;
    for(int kk=0;kk<o.k;kk+=128){
     auto A=nv_int("NS_A_PREFETCH",0)?A_tasks.read():launch_A(wave,kk,count);
     require(A&&A->kk==kk&&A->remaining==count,"native A prefetch identity/order");
     for(int n=0;n<count;++n){
      ns_buffers[worker]->record_free.wait();++ns_record_live[worker];
      ns_record_peak=std::max(ns_record_peak,ns_record_live[worker]);
      W_free.wait();int bank=0;while(bank<4&&W_live[bank])++bank;require(bank<4,"native W ownership");
      W_live[bank]=true;const U generation=++W_generation[bank];
      U live=0;for(bool b:W_live)live+=b;ns_W_peak=std::max(ns_W_peak,live);
      const int col=selected[first+size_t(n)];
      auto W=mem.submit(worker,cl_packed_address(o.in[1],col,kk,o.k,cl_record_size(o.cols,o.k)),
                        cl_record_size(o.cols,o.k),false,detail::WEIGHT,bank);
      tasks.write(new NSTask{col,kk,bank,generation,A,W});
     }
    }
   }
   if(nv_int("NS_A_PREFETCH",0))require(!A_tasks.read(),"native extra A prefetch");
   tasks.write(nullptr);
  });
  std::map<int,int> next_k;
  while(true){
   before=now();auto* t=tasks.read();stats.ready+=now()-before;if(!t)break;
   before=now();
   while(!t->A->ready){wait(t->A->arrived);}
   mem.await(t->W);
   stats.ack+=now()-before;
   require(W_live[t->bank]&&W_generation[t->bank]==t->generation,"native stale W");
   before=now();command_free.wait();stats.output+=now()-before;
   ++live_command;ns_result_peak=std::max(ns_result_peak,live_command);before=now();
   require(live_command<=2,"native command/result capacity");
   const bool product=nv_int("NS_PRODUCT",0)!=0;
   if(!t->kk){require(next_k.count(t->col)==0&&next_k.size()<16,"native RF allocation");
    ns_scope_ensure(worker,o.in[1],t->col);
    cycles(U(product?5:nv_int("NS_CONTEXT_CYCLES",3))); // CREATE LC->EOP4, next native accept+1
    next_k[t->col]=0;}
   require(next_k.count(t->col)&&next_k[t->col]==t->kk,"native RF owner/K order");
   cycles(U(product?nv_int("NS_EXEC_GAP",1):nv_int("NS_GUARD_CYCLES",3))); //+1 requires preparse; actual current guard+EXEC is+5
   const bool head=cl_record_size(o.cols,o.k)==1152;
   ns_raw_groups+=head?8:1;ns_RF_groups+=head?8:1; // head retains eight separate RNEs
   const U start=now();
   const bool final=t->kk+128==o.k;
   const U input_extra=head?U(nv_int("NS_HEAD_INPUT_EXTRA",0)):0;
   if(head&&input_extra){
    require(input_extra==8,"head operand trace choice");
    for(U offset:{0,1,2,3,6,9,12,15})pause_until(mem.weight_store[8*worker+t->bank].reserve(start+offset*C,C));
   }else{pause_until(mem.weight_store[8*worker+t->bank].reserve(start,8*C));}
   cycles(1); // final A/W operand -> input_done ACK, measured exec+9
   require(t->A->remaining>0,"native duplicate A release");
   if(--t->A->remaining==0){--live_A;A_free.post();}else ++ns_A_reuse;
   if(product){
    const int bank=t->bank;const U generation=t->generation;
    keep_child(sc_spawn([&,bank,generation,this]{cycles(2);
     require(W_live[bank]&&W_generation[bank]==generation,"native W INPUT EOP identity");
     W_live[bank]=false;W_free.post();W_released.notify(SC_ZERO_TIME);
    }));
   }else{W_live[t->bank]=false;W_free.post();W_released.notify(SC_ZERO_TIME);}
   cycles(3); // both ordinary and head measured result capture exec+12
   const U result_extra=U(nv_int(head?"NS_HEAD_PIPE_EXTRA":"NS_ORDINARY_PIPE_EXTRA",0));
   require(result_extra>=input_extra,"head result precedes operands");cycles(result_extra-input_extra);
   if(product)cycles(final?4:2); // actual 4/2-flit RF response EOP, NOT pure core completion
   next_k[t->col]+=128;
   ++m_tiles;++m_commands;++ns_static_tiles;m_work+=12*C;
   stats.service+=now()-before;++stats.tiles;
   // Command slots are distinct from early-released W storage. A final RF
   // context remains owned through output acknowledgement, not merely compute.
   auto result=sc_spawn([&,t,final,product,this]{
    cycles(2); // guard result capture -> commit decision
    if(final){
     for(int word=0;word<2;++word){
      auto reply=ns_S_request(worker,now());pause_until(reply.ack);
      if(product&&word==0)cycles(1); // actual C_ACK -> second C_REQUEST edge
     }
     require(next_k.at(t->col)==o.k,"native incomplete FINAL");next_k.erase(t->col);
     // The finite guard owns 32B; DDR takes it after its two local writes.
     if(!striped)mem.transfer(worker,tensors[o.out].base+U(t->col)*4,32,true,detail::DOT_OUTPUT);
    }
    cycles(product?(final?1:0):2); // RF-only EOP+2; FINAL EOP+8 with actual S RTT2
    require(ns_record_live[worker]>0,"native orphan record ticket");
    --ns_record_live[worker];ns_buffers[worker]->record_free.post();
    --live_command;command_free.post();all_terminal.notify(SC_ZERO_TIME);delete t;
   });
   keep_child(result);
  }
  before=now();while(live_command)wait(all_terminal);
  for(auto& c:children)if(!c.terminated())wait(c.terminated_event());
  if(A_producer.valid()&&!A_producer.terminated())wait(A_producer.terminated_event());
  require(producer.terminated()&&live_A==0,"native outstanding producer/A");
  for(bool b:W_live)require(!b,"native W leak");
  require(next_k.empty(),"native RF leak");
  stats.output+=now()-before;
  stats.elapsed+=now()-worker_start;done.notify(SC_ZERO_TIME);
 }
 void ns_emit(){
  std::cout<<",\"native_service\":{\"level\":"<<nv_int("NS_NATIVE",0)
   <<",\"static_calls\":"<<ns_static_calls<<",\"static_M_records\":"<<ns_static_tiles
   <<",\"A_S_read_B\":"<<ns_A_load_B<<",\"A_reused_commands\":"<<ns_A_reuse
   <<",\"RAW_groups\":"<<ns_raw_groups<<",\"RF_RNE_groups\":"<<ns_RF_groups
   <<",\"max_W_banks\":"<<ns_W_peak<<",\"max_A_tiles\":"<<ns_A_peak
   <<",\"max_command_result_slots\":"<<ns_result_peak
   <<",\"striped_Mid_read_B\":"<<ns_stripe_S_read_B<<",\"striped_destination_write_B\":"<<ns_stripe_S_write_B
   <<",\"striped_link_B\":"<<ns_stripe_copy_B<<",\"striped_source_route_RTL_verified\":false"
   <<",\"M_exec_result_cycles\":12,\"A_request_gap_cycles\":4,\"A_request_response_cycles\":2"
   <<",\"A_LOAD_command_to_terminal_cycles\":66,\"G128_to_ACK_cycles\":107,\"G128_to_LC_take_cycles\":108"
   <<",\"guard_issue_sensitivity_cycles\":"<<nv_int("NS_GUARD_CYCLES",3)
   <<",\"CREATE_control_sensitivity_cycles\":"<<nv_int("NS_CONTEXT_CYCLES",3)
   <<",\"RF_context_limit\":"<<nv_int("NS_RF_CONTEXTS",16)
   <<",\"projection_columns\":"<<nv_int("NS_PROJECT_COLS",128)<<",\"Down_spill\":"<<(nv_int("NS_SPILL",0)?"true":"false")
   <<",\"A_lookahead\":"<<(nv_int("NS_A_PREFETCH",0)?"true":"false")<<",\"balanced_context_groups\":"<<(nv_int("NS_BALANCE",0)?"true":"false")
   <<",\"first_consumer_starts_stripe_copy\":"<<(nv_int("NS_EARLY_STRIPE",0)?"true":"false")
   <<",\"G_next_projection_overlap_candidate\":"<<(nv_int("NS_G_OVERLAP",0)?"true":"false")
   <<",\"G_ring_peak_values\":"<<ns_ring_peak*8<<",\"G_pending_group_limit\":2,\"G_overlap_RTL_qualified\":false"
   <<",\"M_profile_job\":"<<nv_int("NS_M_PROFILE_JOB",nv_int("NS_HEAD_INPUT_EXTRA",0)==8?102202:nv_int("NS_PRODUCT",0)?102172:102118)
   <<",\"M_next_EXEC_gap_cycles\":"<<nv_int("NS_EXEC_GAP",1)
   <<",\"M_next_EXEC_preparse_RTL_verified\":false"
   <<",\"M_profile_300MHz_qualified\":false"
   <<",\"weight_image_layout\":"<<nv_int("NS_WEIGHT_LAYOUT",0)<<",\"weight_layout_packer_verified\":false"
   <<",\"ordinary_pipeline_extra_candidate_cycles\":"<<nv_int("NS_ORDINARY_PIPE_EXTRA",0)
   <<",\"head_pipeline_extra_candidate_cycles\":"<<nv_int("NS_HEAD_PIPE_EXTRA",0)
   <<",\"head_INPUT_extra_candidate_cycles\":"<<nv_int("NS_HEAD_INPUT_EXTRA",0)
   <<",\"CL_early_W_input_ACK_release\":"<<(nv_int("NS_EARLY_W",0)?"true":"false")
   <<",\"max_total_record_owners\":"<<ns_record_peak<<",\"record_owner_limit\":"<<nv_int("NS_RECORD_CREDITS",6)
   <<",\"six_record_owner_RTL_job\":102160,\"six_record_owner_RTL_verified\":true"
   <<",\"native_product_EOP_profile\":"<<(nv_int("NS_PRODUCT",0)?"true":"false")
   <<",\"scope_BEGINs\":"<<ns_scope_BEGINs<<",\"scope_hits\":"<<ns_scope_hits
   <<",\"scope_slots_per_P\":16,\"scope_BEGIN_EOP_cycles\":11,\"scope_prefetch_RTL_qualified\":false"
   <<",\"quantizer_profile_job\":102168,\"quantizer32B_pack\":true,\"quantizer_frames\":"<<ns_quant_frames
   <<",\"known_shift_quantizer_frames\":"<<ns_quant_known<<",\"quantizer_S_reads\":"<<ns_quant_reads
   <<",\"quantizer_S_writes\":"<<ns_quant_writes<<",\"shared_S_owner_peak\":"<<ns_S_owners_peak
   <<",\"DDR_channels\":2,\"DDR_beat_credits_each\":32,\"new_local_SRAM_B\":0"
   <<",\"whole_system_calibrated\":false,\"numerically_replayed\":false,\"physical_system_qualified\":false"
   <<",\"unqualified\":[\"dynamic_layout1_2_S32xS32\",\"E32_vector_services\",\"N_full_S32_numeric_profile\",\"dynamic_A_scale_ACK\",\"LC128_framed_native_interface\"]}";
 }
