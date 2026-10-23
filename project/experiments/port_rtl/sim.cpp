// Executable bank-controller harness. M/V arithmetic is NOT implemented here.
#include "Vbank_port_fabric.h"
#include "verilated.h"
#include <array>
#include <vector>
#include <deque>
#include <fstream>
#include <iostream>
#include <sstream>
#include <iomanip>
#include <algorithm>
#include <stdexcept>
#include <random>
#include <cstdint>
#include <memory>

#ifndef PORT_MODE
#define PORT_MODE 0
#endif
#ifndef RESP_DEPTH
#define RESP_DEPTH 2
#endif
#ifndef LINK_MASK
#define LINK_MASK 63
#endif

using Data = std::array<uint32_t,16>;
struct Req { bool valid=false, write=false; int bank=0, addr=0; uint32_t tag=0; uint64_t strb=0; Data data{}; int generation=-1, generation_offset=0; };
struct Expected { bool write; uint32_t tag; Data data; uint64_t check_mask; };
struct Cycle { std::array<bool,3> grant{}, response{}; };
static void need(bool ok, const std::string& what) { if(!ok) throw std::runtime_error(what); }
static uint8_t byte(const Data& d,int i) { return uint8_t(d[i/4]>>(8*(i%4))); }
static void putbyte(Data& d,int i,uint8_t v) { uint32_t shift=8*(i%4); d[i/4]=(d[i/4]&~(255u<<shift))|(uint32_t(v)<<shift); }
static uint8_t token(int generation,int offset) { uint32_t word=uint32_t(generation+1)*2654435761u+uint32_t(offset/4)*2246822519u;return uint8_t(word>>(8*(offset%4))); }
template<class T> static std::string hexdata(const T& d,int words) { std::ostringstream o; o<<std::hex<<std::setfill('0'); for(int i=words-1;i>=0;--i)o<<std::setw(8)<<uint32_t(d[i]);return o.str(); }
static std::string hex64(uint64_t n) { std::ostringstream o;o<<std::hex<<std::setfill('0')<<std::setw(16)<<n;return o.str(); }

