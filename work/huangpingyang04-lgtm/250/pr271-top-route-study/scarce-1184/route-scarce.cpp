// Schedule branches by sampled CUGR corridor scarcity, regardless of length.
#define main adapter_main
#include "trunk-engine.cpp"
#undef main

struct PinAccess {int exits=-1, density=0;};
struct Task {int net,pin,options,span,exits,density;};
struct Stub {Route route; Range shapes{}; bool active=false;};

vector<vector<PinAccess>> load_access(const vector<Net>& nets,const string& path) {
    vector<vector<PinAccess>> access(nets.size());
    for(const auto& n:nets)access[n.id].resize(n.pins.size());
    ifstream input(path);
    string header;
    getline(input,header);
    int i,j,ways,near,reserved;
    while(input>>i>>j>>ways>>near>>reserved)access.at(i).at(j)={ways,near};
    if(!input.eof())throw runtime_error("Malformed pin access file");
    for(const auto& row:access)for(auto a:row)if(a.exits<0)throw runtime_error("Missing pin access entry");
    return access;
}

vector<Task> load_tasks(const vector<Net>& nets,const vector<vector<PinAccess>>& ports,const string& path,int mode) {
    ifstream input(path);
    string header;
    getline(input,header);
    vector<Task> tasks;
    vector<vector<bool>> covered(nets.size());
    for(const auto& n:nets)covered[n.id].resize(n.pins.size());
    int i,j,options,span;
    while(input>>i>>j>>options>>span) {
        const auto& n=nets.at(i);
        if(j<1||options<0||options>3||covered.at(i).at(j)||span!=md(n.pins.front(),n.pins[j]))
            throw runtime_error("Invalid candidate ranking data");
        covered[i][j]=true;
        const auto a=ports[i].front(), b=ports[i][j];
        tasks.push_back({i,j,options,span,min(a.exits,b.exits),max(a.density,b.density)});
    }
    if(!input.eof()||tasks.size()!=1674)throw runtime_error("Incomplete branch ranking data");
    stable_sort(tasks.begin(),tasks.end(),[&](auto a,auto b) {
        const auto rank=[&](auto t) {
            if(mode==0)return make_tuple(t.options,min(t.exits,5),-t.density,t.span,t.net,t.pin);
            return make_tuple(t.options,min(t.exits,5),mode==1?t.span:-t.span,-t.density,t.net,t.pin);
        };
        return rank(a)<rank(b);
    });
    return tasks;
}

vector<vector<Stub>> reserve(const vector<Net>& nets,const vector<Task>& tasks,
                             const vector<vector<PinAccess>>& access,Board& board,int density) {
    vector<vector<Stub>> stubs(nets.size());
    vector<vector<bool>> done(nets.size());
    for(const auto& n:nets) {
        stubs[n.id].resize(n.pins.size()); done[n.id].resize(n.pins.size());
    }
    int held=0,requested=0;
    auto hold=[&](const Net& n,int pin,int peer,int options) {
        if(done[n.id][pin])return;
        done[n.id][pin]=true;
        if(access[n.id][pin].density<density&&access[n.id][pin].exits>2&&options>1)return;
        ++requested;
        auto& stub=stubs[n.id][pin];
        const auto from=n.pins[pin], to=n.pins[peer];
        vector<Node> selected;
        int best=numeric_limits<int>::max();
        for(const auto& stem:portals(from,n,board.occupied,{},24)) {
            const auto exit=stem.back();
            for(int step:{-pitch,pitch}) {
                auto option=exit;
                (option.layer?option.y:option.x)+=step;
                if(!board.occupied.fits(option)||board.occupied.blocked(n.id,exit,option)!=-1)continue;
                const int cost=md(option,to)-md(from,to)+2*int(stem.size());
                if(cost>=best)continue;
                best=cost; selected=stem; selected.push_back(option);
            }
        }
        if(selected.empty())return;
        append_path(stub.route,n,selected);
        stub.shapes=board.place(n.id,stub.route);
        stub.active=true;
        ++held;
    };
    for(auto t:tasks) {
        hold(nets[t.net],t.pin,0,t.options);
        hold(nets[t.net],0,t.pin,t.options);
    }
    cerr<<"reserved_pins="<<held<<" / "<<requested<<" density="<<density<<'\n';
    return stubs;
}

