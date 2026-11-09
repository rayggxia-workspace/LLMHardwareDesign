 // Raw pointwise E->E forwarding; no canonical/NExp/reduce rewrite. The old
 // flattened vector_region indexing is retained; physical strides are unproved.
 struct UForwardStats {
  U eligible_graph_edges=0,forwarded_packets=0,forwarded_bytes=0;
  U saved_S_read_bytes=0,saved_S_write_bytes=0;
  U saved_S_read_service_subcycles=0,saved_S_write_service_subcycles=0;
  U saved_S_read_reservations=0,saved_S_write_reservations=0;
  U forward_control_subcycles=0,forward_peak_bytes=0,E_arithmetic_subcycles=0;
  U packet_count=0,region_count=0,register_read_packet_cycles=0,register_write_packet_cycles=0;
 } u_stats;
 struct UPhaseSnapshot {U at,service,read,write;};
 struct UForwardSlot {bool valid=false;int tensor=-1;U offset=0,n=0,bytes=0;};
 std::vector<U> u_use_count;
 std::ofstream u_events;
 UPhaseSnapshot u_snapshot()const{return {now(),store[3].busy,mem.bytes_read,mem.bytes_write};}
 void u_init(const std::string& trace){
  u_use_count.assign(tensors.size(),0);for(const auto& op:ops)for(int tensor:op.in)++u_use_count[tensor];
  const char* path=std::getenv("U_FUSION_EVENTS");if(!path||!*path)return;
  const char* sha=std::getenv("U_FUSION_TRACE_SHA256");
  require(sha&&std::string(sha).size()==64&&std::all_of(sha,sha+64,[](unsigned char ch){return (ch>='0'&&ch<='9')||(ch>='a'&&ch<='f');}),"event log requires actual frozen trace SHA256");
  u_events.open(path);require(bool(u_events),"cannot open U fusion events");
  u_events<<"{\"schema_version\":1,\"trace_path\":"<<std::quoted(trace)<<",\"trace_sha256\":\""<<sha
   <<"\",\"subcycles_per_core_cycle\":"<<C<<",\"core_clock_Hz\":300000000"
   <<",\"fusion\":"<<(cfg.u_fusion?"true":"false")<<",\"fee_cycles\":"<<cfg.u_forward_fee
   <<",\"forward_capacity_bytes\":256,\"forward_metadata_bytes\":32"
   <<",\"input_slot_bytes\":768,\"output_slot_bytes\":256"
   <<",\"forward_register_read_bytes_per_cycle\":16,\"forward_register_write_bytes_per_cycle\":16"
   <<",\"forward_register_timing\":\"within original single-E packet service; added mux/control fee separate\""
   <<",\"layout_contract\":\"original flattened vector_region; no additional stride/physical-layout qualification\""
   <<",\"columns\":[\"id\",\"region\",\"op_index\",\"offset\",\"n\",\"forward_input_tensor\",\"forward_output_tensor\","
   <<"\"input_wall\",\"compute_wall\",\"output_wall\",\"input_S_read\",\"input_S_write\",\"output_S_read\",\"output_S_write\","
   <<"\"input_DDR_read_bus\",\"input_DDR_write_bus\",\"output_DDR_read_bus\",\"output_DDR_write_bus\",\"arith_subcycles\",\"control_subcycles\"]}\n";
 }
 bool u_legal_edge(size_t index,size_t end,U count)const{
  if(index+1>=end)return false;
  const auto& producer=ops[index];const auto& consumer=ops[index+1];
  if(!elementwise(producer)||!elementwise(consumer))return false;
  const auto& value=tensors[producer.out];
  return producer.elements==count&&consumer.elements==count&&value.elements==count&&value.bits==32&&
   u_use_count[producer.out]==1&&std::count(consumer.in.begin(),consumer.in.end(),producer.out)==1;
 }
 void vector_region(size_t begin,size_t end){
  if(!elementwise(ops[begin])){vector_region_legacy(begin,end);return;}
  const U count=ops[begin].elements,region=++u_stats.region_count,region_start=now();
  // Observation text is buffered for one region only so metadata precedes its
  // packets on disk. This host logger is not a claimed hardware data FIFO.
  std::ostringstream region_events;
  std::vector<bool> edges(end-begin,false);
  for(size_t index=begin;index<end;++index)if(u_legal_edge(index,end,count)){
   edges[index-begin]=true;++u_stats.eligible_graph_edges;
  }
  for(U offset=0;offset<count;offset+=64){const U n=std::min<U>(64,count-offset);UForwardSlot forward;
   for(size_t index=begin;index<end;++index){const auto& op=ops[index];if(op.kind=="Constant")continue;
    require(op.in.size()<=3,"E packet exceeds declared three-input FIFO contract");
    const auto input_before=u_snapshot();U input_direct=0,input_bytes=0;int forwarded_input=-1;
    auto read=[&](int tensor,U at,U bytes){read_range(tensor,at,bytes);
     input_direct+=ceildiv(bytes,cfg.swidth)*cfg.slat*C;input_bytes+=bytes;
    };
    for(int tensor:op.in){const U total=tensors[tensor].elements,bytes=tensors[tensor].bits/8;
     const U start=total==1?0:offset%total,take=std::min<U>(n,total-start);
     if(cfg.u_fusion&&forward.valid&&tensor==forward.tensor){
      require(forward.offset==offset&&forward.n==n&&forward.bytes==n*4&&bytes==4&&total==count,"forwarded E value identity");
      require(forwarded_input==-1,"multiple forwarded operands");forwarded_input=tensor;
      input_bytes+=forward.bytes;u_stats.saved_S_read_bytes+=forward.bytes;
      u_stats.saved_S_read_service_subcycles+=ceildiv(forward.bytes,cfg.swidth)*cfg.slat*C;
      ++u_stats.saved_S_read_reservations;u_stats.register_read_packet_cycles+=ceildiv(forward.bytes,16);
     }else{
      read(tensor,start*bytes,take*bytes);
      if(take<n&&total>1)read(tensor,0,std::min<U>(n-take,total)*bytes);
     }
    }
    if(forward.valid)require(forwarded_input==forward.tensor,"forwarded value not consumed by unique adjacent E");
    require(input_bytes<=768,"E packet input FIFO byte budget");
    const auto input_after=u_snapshot();const U input_read_bus=input_after.read-input_before.read;
    const U input_write_bus=input_after.write-input_before.write;
    const U beat_service=ceildiv(cfg.beat,cfg.swidth)*cfg.slat*C;
    const U input_S_read=input_direct+(input_write_bus/cfg.beat)*beat_service;
    const U input_S_write=(input_read_bus/cfg.beat)*beat_service;
    require(input_S_read+input_S_write==input_after.service-input_before.service,"input S direction/work accounting");
    const bool forwarded_output=cfg.u_fusion&&edges[index-begin];
    const U packets=ceildiv(n,4),cost=cfg.vecpipe?ceildiv(n,cfg.vector_lanes)+5:packets*cfg.ewise;
    const U compute_start=now();e_work+=cost*C;u_stats.E_arithmetic_subcycles+=cost*C;cycles(cost);
    const U control=forwarded_output?U(cfg.u_forward_fee)*C:0;
    u_stats.forward_control_subcycles+=control;if(control)cycles(cfg.u_forward_fee);
    const U compute_end=now();
    // The RF operand is streamed at 16B/cycle within this same E service. Its
    // slot remains owned until consumer E completion; input prefetch does not
    // get an uncharged 256-byte RF-to-FIFO copy.
    if(forward.valid)forward.valid=false;
    const auto output_before=u_snapshot();
    const U output_bytes=n*(tensors[op.out].bits/8);U output_direct=0;
    require(output_bytes<=256,"E packet output FIFO byte budget");
    if(forwarded_output){
     require(!forward.valid&&output_bytes==n*4&&output_bytes<=256,"forward output register budget");
     require(cost>=ceildiv(output_bytes,16),"forward register throughput exceeds E packet service");
     forward={true,op.out,offset,n,output_bytes};
     ++u_stats.forwarded_packets;u_stats.forwarded_bytes+=output_bytes;
     u_stats.saved_S_write_bytes+=output_bytes;
     u_stats.saved_S_write_service_subcycles+=ceildiv(output_bytes,cfg.swidth)*cfg.slat*C;
     ++u_stats.saved_S_write_reservations;u_stats.register_write_packet_cycles+=ceildiv(output_bytes,16);
     u_stats.forward_peak_bytes=std::max(u_stats.forward_peak_bytes,output_bytes);
    }else{
     write_range(op.out,offset*(tensors[op.out].bits/8),output_bytes);
     output_direct=ceildiv(output_bytes,cfg.swidth)*cfg.slat*C;
    }
    for(int tensor:op.in)if(last_use[tensor]==static_cast<int>(index)&&(tensors[tensor].elements==count||offset+n==count)){
     const U bytes=tensors[tensor].bits/8;
     discard_range(tensor,tensors[tensor].elements==count?offset*bytes:0,std::min<U>(n,tensors[tensor].elements)*bytes);
    }
    const auto output_after=u_snapshot();const U output_read_bus=output_after.read-output_before.read;
    const U output_write_bus=output_after.write-output_before.write;
    const U output_S_read=(output_write_bus/cfg.beat)*beat_service;
    const U output_S_write=output_direct+(output_read_bus/cfg.beat)*beat_service;
    require(output_S_read+output_S_write==output_after.service-output_before.service,"output S direction/work accounting");
    const U id=++u_stats.packet_count;
    if(u_events.is_open())region_events<<"["<<id<<","<<region<<","<<index<<","<<offset<<","<<n<<","<<forwarded_input<<","<<(forwarded_output?op.out:-1)
     <<","<<input_after.at-input_before.at<<","<<compute_end-compute_start<<","<<output_after.at-output_before.at
     <<","<<input_S_read<<","<<input_S_write<<","<<output_S_read<<","<<output_S_write
     <<","<<input_read_bus<<","<<input_write_bus<<","<<output_read_bus<<","<<output_write_bus
     <<","<<cost*C<<","<<control<<"]\n";
   }
   require(!forward.valid,"forward register survives region chunk boundary");
  }
  if(u_events.is_open()){
   u_events<<"{\"type\":\"region\",\"id\":"<<region<<",\"begin\":"<<begin<<",\"end_exclusive\":"<<end
    <<",\"elements\":"<<count<<",\"start_subcycles\":"<<region_start<<",\"end_subcycles\":"<<now()<<"}\n";
   u_events<<region_events.str();
  }
 }
 void emit_u_fusion(){
  require(u_stats.forwarded_packets==u_stats.saved_S_read_reservations&&u_stats.forwarded_packets==u_stats.saved_S_write_reservations,"forward read/write count conservation");
  require(u_stats.saved_S_read_bytes==u_stats.forwarded_bytes&&u_stats.saved_S_write_bytes==u_stats.forwarded_bytes,"forward byte conservation");
  if(u_events.is_open()){u_events.flush();require(bool(u_events),"U event log write failure");}
  std::cout<<",\"u_fusion_study\":{\"fusion_enabled\":"<<(cfg.u_fusion?"true":"false")
   <<",\"forward_control_cycles\":"<<cfg.u_forward_fee<<",\"forward_capacity_bytes\":256,\"forward_metadata_bytes\":32"
   <<",\"eligible_graph_edges\":"<<u_stats.eligible_graph_edges
   <<",\"forwarded_packets\":"<<u_stats.forwarded_packets<<",\"forwarded_bytes\":"<<u_stats.forwarded_bytes
   <<",\"saved_S_read_bytes\":"<<u_stats.saved_S_read_bytes<<",\"saved_S_write_bytes\":"<<u_stats.saved_S_write_bytes
   <<",\"saved_S_read_service_subcycles\":"<<u_stats.saved_S_read_service_subcycles
   <<",\"saved_S_write_service_subcycles\":"<<u_stats.saved_S_write_service_subcycles
   <<",\"saved_S_read_reservations\":"<<u_stats.saved_S_read_reservations
   <<",\"saved_S_write_reservations\":"<<u_stats.saved_S_write_reservations
   <<",\"forward_control_subcycles\":"<<u_stats.forward_control_subcycles<<",\"forward_peak_bytes\":"<<u_stats.forward_peak_bytes
   <<",\"E_arithmetic_subcycles\":"<<u_stats.E_arithmetic_subcycles<<",\"packet_count\":"<<u_stats.packet_count<<",\"region_count\":"<<u_stats.region_count
   <<",\"register_read_packet_cycles\":"<<u_stats.register_read_packet_cycles<<",\"register_write_packet_cycles\":"<<u_stats.register_write_packet_cycles
   <<",\"event_log_enabled\":"<<(u_events.is_open()?"true":"false")<<",\"event_schema_version\":1"
   <<",\"scope\":\"actual sequential adjacent-E single-consumer forwarding; saved service counts direct SIO only; real cache/DDR effects retained; one E and per-op arithmetic unchanged; overlap only in separate frozen-cost replay\"}";
 }
