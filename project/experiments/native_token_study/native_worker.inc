// Included within Study. Finite serial controller for each of two concurrent P.
// No same-P DMA/LOAD/compute overlap is claimed. All descriptor/S ACKs retire.
void matrix_worker(const Op& o,int worker,sc_event& done){
 auto& n=native_model::data[worker];auto& d=detail::data.p[worker];const U started=now();U ack=0,output_time=0;
 const auto& a=tensors[o.in[0]];const auto& b=tensors[o.in[1]];
 const bool stat=o.layout==0;const int abits=a.bits,bbits=stat?cfg.weight_bits:b.bits;
 require((abits==8||abits==16||abits==32)&&(bbits==8||bbits==16||bbits==32),"unsupported native integer width");
 const int limbs_a=abits==32?3:1,limbs_b=bbits==32?3:1;
 const bool aw=abits!=8,bw=bbits!=8;
 const bool context=cfg.native_context&&stat&&o.rows==1&&U(o.k)*limbs_a<=65535;
 const int group_limit=context?cfg.native_contexts:1;
 const U raw_a_chunk=32*U(abits/8),raw_b_chunk=32*8*U(bbits/8);
 const U packed_a_chunk=4*64*U(stat?1:limbs_a),packed_b_chunk=4*U(bw?128:64)*limbs_b;
 // One raw/packed tile staging slot, one 96-byte scratch, finite conversion
 // pair state and 32-byte output slot. S64 M results are existing registers.
 const U fixed=1024+raw_b_chunk+packed_b_chunk+packed_a_chunk+96+32+32;
 const U full_a=U(o.k)*U(abits/8);const bool resident=full_a+fixed<=16384;
 const U peak=fixed+(resident?full_a:raw_a_chunk);require(peak<=16384,"native P 16KiB overflow");
 n.peak_S_bytes=std::max(n.peak_S_bytes,peak);scratch_peak=std::max(scratch_peak,peak);
 const auto cols=detail::columns(o.cols,worker,2,false);
 auto local=[&](U words,bool write,U first=0){
  if(!words)return;
  (write?n.local_write_words:n.local_read_words)+=words;native_model::word_operations(n,first,words);
  pause_until(store[worker].reserve(now(),words*native_model::narrow_cycles*C));
 };
 auto work=[&](U cost,bool merge=false){
  if(merge)n.merge_cycles+=cost;else n.split_cycles+=cost;
  adapter_work+=cost*C;cycles(cost);
 };
 auto transfer=[&](U address,U bytes,bool write,detail::Flow flow){
  if(flow==detail::A)n.source_A_DDR_bytes+=bytes;
  else if(flow==detail::WEIGHT||flow==detail::DYNAMIC_B)n.source_B_DDR_bytes+=bytes;
  else if(flow==detail::DOT_OUTPUT)n.output_DDR_bytes+=bytes;
  U before=now();mem.transfer(worker,address,bytes,write,flow);ack+=now()-before;
 };
 auto command=[&](int op,U leaf=0){
  n.leaf_cycles+=leaf;n.wrapper_control_cycles+=native_model::wrapper_cycles;
  if(op==4)++n.scale_commands;else if(op==3)++n.raw_commands;else if(op==5)++n.RNE_commands;else if(op==14)++n.release_commands;
  else{++n.MAC_commands;++m_commands;++m_tiles;++d.tiles;m_work+=leaf*C;}
  cycles(leaf+native_model::wrapper_cycles);
 };
 auto load=[&](int rows,int tiles,bool reuse_b=false){
  require(!(rows==0&&reuse_b),"empty native LOAD");++n.loads;if(rows==0)++n.B_only_loads;
  U wide=U(tiles)*((rows?1:0)+(reuse_b?0:(bw?2:1)));
  n.wide_reads+=wide;n.A_beats+=U(rows)*tiles;n.B_beats+=reuse_b?0:U(tiles)*(bw?2:1);
  for(int bank=0;bank<4;++bank)n.bank_operations[bank]+=wide;
  // Actual 4x1RW issue, one physical read per bank; response/hold/control
  // costs are represented by the structural loader recurrence, not a 1R1W port.
  U cost=native_model::loader_done(rows,tiles,bw,reuse_b)+2;n.load_cycles+=cost;
  U begin=now();pause_until(store[worker].reserve(begin,wide*C));pause_until(begin+cost*C);
 };
 auto pack_a=[&](int k,int tiles){
  U raw=U(k)*U(abits/8);n.raw_A_conversion_read_bytes+=raw;local(ceildiv(raw,16),false);
  work(ceildiv(U(k),native_model::split_width));
  U packed=U(tiles)*64*U(stat?1:limbs_a);n.packed_A_bytes+=packed;local(packed/16,true);
 };
 auto pack_b=[&](int k,int valid_n,int tiles){
  U raw=U(k)*valid_n*U(bbits/8);n.raw_B_conversion_read_bytes+=raw;local(ceildiv(raw,16),false);
  work(ceildiv(U(k)*valid_n,native_model::split_width));
  U packed=U(tiles)*U(bw?128:64)*limbs_b;n.packed_B_bytes+=packed;local(packed/16,true);
 };
 auto load_b_source=[&](int batch,int col,int kk,int k,int valid_n){
  if(stat)transfer(b.base+(U(batch)*o.cols*o.k+U(col)*o.k+U(kk)*valid_n)*U(bbits/8),U(k)*valid_n*U(bbits/8),false,detail::WEIGHT);
  else if(o.layout==1){for(int c=0;c<valid_n;++c)transfer(b.base+(U(batch)*o.cols*o.k+U(col+c)*o.k+kk)*U(bbits/8),U(k)*U(bbits/8),false,detail::DYNAMIC_B);}
  else for(int r=0;r<k;++r)transfer(b.base+(U(batch)*o.k*o.cols+U(kk+r)*o.cols+col)*U(bbits/8),U(valid_n)*U(bbits/8),false,detail::DYNAMIC_B);
 };
 auto clear96=[&]{n.S96_clear_words+=6;local(6,true);};
 auto merge96=[&]{
  ++n.S96_terms;
  for(U pair=0;pair<4;++pair){
   command(3);const U first=(pair*24)/16;
   local(2,false,first);work(native_model::merge_pair_cycles,true);local(2,true,first);
  }
 };
 auto final96=[&]{
  for(U pair=0;pair<4;++pair){local(2,false,(pair*24)/16);n.final_rne_cycles+=native_model::rne_pair_cycles;
   adapter_work+=native_model::rne_pair_cycles*C;cycles(native_model::rne_pair_cycles);}
  local(2,true); // Two full128-bit output containers; inactive columns padded.
 };
 auto native_output=[&]{
  for(int half=0;half<2;++half){command(5,3);
   // Exact P native final read with store ACK: leaf+9 instead of leaf+4.
   ++n.local_write_words;native_model::word_operations(n,U(half),1);
   pause_until(store[worker].reserve(now(),5*C));
  }
 };
 for(int batch=0;batch<o.batches;++batch)for(int row=0;row<o.rows;++row){
  if(cols.empty())continue;
  if(resident){transfer(a.base+(U(batch)*o.rows+row)*o.k*U(abits/8),full_a,false,detail::A);n.resident_A_bytes+=full_a;
   resident_saved+=full_a*(ceildiv(U(cols.size()),U(group_limit))-1);}
  for(size_t group=0;group<cols.size();group+=size_t(group_limit)){
   const size_t count=std::min<size_t>(group_limit,cols.size()-group);
   const bool native_static=stat;
   if(stat)++n.static_groups;else ++n.dynamic_groups;
   if(context){++n.context_groups;n.context_outputs+=count;}
   std::array<U,8> next{};std::array<bool,8> complete{};
   if(!context)command(4); // Explicit coefficient1/shift0 for legacy full-K limb rows.
   if(!native_static)clear96();
   for(int kk=0;kk<o.k;kk+=32){
    int k=std::min(32,o.k-kk),tiles=(k+7)/8;
    if(!resident)transfer(a.base+((U(batch)*o.rows+row)*o.k+kk)*U(abits/8),U(k)*U(abits/8),false,detail::A);
    pack_a(k,tiles);
    for(size_t c=0;c<count;++c){
     int col=cols[group+c],valid_n=std::min(8,o.cols-col);
     load_b_source(batch,col,kk,k,valid_n);pack_b(k,valid_n,tiles);
     if(native_static){
      load(context&&c?0:limbs_a,tiles);
      if(context){
       for(int limb=0;limb<limbs_a;++limb){
        U flat=U(limbs_a)*kk+U(limb)*k;require(next[c]==flat&&!complete[c],"context flatK lifecycle");
        command(4);command(13,native_model::leaf_latency(1,tiles,aw,bw));
        ++n.scalar_row_terms;n.S8_bitpass_issues+=U(tiles)*(aw?3:1)*(bw?3:1);
        if(abits==32)++n.static_S32_MAC_commands;
        next[c]+=k;complete[c]=kk+k==o.k&&limb+1==limbs_a;
       }
      }else{
       command(10,native_model::leaf_latency(limbs_a,tiles,aw,bw));
       n.scalar_row_terms+=limbs_a;n.S8_bitpass_issues+=U(limbs_a)*tiles*(aw?3:1)*(bw?3:1);
       if(abits==32)++n.static_S32_MAC_commands;
      }
     }else{
      // Exact32x32 requires9 distinct native terms. Each finishes before its
      // raw64 result is added to the owned96 scratch. No hidden9 context RF.
      for(int al=0;al<limbs_a;++al)for(int bl=0;bl<limbs_b;++bl){
       load(1,tiles);command(10,native_model::leaf_latency(1,tiles,aw,bw));++n.dynamic_MAC_commands;merge96();
       ++n.scalar_row_terms;n.S8_bitpass_issues+=U(tiles)*(aw?3:1)*(bw?3:1);
      }
     }
    }
   }
   for(size_t c=0;c<count;++c){
    const int col=cols[group+c],valid_n=std::min(8,o.cols-col);U before=now();
    if(context){require(complete[c]&&next[c]==U(limbs_a)*o.k,"context finalK");native_output();}
    else if(native_static){
     if(limbs_a==1)native_output();else{clear96();for(int limb=0;limb<limbs_a;++limb)merge96();final96();}
    }else final96();
    // Copy padded native/conditional output to a real finite S slot before DMA.
    // The memory descriptor reads only the valid n*4 bytes; all ACKs precede reuse.
    U pre_transfer=now();transfer(tensors[o.out].base+((U(batch)*o.rows+row)*o.cols+col)*4,U(valid_n)*4,true,detail::DOT_OUTPUT);
    ack-=now()-pre_transfer; // Output wait belongs to output, not input-ACK stage.
    if(context)command(14);
    output_time+=now()-before;n.useful_MACs+=U(o.k)*valid_n;
   }
  }
 }
 d.ack+=ack;d.output+=output_time;d.service+=now()-started-ack-output_time;d.elapsed+=now()-started;
 done.notify(SC_ZERO_TIME);
}
void matrix(const Op& o){
 ++native_model::all_Dot_calls;bool s32=false;for(int t:o.in)if(tensors[t].bits==32){++native_model::S32_Dot_input_occurrences;s32=true;}
 if(s32)++native_model::S32_Dot_calls;
 U before=now(),old_tiles=m_tiles,old_commands=m_commands;auto previous=detail::flow_totals();
 for(int t:o.in)flush(t);
 std::vector<std::unique_ptr<sc_event>> done;std::vector<sc_process_handle> workers;
 for(int w=0;w<2;++w){done.emplace_back(new sc_event);workers.push_back(sc_spawn([&,w,this]{matrix_worker(o,w,*done[w]);}));}
 for(auto& w:workers)if(!w.terminated())wait(w.terminated_event());
 matrix_backed.insert(o.out);
 std::string key=std::to_string(o.rows)+"x"+std::to_string(o.cols)+"x"+std::to_string(o.k)+"b"+std::to_string(o.batches)+"l"+std::to_string(o.layout);
 auto& shape=detail::data.shapes[key];++shape.calls;shape.wall+=now()-before;shape.tiles+=m_tiles-old_tiles;shape.commands+=m_commands-old_commands;
 auto current=detail::flow_totals();for(int f=0;f<detail::FLOWS;++f)detail::accumulate(shape.flows[f],detail::difference(current[f],previous[f]));
 require(mem.outstanding[0]==0&&mem.outstanding[1]==0,"native P outstanding ACK at barrier");
}
