// Independent SystemC processes for bounded, timing-only native phase probes.
// One symbolic tick = one ns. No physical-frequency or energy qualification.
#include <systemc>
#include <algorithm>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <memory>
#include <stdexcept>
#include <string>
#include <tuple>
#include <vector>

using namespace sc_core;
using Tick = std::uint64_t;
struct Phase { int channel; Tick ticks; };
using Row = std::tuple<int,int,int,Tick,Tick>;
struct Context {
    std::vector<Row> rows;
    int count = 0, finished = 0;
    bool whole = false;
};
Tick now() { return sc_time_stamp().value(); }
void delay(Tick ticks) { wait(sc_time(static_cast<double>(ticks), SC_NS)); }

struct Request {
    int worker, sequence;
    Tick arrival, ticks;
    sc_event completed;
    Request(int w, int s, Tick t): worker(w), sequence(s), arrival(now()), ticks(t) {}
};

struct Channel : sc_module {
    Context& context;
    int id;
    sc_mutex lease;
    sc_event kick;
    std::vector<Request*> pending;
    Channel(sc_module_name name, Context& c, int i): sc_module(name), context(c), id(i) {
        SC_THREAD(run);
    }
    void transfer(int worker, int sequence, Tick ticks) {
        Request request(worker, sequence, ticks);
        pending.push_back(&request);
        kick.notify(SC_ZERO_TIME);
        wait(request.completed);
    }
    void run() {
        while (true) {
            if (pending.empty()) wait(kick);
            // Collect all requests at this physical timestamp, independent
            // of process construction and delta-cycle notification order.
            wait(SC_ZERO_TIME);
            wait(SC_ZERO_TIME);
            if (pending.empty()) continue;
            auto chosen = std::min_element(pending.begin(), pending.end(), [](Request* a, Request* b) {
                return std::tie(a->arrival,a->worker,a->sequence) < std::tie(b->arrival,b->worker,b->sequence);
            });
            Request* request = *chosen;
            pending.erase(chosen);
            Tick start = now();
            delay(request->ticks);
            context.rows.emplace_back(request->worker,request->sequence,id,start,now());
            request->completed.notify(SC_ZERO_TIME);
            wait(SC_ZERO_TIME);
            wait(SC_ZERO_TIME);
        }
    }
};

struct Worker : sc_module {
    Context& context;
    int id;
    std::vector<Phase> phases;
    std::vector<std::unique_ptr<Channel>>& channels;
    Worker(sc_module_name name, Context& c, int i, std::vector<Phase> p,
           std::vector<std::unique_ptr<Channel>>& ch):
        sc_module(name), context(c), id(i), phases(std::move(p)), channels(ch) {
        SC_THREAD(run);
    }
    void run() {
        int owned = -1;
        if (context.whole) {
            for (const Phase& p: phases) if (p.channel >= 0) owned = p.channel;
            channels.at(static_cast<std::size_t>(owned))->lease.lock();
        }
        for (std::size_t j=0; j<phases.size(); ++j) {
            const Phase& p = phases[j];
            if (p.channel < 0 || context.whole) {
                Tick start = now();
                delay(p.ticks);
                context.rows.emplace_back(id,static_cast<int>(j),p.channel,start,now());
            } else channels.at(static_cast<std::size_t>(p.channel))->transfer(id,static_cast<int>(j),p.ticks);
        }
        if (context.whole) channels.at(static_cast<std::size_t>(owned))->lease.unlock();
        if (++context.finished == context.count) sc_stop();
    }
};

int sc_main(int argc, char** argv) {
    try {
        if (argc != 3) throw std::runtime_error("usage: systemc-phase probe.txt whole-service|descriptor-phases");
        sc_set_time_resolution(1,SC_NS);
        std::string mode(argv[2]);
        if (mode != "whole-service" && mode != "descriptor-phases") throw std::runtime_error("unknown phase mode");
        std::ifstream input(argv[1]);
        int count=0, nchan=0;
        if (!(input>>count>>nchan) || count<1 || count>32 || nchan<1 || nchan>32)
            throw std::runtime_error("invalid phase dimensions");
        std::vector<std::vector<Phase>> programs;
        for (int i=0;i<count;++i) {
            int size=0;
            if (!(input>>size) || size<1 || size>100000) throw std::runtime_error("invalid finite phase count");
            std::vector<Phase> program;
            int channel=-1;
            for (int j=0;j<size;++j) {
                Phase p{};
                if (!(input>>p.channel>>p.ticks) || p.channel < -1 || p.channel>=nchan || !p.ticks || p.ticks>1000000000)
                    throw std::runtime_error("invalid phase");
                if (p.channel>=0) {
                    if (channel>=0 && channel!=p.channel) throw std::runtime_error("probe worker crosses channels");
                    channel=p.channel;
                }
                program.push_back(p);
            }
            if (channel<0) throw std::runtime_error("probe lacks external memory activity");
            programs.push_back(std::move(program));
        }
        std::string trailing;
        if (input>>trailing) throw std::runtime_error("trailing phase input");
        Context context;
        context.count=count; context.whole=mode=="whole-service";
        std::vector<std::unique_ptr<Channel>> channels;
        for (int i=0;i<nchan;++i) channels.emplace_back(new Channel(("channel_"+std::to_string(i)).c_str(),context,i));
        std::vector<std::unique_ptr<Worker>> workers;
        for (int i=0;i<count;++i)
            workers.emplace_back(new Worker(("worker_"+std::to_string(i)).c_str(),context,i,std::move(programs[i]),channels));
        sc_start();
        if (context.finished!=count) throw std::runtime_error("phase workers did not drain");
        std::sort(context.rows.begin(),context.rows.end());
        for (const Row& row:context.rows)
            std::cout<<"PHASE "<<std::get<0>(row)<<' '<<std::get<1>(row)<<' '<<std::get<2>(row)<<' '
                     <<std::get<3>(row)<<' '<<std::get<4>(row)<<'\n';
        std::cout<<"PHASE_COMPLETE "<<now()<<'\n';
        return 0;
    } catch (const std::exception& error) {
        std::cerr<<"PHASE_FAIL "<<error.what()<<'\n';
        return 1;
    }
}
