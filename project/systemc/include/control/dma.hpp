#pragma once
#include "abi.hpp"
#include <optional>
namespace control {
struct Burst {
    uint64_t address=0;
    uint16_t local_word=0;
    uint8_t beats=0,id=0;
    uint16_t last_strobe=65535;
    bool write=false;
};
inline std::ostream& operator<<(std::ostream& s,const Burst& b) {return s<<"burst("<<b.address<<","<<unsigned(b.beats)<<")";}
struct DmaCommand {DmaDescriptor descriptor{};uint16_t tag=0;};
inline std::ostream& operator<<(std::ostream& s,const DmaCommand& c) {return s<<"dma("<<c.tag<<")";}
struct BurstAck {unsigned id=0;bool error=false;};
inline std::ostream& operator<<(std::ostream& s,const BurstAck& c) {return s<<"ack("<<c.id<<")";}
// Address/credit contract model. Payload transport is deliberately not hidden
// here: acknowledge() is called only after actual S writes / AXI B completion.
// There are two descriptor entries and two outstanding bursts, each <=16 beats.
// Thus no read side can reserve more than the explicit 32-word payload FIFO.
// This is NOT yet an AXI channel simulation or an external DRAM/PHY model.
class DmaPlanner {
    struct Transfer {DmaDescriptor d{};uint16_t tag=0;unsigned row=0,offset=0;
        bool valid=false,all_issued=false,failed=false;unsigned pending=0;};
    std::array<Transfer,2> queue_{};
    struct Flight {bool used=false;unsigned owner=0,beats=0;};
    std::array<Flight,2> flights_{};
    unsigned head_=0,tail_=0,size_=0,reserved_=0;
  public:
    uint64_t burst_count=0,word_count=0;
    bool ready() const {return size_<2;}
    bool submit(const DmaDescriptor& d,uint16_t tag) {
        if(!ready() || d.validate()!=Status::Ok) return false;
        queue_[tail_]={d,tag,0,0,true,false,false,0};tail_^=1;++size_;return true;
    }
    unsigned reserved() const {return reserved_;}
    std::optional<Burst> peek() const {
        if(!size_) return {};
        const auto&t=queue_[head_];if(t.all_issued || t.failed) return {};
        unsigned id=0;while(id<2 && flights_[id].used) ++id;if(id==2) return {};
        Burst b;b.address=t.d.external+uint64_t(t.row)*t.d.external_stride+t.offset;
        b.local_word=(t.d.s_offset+t.row*t.d.s_stride+t.offset)/16;b.id=id;b.write=t.d.write;
        const unsigned remaining=(t.d.row_bytes-t.offset+15)/16;
        // AXI INCR bursts cannot cross a 4KiB boundary.
        const unsigned boundary=(4096-unsigned(b.address&4095))/16;
        const unsigned n=remaining<16?remaining:16;
        b.beats=uint8_t(n<boundary?n:boundary);
        if(t.offset+b.beats*16>=t.d.row_bytes && t.d.row_bytes%16)
            b.last_strobe=uint16_t((1u<<(t.d.row_bytes%16))-1);
        if(reserved_+b.beats>32) return {};
        return b;
    }
    bool issue() {
        const auto b=peek();if(!b) return false;
        auto&t=queue_[head_];flights_[b->id]={true,head_,b->beats};
        ++t.pending;reserved_+=b->beats;++burst_count;word_count+=b->beats;
        t.offset+=b->beats*16;
        if(t.offset>=t.d.row_bytes) {t.offset=0;if(++t.row==t.d.rows) t.all_issued=true;}
        return true;
    }
    bool acknowledge(unsigned id,bool error=false) {
        if(id>=2 || !flights_[id].used) return false;
        auto&f=flights_[id];auto&t=queue_[f.owner];
        t.failed|=error;--t.pending;reserved_-=f.beats;f.used=false;return true;
    }
    std::optional<Completion> completion() const {
        if(!size_) return {};
        const auto&t=queue_[head_];if(t.pending || !(t.all_issued||t.failed)) return {};
        Completion c;c.tag=t.tag;c.endpoint=Endpoint::D;
        c.status=t.failed?Status::Remote:Status::Ok;
        c.result=t.failed?0:t.d.row_bytes*t.d.rows;return c;
    }
    bool take_completion() {
        if(!completion()) return false;
        queue_[head_]={};head_^=1;--size_;return true;
    }
};
} // namespace control
