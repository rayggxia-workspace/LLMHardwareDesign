"""Derive a three-stage/true-S integration trial from the finite DMA oracle."""
from pathlib import Path
root=Path('project/experiments/mother_control_native/typed_dma')
s=(root/'typed.cpp').read_text(encoding='utf-8').replace('Vmc_dma_fabric_typed_p','Vmc_dma_stage64_joint')
s=s.replace('struct Held{', '''struct Stage {
 Packet p;int dst=0,first=0,words=0,requests=0,acks=0,capture=-1,raw_first=-1,last_ack=-1,raw_ack=-1;
 bool cancelled=false;
};
struct Held{''')
s=s.replace('int mode_accepts=0,native_legal=0,native_bad=0;', '''int mode_accepts=0,native_legal=0,native_bad=0,stage_done=0,stage_reject=0,stage_cancel=0,stage_reads=0;
uint8_t hold_done=0,cancel_pending=0;
std::array<uint32_t,3>cancel_tags{};
std::map<Key,Stage>stages;
std::array<int,3>peak_stages{};
int dst(const Packet&p){return int((p.tag>>1)%160)*4;}
int nwords(const Packet&p){return (p.tag&2)?2:4;}
int first_word(const Packet&p){return nwords(p)==2&&p.tag&4?2:0;}''')
s=s.replace('&&t.debug_beats==0&&t.debug_descriptors==0', '&&stages.empty()&&t.debug_beats==0&&t.debug_descriptors==0')
s=s.replace(' t.c_req_valid=0;zero(t.c_req_address', ''' t.dyn_cmd_valid=0;zero(t.dyn_cmd_address,6);zero(t.dyn_cmd_tag,3);t.dyn_cmd_dst=0;t.dyn_cmd_first=0;t.dyn_cmd_words=0;t.dyn_force_bad_channel=0;
 t.dyn_cancel_valid=cancel_pending;for(int c=0;c<3;++c)t.dyn_cancel_tag[c]=cancel_tags[c];
 t.dyn_done_ready=uint8_t((ideal?7U:rng()&7U)&~hold_done);
 t.block_S_req=uint8_t(block_clients?7U:(ideal?0U:(rng()&rng())&7U));
 t.block_S_ack=uint8_t(ideal?0U:(rng()&rng())&7U);
 t.c_req_valid=0;zero(t.c_req_address''')
