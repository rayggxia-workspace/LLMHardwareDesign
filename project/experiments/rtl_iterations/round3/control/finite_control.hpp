#pragma once
// Data-free cycle model of r3_m_finite.sv, not a matrix numerical oracle.
// Observe combinational outputs before the edge; tick applies NBA-equivalent
// updates from the same old state. SRAM timing is supplied through Inputs.
#include <array>
#include <cstdint>
#include <stdexcept>

namespace finite_m {
constexpr const char* rtl_sha256="783089199218a48c3c6cfe78a67509dba1ee95ea23858f7c7e79737e7911510c";
struct Command {
 unsigned ctx=0,tag=0,ki=0,total=0,k=0,n=0,shift=0;
 bool first=false,last=false;
 unsigned a=0,b=0,out=0;
};
struct Inputs {
 bool reset=false,command_valid=false,read_ready=false,read_response=false;
 bool write_ready=false,write_ack=false,done_ready=true;
 Command command{};
};
struct Outputs {
 bool command_ready=false,descriptor_ok=false,done_valid=false,done_error=false,done_last=false;
 unsigned done_ctx=0,done_tag=0,done_next=0;
 bool read_valid=false,read_take=false,write_valid=false,write_take=false;
 unsigned read_address=0,write_address=0;
 bool leaf_valid=false,leaf_ready=false,leaf_fire=false,commit=false,final_capture=false,core_advance_active=false;
 unsigned leaf_ctx=0,leaf_end=0,leaf_sequence=0,commit_ctx=0,commit_end=0;
 unsigned reservations=0,reads_outstanding=0,live_buffers=0;
 bool command_fire=false,read_fire=false,read_pop=false,write_fire=false,write_pop=false,completion_pop=false;
 int free_id=0,load_id=0,ready_id=0,allocate_id=0;
 bool free_found=false,load_found=false,ready_found=false;
};
class Model {
 enum {EMPTY=0,LOADING=1,READY=2,W_IDLE=0,W_ACTIVE=1,W_HOLD=2};
 struct Packet {
  unsigned state=EMPTY,sequence=0,ctx=0,reservation=0,end=0,k=0,n=0,shift=0;
  unsigned a=0,b=0,issued=0,received=0,needed=0;
  bool first=false,last=false;
 };
 struct Context {
  bool active=false,closing=false;
  unsigned tag=0,reserved=0,committed=0,total=0,n=0,shift=0,out=0;
 };
 struct Completion {
  bool valid=false,error=false,last=false,release=false;
  unsigned ctx=0,tag=0,next=0;
 };
 struct Pipe {
  bool valid=false,last=false;
  unsigned ctx=0,reservation=0,end=0;
 };
 int buffers_;
 std::array<Packet,2> packets_{};
 std::array<Context,8> contexts_{};
 std::array<Completion,8> completions_{};
 std::array<Pipe,3> pipe_{};
 unsigned reservation_head_=0,reservation_tail_=0,reservation_count_=0,next_sequence_=0;
 unsigned read_head_=0,read_tail_=0,read_count_=0;
 std::array<unsigned,2> read_buffer_{},read_part_{};
 unsigned write_phase_=W_IDLE,write_reservation_=0,write_issued_=0,write_acked_=0,write_base_=0;
 bool core_out_valid_=false;
 unsigned core_out_ctx_=0,result_reservation_=0;

