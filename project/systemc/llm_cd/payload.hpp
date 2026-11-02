// Clocked C/D contract experiment; assumed latency, not RTL timing.
#pragma once
#include "control/modules.hpp"
#include "blocks/s.hpp"
#include <algorithm>
#include <vector>
#include <stdexcept>
#include <iostream>
namespace llm_cd {
class Payload : public sc_core::sc_module {
    sc_core::sc_clock clock_{"clock",1,sc_core::SC_NS};
    control::C c_{"c"};
    control::DModule d_{"d"};
    sc_core::sc_fifo<control::Task> tasks_{"tasks",2};
    sc_core::sc_fifo<control::Completion> done_{"done",2};
    sc_core::sc_fifo<control::DmaCommand> commands_{"commands",2};
    sc_core::sc_fifo<control::Burst> bursts_{"bursts",2};
    sc_core::sc_fifo<control::BurstAck> acks_{"acks",2};
    blocks::SEngine storage_;
    // Two finite staging windows, input and output; never a whole Tensor.
    std::array<uint8_t,32768> external_{};
    sc_core::sc_mutex ownership_;
    void dispatch() {
        while(true) {
            auto task=tasks_.read();control::DmaDescriptor descriptor;
            if(control::DmaDescriptor::unpack(task,descriptor)!=control::Status::Ok)
                throw std::runtime_error("C/D descriptor rejected");
            commands_.write({descriptor,task.tag()});
        }
    }
    void transfer() {
        while(true) {
            auto burst=bursts_.read();bool error=false;
            if(burst.address+uint64_t(burst.beats)*16>external_.size()) error=true;
            for(unsigned i=0;i<burst.beats&&!error;++i) {
                blocks::SCommand command;command.address=burst.local_word+i;
                command.op=burst.write?blocks::SCommand::Op::Read:blocks::SCommand::Op::Write;
                auto address=burst.address+i*16;
                if(!burst.write)for(unsigned byte=0;byte<16;++byte)
                    command.data[byte/8]|=uint64_t(external_[address+byte])<<(byte%8*8);
                // A real model S operation and response precede ACK/credit release.
                auto result=storage_.execute(command);
                if(result.error) {error=true;break;}
                if(burst.write)for(unsigned byte=0;byte<16;++byte)
                    if(i+1<burst.beats || (burst.last_strobe&(1u<<byte)))
                        external_[address+byte]=uint8_t(result.bits[byte/8]>>(byte%8*8));
                sc_core::wait(1,sc_core::SC_NS);++words;
            }
            sc_core::wait(2,sc_core::SC_NS);++burst_count;
            acks_.write({burst.id,error});
        }
    }
    void program(size_t count) {
        control::DmaDescriptor load;load.row_bytes=uint32_t(count);load.rows=1;
        auto store=load;store.external=16384;store.write=true;
        if(!c_.core.descriptor(0,load.pack())||!c_.core.descriptor(1,store.pack()))
            throw std::runtime_error("C descriptor load while busy");
        using control::Op;using control::encode;
        const std::array<uint64_t,5> code{{encode(Op::Submit,0,0,0,1,0),
            encode(Op::Wait,1,0),encode(Op::Submit,0,1,0,1,0),encode(Op::Wait,1,0),encode(Op::End)}};
        for(unsigned i=0;i<code.size();++i)if(!c_.core.load(i,code[i]))throw std::runtime_error("C program load");
        if(!c_.core.start())throw std::runtime_error("C start");
        unsigned watchdog=0;
        while(!c_.core.ended()) {
            sc_core::wait(1,sc_core::SC_NS);
            if(c_.core.fault()!=control::Status::Ok)throw std::runtime_error("C completion fault");
            if(++watchdog>100000)throw std::runtime_error("C/D watchdog");
        }
        if(d_.core.reserved()!=0)throw std::runtime_error("D credit leak");
        ++windows;
    }
  public:
    uint64_t words=0,burst_count=0,windows=0;
    SC_HAS_PROCESS(Payload);
    explicit Payload(sc_core::sc_module_name name):sc_module(name) {
        c_.clk(clock_);c_.tasks(tasks_);c_.completions(done_);
        d_.clk(clock_);d_.commands(commands_);d_.completions(done_);d_.bursts(bursts_);d_.acknowledgements(acks_);
        SC_THREAD(dispatch);SC_THREAD(transfer);
    }
    ~Payload() override {
        std::cout << "CD_EXECUTED windows=" << windows << " words=" << words
                  << " bursts=" << burst_count << " C_submitted=" << c_.core.submitted
                  << " C_completed=" << c_.core.completed << "\n";
    }
    std::vector<uint8_t> exchange(const std::vector<uint8_t>& input) {
        ownership_.lock();std::vector<uint8_t> output;output.reserve(input.size());
        for(size_t offset=0;offset<input.size();offset+=16384) {
            auto count=std::min(size_t(16384),input.size()-offset);
            external_.fill(0);std::copy_n(input.begin()+offset,count,external_.begin());
            program(count);
            output.insert(output.end(),external_.begin()+16384,external_.begin()+16384+count);
        }
        ownership_.unlock();
        if(input!=output)throw std::runtime_error("C/D actual payload mismatch");
        return output;
    }
};
} // namespace llm_cd
