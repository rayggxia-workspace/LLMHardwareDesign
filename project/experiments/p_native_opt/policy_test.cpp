#include "Vpolicy_top.h"
#include "verilated.h"
#include <algorithm>
#include <array>
#include <cstdint>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

using Word=std::array<uint32_t,4>;
struct Command { unsigned client=0,address=0; bool write=false; Word data{}; };
struct Client { unsigned issued=0,completed=0,target=0; bool outstanding=false;
    uint64_t request_since=0; unsigned skipped=0,max_skipped=0; };

class Bench {
public:
    Vpolicy_top d;
    std::array<Word,1024> ram{};
    std::array<Client,4> c{};
    Command accepted{};
    Word expected{},response{};
    bool active=false,pending=false,enabled=false,random=false,corrupt=false;
    unsigned burst=2,seed=1,latency=2;
    uint64_t cycle=0,due=0,hold_mem_until=0,hold_rsp_until=0;
    uint64_t total_accept=0,total_mem=0,total_ack=0,default_cycles=0;
    uint64_t consumer_wait_sum=0,consumer_response_sum=0,consumer_responses=0,external_wait_max=0;
    unsigned max_external_skips=0;
    std::vector<unsigned> grants;
    std::array<uint64_t,4> request_origin{};

    Bench(bool en,unsigned b,unsigned s):enabled(en),burst(b),seed(s) {
        d.clk=0; d.reset=1; d.req_valid=0; d.req_write=0; d.rsp_ready=0;
        d.req_addr=0; d.mem_ready=0; d.mem_valid=0;
        for (unsigned i=0;i<16;i++) d.req_data[i]=0;
        for (unsigned i=0;i<4;i++) d.mem_result[i]=0;
        d.eval(); d.clk=1; d.eval(); d.clk=0; d.eval(); d.reset=0;
    }
    uint32_t rng() { seed^=seed<<13; seed^=seed>>17; seed^=seed<<5; return seed; }
    static void require(bool ok,const char* what) {
        if (!ok) throw std::runtime_error(what);
    }
    Command next(unsigned i) const {
        Command x; x.client=i; x.write=(c[i].issued%2)==0;
        x.address=i*128+(c[i].issued/2)%128;
        for (unsigned j=0;j<4;j++)
            x.data[j]=0x137ac000U+uint32_t(i*0x1000+c[i].issued/2*4+j);
        return x;
    }
    void same_default() {
        if (enabled) return;
        require(d.req_ready==d.ref_req_ready && d.rsp_valid==d.ref_rsp_valid &&
            d.mem_req==d.ref_mem_req && d.mem_write==d.ref_mem_write &&
            d.mem_take==d.ref_mem_take && d.busy==d.ref_busy &&
            d.mem_addr==d.ref_mem_addr,"DEFAULT_CONTROL_DRIFT");
        for (unsigned i=0;i<16;i++) require(d.rsp_data[i]==d.ref_rsp_data[i],"DEFAULT_RESPONSE_DRIFT");
        for (unsigned i=0;i<4;i++) require(d.mem_data[i]==d.ref_mem_data[i],"DEFAULT_PAYLOAD_DRIFT");
        default_cycles++;
    }
    void tick(bool allow_new=true) {
        d.clk=0; d.reset=0; d.req_valid=0; d.req_write=0; d.req_addr=0;
        for (unsigned i=0;i<4;i++) {
            auto x=next(i);
            if (allow_new && !c[i].outstanding && c[i].issued<c[i].target) {
                d.req_valid|=1U<<i;
                if (c[i].request_since==0) c[i].request_since=cycle+1;
            }
            if (x.write) d.req_write|=1U<<i;
            d.req_addr|=uint64_t(x.address)<<(10*i);
            for (unsigned j=0;j<4;j++)
                d.req_data[4*i+j]=c[i].outstanding ? 0xdeadbeefU : x.data[j];
        }
        d.mem_ready=!pending && cycle>=hold_mem_until && (!random || rng()%4!=0);
        d.mem_valid=pending && cycle>=due;
        for (unsigned j=0;j<4;j++) d.mem_result[j]=response[j];
        if (corrupt && d.mem_valid && !accepted.write) d.mem_result[0]^=1U;
        d.rsp_ready=cycle>=hold_rsp_until ? (random ? (rng()&15U) : 15U) : 0U;
        d.eval(); same_default();
        require((d.req_ready & (d.req_ready-1U))==0,"MULTIPLE_CLIENT_ACCEPTS");
        require((d.rsp_valid & (d.rsp_valid-1U))==0,"MULTIPLE_RESPONSES");
        unsigned fire=d.req_ready & d.req_valid;
        if (active) require(fire==0,"EARLY_READMISSION_BEFORE_ACK");
        if (fire) {
            require(!active && !pending,"SECOND_OWNER_ACCEPTED");
            unsigned owner=0; while (!(fire&(1U<<owner))) owner++;
            for (unsigned i=0;i<4;i++) {
                if (d.req_valid&(1U<<i)) {
                    if (i==owner) { c[i].max_skipped=std::max(c[i].max_skipped,c[i].skipped); c[i].skipped=0; }
                    else c[i].skipped++;
                } else c[i].skipped=0;
            }
            if (enabled) {
                for (unsigned i=0;i<2;i++)
                    require(c[i].skipped<=2*(burst+1)-1,"EXTERNAL_FAIRNESS_BOUND");
                // With all four continuously pending, each class has its own
                // cyclic order. This catches a shared or stuck consumer cursor.
                if (grants.size()<24 && d.req_valid==15) {
                    unsigned n=unsigned(grants.size()),group=n/(burst+1),pos=n%(burst+1);
                    unsigned wanted=pos<burst ? 2+(group*burst+pos)%2 : group%2;
                    require(owner==wanted,"SATURATED_CLASS_ROUND_ROBIN");
                }
            }
            accepted=next(owner); active=true; c[owner].outstanding=true;
            request_origin[owner]=c[owner].request_since;
            if (owner>=2) consumer_wait_sum+=cycle+1-c[owner].request_since;
            else external_wait_max=std::max(external_wait_max,cycle+1-c[owner].request_since);
            c[owner].request_since=0; c[owner].issued++;
            grants.push_back(owner); total_accept++;
        }
        bool mem_fire=d.mem_req && d.mem_ready;
        if (d.mem_req) {
            require(active && !pending,"MEMORY_REQUEST_WITHOUT_OWNER");
            require(d.mem_addr==accepted.address && bool(d.mem_write)==accepted.write,"REQUEST_CHANGED_WHILE_HELD");
            for (unsigned j=0;j<4;j++) require(d.mem_data[j]==accepted.data[j],"PAYLOAD_CHANGED_WHILE_HELD");
        }
        if (d.rsp_valid) {
            require(active && pending && d.mem_valid,"UNSOLICITED_RESPONSE");
            require(d.rsp_valid==(1U<<accepted.client),"WRONG_RESPONSE_OWNER");
            for (unsigned j=0;j<4;j++)
                require(d.rsp_data[accepted.client*4+j]==expected[j],"READ_DATA_MISMATCH");
        }
        bool ack=(d.rsp_valid & d.rsp_ready)!=0;
        require(ack==bool(d.mem_valid && d.mem_take),"ACK_OWNERSHIP_MISMATCH");
        d.clk=1; d.eval(); d.clk=0; d.eval();
        if (mem_fire) {
            require(!pending,"MEMORY_RESPONSE_OVERWRITE");
            if (accepted.write) ram[accepted.address]=accepted.data;
            expected=accepted.write ? Word{} : ram[accepted.address];
            response=expected; pending=true; due=cycle+latency+(random ? rng()%5 : 0);
            total_mem++;
        }
        if (ack) {
            auto i=accepted.client; c[i].outstanding=false; c[i].completed++;
            if (i>=2) { consumer_responses++; consumer_response_sum+=cycle+1-request_origin[i]; }
            else max_external_skips=std::max(max_external_skips,c[i].max_skipped);
            active=false; pending=false; total_ack++;
        }
        cycle++;
        require(cycle<200000,"TIMEOUT");
    }
    bool done() const {
        if (active || pending) return false;
        for (const auto& x:c) if (x.completed!=x.target) return false;
        return true;
    }
    void configure(unsigned count,bool stalls) {
        require(!active && !pending,"CONFIGURE_WHILE_ACTIVE");
        c={}; grants.clear(); random=stalls;
        for (auto& x:c) x.target=count;
    }
    void drain() { while (!done()) tick(); for (unsigned i=0;i<4;i++) tick(); }
    void reset_now() {
        d.clk=0; d.reset=1; d.eval();
        require(d.req_ready==0 && d.rsp_valid==0 && !d.mem_req && !d.mem_take,"RESET_EXPOSED_HANDSHAKE");
        d.clk=1; d.eval(); d.clk=0; d.eval();
        active=false; pending=false; c={}; grants.clear();
        hold_mem_until=0; hold_rsp_until=0;
        d.reset=0; d.mem_valid=0; d.req_valid=0; d.rsp_ready=0; d.eval();
        for (unsigned i=0;i<8;i++) {
            tick(); require(!d.busy && !d.rsp_valid && !d.mem_req,"STALE_TRANSACTION_AFTER_RESET");
        }
    }
};

