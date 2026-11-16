// A second pass over independently verified candidate paths on the identical graph.
#define main original_main
#include "transactional-maze.cpp"
#undef main

int main(int argc,char** argv) {
    if(argc!=5)return 2;
    const auto nets=read_nets(argv[1]);
    auto baseline=read_paths(argv[2],nets.size());
    auto candidates=read_paths(argv[3],nets.size());
    Board board(nets);
    for(const auto& net:nets) {
        auto& candidate=baseline[net.id];
        if(!has_route(candidate))continue;
        if(!legal_route(net,candidate,board.occupied))
            throw runtime_error("Verified starting route is incompatible with admitted ports");
        board.install(net.id,move(candidate));
    }
    const int initial=route_count(board);
    write_routes(string(argv[4])+".initial",board.routes);
    Router maze(board.tracks,24,false);
    int attempts=0,accepted=0,direct=0,rolled=0,restored=0;
    for(int id:order_by_span(nets)) {
        auto& proposed=candidates[id];
        if(has_route(board.routes[id])||!has_route(proposed))continue;
        if(legal_route(nets[id],proposed,board.occupied)) {
            board.install(id,move(proposed));
            ++direct;
            continue;
        }
        const auto conflicts=blockers(board,id,proposed);
        if(conflicts.empty()||conflicts.size()>4||attempts>=120||
           any_of(conflicts.begin(),conflicts.end(),[&](int k){return !has_route(board.routes.at(k));}))continue;
        ++attempts;
        vector<Route> old;
        for(int k:conflicts)old.push_back(board.remove(k));
        vector<int> changed;
        if(legal_route(nets[id],proposed,board.occupied)) {
            board.install(id,move(proposed));
            changed.push_back(id);
        }
        if(!changed.empty())for(int k:conflicts) {
            board.tracks.use_pads(nets[k]);
            auto r=maze.run(nets[k],board.occupied);
            if(r.status!=connected)break;
            board.install(k,move(r.route));
            changed.push_back(k);
        }
        bool ok=changed.size()==1+conflicts.size();
        if(ok)for(int k:changed)ok=ok&&legal_route(nets[k],board.routes[k],board.occupied);
        if(ok) {
            ++accepted;
            restored+=conflicts.size();
        } else {
            ++rolled;
            for(int k:changed)board.remove(k);
            for(size_t i=0;i<conflicts.size();++i) {
                int k=conflicts[i];
                if(!legal_route(nets[k],old[i],board.occupied))
                    throw runtime_error("Rollback did not restore the initial geometry");
                board.install(k,move(old[i]));
            }
        }
    }
    const int final_count=route_count(board);
    if(final_count!=initial+direct+accepted)throw runtime_error("Merge count invariant failed");
    write_routes(argv[4],board.routes);
    cerr<<"merge initial="<<initial<<" direct="<<direct<<" transactions="<<attempts
        <<" committed="<<accepted<<" rolled_back="<<rolled<<" old_restored_on_commit="<<restored
        <<" upstream_matched="<<maze.matched<<" now="<<final_count<<'\n';
    return 0;
}
