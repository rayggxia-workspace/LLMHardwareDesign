#include <cstdlib>
#include "focus-via.inc"

struct EntryTarget {int net,pin;bool geometry;Node exit;};

Route attach_entry(Route routed,const Route& stem) {
    routed.wires.insert(routed.wires.end(),stem.wires.begin(),stem.wires.end());
    for(auto v:stem.vias)
        if(none_of(routed.vias.begin(),routed.vias.end(),[&](auto p){return p.x==v.x&&p.y==v.y;}))routed.vias.push_back(v);
    return routed;
}

void route_focus(const vector<Net>& nets,Board& board,vector<vector<Stub>>& stubs,int mode,int via,int margin) {
    const char* path=getenv("FOCUS_PLAN");
    if(!path)throw runtime_error("Entry plan required");
    const string folder=path;
    auto entry=read_paths(folder+"/entry.paths",nets.size());
    vector<EntryTarget> selected;
    ifstream records(folder+"/reservations.tsv");
    string header,status;
    getline(records,header);
    int i,j,x,y,ways,kind;
    int planned=0;
    while(records>>i>>j>>status>>x>>y>>ways) {
        const auto& n=nets.at(i);
        if(status!="reserved")continue;
        auto local=n; local.pins={n.pins.at(j),Node{x,y,0}};
        if(!on_track(local.pins.back())||!legal_route(local,entry[i],board.occupied))
            throw runtime_error("Unsafe M11 reservation");
        auto& stub=stubs[i][j];
        stub.route=move(entry[i]); stub.shapes=board.place(i,stub.route); stub.active=true;
        selected.push_back({i,j,false,local.pins.back()});
        ++planned;
    }
    if(!records.eof())throw runtime_error("Malformed M11 entry plan");
    ifstream targets(folder+"/targets.tsv");
    while(targets>>i>>j>>kind)if(kind==1)selected.push_back({i,j,true,{0,0,0}});
    if(!targets.eof()||selected.size()!=size_t(planned+7))throw runtime_error("Malformed focus targets");
    if(mode==1)stable_sort(selected.begin(),selected.end(),[&](const auto& a,const auto& b){
        const auto score=[&](const auto& t){
            const auto& n=nets[t.net];
            return make_tuple(t.geometry,md(n.pins[0],n.pins[t.pin?t.pin:1]),t.net);
        };
        return score(a)<score(b);
    });
    Router local(board.tracks,8,false,via,margin), wide(board.tracks,4,false,via,2*margin);
    FastMaze via_check(board.tracks,via,2*margin);
    int access_done=0,geometry_done=0;
    ofstream receipt("priority-entries.tsv");
    receipt<<"net\tpin\tcategory\tcompleted_first\tv11_retries\n";
    for(const auto& t:selected) {
        auto n=nets[t.net];
        const auto& original=nets[t.net];
        auto& stub=stubs[t.net][t.pin];
        Route chosen;
        int attempts=0;
        if(t.geometry) {
            auto picked=fix_v11(original,board,via_check,16);
            chosen=move(picked.route); attempts=picked.attempts;
        } else {
            board.release(stub.shapes,stub.route); stub.active=false;
            n.pins[t.pin]=t.exit;
            board.tracks.use_pads(original);
            for(auto* router:{&local,&wide}) {
                auto trial=router->run(n,board.occupied);
                if(trial.status!=connected)continue;
                auto combination=attach_entry(move(trial.route),stub.route);
                if(legal_route(original,combination,board.occupied)) {chosen=move(combination);break;}
            }
            if(!has_route(chosen)) {stub.shapes=board.place(t.net,stub.route);stub.active=true;}
        }
        const bool admitted=has_route(chosen);
        if(admitted) {
            if(!legal_route(original,chosen,board.occupied))throw runtime_error("Focus path invalid at commit");
            board.install(t.net,move(chosen));
            if(t.geometry)++geometry_done;else ++access_done;
        }
        receipt<<t.net<<'\t'<<t.pin<<'\t'<<(t.geometry?"geometry":"entry")<<'\t'<<admitted<<'\t'<<attempts<<'\n';
    }
    cerr<<"focus_early reserved="<<planned<<" via_reserved="<<access_done<<" via_fixed="<<geometry_done
        <<" upstream_matched="<<local.matched+wide.matched<<'\n';
}
