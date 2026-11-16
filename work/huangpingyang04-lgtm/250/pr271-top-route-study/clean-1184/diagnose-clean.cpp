#define main adapter_main
#include "transactional-maze.cpp"
#undef main
#include <map>

const char* label(Attempt value) {
    constexpr array<const char*,5> names={"available","driver_access","sink_access","channel","geometry"};
    return names.at(value);
}

int main(int argc,char** argv) {
    if(argc!=5)return 2;
    const auto nets=read_nets(argv[1]);
    auto paths=read_paths(argv[2],nets.size());
    const int shard=stoi(argv[3]),nshards=stoi(argv[4]);
    if(nets.size()!=1184||shard<0||shard>=nshards)return 2;
    Board board(nets),fixed_pins(nets);
    for(const auto& n:nets)if(has_route(paths[n.id])) {
        if(!legal_route(n,paths[n.id],board.occupied))throw runtime_error("Cannot replay verified routes");
        board.install(n.id,move(paths[n.id]));
    }
    Router loaded(board.tracks,4,false), isolated(fixed_pins.tracks,4,false);
    DetailedGraph local(board.tracks);
    FastMaze rejected(board.tracks);
    cout<<"index\tstatus\tlocation_x\tlocation_y\tfailed_pin\tstandalone_status\tblocking_nets\n";
    for(const auto& n:nets) {
        if(n.id%nshards!=shard||has_route(board.routes[n.id]))continue;
        board.tracks.use_pads(n);
        fixed_pins.tracks.use_pads(n);
        const auto current=loaded.run(n,board.occupied);
        const auto free=isolated.run(n,fixed_pins.occupied);
        int x=-1,y=-1,bad=-1,nblocks=-1;
        if(current.status==driver_blocked||current.status==sink_blocked) {
            local.load(n,board.occupied);
            for(size_t i=0;i<n.pins.size();++i)if(!local.can_reach_track(int(i))) {
                x=n.pins[i].x; y=n.pins[i].y; bad=int(i); break;
            }
        } else if(current.status==geometry_blocked) {
            rejected.graph.load(n,board.occupied);
            if(rejected.route(n.pins.size())) {
                auto attempt=rejected.extract(n);
                for(size_t i=0;i<attempt.vias.size()&&x<0;++i)
                    for(size_t j=0;j<i&&x<0;++j)if(via_conflict(attempt.vias[i],attempt.vias[j])) {
                        x=attempt.vias[i].x; y=attempt.vias[i].y;
                    }
            }
        }
        if(free.status==connected) {
            nblocks=blockers(board,n.id,free.route).size();
            if(current.status==graph_blocked) {
                constexpr int band=1600;
                map<pair<int,int>,int> counts;
                for(auto w:free.route.wires) {
                    auto a=w.a,b=w.b;
                    const bool horizontal=a.layer==0;
                    if((horizontal?a.x:a.y)>(horizontal?b.x:b.y))swap(a,b);
                    for(auto p=a;;) {
                        auto q=p;
                        if(horizontal)q.x=min(p.x+4*pitch,b.x);
                        else q.y=min(p.y+4*pitch,b.y);
                        if(board.occupied.blocked(n.id,p,q)!=-1)
                            ++counts[{(p.x+q.x)/(2*band),(p.y+q.y)/(2*band)}];
                        if(key(q)==key(b))break;
                        p=q;
                    }
                }
                for(auto v:free.route.vias) {
                    const Node a{v.x,v.y,0}, b{v.x,v.y,1};
                    if(board.occupied.blocked(n.id,a,b)!=-1)++counts[{v.x/band,v.y/band}];
                }
                if(!counts.empty()) {
                    auto best=max_element(counts.begin(),counts.end(),[](auto a,auto b){return a.second<b.second;});
                    x=best->first.first*band+band/2; y=best->first.second*band+band/2;
                }
            }
        }
        cout<<n.id<<'\t'<<label(current.status)<<'\t'<<x<<'\t'<<y<<'\t'<<bad<<'\t'<<label(free.status)<<'\t'<<nblocks<<'\n';
    }
}
