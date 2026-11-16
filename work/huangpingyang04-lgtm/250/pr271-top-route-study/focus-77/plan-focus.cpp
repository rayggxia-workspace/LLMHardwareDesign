#define main adapter_main
#include "trunk-engine.cpp"
#undef main
#include "focus-via.inc"

struct Target {int id,pin,kind;};
struct Access {Route route; Node exit; int cost;};

vector<Access> entries(const Net& n,int pin,const Occupancy& occupied) {
    vector<Access> options;
    const auto port=n.pins[pin];
    auto local=n; local.pins={port};
    const auto remote=n.pins[pin==0?1:0];
    for(const auto& stem:portals(port,n,occupied,{},120)) {
        const Node p=stem.back();
        if(p.layer!=0)continue;
        for(int offset:{-pitch,pitch}) {
            const Node e{p.x+offset,p.y,0};
            if(!occupied.fits(e)||occupied.blocked(n.id,p,e)!=-1||
               any_of(n.pins.begin(),n.pins.end(),[&](auto q){return key(e)==key(q);}))continue;
            auto connection=stem;
            connection.push_back(e);
            Route candidate;
            append_path(candidate,n,connection);
            if(legal_route(local,candidate,occupied))
                options.push_back({move(candidate),e,int(stem.size())*2+md(e,remote)-md(port,remote)});
        }
    }
    stable_sort(options.begin(),options.end(),[](const auto& a,const auto& b){return a.cost<b.cost;});
    return options;
}

int main(int argc,char** argv) {
    if(argc!=4)return 2;
    const auto nets=read_nets(argv[1]);
    if(nets.size()!=1184)return 2;
    const string folder=argv[3];
    ifstream target_file(argv[2]);
    vector<Target> targets,repair;
    unordered_set<int> seen;
    int id,pin,kind;
    while(target_file>>id>>pin>>kind) {
        if(!seen.insert(id).second||pin<0||pin>=int(nets.at(id).pins.size())||kind<0||kind>1)
            throw runtime_error("Invalid target list");
        (kind?repair:targets).push_back({id,pin,kind});
    }
    if(!target_file.eof()||targets.size()!=70||repair.size()!=7)return 2;
    Board empty(nets);
    vector<vector<Access>> options(nets.size());
    for(auto t:targets)options[t.id]=entries(nets[t.id],t.pin,empty.occupied);
    stable_sort(targets.begin(),targets.end(),[&](auto a,auto b){return options[a.id].size()<options[b.id].size();});
    vector<Route> assigned(nets.size());
    ofstream selected(folder+"/reservations.tsv");
    selected<<"net\tpin\tstatus\tx\ty\toptions\n";
    int reserved=0;
    for(auto t:targets) {
        const auto& n=nets[t.id];
        auto local=n;local.pins={n.pins[t.pin]};
        bool found=false;
        for(auto& arm:options[t.id])if(legal_route(local,arm.route,empty.occupied)) {
            empty.install(t.id,arm.route);
            assigned[t.id]=move(arm.route);
            selected<<t.id<<'\t'<<t.pin<<"\treserved\t"<<arm.exit.x<<'\t'<<arm.exit.y<<'\t'<<options[t.id].size()<<'\n';
            ++reserved;found=true;break;
        }
        if(!found)selected<<t.id<<'\t'<<t.pin<<"\tfanout_needed\t-1\t-1\t"<<options[t.id].size()<<'\n';
    }
    write_routes(folder+"/entry.paths",assigned);
    cerr<<"M11 entries reserved="<<reserved<<" required=70 fanout_needed="<<70-reserved<<'\n';

    Board pins(nets,28);
    FastMaze checker(pins.tracks);
    ofstream audit(folder+"/v11-audit.tsv");
    audit<<"net\tpin\tx1\ty1\tx2\ty2\tdx\tdy\tother_geometry\ttrials\tlegal_after_v11_repair\n";
    for(auto t:repair) {
        auto a=fix_v11(nets[t.id],pins,checker);
        const auto [x,y,u,v]=a.first_pair;
        audit<<t.id<<'\t'<<t.pin<<'\t'<<x<<'\t'<<y<<'\t'<<u<<'\t'<<v<<'\t'
             <<(x<0?-1:abs(x-u))<<'\t'<<(x<0?-1:abs(y-v))<<'\t'<<a.other_geometry<<'\t'
             <<a.attempts<<'\t'<<has_route(a.route)<<'\n';
    }
}
