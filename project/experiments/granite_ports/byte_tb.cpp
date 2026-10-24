#include "Vbyte_core.h"
#include "verilated.h"
#include <array>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

static void need(bool ok, const std::string& message) { if (!ok) throw std::runtime_error(message); }
static void edge(Vbyte_core& top) { top.clk=0; top.eval(); top.clk=1; top.eval(); top.clk=0; top.eval(); }
static int read_ref(const std::array<int,512>& memory, const std::array<bool,512>& live, int address) {
    if(address<0) { need(address>=-256,"immediate domain"); return -1-address; }
    need(address<512 && live[address] && memory[address]>=0,"live initialized source"); return memory[address];
}
int main(int argc, char** argv) {
    Verilated::commandArgs(argc,argv);
    try {
        need(argc>=5,"usage: tb trace.tsv rom.requests actual.tsv report.json +rom=rom.hex");
        Vbyte_core top; top.reset=1; top.request=0; top.rom_request=0; edge(top); edge(top); top.reset=0;
        std::array<int,512> memory; memory.fill(-1); std::array<bool,512> live{};
        std::ifstream trace(argv[1]); need(trace.good(),"trace open"); std::ofstream actual(argv[3]);
        std::string line, current; std::uint64_t actions=0, cases=0, clocks=0; std::array<std::uint64_t,8> lanes{};
        while(std::getline(trace,line)) {
            if(line.empty()) continue;
            std::istringstream row(line); char kind; row>>kind;
            if(kind=='B') { row>>current; memory.fill(-1); live.fill(false); ++cases; }
            else if(kind=='M') { int start,size; row>>start>>size; need(start>=0&&size>=0&&start+size<=512,"frame allocate");
                for(int i=start;i<start+size;++i) { need(!live[i],"frame overlap"); live[i]=true; memory[i]=-1; } }
            else if(kind=='F') { int start,size; row>>start>>size; for(int i=start;i<start+size;++i) { need(i>=0&&i<512&&live[i],"free live");live[i]=false;memory[i]=-1; } }
            else if(kind=='I') { int address,value; row>>address>>value; need(address>=0&&address<512&&live[address]&&value>=0&&value<256,"input initialization");memory[address]=value; }
            else if(kind=='O') {
                std::string name, refs, values; int sign; row>>name>>sign>>refs>>values;
                for(char& x:refs)if(x==',')x=' ';for(char& x:values)if(x==',')x=' ';
                std::istringstream rr(refs),vv(values);int address,value;
                while(rr>>address){need(bool(vv>>value),"output value parse");need(read_ref(memory,live,address)==value,"final output from actual live RTL store");}
            }
            else if(kind=='A') {
                int op,ra,rb,rc,rd,rh,av,bv,cv,lo,hi; row>>op>>ra>>rb>>rc>>rd>>rh>>av>>bv>>cv>>lo>>hi;
                need(!row.fail() && op>=0 && op<=11,"action parse/opcode domain");
                int a=read_ref(memory,live,ra), b=read_ref(memory,live,rb), c=read_ref(memory,live,rc);
                need(a==av&&b==bv&&c==cv,"trace must consume actual causal RTL store");
                unsigned lane=actions%8; top.request=1u<<lane; top.opcode[lane]=op;
                top.a[lane]=a;top.b[lane]=b;top.cin[lane]=c;edge(top);++clocks;
                need(top.response==(1u<<lane)&&top.lo[lane]==lo&&top.hi[lane]==hi,"byte RTL mismatch case="+current+" action="+std::to_string(actions));
                if(rd>=0) { need(rd<512&&live[rd],"live output");memory[rd]=top.lo[lane]; }
                if(rh>=0) { need(rh<512&&live[rh],"live flag");memory[rh]=top.hi[lane]; }
                actual<<actions<<' '<<lane<<' '<<unsigned(top.lo[lane])<<' '<<unsigned(top.hi[lane])<<'\n';
                ++actions; ++lanes[lane];
            } else need(kind=='E',"unknown trace command");
        }
        top.request=0;
        std::ifstream requests(argv[2]); need(requests.good(),"ROM requests open");
        std::vector<std::pair<unsigned,std::uint32_t>> queries; unsigned addr; std::uint32_t expect;
        while(requests>>addr>>expect) { need(addr<32768,"ROM address"); queries.emplace_back(addr,expect); }
        for(std::size_t cycle=0;cycle<queries.size()+2;++cycle) {
            top.rom_request=cycle<queries.size(); if(cycle<queries.size())top.rom_address=queries[cycle].first;
            edge(top); ++clocks;
            bool want=cycle>=2;
            need(bool(top.rom_response)==want,"ROM exact response valid/latency2");
            if(want) { need(top.rom_data==queries[cycle-2].second,"ROM data/order under continuous II1 requests");
                actual<<"R "<<cycle<<' '<<queries[cycle-2].first<<' '<<std::uint32_t(top.rom_data)<<'\n'; }
        }
        std::ofstream report(argv[4]);
        report<<"{\"status\":\"PASS_BYTE_CORE_RTL_REPLAY\",\"cases\":"<<cases<<",\"actions\":"<<actions
              <<",\"ALU_latency_edges\":1,\"ALU_action_cycles\":"<<actions<<",\"ROM_requests\":"<<queries.size()
              <<",\"ROM_latency_cycles\":2,\"ROM_II_cycles\":1,\"ROM_word_bits\":32,\"ROM_ports\":1,\"lanes_covered\":[";
        for(unsigned i=0;i<8;++i)report<<(i?",":"")<<lanes[i];
        report<<"],\"controller\":\"software address controller/external finite byte store; no full wide FSM or RF RTL\"}\n";
        std::cout<<"PASS actions="<<actions<<" cases="<<cases<<" ROM="<<queries.size()<<'\n';
        return 0;
    } catch(const std::exception& error) {std::cerr<<error.what()<<'\n';return 1;}
}
