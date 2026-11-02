#pragma once
#include "sequencer.hpp"
#include "dma.hpp"
#include <systemc>
namespace control {
// Testbench loads core while idle, then enables the clocked module. Bounded
// channels retain an unaccepted task. Completion ingress is polled every edge,
// including WAIT and output backpressure; no blocking write stalls that path.
class C : public sc_core::sc_module {
    void run() {
        while(true) {
            wait(clk.posedge_event());
            Completion done;
            if(completions.nb_read(done)) core.completion(done);
            bool accepted=false;
            if(core.output()) accepted=tasks.nb_write(*core.output());
            core.step(accepted);
        }
    }
  public:
    Sequencer core;
    sc_core::sc_in<bool> clk{"clk"};
    sc_core::sc_fifo_out<Task> tasks{"tasks"};
    sc_core::sc_fifo_in<Completion> completions{"completions"};
    SC_HAS_PROCESS(C);
    explicit C(sc_core::sc_module_name name):sc_module(name) {SC_THREAD(run);}
};
// Endpoint packet ingress: exactly eight accepted 32-bit flits, then one
// 256-bit task. A held task prevents packet overwrite. Reset is idle-only.
class PacketIngress {
    Task task_{};
    unsigned count_=0;
  public:
    bool ready() const {return count_<8;}
    bool push(uint32_t word) {if(!ready()) return false;task_.words[count_++]=word;return true;}
    bool valid() const {return count_==8;}
    const Task& value() const {return task_;}
    bool pop() {if(!valid()) return false;count_=0;return true;}
};
class DModule : public sc_core::sc_module {
    std::optional<Completion> rejected_;
    void run() {
        while(true) {
            wait(clk.posedge_event());
            BurstAck ack;
            if(acknowledgements.nb_read(ack) && !core.acknowledge(ack.id,ack.error))
                SC_REPORT_ERROR("D", "unsolicited burst acknowledgement");
            if(rejected_) {
                if(completions.nb_write(*rejected_)) rejected_.reset();
            } else if(auto done=core.completion()) {
                if(completions.nb_write(*done)) core.take_completion();
            }
            if(!rejected_ && core.ready()) {
                DmaCommand command;
                if(commands.nb_read(command) && !core.submit(command.descriptor,command.tag)) {
                    Completion c;c.tag=command.tag;c.endpoint=Endpoint::D;c.status=Status::Bounds;
                    rejected_=c;
                }
            }
            if(auto burst=core.peek()) if(bursts.nb_write(*burst)) core.issue();
        }
    }
  public:
    DmaPlanner core;
    sc_core::sc_in<bool> clk{"clk"};
    sc_core::sc_fifo_in<DmaCommand> commands{"commands"};
    sc_core::sc_fifo_out<Burst> bursts{"bursts"};
    sc_core::sc_fifo_in<BurstAck> acknowledgements{"acknowledgements"};
    sc_core::sc_fifo_out<Completion> completions{"completions"};
    SC_HAS_PROCESS(DModule);
    explicit DModule(sc_core::sc_module_name name):sc_module(name) {SC_THREAD(run);}
};
} // namespace control
