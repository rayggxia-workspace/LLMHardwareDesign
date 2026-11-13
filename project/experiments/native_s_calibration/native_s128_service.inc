 // One physical ordinary request port, two total response owners per S.
 // Caller-specific READY may hold the ordered provider queue. Reservations
 // denote accepted requests; no future request is booked before its clock.
 struct NSSReply {U accepted,ack;};
 std::array<std::deque<U>,4> ns_S_ACKs;
 U ns_S_owners_peak=0,ns_quant_frames=0,ns_quant_known=0,ns_quant_reads=0,ns_quant_writes=0;
 NSSReply ns_S_request(int group,U earliest,U ready_after=0){
  auto& ACKs=ns_S_ACKs[group];
  pause_until(earliest);
  while(true){
   while(!ACKs.empty()&&ACKs.front()<=now())ACKs.pop_front();
   if(ACKs.size()==2){pause_until(ACKs.front());continue;}
   U slot=now();
   for(const auto& p:store[group].slots){
    if(p.second<=slot)continue;
    if(slot+C<=p.first)break;
    slot=std::max(slot,p.second);
   }
   if(slot>now()){pause_until(slot);continue;}
   const U accepted=now();require(store[group].reserve(accepted,C)==accepted+C,"native S accept calendar");
   U ack=std::max(accepted+2*C,ready_after);
   if(!ACKs.empty())ack=std::max(ack,ACKs.back()+C);
   ACKs.push_back(ack);ns_S_owners_peak=std::max<U>(ns_S_owners_peak,ACKs.size());
   require(ACKs.size()<=2,"native shared S owner overflow");return {accepted,ack};
  }
 }
 void ns_quantize(int group,bool known){
  const U start=now();U shift=0,last_ACK=start;
  const auto& requests=known?ns_quant_profile::known_requests:ns_quant_profile::fallback_requests;
  const auto& writes=known?ns_quant_profile::known_writes:ns_quant_profile::fallback_writes;
  for(size_t i=0;i<requests.size();++i){
   const U wanted=start+C+requests[i]*C+shift;
   auto reply=ns_S_request(group,wanted);
   shift+=reply.accepted-wanted;last_ACK=std::max(last_ACK,reply.ack);
   if(writes[i])++ns_quant_writes;else ++ns_quant_reads;
  }
  pause_until(last_ACK+2*C);++ns_quant_frames;ns_quant_known+=known;
 }
 // Existing single-source16B copy, not a free bulk-DMA. The next source
 // response can be held until every previous destination hold has ACKed.
 // Endpoint/register-directory headers are charged separately by the caller.
 void ns_copy_words(int source,const std::vector<int>& destinations,int words,bool owns_route=false){
  if(!owns_route)ns_copy_lock->wait();
  U next=now()+2*C,last_ACK=0;
  for(int word=0;word<words;++word){
   auto source_reply=ns_S_request(source,next,last_ACK?last_ACK+C:0);
   pause_until(source_reply.ack);next=source_reply.ack+2*C;ns_stripe_S_read_B+=16;
   U all_ACK=0;size_t accepted=0;sc_event accepted_event;std::vector<sc_process_handle> destinations_pending;
   const U launch=now();
   for(int p:destinations){
    const U link_end=cl_links[p].reserve(launch,C);
    destinations_pending.push_back(sc_spawn([&,p,link_end,this]{
     auto destination_reply=ns_S_request(p,link_end);
     all_ACK=std::max(all_ACK,destination_reply.ack);
     ns_stripe_copy_B+=16;ns_stripe_S_write_B+=16;cl_link_bytes+=16;
     ++accepted;accepted_event.notify(SC_ZERO_TIME);
    }));
   }
   while(accepted<destinations.size())wait(accepted_event);
   for(auto& child:destinations_pending)if(!child.terminated())wait(child.terminated_event());
   last_ACK=all_ACK;
  }
  pause_until(last_ACK);cycles(2);
  if(!owns_route)ns_copy_lock->post();
 }
 void ns_check_quantizer(){
  U at=now();ns_quantize(0,false);require(now()-at==95*C,"fallback quantizer trace mismatch");
  at=now();ns_quantize(0,true);require(now()-at==60*C,"known-shift quantizer trace mismatch");
  require(ns_quant_reads==96&&ns_quant_writes==32&&ns_S_owners_peak==2,"quantizer transaction/owner mismatch");
  at=now();ns_copy_words(0,{0,1,2},32);
  require(now()-at==133*C,("actual32word copy timing mismatch got"+std::to_string((now()-at)/C)).c_str());
  std::cout<<"QUANT_TRACE_MATCH fallback95 known60 read96 write32 owners2 source102168\n";
 }
