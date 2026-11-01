#include "control/modules.hpp"
#include <cstdlib>
#include <iostream>
#include <vector>
using namespace control;
static uint64_t checks=0;
static void require(bool v,const char* why) {++checks;if(!v){std::cerr<<why<<"\n";std::exit(1);}}
static void scalar_tests() {
    Sequencer c;
    const std::array<uint64_t,9> p{{encode(Op::Movi,0,0,0,0,0,3),encode(Op::Movi,1,0,0,0,0,7),
        encode(Op::Loop,0,0),encode(Op::Add,2,2,1),encode(Op::EndLoop),
        encode(Op::SetAddr,1,0,0,0,0xff,0xfffffff0),encode(Op::AddAddr,1,1,0,0,0,15),
        encode(Op::Fence),encode(Op::End)}};
    for(unsigned i=0;i<p.size();++i) require(c.load(i,p[i]),"program load");
    require(!c.load(256,0),"program overflow");require(c.start(),"start");
    require(!c.load(0,0),"busy load rejection");
    for(unsigned i=0;i<100 && !c.idle();++i)c.step();
    require(c.ended() && c.fault()==Status::Ok,"scalar end");
    require(c.regs[2]==21 && c.addresses[1]==(1ULL<<40)-1,"scalar/address result");
    require(c.load(0,encode(Op::AddAddr,1,1,0,0,0,1)),"overflow program");
    require(c.start(),"restart");c.step();require(c.fault()==Status::Bounds,"address overflow rejected");
    require(c.reset_idle(),"idle reset");
    for(unsigned i=0;i<5;++i) require(c.load(i,encode(Op::Loop,0,0)),"nested load");
    c.regs[0]=1;require(c.start(),"nested start");
    for(unsigned i=0;i<5;++i)c.step();
    require(c.fault()==Status::Bounds,"fifth loop rejected");
}
static void event_tests() {
    Sequencer c;Task t;t.words[0]=(Endpoint::M<<8)|1;t.words[1]=64;
    require(c.descriptor(0,t),"descriptor load");
    require(!c.descriptor(16,t),"descriptor bounds");
    require(c.load(0,encode(Op::Submit,1,0,0,1,3)),"submit code");
    require(c.load(1,encode(Op::Wait,2,1)),"wait code");
    require(c.load(2,encode(Op::End)),"end code");require(c.start(),"event start");
    c.step();require(bool(c.output()),"task exists");const auto task=*c.output();
    for(unsigned i=0;i<50;++i) {c.step();require(c.output()->words==task.words,"stable stalled packet");}
    c.step(true);for(unsigned i=0;i<20;++i)c.step();
    require(!c.idle() && c.pc()==1,"wait retains event");
    Completion d;d.endpoint=Endpoint::M;d.tag=task.tag();d.result=99;c.completion(d);c.step();c.step();
    require(c.ended() && c.regs[2]==99 && c.completed==1,"completion result");
    c.completion(d);require(c.fault()==Status::Protocol,"duplicate rejected");
    require(c.reset_idle(),"fault recovery");
    // Fill all 32 slots without completing them; the 33rd must not issue.
    for(unsigned i=0;i<34;++i)require(c.load(i,encode(Op::Submit,0,0)),"capacity program");
    require(c.start(),"capacity start");
    std::array<Task,32> tasks{};
    for(unsigned i=0;i<32;++i) {c.step(true);require(bool(c.output()),"32 slots issue");tasks[i]=*c.output();}
    c.step(true);require(!c.output() && c.submitted==33,"event capacity stops issue");
    // completed slots stay occupied until WAIT consumes them.
    for(unsigned i=0;i<32;++i){d.tag=tasks[i].tag();c.completion(d);}
    c.step();require(!c.output(),"unconsumed events retained");
    require(!c.load(0,0),"cannot rewrite a live stalled program");
    // A separately constructed controller rejects the unqualified R endpoint.
    Sequencer r;t.words[0]=Endpoint::R<<8;require(r.descriptor(0,t),"R descriptor");
    require(r.load(0,encode(Op::Submit)),"R program");require(r.start(),"R start");r.step();
    require(r.fault()==Status::Unavailable,"R disabled");
}
static void dma_tests() {
    // Independent address enumeration: coverage, byte masks, 4KiB cuts,
    // delayed/reordered burst acknowledgements, queue limits and drain errors.
    for(unsigned bytes: {1u,15u,16u,17u,255u,256u,257u,1024u,4096u}) {
        DmaDescriptor d;d.external=0x100000ff0ULL;d.s_offset=0;d.row_bytes=bytes;d.rows=2;
        d.external_stride=8192;d.s_stride=uint16_t((bytes+15)&~15u);
        require(d.validate()==Status::Ok,"DMA descriptor");DmaPlanner m;
        require(m.submit(d,55),"DMA submit");require(m.submit(d,56),"two DMA descriptors");
        require(!m.submit(d,57),"third DMA descriptor rejected");
        unsigned words=0;std::vector<unsigned> flight;
        for(unsigned guard=0;guard<2000 && !m.completion();++guard) {
            if(auto b=m.peek()) {
                const unsigned row=words/((bytes+15)/16),col=words%((bytes+15)/16);
                require(b->address==d.external+row*8192+col*16,"burst external address");
                require(b->local_word==row*d.s_stride/16+col,"burst S address");
                require(b->beats>=1 && b->beats<=16 && (b->address&4095)+b->beats*16<=4096,"AXI burst limits");
                require(m.issue(),"burst accepted");words+=b->beats;flight.push_back(b->id);
            } else if(!flight.empty()) {
                require(m.acknowledge(flight.back()),"delayed ACK");flight.pop_back();
            }
            require(m.reserved()<=32,"payload credits bounded");
        }
        require(bool(m.completion()),"DMA terminates");require(words==2*((bytes+15)/16),"all words covered");
        require(m.completion()->result==bytes*2,"valid bytes exclude padding");
        require(m.take_completion(),"consume DMA result");
    }
    DmaDescriptor bad;bad.external=(1ULL<<40)-16;bad.row_bytes=17;bad.rows=1;
    require(bad.validate()==Status::Bounds,"40bit external overflow");
    bad.external=0;bad.s_offset=16368;require(bad.validate()==Status::Bounds,"S capacity overflow");
    bad.s_offset=0;bad.rows=2;bad.s_stride=16;bad.external_stride=32;
    require(bad.validate()==Status::Bounds,"padded row overlap");
    DmaPlanner m;bad.row_bytes=512;bad.rows=1;require(m.submit(bad,9),"error descriptor");
    require(m.issue() && m.issue(),"two flight bursts");require(!m.peek(),"outstanding limit");
    require(m.acknowledge(0,true),"first burst error");require(!m.completion() && !m.peek(),"error drains remaining");
    require(m.acknowledge(1),"remaining drain");require(m.completion()->status==Status::Remote,"error reported");
    require(!m.acknowledge(1),"duplicate AXI acknowledgement rejected");
}
struct Harness:sc_core::sc_module {
    C c{"C"};DModule d{"D"};
    sc_core::sc_clock clk{"clk",sc_core::sc_time(10,sc_core::SC_NS)};
    sc_core::sc_fifo<Task> task{"task",1};
    sc_core::sc_fifo<Completion> done{"done",1},ddone{"ddone",1};
    sc_core::sc_fifo<DmaCommand> command{"command",1};
    sc_core::sc_fifo<Burst> burst{"burst",1};
    sc_core::sc_fifo<BurstAck> ack{"ack",1};
    bool passed=false;
    void run() {
        wait(100,sc_core::SC_NS); // intentionally hold endpoint to test bounded output
        const auto t=task.read();wait(50,sc_core::SC_NS);
        Completion r;r.tag=t.tag();r.endpoint=t.endpoint();r.result=123;done.write(r);
        DmaCommand cmd;cmd.descriptor.external=4080;cmd.descriptor.row_bytes=257;cmd.descriptor.rows=1;cmd.tag=17;
        command.write(cmd);unsigned words=0;
        while(words<17) {const auto b=burst.read();words+=b.beats;wait(30,sc_core::SC_NS);ack.write({b.id,false});}
        const auto dc=ddone.read();require(dc.result==257 && dc.tag==17,"clocked D completion");
        wait(100,sc_core::SC_NS);
        require(c.core.ended() && c.core.regs[2]==123,"clocked C completion during WAIT");
        passed=true;sc_core::sc_stop();
    }
    SC_CTOR(Harness) {
        c.clk(clk);c.tasks(task);c.completions(done);
        d.clk(clk);d.commands(command);d.bursts(burst);d.acknowledgements(ack);d.completions(ddone);
        Task t;t.words[0]=Endpoint::M<<8;require(c.core.descriptor(0,t),"clock descriptor");
        require(c.core.load(0,encode(Op::Submit,1,0)),"clock submit");
        require(c.core.load(1,encode(Op::Wait,2,1)),"clock wait");
        require(c.core.load(2,encode(Op::End)),"clock end");require(c.core.start(),"clock start");
        SC_THREAD(run);
    }
};
int sc_main(int,char**) {
    scalar_tests();event_tests();dma_tests();
    PacketIngress p;for(unsigned i=0;i<8;++i)require(p.push(i+100),"packet ingress");
    require(!p.push(9) && p.valid() && p.value().words[7]==107,"packet retained");require(p.pop(),"packet pop");
    Harness h{"h"};sc_core::sc_start(100,sc_core::SC_US);require(h.passed,"SystemC timeout");
    std::cout<<"PASS control contract checks="<<checks<<"\n";return 0;
}