int main(int argc,char** argv) {
    if(argc!=11)return 2;
    const auto nets=read_nets(argv[1]);
    if(nets.size()!=1184)throw runtime_error("Expected exactly 1184 nets");
    const auto access=load_access(nets,argv[2]);
    const string output=argv[4];
    const int density=stoi(argv[5]),via=stoi(argv[6]),margin=stoi(argv[7]),mode=stoi(argv[8]),
              recover=stoi(argv[9]),repairs=stoi(argv[10]);
    const auto tasks=load_tasks(nets,access,argv[3],mode);
    Board board(nets,via);
    if(route_count(board)!=0)throw runtime_error("Top board already routed");
    cerr<<"clean nets=1184 M11=0 M12=0 V11=0 restored=0\n";
    auto stubs=reserve(nets,tasks,access,board,density);
    vector<vector<bool>> completed(nets.size());
    vector<int> left(nets.size());
    for(const auto& n:nets) {
        completed[n.id].resize(n.pins.size());
        completed[n.id][0]=true;
        left[n.id]=int(n.pins.size())-1;
    }
    auto release=[&](Stub& s) {
        if(s.active) {board.release(s.shapes,s.route);s.active=false;}
    };
    Router maze(board.tracks,24,false,via,margin), wide(board.tracks,4,false,via,margin*2),
           unrestricted(board.tracks,0,false,via);
    int attempted=0,done_branches=0,done_nets=0,early_multi=0,early_short=0;
    for(auto t:tasks) {
        const int id=t.net;
        const auto& full=nets[id];
        if(attempted<250&&full.pins.size()>2) {++early_multi; early_short+=t.span<=3000;}
        release(stubs[id][0]);
        release(stubs[id][t.pin]);
        auto tree=board.remove(id);
        const Route* start=has_route(tree)?&tree:nullptr;
        board.tracks.use_pads(full);
        auto branch=full;
        branch.pins={full.pins.front(),full.pins[t.pin]};
        if(!start)branch.windows={full.windows.front(),full.windows[t.pin]};
        auto trial=maze.run(branch,board.occupied,nullptr,0,start);
        if(trial.status!=connected&&(t.options<=1||mode==1))trial=wide.run(branch,board.occupied,nullptr,0,start);
        if(trial.status==connected) {
            auto reached=full;
            reached.pins.clear();
            for(size_t i=0;i<full.pins.size();++i)
                if(completed[id][i]||int(i)==t.pin)reached.pins.push_back(full.pins[i]);
            if(legal_route(reached,trial.route,board.occupied)) {
                board.install(id,move(trial.route));
                completed[id][t.pin]=true;
                ++done_branches;
                if(--left[id]==0)++done_nets;
            } else trial.status=geometry_blocked;
        }
        if(trial.status!=connected&&start)board.install(id,move(tree));
        if(++attempted%100==0)cerr<<"scheduled="<<attempted<<" branches="<<done_branches
                                 <<" full_nets="<<done_nets<<" corridors="<<t.options<<'\n';
    }
    cerr<<"scarce_first attempted="<<attempted<<" branches="<<done_branches<<" fully_routed="<<done_nets
        <<" multi_first250="<<early_multi<<" short_multi_first250="<<early_short
        <<" upstream_matched="<<maze.matched+wide.matched<<'\n';
    for(const auto& n:nets) {
        for(auto& s:stubs[n.id])release(s);
        if(left[n.id]>0&&has_route(board.routes[n.id]))board.remove(n.id);
    }
    if(route_count(board)!=done_nets)throw runtime_error("Partial branch counted as full route");
    vector<int> priority;
    vector<bool> seen(nets.size());
    for(auto t:tasks)if(!seen[t.net]) {seen[t.net]=true;priority.push_back(t.net);}
    // After the branch reservations have served their purpose, retry complete nets.
    attempted=0;
    for(int id:priority) {
        if(has_route(board.routes[id]))continue;
        if(attempted++>=recover)break;
        const auto& n=nets[id];
        board.tracks.use_pads(n);
        auto trial=wide.run(n,board.occupied);
        if(trial.status==connected)board.install(id,move(trial.route));
    }
    cerr<<"before_transaction="<<route_count(board)<<'\n';
    write_routes(output+".initial",board.routes);
    write_routes(output,board.routes);
    run_repair(board,nets,unrestricted,priority,repairs,output);
    write_routes(output,board.routes);
    cerr<<"done "<<route_count(board)<<" / "<<nets.size()<<'\n';
}
