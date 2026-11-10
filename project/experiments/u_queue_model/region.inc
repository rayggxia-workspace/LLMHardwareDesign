 // Replace one qualified staged tile's old local E/S/NExp fees exactly once.
 // Cache and DDR touches retain their original ordering and byte quantities.
 void native_nexp_region(const Op& o,size_t index){
  require(o.in.size()==1&&tensors[o.in[0]].bits==16&&tensors[o.out].bits==32,"native region format");
  require(o.elements%64==0&&tensors[o.in[0]].elements==o.elements,"native calibrated shape");
  int input=o.in[0];++optimization::region_count;
  for(U offset=0;offset<o.elements;offset+=64){
   touch(input,offset*2,128,false);
   U old_vector=cfg.vecpipe?21:16*cfg.ewise;
   optimization::vector_cost(old_vector,old_vector);
   optimization::removed_vector+=old_vector;
   optimization::removed_s_subcycles+=s_port_duration(cfg,3,128)+s_port_duration(cfg,3,256);
   const U cost=optimization::region_tile_cycles;
   // The native time includes the sequencer, N core and actual old S arbiter.
   // Do not charge read_range/write_range or separate compute cycles again.
   pause_until(store[3].reserve(now(),cost*C));e_work+=cost*C;
   optimization::native_region_cycles+=cost;++optimization::region_tiles;
   touch(o.out,offset*4,256,true);
   if(last_use[input]==static_cast<int>(index))discard_range(input,offset*2,128);
  }
  U old_extra=iteration4::supplemental_service(o.elements,cfg.iteration1_nexp,cfg.iteration2_nexp,cfg.iteration4_nexp,false);
  optimization::removed_nexp+=optimization::nexp_cost(o.elements,false,old_extra,true);
 }