a=s.index('  if(!queues[size_t(c)].empty()){')
b=s.index('  if(!closes',a)
s=s[:a]+'''  if(!queues[size_t(c)].empty()){
   auto&p=queues[size_t(c)].front();
   if(c<3&&((t.p_mode_active>>c)&1U)){
    t.dyn_cmd_valid|=uint8_t(1U<<c);set64(t.dyn_cmd_address,c*2,p.address);t.dyn_cmd_tag[c]=p.tag;
    t.dyn_cmd_dst|=uint32_t(dst(p))<<(10*c);t.dyn_cmd_words|=uint16_t(nwords(p)<<(3*c));
    t.dyn_cmd_first|=uint8_t(first_word(p)<<(2*c));t.dyn_force_bad_channel|=uint8_t((p.channel^int((p.address>>11)&1U))<<c);
   }else{
    t.c_req_valid|=uint16_t(1U<<c);set64(t.c_req_address,c*2,p.address);t.c_req_tag[c]=p.tag;
    t.c_req_channel|=uint16_t(p.channel<<c);t.c_req_record_beats|=uint64_t(p.length)<<(5*c);
   }
  }
'''+s[b:]
s=s.replace('  uint8_t mfire=', '''  for(int c=0;c<3;++c){
   if((t.dyn_cmd_admit>>c)&1U){
    auto p=queues[size_t(c)].front();Key key={c,p.tag};need(!stages.count(key),"duplicate stage admission");
    Stage v;v.p=p;v.dst=dst(p);v.first=first_word(p);v.words=nwords(p);stages.emplace(key,v);
    int live=0;for(auto&[k,sv]:stages){(void)sv;live+=k.first==c;}
    peak_stages[c]=std::max(peak_stages[c],live);need(live<=2,"stage owner over capacity");
    trace<<"STAGE_CMD,"<<cycle<<","<<c<<","<<p.tag<<","<<v.dst<<","<<v.first<<","<<v.words<<"\\n";
   }
   if(((t.dyn_cancel_valid&t.dyn_cancel_ready)>>c)&1U){
    auto tag=cancel_tags[c];need(stages.count({c,tag}),"cancel missing admitted owner");stages.at({c,tag}).cancelled=true;
    cancel_pending&=uint8_t(~(1U<<c));trace<<"STAGE_CANCEL,"<<cycle<<","<<c<<","<<tag<<"\\n";
   }
   if(((t.p_mode_active&t.c_rsp_valid)>>c)&1U){
    auto tag=t.c_rsp_tag[c];need(stages.count({c,tag}),"real raw has no matching stage");auto&v=stages.at({c,tag});
    if(v.raw_first<0){v.raw_first=cycle;need(v.capture>=0&&v.capture<cycle,"raw before backend landing");
     trace<<"STAGE_RAW_FIRST,"<<cycle<<","<<c<<","<<tag<<"\\n";}
    if((t.mon_s_ack>>c)&1U){need(v.acks<v.requests,"orphan true SACK");++v.acks;v.last_ack=cycle;
     trace<<"STAGE_SACK,"<<cycle<<","<<c<<","<<tag<<","<<v.acks<<"\\n";}
    if((t.mon_s_req>>c)&1U){
     need(v.requests<v.words&&v.requests-v.acks<2,"S req bounds");
     int addr=int((t.mon_s_address>>(c*10))&1023U);need(addr==v.dst+v.requests,"true S write address");
     for(int q=0;q<4;++q)need(t.mon_s_data[c*4+q]==v.p.data[(v.first+v.requests)*4+q],"true S write payload");
     ++v.requests;trace<<"STAGE_SREQ,"<<cycle<<","<<c<<","<<tag<<","<<addr<<"\\n";
    }
    if((t.mon_raw_retire>>c)&1U){
     need(v.acks==v.requests&&(v.last_ack<cycle)&&v.acks==(v.cancelled?0:v.words),"raw release before true S drain");
     v.raw_ack=cycle;trace<<"STAGE_RAW_ACK,"<<cycle<<","<<c<<","<<tag<<"\\n";
    }
   }else need(!((t.mon_s_req|t.mon_s_ack|t.mon_raw_retire)&(1<<c)),"S/response owner absent");
   if(((t.dyn_done_valid&t.dyn_done_ready)>>c)&1U){
    auto tag=t.dyn_done_tag[c];need(stages.count({c,tag}),"unknown stage terminal");auto v=stages.at({c,tag});
    bool e=(t.dyn_done_error>>c)&1U,x=(t.dyn_done_cancelled>>c)&1U;int mask=(t.dyn_done_mask>>(4*c))&15;
    need(e==v.p.bad&&x==v.cancelled&&mask==(e||x?0:(1<<v.words)-1),"stage terminal status/word proof");
    if(e){need(v.capture<0&&v.raw_first<0&&v.requests==0,"rejected stage consumed payload");++stage_reject;}
    else {need(v.raw_ack>=0&&v.raw_ack<cycle,"terminal before true raw retire");if(x)++stage_cancel;}
    trace<<"STAGE_DONE,"<<cycle<<","<<c<<","<<tag<<","<<mask<<","<<int(e)<<","<<int(x)<<"\\n";
    stages.erase({c,tag});++stage_done;
   }
  }
  uint8_t mfire=''')
s=s.replace('ready=(t.c_rsp_ready>>c)&1U', 'ready=(t.mon_rsp_ready>>c)&1U')
s=s.replace('if(((t.c_req_valid&t.c_req_ready)>>c)&1U)', 'if((((t.c_req_valid&t.c_req_ready)|(t.dyn_cmd_valid&t.dyn_cmd_ready))>>c)&1U)')
s=s.replace('if(!ext.at(h.tag).delivered)ext.at(h.tag).delivered=true;', '''if(!ext.at(h.tag).delivered){auto &p=ext.at(h.tag).p;
      if(stages.count({p.client,p.tag})){auto&v=stages.at({p.client,p.tag});v.capture=cycle;
       trace<<"STAGE_CAPTURE,"<<cycle<<","<<p.client<<","<<p.tag<<"\\n";}
      ext.at(h.tag).delivered=true;}''')