int main(int argc,char** argv) {
    Verilated::commandArgs(argc,argv);
    bool enable=false,negative=false; unsigned burst=2,seed=143;
    for (int i=1;i<argc;i++) {
        std::string a=argv[i];
        if (a=="--enabled") enable=true;
        else if (a=="--negative-response") negative=true;
        else if (a=="--burst" && i+1<argc) burst=unsigned(std::stoul(argv[++i]));
        else if (a=="--seed" && i+1<argc) seed=unsigned(std::stoul(argv[++i]));
    }
    try {
        Bench b(enable,burst,seed);
        b.configure(32,false); b.corrupt=negative; b.drain();
        auto steady_cycles=b.cycle; auto consumer_wait=b.consumer_wait_sum;
        auto consumer_count=b.consumer_responses; auto response_sum=b.consumer_response_sum;
        auto external_wait=b.external_wait_max;
        auto ext_skips=b.max_external_skips;
        b.reset_now(); b.configure(80,true); b.drain();
        // Pending command must remain stable although the source payload is poisoned.
        b.reset_now(); b.configure(4,false); b.hold_mem_until=b.cycle+31; b.drain();
        // One held response reserves its owner and blocks every new grant.
        b.reset_now(); b.configure(4,false); b.hold_rsp_until=b.cycle+41; b.drain();
        // Reset while idle, while a command waits for acceptance, and after a
        // real response is valid but deliberately not acknowledged.
        b.reset_now(); b.configure(2,false); b.hold_mem_until=b.cycle+40;
        b.tick(); b.tick(); Bench::require(b.active && !b.pending,"RESET_SEND_SETUP"); b.reset_now();
        b.configure(2,false); b.hold_rsp_until=b.cycle+80;
        while (!b.pending || b.cycle<=b.due+2) b.tick();
        Bench::require(b.active && b.pending,"RESET_RETURN_SETUP"); b.reset_now();
        b.configure(16,true); b.drain();
        // Addressable storage persists through reset; no pending response does.
        Bench::require(b.ram[0][0]==0x137ac000U,"RESET_ERASED_RAM_OR_WRONG_WRITE");
        Bench::require(b.total_accept==b.total_mem+1 && b.total_mem==b.total_ack+1,
            "FINAL_ACK_ACCOUNTING");
        std::cout<<"POLICY_PASS enabled="<<enable<<" burst="<<burst<<" seed="<<seed
            <<" steady_cycles="<<steady_cycles<<" consumer_admission_wait_sum="<<consumer_wait
            <<" consumer_responses="<<consumer_count<<" max_external_admission_wait="<<external_wait
            <<" consumer_response_latency_sum="<<response_sum
            <<" max_external_skipped_grants="<<ext_skips
            <<" default_compared_cycles="<<b.default_cycles
            <<" accepts="<<b.total_accept<<" memory_requests="<<b.total_mem<<" response_ACKs="<<b.total_ack
            <<" reset_discarded_commands=2\n";
        b.d.final(); return 0;
    } catch (const std::exception& e) {
        std::cerr<<"POLICY_CHECK_FAILED "<<e.what()<<"\n"; return 1;
    }
}