class Sim {
public:
    Vbank_port_fabric dut;
    std::array<std::array<Data,1024>,2> memory{};
    std::array<std::array<uint64_t,1024>,2> initialized{};
    std::array<std::deque<Expected>,3> pending;
    uint64_t cycle=0, requests=0, responses=0, read_beats=0, write_beats=0, stalled=0;
    std::array<unsigned,3> max_pending{};
    std::ofstream trace;
    explicit Sim(const std::string& trace_path) {
        if(!trace_path.empty()) { trace.open(trace_path); need(bool(trace),"cannot open trace");
            trace<<"{\"type\":\"config\",\"mode\":"<<PORT_MODE<<",\"depth\":"<<RESP_DEPTH<<",\"mask\":"<<LINK_MASK<<"}\n"; }
        dut.clk=0; dut.rst=1; dut.req_valid=0;dut.rsp_ready=0;dut.eval();
        dut.clk=1;dut.eval();dut.clk=0;dut.rst=0;dut.eval();
    }
    bool empty() const { return std::all_of(pending.begin(),pending.end(),[](const std::deque<Expected>& q){return q.empty();}); }
    Cycle tick(const std::array<Req,3>& req,const std::array<bool,3>& ready) {
        dut.clk=0; dut.req_valid=0;dut.req_bank=0;dut.req_write=0;dut.req_addr=0;dut.rsp_ready=0;
        for(int e=0;e<3;e++) {
            const auto& q=req[e];
            dut.req_valid|=(q.valid<<e);dut.req_bank|=(q.bank<<e);dut.req_write|=(q.write<<e);
            dut.req_addr|=(uint32_t(q.addr)<<(e*10));dut.req_tag[e]=q.tag;
            for(int j=0;j<16;j++)dut.req_wdata[e*16+j]=q.data[j];
            dut.req_wstrb[e*2]=uint32_t(q.strb);dut.req_wstrb[e*2+1]=uint32_t(q.strb>>32);
            dut.rsp_ready|=(ready[e]<<e);
        }
        dut.eval();
        Cycle r;
        if(trace)trace<<"{\"cycle\":"<<cycle<<",\"reset\":false,\"req\":[";
        for(int e=0;e<3;e++) {
            r.grant[e]=req[e].valid && ((dut.req_ready>>e)&1);
            r.response[e]=((dut.rsp_valid>>e)&1) && ready[e];
            if(trace) { const auto& q=req[e]; if(e)trace<<',';
                trace<<"{\"valid\":"<<int(q.valid)<<",\"ready\":"<<((dut.req_ready>>e)&1)
                     <<",\"bank\":"<<q.bank<<",\"write\":"<<int(q.write)<<",\"addr\":"<<q.addr
                     <<",\"tag\":"<<q.tag<<",\"generation\":"<<q.generation<<",\"generation_offset\":"<<q.generation_offset
                     <<",\"wdata_hex\":\""<<hexdata(q.data,16)<<"\",\"wstrb_hex\":\""<<hex64(q.strb)<<"\"}";
            }
            if(req[e].valid&&!r.grant[e])stalled++;
            need(bool((dut.rsp_valid>>e)&1)==!pending[e].empty(),"response valid/queue mismatch");
            if((dut.rsp_valid>>e)&1) {
                const auto& x=pending[e].front();
                need(dut.rsp_tag[e]==x.tag,"response tag mismatch");
                need(bool((dut.rsp_write>>e)&1)==x.write,"response direction mismatch");
                if(!x.write)for(int j=0;j<64;j++)if((x.check_mask>>j)&1)
                    need(uint8_t(dut.rsp_data[e*16+j/4]>>(8*(j%4)))==byte(x.data,j),"read payload mismatch");
            }
            if(r.response[e]) { pending[e].pop_front(); responses++; }
        }
        if(trace) { trace<<"],\"rsp\":[";
            for(int e=0;e<3;e++) { if(e)trace<<','; Data d{};for(int j=0;j<16;j++)d[j]=dut.rsp_data[e*16+j];
                trace<<"{\"valid\":"<<((dut.rsp_valid>>e)&1)<<",\"ready\":"<<int(ready[e])
                     <<",\"write\":"<<((dut.rsp_write>>e)&1)<<",\"tag\":"<<dut.rsp_tag[e]
                     <<",\"data_hex\":\""<<hexdata(d,16)<<"\"}";
            } trace<<"]}\n";
        }
        int reads[2]={},writes[2]={};
        for(int e=0;e<3;e++)if(r.grant[e]) {
            const auto& q=req[e];
            need((LINK_MASK>>(2*e+q.bank))&1,"disabled link grant");
            need(q.addr>=0&&q.addr<1024,"address outside bank");
            need(pending[e].size()<RESP_DEPTH,"response credit overflow");
            if(q.write) {
                need(!(((dut.rsp_valid>>e)&1)&&!((dut.rsp_write>>e)&1)),"half duplex data collision");
                writes[q.bank]++;write_beats++;
            } else { reads[q.bank]++;read_beats++; }
            for(int f=0;f<e;f++)if(r.grant[f])need(!(req[f].bank==q.bank&&req[f].addr==q.addr),"same row dual grant");
            // Only requested read bytes are semantically initialized. Full beat is transported.
            const uint64_t check=q.write ? 0 : q.strb;
            if(!q.write)need((initialized[q.bank][q.addr]&check)==check,"uninitialized requested read byte");
            if(!q.write&&q.generation>=0)for(int j=0;j<64;j++)if((check>>j)&1)
                need(byte(memory[q.bank][q.addr],j)==token(q.generation,q.generation_offset+j),"wrong graph generation at accepted read");
            pending[e].push_back(Expected{q.write,q.tag,memory[q.bank][q.addr],check});
            if(q.write)for(int j=0;j<64;j++)if((q.strb>>j)&1)putbyte(memory[q.bank][q.addr],j,byte(q.data,j));
            if(q.write)initialized[q.bank][q.addr]|=q.strb;
            max_pending[e]=std::max<unsigned>(max_pending[e],pending[e].size());requests++;
        }
        for(int b=0;b<2;b++) {
            if(PORT_MODE==0)need(reads[b]+writes[b]<=1,"1RW overissue");
            if(PORT_MODE==1)need(reads[b]<=1&&writes[b]<=1,"1R1W overissue");
            if(PORT_MODE==2)need(reads[b]+writes[b]<=2,"2RW overissue");
        }
        dut.clk=1;dut.eval();cycle++;return r;
    }
};

struct Task {int id,kind,ep,bank,write,offset,bytes,latency,version;std::vector<int> deps;int priority=0;
    bool started=false,done=false; int start=-1,end=-1,ready_at=-1,accepted=0,received=0;};

