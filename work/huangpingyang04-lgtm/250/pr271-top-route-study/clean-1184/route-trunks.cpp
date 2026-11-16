// Route from an empty top board, then attach multi-terminal branches to their trunks.
#define main adapter_main
#include "trunk-engine.cpp"
#undef main

struct Priority {int net, anchor, span, choices;};

int main(int argc,char** argv) {
    if(argc!=9)return 2;
    const auto nets=read_nets(argv[1]);
    if(nets.size()!=1184)throw runtime_error("Expected exactly 1184 nets");
    const string path=argv[3];
    const int density=stoi(argv[4]), via=stoi(argv[5]), guide=stoi(argv[6]), group=stoi(argv[7]), repairs=stoi(argv[8]);
    Board board(nets,via);
    if(route_count(board)!=0)throw runtime_error("Initial top board is already occupied");
    cerr<<"clean nets="<<nets.size()<<" M11=0 M12=0 V11=0 restored=0\n";
    vector<vector<int>> exits(nets.size());
    for(const auto& n:nets)exits[n.id].resize(n.pins.size(),-1);
    ifstream audit(argv[2]);
    string header;
    getline(audit,header);
    int id,pin,ways,near,reserved;
    while(audit>>id>>pin>>ways>>near>>reserved)exits.at(id).at(pin)=ways;
    if(!audit.eof())throw runtime_error("Malformed access audit");
    vector<Priority> ordered;
    vector<vector<bool>> branch_flags(nets.size());
    for(const auto& n:nets) {
        if(find(exits[n.id].begin(),exits[n.id].end(),-1)!=exits[n.id].end())throw runtime_error("Missing access audit");
        int far=1;
        for(size_t i=2;i<n.pins.size();++i)if(md(n.pins[0],n.pins[i])>md(n.pins[0],n.pins[far]))far=i;
        ordered.push_back({n.id,far,md(n.pins[0],n.pins[far]),min(exits[n.id][0],exits[n.id][far])});
        branch_flags[n.id].resize(n.pins.size(),true);
        branch_flags[n.id][0]=branch_flags[n.id][far]=false;
    }
    stable_sort(ordered.begin(),ordered.end(),[&](auto a,auto b){
        const auto rank=[&](auto p){return make_tuple(-p.span/group,p.choices,-p.span,p.net);};
        return rank(a)<rank(b);
    });
    Router maze(board.tracks,24,false,via,guide), broad(board.tracks,0,false,via,-1);
    auto reservations=reserve_access(nets,board,density);
    vector<bool> trunk(nets.size()), complete(nets.size());
    int count=0,attempted=0;
    for(auto row:ordered) {
        const auto& n=nets[row.net];
        board.release(reservations[n.id].shapes,reservations[n.id].stub);
        board.tracks.use_pads(n);
        auto demand=n;
        demand.pins={n.pins[0],n.pins[row.anchor]};
        demand.windows={n.windows[0],n.windows[row.anchor]};
        auto trial=maze.run(demand,board.occupied);
        if(trial.status!=connected&&row.choices<=1&&guide>=0)trial=broad.run(demand,board.occupied);
        if(trial.status==connected) {
            board.install(n.id,move(trial.route));
            trunk[n.id]=true;
            complete[n.id]=n.pins.size()==2;
            ++count;
        }
        if(++attempted%100==0)cerr<<"trunks attempted="<<attempted<<" placed="<<count<<'\n';
    }
    cerr<<"trunks placed="<<count<<" / "<<nets.size()<<" upstream_matched="<<maze.matched<<'\n';
    for(const auto& n:nets)if(!trunk[n.id])fill(branch_flags[n.id].begin(),branch_flags[n.id].end(),false);
    reservations=reserve_access(nets,board,density,&branch_flags);
    int branch_attempts=0,branch_ok=0;
    for(auto row:ordered) {
        const auto& n=nets[row.net];
        board.release(reservations[n.id].shapes,reservations[n.id].stub);
        if(!trunk[n.id]||complete[n.id])continue;
        ++branch_attempts;
        auto tree=board.remove(n.id);
        board.tracks.use_pads(n);
        auto leaves=n;
        leaves.pins.erase(leaves.pins.begin()+row.anchor);
        auto trial=maze.run(leaves,board.occupied,nullptr,0,&tree);
        if(trial.status!=connected&&guide>=0)trial=broad.run(leaves,board.occupied,nullptr,0,&tree);
        if(trial.status==connected&&legal_route(n,trial.route,board.occupied)) {
            board.install(n.id,move(trial.route));
            complete[n.id]=true;
            ++branch_ok;
        }
    }
    cerr<<"short_branches nets_attempted="<<branch_attempts<<" completed="<<branch_ok<<" complete="<<route_count(board)<<'\n';
    for(auto row:ordered) {
        const auto& n=nets[row.net];
        if(complete[n.id])continue;
        board.tracks.use_pads(n);
        auto trial=maze.run(n,board.occupied);
        if(trial.status==connected)board.install(n.id,move(trial.route));
    }
    auto ids=order_by_span(nets);
    cerr<<"complete_before_repair="<<route_count(board)<<'\n';
    write_routes(path+".initial",board.routes);
    write_routes(path,board.routes);
    run_repair(board,nets,broad,ids,repairs,path);
    write_routes(path,board.routes);
    cerr<<"done "<<route_count(board)<<" / "<<nets.size()<<'\n';
}
