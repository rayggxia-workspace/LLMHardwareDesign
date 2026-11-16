// Group routes by the wires that actually block one CUGR fine-maze proposal.
#define main adapter_main
#include "trunk-engine.cpp"
#undef main
#include <chrono>

class GroupRepair {
    const vector<Net>& nets;
    Board& board;
    Board protected_routes;
    Router near_maze, wide_maze;
    const int limit;
    const unsigned base_cost;

    Trial relaxed(int id,Router& maze,unsigned price) {
        const auto& n=nets[id];
        board.tracks.use_pads(n);
        protected_routes.tracks.use_pads(n);
        board.tracks.use_relaxed_cost(&protected_routes.tracks,price);
        auto r=maze.run(n,protected_routes.occupied,&board.occupied,price);
        board.tracks.use_relaxed_cost(nullptr,0);
        return r;
    }

public:
    int direct=0,groups=0,old_rerouted=0,rolled_back=0,
        no_candidate=0,too_many=0,alternative_used=0;
    GroupRepair(const vector<Net>& ns,Board& plan,int via,int margin,int cap,unsigned fee)
      :nets(ns),board(plan),protected_routes(ns,via),near_maze(plan.tracks,24,false,via,margin),
       wide_maze(plan.tracks,8,false,via,2*margin),limit(cap),base_cost(fee*cost_scale) {}
    int checked_loops() const {return near_maze.matched+wide_maze.matched;}

    bool place(int index,Route proposed) {
        vector<pair<int,Route>> original;
        vector<int> staged;
        auto evict=[&](int id,const Route& candidate) {
            const auto conflicts=blockers(board,id,candidate);
            if(conflicts.size()+original.size()>size_t(limit))return false;
            for(int i:conflicts)
                if(i<0||i>=int(nets.size())||!has_route(board.routes[i])||has_route(protected_routes.routes[i]))return false;
            for(int i:conflicts)original.emplace_back(i,board.remove(i));
            return true;
        };
        auto add=[&](int id,Route route) {
            if(!legal_route(nets[id],route,board.occupied))return false;
            protected_routes.install(id,route);
            board.install(id,move(route));
            staged.push_back(id);
            return true;
        };
        if(!evict(index,proposed)){++too_many;return false;}
        bool success=add(index,move(proposed));
        for(size_t i=0;success&&i<original.size();++i) {
            const int id=original[i].first;
            const auto& net=nets[id];
            board.tracks.use_pads(net);
            auto best=near_maze.run(net,board.occupied);
            if(best.status!=connected)best=wide_maze.run(net,board.occupied);
            if(best.status!=connected&&original.size()<size_t(limit)) {
                best=relaxed(id,near_maze,base_cost*2);
                if(best.status==connected&&!evict(id,best.route))best.status=graph_blocked;
            }
            success=best.status==connected&&add(id,move(best.route));
        }
        for(int id:staged) {
            success=success&&legal_route(nets[id],board.routes[id],board.occupied);
            protected_routes.remove(id);
        }
        if(success) {
            if(staged.size()!=original.size()+1)throw runtime_error("Incomplete group transaction");
            if(original.empty())++direct;
            else {++groups;old_rerouted+=original.size();}
            return true;
        }
        for(int id:staged)board.remove(id);
        for(auto& [id,route]:original) {
            if(!legal_route(nets[id],route,board.occupied))throw runtime_error("Rollback could not restore prior geometry");
            board.install(id,move(route));
        }
        ++rolled_back;
        return false;
    }

    bool augment(int id) {
        auto first=relaxed(id,near_maze,base_cost);
        if(first.status==connected&&place(id,first.route))return true;
        auto second=relaxed(id,wide_maze,base_cost*3);
        if(second.status==connected&&
           (first.status!=connected||!same_route(first.route,second.route))&&place(id,move(second.route))) {
            ++alternative_used;
            return true;
        }
        if(first.status!=connected&&second.status!=connected)++no_candidate;
        return false;
    }
};

int main(int argc,char** argv) {
    if(argc!=11)return 2;
    const auto nets=read_nets(argv[1]);
    if(nets.size()!=1184)return 2;
    auto input=read_paths(argv[2],nets.size());
    const string path=argv[3];
    const int via=stoi(argv[4]),fee=stoi(argv[5]),cap=stoi(argv[6]),margin=stoi(argv[7]),
        budget=stoi(argv[8]),order=stoi(argv[9]),seconds=stoi(argv[10]);
    if(min({via,fee,cap,margin,budget,seconds})<1)return 2;
    Board board(nets,via);
    for(const auto& n:nets)if(has_route(input[n.id])) {
        if(!legal_route(n,input[n.id],board.occupied))throw runtime_error("Invalid clean-run continuation");
        board.install(n.id,move(input[n.id]));
    }
    const int start=route_count(board);
    write_routes(path+".initial",board.routes);
    write_routes(path,board.routes);
    auto ids=order_by_span(nets);
    if(order==1)reverse(ids.begin(),ids.end());
    if(order==2)iota(ids.begin(),ids.end(),0);
    GroupRepair repair(nets,board,via,margin,cap,fee);
    const auto deadline=chrono::steady_clock::now()+chrono::seconds(seconds);
    int tried=0;
    for(int id:ids) {
        if(has_route(board.routes[id]))continue;
        if(tried>=budget||chrono::steady_clock::now()>=deadline)break;
        ++tried;
        if(repair.augment(id))write_routes(path,board.routes);
        if(tried%25==0)cerr<<"group_attempted="<<tried<<" routed="<<route_count(board)<<'\n';
    }
    const int final=route_count(board);
    if(final!=start+repair.direct+repair.groups)throw runtime_error("Group repair changed previous coverage");
    cerr<<"group initial="<<start<<" tried="<<tried<<" direct="<<repair.direct<<" committed="<<repair.groups
        <<" rolled_back="<<repair.rolled_back<<" old_rerouted="<<repair.old_rerouted
        <<" alternatives_used="<<repair.alternative_used<<" no_candidate="<<repair.no_candidate<<" too_large="
        <<repair.too_many<<" upstream_matched="<<repair.checked_loops()<<" final="<<final<<'\n';
}
