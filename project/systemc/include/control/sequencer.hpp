#pragma once
#include "abi.hpp"
#include <optional>
namespace control {
// One instruction maximum per step; completion ingress is independent of WAIT.
// This is a clock-stepped contract model, NOT a calibrated RTL timing model.
class Sequencer {
    struct Event { uint16_t generation=0; uint8_t endpoint=0, lease=0; bool leased=false;
        enum State {Free, Pending, Done} state=Free; Completion completion{}; };
    struct Loop { uint16_t first=0; uint32_t left=0; };
    std::array<uint64_t,ProgramWords> program_{};
    std::array<bool,ProgramWords> loaded_{};
    std::array<Task,DescriptorCount> descriptors_{};
    std::array<Event,EventCount> events_{};
    std::array<bool,16> leases_{};
    std::array<Loop,4> loops_{};
    unsigned depth_=0;
    std::optional<Task> outgoing_;
    bool running_=false,ended_=false;
    Status fault_=Status::Ok;
    uint16_t pc_=0, error_pc_=0;
    uint16_t enabled_=0x7f; // R absent; enable requires a separately qualified endpoint
    void fail(Status s) { if(fault_==Status::Ok) {fault_=s;error_pc_=pc_;} running_=false; }
    bool pending() const { for(const auto &e:events_) if(e.state==Event::Pending) return true; return false; }
    void consume(unsigned slot) { auto &e=events_[slot]; if(e.leased) leases_[e.lease]=false;
        e.leased=false; e.state=Event::Free; }
  public:
    std::array<uint32_t,16> regs{};
    std::array<uint64_t,8> addresses{};
    uint64_t clocks=0, stalled=0, submitted=0, completed=0;
    bool load(unsigned index,uint64_t instruction) {
        if(running_ || outgoing_ || pending() || index>=ProgramWords) return false;
        program_[index]=instruction; loaded_[index]=true; return true;
    }
    bool descriptor(unsigned index,const Task& t) {
        if(running_ || outgoing_ || pending() || index>=DescriptorCount) return false;
        descriptors_[index]=t;return true;
    }
    bool start(unsigned entry=0) {
        if(running_ || outgoing_ || pending() || entry>=ProgramWords || !loaded_[entry]) return false;
        // Done slots must be consumed before restarting; no hidden tag reuse.
        for(const auto&e:events_) if(e.state!=Event::Free) return false;
        fault_=Status::Ok; ended_=false; depth_=0; pc_=entry; running_=true; return true;
    }
    bool idle() const {return !running_ && !outgoing_ && !pending();}
    bool reset_idle() {
        if(!idle()) return false;
        for(auto&e:events_) {e.state=Event::Free;e.leased=false;}
        leases_.fill(false);regs.fill(0);addresses.fill(0);depth_=0;pc_=0;
        fault_=Status::Ok;ended_=false;return true;
    }
    bool ended() const {return ended_;}
    Status fault() const {return fault_;}
    unsigned pc() const {return pc_;}
    unsigned error_pc() const {return error_pc_;}
    const std::optional<Task>& output() const {return outgoing_;}
    // A completion must only be delivered for a task accepted by its endpoint.
    // Stale/duplicate/wrong-source messages latch Protocol and never free a lease.
    void completion(const Completion& c) {
        auto&e=events_[c.tag&31];
        if(e.state!=Event::Pending || e.generation!=(c.tag>>5) || e.endpoint!=c.endpoint) {
            fail(Status::Protocol); return;
        }
        e.state=Event::Done;e.completion=c;++completed;
        if(c.status!=Status::Ok) fail(Status::Remote);
    }
    void step(bool task_ready=false) {
        ++clocks;
        if(outgoing_ && task_ready) outgoing_.reset();
        if(!running_) return;
        if(outgoing_) {++stalled;return;}
        if(pc_>=ProgramWords || !loaded_[pc_]) {fail(Status::Bounds);return;}
        const Instruction i{program_[pc_]};
        const unsigned rd=i.rd(),ra=i.ra(),rb=i.rb(),aux=i.aux();
        const uint32_t imm=i.imm();
        uint16_t next=pc_+1;
        switch(i.op()) {
        case Op::Nop:break;
        case Op::Movi:regs[rd]=imm;break;
        case Op::Add:regs[rd]=regs[ra]+regs[rb];break;
        case Op::Sub:regs[rd]=regs[ra]-regs[rb];break;
        case Op::And:regs[rd]=regs[ra]&regs[rb];break;
        case Op::Or:regs[rd]=regs[ra]|regs[rb];break;
        case Op::Shift:regs[rd]=(i.flags()&1)?regs[ra]>>(imm&31):regs[ra]<<(imm&31);break;
        case Op::SetAddr:
            if(rd>=8) {fail(Status::Bounds);return;}
            addresses[rd]=(uint64_t(aux)<<32)|imm;break;
        case Op::AddAddr: {
            if(rd>=8 || ra>=8) {fail(Status::Bounds);return;}
            const int64_t delta=imm<0x80000000u?int64_t(imm):int64_t(imm)-0x100000000LL;
            const int64_t sum=int64_t(addresses[ra])+delta;
            if(sum<0 || uint64_t(sum)>=1ULL<<40) {fail(Status::Bounds);return;}
            addresses[rd]=uint64_t(sum);break;
        }
        case Op::Loop:
            if(depth_==4 || !regs[ra]) {fail(Status::Bounds);return;}
            loops_[depth_++]={next,regs[ra]};break;
        case Op::EndLoop:
            if(!depth_) {fail(Status::Illegal);return;}
            if(--loops_[depth_-1].left) next=loops_[depth_-1].first;else --depth_;
            break;
        case Op::Branch:
            if(imm>=ProgramWords) {fail(Status::Bounds);return;}
            if(!i.flags() || regs[ra]) next=uint16_t(imm);
            break;
        case Op::DescWrite:
            if(aux>=8) {fail(Status::Bounds);return;}
            descriptors_[rd].words[aux]=regs[ra];break;
        case Op::Submit: {
            const unsigned ep=descriptors_[ra].endpoint();
            if(!(enabled_&(1u<<ep))) {fail(Status::Unavailable);return;}
            if((i.flags()&1) && leases_[aux&15]) {++stalled;return;}
            unsigned slot=0;while(slot<EventCount && events_[slot].state!=Event::Free) ++slot;
            if(slot==EventCount) {++stalled;return;}
            auto&e=events_[slot];e.generation=(e.generation+1)&2047;e.endpoint=ep;
            e.state=Event::Pending;e.leased=i.flags()&1;e.lease=aux&15;
            if(e.leased) leases_[e.lease]=true;
            const uint16_t tag=(e.generation<<5)|slot;
            outgoing_=descriptors_[ra];outgoing_->tag(tag);regs[rd]=tag;++submitted;break;
        }
        case Op::Wait: {
            const uint16_t tag=uint16_t(regs[ra]);auto&e=events_[tag&31];
            if(e.state==Event::Free || e.generation!=tag>>5) {fail(Status::Protocol);return;}
            if(e.state==Event::Pending) {++stalled;return;}
            regs[rd]=e.completion.result;consume(tag&31);break;
        }
        case Op::WaitAll:
        case Op::Fence:
            if(pending()) {++stalled;return;}
            for(unsigned s=0;s<EventCount;++s) if(events_[s].state==Event::Done) consume(s);
            break;
        case Op::LoadMeta:
            // Metadata is a real endpoint command, followed by WAIT into a GPR.
            // No direct host-memory read, and no implicit zero-latency bypass.
            fail(Status::Illegal);return;
        case Op::End:
            if(pending()) {++stalled;return;}
            for(unsigned s=0;s<EventCount;++s) if(events_[s].state==Event::Done) consume(s);
            ended_=true;running_=false;break;
        default:fail(Status::Illegal);return;
        }
        pc_=next;
    }
};
} // namespace control