static void run_program(const std::string& file,const std::string& trace) {
    std::ifstream input(file);need(bool(input),"cannot open program");int n=0,stalls=0,mode=0,depth=0,mask=0;input>>n>>stalls>>mode>>depth>>mask;need(bool(input),"incomplete program header");need(n>0&&n<10000,"invalid task count");
    need(mode==PORT_MODE&&depth==RESP_DEPTH&&mask==LINK_MASK,"program/binary hardware mismatch");
    need(stalls==0||stalls==1,"invalid stall profile");
    std::vector<Task> tasks(n);for(auto& t:tasks){input>>t.priority;need(bool(input),"incomplete priorities");}
    for(int i=0;i<n;i++) { auto& t=tasks[i];int count=0;input>>t.id>>t.kind>>t.ep>>t.bank>>t.write>>t.offset>>t.bytes>>t.latency>>t.version>>count;
        need(bool(input),"incomplete task row");need(t.id==i&&count>=0&&count<n,"invalid task row");t.deps.resize(count);for(int&d:t.deps){input>>d;need(bool(input),"incomplete dependency list");need(d>=0&&d<i,"dependency must precede task");}
        need(t.ep>=0&&t.ep<3&&t.latency>0&&t.latency<2000000,"invalid engine/latency");
        need((t.kind==0||t.kind==1)&&(t.bank==0||t.bank==1)&&(t.write==0||t.write==1),"invalid task kind/bank/direction");
        if(t.kind){need(t.offset>=0&&t.offset%64==0&&t.bytes>0&&t.bytes<=65536&&t.offset<=65536-t.bytes,"invalid transfer extent");
            need(t.write || (t.version>=0&&t.version<i),"invalid expected read generation");
            need((LINK_MASK>>(2*t.ep+t.bank))&1,"program requests disabled link");}
    }need(bool(input),"incomplete program");
    Sim sim(trace); std::array<int,3> active{{-1,-1,-1}};std::array<Req,3> held{};uint32_t next_tag=1;int completed=0;int last_dma_write=-2,last_external_data=-2;
    while(completed<n) {
        need(sim.cycle<2000000,"program watchdog");
        for(auto& t:tasks)if(t.started&&!t.done&&!t.kind&&int(sim.cycle)>=t.end){t.done=true;completed++;}
        for(auto& t:tasks)if(!t.started&&t.ready_at<0&&std::all_of(t.deps.begin(),t.deps.end(),[&](int d){return tasks[d].done;}))t.ready_at=sim.cycle;
        for(auto& t:tasks)if(!t.started&&!t.kind&&t.ready_at>=0){t.started=true;t.start=sim.cycle;t.end=t.start+t.latency;}
        for(int e=0;e<3;e++) {
            if(active[e]<0) {
                int best=-1; for(const auto& t:tasks)if(t.kind&&!t.started&&t.ep==e&&t.ready_at>=0) {
                    if(best<0 || t.priority>tasks[best].priority ||
                       (t.priority==tasks[best].priority && (t.ready_at<tasks[best].ready_at || (t.ready_at==tasks[best].ready_at&&t.id<best))))best=t.id;
                }
                if(best>=0){active[e]=best;tasks[best].started=true;tasks[best].start=sim.cycle;}
            }
            if(active[e]>=0&&!held[e].valid) {
                auto& t=tasks[active[e]];int beats=(t.bytes+63)/64;
                if(t.accepted<beats && int(sim.cycle)>=t.start+t.latency && !(e==2&&t.write&&(int(sim.cycle)<last_dma_write+2))) {
                    Req q;q.valid=true;q.bank=t.bank;q.write=t.write;q.addr=t.offset/64+t.accepted;q.tag=next_tag++;
                    int count=std::min(64,t.bytes-t.accepted*64);q.strb=count==64?~uint64_t(0):((uint64_t(1)<<count)-1);
                    q.generation=t.write?t.id:t.version;q.generation_offset=t.accepted*64;
                    for(int j=0;j<count;j++)putbyte(q.data,j,token(t.id,t.accepted*64+j));
                    if(!q.write)for(int j=0;j<count;j++)need(byte(sim.memory[q.bank][q.addr],j)==token(t.version,t.accepted*64+j),"wrong graph version at read issue");
                    held[e]=q;
                }
            }
        }
        std::array<bool,3> ready{};
        for(int e=0;e<3;e++)ready[e]=(!stalls||((sim.cycle+e*2)%8>=3));
        // External read sink is 32 B/cycle, modeled by a 64 B beat every two cycles.
        if((sim.dut.rsp_valid&4)&&!(sim.dut.rsp_write&4)&&(sim.cycle%2))ready[2]=false;
        Cycle r=sim.tick(held,ready);
        if((r.grant[2]&&held[2].write)||(r.response[2]&&active[2]>=0&&!tasks[active[2]].write)) {
            need(int(sim.cycle)-1-last_external_data>=2,"shared external bandwidth exceeded");
            last_external_data=sim.cycle-1;
        }
        for(int e=0;e<3;e++)if(active[e]>=0) {
            auto& t=tasks[active[e]];
            if(r.grant[e]){if(e==2&&held[e].write)last_dma_write=sim.cycle-1;t.accepted++;held[e].valid=false;}
            if(r.response[e])t.received++;
            if(t.received==(t.bytes+63)/64){need(t.accepted==t.received,"premature task completion");t.done=true;t.end=sim.cycle;completed++;active[e]=-1;}
        }
    }
    need(sim.empty()&&sim.requests==sim.responses,"undrained program");
    // Final empty cycle is evidence of no unaccounted response.
    sim.tick({},{{true,true,true}});
    std::cout<<"{\"cycles\":"<<sim.cycle-1<<",\"requests\":"<<sim.requests<<",\"responses\":"<<sim.responses
             <<",\"read_beats\":"<<sim.read_beats<<",\"write_beats\":"<<sim.write_beats<<",\"request_stall_cycles\":"<<sim.stalled
             <<",\"max_pending\":["<<sim.max_pending[0]<<','<<sim.max_pending[1]<<','<<sim.max_pending[2]<<"],\"tasks\":[";
    for(int i=0;i<n;i++){if(i)std::cout<<',';std::cout<<"["<<i<<','<<tasks[i].start<<','<<tasks[i].end<<"]";}std::cout<<"]}\n";
}

