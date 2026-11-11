 // Included inside Study. No tensor arithmetic occurs in this performance model.
 std::vector<std::unique_ptr<finite_m::Model>> finite_models;
 std::array<iteration3::Counters,3> finite_stats{};
 bool finite_target(const Op& o,const Tile& p) const {
  return cfg.iteration3_buffers!=0&&cfg.stream&&cfg.m_mode==2&&cfg.pbytes==16384&&
   cfg.swidth==64&&s_port_duration(cfg,0,64)==C&&cfg.contexts==8&&
   o.layout==0&&o.rows==1&&tensors[o.in[0]].bits==32&&cfg.weight_bits==8&&
   o.shift==16&&(o.k==2048||o.k==11008)&&o.cols%8==0&&
   p.r==1&&p.n==8&&p.k==256&&p.ki%256==0;
 }
 static bool finite_port_available(Calendar& port,U at){
  // Same expiry as Calendar::reserve; no ledger or future reservation changes.
  auto end=std::remove_if(port.slots.begin(),port.slots.end(),[at](auto slot){return slot.second<=at;});
  port.slots.erase(end,port.slots.end());
  for(const auto& slot:port.slots){if(slot.first<at+C&&slot.second>at){return false;}}
  return true;
 }
 void finite_layout(const Tile& p,bool resident,U full_a,U prefix,U apad,U bpad) const {
  const U wb_bytes=cfg.combine?512:0,workspace=1024+wb_bytes;
  const U output_base=cfg.pbytes-workspace;
  const U data_end=resident?full_a+2*bpad+96:prefix+2*apad+2*bpad+128;
  require(cfg.pbytes==16384&&apad==1024&&bpad==2048,"finite physical tile layout width");
  require(data_end<=output_base&&output_base+8*32<=cfg.pbytes-wb_bytes,
          "finite inputs/old psum/output workspace/WB overlap");
  require(p.finite_a%64==0&&p.finite_b%64==0&&
          U(p.finite_a)+1024<=data_end&&U(p.finite_b)+2048<=data_end&&
          (U(p.finite_a)+1024<=p.finite_b||U(p.finite_b)+2048<=p.finite_a),
          "finite tile input placement outside declared layout");
 }
 void finite_service(const Op& o,const Tile& p,int worker,unsigned context){
  require(iteration3::profile_available,"finite M calibrated profile unavailable");
  while(finite_models.size()<static_cast<size_t>(cfg.mcount)){
   finite_models.emplace_back(new finite_m::Model(cfg.iteration3_buffers));
  }
  auto& engine=*finite_models[worker];auto& stats=finite_stats[worker];
  require(engine.empty(),"old tile enters with live finite completion");
  const U entry=now(),aligned=ceildiv(entry,C)*C;pause_until(aligned);
  stats.alignment_subcycles+=aligned-entry;
  std::deque<U> reads,writes;unsigned issued=0,retired=0;
  const U old_adapt=std::max(ceildiv(p.abytes,32),ceildiv(p.bbytes,64));
  const U old_compute=U(p.r)*ceildiv(p.k,8);
  const U old_tail=4+(p.ki==0?14:0)+(p.last?8+ceildiv(U(p.r)*p.n,4)*2:0);
  stats.old_adapter_cycles+=old_adapt;stats.old_M_cycles+=old_compute+old_tail;
  ++stats.old_tiles;if(p.last){++stats.final_outputs;}
  const unsigned tag=static_cast<unsigned>((U(p.batch)*o.cols+p.col)/8+1);
  auto& read_port=store[worker];auto& write_port=cfg.split_P_ports?write_store[worker]:store[worker];
  const U service_start=now();
  while(retired<16){
   finite_m::Inputs in{};in.command_valid=issued<16;
   auto& command=in.command;command.ctx=context;command.tag=tag;
   command.ki=static_cast<unsigned>(p.ki)+issued*16;command.total=static_cast<unsigned>(o.k);
   command.k=16;command.n=8;command.shift=16;command.first=command.ki==0;
   command.last=command.ki+16==command.total;
   command.a=p.finite_a+issued*64;command.b=p.finite_b+issued*128;
   command.out=static_cast<unsigned>(cfg.pbytes-(1024+(cfg.combine?512:0)))+context*32;
   // Held invalid command fields must remain within physical port widths.
   if(!in.command_valid){command={};}
   in.read_response=!reads.empty()&&reads.front()<=now();
   in.write_ack=!writes.empty()&&writes.front()<=now();
   auto observed=engine.observe(in);
   in.read_ready=observed.read_valid&&finite_port_available(read_port,now());
   in.write_ready=observed.write_valid&&finite_port_available(write_port,now());
   stats.peak_calendar_intervals=std::max(stats.peak_calendar_intervals,U(read_port.slots.size()+
       (cfg.split_P_ports?write_port.slots.size():0)));
   observed=engine.observe(in);
   require(!(observed.read_fire&&observed.write_fire),"finite S read/write accepted together");
   stats.peak_buffers=std::max(stats.peak_buffers,U(observed.live_buffers));
   stats.peak_reads=std::max(stats.peak_reads,U(observed.reads_outstanding));
   stats.peak_completions=std::max(stats.peak_completions,U(observed.reservations));
   if(observed.read_pop){reads.pop_front();++stats.read_acks;}
   if(observed.write_pop){writes.pop_front();++stats.write_acks;}
   if(observed.read_fire){
    require(read_port.reserve(now(),C)==now()+C,"finite read reservation slipped");
    reads.push_back(now()+iteration3::read_ack_cycles*C);++stats.read_requests;
    adapter_work+=C;
   }
   if(observed.write_fire){
    require(write_port.reserve(now(),C)==now()+C,"finite write reservation slipped");
    writes.push_back(now()+iteration3::write_ack_cycles*C);++stats.write_requests;
   }
   stats.peak_calendar_intervals=std::max(stats.peak_calendar_intervals,U(read_port.slots.size()+
       (cfg.split_P_ports?write_port.slots.size():0)));
   if(observed.read_valid&&!in.read_ready){++stats.read_calendar_stalls;}
   if(observed.write_valid&&!in.write_ready){++stats.write_calendar_stalls;}
   if(observed.command_fire){require(observed.descriptor_ok,"finite generated invalid descriptor");++issued;++stats.commands;++m_commands;}
   if(observed.leaf_fire){++stats.leaf_accepts;}
   if(observed.commit){++stats.commits;}
   if(observed.core_advance_active){++stats.core_active_cycles;m_work+=C;}
   if(observed.completion_pop){
    require(!observed.done_error&&observed.done_ctx==context&&observed.done_tag==tag&&
       observed.done_next==static_cast<unsigned>(p.ki)+(retired+1)*16,"finite completion order/error");
    ++retired;++stats.completions;
   }
   engine.tick(in);++stats.control_cycles;
   // Include the next acceptance edge, never permit two old tiles at one edge.
   cycles(1);
  }
  require(issued==16&&engine.empty()&&reads.empty()&&writes.empty(),"finite service failed to drain");
  require(p.last?!engine.active(context):engine.committed(context)==static_cast<unsigned>(p.ki+p.k),"finite K/context retirement");
  stats.wall_subcycles+=now()-service_start;++m_tiles;
 }
 void emit_finite(){iteration3::emit(std::cout,cfg.iteration3_buffers,finite_stats,cfg.mcount);}
