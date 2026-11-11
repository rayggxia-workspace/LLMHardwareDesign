  // Explicit finite FIFO: issue and retire events advance independently.
  // Each entry is one 64B physical-line fragment, including in-flight data.
  // A consumer clock may retire two returned entries, never two future reads.
  U feed(int worker,U row,U row_count,U ki,U count,U tile_id=0,U local_ready_at=0){
   if(!active)return 0;
   require(valid&&worker>=0&&worker<2&&row+row_count<=rows&&ki+count<=K,"invalid pool read generation/range");
   auto& w=workers[worker];require(!w.active,"overlapping FIFO use by one P");w.active=1;
   ++live_workers;max_live_workers=std::max(max_live_workers,live_workers);
   const U started=now(),generation=epoch;U hit=0,next_issue=now();
   struct Beat {U row,address,bytes,issued,ready,done,outstanding;bool last_in_row;};
   const U shared_k=ki<prefix_k?std::min(count,prefix_k-ki):0;
   const U shared_bytes=shared_k*element_bytes,local_cycles=ceildiv((count-shared_k)*element_bytes,32)*C;
   U issue_row=row,position=ki*element_bytes,left=shared_bytes,consumer_busy=now();
   std::deque<Beat> fifo;
   if(!shared_bytes){
    // All-local tiles retain the frozen aggregate suffix timing.
    pause_until(now()+row_count*local_cycles);issue_row=row+row_count;
   }
   // One FIFO spans rows, exactly as in the frozen path: requests may prefetch
   // later rows while the consumer waits for the preceding local A suffix.
   while(issue_row<row+row_count||!fifo.empty()||consumer_busy>now()){
     const U at=now();
     while(!fifo.empty()&&fifo.front().done&&fifo.front().done<=at)fifo.pop_front();
     if(issue_row==row+row_count&&fifo.empty()&&consumer_busy<=at)break;
     // Acceptance quota is per P, not a second free physical read port.
     if(issue_row<row+row_count&&fifo.size()<depth&&at>=next_issue){
      U issued_count=0;
      while(issue_row<row+row_count&&fifo.size()<depth&&issued_count<2){
       const U address=issue_row*stride+position,take=std::min(left,64-address%64);
       const U end=reserve(at,false,address),ready=end+latency*C;
       w.port_wait+=end-port_cycles*C-at;w.latency_subcycles+=latency*C;
       ++w.reads;w.read_bytes+=take;w.read_bus_bytes+=64;hit+=take;
       fifo.push_back(Beat{issue_row,address,take,at,ready,0,U(fifo.size()+1),take==left});
       w.fifo_peak=std::max<U>(w.fifo_peak,fifo.size());
       require(w.fifo_peak<=depth,"FIFO capacity exceeded");
       position+=take;left-=take;++issued_count;
       if(!left){++issue_row;position=ki*element_bytes;left=shared_bytes;}
      }
      w.issue_peak_per_cycle=std::max(w.issue_peak_per_cycle,issued_count);
      next_issue=at+C;
     }
     if(consumer_busy<=at&&!fifo.empty()&&!fifo.front().done&&fifo.front().ready<=at){
      U entries=0,bytes=0,done=at+C;
      std::array<Consumed,2> events{};
      // A second line joins only if it has actually returned by clock start.
      for(auto& beat:fifo){
       if(entries==2||beat.done||beat.ready>at||beat.row!=fifo.front().row)break;
       const U source=base+beat.row*K*element_bytes+beat.address-beat.row*stride;
       events[entries]=Consumed{worker,generation,beat.row,source,beat.address,beat.bytes,tile_id,beat.ready,at+C};
       if(consumer_ready_at)done=std::max(done,consumer_ready_at(events[entries]));
       bytes+=beat.bytes;++entries;
      }
      require(entries&&bytes<=128,"invalid two-line consumer batch");
      ++w.consumer_cycles;
      if(entries==2)++w.two_line_consume_cycles;
      w.consumer_peak_bytes_per_cycle=std::max(w.consumer_peak_bytes_per_cycle,bytes);
      for(U i=0;i<entries;++i){
       auto& beat=fifo[i];beat.done=done;events[i].consumed_at=done;
       w.consumed_bytes+=beat.bytes;
       if(on_consume)on_consume(events[i]);
       // Deferred observer: issuance facts retain the actual acceptance time
       // and credit count; release time is known only after consumer stalls.
       if(on_issue)on_issue(Issued{worker,generation,beat.address,beat.bytes,tile_id,
         beat.issued,beat.ready,done,beat.outstanding});
      }
      consumer_busy=done;
      if(fifo[entries-1].last_in_row){
       if(shared_k<count)consumer_busy=std::max(consumer_busy,local_ready_at);
       consumer_busy+=local_cycles;
      }
     }
     U next=~U(0);
     if(issue_row<row+row_count&&fifo.size()<depth&&next_issue>at)next=std::min(next,next_issue);
     if(!fifo.empty()){
      if(fifo.front().done>at)next=std::min(next,fifo.front().done);
      if(!fifo.front().done&&fifo.front().ready>at)next=std::min(next,fifo.front().ready);
     }
     if(consumer_busy>at)next=std::min(next,consumer_busy);
     require(next!=~U(0)&&next>at,"finite FIFO event progress lost");
     if(issue_row<row+row_count&&fifo.size()>=depth)w.credit_wait+=next-at;
     pause_until(next);
   }
   require(epoch==generation&&active&&valid,"stale generation consumed");
   w.feed_subcycles+=now()-started;++w.completed_tiles;w.active=0;--live_workers;return hit;
  }