static void run_stress(unsigned seed,const std::string& trace) {
    Sim sim(trace);std::mt19937 rng(seed);std::array<Req,3> held{};uint32_t tag=1;
    // Initialize both full banks via any enabled endpoint. Memory reset is not invented.
    for(int bank=0;bank<2;bank++) {
        int e=0;while(e<3&&!((LINK_MASK>>(2*e+bank))&1))e++;need(e<3,"no initializer link");
        int accepted=0,received=0;
        while(received<1024) {
            need(sim.cycle<10000,"stress initialization watchdog");
            if(!held[e].valid&&accepted<1024){auto&q=held[e];q.valid=true;q.write=true;q.bank=bank;q.addr=accepted;q.tag=tag++;q.strb=~uint64_t(0);for(auto&w:q.data)w=rng();}
            auto r=sim.tick(held,{{true,true,true}});if(r.grant[e]){accepted++;held[e].valid=false;}if(r.response[e])received++;
        }
    }
    uint64_t start=sim.cycle;int issued=0;
    while(sim.cycle-start<4000||!sim.empty()||std::any_of(held.begin(),held.end(),[](const Req&q){return q.valid;})) {
        need(sim.cycle-start<5000,"stress watchdog");
        for(int e=0;e<3;e++)if(!held[e].valid&&sim.cycle-start<4000){auto&q=held[e];q.valid=true;q.bank=rng()%2;
            if(!((LINK_MASK>>(2*e+q.bank))&1))q.bank^=1;
            q.write=rng()%2;q.addr=(sim.cycle%4==0)?0:int(rng()%16);q.tag=tag++;q.strb=(uint64_t(rng())<<32)|rng();for(auto&w:q.data)w=rng();}
        std::array<bool,3> ready{};for(int e=0;e<3;e++)ready[e]=(sim.cycle-start>=4000)||((sim.cycle+e)%11>=5);
        auto r=sim.tick(held,ready);for(int e=0;e<3;e++)if(r.grant[e]){held[e].valid=false;issued++;}
    }
    sim.tick({},{{true,true,true}});
    std::cout<<"{\"seed\":"<<seed<<",\"cycles\":"<<sim.cycle<<",\"requests\":"<<sim.requests<<",\"responses\":"<<sim.responses
             <<",\"stress_requests\":"<<issued<<",\"max_pending\":["<<sim.max_pending[0]<<','<<sim.max_pending[1]<<','<<sim.max_pending[2]<<"]}\n";
}
int main(int argc,char**argv) {
    try { need(argc>=3,"usage: sim --program file [trace] | --stress seed [trace]");
        std::string trace=argc>3?argv[3]:"";if(std::string(argv[1])=="--program")run_program(argv[2],trace);
        else if(std::string(argv[1])=="--stress")run_stress(std::stoul(argv[2]),trace);else throw std::runtime_error("unknown mode");return 0;
    } catch(const std::exception&e){std::cerr<<"FAIL: "<<e.what()<<'\n';return 1;}
}