a=s.index('int main(')
s=s[:a]+'''void read_words(const Packet&p){
 int c=p.client;uint8_t bit=uint8_t(1U<<c);need(stages.empty(),"readback while stage still owns S");
 t.rd_mode=bit;t.rd_rsp_ready=bit;
 for(int j=0;j<nwords(p);++j){
  t.rd_address=uint32_t(dst(p)+j)<<(c*10);t.rd_valid=bit;t.eval();
  wait([&]{return (t.rd_ready&bit)!=0;},"actual S read request");tick();t.rd_valid=0;t.eval();
  wait([&]{return (t.rd_rsp_valid&bit)!=0;},"actual S read response");
  for(int q=0;q<4;++q)need(t.rd_data[c*4+q]==p.data[(first_word(p)+j)*4+q],"actual bank readback mismatch");
  tick();++stage_reads;
 }
 t.rd_mode=0;t.rd_rsp_ready=0;
}
'''+s[a:]
s=s.replace('t.reset=1;for(int n=0;', 't.rd_mode=0;t.rd_valid=0;t.rd_address=0;t.rd_rsp_ready=0;t.reset=1;for(int n=0;')
s=s.replace('mode_pending=1;mode_choice=0;client_drained=6;', 'mode_pending=1;mode_choice=0;hold_done=1;')
s=s.replace('block_clients=false;quiet();\n for(int i=0;i<8;++i)', '''block_clients=false;
 wait([]{return expected.empty()&&ext.empty()&&t.debug_beats==0&&t.debug_descriptors==0&&(t.dyn_done_valid&1);},"actual raw/S drain with DONE retained");
 for(int i=0;i<8;++i)''')
s=s.replace('client_drained=7;wait([]{return mode_pending==0;}', 'hold_done=0;wait([]{return mode_pending==0;}')
s=s.replace(' submit_bad(packet(2,11001,0,2,0));','')
s=s.replace('native_legal==433&&native_bad==5','native_legal==433&&native_bad==4')
s=s.replace('native_legal==434&&native_bad==6','native_legal==434&&native_bad==5')
s=s.replace(' set_modes(7,0);', ''' for(int c=0;c<3;++c)read_words(one(c,11243,(143+c)&1));
 // Cancel a stage before raw arrives. The request still issues/returns,
 // but it produces no S write and cannot bypass the held raw drain.
 block_backend=true;int base_legal=native_legal;auto cp=one(0,16000,1);queues[0].push_back(cp);
 wait([&]{return native_legal==base_legal+1;},"admitted real early cancel");
 cancel_tags[0]=cp.tag;cancel_pending=1;
 wait([]{return cancel_pending==0;},"stage exact early cancel");
 block_backend=false;quiet();need(stage_cancel==1,"expected one drained stage cancel");
 set_modes(7,0);''')
s=s.replace('need(mode_accepts==8&&t.p_mode_active==0,', 'need(stage_done==440&&stage_reject==5&&stage_reads==6&&peak_stages[0]==2&&peak_stages[1]==2&&peak_stages[2]==2,"actual three-stage terminal/ownership/readback coverage");\n need(mode_accepts==8&&t.p_mode_active==0,')
s=s.replace('<<" mode_accepts="<<mode_accepts', '<<" stage_done="<<stage_done<<" stage_rejected="<<stage_reject<<" stage_cancel="<<stage_cancel<<" true_S_reads="<<stage_reads<<" mode_accepts="<<mode_accepts')
s=s.replace('void tick(){', '''void advance(uint64_t goal){
 while(t.eventsPending()&&t.nextTimeSlot()<goal){
  Verilated::timeInc(t.nextTimeSlot()-Verilated::time());t.eval();
 }
 Verilated::timeInc(goal-Verilated::time());
}
void tick(){''')
s=s.replace(' t.clk=1;t.eval();t.clk=0;t.eval();++cycle;', ''' advance(Verilated::time()+5000);t.clk=1;t.eval();
 advance(Verilated::time()+5000);t.clk=0;t.eval();++cycle;''')
(root/'joint.cpp').write_text(s,encoding='utf-8')