 static bool overlap(unsigned a0,unsigned a1,unsigned b0,unsigned b1){return a0<b1&&b0<a1;}
 bool descriptor_ok(const Command& c) const {
  if(c.ctx>=8||c.k<1||c.k>16||c.n<1||c.n>8||c.total==0||c.total>65535||c.ki>65535||
     c.ki+c.k>65535||c.ki+c.k>c.total||c.last!=(c.ki+c.k==c.total)||
     c.shift>63||(c.a%64)!=0||(c.out%16)!=0||c.a+64>16384||c.b+c.k*c.n>16384||c.out+32>16384){return false;}
  const auto& old=contexts_[c.ctx];
  if(c.first){if(c.ki!=0||old.active){return false;}}
  else if(!old.active||old.closing||c.ki!=old.reserved||c.tag!=old.tag||c.total!=old.total||
          c.n!=old.n||c.shift!=old.shift||c.out!=old.out){return false;}
  if(overlap(c.a,c.a+64,c.out,c.out+32)||overlap(c.b,c.b+c.k*c.n,c.out,c.out+32)){return false;}
  for(const auto& x:contexts_){if(x.active){
   if(overlap(c.a,c.a+64,x.out,x.out+32)||overlap(c.b,c.b+c.k*c.n,x.out,x.out+32)||
      (c.first&&overlap(c.out,c.out+32,x.out,x.out+32))){return false;}
  }}
  for(int slot=0;slot<buffers_;++slot){const auto& x=packets_[slot];if(x.state!=EMPTY){
   if(overlap(c.out,c.out+32,x.a,x.a+64)||overlap(c.out,c.out+32,x.b,x.b+x.k*x.n)){return false;}
  }}
  return true;
 }
public:
 explicit Model(int buffers):buffers_(buffers){if(buffers!=1&&buffers!=2){throw std::invalid_argument("finite M supports BUF1/2");}}
 int buffers() const{return buffers_;}
 bool empty() const{return reservation_count_==0;}
 unsigned committed(unsigned ctx) const{return contexts_.at(ctx).committed;}
 unsigned reserved(unsigned ctx) const{return contexts_.at(ctx).reserved;}
 bool active(unsigned ctx) const{return contexts_.at(ctx).active;}
 Outputs observe(const Inputs& in) const {
  const auto& c=in.command;
  if(c.ctx>7||c.ki>65535||c.total>65535||c.k>31||c.n>15||c.shift>63||c.a>16383||c.b>16383||c.out>16383){
   throw std::invalid_argument("input exceeds RTL port width");
  }
  Outputs o{};o.reservations=reservation_count_;o.reads_outstanding=read_count_;
  for(int slot=0;slot<buffers_;++slot){const auto& p=packets_[slot];
   if(p.state!=EMPTY){++o.live_buffers;}
   if(p.state==EMPTY&&!o.free_found){o.free_found=true;o.free_id=slot;}
   if(p.state==LOADING&&p.issued<p.needed&&(!o.load_found||
      static_cast<std::int32_t>(p.sequence-packets_[o.load_id].sequence)<0)){o.load_found=true;o.load_id=slot;}
   if(p.state==READY&&(!o.ready_found||
      static_cast<std::int32_t>(p.sequence-packets_[o.ready_id].sequence)<0)){o.ready_found=true;o.ready_id=slot;}
  }
  const auto& head=completions_[reservation_head_];
  o.done_valid=!in.reset&&reservation_count_!=0&&head.valid;
  o.done_ctx=head.ctx;o.done_tag=head.tag;o.done_next=head.next;o.done_last=head.last;o.done_error=head.error;
  o.completion_pop=o.done_valid&&in.done_ready;
  o.leaf_ready=!in.reset&&(!core_out_valid_||write_phase_==W_IDLE);
  const auto& ready=packets_[o.ready_id];
  const bool frontier=contexts_[ready.ctx].committed==ready.end-ready.k||
    (pipe_[1].valid&&pipe_[1].ctx==ready.ctx&&pipe_[1].end==ready.end-ready.k);
  o.leaf_valid=!in.reset&&o.ready_found&&frontier;o.leaf_fire=o.leaf_valid&&o.leaf_ready;
  o.core_advance_active=o.leaf_ready&&(o.leaf_fire||pipe_[0].valid||pipe_[1].valid||
      (pipe_[2].valid&&pipe_[2].last)||core_out_valid_);
  o.leaf_ctx=ready.ctx;o.leaf_end=ready.end;o.leaf_sequence=ready.sequence;
  o.commit=o.leaf_ready&&pipe_[1].valid;o.commit_ctx=pipe_[1].ctx;o.commit_end=pipe_[1].end;
  o.final_capture=!in.reset&&core_out_valid_&&write_phase_==W_IDLE;
  o.allocate_id=o.free_found?o.free_id:o.ready_id;
  o.descriptor_ok=descriptor_ok(in.command);
  o.command_ready=!in.reset&&(reservation_count_<8||o.completion_pop)&&(!o.descriptor_ok||o.free_found||o.leaf_fire);
  o.command_fire=in.command_valid&&o.command_ready;
  o.write_valid=!in.reset&&write_phase_==W_ACTIVE&&write_issued_<2;
  o.write_address=(write_base_+write_issued_)&1023;
  o.write_take=!in.reset&&write_phase_==W_ACTIVE&&write_acked_<write_issued_;
  o.write_fire=o.write_valid&&in.write_ready;o.write_pop=o.write_take&&in.write_ack;
  o.read_take=!in.reset&&read_count_!=0;o.read_pop=o.read_take&&in.read_response;
  o.read_valid=!in.reset&&o.load_found&&!o.write_valid&&(read_count_<2||o.read_pop);
  const auto& load=packets_[o.load_id];
  o.read_address=load.issued==0?load.a/64:(load.b/64+load.issued-1)&255;
  o.read_fire=o.read_valid&&in.read_ready;
  return o;
 }
 void tick(const Inputs& in){
  if(in.reset){*this=Model(buffers_);return;}
  const Outputs o=observe(in);Model next=*this;
  if(o.completion_pop){
   next.completions_[reservation_head_].valid=false;next.reservation_head_=(reservation_head_+1)&7;
   const auto& old=completions_[reservation_head_];
   if(old.release){auto& c=next.contexts_[old.ctx];c.active=false;c.closing=false;c.reserved=0;c.committed=0;next.write_phase_=W_IDLE;}
  }
  if(o.command_fire&&!o.completion_pop){next.reservation_count_=reservation_count_+1;}
  if(!o.command_fire&&o.completion_pop){next.reservation_count_=reservation_count_-1;}
  if(o.leaf_ready){
   next.core_out_valid_=pipe_[2].valid&&pipe_[2].last;
   if(next.core_out_valid_){next.core_out_ctx_=pipe_[2].ctx;}
   next.pipe_[2]=pipe_[1];next.pipe_[1]=pipe_[0];next.pipe_[0].valid=o.leaf_fire;
   if(o.leaf_fire){const auto& p=packets_[o.ready_id];next.pipe_[0]={true,p.last,p.ctx,p.reservation,p.end};}
   if(pipe_[1].valid){
    next.contexts_[pipe_[1].ctx].committed=pipe_[1].end;
    next.completions_[pipe_[1].reservation].next=pipe_[1].end;
    if(!pipe_[1].last){next.completions_[pipe_[1].reservation].valid=true;}
   }
   if(pipe_[2].valid){next.result_reservation_=pipe_[2].reservation;}
  }
  if(o.leaf_fire){next.packets_[o.ready_id].state=EMPTY;}
  if(o.read_fire){
   next.read_buffer_[read_tail_]=static_cast<unsigned>(o.load_id);next.read_part_[read_tail_]=packets_[o.load_id].issued;
   next.read_tail_=read_tail_^1;next.packets_[o.load_id].issued=packets_[o.load_id].issued+1;
  }
  if(o.read_pop){
   const unsigned slot=read_buffer_[read_head_];const auto& old=packets_[slot];
   next.packets_[slot].received=old.received+1;
   if(old.received+1==old.needed){next.packets_[slot].state=READY;}
   next.read_head_=read_head_^1;
  }
  if(o.read_fire&&!o.read_pop){next.read_count_=read_count_+1;}
  if(!o.read_fire&&o.read_pop){next.read_count_=read_count_-1;}
  if(o.final_capture){
   next.write_reservation_=result_reservation_;next.write_base_=contexts_[core_out_ctx_].out/16;
   next.write_issued_=0;next.write_acked_=0;next.write_phase_=W_ACTIVE;
   next.completions_[result_reservation_].release=true;next.completions_[result_reservation_].error=false;
  }
  if(o.write_fire){next.write_issued_=write_issued_+1;}
  if(o.write_pop){
   next.write_acked_=write_acked_+1;
   if(write_acked_==1){next.write_phase_=W_HOLD;next.completions_[write_reservation_].valid=true;}
  }
  if(o.command_fire){
   const auto& c=in.command;next.reservation_tail_=(reservation_tail_+1)&7;
   auto& completion=next.completions_[reservation_tail_];
   completion.ctx=c.ctx;completion.tag=c.tag;completion.last=c.last;completion.release=false;
   completion.error=!o.descriptor_ok;completion.next=contexts_[c.ctx].reserved;completion.valid=!o.descriptor_ok;
   if(o.descriptor_ok){
    auto& p=next.packets_[o.allocate_id];p.state=LOADING;p.sequence=next_sequence_;next.next_sequence_=next_sequence_+1;
    p.ctx=c.ctx;p.reservation=reservation_tail_;p.end=c.ki+c.k;p.k=c.k;p.n=c.n;p.shift=c.shift;
    p.first=c.first;p.last=c.last;p.a=c.a;p.b=c.b;p.issued=0;p.received=0;p.needed=1+((c.b%64+c.k*c.n+63)/64);
    auto& context=next.contexts_[c.ctx];context.reserved=c.ki+c.k;if(c.last){context.closing=true;}
    if(c.first){context.active=true;context.tag=c.tag;context.committed=0;context.total=c.total;context.n=c.n;context.shift=c.shift;context.out=c.out;}
   }
  }
  if(next.reservation_count_>8||next.read_count_>2){throw std::runtime_error("finite M resource overflow");}
  *this=next;
 }
};
} // namespace finite_m
