#define main adapter_main
#include "transactional-maze.cpp"
#undef main

int main(int argc,char** argv) {
    if(argc!=2)return 2;
    const auto nets=read_nets(argv[1]);
    if(nets.size()!=1184)throw runtime_error("Expected the 1184-net handoff");
    Board empty(nets);
    if(route_count(empty)!=0)throw runtime_error("Input has routed nets");
    const auto reserves=reserve_access(nets,empty,6);
    for(const auto& n:nets)empty.release(reserves[n.id].shapes,reserves[n.id].stub);
    cout<<"net_index\tpin_index\tindependent_exits\tnearby_pins\treserved_exit\n";
    for(const auto& n:nets)for(size_t i=0;i<n.pins.size();++i) {
        const auto p=n.pins[i];
        const auto starts=portals(p,n,empty.occupied,{},32);
        unordered_set<uint64_t> exits;
        for(const auto& path:starts) {
            auto a=path.back();
            for(int change:{-pitch,pitch}) {
                auto b=a;
                (b.layer?b.y:b.x)+=change;
                if(empty.occupied.fits(b)&&empty.occupied.blocked(n.id,a,b)==-1)exits.insert(key(b));
            }
        }
        int density=0;
        for(const auto& other:nets)if(n.id!=other.id)for(auto q:other.pins)
            density+=abs(q.x-p.x)<=4*pitch&&abs(q.y-p.y)<=4*pitch;
        const auto r=rectangle(p,p);
        const auto& stub=reserves[n.id].stub;
        const bool reserved=any_of(stub.wires.begin(),stub.wires.end(),[&](const Wire& w) {
            return w.a.layer==0&&touch(r,rectangle(w.a,w.b));
        })||any_of(stub.vias.begin(),stub.vias.end(),[&](Node via) {return touch(r,rectangle(via,via));});
        cout<<n.id<<'\t'<<i<<'\t'<<exits.size()<<'\t'<<density<<'\t'<<reserved<<'\n';
    }
}
